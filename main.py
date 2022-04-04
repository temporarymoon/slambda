import evdev, asyncio

# List all devices
print("Devices:")
allDevices = [evdev.InputDevice(path) for path in evdev.list_devices()]

for device in allDevices:
    print(device.path, device.name, device.phys)

# devices = []
# for device in allDevices:
#     devices.append(evdev.InputDevice(device.path))

print("\nEvents:")
deviceCodes = [10, 20]
devices = [evdev.InputDevice(f"/dev/input/event{code}") for code in deviceCodes]

async def print_events(device):
    async for event in device.async_read_loop():
        print(device.path, evdev.categorize(event), sep=': ')

for device in devices:
    asyncio.ensure_future(print_events(device))

loop = asyncio.get_event_loop()
loop.run_forever()
