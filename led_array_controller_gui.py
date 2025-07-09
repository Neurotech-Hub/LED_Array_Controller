#!/usr/bin/env python3
"""
SEEEDuino LED Array Controller GUI

This GUI provides an interface for controlling SEEEDuino XIAO boards
in a daisy-chained round-robin communication system.

Features:
- Serial port scanning and connection management
- Servo angle control (0-180 degrees)
- DAC control via percentage (0-100%)
- Device targeting (all devices or specific device)
- Real-time status monitoring
- Command history and logging

Hardware Requirements:
- SEEEDuino XIAO (SAMD21) controllers in daisy-chain
- USB connection to master device
- Servo and DAC outputs per device

Author: Neurotech Hub
Version: 0.1
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import re
from datetime import datetime
import queue


class LEDArrayControllerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SEEEDuino LED Array Controller v1.0")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Serial connection variables
        self.serial_connection = None
        self.connected = False
        self.available_ports = []
        self.total_devices = 0
        self.device_status = "Disconnected"
        
        # Threading for serial communication
        self.stop_threads = False
        self.message_queue = queue.Queue()
        
        # Command history
        self.command_history = []
        
        # Create GUI elements
        self.create_widgets()
        self.update_port_list()
        
        # Start GUI update loop
        self.update_gui()
        
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # === Connection Section ===
        self.create_connection_section(main_frame, 0, 0)
        
        # === Device Status Section ===
        self.create_status_section(main_frame, 0, 1)
        
        # === Control Sections ===
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)
        
        self.create_servo_section(control_frame, 0, 0)
        self.create_dac_section(control_frame, 0, 1)
        
        # === Command Log Section ===
        self.create_log_section(main_frame, 2, 0)
        
    def create_connection_section(self, parent, row, col):
        """Create serial port connection controls"""
        connection_frame = ttk.LabelFrame(parent, text="Serial Connection", padding="10")
        connection_frame.grid(row=row, column=col, sticky=(tk.W, tk.E, tk.N), padx=(0, 5))
        
        # Port selection
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(connection_frame, textvariable=self.port_var, 
                                      width=20, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=(5, 5), pady=(0, 5))
        
        # Refresh ports button
        self.refresh_btn = ttk.Button(connection_frame, text="Refresh", 
                                     command=self.update_port_list)
        self.refresh_btn.grid(row=0, column=2, padx=(5, 0), pady=(0, 5))
        
        # Baud rate
        ttk.Label(connection_frame, text="Baud:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(connection_frame, textvariable=self.baud_var, 
                                 values=["9600", "115200", "230400"], width=10, state="readonly")
        baud_combo.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # Connect/Disconnect buttons
        button_frame = ttk.Frame(connection_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0))
        
        self.connect_btn = ttk.Button(button_frame, text="Connect", 
                                     command=self.connect_serial)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", 
                                        command=self.disconnect_serial, state="disabled")
        self.disconnect_btn.pack(side=tk.LEFT)
        
    def create_status_section(self, parent, row, col):
        """Create device status display"""
        status_frame = ttk.LabelFrame(parent, text="System Status", padding="10")
        status_frame.grid(row=row, column=col, sticky=(tk.W, tk.E, tk.N), padx=(5, 0))
        
        # Connection status
        ttk.Label(status_frame, text="Connection:").grid(row=0, column=0, sticky=tk.W)
        self.connection_status_var = tk.StringVar(value="Disconnected")
        self.connection_label = ttk.Label(status_frame, textvariable=self.connection_status_var, 
                                         foreground="red")
        self.connection_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        # Device count
        ttk.Label(status_frame, text="Total Devices:").grid(row=1, column=0, sticky=tk.W)
        self.device_count_var = tk.StringVar(value="0")
        ttk.Label(status_frame, textvariable=self.device_count_var).grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        
        # System state
        ttk.Label(status_frame, text="System State:").grid(row=2, column=0, sticky=tk.W)
        self.system_state_var = tk.StringVar(value="Unknown")
        ttk.Label(status_frame, textvariable=self.system_state_var).grid(row=2, column=1, sticky=tk.W, padx=(5, 0))
        
        # Manual device count override (for debugging)
        manual_count_frame = ttk.Frame(status_frame)
        manual_count_frame.grid(row=3, column=0, columnspan=2, pady=(5, 0), sticky="we")
        
        ttk.Label(manual_count_frame, text="Manual Count:").pack(side=tk.LEFT)
        self.manual_count_var = tk.StringVar(value="2")
        ttk.Spinbox(manual_count_frame, from_=1, to=10, width=5, 
                   textvariable=self.manual_count_var).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(manual_count_frame, text="Set", 
                  command=self.set_manual_device_count).pack(side=tk.LEFT)
        

        # Manual commands
        manual_frame = ttk.Frame(status_frame)
        manual_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(manual_frame, text="Device Status", 
                  command=lambda: self.send_command("status")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manual_frame, text="Re-initialize", 
                  command=lambda: self.send_command("reinit")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manual_frame, text="Help", 
                  command=self.show_help_window).pack(side=tk.LEFT)
        
    def create_servo_section(self, parent, row, col):
        """Create servo control section with dual modes"""
        servo_frame = ttk.LabelFrame(parent, text="Servo Control", padding="10")
        servo_frame.grid(row=row, column=col, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Control mode selection
        mode_frame = ttk.Frame(servo_frame)
        mode_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(mode_frame, text="Control Mode:").pack(side=tk.LEFT)
        self.servo_mode_var = tk.StringVar(value="all")
        
        ttk.Radiobutton(mode_frame, text="All Servos (Disk Mode)", 
                       variable=self.servo_mode_var, value="all",
                       command=self.update_servo_mode).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(mode_frame, text="Individual Servo", 
                       variable=self.servo_mode_var, value="individual",
                       command=self.update_servo_mode).pack(side=tk.LEFT, padx=(10, 0))
        
        # Device selection (for individual mode)
        device_frame = ttk.Frame(servo_frame)
        device_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.servo_device_label = ttk.Label(device_frame, text="Target:")
        self.servo_device_label.pack(side=tk.LEFT)
        self.servo_device_var = tk.StringVar(value="001")
        self.servo_device_combo = ttk.Combobox(device_frame, textvariable=self.servo_device_var, 
                                              values=["001"], width=8, state="readonly")
        self.servo_device_combo.pack(side=tk.LEFT, padx=(5, 5))
        
        self.servo_device_info = ttk.Label(device_frame, text="(001=Master, 002=Slave...)", 
                                          foreground="gray", font=("Arial", 8))
        self.servo_device_info.pack(side=tk.LEFT)
        
        # Initially disable device selection (all mode is default)
        self.servo_device_label.configure(state="disabled")
        self.servo_device_combo.configure(state="disabled")
        
        # Angle control
        ttk.Label(servo_frame, text="Angle (degrees):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.servo_angle_var = tk.IntVar(value=90)
        servo_angle_spin = ttk.Spinbox(servo_frame, from_=0, to=180, width=10, 
                                      textvariable=self.servo_angle_var)
        servo_angle_spin.grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # Angle slider  
        self.servo_scale = ttk.Scale(servo_frame, from_=0, to=180, orient=tk.HORIZONTAL,
                                    variable=self.servo_angle_var, length=250,
                                    command=self.update_servo_display)
        self.servo_scale.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 10))
        
        # Preset buttons
        preset_frame = ttk.Frame(servo_frame)
        preset_frame.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(preset_frame, text="0°", width=6,
                  command=lambda: self.set_servo_angle(0)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="45°", width=6,
                  command=lambda: self.set_servo_angle(45)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="90°", width=6,
                  command=lambda: self.set_servo_angle(90)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="135°", width=6,
                  command=lambda: self.set_servo_angle(135)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="180°", width=6,
                  command=lambda: self.set_servo_angle(180)).pack(side=tk.LEFT)
        
        # Send button with dynamic text
        self.servo_send_btn = ttk.Button(servo_frame, text="Send to All Servos", 
                                        command=self.send_servo_command)
        self.servo_send_btn.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
    def create_dac_section(self, parent, row, col):
        """Create DAC control section with dual modes"""
        dac_frame = ttk.LabelFrame(parent, text="DAC/LED Control", padding="10")
        dac_frame.grid(row=row, column=col, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Control mode selection
        mode_frame = ttk.Frame(dac_frame)
        mode_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(mode_frame, text="Control Mode:").pack(side=tk.LEFT)
        self.dac_mode_var = tk.StringVar(value="all")
        
        ttk.Radiobutton(mode_frame, text="All LEDs", 
                       variable=self.dac_mode_var, value="all",
                       command=self.update_dac_mode).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(mode_frame, text="Individual LED", 
                       variable=self.dac_mode_var, value="individual",
                       command=self.update_dac_mode).pack(side=tk.LEFT, padx=(10, 0))
        
        # Device selection (for individual mode)
        device_frame = ttk.Frame(dac_frame)
        device_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.dac_device_label = ttk.Label(device_frame, text="Target:")
        self.dac_device_label.pack(side=tk.LEFT)
        self.dac_device_var = tk.StringVar(value="001")
        self.dac_device_combo = ttk.Combobox(device_frame, textvariable=self.dac_device_var, 
                                            values=["001"], width=8, state="readonly")
        self.dac_device_combo.pack(side=tk.LEFT, padx=(5, 5))
        
        self.dac_device_info = ttk.Label(device_frame, text="(001=Master, 002=Slave...)", 
                                        foreground="gray", font=("Arial", 8))
        self.dac_device_info.pack(side=tk.LEFT)
        
        # Initially disable device selection (all mode is default)
        self.dac_device_label.configure(state="disabled")
        self.dac_device_combo.configure(state="disabled")
        
        # Percentage control
        ttk.Label(dac_frame, text="Output (%):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.dac_percent_var = tk.IntVar(value=0)
        dac_percent_spin = ttk.Spinbox(dac_frame, from_=0, to=100, width=10, 
                                      textvariable=self.dac_percent_var)
        dac_percent_spin.grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # Percentage slider
        self.dac_scale = ttk.Scale(dac_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                  variable=self.dac_percent_var, length=250,
                                  command=self.update_dac_display)
        self.dac_scale.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 10))
        
        # Raw value display
        ttk.Label(dac_frame, text="Raw Value:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.dac_raw_var = tk.StringVar(value="0")
        ttk.Label(dac_frame, textvariable=self.dac_raw_var).grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # Update raw value when percentage changes
        self.dac_percent_var.trace('w', self.update_dac_raw_value)
        
        # Preset buttons
        preset_frame = ttk.Frame(dac_frame)
        preset_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(preset_frame, text="0%", width=6,
                  command=lambda: self.set_dac_percent(0)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="25%", width=6,
                  command=lambda: self.set_dac_percent(25)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="50%", width=6,
                  command=lambda: self.set_dac_percent(50)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="75%", width=6,
                  command=lambda: self.set_dac_percent(75)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="100%", width=6,
                  command=lambda: self.set_dac_percent(100)).pack(side=tk.LEFT)
        
        # Send button with dynamic text
        self.dac_send_btn = ttk.Button(dac_frame, text="Send to All LEDs", 
                                      command=self.send_dac_command)
        self.dac_send_btn.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        
    def create_log_section(self, parent, row, col):
        """Create command log and output section"""
        log_frame = ttk.LabelFrame(parent, text="Communication Log", padding="10")
        log_frame.grid(row=row, column=col, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Text area with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log control buttons
        button_frame = ttk.Frame(log_frame)
        button_frame.grid(row=1, column=0, pady=(5, 0))
        
        ttk.Button(button_frame, text="Clear Log", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Export Log", 
                  command=self.export_log).pack(side=tk.LEFT)
        
    def update_port_list(self):
        """Scan for available serial ports"""
        try:
            ports = serial.tools.list_ports.comports()
            self.available_ports = [port.device for port in ports]
            self.port_combo['values'] = self.available_ports
            
            if self.available_ports and not self.port_var.get():
                self.port_var.set(self.available_ports[0])
                
            self.log_message(f"Found {len(self.available_ports)} serial ports")
        except Exception as e:
            self.log_message(f"Error scanning ports: {str(e)}")
            
    def connect_serial(self):
        """Connect to selected serial port"""
        if not self.port_var.get():
            messagebox.showerror("Error", "Please select a port")
            return
            
        try:
            self.serial_connection = serial.Serial(
                port=self.port_var.get(),
                baudrate=int(self.baud_var.get()),
                timeout=1
            )
            
            self.connected = True
            self.connection_status_var.set("Connected")
            self.connection_label.configure(foreground="green")
            
            # Update button states
            self.connect_btn.configure(state="disabled")
            self.disconnect_btn.configure(state="normal")
            self.refresh_btn.configure(state="disabled")
            
            # Start reading thread
            self.stop_threads = False
            self.read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.read_thread.start()
            
            self.log_message(f"Connected to {self.port_var.get()} at {self.baud_var.get()} baud")
            
            # Request device status
            time.sleep(2)  # Give Arduino time to initialize
            self.send_command("status")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.log_message(f"Connection failed: {str(e)}")
            
    def disconnect_serial(self):
        """Disconnect from serial port"""
        self.stop_threads = True
        
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            
        self.connected = False
        self.connection_status_var.set("Disconnected")
        self.connection_label.configure(foreground="red")
        self.device_count_var.set("0")
        self.system_state_var.set("Unknown")
        
        # Update button states
        self.connect_btn.configure(state="normal")
        self.disconnect_btn.configure(state="disabled")
        self.refresh_btn.configure(state="normal")
        
        # Reset device lists
        self.update_device_lists()
        
        self.log_message("Disconnected from serial port")
        
    def read_serial_data(self):
        """Read data from serial port in separate thread"""
        while not self.stop_threads and self.connected:
            try:
                if self.serial_connection and self.serial_connection.in_waiting:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.message_queue.put(('receive', line))
                        
                        # Parse device count from status messages
                        if "Total devices:" in line or "Total Devices:" in line:
                            match = re.search(r'Total [Dd]evices:\s*(\d+)', line)
                            if match:
                                self.total_devices = int(match.group(1))
                                self.message_queue.put(('device_count', self.total_devices))
                        
                        # Parse initialization completion messages
                        if "Initialization complete" in line and "Total devices:" in line:
                            match = re.search(r'Total devices:\s*(\d+)', line)
                            if match:
                                self.total_devices = int(match.group(1))
                                self.message_queue.put(('device_count', self.total_devices))
                                self.message_queue.put(('init_complete', True))
                        
                        # Parse master device startup messages for device counting
                        if "Round Robin Master Started" in line:
                            # Start counting devices from master initialization
                            self.message_queue.put(('master_started', True))
                                
                        # Parse device initialization messages  
                        if "Device initialized as ID:" in line:
                            match = re.search(r'ID:\s*(\d+)', line)
                            if match:
                                device_id = int(match.group(1))
                                self.message_queue.put(('device_initialized', device_id))
                                
                        # Parse system state
                        if "Current State:" in line:
                            state_match = re.search(r'Current State:\s*(\w+)', line)
                            if state_match:
                                self.message_queue.put(('system_state', state_match.group(1)))
                                
                time.sleep(0.1)
            except Exception as e:
                if self.connected:  # Only log if we're supposed to be connected
                    self.message_queue.put(('error', f"Read error: {str(e)}"))
                break
                
    def update_gui(self):
        """Update GUI with messages from serial thread"""
        try:
            while True:
                message_type, data = self.message_queue.get_nowait()
                
                if message_type == 'receive':
                    self.log_message(f"RX: {data}")
                elif message_type == 'device_count':
                    self.device_count_var.set(str(data))
                    self.update_device_lists()
                    self.log_message(f"Device count updated: {data} devices detected")
                elif message_type == 'system_state':
                    self.system_state_var.set(data)
                elif message_type == 'master_started':
                    self.log_message("Master device started - beginning device detection")
                elif message_type == 'device_initialized':
                    self.log_message(f"Device {data:03d} initialized")
                elif message_type == 'init_complete':
                    self.log_message("Device initialization complete")
                elif message_type == 'error':
                    self.log_message(data)
                    
        except queue.Empty:
            pass
            
        # Schedule next update
        self.root.after(100, self.update_gui)
        
    def update_device_lists(self):
        """Update device selection dropdowns"""
        individual_devices = []  # Individual devices for servo and DAC individual mode
        
        if self.total_devices > 0:
            individual_devices = [f"{i:03d}" for i in range(1, self.total_devices + 1)]
            
        # Update servo device dropdown (individual devices only)
        if individual_devices:
            self.servo_device_combo['values'] = individual_devices
            if self.servo_device_var.get() not in individual_devices:
                self.servo_device_var.set(individual_devices[0])
        else:
            self.servo_device_combo['values'] = ["001"]
            self.servo_device_var.set("001")
        
        # Update DAC device dropdown (individual devices only)
        if individual_devices:
            self.dac_device_combo['values'] = individual_devices
            if self.dac_device_var.get() not in individual_devices:
                self.dac_device_var.set(individual_devices[0])
        else:
            self.dac_device_combo['values'] = ["001"]
            self.dac_device_var.set("001")
            

                
    def update_servo_mode(self):
        """Update servo control mode and UI elements"""
        if self.servo_mode_var.get() == "all":
            # Disable device selection for all mode
            self.servo_device_label.configure(state="disabled")
            self.servo_device_combo.configure(state="disabled")
            self.servo_send_btn.configure(text="Send to All Servos")
        else:
            # Enable device selection for individual mode
            self.servo_device_label.configure(state="normal")
            self.servo_device_combo.configure(state="readonly")
            self.servo_send_btn.configure(text="Send to Selected Servo")
            
    def update_dac_mode(self):
        """Update DAC control mode and UI elements"""
        if self.dac_mode_var.get() == "all":
            # Disable device selection for all mode
            self.dac_device_label.configure(state="disabled")
            self.dac_device_combo.configure(state="disabled")
            self.dac_send_btn.configure(text="Send to All LEDs")
        else:
            # Enable device selection for individual mode
            self.dac_device_label.configure(state="normal")
            self.dac_device_combo.configure(state="readonly")
            self.dac_send_btn.configure(text="Send to Selected LED")
                
    def send_command(self, command):
        """Send command to Arduino"""
        if not self.connected or not self.serial_connection:
            messagebox.showerror("Error", "Not connected to device")
            return False
            
        try:
            self.serial_connection.write(f"{command}\n".encode())
            self.log_message(f"TX: {command}")
            self.command_history.append(command)
            return True
        except Exception as e:
            self.log_message(f"Send error: {str(e)}")
            return False
            
    def send_servo_command(self):
        """Send servo control command based on selected mode with timeout recovery"""
        angle = self.servo_angle_var.get()
        
        try:
            angle_int = int(angle)
            if 0 <= angle_int <= 180:
                if self.servo_mode_var.get() == "all":
                    # Send to all devices (disk mode)
                    device_id = "000"
                    command = f"{device_id},servo,{angle_int}"
                    if self.send_command_with_recovery(command):
                        self.log_message(f"Servo command sent to ALL devices: Angle {angle_int}° (Disk Mode)")
                else:
                    # Send to individual device
                    device_id = self.servo_device_var.get()
                    command = f"{device_id},servo,{angle_int}"
                    if self.send_command_with_recovery(command):
                        self.log_message(f"Servo command sent to Device {device_id}: Angle {angle_int}°")
            else:
                messagebox.showerror("Error", "Servo angle must be between 0 and 180 degrees")
        except ValueError:
            messagebox.showerror("Error", "Invalid servo angle value")
            
    def send_dac_command(self):
        """Send DAC control command based on selected mode with timeout recovery"""
        percent = self.dac_percent_var.get()
        
        try:
            percent_int = int(percent)
            if 0 <= percent_int <= 100:
                # Convert percentage to 10-bit DAC value (0-1023)
                dac_value = int((percent_int / 100.0) * 1023)
                
                if self.dac_mode_var.get() == "all":
                    # Send to all devices
                    device_id = "000"
                    command = f"{device_id},dac,{dac_value}"
                    if self.send_command_with_recovery(command):
                        self.log_message(f"DAC command sent to ALL LEDs: {percent_int}% (Raw: {dac_value})")
                else:
                    # Send to individual device
                    device_id = self.dac_device_var.get()
                    command = f"{device_id},dac,{dac_value}"
                    if self.send_command_with_recovery(command):
                        self.log_message(f"DAC command sent to Device {device_id}: {percent_int}% (Raw: {dac_value})")
            else:
                messagebox.showerror("Error", "DAC percentage must be between 0 and 100")
        except ValueError:
            messagebox.showerror("Error", "Invalid DAC percentage value")
            
    def send_command_with_recovery(self, command):
        """Send command with automatic recovery on timeout"""
        if not self.connected or not self.serial_connection:
            messagebox.showerror("Error", "Not connected to device")
            return False
        
        # First, check if Arduino is ready by sending status command
        self.send_command("status")
        
        try:
            self.serial_connection.write(f"{command}\n".encode())
            self.log_message(f"TX: {command}")
            self.command_history.append(command)
            
            # Monitor for timeout warning and auto-recover
            import time
            start_time = time.time()
            timeout_detected = False
            
            # Check for timeout warning in next few messages
            while time.time() - start_time < 3.0:  # Wait up to 3 seconds
                if not self.message_queue.empty():
                    try:
                        message_type, data = self.message_queue.get_nowait()
                        if message_type == 'receive' and "WARNING: Command timeout" in data:
                            timeout_detected = True
                            break
                    except:
                        pass
                time.sleep(0.1)
            
            if timeout_detected:
                self.log_message("Timeout detected - reinitializing and retrying...")
                self.send_command("reinit")
                time.sleep(2)  # Wait for reinitialization
                # Retry the command
                self.serial_connection.write(f"{command}\n".encode())
                self.log_message(f"TX (retry): {command}")
                
            return True
        except Exception as e:
            self.log_message(f"Send error: {str(e)}")
            return False
            
    def set_servo_angle(self, angle):
        """Set servo angle from preset button"""
        self.servo_angle_var.set(angle)
        
    def set_dac_percent(self, percent):
        """Set DAC percentage from preset button"""
        self.dac_percent_var.set(percent)
        
    def update_dac_raw_value(self, *args):
        """Update raw DAC value display when percentage changes"""
        try:
            percent = int(self.dac_percent_var.get())
            raw_value = int((percent / 100.0) * 1023)
            self.dac_raw_var.set(str(raw_value))
        except (ValueError, AttributeError):
            self.dac_raw_var.set("0")
            
    def update_servo_display(self, value):
        """Update servo angle display to show integer values"""
        try:
            int_value = int(float(value))
            self.servo_angle_var.set(int_value)
        except (ValueError, TypeError):
            pass
            
    def update_dac_display(self, value):
        """Update DAC percentage display to show integer values"""
        try:
            int_value = int(float(value))
            self.dac_percent_var.set(int_value)
        except (ValueError, TypeError):
            pass
            
    def export_log(self):
        """Export communication log to file"""
        try:
            from tkinter import filedialog
            from datetime import datetime
            
            # Get current log content
            log_content = self.log_text.get(1.0, tk.END)
            
            if not log_content.strip():
                messagebox.showwarning("Warning", "Log is empty - nothing to export")
                return
            
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"led_controller_log_{timestamp}.txt"
            
            # Open file dialog
            filename = filedialog.asksaveasfilename(
                title="Export Communication Log",
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ],
                initialfile=default_filename
            )
            
            if filename:
                # Write log content to file
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("SEEEDuino LED Array Controller - Communication Log\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total Devices: {self.total_devices}\n")
                    f.write(f"Connection Status: {self.connection_status_var.get()}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(log_content)
                
                self.log_message(f"Log exported to: {filename}")
                messagebox.showinfo("Export Complete", f"Log exported successfully to:\n{filename}")
                
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("Export Error", error_msg)
            
    def set_manual_device_count(self):
        """Manually set device count for debugging"""
        try:
            count = int(self.manual_count_var.get())
            if 1 <= count <= 10:
                self.total_devices = count
                self.device_count_var.set(str(count))
                self.update_device_lists()
                self.log_message(f"Manual device count set to: {count}")
            else:
                messagebox.showerror("Error", "Device count must be between 1 and 10")
        except ValueError:
            messagebox.showerror("Error", "Invalid device count value")
            

    def show_help_window(self):
        """Show comprehensive GUI help window"""
        help_window = tk.Toplevel(self.root)
        help_window.title("SEEEDuino LED Array Controller - Help")
        help_window.geometry("800x600")
        help_window.configure(bg='#f0f0f0')
        
        # Create scrollable text area
        help_frame = ttk.Frame(help_window, padding="20")
        help_frame.pack(fill=tk.BOTH, expand=True)
        
        help_text = scrolledtext.ScrolledText(help_frame, height=30, width=80, wrap=tk.WORD)
        help_text.pack(fill=tk.BOTH, expand=True)
        
        # Help content
        help_content = """
        SEEEDuino LED Array Controller GUI - User Guide
        ===============================================
        
        DEVICE NUMBERING SYSTEM:
        • 000 = ALL DEVICES (Broadcast command)
        • 001 = Master Device (Connected to computer via USB)
        • 002, 003, 004... = Slave Devices (In daisy-chain)
        
        SERVO CONTROL MODES:
        
        1. ALL SERVOS (DISK MODE):
           • Commands all servos simultaneously
           • Perfect for synchronized rotation
           • Uses device ID 000 automatically
           • Example: All servos move to 90° together
        
        2. INDIVIDUAL SERVO MODE:
           • Target specific devices (001, 002, 003...)
           • Precise control of single servos
           • Select device from dropdown
           • Example: Only device 002 servo moves to 45°
        
        DAC (LED) CONTROL:
        • 000 = All LEDs (synchronized brightness)
        • 001, 002, 003... = Individual device LEDs
        • Control via percentage (0-100%)
        • Automatic conversion to 10-bit values (0-1023)
        
        COMMAND EXAMPLES:
        
        Servo Commands:
        • All servos to 90°: Uses mode "All Servos", angle=90
        • Device 2 servo to 45°: Uses mode "Individual", device=002, angle=45
        • Device 1 servo to 180°: Uses mode "Individual", device=001, angle=180
        
        DAC/LED Commands:
        • All LEDs to 50%: Device=000, percentage=50% (→ raw value 512)
        • Device 3 LED to 75%: Device=003, percentage=75% (→ raw value 768)
        • Device 1 LED off: Device=001, percentage=0% (→ raw value 0)
        
        CONNECTION SETUP:
        
        1. Hardware Connection:
           • Connect master device (001) to computer via USB
           • Daisy-chain: 001→002→003→...→001 (round-robin)
           • TX of device N connects to RX of device N+1
           • Last device TX connects back to master RX
        
        2. Software Connection:
           • Select correct COM port from dropdown
           • Set baud rate to 115200 (matches Arduino)
           • Click "Connect"
           • Wait for device initialization (5-10 seconds)
           • Check "Total Devices" count
        
        TROUBLESHOOTING:
        
        Device Detection Issues:
        • Use "Manual Count" to set device count (e.g., 2 or 3)
        • Click "Re-initialize" to restart detection
        • Check physical connections in daisy-chain
        • Ensure all devices are powered
        
        Timeout Warnings:
        • "WARNING: Command timeout" is normal Arduino protection
        • Occurs if command takes longer than 2.5 seconds
        • System automatically returns to READY state
        • Simply resend the command if needed
        • NOT a GUI problem - this is Arduino safety feature
        
        Command Not Working:
        • Check device is detected (see "Total Devices")
        • Verify device ID is in valid range (001 to detected count)
        • Ensure servo angles are 0-180°
        • Ensure DAC percentages are 0-100%
        • Check communication log for error messages
        
        PRESET BUTTONS:
        
        Servo Presets: 0°, 45°, 90°, 135°, 180°
        DAC Presets: 0%, 25%, 50%, 75%, 100%
        
        These provide quick access to common values.
        
        STATUS INDICATORS:
        
        • Connection: Green="Connected", Red="Disconnected"
        • Total Devices: Number of detected devices in chain
        • System State: READY, PROCESSING, INIT_WAITING, etc.
        
        COMMUNICATION LOG:
        
        • TX: Commands sent from GUI to Arduino
        • RX: Responses received from Arduino
        • Timestamps for all communications
        • Useful for debugging connection issues
        
        MANUAL COMMANDS:
        
        • Device Status: Query system status and device info
        • Re-initialize: Restart device chain detection
        • Help: Arduino's built-in command help (via serial)
        
        ADVANCED FEATURES:
        
        Manual Device Count:
        • Override automatic detection
        • Useful when auto-detection fails
        • Set count and click "Set" button
        • Updates device dropdown lists
        
        BEST PRACTICES:
        
        1. Always wait for initialization to complete
        2. Use "All Servos" mode for synchronized movements
        3. Use "Individual" mode for precise positioning
        4. Monitor the communication log for issues
        5. Use manual device count if auto-detection fails
        6. Check timeout warnings - they're usually harmless
        
        HARDWARE NOTES:
        
        • Master device (001) must be connected via USB
        • Slave devices get power through daisy-chain
        • Each device has one servo and one DAC output
        • Round-robin ensures all devices receive commands
        • Commands loop through the entire chain
        
        For technical support, check the communication log
        and verify all physical connections.
        """
        
        help_text.insert(tk.END, help_content)
        help_text.configure(state='disabled')  # Make read-only
        
        # Close button
        close_btn = ttk.Button(help_frame, text="Close", 
                              command=help_window.destroy)
        close_btn.pack(pady=(10, 0))
            
    def log_message(self, message):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Update GUI in main thread
        self.root.after(0, self._append_to_log, formatted_message)
        
    def _append_to_log(self, message):
        """Append message to log text widget (must be called from main thread)"""
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        
        # Limit log size
        lines = self.log_text.get(1.0, tk.END).count('\n')
        if lines > 1000:
            self.log_text.delete(1.0, "100.0")
            
    def clear_log(self):
        """Clear the communication log"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("Log cleared")
        
    def on_closing(self):
        """Handle application closing"""
        if self.connected:
            self.disconnect_serial()
        self.stop_threads = True
        self.root.destroy()


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = LEDArrayControllerGUI(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the GUI
    root.mainloop()


if __name__ == "__main__":
    main() 