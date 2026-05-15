# License : GPLv2.0
# copyright (c) 2026  Dave Bailey
# Author: Dave Bailey (dbisu, @daveisu)
# DuckyScript 3.0 Extension & Parsing Overhaul integrated
#
#  TODO: ADD support for the following:
# Add LED functionality
import re
import time
import random
import digitalio
from digitalio import DigitalInOut, Pull
from adafruit_debouncer import Debouncer
import board
from board import *
import asyncio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from pins import *

# comment out these lines for non_US keyboards
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS as KeyboardLayout
from adafruit_hid.keycode import Keycode

# uncomment these lines for non_US keyboards
# replace LANG with appropriate language
#from keyboard_layout_win_LANG import KeyboardLayout as KeyboardLayout
#from keycode_win_LANG import Keycode

class ReturnException(Exception):
    pass

def _capsOn():
    return kbd.led_on(Keyboard.LED_CAPS_LOCK)

def _numOn():
    return kbd.led_on(Keyboard.LED_NUM_LOCK)

def _scrollOn():
    return kbd.led_on(Keyboard.LED_SCROLL_LOCK)

def pressLock(key):
    kbd.press(key)
    kbd.release(key)

def SaveKeyboardLedState():
    variables["$_INITIAL_SCROLLLOCK"] = _scrollOn()
    variables["$_INITIAL_NUMLOCK"] = _numOn()
    variables["$_INITIAL_CAPSLOCK"] = _capsOn()

def RestoreKeyboardLedState():
    if(variables["$_INITIAL_CAPSLOCK"] != _capsOn()):
        pressLock(Keycode.CAPS_LOCK)
    if(variables["$_INITIAL_NUMLOCK"] != _numOn()):
        pressLock(Keycode.NUM_LOCK)
    if(variables["$_INITIAL_SCROLLLOCK"] != _scrollOn()):
        pressLock(Keycode.SCROLL_LOCK)

duckyKeys = {
    'WINDOWS': Keycode.GUI, 'RWINDOWS': Keycode.RIGHT_GUI, 'GUI': Keycode.GUI, 'RGUI': Keycode.RIGHT_GUI, 'COMMAND': Keycode.GUI, 'RCOMMAND': Keycode.RIGHT_GUI,
    'APP': Keycode.APPLICATION, 'MENU': Keycode.APPLICATION, 'SHIFT': Keycode.SHIFT, 'RSHIFT': Keycode.RIGHT_SHIFT,
    'ALT': Keycode.ALT, 'RALT': Keycode.RIGHT_ALT, 'OPTION': Keycode.ALT, 'ROPTION': Keycode.RIGHT_ALT, 'CONTROL': Keycode.CONTROL, 'CTRL': Keycode.CONTROL, 'RCTRL': Keycode.RIGHT_CONTROL,
    'ALT_LEFT': Keycode.ALT, 'ALT_RIGHT': Keycode.RIGHT_ALT, 'LEFT_ALT': Keycode.ALT, 'RIGHT_ALT': Keycode.RIGHT_ALT,
    'DOWNARROW': Keycode.DOWN_ARROW, 'DOWN': Keycode.DOWN_ARROW, 'LEFTARROW': Keycode.LEFT_ARROW,
    'LEFT': Keycode.LEFT_ARROW, 'RIGHTARROW': Keycode.RIGHT_ARROW, 'RIGHT': Keycode.RIGHT_ARROW,
    'UPARROW': Keycode.UP_ARROW, 'UP': Keycode.UP_ARROW, 'BREAK': Keycode.PAUSE,
    'PAUSE': Keycode.PAUSE, 'CAPSLOCK': Keycode.CAPS_LOCK, 'DELETE': Keycode.DELETE,
    'END': Keycode.END, 'ESC': Keycode.ESCAPE, 'ESCAPE': Keycode.ESCAPE, 'HOME': Keycode.HOME,
    'INSERT': Keycode.INSERT, 'NUMLOCK': Keycode.KEYPAD_NUMLOCK, 'PAGEUP': Keycode.PAGE_UP,
    'PAGEDOWN': Keycode.PAGE_DOWN, 'PRINTSCREEN': Keycode.PRINT_SCREEN, 'ENTER': Keycode.ENTER,
    'SCROLLLOCK': Keycode.SCROLL_LOCK, 'SPACE': Keycode.SPACE, 'TAB': Keycode.TAB,
    'BACKSPACE': Keycode.BACKSPACE,
    'A': Keycode.A, 'B': Keycode.B, 'C': Keycode.C, 'D': Keycode.D, 'E': Keycode.E,
    'F': Keycode.F, 'G': Keycode.G, 'H': Keycode.H, 'I': Keycode.I, 'J': Keycode.J,
    'K': Keycode.K, 'L': Keycode.L, 'M': Keycode.M, 'N': Keycode.N, 'O': Keycode.O,
    'P': Keycode.P, 'Q': Keycode.Q, 'R': Keycode.R, 'S': Keycode.S, 'T': Keycode.T,
    'U': Keycode.U, 'V': Keycode.V, 'W': Keycode.W, 'X': Keycode.X, 'Y': Keycode.Y,
    'Z': Keycode.Z, 'F1': Keycode.F1, 'F2': Keycode.F2, 'F3': Keycode.F3,
    'F4': Keycode.F4, 'F5': Keycode.F5, 'F6': Keycode.F6, 'F7': Keycode.F7,
    'F8': Keycode.F8, 'F9': Keycode.F9, 'F10': Keycode.F10, 'F11': Keycode.F11,
    'F12': Keycode.F12, 'F13': Keycode.F13, 'F14': Keycode.F14, 'F15': Keycode.F15,
    'F16': Keycode.F16, 'F17': Keycode.F17, 'F18': Keycode.F18, 'F19': Keycode.F19,
    'F20': Keycode.F20, 'F21': Keycode.F21, 'F22': Keycode.F22, 'F23': Keycode.F23,
    'F24': Keycode.F24
}
duckyConsumerKeys = {
    'MK_VOLUP': ConsumerControlCode.VOLUME_INCREMENT, 'MK_VOLDOWN': ConsumerControlCode.VOLUME_DECREMENT, 'MK_MUTE': ConsumerControlCode.MUTE,
    'MK_NEXT': ConsumerControlCode.SCAN_NEXT_TRACK, 'MK_PREV': ConsumerControlCode.SCAN_PREVIOUS_TRACK,
    'MK_PP': ConsumerControlCode.PLAY_PAUSE, 'MK_STOP': ConsumerControlCode.STOP
}

variables = {
    "$_RANDOM_MIN": 0, "$_RANDOM_MAX": 65535,
    "$_EXFIL_MODE_ENABLED": False, "$_EXFIL_LEDS_ENABLED": False,
    "$_INITIAL_SCROLLLOCK": False, "$_INITIAL_NUMLOCK": False, "$_INITIAL_CAPSLOCK": False,
    "$_JITTER": 0,
    "$_OS": "WINDOWS",
    "WINDOWS": "WINDOWS", "MACOS": "MACOS", "LINUX": "LINUX", "CHROMEOS": "CHROMEOS",
    "$_RECEIVED_HOST_LOCK_LED_REPLY": True,
    "$_HOST_CONFIGURATION_REQUEST_COUNT": 0
}
internalVariables = {"$_CAPSLOCK_ON": _capsOn, "$_NUMLOCK_ON": _numOn, "$_SCROLLLOCK_ON": _scrollOn}
defines = {}
functions = {}
extensions = {}

letters = "abcdefghijklmnopqrstuvwxyz"
numbers = "0123456789"
specialChars = "!@#$%^&*()"

class IF:
    def __init__(self, condition, codeIter):
        self.condition = condition
        self.codeIter = list(codeIter)
        self.lastIfResult = None

    def _exitIf(self):
        _depth = 0
        for line in self.codeIter:
            line = self.codeIter.pop(0)
            line = line.strip()
            if line.upper().startswith("END_IF"):
                _depth -= 1
            elif line.upper().startswith("IF"):
                _depth += 1
            if _depth < 0:
                print("No else, exiting" + str(list(self.codeIter)))
                break
        return(self.codeIter)

    async def runIf(self):
        if isinstance(self.condition, str):
            self.lastIfResult = evaluateExpression(self.condition)
        elif isinstance(self.condition, bool):
            self.lastIfResult = self.condition
        else:
            raise ValueError("Invalid condition type")

        depth = 0
        for line in self.codeIter:
            line = self.codeIter.pop(0)
            line = line.strip()
            if line == "":
                continue

            if line.startswith("IF"):
                depth += 1
            elif line.startswith("END_IF"):
                if depth == 0:
                    return(self.codeIter, -1)
                depth -=1

            elif line.startswith("ELSE") and depth == 0:
                if self.lastIfResult is False:
                    line = line[4:].strip()  # Remove 'ELSE' and strip whitespace
                    if line.startswith("IF"):
                        nestedCondition = _getIfCondition(line)
                        self.codeIter, self.lastIfResult = await IF(nestedCondition, self.codeIter).runIf()
                        if self.lastIfResult == -1 or self.lastIfResult == True:
                            return(self.codeIter, True)
                    else:
                        return await IF(True, self.codeIter).runIf()
                else:
                    self._exitIf()
                    break

            elif self.lastIfResult:
                self.codeIter = list(await parseLine(line, self.codeIter))
        return(self.codeIter, self.lastIfResult)

def _getIfCondition(line):
    """Robust extractor for IF (...) THEN logic"""
    stripped = line.strip()
    if stripped.upper().startswith("IF "):
        stripped = stripped[3:].strip()
    if stripped.upper().endswith(" THEN"):
        stripped = stripped[:-5].strip()
    return stripped

def _isCodeBlock(line):
    line = line.upper().strip()
    if line.startswith("IF ") or line.startswith("WHILE") or line.startswith("IF_DEFINED") or line.startswith("EXTENSION") or line.startswith("FUNCTION") or line.startswith("BUTTON_DEF") or line.startswith("REM_BLOCK"):
        return True
    return False

def _getCodeBlock(linesIter):
    """Returns the code block starting at the given line."""
    code = []
    depth = 1
    for line in linesIter:
        line = line.strip()
        if line.upper().startswith("END_"):
            depth -= 1
        elif _isCodeBlock(line):
            depth += 1
        if depth <= 0:
            break
        code.append(line)
    return code

def replaceBooleans(text):
    text = re.sub(r'[Tt][Rr][Uu][Ee]', 'True', text)
    text = re.sub(r'[Ff][Aa][Ll][Ss][Ee]', 'False', text)
    return text

def evaluateExpression(expression):
    """Evaluates an expression with variables and returns the result."""
    expression = replaceVariables(expression)
    expression = replaceBooleans(expression)

    expression = expression.replace("^", "**")
    expression = expression.replace("&&", "and")
    expression = expression.replace("||", "or")

    # Handle ! operator (NOT), but ignore != using non-regex methods
    expression = expression.replace("!=", "___NOT_EQ___")
    expression = expression.replace("!", " not ")
    expression = expression.replace("___NOT_EQ___", "!=")

    # % works natively in python's eval(). Replace 'MOD' explicitly if used without regex bounds
    expression = expression.replace(" MOD ", " % ")

    expression = expression.replace("TRUE", "True")
    expression = expression.replace("FALSE", "False")

    try:
        return eval(expression, {}, variables)
    except Exception:
        # Fallback for bare strings or identifiers like in DuckyScript 3 variable assignments
        return expression.strip()

def deepcopy(List):
    return(List[:])

def convertLine(line):
    commands = []
    for key in filter(None, line.split(" ")):
        key = key.upper()
        command_keycode = duckyKeys.get(key, None)
        command_consumer_keycode = duckyConsumerKeys.get(key, None)
        if command_keycode is not None:
            commands.append(command_keycode)
        elif command_consumer_keycode is not None:
            commands.append(1000+command_consumer_keycode)
        elif hasattr(Keycode, key):
            commands.append(getattr(Keycode, key))
        else:
            print(f"Unknown key: <{key}>")
    return commands

async def runScriptLine(line):
    keys = convertLine(line)
    for k in keys:
        if k > 1000:
            consumerControl.press(int(k-1000))
        else:
            kbd.press(k)
    for k in reversed(keys):
        if k > 1000:
            consumerControl.release()
        else:
            kbd.release(k)

    jitter = int(variables.get("$_JITTER", 0))
    if jitter > 0:
        await asyncio.sleep(random.randint(0, jitter) / 1000.0)

async def sendString(line):
    jitter = int(variables.get("$_JITTER", 0))
    if jitter > 0:
        for char in line:
            layout.write(char)
            await asyncio.sleep(random.randint(0, jitter) / 1000.0)
    else:
        layout.write(line)

def replaceVariables(line):
    for var in variables:
        line = line.replace(var, str(variables[var]))
    for var in internalVariables:
        line = line.replace(var, str(internalVariables[var]()))
    return line

def replaceDefines(line):
    for define, value in defines.items():
        line = line.replace(define, value)
    return line

async def parseLine(line, script_lines):
    global defaultDelay, variables, functions, extensions, defines
    line = line.strip()

    # DuckyScript 3.0 dynamic variable handling for inline occurrences
    while "$_RANDOM_INT" in line:
        line = line.replace("$_RANDOM_INT", str(random.randint(int(variables.get("$_RANDOM_MIN", 0)), int(variables.get("$_RANDOM_MAX", 65535)))), 1)

    # Payload-specific random keycodes
    while "$_RANDOM_LETTER_KEYCODE" in line:
        line = line.replace("$_RANDOM_LETTER_KEYCODE", random.choice(letters + letters.upper()), 1)
    while "$_RANDOM_LOWER_LETTER_KEYCODE" in line:
        line = line.replace("$_RANDOM_LOWER_LETTER_KEYCODE", random.choice(letters), 1)
    while "$_RANDOM_UPPER_LETTER_KEYCODE" in line:
        line = line.replace("$_RANDOM_UPPER_LETTER_KEYCODE", random.choice(letters.upper()), 1)
    while "$_RANDOM_NUMBER_KEYCODE" in line:
        line = line.replace("$_RANDOM_NUMBER_KEYCODE", random.choice(numbers), 1)

    while "$_RANDOM_LETTER" in line:
        line = line.replace("$_RANDOM_LETTER", random.choice(letters + letters.upper()), 1)
    while "$_RANDOM_NUMBER" in line:
        line = line.replace("$_RANDOM_NUMBER", random.choice(numbers), 1)
    while "$_RANDOM_SPECIAL" in line:
        line = line.replace("$_RANDOM_SPECIAL", random.choice(specialChars), 1)

    line = replaceDefines(line)

    if line[:10] == "INJECT_MOD":
        line = line[11:]
    elif line.startswith("INJECT_VAR"):
        var_name = line[11:].strip()
        if var_name in variables:
            await sendString(str(variables[var_name]))
        else:
            print(f"[SCRIPT]: Variable {var_name} not found")
    elif line.startswith("REM_BLOCK"):
        while line.startswith("END_REM") == False:
            line = next(script_lines).strip()
    elif(line[0:3] == "REM"):
        pass
    elif line == "RETURN":
        raise ReturnException()
    elif line == "HIDE_PAYLOAD":
        print("[SCRIPT]: HIDE_PAYLOAD executed")
    elif line == "RESTORE_PAYLOAD":
        print("[SCRIPT]: RESTORE_PAYLOAD executed")
    elif line.startswith("VERSION"):
        pass # DS3 Extensions define Version, skipped at runtime
    elif line.startswith("ATTACKMODE"):
        pass # Ignored dynamically; usually handled in boot.py for pico-ducky
    elif line == "SAVE_HOST_KEYBOARD_STATE":
        SaveKeyboardLedState()
    elif line.startswith("HOLD"):
        key = line[5:].strip().upper()
        commandKeycode = duckyKeys.get(key, None)
        if commandKeycode:
            kbd.press(commandKeycode)
        else:
            print(f"Unknown key to HOLD: <{key}>")
    elif line.startswith("RELEASE"):
        key = line[8:].strip().upper()
        commandKeycode = duckyKeys.get(key, None)
        if commandKeycode:
            kbd.release(commandKeycode)
        else:
            print(f"Unknown key to RELEASE: <{key}>")
    elif(line[0:5] == "DELAY"):
        line = replaceVariables(line)
        await asyncio.sleep(float(line[6:])/1000)
    elif line == "STRINGLN":
        line = next(script_lines).strip()
        line = replaceVariables(line)
        while line.startswith("END_STRINGLN") == False:
            await sendString(line)
            kbd.press(Keycode.ENTER)
            kbd.release(Keycode.ENTER)
            line = next(script_lines).strip()
            line = replaceVariables(line)
            line = replaceDefines(line)
    elif(line[0:8] == "STRINGLN"):
        await sendString(replaceVariables(line[9:]))
        kbd.press(Keycode.ENTER)
        kbd.release(Keycode.ENTER)
    elif line == "STRING":
        line = next(script_lines).strip()
        line = replaceVariables(line)
        while line.startswith("END_STRING") == False:
            await sendString(line)
            line = next(script_lines).strip()
            line = replaceVariables(line)
            line = replaceDefines(line)
    elif(line[0:6] == "STRING"):
        await sendString(replaceVariables(line[7:]))
    elif(line[0:5] == "PRINT"):
        line = replaceVariables(line[6:])
        print("[SCRIPT]: " + line)
    elif(line[0:6] == "IMPORT"):
        await runScript(line[7:])
    elif(line.startswith("IMPORT_EXTENSION")):
        ext_filename = line.split()[1]
        try:
            with open(ext_filename, "r", encoding="utf-8") as ext_f:
                ext_lines = iter(ext_f.readlines())
                for ext_line in ext_lines:
                    await parseLine(ext_line, ext_lines)
        except OSError:
            print(f"[ERROR] Could not load extension: {ext_filename}")
    elif(line[0:13] == "DEFAULT_DELAY"):
        defaultDelay = int(line[14:]) * 10
    elif(line[0:12] == "DEFAULTDELAY"):
        defaultDelay = int(line[13:]) * 10
    elif(line[0:3] == "LED"):
        if(led.value == True):
            led.value = False
        else:
            led.value = True
    elif(line[:7] == "LED_OFF"):
        led.value = False
    elif(line[:5] == "LED_R"):
        led.value = True
    elif(line[:5] == "LED_G"):
        led.value = True
    elif(line[0:21] == "WAIT_FOR_BUTTON_PRESS"):
        button_pressed = False
        while not button_pressed:
            button1.update()
            button1Pushed = button1.fell
            if(button1Pushed):
                print("Button 1 pushed")
                button_pressed = True
    elif line.startswith("VAR"):
        match = re.match(r"VAR\s+\$(\w+)\s*=\s*(.+)", line)
        if match:
            varName = f"${match.group(1)}"
            value = evaluateExpression(match.group(2))
            variables[varName] = value
        else:
            raise SyntaxError(f"Invalid variable declaration: {line}")
    elif line.startswith("$"):
        match = re.match(r"\$(\w+)\s*=\s*(.+)", line)
        if match:
            varName = f"${match.group(1)}"
            expression = match.group(2)
            value = evaluateExpression(expression)
            variables[varName] = value
        else:
            raise SyntaxError(f"Invalid variable update, declare variable first: {line}")
    elif line.startswith("DEFINE"):
        defineLocation = line.find(" ")
        valueLocation = line.find(" ", defineLocation + 1)
        defineName = line[defineLocation+1:valueLocation]
        defineValue = line[valueLocation+1:]
        defines[defineName] = defineValue
    elif line.startswith("IF_DEFINED_TRUE") or line.startswith("IF_DEFINED_FALSE"):
        is_true_check = line.startswith("IF_DEFINED_TRUE")
        condition_val = line.split()[1] if len(line.split()) > 1 else "FALSE"

        if is_true_check:
            condition_met = (condition_val == "TRUE" or condition_val == "True")
        else:
            condition_met = (condition_val == "FALSE" or condition_val == "False")

        ifCode = list(_getCodeBlock(script_lines))

        blocks = []
        current_block = []
        current_condition = condition_met
        depth = 0

        for b_line in ifCode:
            stripped = b_line.strip()
            if stripped.upper().startswith("END_"):
                depth -= 1

            if depth == 0:
                if stripped.upper().startswith("ELSE_DEFINED"):
                    blocks.append((current_condition, current_block))
                    current_condition = not condition_met
                    current_block = []
                    continue

            current_block.append(b_line)

            if _isCodeBlock(stripped):
                depth += 1

        blocks.append((current_condition, current_block))

        for cond, block in blocks:
            if cond:
                blockIter = iter(deepcopy(block))
                for bline in blockIter:
                    await parseLine(bline, blockIter)
                break
    elif line.startswith("EXTENSION"):
        ext_name = line.split()[1] if len(line.split()) > 1 else "UNNAMED"

        # ALWAYS parse the inline block to advance the script pointer properly
        ext_code = []
        try:
            next_line = next(script_lines).strip()
            while next_line != "END_EXTENSION":
                ext_code.append(next_line)
                next_line = next(script_lines).strip()
        except StopIteration:
            pass

        # Check if the extension is already loaded
        if ext_name not in extensions:
            extensions[ext_name] = "LOADING" # Mark as loading to prevent recursive reads

            # Build potential file paths to look for on the Pico's root
            file_candidates = [
                f"{ext_name}.dd", f"{ext_name}.txt",
                f"{ext_name.lower()}.dd", f"{ext_name.lower()}.txt"
            ]

            # Special case to look for os_detect.dd/txt as requested
            if ext_name == "OS_DETECTION":
                file_candidates = ["os_detect.dd", "os_detect.txt"] + file_candidates

            loaded_from_file = False

            # Try loading from files dynamically
            for fname in file_candidates:
                try:
                    with open(fname, "r", encoding="utf-8") as ext_f:
                        ext_lines_list = ext_f.readlines()
                        extIter = iter(ext_lines_list)
                        for extLine in extIter:
                            await parseLine(extLine, extIter)
                    extensions[ext_name] = True
                    loaded_from_file = True
                    print(f"[SCRIPT]: Extension {ext_name} auto-loaded from {fname}")
                    break
                except OSError:
                    continue

            # Execute standard inline block parsing if external file not found
            if not loaded_from_file:
                extensions[ext_name] = ext_code

                # Execute the extension block immediately (inline execution)
                extIter = iter(deepcopy(ext_code))
                for extLine in extIter:
                    await parseLine(extLine, extIter)

        elif extensions[ext_name] == "LOADING":
            # The extension file being loaded contained its own EXTENSION block. We execute the inner code now.
            extensions[ext_name] = ext_code
            extIter = iter(deepcopy(ext_code))
            for extLine in extIter:
                await parseLine(extLine, extIter)

    elif line.startswith("BUTTON_DEF"):
        button_code = []
        line = next(script_lines).strip()
        while line != "END_BUTTON":
            button_code.append(line)
            line = next(script_lines).strip()
        functions["BUTTON_DEF"] = button_code
    elif line.startswith("FUNCTION"):
        func_name = line.split()[1]
        functions[func_name] = []
        line = next(script_lines).strip()
        while line != "END_FUNCTION":
            functions[func_name].append(line)
            line = next(script_lines).strip()
    elif line.startswith("WHILE"):
        condition = line[5:].strip()
        loopCode = list(_getCodeBlock(script_lines))
        while evaluateExpression(condition) == True:
            currentIter = iter(deepcopy(loopCode))
            for loopLine in currentIter:
                await parseLine(loopLine, currentIter)

    elif line.upper().startswith("IF"):
        condition = _getIfCondition(line)
        ifCode = list(_getCodeBlock(script_lines))

        blocks = []
        current_block = []
        current_condition = condition
        depth = 0

        for b_line in ifCode:
            stripped = b_line.strip()
            if stripped.upper().startswith("END_"):
                depth -= 1

            if depth == 0:
                if stripped.upper().startswith("ELSE IF"):
                    blocks.append((current_condition, current_block))
                    if_part = stripped[4:].strip() # Extract "ELSE IF (...)" -> "IF (...)"
                    current_condition = _getIfCondition(if_part)
                    current_block = []
                    continue
                elif stripped.upper().startswith("ELSE"):
                    blocks.append((current_condition, current_block))
                    current_condition = "True"
                    current_block = []
                    continue

            current_block.append(b_line)

            if _isCodeBlock(stripped):
                depth += 1

        blocks.append((current_condition, current_block))

        # Evaluate standard DS3 IF / ELSE IF / ELSE chains
        for cond, block in blocks:
            if evaluateExpression(cond):
                blockIter = iter(deepcopy(block))
                for bline in blockIter:
                    await parseLine(bline, blockIter)
                break # Only run the first matched block

    elif line.upper().startswith("END_IF"):
        pass
    elif line == "RANDOM_LOWERCASE_LETTER":
        await sendString(random.choice(letters))
    elif line == "RANDOM_UPPERCASE_LETTER":
        await sendString(random.choice(letters.upper()))
    elif line == "RANDOM_LETTER":
        await sendString(random.choice(letters + letters.upper()))
    elif line == "RANDOM_NUMBER":
        await sendString(random.choice(numbers))
    elif line == "RANDOM_SPECIAL":
        await sendString(random.choice(specialChars))
    elif line == "RANDOM_CHAR":
        await sendString(random.choice(letters + letters.upper() + numbers + specialChars))
    elif line == "VID_RANDOM" or line == "PID_RANDOM":
        for _ in range(4):
            await sendString(random.choice("0123456789ABCDEF"))
    elif line == "MAN_RANDOM" or line == "PROD_RANDOM":
        for _ in range(12):
            await sendString(random.choice(letters + letters.upper() + numbers))
    elif line == "SERIAL_RANDOM":
        for _ in range(12):
            await sendString(random.choice(letters + letters.upper() + numbers + specialChars))
    elif line == "RESET":
        kbd.release_all()
    elif line == "SAVE_HOST_KEYBOARD_LOCK_STATE":
        SaveKeyboardLedState()
    elif line == "RESTORE_HOST_KEYBOARD_LOCK_STATE":
        RestoreKeyboardLedState()
    elif line == "WAIT_FOR_SCROLL_CHANGE":
        last_scroll_state = _scrollOn()
        while True:
            current_scroll_state = _scrollOn()
            if current_scroll_state != last_scroll_state:
                break
            await asyncio.sleep(0.01)
    elif line == "WAIT_FOR_CAPS_ON":
        while not _capsOn():
            await asyncio.sleep(0.01)
    elif line == "WAIT_FOR_CAPS_OFF":
        while _capsOn():
            await asyncio.sleep(0.01)
    elif line == "WAIT_FOR_NUM_ON":
        while not _numOn():
            await asyncio.sleep(0.01)
    elif line == "WAIT_FOR_NUM_OFF":
        while _numOn():
            await asyncio.sleep(0.01)
    elif line == "WAIT_FOR_SCROLL_ON":
        while not _scrollOn():
            await asyncio.sleep(0.01)
    elif line == "WAIT_FOR_SCROLL_OFF":
        while _scrollOn():
            await asyncio.sleep(0.01)
    # Allows calls like DETECT_OS()
    elif line in functions:
            funcIter = iter(deepcopy(functions[line]))
            try:
                for funcLine in funcIter:
                    await parseLine(funcLine, funcIter)
            except ReturnException:
                pass
    else:
        await runScriptLine(line)

    return(script_lines)

kbd = Keyboard(usb_hid.devices)
consumerControl = ConsumerControl(usb_hid.devices)
layout = KeyboardLayout(kbd)

def getProgrammingStatus():
    progStatus = not progStatusPin.value
    return(progStatus)

defaultDelay = 0

async def runScript(file):
    global defaultDelay

    duckyScriptPath = file
    restart = True
    try:
        while restart:
            restart = False
            with open(duckyScriptPath, "r", encoding='utf-8') as f:
                script_lines = iter(f.readlines())
                previousLine = ""
                try:
                    for line in script_lines:
                        print(f"runScript: {line}")
                        if(line[0:6] == "REPEAT"):
                            for i in range(int(line[7:])):
                                await parseLine(previousLine, script_lines)
                                await asyncio.sleep(float(defaultDelay) / 1000)
                        elif line.startswith("RESTART_PAYLOAD"):
                            restart = True
                            break
                        elif line.startswith("STOP_PAYLOAD"):
                            restart = False
                            break
                        else:
                            await parseLine(line, script_lines)
                            previousLine = line
                        await asyncio.sleep(float(defaultDelay) / 1000)
                except ReturnException:
                    print("Script executed RETURN")
                    restart = False
    except OSError as e:
        print("Unable to open file", file)

def selectPayload():
    global payload1Pin, payload2Pin, payload3Pin, payload4Pin
    payload = "payload.dd"
    payload1State = not payload1Pin.value
    payload2State = not payload2Pin.value
    payload3State = not payload3Pin.value
    payload4State = not payload4Pin.value

    if(payload1State == True):
        payload = "payload.dd"
    elif(payload2State == True):
        payload = "payload2.dd"
    elif(payload3State == True):
        payload = "payload3.dd"
    elif(payload4State == True):
        payload = "payload4.dd"
    else:
        payload = "payload.dd"

    return payload

async def blink_led(led):
    print("Blink")
    if(board.board_id == 'raspberry_pi_pico' or board.board_id == 'raspberry_pi_pico2'):
        await blink_pico_led(led)
    elif(board.board_id == 'raspberry_pi_pico_w' or board.board_id == 'raspberry_pi_pico2_w'):
        await blink_pico_w_led(led)

async def blink_pico_led(led):
    print("starting blink_pico_led")
    led_state = False
    while True:
        if(variables.get("$_EXFIL_LEDS_ENABLED")):
            led.duty_cycle = 65535
        else:
            if led_state:
                for i in range(100):
                    if i < 50:
                        led.duty_cycle = int(i * 2 * 65535 / 100)
                    await asyncio.sleep(0.01)
                led_state = False
            else:
                for i in range(100):
                    if i >= 50:
                        led.duty_cycle = 65535 - int((i - 50) * 2 * 65535 / 100)
                    await asyncio.sleep(0.01)
                led_state = True
        await asyncio.sleep(0)

async def blink_pico_w_led(led):
    print("starting blink_pico_w_led")
    led_state = False
    while True:
        if(variables.get("$_EXFIL_LEDS_ENABLED")):
            led.value = 1
        else:
            if led_state:
                led.value = 1
                await asyncio.sleep(0.5)
                led_state = False
            else:
                led.value = 0
                await asyncio.sleep(0.5)
                led_state = True
            await asyncio.sleep(0.5)

async def monitor_buttons(button1):
    global inBlinkeyMode, inMenu, enableRandomBeep, enableSirenMode, pixel
    print("starting monitor_buttons")
    button1Down = False
    while True:
        button1.update()

        button1Pushed = button1.fell
        button1Released = button1.rose

        if(button1Pushed):
            print("Button 1 pushed")
            button1Down = True
        if(button1Released):
            print("Button 1 released")
            if(button1Down):
                print("push and released")

        if(button1Released):
            if(button1Down):
                if "BUTTON_DEF" in functions:
                    print("Running BUTTON_DEF")
                    funcIter = iter(deepcopy(functions["BUTTON_DEF"]))
                    try:
                        for funcLine in funcIter:
                            await parseLine(funcLine, funcIter)
                    except ReturnException:
                        pass
                else:
                    payload = selectPayload()
                    print("Running ", payload)
                    await runScript(payload)
                    print("Done")
            button1Down = False

        await asyncio.sleep(0)

async def monitor_led_changes():
    print("starting monitor_led_changes")

    while True:
        if variables.get("$_EXFIL_MODE_ENABLED"):
            try:
                bit_list = []
                last_caps_state = _capsOn()
                last_num_state = _numOn()
                last_scroll_state = _scrollOn()

                with open("loot.bin", "ab") as file:
                    while variables.get("$_EXFIL_MODE_ENABLED"):
                        caps_state = _capsOn()
                        num_state = _numOn()
                        scroll_state = _scrollOn()

                        if caps_state != last_caps_state:
                            bit_list.append(0)
                            last_caps_state = caps_state

                        elif num_state != last_num_state:
                            bit_list.append(1)
                            last_num_state = num_state

                        if len(bit_list) == 8:
                            byte = 0
                            for b in bit_list:
                                byte = (byte << 1) | b
                            file.write(bytes([byte]))
                            bit_list = []

                        if scroll_state != last_scroll_state:
                            variables["$_EXFIL_LEDS_ENABLED"] = False
                            break

                        await asyncio.sleep(0.001)
            except Exception as e:
                print(f"Error occurred: {e}")

        await asyncio.sleep(0.0)
