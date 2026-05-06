import os
import time
import queue
import threading
import msvcrt
import mba

def clear_screen():
    os.system('cls')

# ---- DLL LOAD FIX ----
dll_dir = os.path.dirname(os.path.abspath(__file__))
os.add_dll_directory(dll_dir)

rx_queue = queue.Queue()
tx_queue = queue.Queue()

print_lock = threading.Lock()

MODE_RX = 0
MODE_TX = 1
current_mode = MODE_RX

RX_WARMUP_SEC = 0.5
rx_enabled = False
rx_start_time = 0.0

# ---- COLORS ----
COLOR_RESET = "\033[0m"
COLOR_TX_MODE = "\033[33m"
COLOR_RX_MODE = "\033[36m"
COLOR_TX_FRAME = "\033[93m"
COLOR_RX_FRAME = "\033[38;5;110m"
COLOR_WAIT  = "\033[92m"
COLOR_ERROR = "\033[91m"

# ---- Helper ----
def flags_to_text(flags):
    return "XTD" if flags & mba.CANFRAME_FLAG_EXTENDED else "STD"


# ---- RX CALLBACK (NO CHANNEL SUPPORT IN YOUR SDK) ----
def device_callback(data):
    if not rx_enabled:
        return

    if time.time() - rx_start_time < RX_WARMUP_SEC:
        return

    if data.command == mba.CAN_MSG_RX:
        rx_queue.put(data.msg)   # ✅ FIX: no channel


# ---- RX THREAD ----
def rx_thread(stop_event):
    global current_mode

    while not stop_event.is_set():
        try:
            msg = rx_queue.get(timeout=0.5)

            if current_mode == MODE_RX:
                payload = " ".join(f"{b:02X}" for b in msg.data[:msg.dlc])

                with print_lock:
                    ts = time.strftime("%H:%M:%S")
                    print(
                        f"\n{COLOR_RX_FRAME}[{ts}] RX | "
                        f"{flags_to_text(msg.flags)} "
                        f"| ID=0x{msg.id:X} "
                        f"| DLC={msg.dlc} "
                        f"| Data={payload}{COLOR_RESET}"
                    )

        except queue.Empty:
            pass


# ---- TX THREAD ----
def tx_thread(device, stop_event):
    while not stop_event.is_set():
        try:
            channel, can_id, payload = tx_queue.get(timeout=0.5)

            # ✅ Auto STD / EXT
            flag = mba.CANFRAME_FLAG_EXTENDED if can_id > 0x7FF else 0

            device.can_send_frame(
                channel,
                can_id,
                payload,
                len(payload),
                flag,
                1000
            )

            payload_str = " ".join(f"{b:02X}" for b in payload)

            with print_lock:
                ts = time.strftime("%H:%M:%S")
                print(
                    f"\n{COLOR_TX_FRAME}[{ts}] TX | CH={channel} | {flags_to_text(flag)} "
                    f"| ID=0x{can_id:X} | DLC={len(payload)} | Data={payload_str}{COLOR_RESET}"
                )
                print(f"\n{COLOR_RX_MODE}--- RX MODE ---{COLOR_RESET}")
                print(f"{COLOR_WAIT}RX>{COLOR_RESET}", flush=True)

        except queue.Empty:
            pass


# ---- KEYBOARD THREAD ----
def keyboard_thread(stop_event):
    global current_mode

    with print_lock:
        clear_screen()
        print("\nDual CAN Monitor (CAN0 + CAN1)")
        print("Press 'T' for TX | 'Q' to Quit\n")

    while not stop_event.is_set():
        if msvcrt.kbhit():
            key = msvcrt.getch().decode(errors="ignore").lower()

            if key == 't' and current_mode == MODE_RX:
                current_mode = MODE_TX

                with print_lock:
                    print(f"\n{COLOR_TX_MODE}--- TX MODE ---{COLOR_RESET}")
                    print("Format: <CH> <ID> <DATA>")
                    print("Example: 0 123 11 22 33 44")
                    print("Example: 1 1FEED004 CA FE BA BE BA AD F0 0D")
                    print(f"{COLOR_WAIT}TX>{COLOR_RESET} ", end="", flush=True)

                line = input().strip()

                if not line:
                    current_mode = MODE_RX
                    continue

                try:
                    parts = line.split()

                    channel = int(parts[0])
                    if channel not in [0, 1]:
                        raise ValueError("Channel must be 0 or 1")

                    can_id = int(parts[1], 16)
                    payload = [int(b, 16) for b in parts[2:]]

                    if len(payload) > 8:
                        raise ValueError("Max 8 bytes allowed")

                    tx_queue.put((channel, can_id, payload))

                except Exception as e:
                    with print_lock:
                        print(f"{COLOR_ERROR}Error: {e}{COLOR_RESET}")

                current_mode = MODE_RX

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

    # ---- CAN0 ----
    device.can_set_speed(mba.CAN0, 250, 250)
    device.can_set_mode(
        mba.CAN0,
        mba.CAN_MODE_CLASSIC,
        mba.CAN_TESTMODE_NORMAL,
        True
    )

    # ---- CAN1 ----
    device.can_set_speed(mba.CAN1, 250, 250)
    device.can_set_mode(
        mba.CAN1,
        mba.CAN_MODE_CLASSIC,
        mba.CAN_TESTMODE_NORMAL,
        True
    )

    stop_event = threading.Event()

    threads = [
        threading.Thread(target=rx_thread, args=(stop_event,), daemon=True),
        threading.Thread(target=tx_thread, args=(device, stop_event), daemon=True),
        threading.Thread(target=keyboard_thread, args=(stop_event,), daemon=True),
    ]

    for t in threads:
        t.start()

    global rx_enabled, rx_start_time
    rx_start_time = time.time()
    rx_enabled = True

    with print_lock:
        print(f"{COLOR_RX_MODE}--- RX MODE (CAN0 + CAN1) ---{COLOR_RESET}")
        print(f"{COLOR_WAIT}RX>{COLOR_RESET}")

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

    device.close_device()
    print("Stopped")


if __name__ == "__main__":
    main()
