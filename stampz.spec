# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

# Version for PyInstaller spec - keep this in sync with __init__.py
VERSION = '2.0.3'

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

# Collect seaborn data files and imports for Plot_3D
try:
    seaborn_datas, seaborn_binaries, seaborn_hiddenimports = collect_all('seaborn')
    datas += seaborn_datas
    binaries += seaborn_binaries
    hiddenimports += seaborn_hiddenimports
except Exception:
    pass

# Collect scikit-learn data files and imports for Plot_3D clustering and PCA
try:
    sklearn_datas, sklearn_binaries, sklearn_hiddenimports = collect_all('sklearn')
    datas += sklearn_datas
    binaries += sklearn_binaries
    hiddenimports += sklearn_hiddenimports
except Exception:
    pass

# Collect ezodf data files and imports for ODS file handling
try:
    ezodf_datas, ezodf_binaries, ezodf_hiddenimports = collect_all('ezodf')
    datas += ezodf_datas
    binaries += ezodf_binaries
    hiddenimports += ezodf_hiddenimports
except Exception:
    pass

# Collect lxml data files and imports for XML/HTML parsing
try:
    lxml_datas, lxml_binaries, lxml_hiddenimports = collect_all('lxml')
    datas += lxml_datas
    binaries += lxml_binaries
    hiddenimports += lxml_hiddenimports
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
    'seaborn',
    'sklearn',
    'sklearn.cluster',
    'sklearn.decomposition',
    'odf.opendocument',
    'odf.table',
    'odf.text',
    'odf.style',
    'odf.number',
    'ezodf',
    'lxml',
    'lxml.etree',
    'lxml.html',
    'openpyxl',
    'tifffile',
]

# Platform specific settings
if sys.platform == 'darwin':
    # macOS - use original StampZ icon (convert on-the-fly if needed)
    icon_path = 'resources/StampZ.ico' if os.path.exists('resources/StampZ.ico') else None
    onefile = False  # Use --onedir for app bundles
elif sys.platform == 'win32':
    # Windows - use original StampZ icon
    icon_path = 'resources/StampZ.ico' if os.path.exists('resources/StampZ.ico') else None
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

# Explicitly add templates directory to ensure Plot_3D templates are included
# This fixes the issue where Plot_3D export would fail in bundled apps due to missing template files
# The templates directory contains Plot3D_Template.ods which is required for the export functionality
if os.path.exists('data/templates'):
    datas += [('data/templates', 'data/templates')]

# Add Plot_3D configuration files (zoom presets, etc.)
if os.path.exists('plot3d/zoom_presets.json'):
    datas += [('plot3d/zoom_presets.json', 'plot3d')]

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
