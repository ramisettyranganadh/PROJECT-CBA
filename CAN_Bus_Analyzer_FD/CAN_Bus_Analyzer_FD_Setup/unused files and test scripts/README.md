I'm attaching a Python script for a minimal transmission test: apgdt006_python_tx_test.zip.



Steps 



1. Install Python and locate the installation folder.

On my PC this is the installation folder:

C:\Python311\

It is assumed that this path was added to system paths and the "python" application is recognized at Command Prompt in Windows.



2. Create a new folder, for example C:\can_test\ and unzip the archive  apgdt006_python_tx_test.zip there.

The folder should contain the following files:

mba-1.3.0-py3-none-any.whl

MbaInterface.dll

CAN_FD_pythonTxTest.py





3. Open Windows Command Prompt and install mba 1.3.0 library using the following command:

python -m pip install C:\can_test\mba-1.3.0-py3-none-any.whl



Check if the mba library was installed with command:

python -m pip list



4. Bug fix. 

Locate the "mba.py" file in Python installation folder.

On my PC the path is C:\Python311\Lib\site-packages\mba\mba.py





Open the "mba.py" file and replace line 491:



with this one:



5. Install CBA driver. 

Download the driver from https://ww1.microchip.com/downloads/aemDocuments/documents/APG/ProductDocuments/SoftwareTools/APGDT006-driver-Oct2023.zip

Connect the board to PC using USB cable.

Go to Device Manager (administrator privileges are required) and locate the MBAnalyzer.

Double click on it and update the driver with mba.inf/mba.cat from the previously downloaded zip.





After installing the driver, the CAN Analyzer tool should look in this way in Control Panel.







6. Connect CAN_HI and CAN_LO from CAN0 DB9 connector to the corresponding pins on CAN1 DB9 Connector.

DB9 pin 2= CAN_HI

DB9 pin 7= CAN_LO





7. Run the Python script CAN_FD_pythonTxTest.py with command:

python CAN_FD_pythonTxTest.py



The script transmits a message on CAN0 bus and this should be received on CAN1 bus. If the transmission is successful the output should look in the following way:





Please let me know if you have any problem when executing the above steps.