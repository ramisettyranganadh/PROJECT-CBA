import mba
import time

def flags_to_text(flags: int) -> str:
    return "XTD" if flags & mba.CANFRAME_FLAG_EXTENDED else "-"

def _device_callback(data):
    # RX from CAN0 → forward to USB (print to host)
    if data.command == mba.CAN_MSG_RX:
        data_str = " ".join(f"{b:02X}" for b in data.msg.data[:data.msg.dlc])
        print(
            f"RX | BusID: {hex(data.msg.busId)}"
            f" | Flags: {flags_to_text(data.msg.flags)}"
            f" | ID: {hex(data.msg.id)}"
            f" | Length: {data.msg.dlc}"
            f" | Data: {data_str}"
        )
        # Example: forward CAN0 RX back to USB (host sees it)
        # In practice, "USB" here means the Python host prints/logs it.
        # If you want to echo back onto CAN0, you can re‑send:
        device.can_send_frame(
            mba.CAN0,
            data.msg.id,
            list(data.msg.data[:data.msg.dlc]),
            data.msg.dlc,
            data.msg.flags,
            1000
        )

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

# --- Initial transmit from Host to EV31E34A ---
tx_id      = 0x1FEED004
tx_dlc     = 8
tx_payload = [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]

rc = device.can_send_frame(
    mba.CAN0,
    tx_id,
    tx_payload,
    tx_dlc,
    mba.CANFRAME_FLAG_EXTENDED,  # Extended ID
    1000
)

if rc == 0:
    print(f"Transmission initiated: ID={hex(tx_id)}")

# --- Infinite loop waiting for messages ---
print("Bridge active: forwarding CAN0 <-> USB (Ctrl+C to stop)")
try:
    while True:
        time.sleep(0.1)  # keep process alive, callback handles RX/TX
except KeyboardInterrupt:
    print("Stopping bridge...")

device.close_device()
