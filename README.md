# Audio to Stream

A Windows application that captures audio from any input device and streams it in real-time using the SRT (Secure Reliable Transport) protocol. Perfect for streaming audio to OBS Studio or other media applications with low latency.

## Overview

**Audio to Stream** provides a simple GUI to:
- Select any audio input device (microphone, line-in, WASAPI loopback, etc.)
- Configure streaming bitrate (64k - 320k)
- Stream audio via SRT protocol with customizable URLs
- Monitor audio levels with real-time VU meters
- Track streaming statistics (bitrate, connection status, duration)

The application uses FFmpeg for encoding and streaming, with SRT protocol ensuring reliable transmission even over unreliable networks.

## Features

- 🎵 **Multiple Audio Sources**: Support for all Windows audio input devices
- 🎚️ **Adjustable Bitrate**: Choose from 64k to 320k for quality vs. bandwidth tradeoffs
- 📊 **Real-time VU Meters**: Monitor left and right channel audio levels
- 📡 **SRT Streaming**: Low-latency, reliable streaming protocol
- 💾 **Persistent Settings**: Automatically saves your configuration
- 🎨 **Dark Theme UI**: Easy on the eyes during long streaming sessions
- 📈 **Live Statistics**: View connection status, bitrate, and streaming duration

![afbeelding](https://i.gyazo.com/e4ff544f6410ac24b4294869213dfe40.png)

## Requirements

- Windows OS
- FFmpeg (bundled with the executable or available in PATH)
- Audio input device

## Build in Python v3.10.10
![Language](https://img.shields.io/badge/language-Python-blue.svg)

## Usage

### Basic Setup

1. Launch **Audio to Stream**
2. Select your audio input device from the dropdown
3. Choose your desired bitrate (192k recommended for good quality)
4. Configure the stream URL (default: `srt://localhost:9000`)
5. Click **Start Streaming**

### Stream URL Format

The default SRT URL format is:
```
srt://<ip_address>:<port>
```

For example:
- `srt://localhost:9000` - Stream locally
- `srt://192.168.1.100:9000` - Stream to another device on your network
- `srt://0.0.0.0:9000?mode=listener` - Listen mode (wait for connection)

## OBS Studio Integration

To receive the audio stream in OBS Studio, follow these steps:

### Adding an SRT Media Source

1. **Add a Media Source**
   - In OBS Studio, click the **+** button in the Sources panel
   - Select **Media Source**
   - Give it a name (e.g., "Audio Stream")
   - Click **OK**

2. **Configure the Media Source**
   - **Uncheck** "Local File"
   - In the **Input** field, enter your SRT URL with parameters:
     ```
     srt://<local_ip>:<port>?mode=listener&latency=2000000
     ```
     
     Example:
     ```
     srt://192.168.1.100:9000?mode=listener&latency=2000000
     ```
     
     Or for localhost:
     ```
     srt://127.0.0.1:9000?mode=listener&latency=2000000
     ```

3. **Set Input Format**
   - In the **Input Format** field, enter:
     ```
     mpegts
     ```

4. **Configure Network Options**
   - **Uncheck** "Buffering"
   - Set **Network Buffering** to `0` MB or uncheck the buffering option entirely
   - Set **Reconnect Delay** to `2` seconds (2000 ms)

5. **Apply Settings**
   - Click **OK** to save the media source
   - The audio should now appear in OBS

### Connection Flow

The typical setup uses:
- **Audio to Stream**: Runs in **caller** mode (connects to OBS)
- **OBS Studio**: Runs in **listener** mode (waits for the connection)

Make sure to:
1. Start **OBS Studio** first and add the media source
2. Then start streaming from **Audio to Stream**

### SRT URL Parameters Explained

- `mode=listener` - OBS waits for incoming connections (recommended for OBS side)
- `latency=2000000` - Sets latency to 2000ms (2 seconds) in microseconds. Adjust based on network conditions:
  - LAN/Local: `1000000` (1 second)
  - Stable network: `2000000` (2 seconds)
  - Unreliable network: `3000000-5000000` (3-5 seconds)

### Troubleshooting OBS Connection

**If you don't see/hear audio in OBS:**

1. **Check IP and Port**: Ensure the IP address and port match between Audio to Stream and OBS
2. **Firewall**: Windows Firewall may block SRT connections. Allow OBS through the firewall
3. **Start Order**: Start OBS's media source (listener) before starting Audio to Stream (caller)
4. **Test Locally First**: Use `127.0.0.1` or `localhost` to test on the same machine
5. **Check Audio Device**: Verify the correct audio device is selected in Audio to Stream
6. **Monitor VU Meters**: Ensure audio levels are showing in Audio to Stream
7. **Increase Latency**: If stream is choppy, try increasing the latency parameter

## Configuration File

Settings are automatically saved to `settings.ini` in the application directory:

```ini
[Settings]
audio_device = 0
bitrate = 192k
stream_url = srt://localhost:9000
```

## Technical Details

- **Encoding**: AAC audio codec
- **Container**: MPEGTS (MPEG Transport Stream)
- **Protocol**: SRT (Secure Reliable Transport)
- **Sample Rate**: 44100 Hz (configurable via FFmpeg)
- **Channels**: Stereo (2 channels)

## Building from Source

See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for details on building the executable with PyInstaller.

### Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

Required packages:
- `sounddevice` - Audio device interface
- `numpy` - Audio data processing
- `PyInstaller` - Executable building
- `pillow` - Image processing (for icon)

## License

This project is provided as-is for personal and commercial use.

## Credits

- Uses [FFmpeg](https://ffmpeg.org/) for audio encoding and streaming
- Built with Python and tkinter
- SRT protocol implementation via FFmpeg

## Support

For issues, questions, or contributions, please visit the project repository on GitHub.

---

**Note**: Ensure FFmpeg is available either bundled with the application or installed in your system PATH.
