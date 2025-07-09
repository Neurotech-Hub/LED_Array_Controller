# SEEEDuino LED Array Controller GUI

A Python GUI application for controlling SEEEDuino XIAO (SAMD21) boards in a daisy-chained round-robin communication system.

## Features

- **Serial Port Management**: Automatic port scanning, connection, and disconnection
- **Servo Control**: Set servo angles from 0-180 degrees with preset buttons and slider
- **DAC Control**: Control DAC output via percentage (0-100%) with automatic conversion to 10-bit values
- **Device Targeting**: Command all devices (000) or target specific devices individually
- **Real-time Status**: Monitor connection status, device count, and system state
- **Command Logging**: Track all sent and received commands with timestamps
- **Extensible Design**: Ready for future GPIO control additions

## Hardware Requirements

- SEEEDuino XIAO (SAMD21) controllers in daisy-chain configuration
- USB connection to master device
- Servo motors connected to PWM pins
- DAC outputs for LED array control

## Installation

1. **Install Python 3.7 or higher**
2. **Install required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the GUI**:
   ```bash
   python led_array_controller_gui.py
   ```

## Usage

### Connection Setup

1. **Connect your SEEEDuino master device** via USB
2. **Select the correct COM port** from the dropdown
3. **Choose baud rate** (default: 115200)
4. **Click "Connect"** to establish communication
5. **Wait for device initialization** - the system will auto-detect connected devices

### Device Control

#### Servo Control
- **Target Device**: Select specific device (001, 002, etc.) or all devices (000)
- **Angle Control**: Use slider, spinbox, or preset buttons (0°, 45°, 90°, 135°, 180°)
- **Send Command**: Click "Send Servo Command" to execute

#### DAC Control
- **Target Device**: Select specific device or all devices
- **Percentage Control**: Set output from 0-100% using slider, spinbox, or preset buttons
- **Raw Value Display**: Shows the converted 10-bit DAC value (0-1023)
- **Send Command**: Click "Send DAC Command" to execute

### System Commands

- **Device Status**: Query current system status and device count
- **Re-initialize**: Manually restart the device chain initialization
- **Help**: Display Arduino's built-in help information

### Command Format

The GUI automatically formats commands in the Arduino-expected format:
```
deviceId,command,value
```

Examples:
- `002,servo,90` - Set device 2 servo to 90 degrees
- `000,dac,512` - Set all devices DAC to 50% (512/1023)
- `001,servo,45` - Set device 1 servo to 45 degrees

## GUI Sections

### 1. Serial Connection
- Port selection and refresh
- Baud rate configuration
- Connect/disconnect controls

### 2. System Status
- Connection status indicator
- Total device count
- Current system state
- Manual command buttons

### 3. Control Panels
- **Servo Control**: Angle adjustment and targeting
- **DAC Control**: Percentage-based output control
- **GPIO Control**: Reserved for future expansion

### 4. Communication Log
- Real-time command and response logging
- Timestamps for all communications
- Clear log functionality

## Device Communication

The system uses a round-robin communication protocol:

1. **Master Device**: Connected via USB, manages the communication chain
2. **Slave Devices**: Daisy-chained via Serial1, forward commands in sequence
3. **Device IDs**: Automatically assigned during initialization (001, 002, 003...)
4. **Broadcasting**: Use device ID 000 to command all devices simultaneously

## Troubleshooting

### Connection Issues
- Ensure the correct COM port is selected
- Check that the SEEEDuino is properly connected via USB
- Try refreshing the port list
- Verify the baud rate matches the Arduino code (115200)

### Device Detection
- Wait for initialization to complete (may take 5-10 seconds)
- Use "Re-initialize" if devices are not detected
- Check Serial1 connections between devices in the daisy chain

### Command Issues
- Verify device IDs are within the detected range
- Check the communication log for error messages
- Ensure servo angles are 0-180 degrees
- Ensure DAC percentages are 0-100%

## Future Enhancements

The GPIO Control section is prepared for future expansion to include:
- Digital pin control (D4, D5, D8, D9, D10)
- Analog input reading
- Custom command sequences
- Device-specific configurations

## Arduino Compatibility

This GUI is designed to work with the SEEEDuino LED Array Controller Arduino code:
- Supports round-robin communication protocol
- Compatible with servo and DAC commands
- Handles device initialization and status queries
- Processes broadcast and targeted commands

## License

This project is part of the LED Array Controller system. Please refer to the main project documentation for licensing information. 