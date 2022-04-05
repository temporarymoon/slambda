import evdev, asyncio
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
deviceCodes = [] 
devicePaths = ["/by-path/platform-i8042-serio-0-event-kbd"] + [f"event{code}" for code in deviceCodes] # laptop only
devices = [evdev.InputDevice(f"/dev/input/{path}") for path in devicePaths]

keyState = {}

previous = None

chordMax = 1/100 # ms
currentChord = []

ui = evdev.UInput(name="My-own-sink")

for device in devices:
    device.grab()

async def print_events(device):
    global currentChord
    async for event in device.async_read_loop():
        try:
            categorized = evdev.categorize(event)
            foundChord = False
            if event.type == 4:
                ui.write(event.type, event.code, event.value)
            elif event.type == EV_KEY:
                if categorized.keystate == KeyEvent.key_down:
                    if len(currentChord) == 0:
                        currentChord.append(event)
                    elif (event.timestamp() - currentChord[-1].timestamp()) <= chordMax:
                        currentChord.append(event)
                    else:
                        currentChord.clear()
                        currentChord.append(event)
                    keyState[categorized.keycode] = True
                elif categorized.keystate == KeyEvent.key_up:
                    if len(currentChord) > 1 and categorized.keycode == evdev.categorize(currentChord[-1]).keycode:
                        print("Chord detected: ", [evdev.categorize(event).keycode for event in currentChord])
                        currentChord = sorted(currentChord, key = lambda e: evdev.categorize(e).keycode)
                        if len(currentChord) == 2 and currentChord[0].code == KEY_A and currentChord[1].code == KEY_J:
                            print("Sending chord!")
                            ui.write(EV_KEY, KEY_P, 1)
                            ui.syn()
                            ui.write(EV_KEY, KEY_P, 0)
                            ui.syn()
                        currentChord.clear()
                        foundChord = True
                    keyState[categorized.keycode] = False
                ui.write(event.type, event.code, event.value)
            elif event.type == EV_SYN and not (previous.type == EV_KEY and evdev.categorize(previous).keystate == KeyEvent.key_hold):
                if not foundChord:
                    print(f"Pressed keys: {[code for (code, pressed) in keyState.items() if pressed]}")
                else:
                    print("\n")
                ui.syn()

            previous = event
            # else:
            #     print(device.path, categorized, sep=': ')
        except:
            exit()


for device in devices:
    asyncio.ensure_future(print_events(device))

loop = asyncio.get_event_loop()
loop.run_forever()
