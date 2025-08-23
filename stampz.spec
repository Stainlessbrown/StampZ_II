# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

# Version for PyInstaller spec - keep this in sync with __init__.py
VERSION = '1.7.2'

# Safely collect odfpy data files and imports
try:
    datas, binaries, hiddenimports = collect_all('odfpy')
except Exception:
    datas, binaries, hiddenimports = [], [], []

# Collect matplotlib data files and imports
try:
    matplotlib_datas, matplotlib_binaries, matplotlib_hiddenimports = collect_all('matplotlib')
    datas += matplotlib_datas
    binaries += matplotlib_binaries
    hiddenimports += matplotlib_hiddenimports
except Exception:
    pass

# Collect openpyxl data files and imports
try:
    openpyxl_datas, openpyxl_binaries, openpyxl_hiddenimports = collect_all('openpyxl')
    datas += openpyxl_datas
    binaries += openpyxl_binaries
    hiddenimports += openpyxl_hiddenimports
except Exception:
    pass

# Add additional hidden imports
hiddenimports += [
    'PIL.Image',
    'PIL.ImageTk',
    'PIL._tkinter_finder',
    'PIL._imaging',
    'PIL._imagingft',
    'PIL._imagingmath',
    'PIL._imagingmorph',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageFilter',
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.simpledialog',
    'tkinter.ttk',
    '_tkinter',
    'numpy',
    'colorspacious',
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.backends.backend_tkagg',
    'pandas',
    'odf.opendocument',
    'odf.table',
    'odf.text',
    'odf.style',
    'odf.number',
    'openpyxl',
    'tifffile',
]

# Platform specific settings
if sys.platform == 'darwin':
    # macOS
    icon_path = 'StampZ_II.icns' if os.path.exists('StampZ_II.icns') else None
    onefile = False  # Use --onedir for app bundles
elif sys.platform == 'win32':
    # Windows
    icon_path = 'resources/StampZ_II_icon.ico' if os.path.exists('resources/StampZ_II_icon.ico') else None
    onefile = True
else:
    # Linux
    icon_path = None
    onefile = True

# Collect data files - only if they exist
if os.path.exists('resources'):
    datas += [('resources', 'resources')]
if os.path.exists('data'):
    datas += [('data', 'data')]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['.'],  # Look for hooks in current directory
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

if onefile:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='StampZ_II',
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
        icon=icon_path,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='StampZ_II',
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
        icon=icon_path,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='StampZ_II',
    )
    
    # macOS app bundle
    if sys.platform == 'darwin':
        app = BUNDLE(
            coll,
            name='StampZ_II.app',
            icon=icon_path,
            bundle_identifier='com.stainlessbrown.stampz_ii',
            version=VERSION,
        )
