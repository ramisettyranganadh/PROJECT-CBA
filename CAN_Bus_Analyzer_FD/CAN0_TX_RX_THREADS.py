import os
import time
import queue
import threading
import msvcrt
import mba

# ---- DLL LOAD FIX ----
dll_dir = os.path.dirname(os.path.abspath(__file__))
os.add_dll_directory(dll_dir)

rx_queue = queue.Queue()
tx_queue = queue.Queue()

print_lock = threading.Lock()

MODE_RX = 0
MODE_TX = 1
current_mode = MODE_RX

# ---- Helpers ----
def flags_to_text(flags):
    return "XTD" if flags & mba.CANFRAME_FLAG_EXTENDED else "STD"

# ---- RX CALLBACK (FAST, NEVER BLOCKS) ----
def device_callback(data):
    if data.command == mba.CAN_MSG_RX:
        rx_queue.put(data.msg)

# ---- RX PRINT THREAD ----
def rx_thread(stop_event):
    global current_mode

    while not stop_event.is_set():
        try:
            msg = rx_queue.get(timeout=0.5)

            if current_mode == MODE_RX:
                payload = " ".join(
                    f"{b:02X}" for b in msg.data[:msg.dlc]
                )
                with print_lock:
                    print(
                        f"\nRX | {flags_to_text(msg.flags)} "
                        f"| ID=0x{msg.id:X} "
                        f"| DLC={msg.dlc} "
                        f"| Data={payload}"
                    )

        except queue.Empty:
            pass

# ---- TX WORKER THREAD ----
def tx_thread(device, stop_event):
    while not stop_event.is_set():
        try:
            can_id, payload = tx_queue.get(timeout=0.5)

            device.can_send_frame(
                mba.CAN0,
                can_id,
                payload,
                len(payload),
                mba.CANFRAME_FLAG_EXTENDED,
                1000
            )

            with print_lock:
                print(f"\nTX | ID=0x{can_id:X}")

        except queue.Empty:
            pass

# ---- KEY + MODE HANDLER ----
def keyboard_thread(stop_event):
    global current_mode

    with print_lock:
        print("\nPress 'T' to enter TX mode | 'Q' to quit")

    while not stop_event.is_set():
        if msvcrt.kbhit():
            key = msvcrt.getch().decode(errors="ignore").lower()

            # ---- ENTER TX MODE ----
            if key == 't' and current_mode == MODE_RX:
                current_mode = MODE_TX

                with print_lock:
                    print("\n--- TX MODE ---")
                    print("Enter frame: <ID> <bytes...>")
                    print("Example: 1FEED004 CA FE BA BE")
                    print("TX> ", end="", flush=True)

                line = input().strip()

                if line:
                    try:
                        parts = line.split()
                        can_id = int(parts[0], 16)
                        payload = [int(b, 16) for b in parts[1:]]
                        tx_queue.put((can_id, payload))
                    except ValueError:
                        with print_lock:
                            print("Invalid TX format")

                current_mode = MODE_RX
                with print_lock:
                    print("--- RX MODE ---")

            elif key == 'q':
                stop_event.set()

        time.sleep(0.05)

# ---- MAIN ----
def main():
    num_devices, _, serials = mba.enum_devices()
    if num_devices <= 0:
        raise RuntimeError("No devices found")

    device = mba.Mba()
    device.open_device(serials[0])
    device.register_callback(device_callback, None)

    device.can_set_speed(mba.CAN0, 250, 250)
    device.can_set_mode(
        mba.CAN0,
        mba.CAN_MODE_CLASSIC,
        mba.CAN_TESTMODE_NORMAL,
        False
    )

    stop_event = threading.Event()

    threads = [
        threading.Thread(target=rx_thread, args=(stop_event,), daemon=True),
        threading.Thread(target=tx_thread, args=(device, stop_event), daemon=True),
        threading.Thread(target=keyboard_thread, args=(stop_event,), daemon=True),
    ]

    for t in threads:
        t.start()

    print("CAN Monitor Running (RX mode)")

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

    device.close_device()
    print("Stopped")

if __name__ == "__main__":
    main()