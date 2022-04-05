import evdev, asyncio
from enum import Enum, IntEnum
from evdev.events import InputEvent, KeyEvent, SynEvent
from evdev.ecodes import keys, KEY, SYN, REL, ABS, EV_KEY, EV_REL, EV_ABS, EV_SYN, KEY_A, KEY_J, KEY_P

# List all devices
print("Devices:")
allDevices = [evdev.InputDevice(path) for path in evdev.list_devices()]

for device in allDevices:
    print(device.path, device.name, device.phys)

# devices = []
# for device in allDevices:
#     devices.append(evdev.InputDevice(device.path))

print("\nEvents:")
# deviceCodes = [10, 20] # both keyboards
deviceCodes = [7] 
devicePaths = ["/by-path/platform-i8042-serio-0-event-kbd"] + [f"event{code}" for code in deviceCodes] # laptop only
devices = [evdev.InputDevice(f"/dev/input/{path}") for path in devicePaths]

# keyState = {}
# 
# previous = None
# 
# chordMax = 1/100 # ms
# currentChord = []
# 
# 
# for device in devices:
#     device.grab()

ec = evdev.ecodes
blacklisted = [ec.KEY_LEFTSHIFT]
basicRemaps = [
    dict(from_ = [ec.KEY_D, ec.KEY_S], to = [ec.KEY_LEFTSHIFT]),
    dict(from_ = [ec.KEY_L, ec.KEY_K], to = [ec.KEY_RIGHTSHIFT])
]

def mapChord(chord):
    if len(chord) <= 1:
        return

    print(*[event.keycode for event in chord])

    codes = [keyEvent.event.code for keyEvent in chord]

    for remap in basicRemaps:
        if not all(code in codes for code in remap["from_"]):
            continue
        return remap["to"] + [code for code in codes if code not in remap["from_"]]

    print("No mapping found")

    return None # default to the unsorted chord

class DeviceManager:
    delay = 1/30 # in seconds

    def __init__(self, device, ui = None):
        self.device = device
        self.taskEndChord = None
        self.currentChord = []
        self.pressedCombos = []
        self.ui = ui

        if ui != None:
            self.device.grab()

    def writeUi(self, type, code, value, fallback = None):
        if self.ui == None: 
            return print(
                self.device.path, 
                fallback if fallback != None else f"Type: {type}, Code: {code}, value: {value}", 
                sep = ": "
            )

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
