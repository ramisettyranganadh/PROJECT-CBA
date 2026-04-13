################################################################################
# Subject to your compliance with these terms, you may use Microchip software
# and any derivatives exclusively with Microchip products. It is your
# responsibility to comply with third party license terms applicable to your
# use of third party software (including open source software) that may
# accompany Microchip software.
#
# THIS SOFTWARE IS SUPPLIED BY MICROCHIP "AS IS". NO WARRANTIES, WHETHER
# EXPRESS, IMPLIED OR STATUTORY, APPLY TO THIS SOFTWARE, INCLUDING ANY IMPLIED
# WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A
# PARTICULAR PURPOSE.
#
# IN NO EVENT WILL MICROCHIP BE LIABLE FOR ANY INDIRECT, SPECIAL, PUNITIVE,
# INCIDENTAL OR CONSEQUENTIAL LOSS, DAMAGE, COST OR EXPENSE OF ANY KIND
# WHATSOEVER RELATED TO THE SOFTWARE, HOWEVER CAUSED, EVEN IF MICROCHIP HAS
# BEEN ADVISED OF THE POSSIBILITY OR THE DAMAGES ARE FORESEEABLE. TO THE
# FULLEST EXTENT ALLOWED BY LAW, MICROCHIP'S TOTAL LIABILITY ON ALL CLAIMS IN
# ANY WAY RELATED TO THIS SOFTWARE WILL NOT EXCEED THE AMOUNT OF FEES, IF ANY,
# THAT YOU HAVE PAID DIRECTLY TO MICROCHIP FOR THIS SOFTWARE.
################################################################################
import logging
import mba
from time import sleep


def flags_to_text(flags: int) -> str:
    parts = []

    if flags & mba.CANFRAME_FLAG_EXTENDED:
        parts.append("XTD")
    if flags & mba.CANFRAME_FLAG_FD:
        parts.append("FD")
    if flags & mba.CANFRAME_FLAG_BRS:
        parts.append("BRS")

    ret_str = "|".join(parts) if parts else "-" 
    
    return ret_str

def _device_callback(data):
    if data.command in (
        mba.CAN_MSG_RX,
        mba.CAN_MSG_TX,
    ):
        msg_type = {
            mba.CAN_MSG_RX: "RX",
            mba.CAN_MSG_TX: "TX",
        }[data.command]

        line = f"Callback | Type: {msg_type}"

        if data.command in (mba.CAN_MSG_RX, mba.CAN_MSG_TX):
            data_str = " ".join(f"{b:02X}" for b in data.msg.data[:data.msg.dlc])
            line += (
                f" | BusID: {hex(data.msg.busId)}"
                f" | Flags: {flags_to_text(data.msg.flags)}"
                f" | ID: {hex(data.msg.id)}"
                f" | Length: {data.msg.dlc}"
                f" | Data: {data_str}"
            )
    else:
        if data.command in (
            mba.CAN_MSG_ERR,
            mba.CAN_MSG_DBG,
            mba.CAN_MSG_BITRATE,
            mba.CAN_MSG_MODE,
        ):
            msg_type = {
                mba.CAN_MSG_ERR: "ERR",
                mba.CAN_MSG_DBG: "DBG",
                mba.CAN_MSG_BITRATE: "BITRATE",
                mba.CAN_MSG_MODE: "MODE",
            }[data.command]

            line = f"Callback | Type: {msg_type}"
            line += f" | BusID: {hex(data.msg.busId)}"

    print(line)        
    return

#################################################
# Transmission Test
#################################################

num_devices, types, serial_nums = mba.enum_devices()
if 0 >= num_devices:
  raise Exception('No devices detected.')

print("Found %d device" % num_devices)
print("Trying to open %s" % serial_nums[0])

device = mba.Mba()
instance = device.open_device(serial_nums[0])
if 0 > instance:
  raise Exception('Failed open_device.')

rc = device.register_callback(_device_callback, None) # register callback function

print("This is a tool test")    #should ALWAYS print
            
#################################################
#  Setup CAN-FD interface
#################################################
device.can_set_speed(mba.CAN0, 500, 2000) # Bus 0, Nominal Bit Rate=500Kbps, Data Bit Rate=2000Kbps
device.can_set_speed(mba.CAN1, 500, 2000) # Bus 1, Nominal Bit Rate=500Kbps, Data Bit Rate=2000Kbps

# CAN MODE
#   Options:
#       mba.CAN_MODE_CLASSIC,   = CAN Classic
#       mba.CAN_MODE_FD,        = CAN-FD (Bosch-CRC)
#       mba.CAN_MODE_FD_ISO,    = CAN-FD (ISO-CRC)
can_mode  = mba.CAN_MODE_FD     # CAN-FD

# TEST MODE
#   Options:
#       mba.CAN_TESTMODE_INIT,          = Module init (enters after powercycle)
#       mba.CAN_TESTMODE_NORMAL,        = Testmode disabled
#       mba.CAN_TESTMODE_LISTENONLY,    = Listen only, do send ACKs or error frames
#       mba.CAN_TESTMODE_LOOPBACK,      = Local loopback mode
#       mba.CAN_TESTMODE_EXTLOOPBACK,   = Extern loopback mode enhances local loopback by enabling frame transmission to the bus. However RX is still disabled and it will not receive ACK or react on error frames.
test_mode = mba.CAN_TESTMODE_NORMAL   # NORMAL Mode; 

device.can_set_mode(mba.CAN0, can_mode, test_mode, False) # Bus 0, Mode=CAN-FD, NORMAL Mode, No Auto Retry
device.can_set_mode(mba.CAN1, can_mode, test_mode, False) # Bus 1, Mode=CAN-FD, NORMAL Mode, No Auto Retry

canfd_id      = 0x12345678
canfd_dlc     = 64
canfd_payload = list(range(canfd_dlc))     #[0, 1, 2, 3, ... dlc-1]

if(0 == device.can_send_frame(mba.CAN0, canfd_id, canfd_payload, canfd_dlc, mba.CANFRAME_FLAG_NONE | mba.CANFRAME_FLAG_EXTENDED | mba.CANFRAME_FLAG_FD | mba.CANFRAME_FLAG_BRS, 1000)):
    print("Transmission initiated.")
    # The frame is successfully transmitted if another CAN node, identically configured, is connected to the bus and acknowledge the message.

sleep(3) # wait 3 seconds

device.close_device()

