# SEEEDuino LED Array Controller GUI

A Python GUI application for controlling SEEEDuino XIAO (SAMD21) boards in a daisy-chained round-robin communication system. This application provides precise control over servo motors and LED arrays through an intuitive graphical interface.

![LED Array Controller GUI Screenshot](docs/LED%20Array%20Controller%20GUI%20v1.0.png)

## Overview

The LED Array Controller GUI enables seamless control of multiple SEEEDuino XIAO boards arranged in a daisy chain. Each board can control a servo motor (60-120 degrees, safety limited) and an LED array via DAC output (0-2100mA current control). The system uses a round-robin communication protocol where commands are passed from one device to the next, allowing for both synchronized and individual device control.

## 🚀 What This System Does

This GUI controls a smart chain of SEEEDuino XIAO controllers that can:
- Control LED brightness on multiple devices simultaneously or individually
- Move servo motors to precise positions (60-120 degrees)  
- Communicate through a daisy-chain setup (like Christmas lights, but smarter!)
- Automatically detect how many devices are connected
- Provide visual feedback when something goes wrong
- Run entertaining demo patterns for testing and demonstration

Think of it as a "conductor" for an orchestra of LED arrays and servo motors!

## Features

- **Serial Port Management**: Automatic port scanning, connection, and auto-connect to first available port
- **Servo Control**: Set servo angles from 60-120 degrees with preset buttons, slider, and dual control modes
- **Current-Based DAC Control**: Control DAC output via current (0-2100mA) with automatic conversion to 10-bit values (0-1023)
- **Device Targeting**: Command all devices (000) or target specific devices individually with smart mode switching
- **Real-time Status**: Monitor connection status, device count, and system state with color-coded indicators
- **Demo Patterns**: Three built-in demo patterns with synchronized execution and stop functionality
- **Command Logging**: Track all sent and received commands with timestamps and filtered display
- **Error Recovery**: Automatic timeout handling and device reinitialization commands
- **Comprehensive Help**: Built-in help system with complete hardware and software documentation

## Hardware Requirements

- SEEEDuino XIAO (SAMD21) controllers in daisy-chain configuration
- USB connection to master device (device 001)
- 12V external power for slave devices (002, 003, etc.)
- Servo motors connected to PWM pin D2 (optional)
- LED arrays connected to DAC output A0 with current amplification
- Proper daisy-chain wiring for round-robin communication

## Pin Connections

| Pin | Function | Connection |
|-----|----------|------------|
| A0  | DAC Output | → LED Array Control (amplified, 0-2100mA) |
| D2  | PWM Output | → Servo Motor (5V logic level, 60-120°) |
| D1  | RX_READY | ← Signal from previous device |
| D3  | TX_READY | → Signal to next device |
| D6  | TX | → Data to next device |
| D7  | RX | ← Data from previous device |
| D10 | User LED | Built-in status indicator |

## Chain Configuration

```
[Master Device] → [Device 2] → [Device 3] → [Device 4] → ... → [Back to Master]
    (USB)           (12V)        (12V)        (12V)
```

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

1. **Power Sequence**:
   - Connect 12V power to all slave devices first
   - Then connect master device via USB to computer
2. **Software Connection**:
   - Launch GUI (automatically connects to first available port)
   - Or manually select COM port and click "Connect"
   - Set baud rate to 115200 (matches Arduino default)
3. **Initialization**:
   - Wait 5-10 seconds for device auto-detection
   - Check "Total Devices" shows correct count
   - System state should show "Ready"

### Device Control

#### Servo Control (60-120 degrees, safety limited)
- **All Servos Mode**: Synchronize all devices simultaneously (Disk Mode)
- **Individual Mode**: Target specific device (001, 002, 003...)
- **Controls**: Slider, spinbox, or preset buttons (60°, 75°, 90°, 105°, 120°)
- **Real-time**: Live angle adjustment with immediate feedback

#### DAC/LED Control (0-2100mA current-based)
- **All LEDs Mode**: Broadcast to entire chain
- **Individual Mode**: Target specific device
- **Current Control**: Set output from 0-2100mA using slider, spinbox, or presets
- **Raw Value Display**: Shows converted 10-bit DAC value (0-1023)
- **Presets**: 0mA, 525mA, 1050mA, 1575mA, 2100mA

### Demo Patterns

The GUI includes three entertaining demo patterns perfect for testing and demonstration:

1. **🕺 Simple Dance**: Servo sweep (60°→120°→90°) + DAC flash (1050mA→0mA), runs 2 cycles
2. **🌊 Servo Wave**: Smooth servo oscillation with gradual movements, runs 2 cycles  
3. **🌈 DAC Rainbow**: Progressive brightness fade (0→2100mA→0), runs 2 cycles

All demos:
- Run automatically for 2 complete cycles
- Can be interrupted with "Stop Demo" button
- Sync status with current system state
- Perfect for validating complete setup

### System Commands

- **Device Status**: Query current system status, device count, and chain health
- **Re-initialize**: Manually restart device chain detection and ID assignment
- **Help**: Display comprehensive built-in help documentation

### Command Format

The GUI automatically formats commands in the Arduino-expected format:
```
deviceId,command,value
```

Examples:
- `002,servo,90` - Set device 2 servo to 90 degrees
- `000,dac,512` - Set all devices DAC to 1050mA (50% of 2100mA)
- `001,servo,120` - Set device 1 servo to 120 degrees
- `003,dac,0` - Turn off device 3 LEDs

## GUI Sections

### 1. Serial Connection
- Port selection with auto-refresh capability
- Baud rate configuration (default: 115200)
- Auto-connect feature for convenience
- Connect/disconnect controls with status indication

### 2. System Status
- Connection status indicator (Green/Red)
- Auto-detected total device count
- Current system state (Ready, Initializing, Processing, etc.)
- Manual command buttons (Status, Re-initialize, Help)

### 3. Demo Patterns
- Three creative demo patterns with descriptions
- Synchronized execution across all devices
- Stop functionality for immediate interruption
- Status synchronization with system state

### 4. Control Panels
- **Servo Control**: Angle adjustment with dual targeting modes
- **DAC Control**: Current-based output control (0-2100mA)
- **Real-time feedback**: Live updates and confirmation messages

### 5. Communication Log
- Real-time command and response logging with timestamps
- Filtered display (hides protocol messages, shows user-relevant info)
- Export functionality for troubleshooting
- Clear log functionality for fresh starts

## Device Communication

The system uses a sophisticated round-robin communication protocol:

1. **Master Device (001)**: Connected via USB, manages the communication chain
2. **Slave Devices (002, 003, etc.)**: Daisy-chained via Serial pins, forward commands in sequence
3. **Device IDs**: Automatically assigned during initialization process
4. **Broadcasting**: Use device ID 000 to command all devices simultaneously
5. **Auto-Discovery**: Automatic detection of chain length and device assignment
6. **Error Recovery**: Built-in timeout handling and recovery mechanisms

## Troubleshooting

### Visual Indicators on Hardware

- **Blue LED Steady**: Normal operation
- **Blue LED Stuck On**: Device error - press reset button on PCB
- **Orange LED Blinking**: Normal state indication  
- **User LED Active**: When DAC output > 0

### Common Issues

1. **Device Detection Problems**
   - **Symptom**: "Total Devices" shows 0 or wrong count
   - **Solution**: Click "Re-initialize" to restart detection
   - **Check**: Verify all devices are powered before USB connection
   - **Verify**: Physical daisy-chain connections are correct

2. **Command Not Working**
   - **Check**: Device count matches your physical hardware
   - **Verify**: Servo angles are within 60-120° (safety limited)
   - **Verify**: DAC current is within 0-2100mA range
   - **Monitor**: Communication log for error messages
   - **Test**: Use "Device Status" to check system health

3. **Chain Communication Failure**
   - **Symptom**: Commands timeout or devices don't respond
   - **Solution**: Press reset button on any stuck device (blue LED on)
   - **Check**: All 12V power connections and daisy-chain wiring
   - **Try**: Disconnect/reconnect USB and restart GUI

4. **Wrong Device Count**
   - **Symptom**: GUI shows incorrect number of devices
   - **Solution**: Click "Re-initialize" in System Status section
   - **Check**: Power all devices before connecting USB
   - **Verify**: No broken connections in the communication chain

### Best Practices

- **Startup Sequence**: Power slave devices first, then connect master USB
- **Command Execution**: Always wait for "✓ Command completed successfully"
- **Synchronized Control**: Use "All" modes for coordinated movements
- **Individual Control**: Use "Individual" modes for precise positioning
- **Monitoring**: Watch communication log for system feedback
- **Troubleshooting**: Export logs before reporting issues
- **Hardware**: Check physical connections first for any issues

## Technical Specifications

- **Microcontroller**: SAMD21 (SEEEDuino XIAO)
- **Communication**: 115200 baud, round-robin protocol with auto-discovery
- **Servo Range**: 60-120 degrees (safety limited from full 0-180° range)
- **DAC Range**: 0-2100mA (mapped to 0-1023 raw 10-bit values)
- **Max Chain Length**: Limited by power supply and timing constraints
- **Auto-Discovery**: Automatic device detection and ID assignment
- **Error Recovery**: Timeout handling and automatic state recovery
- **Demo Patterns**: Three built-in patterns with 2-cycle execution

## Arduino Firmware

The companion Arduino firmware (LED_Array_SAMD21_Controller) provides:
- Round-robin communication protocol
- Automatic device discovery and ID assignment
- Servo control with safety limits
- DAC output with current conversion
- Error handling and recovery
- Built-in help and status reporting
- Visual feedback via onboard LEDs

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Version History

- **v1.0**: Initial release with percentage-based DAC control
- **v1.1**: Added current-based DAC control (0-2100mA)
- **v1.2**: Added demo patterns and enhanced error handling
- **v1.3**: Improved GUI help system and documentation
- **Current**: Enhanced troubleshooting and user experience features