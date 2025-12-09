# Build Instructions for AudioToStream

## Prerequisites

1. **Python Environment**: Ensure virtual environment is activated
2. **FFmpeg**: Download and install FFmpeg from https://ffmpeg.org/download.html

## Step 1: Install Dependencies

```powershell
pip install -r requirements.txt
```

## Step 2: Setup FFmpeg

### Option A: FFmpeg in System PATH
If FFmpeg is already in your system PATH, the spec file will auto-detect it.

### Option B: Manual FFmpeg Bundling
1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Extract `ffmpeg.exe` from the archive
3. Create a `ffmpeg` folder in this directory
4. Place `ffmpeg.exe` in the `ffmpeg` folder
5. Update `AudioToStream.spec` line 17 to:
   ```python
   datas = [('ffmpeg/ffmpeg.exe', '.')]
   ```

## Step 3: Build the Executable

```powershell
pyinstaller AudioToStream.spec
```

## Step 4: Test the Application

The executable will be created in the `dist` folder:
```powershell
.\dist\AudioToStream.exe
```

## Build Options

### One-File Distribution (Current)
- Single `.exe` file
- Slower startup (extracts to temp folder)
- Easier to distribute

### One-Folder Distribution (Alternative)
If you prefer a folder with all dependencies:
1. In `AudioToStream.spec`, replace the `EXE` section with:
```python
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AudioToStream',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AudioToStream',
)
```

## Troubleshooting

### FFmpeg Not Found Error
- Ensure FFmpeg is bundled correctly
- Check that `ffmpeg.exe` is in the same directory as the built executable
- Or ensure FFmpeg is in system PATH

### Audio Device Errors
- Install PortAudio library (included with sounddevice)
- Check Windows audio permissions

### Import Errors
- Verify all packages in `requirements.txt` are installed
- Re-run: `pip install -r requirements.txt --force-reinstall`

## Distribution

After successful build, distribute:
- `dist/AudioToStream.exe` (one-file mode)
- OR `dist/AudioToStream/` folder (one-folder mode)

Users need:
- Windows 10/11
- Audio input device
- Network connection for streaming
