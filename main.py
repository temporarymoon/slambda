#!/usr/bin/env python3
import evdev # for listening to keyboard events
import asyncio # for async stuff
import sys # for getting commnad line arguments
import json # for json parsing

from enum import Enum, IntEnum
from evdev.events import InputEvent, KeyEvent, SynEvent
from evdev.ecodes import keys, KEY, SYN, REL, ABS, EV_KEY, EV_REL, EV_ABS, EV_SYN, KEY_A, KEY_J, KEY_P

config = sys.argv[1]

f = open(config, "r")
fileContents = f.read()
config = json.loads(fileContents)

# List all devices
allDevices = [evdev.InputDevice(path) for path in evdev.list_devices()]

if not isinstance(config["debug"], list):
    config["debug"] = []

logEvents = "logStuff" in config["debug"]

if "listDevices" in config["debug"]:
    print("Devices:")
    for device in allDevices:
        print(f"{device.path}, {device.name}, {device.phys}")

def somePaths(prefix):
    return [path[(len(prefix) + 1):] for path in config["inputs"] if path.startswith(f"{prefix}:")]

inputPaths = somePaths("path")
inputNames = somePaths("name") 

devices = []

for device in allDevices:
    if device.path in inputPaths or device.name in inputNames:
        devices.append(device)

print("\nEvents:")
print(f"Working with {len(devices)} devices")

ec = evdev.ecodes
blacklisted = []

def keyCode(name):
    return evdev.ecodes.ecodes[f"KEY_{name.upper()}"]

for combo in config["combos"]:
    combo["from"] = [keyCode(key) for key in combo["from"]]
    combo["to"] = [keyCode(key) for key in combo["to"]]

def mapChord(chord):
    codes = [keyEvent.event.code for keyEvent in chord]

    for remap in config["combos"]:
        if not all(code in codes for code in remap["from"]):
            continue

        if len(codes) == len(remap["from"]): # or not remap["exact"]:
            return [key for key in remap["to"]] + [code for code in codes if code not in remap["from"]]

    print("No mapping found")

    return None # default to the unsorted chord

def msToSeconds(ms):
    return ms/1000

class DeviceManager:
    delay = msToSeconds(30) # in seconds

    def __init__(self, device, ui = None):
        self.device = device
        self.taskEndChord = None
        self.currentChord = []
        self.pressedCombos = []
        self.ui = ui

        if ui != None:
            self.device.grab()

    def writeUi(self, type, code, value, fallback = None):
        if logEvents or self.ui == None: 
            print(
                "OUTPUT",
                fallback if fallback != None else f"Type: {type}, Code: {code}, value: {value}", 
                sep = ": "
            )

        if self.ui == None: 
            return

        self.ui.write(type, code, value)
        self.ui.syn()

    def sendEvent(self, event, printEvent = None):
        if isinstance(event, KeyEvent):
            return self.writeUi(event.event.type, event.event.code, event.event.value, event)

        self.writeUi(event.type, event.code, event.value, event)

    def sendKey(self, key, value):
        _up = "up"
        _down = "down"
        self.writeUi(EV_KEY, key, value, f"Key: {evdev.ecodes.keys[key]} {_down if value else _up}")

    async def handlePressDelay(self, event):
        await asyncio.sleep(DeviceManager.delay)

        # Hooray, we haven't been cancelled yet! Time to end the chord I guess
        self.taskEndChord = None # hide the evidence :p

        chord = self.currentChord
        sortedChord = sorted(chord, key = lambda e: e.keycode)
        mapped = mapChord(chord)

        if mapped == None: # No remapping found :(
            for event in chord:
                self.sendEvent(event) # Send the original events through
        else: # Mapping found!
            for key in mapped: # Press all the remapped keys
                self.sendKey(key, 1)

            # Remember the chord for the keyup events
            combo = dict(keys = [], mappedTo = mapped)

            self.pressedCombos.append(combo)

            for event in self.currentChord:
                combo["keys"].append(dict(isPressed = True, event = event))

        self.currentChord.clear()

    def handleEvent(self, event):
        if event.type != EV_KEY:
            return

        if event.code in blacklisted:
            return

        categorized = evdev.categorize(event)
        # print(self.device.path, categorized, sep=': ')

        if logEvents:
            print("INPUT", categorized, sep = ": ")

        if categorized.keystate == KeyEvent.key_down:
            if self.taskEndChord != None:
                self.taskEndChord.cancel()

            self.currentChord.append(categorized)
            self.taskEndChord = asyncio.create_task(self.handlePressDelay(categorized))
        elif categorized.keystate == KeyEvent.key_up:
            for combo in self.pressedCombos:
                keyData = None
                keys = combo["keys"]
                for key in keys:
                    if key["event"].event.code == event.code and key["isPressed"]:
                        keyData = key
                        break

                if keyData != None:
                    keyData["isPressed"] = False
                    if not any([key["isPressed"] for key in keys]):
                        self.pressedCombos.remove(combo)
                        for key in combo["mappedTo"]:
                            self.sendKey(key, 0)
                    break
            else:
                if self.taskEndChord != None:
                    keyDownEvent = None

                    for key in self.currentChord:
                        if key.event.code == event.code:
                            keyDownEvent = key

                    if keyDownEvent != None:
                        for key in [x for x in self.currentChord]:
                            self.sendEvent(key)
                            self.currentChord.remove(key)
                            if key == keyDownEvent:
                                break

                self.sendEvent(categorized)
        elif categorized.keystate == KeyEvent.key_hold:
            print("Holding has not yet been implemented!")

    async def startLoop(self):
        async for event in device.async_read_loop():
            try: 
                self.handleEvent(event)
            except (Exception, KeyboardInterrupt) as e:
                print("An error occured: ", e)
                # Handle errors :D
                if self.loop != None:
                    loop.stop()

                return
managers = []
ui = evdev.UInput(name = "My python uinput!")

for device in devices:
    manager = DeviceManager(device, ui = ui)
    managers.append(manager)
    asyncio.ensure_future(manager.startLoop())

def custom_exception_handler(loop, context):
    # first, handle with default handler
    loop.default_exception_handler(context)

    exception = context.get('exception')

    print(context)
    loop.stop()

loop = asyncio.get_event_loop()

for manager in managers:
    manager.loop = loop

loop.set_exception_handler(custom_exception_handler)
loop.run_forever()
