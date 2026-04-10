import os
import time
import mba

# ---- DLL LOAD FIX (MANDATORY) ----
dll_dir = os.path.dirname(os.path.abspath(__file__))
os.add_dll_directory(dll_dir)

def flags_to_text(flags: int) -> str:
    return "XTD" if flags & mba.CANFRAME_FLAG_EXTENDED else "STD"

def _device_callback(data):
    if data.command == mba.CAN_MSG_RX:
        data_str = " ".join(f"{b:02X}" for b in data.msg.data[:data.msg.dlc])
        print(
            f"RX | BusID: 0x{data.msg.busId:X}"
            f" | Flags: {flags_to_text(data.msg.flags)}"
            f" | ID=0x{data.msg.id:X}"
            f" | Length: {data.msg.dlc}"
            f" | Data: {data_str}"
        )

    elif data.command == mba.CAN_MSG_TX:
        print(
            f"------------- TX DONE | BusID: 0x{data.msg.busId:X}"
            f" | Flags: {flags_to_text(data.msg.flags)}"
            f" | ID=0x{data.msg.id:X}"
            f" | Length: {data.msg.dlc} -------------"
        )

# --- Device setup ---
num_devices, types, serial_nums = mba.enum_devices()
if num_devices <= 0:
    raise Exception("No devices detected")

device = mba.Mba()
instance = device.open_device(serial_nums[0])
if instance < 0:
    raise Exception("Failed to open device")

device.register_callback(_device_callback, None)

# Configure CAN0
device.can_set_speed(mba.CAN0, 250, 250)
device.can_set_mode(
    mba.CAN0,
    mba.CAN_MODE_CLASSIC,
    mba.CAN_TESTMODE_NORMAL,
    False
)

print("Bridge active: type CAN messages to send (Ctrl+C to quit).")
print("Format: <ID> <byte1 byte2 ...>  (hex)")
print("Example: 1FEED004 CA FE BA BE BA AD F0 0D")

try:
    while True:
        # Print prompt explicitly (never inside input)
        print("\nEnter CAN frame: ", end="", flush=True)
        user_input = input().strip()
        if not user_input:
            continue

        parts = user_input.split()
        can_id = int(parts[0], 16)
        payload = [int(b, 16) for b in parts[1:]]
        dlc = len(payload)

        rc = device.can_send_frame(
            mba.CAN0,
            can_id,
            payload,
            dlc,
            mba.CANFRAME_FLAG_EXTENDED,
            1000
        )

        if rc == 0:
            hex_payload = " ".join(f"{b:02X}" for b in payload)
            print("\n")
            print(
                f"TX | BusID: 0x{mba.CAN0:X}"
                f" | Flags: XTD"
                f" | ID=0x{can_id:X}"
                f" | Length: {dlc}"
                f" | Data: {hex_payload}"
            )

            # Allow async TX DONE / RX to complete before next prompt
            time.sleep(0.05)

        else:
            print(f"TX failed, rc={rc}")

except KeyboardInterrupt:
    print("\nStopping bridge...")

device.close_device()