# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import collect_data_files

# Collect all odfpy data files and imports
datas, binaries, hiddenimports = collect_all('odfpy')

# Add additional hidden imports
hiddenimports += [
    'PIL._tkinter_finder',
    'PIL.Image',
    'PIL.ImageTk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.simpledialog',
    'tkinter.ttk',
    'numpy',
    'colorspacious',
    'odf.opendocument',
    'odf.table',
    'odf.text',
    'odf.style',
    'odf.number',
]

# Platform specific settings
if sys.platform == 'darwin':
    # macOS
    icon = 'StampZ.icns'
    onefile = False  # Use --onedir for app bundles
    windowed = True
elif sys.platform == 'win32':
    # Windows
    icon = 'resources/StampZ.ico'
    onefile = True
    windowed = True
else:
    # Linux
    icon = None
    onefile = True
    windowed = True

# Collect data files
datas += [
    ('resources', 'resources'),
    ('data', 'data'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

if onefile:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='StampZ',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='StampZ',
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
        icon=icon,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='StampZ',
    )
    
    # macOS app bundle
    if sys.platform == 'darwin':
        app = BUNDLE(
            coll,
            name='StampZ.app',
            icon=icon,
            bundle_identifier='com.stainlessbrown.stampz',
            version='1.53',
        )
