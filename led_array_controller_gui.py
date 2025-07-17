#!/usr/bin/env python3
"""
SOLAR GUI

This GUI provides an interface for controlling SEEEDuino XIAO boards
in a daisy-chained round-robin communication system.

Features:
- Serial port scanning and connection management
- Servo angle control (60-120 degrees)
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
        self.root.title("SOLAR GUI v1.0")
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
        
        # Demo state variables
        self.demo_running = False
        self.demo_thread = None
        
        # Command completion tracking
        self.waiting_for_eot = False
        
        # Demo status variable (referenced in update_gui but needs initialization)
        self.demo_status_var = tk.StringVar(value="Ready for demos")
        
        # Create GUI elements
        self.create_widgets()
        self.update_port_list()
        
        # Auto-connect to first available port
        self.root.after(1000, self.auto_connect_first_port)
        
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
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # === Connection Section ===
        self.create_connection_section(main_frame, 0, 0)
        
        # === Device Status Section ===
        self.create_status_section(main_frame, 0, 1)
        
        # === Demo Section ===
        self.create_demo_section(main_frame, 0, 2)
        
        # === Control Sections ===
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
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
        
        # Manual commands
        manual_frame = ttk.Frame(status_frame)
        manual_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(manual_frame, text="Device Status", 
                  command=lambda: self.send_command("status")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manual_frame, text="Re-initialize", 
                  command=lambda: self.send_command("reinit")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manual_frame, text="Help", 
                  command=self.show_help_window).pack(side=tk.LEFT)
        
    def create_demo_section(self, parent, row, col):
        """Create demo pattern controls"""
        demo_frame = ttk.LabelFrame(parent, text="Demo Patterns", padding="10")
        demo_frame.grid(row=row, column=col, sticky=(tk.W, tk.E, tk.N), padx=(5, 0))
        
        # Demo 1: Servo Dance
        demo1_frame = ttk.Frame(demo_frame)
        demo1_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 5))
        
        self.demo1_btn = ttk.Button(demo1_frame, text="🕺 Servo Dance", 
                                   command=self.start_dance, width=20)
        self.demo1_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(demo1_frame, text="Servo sweep + DAC flash", 
                 foreground="gray", font=("Arial", 8)).pack(side=tk.LEFT)
        
        # Demo 2: Servo Wave
        demo2_frame = ttk.Frame(demo_frame)
        demo2_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.demo2_btn = ttk.Button(demo2_frame, text="🌊 Servo Wave", 
                                   command=self.start_servo_wave, width=20)
        self.demo2_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(demo2_frame, text="Smooth servo oscillation", 
                 foreground="gray", font=("Arial", 8)).pack(side=tk.LEFT)
        
        # Demo 3: DAC Rainbow
        demo3_frame = ttk.Frame(demo_frame)
        demo3_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.demo3_btn = ttk.Button(demo3_frame, text="🌈 DAC Rainbow", 
                                   command=self.start_dac_rainbow, width=20)
        self.demo3_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(demo3_frame, text="Progressive brightness fade", 
                 foreground="gray", font=("Arial", 8)).pack(side=tk.LEFT)
        
        # Stop demo button
        self.stop_demo_btn = ttk.Button(demo_frame, text="⏹️ Stop Demo", 
                                       command=self.stop_demo, state="disabled")
        self.stop_demo_btn.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
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
        servo_angle_spin = ttk.Spinbox(servo_frame, from_=60, to=120, width=10, 
                                      textvariable=self.servo_angle_var)
        servo_angle_spin.grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # Angle slider  
        self.servo_scale = ttk.Scale(servo_frame, from_=60, to=120, orient=tk.HORIZONTAL,
                                    variable=self.servo_angle_var, length=250,
                                    command=self.update_servo_display)
        self.servo_scale.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 10))
        
        # Preset buttons
        preset_frame = ttk.Frame(servo_frame)
        preset_frame.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(preset_frame, text="60°", width=6,
                  command=lambda: self.set_servo_angle(60)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="75°", width=6,
                  command=lambda: self.set_servo_angle(75)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="90°", width=6,
                  command=lambda: self.set_servo_angle(90)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="105°", width=6,
                  command=lambda: self.set_servo_angle(105)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="120°", width=6,
                  command=lambda: self.set_servo_angle(120)).pack(side=tk.LEFT)
        
        # Send and Demo buttons
        button_frame = ttk.Frame(servo_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        self.servo_send_btn = ttk.Button(button_frame, text="Send to All Servos", 
                                        command=self.send_servo_command)
        self.servo_send_btn.pack(side=tk.LEFT)
        
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
        
                # Current control (mA) - Limited to 1500mA for safety
        ttk.Label(dac_frame, text="Current (mA):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.dac_current_var = tk.IntVar(value=0)
        dac_current_spin = ttk.Spinbox(dac_frame, from_=0, to=1500, width=10, 
                                      textvariable=self.dac_current_var)
        dac_current_spin.grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # Current slider - Limited to 1500mA
        self.dac_scale = ttk.Scale(dac_frame, from_=0, to=1500, orient=tk.HORIZONTAL,
                                  variable=self.dac_current_var, length=250,
                                  command=self.update_dac_display)
        self.dac_scale.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 10))
        
        # Raw value display
        ttk.Label(dac_frame, text="Raw Value:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.dac_raw_var = tk.StringVar(value="0")
        ttk.Label(dac_frame, textvariable=self.dac_raw_var).grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # Update raw value when current changes
        self.dac_current_var.trace('w', self.update_dac_raw_value)
        
        # Preset buttons
        preset_frame = ttk.Frame(dac_frame)
        preset_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(preset_frame, text="0mA", width=7,
                  command=lambda: self.set_dac_current(0)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="375mA", width=7,
                  command=lambda: self.set_dac_current(375)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="750mA", width=7,
                  command=lambda: self.set_dac_current(750)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="1125mA", width=7,
                  command=lambda: self.set_dac_current(1125)).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(preset_frame, text="1500mA", width=7,
                  command=lambda: self.set_dac_current(1500)).pack(side=tk.LEFT)
        
        # Send button with dynamic text
        self.dac_send_btn = ttk.Button(dac_frame, text="Send to All LEDs", 
                                      command=self.send_dac_command)
        self.dac_send_btn.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        
    def create_log_section(self, parent, row, col):
        """Create command log and output section"""
        log_frame = ttk.LabelFrame(parent, text="Communication Log", padding="10")
        log_frame.grid(row=row, column=col, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
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
        
    def auto_connect_first_port(self):
        """Automatically connect to the first available port if not already connected"""
        if self.connected:
            return  # Already connected, skip auto-connect
            
        if not self.available_ports:
            self.log_message("Auto-connect: No serial ports detected")
            return
            
        try:
            first_port = self.available_ports[0]
            self.port_var.set(first_port)
            self.log_message(f"Auto-connecting to first available port: {first_port}")
            self.connect_serial()
        except Exception as e:
            self.log_message(f"Auto-connect failed: {str(e)}")
        
    def read_serial_data(self):
        """Read data from serial port in separate thread"""
        while not self.stop_threads and self.connected:
            try:
                if self.serial_connection and self.serial_connection.in_waiting:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        # Filter out DEBUG messages before any processing
                        if line.startswith("DEBUG:"):
                            continue
                        
                        # Parse new Arduino protocol messages
                        if line.startswith("TOTAL:"):
                            total_match = re.search(r'TOTAL:(\d+)', line)
                            if total_match:
                                self.total_devices = int(total_match.group(1))
                                self.message_queue.put(('device_count', self.total_devices))
                        
                        elif line.startswith("STATE:"):
                            state_match = re.search(r'STATE:(.+)', line)
                            if state_match:
                                state_name = state_match.group(1).strip()
                                self.message_queue.put(('system_state', state_name))
                                
                                # Add user-friendly state messages
                                if state_name == "Chain Wait":
                                    self.message_queue.put(('user_log', "🔗 Waiting for chain connection"))
                                elif state_name == "Initializing":
                                    self.message_queue.put(('user_log', "🚀 Starting device initialization"))
                        
                        elif line.startswith("VER:"):
                            version_match = re.search(r'VER:(.+)', line)
                            if version_match:
                                version = version_match.group(1).strip()
                                self.message_queue.put(('version', version))
                        
                        elif line.startswith("INIT:TOTAL:"):
                            total_match = re.search(r'INIT:TOTAL:(\d+)', line)
                            if total_match:
                                self.total_devices = int(total_match.group(1))
                                self.message_queue.put(('device_count', self.total_devices))
                                self.message_queue.put(('init_complete', True))
                        
                        elif line.startswith("INIT:DEV:"):
                            dev_match = re.search(r'INIT:DEV:(\d+)', line)
                            if dev_match:
                                device_id = int(dev_match.group(1))
                                self.message_queue.put(('device_initialized', device_id))
                        
                        elif line == "EOT":
                            self.message_queue.put(('command_complete', True))
                        
                        elif line.startswith("UI:"):
                            # User interface messages - strip UI: prefix and show
                            ui_message = line[3:].strip()
                            self.message_queue.put(('ui_message', ui_message))
                        
                        elif line.startswith("ERR:"):
                            # Error messages
                            error_message = line[4:].strip()
                            self.message_queue.put(('error_message', error_message))
                        
                        elif line.startswith("SRV:"):
                            # Parse servo feedback for value only: SRV:device:angle
                            srv_match = re.search(r'SRV:(\d+):(\d+)', line)
                            if srv_match:
                                angle = int(srv_match.group(2))
                                self.message_queue.put(('servo_feedback', angle))
                        
                        elif line.startswith("DAC:"):
                            # Parse DAC feedback for value only: DAC:device:value
                            dac_match = re.search(r'DAC:(\d+):(\d+)', line)
                            if dac_match:
                                raw_value = int(dac_match.group(2))
                                self.message_queue.put(('dac_feedback', raw_value))
                        
                        # Only log non-filtered messages to RX log (filter out EOT, VER:, TOTAL:)
                        if not (line.startswith("VER:") or line.startswith("TOTAL:") or 
                        line.startswith("INIT:TOTAL:") or line.startswith("SRV:") or line.startswith("DAC:")
                        or line.startswith("STATE:")):
                            self.message_queue.put(('receive', line))
                                
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
                    # Sync demo status with system state (if not running a demo)
                    if not self.demo_running:
                        if data == "Ready":
                            self.demo_status_var.set("Ready for demos")
                        elif data == "Initializing":
                            self.demo_status_var.set("System initializing...")
                        elif data == "Processing":
                            self.demo_status_var.set("Processing command...")
                        elif data == "Waiting for Chain":
                            self.demo_status_var.set("Waiting for chain...")
                        else:
                            self.demo_status_var.set(f"System: {data}")
                elif message_type == 'command_complete':
                    if self.waiting_for_eot:
                        self.waiting_for_eot = False
                        self.log_message("✓ Command completed successfully")
                elif message_type == 'device_initialized':
                    self.log_message(f"Device {data:03d} initialized")
                elif message_type == 'init_complete':
                    self.log_message("Device initialization complete")
                elif message_type == 'version':
                    self.log_message(f"Arduino Version: {data}")
                elif message_type == 'ui_message':
                    self.log_message(f"ℹ️ {data}")
                elif message_type == 'error_message':
                    self.log_message(f"❌ Error: {data}")
                elif message_type == 'user_log':
                    self.log_message(data)
                elif message_type == 'servo_feedback':
                    angle = data
                    if self.servo_mode_var.get() == "all":
                        self.log_message(f"🎯 All servos set to {angle}°")
                    else:
                        device_id = self.servo_device_var.get()
                        self.log_message(f"🎯 Servo on device {device_id} set to {angle}°")
                elif message_type == 'dac_feedback':
                    raw_value = data
                    current_ma = int((raw_value / 1023.0) * 2100)
                    if self.dac_mode_var.get() == "all":
                        self.log_message(f"💡 All DACs set to {current_ma}mA (raw: {raw_value})")
                    else:
                        device_id = self.dac_device_var.get()
                        self.log_message(f"💡 DAC on device {device_id} set to {current_ma}mA (raw: {raw_value})")
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
        if self.waiting_for_eot:
            messagebox.showwarning("Wait", "Please wait for previous command to complete")
            return
            
        angle = self.servo_angle_var.get()
        
        try:
            angle_int = int(angle)
            if 60 <= angle_int <= 120:
                if self.servo_mode_var.get() == "all":
                    # Send to all devices (disk mode)
                    device_id = "000"
                    command = f"{device_id},servo,{angle_int}"
                    if self.send_command_with_eot_tracking(command):
                        self.log_message(f"Servo command sent to ALL devices: Angle {angle_int}° (Disk Mode)")
                else:
                    # Send to individual device
                    device_id = self.servo_device_var.get()
                    command = f"{device_id},servo,{angle_int}"
                    if self.send_command_with_eot_tracking(command):
                        self.log_message(f"Servo command sent to Device {device_id}: Angle {angle_int}°")
            else:
                messagebox.showerror("Error", "Servo angle must be between 60 and 120 degrees")
        except ValueError:
            messagebox.showerror("Error", "Invalid servo angle value")
            
    def send_dac_command(self):
        """Send DAC control command based on selected mode with timeout recovery"""
        if self.waiting_for_eot:
            messagebox.showwarning("Wait", "Please wait for previous command to complete")
            return
            
        current_ma = self.dac_current_var.get()
        
        try:
            current_int = int(current_ma)
            if 0 <= current_int <= 1500:
                # Convert current (mA) to 10-bit DAC value (0-1023)
                # 0-2100mA maps to 0-1023 raw value
                dac_value = int((current_int / 2100.0) * 1023)
                
                if self.dac_mode_var.get() == "all":
                    # Send to all devices
                    device_id = "000"
                    command = f"{device_id},dac,{dac_value}"
                    if self.send_command_with_eot_tracking(command):
                        self.log_message(f"DAC command sent to ALL LEDs: {current_int}mA (Raw: {dac_value})")
                else:
                    # Send to individual device
                    device_id = self.dac_device_var.get()
                    command = f"{device_id},dac,{dac_value}"
                    if self.send_command_with_eot_tracking(command):
                        self.log_message(f"DAC command sent to Device {device_id}: {current_int}mA (Raw: {dac_value})")
            else:
                messagebox.showerror("Error", "Current must be between 0 and 1500 mA (safety limit)")
        except ValueError:
            messagebox.showerror("Error", "Invalid current value")
            
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
            
    def send_command_with_eot_tracking(self, command):
        """Send command and track for completion"""
        if not self.connected or not self.serial_connection:
            messagebox.showerror("Error", "Not connected to device")
            return False
            
        try:
            # Log processing message before sending
            self.log_message("⚙️ Processing command")
            
            self.serial_connection.write(f"{command}\n".encode())
            self.log_message(f"TX: {command}")
            self.command_history.append(command)
            
            # Set waiting flag for completion detection
            self.waiting_for_eot = True
            self.log_message("⏳ Waiting for command completion...")
            
            return True
        except Exception as e:
            self.log_message(f"Send error: {str(e)}")
            self.waiting_for_eot = False
            return False
            
    def set_servo_angle(self, angle):
        """Set servo angle from preset button"""
        self.servo_angle_var.set(angle)
        

        
    def set_dac_current(self, current_ma):
        """Set DAC current from preset button"""
        self.dac_current_var.set(current_ma)
        
    def update_dac_raw_value(self, *args):
        """Update raw DAC value display when current changes"""
        try:
            current_ma = int(self.dac_current_var.get())
            # Convert 0-2100mA to 0-1023 raw value (keeping original mapping)
            # Maximum user input is 1500mA (safety limit) = raw value 730
            raw_value = int((current_ma / 2100.0) * 1023)
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
        """Update DAC current display to show integer values"""
        try:
            int_value = int(float(value))
            self.dac_current_var.set(int_value)
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
                    f.write("SOLAR- Communication Log\n")
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
            
    # === DEMO METHODS ===
    
    def start_dance(self):
        """Start Servo Dance demo: Servo 60→120→90, DAC 50%→0%, repeat 2x"""
        if self.demo_running:
            self.log_message("Demo already running - please wait for completion")
            return
        if not self.connected:
            messagebox.showerror("Error", "Not connected to device")
            return
        
        self.demo_running = True
        self.demo_status_var.set("Running Servo Dance...")
        self.disable_demo_buttons()
        self.demo_thread = threading.Thread(target=self.run_dance, daemon=True)
        self.demo_thread.start()
        
    def run_dance(self):
        """Run dance pattern"""
        try:
            self.log_message("🕺 Starting Servo Dance demo...")
            
            for cycle in range(2):  # Repeat 2 times
                if not self.demo_running:
                    break
                    
                self.log_message(f"Dance - Cycle {cycle + 1}/2")
                
                # Servo to 60°
                self.send_command("000,servo,60")
                time.sleep(0.8)
                
                # Servo to 120°
                if self.demo_running:
                    self.send_command("000,servo,120")
                    time.sleep(0.8)
                
                # DAC to 750mA (50% of 1500mA limit)
                if self.demo_running:
                    dac_value = int((750 / 2100.0) * 1023)  # 750mA within safety limit
                    self.send_command(f"000,dac,{dac_value}")
                    time.sleep(0.5)
                
                # Servo to 90°
                if self.demo_running:
                    self.send_command("000,servo,90")
                    time.sleep(0.5)
                
                # DAC to 0mA
                if self.demo_running:
                    self.send_command("000,dac,0")
                    time.sleep(0.8)
                    
        except Exception as e:
            self.log_message(f"Demo error: {str(e)}")
        finally:
            self.demo_running = False
            self.root.after(0, self.reset_demo_state)
            self.log_message("🕺 Servo Dance demo completed")
    
    def start_servo_wave(self):
        """Start smooth servo wave demo"""
        if self.demo_running:
            self.log_message("Demo already running - please wait for completion")
            return
        if not self.connected:
            messagebox.showerror("Error", "Not connected to device")
            return
            
        self.demo_running = True
        self.demo_status_var.set("Running Servo Wave...")
        self.disable_demo_buttons()
        self.demo_thread = threading.Thread(target=self.run_servo_wave, daemon=True)
        self.demo_thread.start()
        
    def run_servo_wave(self):
        """Run smooth servo wave pattern"""
        try:
            self.log_message("🌊 Starting Servo Wave demo...")
            
            # Create smooth wave motion
            for cycle in range(2):
                if not self.demo_running:
                    break
                    
                # Forward wave: 60 to 120 in small steps
                for angle in range(60, 121, 5):
                    if not self.demo_running:
                        break
                    self.send_command(f"000,servo,{angle}")
                    time.sleep(0.3)
                
                # Backward wave: 120 to 60 in small steps
                for angle in range(120, 59, -5):
                    if not self.demo_running:
                        break
                    self.send_command(f"000,servo,{angle}")
                    time.sleep(0.3)
                    
        except Exception as e:
            self.log_message(f"Demo error: {str(e)}")
        finally:
            self.demo_running = False
            self.root.after(0, self.reset_demo_state)
            self.log_message("🌊 Servo Wave demo completed")
    
    def start_dac_rainbow(self):
        """Start DAC rainbow fade demo"""
        if self.demo_running:
            self.log_message("Demo already running - please wait for completion")
            return
        if not self.connected:
            messagebox.showerror("Error", "Not connected to device")
            return
            
        self.demo_running = True
        self.demo_status_var.set("Running DAC Rainbow...")
        self.disable_demo_buttons()
        self.demo_thread = threading.Thread(target=self.run_dac_rainbow, daemon=True)
        self.demo_thread.start()
        
    def run_dac_rainbow(self):
        """Run DAC rainbow fade pattern"""
        try:
            self.log_message("🌈 Starting DAC Rainbow demo...")
            
            for cycle in range(2):  # 2 complete fades
                if not self.demo_running:
                    break
                    
                # Fade up: 0mA to 1500mA (safety limit)
                for current_ma in range(0, 1501, 150):
                    if not self.demo_running:
                        break
                    dac_value = int((current_ma / 2100.0) * 1023)
                    self.send_command(f"000,dac,{dac_value}")
                    time.sleep(0.2)
                
                # Hold at maximum
                if self.demo_running:
                    time.sleep(0.5)
                
                # Fade down: 1500mA to 0mA
                for current_ma in range(1500, -1, -150):
                    if not self.demo_running:
                        break
                    dac_value = int((current_ma / 2100.0) * 1023)
                    self.send_command(f"000,dac,{dac_value}")
                    time.sleep(0.2)
                
                # Hold at minimum
                if self.demo_running:
                    time.sleep(0.5)
                    
        except Exception as e:
            self.log_message(f"Demo error: {str(e)}")
        finally:
            self.demo_running = False
            self.root.after(0, self.reset_demo_state)
            self.log_message("🌈 DAC Rainbow demo completed")
    

    
    def stop_demo(self):
        """Stop any running demo"""
        if self.demo_running:
            self.demo_running = False
            self.log_message("⏹️ Demo stopped by user")
            self.reset_demo_state()
        
    def disable_demo_buttons(self):
        """Disable all demo buttons during demo"""
        self.demo1_btn.configure(state="disabled")
        self.demo2_btn.configure(state="disabled")
        self.demo3_btn.configure(state="disabled")
        self.stop_demo_btn.configure(state="normal")
        
    def reset_demo_state(self):
        """Reset demo UI state (must be called from main thread)"""
        # Sync with current system state when demo ends
        current_state = self.system_state_var.get()
        if current_state == "Ready":
            self.demo_status_var.set("Ready for demos")
        else:
            self.demo_status_var.set(f"System: {current_state}")
            
        self.demo1_btn.configure(state="normal")
        self.demo2_btn.configure(state="normal")
        self.demo3_btn.configure(state="normal")
        self.stop_demo_btn.configure(state="disabled")

    def show_help_window(self):
        """Show comprehensive GUI help window"""
        help_window = tk.Toplevel(self.root)
        help_window.title("SOLAR- Help")
        help_window.geometry("800x600")
        help_window.configure(bg='#f0f0f0')
        
        # Create scrollable text area
        help_frame = ttk.Frame(help_window, padding="20")
        help_frame.pack(fill=tk.BOTH, expand=True)
        
        help_text = scrolledtext.ScrolledText(help_frame, height=30, width=80, wrap=tk.WORD)
        help_text.pack(fill=tk.BOTH, expand=True)
        
        # Help content
        help_content = """
        SOLAR GUI - Complete User Guide
        ========================================================
        
        🚀 WHAT THIS SYSTEM DOES:
        
        This GUI controls a smart chain of SEEEDuino XIAO controllers that can:
        • Control LED brightness on multiple devices simultaneously or individually
        • Move servo motors to precise positions (60-120 degrees)  
        • Communicate through a daisy-chain setup (like Christmas lights, but smarter!)
        • Automatically detect how many devices are connected
        • Provide visual feedback when something goes wrong
        
        Think of it as a "conductor" for an orchestra of LED arrays and servo motors!
        
        📍 HARDWARE SETUP:
        
        Pin Connections (on each XIAO board):
        • A0 = DAC Output → LED Array Control (amplified)
        • D2 = PWM Output → Servo Motor (5V logic level)
        • D1 = RX_READY ← Signal from previous device
        • D3 = TX_READY → Signal to next device
        • D6 = TX → Data to next device
        • D7 = RX ← Data from previous device
        • D10 = User LED (built-in status indicator)
        
        Chain Configuration:
        [Master Device] → [Device 2] → [Device 3] → ... → [Back to Master]
            (USB)           (12V)        (12V)
        
        🎯 DEVICE NUMBERING SYSTEM:
        
        • 000 = ALL DEVICES (Broadcast to entire chain)
        • 001 = Master Device (Connected to computer via USB)
        • 002, 003, 004... = Slave Devices (Powered externally, in daisy-chain)
        
        🎮 GUI CONTROL SECTIONS:
        
        1. SERIAL CONNECTION:
           • Port Selection: Choose your USB COM port
           • Baud Rate: Set to 115200 (matches Arduino)
           • Auto-Connect: Automatically connects to first available port
           • Refresh: Scan for new ports
        
        2. SYSTEM STATUS:
           • Connection Status: Green=Connected, Red=Disconnected
           • Total Devices: Auto-detected device count in chain
           • System State: Ready, Initializing, Processing, etc.
           • Manual Commands: Device Status, Re-initialize, Help
        
        3. DEMO PATTERNS:
           • 🕺 Simple Dance: Servo sweep + DAC flash (2 cycles)
           • 🌊 Servo Wave: Smooth servo oscillation (2 cycles)
           • 🌈 DAC Rainbow: Progressive brightness fade (2 cycles)
           • ⏹️ Stop Demo: Interrupt any running demo
        
        4. SERVO CONTROL:
           • Range: 60-120 degrees (safety limited)
           • All Servos Mode: Synchronize all devices (Disk Mode)
           • Individual Mode: Target specific device (001, 002, etc.)
           • Presets: 60°, 75°, 90°, 105°, 120°
           • Real-time Slider: Live angle adjustment
        
        5. DAC/LED CONTROL:
           • Range: 0-1500mA (safety limited, converts to 0-730 raw)
           • All LEDs Mode: Broadcast to entire chain
           • Individual Mode: Target specific device
           • Presets: 0mA, 375mA, 750mA, 1125mA, 1500mA
           • Raw Value Display: Shows actual DAC value sent
        
        6. COMMUNICATION LOG:
           • TX: Commands sent from GUI to Arduino
           • RX: Responses received from Arduino (filtered)
           • Timestamps: All communications timestamped
           • Export/Clear: Save logs or clear display
        
        🎯 COMMAND EXAMPLES:
        
        Servo Commands (GUI generates these automatically):
        • All servos to 90°: "000,servo,90"
        • Device 2 servo to 75°: "002,servo,75"
        • Device 1 servo to 120°: "001,servo,120"
        
        DAC/LED Commands (current in mA, max 1500mA):
        • All LEDs to 750mA: "000,dac,365" (50% of limit)
        • Device 3 LED to 1125mA: "003,dac,548" (75% of limit)
        • Turn off device 1 LEDs: "001,dac,0" (0mA)
        
        System Commands:
        • "status" - Check device count and system state
        • "reinit" - Restart device chain detection
        
        🔧 CONNECTION PROCESS:
        
        1. Hardware Setup:
           • Connect master device to computer via USB
           • Connect 12V power to all slave devices
           • Verify daisy-chain wiring is correct
        
        2. Software Connection:
           • Launch GUI (auto-connects to first port)
           • Or manually select COM port and click "Connect"
           • Wait 5-10 seconds for device initialization
           • Check "Total Devices" shows correct count
        
        3. Test System:
           • Click "Device Status" to verify all devices
           • Try a simple servo command (e.g., All Servos to 90°)
           • Watch for "✓ Command completed successfully"
        
        🚨 TROUBLESHOOTING:
        
        Visual Indicators on Hardware:
        • Blue LED Stuck On: Device error - press reset button on PCB
        • Orange LED Blinking: Normal state indication
        • User LED Active: When DAC output > 0
        
        Common Issues:
        
        Device Detection Problems:
        • Symptom: "Total Devices" shows 0 or wrong count
        • Solution: Click "Re-initialize" to restart detection
        • Check: Verify all devices are powered and connected
        • Verify: Physical daisy-chain connections are correct
        
        Command Not Working:
        • Check: Device count matches your hardware
        • Verify: Servo angles are within 60-120°
        • Verify: DAC current is within 0-1500mA (safety limit)
        • Check: Communication log for error messages
        • Try: "Device Status" to check system health
        
        Chain Communication Failure:
        • Symptom: Commands timeout or devices don't respond
        • Solution: Press reset button on any stuck device (blue LED on)
        • Check: All power connections and daisy-chain wiring
        • Try: Disconnect/reconnect USB and restart GUI
        
        Wrong Device Count:
        • Symptom: GUI shows wrong number of devices
        • Solution: Click "Re-initialize" in System Status
        • Check: Power all devices before connecting USB
        • Verify: No broken connections in the chain
        
        🎯 BEST PRACTICES:
        
        1. Startup Sequence:
           • Power all slave devices with 12V first
           • Then connect master device USB to computer
           • Launch GUI and wait for initialization
        
        2. Operation:
           • Always wait for "✓ Command completed successfully"
           • Use "All" modes for synchronized movements
           • Use "Individual" modes for precise control
           • Monitor communication log for issues
        
        3. Demos:
           • Demos run for 2 complete cycles automatically
           • Use "Stop Demo" to interrupt any demo
           • Demos sync with current system state
           • Perfect for testing your complete setup
        
        4. Troubleshooting:
           • Export logs before reporting issues
           • Check hardware connections first
           • Use "Re-initialize" for detection problems
           • Reset devices (button) if LEDs stuck on
        
        💡 TECHNICAL SPECIFICATIONS:
        
        • Microcontroller: SAMD21 (SEEEDuino XIAO)
        • Communication: 115200 baud, round-robin protocol
        • Servo Range: 60-120 degrees (safety limited)
        • DAC Range: 0-1500mA (safety limited, mapped to 0-730 raw values)
        • Max Chain Length: Limited by power and timing
        • Auto-Discovery: Automatic device detection
        • Error Recovery: Automatic timeout handling
        
        For advanced users: The Arduino code includes extensive
        error checking and self-recovery features. Check the
        communication log for detailed system messages.
        
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