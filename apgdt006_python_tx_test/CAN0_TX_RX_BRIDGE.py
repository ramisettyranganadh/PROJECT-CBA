import mba
import time

def flags_to_text(flags: int) -> str:
    return "XTD" if flags & mba.CANFRAME_FLAG_EXTENDED else "-"

def _device_callback(data):
    # Handle RX from CAN0
    if data.command == mba.CAN_MSG_RX:
        data_str = " ".join(f"{b:02X}" for b in data.msg.data[:data.msg.dlc])
        print(
            f"RX | BusID: 0x{data.msg.busId:X}"
            f" | Flags: {flags_to_text(data.msg.flags)}"
            f" | ID=0x{data.msg.id:X}"
            f" | Length: {data.msg.dlc}"
            f" | Data: {data_str}"
        )
        # Forward received CAN0 frame back to USB (host prints it)
    elif data.command == mba.CAN_MSG_TX:
        print("TX complete")

# --- Device setup ---
num_devices, types, serial_nums = mba.enum_devices()
if num_devices <= 0:
    raise Exception("No devices detected")

device = mba.Mba()
instance = device.open_device(serial_nums[0])
if instance < 0:
    raise Exception("Failed to open device")

device.register_callback(_device_callback, None)

# Configure CAN0 at 250 kbps, Classic CAN
device.can_set_speed(mba.CAN0, 250, 250)
device.can_set_mode(mba.CAN0, mba.CAN_MODE_CLASSIC, mba.CAN_TESTMODE_NORMAL, False)

print("Bridge active: type CAN messages to send (Ctrl+C to quit).")
print("Format: <ID> <byte1 byte2 ...> (hex values, space separated)")
print("Example: 1FEED004 CA FE BA BE BA AD F0 0D")

try:
    while True:
        user_input = input("Enter CAN frame: ").strip()
        if not user_input:
            continue

        parts = user_input.split()
        try:
            can_id = int(parts[0], 16)  # first token is ID in hex
            payload = [int(b, 16) for b in parts[1:]]
            dlc = len(payload)
            
            rc = device.can_send_frame(
                mba.CAN0,
                can_id,
                payload,
                dlc,
                mba.CANFRAME_FLAG_EXTENDED,  # Extended ID
                1000
            )
            
            if rc == 0:
                hex_payload = " ".join(f"{b:02X}" for b in payload)
                print(f"TX initiated: ID=0x{can_id:X} Data={hex_payload}")
        except Exception as e:
            print(f"Invalid input: {e}")

except KeyboardInterrupt:
    print("Stopping bridge...")

device.close_device()
