# PyInstaller hook for PIL to ensure tkinter compatibility on Linux
# This hook ensures all necessary PIL modules are included, especially for Linux Mint 22

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all PIL submodules
hiddenimports = collect_submodules('PIL')

# Add specific modules that are often missed
hiddenimports += [
    'PIL._tkinter_finder',
    'PIL._imaging',
    'PIL._imagingft', 
    'PIL._imagingmath',
    'PIL._imagingmorph',
    'PIL._imagingcms',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageFilter',
    'PIL.ImageEnhance',
    'PIL.ImageOps',
    'PIL.ImageChops',
    'PIL.ImageStat',
    'PIL.ImageColor',
    'PIL.ImageMode',
]

# Collect data files
datas = collect_data_files('PIL')
