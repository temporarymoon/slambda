import evdev # for listening to keyboard events
import asyncio # async stuff
import sys # for getting commnad line arguments
import json # for json parsing

from evdev.events import KeyEvent
from evdev.ecodes import EV_KEY

config = sys.argv[1]

f = open(config, "r")
fileContents = f.read()
config = json.loads(fileContents)

# When true, we log everything to the console
logEvents = config["debug"] and "logs" in config["debug"]


def log(*args):
    if logEvents:
        print(*args)


device = evdev.InputDevice(config["device"])

ec = evdev.ecodes
blacklisted = []


def keyCode(name):
    return evdev.ecodes.ecodes[f"KEY_{name.upper()}"]


for combo in config["chords"]:
    combo["from"] = [keyCode(key) for key in combo["from"]]
    combo["to"] = [keyCode(key) for key in combo["to"]]


def mapChord(chord):
    codes = [keyEvent.event.code for keyEvent in chord]

    for remap in config["chords"]:
        if not all(code in codes for code in remap["from"]):
            continue

        if len(codes) == len(remap["from"]): # or not remap["exact"]:
            remapped = [key for key in remap["to"]]
            # TODO: add option for enabling fallthrough!
            # (this will always be empty at the moment)
            fallthrough = [code for code in codes if code not in remap["from"]]
            return remapped + fallthrough

    log("No mapping found")

    return None # default to the unsorted chord


def msToSeconds(ms):
    return ms / 1000


class DeviceManager:
    delay = msToSeconds(config["delay"]) # in seconds

    def __init__(self, device, ui=None):
        self.device = device
        self.taskEndChord = None
        self.currentChord = []
        self.pressedCombos = []
        self.ui = ui

        if ui is not None:
            self.device.grab()

    def writeUi(self, type, code, value, fallback=None):
        log(
            "OUTPUT: ",
            fallback if fallback is not None
            else f"Type: {type}, Code: {code}, value: {value}",
        )

        if self.ui is None:
            return

        self.ui.write(type, code, value)
        self.ui.syn()

    def sendEvent(self, event, printEvent=None):
        if isinstance(event, KeyEvent):
            return self.writeUi(
                event.event.type,
                event.event.code,
                event.event.value,
                event
            )

        self.writeUi(event.type, event.code, event.value, event)

    def sendKey(self, key, value):
        direction = "down" if value else "up"

        self.writeUi(
            EV_KEY,
            key,
            value,
            f"Key: {evdev.ecodes.keys[key]} {direction}"
        )

    async def handlePressDelay(self, event):
        await asyncio.sleep(DeviceManager.delay)

        # Hooray, we haven't been cancelled yet! Time to end the chord I guess
        self.taskEndChord = None # hide the evidence :p

        chord = self.currentChord
        mapped = mapChord(chord)

        if mapped is None: # No remapping found :(
            for event in chord:
                self.sendEvent(event) # Send the original events through
        else: # Mapping found!
            for key in mapped: # Press all the remapped keys
                self.sendKey(key, 1)

            # Remember the chord for the keyup events
            combo = dict(keys=[], mappedTo=mapped)

            self.pressedCombos.append(combo)

            for event in self.currentChord:
                combo["keys"].append(dict(isPressed=True, event=event))

        self.currentChord.clear()

    def handleEvent(self, event):
        if event.type is not EV_KEY:
            return

        if event.code in blacklisted:
            return

        categorized = evdev.categorize(event)

        log("INPUT: ", categorized)

        if categorized.keystate == KeyEvent.key_down:
            if self.taskEndChord is not None:
                self.taskEndChord.cancel()

            self.currentChord.append(categorized)
            self.taskEndChord = asyncio.create_task(
                self.handlePressDelay(categorized)
            )
        elif categorized.keystate == KeyEvent.key_up:
            for combo in self.pressedCombos:
                keyData = None
                keys = combo["keys"]
                for key in keys:
                    if key["event"].event.code == event.code and \
                       key["isPressed"]:
                        keyData = key
                        break

                if keyData is not None:
                    keyData["isPressed"] = False
                    if not any([key["isPressed"] for key in keys]):
                        self.pressedCombos.remove(combo)
                        for key in combo["mappedTo"]:
                            self.sendKey(key, 0)
                    break
            else:
                if self.taskEndChord is not None:
                    keyDownEvent = None
                    for key in self.currentChord:
                        if key.event.code == event.code:
                            keyDownEvent = key

                    if keyDownEvent is not None:
                        for key in [x for x in self.currentChord]:
                            self.sendEvent(key)
                            self.currentChord.remove(key)
                            if key == keyDownEvent:
                                break

                self.sendEvent(categorized)
        elif categorized.keystate == KeyEvent.key_hold:
            log("Holding has not yet been implemented!")

    async def startLoop(self):
        async for event in device.async_read_loop():
            try:
                self.handleEvent(event)
            except (Exception, KeyboardInterrupt) as e:
                print("An error occured: ", e)

                return


ui = evdev.UInput(name="My python uinput!")

manager = DeviceManager(device, ui=ui)
asyncio.ensure_future(manager.startLoop())

loop = asyncio.get_event_loop()
loop.run_forever()
