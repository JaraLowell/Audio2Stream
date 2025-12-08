# -*- mode: python ; coding: utf-8 -*-
import os
import shutil

block_cipher = None

# Try to find FFmpeg in common locations
ffmpeg_path = r'ffmpeg\ffmpeg.exe'

# Prepare data files - include FFmpeg if found
datas = []
if ffmpeg_path:
    datas.append((ffmpeg_path, '.'))
    print(f"Found FFmpeg at: {ffmpeg_path}")
else:
    print("WARNING: FFmpeg not found! You'll need to bundle it manually.")
    print("Place ffmpeg.exe in the 'ffmpeg' folder and update this spec file:")
    print("  datas = [('ffmpeg/ffmpeg.exe', '.')]")

# Add Icon.ico to data files
if os.path.exists('Icon.ico'):
    datas.append(('Icon.ico', '.'))
    print("Icon.ico will be included in distribution")

a = Analysis(
    ['SteamAudio.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'sounddevice',
        '_sounddevice',
        'numpy',
        'tkinter',
        'configparser',
        'numpy.core._methods',
        'numpy.lib.format',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=['Icon.ico'],
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
