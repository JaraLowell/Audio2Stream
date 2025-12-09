import sounddevice as sd
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import threading
import os
import sys
import configparser
import time

def get_ffmpeg_path():
    """Find FFmpeg executable, checking bundled location first"""
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running in a bundle - check bundle directory
        bundle_dir = sys._MEIPASS
        ffmpeg_bundled = os.path.join(bundle_dir, 'ffmpeg.exe')
        if os.path.exists(ffmpeg_bundled):
            return ffmpeg_bundled
    
    # Check in script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_local = os.path.join(script_dir, 'ffmpeg.exe')
    if os.path.exists(ffmpeg_local):
        return ffmpeg_local
    
    # Fall back to system PATH
    return 'ffmpeg'

class AudioStreamerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio to Stream")
        self.root.geometry("590x380")
        self.root.resizable(False, False)
        
        # Apply dark theme
        self.apply_dark_theme()
        
        self.ffmpeg_proc = None
        self.stderr_thread = None
        self.stream = None
        self.monitor_stream = None
        self.is_streaming = False
        self.audio_level_left = 0.0
        self.audio_level_right = 0.0
        self.smoothed_level_left = 0.0
        self.smoothed_level_right = 0.0
        self.ffmpeg_connected = False
        self.bytes_sent = 0
        self.start_time = None
        self.output_bitrate = "0kbits/s"
        self.encoded_size = 0
        self.ffmpeg_time = "00:00:00"
        self.sample_rate = 44100  # Default sample rate
        
        # Config file path
        if getattr(sys, 'frozen', False):
            # Running as executable
            self.config_path = os.path.join(os.path.dirname(sys.executable), 'settings.ini')
        else:
            # Running as script
            self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.ini')
        
        self.setup_ui()
        self.load_audio_devices()
        self.load_settings()
    
    def apply_dark_theme(self):
        """Apply a dark mode theme to the application"""
        # Dark color palette
        bg_dark = '#2b2b2b'
        bg_darker = '#1e1e1e'
        fg_color = '#e0e0e0'
        accent_color = '#007acc'
        border_color = '#3c3c3c'
        
        # Configure root window
        self.root.configure(bg=bg_dark)
        
        # Create custom style
        style = ttk.Style()
        
        # Configure TFrame
        style.configure('TFrame', background=bg_dark)
        
        # Configure TLabel
        style.configure('TLabel',
                       background=bg_dark,
                       foreground=fg_color,
                       font=('Segoe UI', 9))
        
        # Configure TButton
        style.configure('TButton',
                       background='#2b2b2b',
                       foreground='black',
                       borderwidth=1,
                       relief='raised',
                       font=('Segoe UI', 9, 'bold'),
                       padding=6)
        style.map('TButton',
                 background=[('active', '#2b2b2b'), ('pressed', '#c0c0c0'), ('disabled', '#d0d0d0')],
                 foreground=[('active', 'black'), ('pressed', 'black'), ('disabled', '#808080')])
        
        # Configure TCombobox
        style.configure('TCombobox',
                       fieldbackground='white',
                       background='white',
                       foreground='black',
                       arrowcolor='black',
                       borderwidth=1,
                       relief='solid',
                       font=('Segoe UI', 9))
        style.map('TCombobox',
                 fieldbackground=[('readonly', 'white'), ('disabled', '#f0f0f0')],
                 foreground=[('readonly', 'black'), ('disabled', '#808080')],
                 selectbackground=[('readonly', accent_color)],
                 selectforeground=[('readonly', 'white')])
        
        # Configure TEntry
        style.configure('TEntry',
                       fieldbackground='white',
                       foreground='black',
                       insertcolor='black',
                       borderwidth=1,
                       relief='solid',
                       font=('Segoe UI', 9))
        style.map('TEntry',
                 fieldbackground=[('readonly', '#f0f0f0'), ('disabled', '#f0f0f0')],
                 foreground=[('readonly', '#404040'), ('disabled', '#808080')])
        
        # Store colors for later use
        self.dark_bg = bg_dark
        self.dark_bg_darker = bg_darker
        self.dark_fg = fg_color
        self.dark_accent = accent_color
        self.dark_border = border_color
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        icon_path = os.path.join(getattr(sys, '_MEIPASS', os.path.abspath('.')), "Icon.ico")
        self.root.iconbitmap(icon_path)
        self.root.title("Audio to Stream")

        # Audio Source Selection
        ttk.Label(main_frame, text="Audio Source:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(main_frame, textvariable=self.device_var, width=50, state='readonly')
        self.device_combo.grid(row=0, column=1, pady=5, padx=5)
        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_selected)
        
        # Refresh button
        ttk.Button(main_frame, text="Refresh", command=self.load_audio_devices).grid(row=0, column=2, pady=5)
        
        # Bitrate and Sample Rate
        ttk.Label(main_frame, text="Bitrate:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.bitrate_var = tk.StringVar(value="192k")
        self.bitrate_combo = ttk.Combobox(main_frame, textvariable=self.bitrate_var, width=10, state='readonly')
        self.bitrate_combo['values'] = ('64k', '96k', '128k', '160k', '192k', '224k', '256k', '288k', '320k')
        self.bitrate_combo.current(4)  # Default to 192k
        self.bitrate_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(5, 10))
        self.bitrate_combo.bind('<<ComboboxSelected>>', lambda e: self.save_settings())
        
        # Sample Rate
        ttk.Label(main_frame, text="Sample Rate:").grid(row=1, column=1, sticky=tk.W, pady=5, padx=(120, 0))
        self.samplerate_var = tk.StringVar(value="44.1kHz")
        self.samplerate_combo = ttk.Combobox(main_frame, textvariable=self.samplerate_var, width=10, state='readonly')
        self.samplerate_combo['values'] = ('44.1kHz', '48.0kHz', '88.2kHz', '96.0kHz', '176.4kHz', '192.0kHz')
        self.samplerate_combo.current(0)  # Default to 44.1kHz
        self.samplerate_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(210, 0))
        self.samplerate_combo.bind('<<ComboboxSelected>>', lambda e: self.save_settings())
        
        # Stream URL
        ttk.Label(main_frame, text="Stream URL:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar(value="srt://localhost:9000")
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=50)
        url_entry.grid(row=2, column=1, pady=5, padx=5, columnspan=2)
        url_entry.bind('<FocusOut>', lambda e: self.save_settings())
        url_entry.bind('<Return>', lambda e: self.save_settings())
        
        # VU Meter Label
        ttk.Label(main_frame, text="Audio Levels:").grid(row=3, column=0, sticky=tk.W, pady=10)
        
        # VU Meter Frame
        vu_frame = ttk.Frame(main_frame)
        vu_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))
        
        # Left Channel
        ttk.Label(vu_frame, text="L:").pack(side=tk.LEFT, padx=5)
        self.vu_left = tk.Canvas(vu_frame, width=350, height=20, bg='#1e1e1e', highlightthickness=1, highlightbackground='#3c3c3c')
        self.vu_left.pack(side=tk.LEFT, padx=5)
        
        # Right Channel
        vu_frame2 = ttk.Frame(main_frame)
        vu_frame2.grid(row=5, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(vu_frame2, text="R:").pack(side=tk.LEFT, padx=5)
        self.vu_right = tk.Canvas(vu_frame2, width=350, height=20, bg='#1e1e1e', highlightthickness=1, highlightbackground='#3c3c3c')
        self.vu_right.pack(side=tk.LEFT, padx=5)
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=20)
        
        self.start_button = ttk.Button(button_frame, text="Start Streaming", command=self.start_streaming, width=20)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Streaming", command=self.stop_streaming, width=20, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Status Label
        self.status_var = tk.StringVar(value="Ready")
        status_label = tk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W,
                               bg='#1e1e1e', fg='#e0e0e0', font=('Segoe UI', 9))
        status_label.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # FFmpeg Stats Label
        self.stats_var = tk.StringVar(value="")
        stats_label = tk.Label(main_frame, textvariable=self.stats_var, font=('Consolas', 8, 'bold'), anchor=tk.W,
                              bg='#2b2b2b', fg='#00d700')
        stats_label.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Start VU meter update
        self.update_vu_meters()
        
    def load_audio_devices(self):
        """Load available audio input devices"""
        devices = sd.query_devices()
        self.device_list = []
        device_names = []
        
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                device_names.append(f"{idx}: {dev['name']}")
                self.device_list.append(idx)
        
        self.device_combo['values'] = device_names
        if device_names:
            self.device_combo.current(0)
    
    def save_settings(self):
        """Save current settings to INI file"""
        config = configparser.ConfigParser()
        config['Settings'] = {
            'audio_device': self.device_combo.current(),
            'bitrate': self.bitrate_var.get(),
            'stream_url': self.url_var.get(),
            'sample_rate': self.samplerate_var.get()
        }
        try:
            with open(self.config_path, 'w') as configfile:
                config.write(configfile)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def load_settings(self):
        """Load settings from INI file"""
        config = configparser.ConfigParser()
        try:
            if os.path.exists(self.config_path):
                config.read(self.config_path)
                if 'Settings' in config:
                    # Load bitrate
                    if 'bitrate' in config['Settings']:
                        bitrate = config['Settings']['bitrate']
                        self.bitrate_var.set(bitrate)
                        # Set combo box index
                        try:
                            idx = self.bitrate_combo['values'].index(bitrate)
                            self.bitrate_combo.current(idx)
                        except ValueError:
                            pass
                    
                    # Load stream URL
                    if 'stream_url' in config['Settings']:
                        self.url_var.set(config['Settings']['stream_url'])
                    
                    # Load sample rate
                    if 'sample_rate' in config['Settings']:
                        samplerate = config['Settings']['sample_rate']
                        self.samplerate_var.set(samplerate)
                        # Set combo box index
                        try:
                            idx = self.samplerate_combo['values'].index(samplerate)
                            self.samplerate_combo.current(idx)
                        except ValueError:
                            pass
                    
                    # Load audio device (after devices are loaded)
                    if 'audio_device' in config['Settings']:
                        try:
                            device_idx = int(config['Settings']['audio_device'])
                            if 0 <= device_idx < len(self.device_combo['values']):
                                self.device_combo.current(device_idx)
                                self.on_device_selected()
                        except (ValueError, tk.TclError):
                            pass
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def get_sample_rate_value(self):
        """Convert sample rate string to integer value"""
        samplerate_str = self.samplerate_var.get()
        rate_map = {
            '44.1kHz': 44100,
            '48.0kHz': 48000,
            '88.2kHz': 88200,
            '96.0kHz': 96000,
            '176.4kHz': 176400,
            '192.0kHz': 192000
        }
        return rate_map.get(samplerate_str, 44100)
    
    def on_device_selected(self, event=None):
        """Start monitoring audio when device is selected"""
        # Save settings when device changes
        if event:  # Only save if triggered by user action
            self.save_settings()
        
        # Stop existing monitor stream
        if self.monitor_stream and not self.is_streaming:
            self.monitor_stream.stop()
            self.monitor_stream.close()
            self.monitor_stream = None
        
        # Don't start monitoring if already streaming
        if self.is_streaming:
            return
        
        # Get selected device
        selected_idx = self.device_combo.current()
        if selected_idx < 0:
            return
        
        device_id = self.device_list[selected_idx]
        
        try:
            # Get selected sample rate
            sample_rate = self.get_sample_rate_value()
            
            # Start monitoring stream (VU meter only, no FFmpeg)
            self.monitor_stream = sd.InputStream(
                device=device_id,
                channels=2,
                samplerate=sample_rate,
                dtype='float32',
                callback=self.monitor_callback
            )
            self.monitor_stream.start()
            self.status_var.set(f"Monitoring audio source")
        except Exception as e:
            self.status_var.set(f"Error monitoring: {str(e)}")
    
    def monitor_callback(self, indata, frames, time, status):
        """Callback for monitoring audio (VU meter only)"""
        if status:
            print(f"Monitor callback status: {status}")
        
        # Calculate audio levels for VU meter
        if len(indata.shape) == 2:
            self.audio_level_left = np.abs(indata[:, 0]).mean()
            self.audio_level_right = np.abs(indata[:, 1]).mean()
        else:
            self.audio_level_left = np.abs(indata).mean()
            self.audio_level_right = self.audio_level_left
            
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio stream"""
        if status:
            print(f"Audio callback status: {status}")
            
        # Calculate audio levels for VU meter
        if len(indata.shape) == 2:
            self.audio_level_left = np.abs(indata[:, 0]).mean()
            self.audio_level_right = np.abs(indata[:, 1]).mean()
        else:
            self.audio_level_left = np.abs(indata).mean()
            self.audio_level_right = self.audio_level_left
            
        # Send audio to FFmpeg
        if self.ffmpeg_proc and self.ffmpeg_proc.stdin:
            try:
                data_bytes = indata.tobytes()
                self.ffmpeg_proc.stdin.write(data_bytes)
                self.ffmpeg_proc.stdin.flush()
                # Track bytes sent
                self.bytes_sent += len(data_bytes)
            except (BrokenPipeError, OSError) as e:
                print(f"FFmpeg pipe error: {e}")
                # Schedule UI update and cleanup on main thread
                self.root.after(0, self.handle_client_disconnect)

    def handle_client_disconnect(self):
        """Handle client disconnection - called from audio callback or stderr monitor"""
        # Prevent multiple simultaneous disconnect calls
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        self.status_var.set("Disconnected - Client closed connection")
        self.cleanup_stream()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.device_combo.config(state='readonly')
        self.stats_var.set("")
        # Restart monitoring
        self.on_device_selected()
    
    def monitor_ffmpeg_stderr(self):
        """Monitor FFmpeg stderr output for debugging and stats"""
        try:
            if self.ffmpeg_proc and self.ffmpeg_proc.stderr:
                # Read character by character to catch \r-separated progress updates
                buffer = b''
                while self.ffmpeg_proc.poll() is None:
                    char = self.ffmpeg_proc.stderr.read(1)
                    if not char:
                        break
                    
                    buffer += char
                    
                    # Process on newline or carriage return
                    if char in (b'\n', b'\r'):
                        if buffer.strip():
                            line_str = buffer.decode('utf-8', errors='ignore').strip()
                            
                            # Check for various connection status indicators
                            line_lower = line_str.lower()
                            if any(keyword in line_lower for keyword in ['connected', 'opening', 'stream']):
                                if 'connected' in line_lower or 'opening' in line_lower:
                                    self.ffmpeg_connected = True
                            
                            # Check for I/O errors or connection failures
                            if 'i/o error' in line_lower or 'error muxing' in line_lower or \
                               'error submitting' in line_lower or 'conversion failed' in line_lower or \
                               'error writing trailer' in line_lower or 'error closing file' in line_lower:
                                print(f"[FFMPEG ERROR] {line_str}")
                                # Only trigger disconnect once
                                if self.is_streaming:
                                    self.root.after(0, self.handle_client_disconnect)
                            elif 'error' in line_lower or 'failed' in line_lower:
                                print(f"[FFMPEG ERROR] {line_str}")

                            # Parse FFmpeg progress output - look for common patterns
                            # FFmpeg outputs: frame=... fps=... q=... size=... time=... bitrate=... speed=...
                            if ('frame=' in line_str or 'size=' in line_str or 
                                'time=' in line_str or 'bitrate=' in line_str):
                                self.parse_ffmpeg_stats(line_str)
                        
                        buffer = b''
        except Exception as e:
            print(f"Error in monitor thread: {e}")
    
    def parse_ffmpeg_stats(self, line):
        """Parse FFmpeg statistics from stderr output"""
        try:
            stats = {}
            # Remove ANSI color codes if present
            import re
            line = re.sub(r'\x1b\[[0-9;]*m', '', line)
            
            # FFmpeg format: size=     395KiB time=00:00:14.90 bitrate= 216.9kbits/s speed=1.45x
            # Use regex to extract key=value pairs more reliably
            patterns = {
                'size': r'size=\s*(\S+)',
                'time': r'elapsed=(\S+)',
                'bitrate': r'bitrate=\s*(\S+)',
                'speed': r'speed=\s*(\S+)',
                'frame': r'frame=\s*(\d+)',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, line)
                if match:
                    stats[key] = match.group(1)
            
            # Extract FFmpeg's time (format: 00:00:14.90)
            time_str = stats.get('time', None)
            if time_str:
                # Convert to HH:MM:SS format (remove milliseconds)
                if '.' in time_str:
                    time_str = time_str.split('.')[0]
                self.ffmpeg_time = time_str
            
            # Extract FFmpeg's output size and bitrate (encoded, not raw input)
            size_str = stats.get('size', '0KiB')
            bitrate_str = stats.get('bitrate', None)
            
            # Update output bitrate if available
            if bitrate_str and bitrate_str != 'N/A':
                self.output_bitrate = bitrate_str
            
            # Convert encoded size to bytes
            size_val = 0
            try:
                if 'KiB' in size_str or 'kB' in size_str:
                    size_kb = float(re.sub(r'[^\d.]', '', size_str))
                    size_val = int(size_kb * 1024)
                elif 'MiB' in size_str or 'MB' in size_str:
                    size_mb = float(re.sub(r'[^\d.]', '', size_str))
                    size_val = int(size_mb * 1024 * 1024)
                elif 'GiB' in size_str or 'GB' in size_str:
                    size_gb = float(re.sub(r'[^\d.]', '', size_str))
                    size_val = int(size_gb * 1024 * 1024 * 1024)
                elif size_str != 'N/A':
                    # Try to extract just the number
                    num_str = re.sub(r'[^\d.]', '', size_str)
                    if num_str:
                        size_val = int(float(num_str))
                
                if size_val > 0:
                    self.encoded_size = size_val
                    self.ffmpeg_connected = True
            except (ValueError, AttributeError) as e:
                print(f"[PARSE] Error converting size '{size_str}': {e}")
        except Exception as e:
            print(f"Error parsing FFmpeg stats: {e}")

    def format_bytes(self, bytes_val):
        """Format bytes into human-readable string"""
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"
                
    def start_streaming(self):
        """Start the audio streaming"""
        # Stop monitoring stream if active
        if self.monitor_stream:
            self.monitor_stream.stop()
            self.monitor_stream.close()
            self.monitor_stream = None
        
        # Get selected device
        selected_idx = self.device_combo.current()
        if selected_idx < 0:
            messagebox.showerror("Error", "Please select an audio source")
            return
            
        device_id = self.device_list[selected_idx]
        url = self.url_var.get().strip()
        bitrate = self.bitrate_var.get().strip()
        
        if not url:
            messagebox.showerror("Error", "Please enter a stream URL")
            return
            
        # Reset stats
        self.ffmpeg_connected = False
        self.bytes_sent = 0
        self.start_time = None
        
        # Start FFmpeg process with low-latency configuration
        self.stats_var.set("Initializing FFmpeg...")
        
        # Start FFmpeg process with low-latency configuration
        try:
            ffmpeg_exe = get_ffmpeg_path()
            
            # Determine if URL is SRT protocol
            url_lower = url.lower()
            is_srt = url_lower.startswith('srt://')
            
            # Get selected sample rate
            sample_rate = self.get_sample_rate_value()
            
            ffmpeg_cmd = [
                ffmpeg_exe,
                "-y",                      # Overwrite output
                "-loglevel", "info",       # Enable informational output
                "-stats",                  # Enable stats output
                "-f", "f32le",
                "-ar", str(sample_rate),
                "-ac", "2",
                "-i", "pipe:0",
                "-c:a", "aac",             # AAC encoder (software, very fast and reliable)
                "-b:a", bitrate,
                "-profile:a", "aac_low",   # Low complexity profile for faster encoding
                "-tune", "zerolatency",    # Zero latency tuning
                "-cutoff", "18000",        # High frequency cutoff reduces processing
                "-fflags", "nobuffer+flush_packets",  # No buffering, flush immediately
                "-flags", "low_delay",     # Low delay mode
                "-avoid_negative_ts", "make_zero",
                "-max_delay", "0",         # Minimize muxing delay
                "-muxdelay", "0",          # No muxing delay
                "-flush_packets", "1",     # Force packet flushing (like recording mode)
                "-write_xing", "0",        # No xing header (reduces startup delay)
                "-muxpreload", "0",        # No preload (like OBS recording mode)
                "-f", "mpegts",            # MPEG-TS for streaming compatibility
                "-mpegts_flags", "initial_discontinuity"
            ]

            # Add SRT-specific low-latency options (based on OBS SRT implementation)
            if is_srt:
                ffmpeg_cmd.extend([
                    "-pkt_size", "1316",      # Optimal packet size for SRT (7 TS packets)
                    "-latency", "50000",      # 50ms SRT latency (microseconds) - balanced for LAN
                    "-tlpktdrop", "1",        # Drop packets if too late (OBS default)
                    "-mode", "caller",        # SRT caller mode
                    "-nakreport", "1"         # Enable NAK reporting for better recovery
                ])
            
            ffmpeg_cmd.append(url)

            # Set binary mode on Windows
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
            
            self.ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=creationflags,
                bufsize=0  # Unbuffered
            )
            
            # Set stdin to binary mode on Windows
            if sys.platform == 'win32' and self.ffmpeg_proc.stdin:
                import msvcrt
                msvcrt.setmode(self.ffmpeg_proc.stdin.fileno(), os.O_BINARY)
            
            # Start stderr monitoring thread
            self.stderr_thread = threading.Thread(target=self.monitor_ffmpeg_stderr, daemon=True)
            self.stderr_thread.start()
            
            # Give FFmpeg a moment to start
            time.sleep(0.25)
            
            # Check if FFmpeg process is still running
            if self.ffmpeg_proc.poll() is not None:
                # Process died, read any error output
                error_output = self.ffmpeg_proc.stderr.read().decode('utf-8', errors='ignore')
                raise Exception(f"FFmpeg failed to start: {error_output}")
            
            # Start a timer to update stats periodically
            self.start_time = time.time()
            print(f"Starting stats updates, start_time={self.start_time}, is_streaming will be set soon")
            
            # Start audio stream
            self.stream = sd.InputStream(
                device=device_id,
                channels=2,
                samplerate=sample_rate,
                dtype='float32',
                callback=self.audio_callback
            )
            self.stream.start()
            
            self.stream.start()
            
            self.is_streaming = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.device_combo.config(state=tk.DISABLED)
            self.status_var.set(f"Streaming to {url}")
            
            # Start stats updates AFTER is_streaming is set
            self.root.after(500, self.update_stream_stats)
            print("Stream started, stats update scheduled")
            
        except Exception as e:
            self.status_var.set(f"Error starting stream: {str(e)}")
            self.cleanup_stream()

    def stop_streaming(self):
        """Stop the audio streaming"""
        self.cleanup_stream()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.device_combo.config(state='readonly')
        self.status_var.set("Stopped")
        self.stats_var.set("")
        self.is_streaming = False
        
        # Restart monitoring
        self.on_device_selected()
        
    def cleanup_stream(self):
        """Cleanup streaming resources"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        if self.monitor_stream:
            self.monitor_stream.stop()
            self.monitor_stream.close()
            self.monitor_stream = None
            
        if self.ffmpeg_proc:
            try:
                if self.ffmpeg_proc.stdin:
                    self.ffmpeg_proc.stdin.close()
                self.ffmpeg_proc.terminate()
                self.ffmpeg_proc.wait(timeout=2)
            except Exception as e:
                print(f"Error terminating FFmpeg: {e}")
                self.ffmpeg_proc.kill()
            self.ffmpeg_proc = None
        
        self.stderr_thread = None
        self.ffmpeg_connected = False
        self.bytes_sent = 0
        self.start_time = None
        self.output_bitrate = "0kbits/s"
        self.encoded_size = 0
        self.ffmpeg_time = "00:00:00"
            
    def update_stream_stats(self):
        """Update streaming statistics periodically"""
        if self.is_streaming and self.start_time:
            try:
                # Use FFmpeg's time instead of calculating locally
                time_str = self.ffmpeg_time
                
                # Use encoded size from FFmpeg if available, otherwise raw input
                display_size = self.encoded_size if self.encoded_size > 0 else self.bytes_sent
                size_display = self.format_bytes(display_size)
                
                # Use FFmpeg's bitrate if available, otherwise show selected bitrate
                if self.output_bitrate and self.output_bitrate != "0kbits/s":
                    bitrate_str = self.output_bitrate
                else:
                    # Show the target bitrate from settings
                    bitrate_str = f"{self.bitrate_var.get()}/s (target)"
                
                # Determine connection status
                if self.encoded_size > 1024 or self.bytes_sent > 100000:  # Encoded > 1KB or raw > 100KB
                    connection_status = "Connected"
                    self.ffmpeg_connected = True
                else:
                    connection_status = "Connecting..."
                
                # Update stats display
                stats_text = f"Status: {connection_status} | Sent: {size_display} | Time: {time_str} | Bitrate: {bitrate_str}"
                self.stats_var.set(stats_text)
                
                # Schedule next update - continue as long as streaming
                if self.is_streaming:
                    self.root.after(1000, self.update_stream_stats)
            except Exception as e:
                print(f"Error updating stats: {e}")
    
    def update_vu_meters(self):
        """Update VU meters display"""
        # Clear canvases
        self.vu_left.delete('all')
        self.vu_right.delete('all')
        
        # Apply smoothing - slow attack, slow decay for smoother movement
        attack_rate = 0.3  # How quickly meter rises (0-1, lower = slower)
        decay_rate = 0.5   # How quickly meter falls (0-1, lower = slower)
        
        # Smooth left channel
        if self.audio_level_left > self.smoothed_level_left:
            self.smoothed_level_left += (self.audio_level_left - self.smoothed_level_left) * attack_rate
        else:
            self.smoothed_level_left += (self.audio_level_left - self.smoothed_level_left) * decay_rate
        
        # Smooth right channel
        if self.audio_level_right > self.smoothed_level_right:
            self.smoothed_level_right += (self.audio_level_right - self.smoothed_level_right) * attack_rate
        else:
            self.smoothed_level_right += (self.audio_level_right - self.smoothed_level_right) * decay_rate
        
        # Calculate bar widths (0-350 pixels) using smoothed values
        left_width = min(int(self.smoothed_level_left * 350 * 3.1415), 350)  # Amplify for visibility
        right_width = min(int(self.smoothed_level_right * 350 * 3.1415), 350)

        # Draw bars
        if left_width > 0:
            self.vu_left.create_rectangle(0, 0, left_width, 20, fill='green', outline='')
        if right_width > 0:
            self.vu_right.create_rectangle(0, 0, right_width, 20, fill='green', outline='')
            
        # Schedule next update
        self.root.after(125, self.update_vu_meters)
        
    def on_closing(self):
        """Handle window closing"""
        if self.is_streaming:
            if messagebox.askokcancel("Quit", "Streaming is active. Do you want to stop and quit?"):
                self.save_settings()
                self.cleanup_stream()
                self.root.destroy()
        else:
            self.save_settings()
            self.root.destroy()

def main():
    root = tk.Tk()
    app = AudioStreamerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
