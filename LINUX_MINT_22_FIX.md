# Linux Mint 22 - PIL._tkinter_finder Error Fix

## Specific Issue with Linux Mint 22

Linux Mint 22 (based on Ubuntu 24.04 LTS) has a known issue where the tkinter development packages are incomplete or have broken symlinks, causing the `PIL._tkinter_finder` error.

## Step-by-Step Fix for Linux Mint 22

### Step 1: Install Complete tkinter Support
```bash
sudo apt update
sudo apt install python3-tk python3-dev tk-dev libtk8.6-dev tcl8.6-dev
```

### Step 2: Fix Python tkinter Installation
```bash
# Remove any broken PIL installation
pip3 uninstall Pillow

# Reinstall with proper tkinter support
pip3 install Pillow==10.4.0 --no-cache-dir --force-reinstall
```

### Step 3: If Still Having Issues - Install System PIL
```bash
# Install system version of python3-pil
sudo apt install python3-pil python3-pil.imagetk

# Then reinstall user version
pip3 install --user Pillow==10.4.0 --no-cache-dir --force-reinstall
```

### Step 4: Verify Installation
Run this test script:
```bash
python3 -c "
import tkinter as tk
from PIL import Image, ImageTk
print('Testing PIL._tkinter_finder...')
try:
    from PIL import _tkinter_finder
    print('✓ PIL._tkinter_finder imported successfully')
except ImportError as e:
    print(f'✗ PIL._tkinter_finder failed: {e}')

# Test ImageTk functionality
root = tk.Tk()
root.withdraw()
test_img = Image.new('RGB', (10, 10), 'red')
photo = ImageTk.PhotoImage(test_img)
print('✓ ImageTk.PhotoImage works!')
root.destroy()
"
```

### Alternative: Use System Python Instead of pip
If the above doesn't work, try using the system Python packages:
```bash
# Remove pip-installed PIL
pip3 uninstall Pillow

# Use only system packages
sudo apt install python3-pil python3-pil.imagetk python3-numpy

# Run StampZ with system Python
python3 /path/to/StampZ/main.py
```

### For the Pre-built Executable
If using the compiled StampZ_linux-x64 executable and it still fails:

1. **Install the system tkinter packages** (Step 1 above)
2. **Set environment variables**:
   ```bash
   export TKINTER_LIBRARY=/usr/lib/python3.12/tkinter
   export TCL_LIBRARY=/usr/share/tcltk/tcl8.6
   export TK_LIBRARY=/usr/share/tcltk/tk8.6
   ./StampZ_linux-x64
   ```

### Linux Mint 22 Specific Notes
- Mint 22 uses Python 3.12 by default
- The system has both Python 3.12 and older versions
- tkinter libraries are in `/usr/lib/python3.12/tkinter/`
- Some symlinks in `/usr/include/` may be broken

### If Nothing Else Works
As a last resort, you can run StampZ from source instead of the compiled version:
```bash
# Clone the repository
git clone https://github.com/Stainlessbrown/StampZ.git
cd StampZ

# Install dependencies
pip3 install -r requirements.txt

# Run from source
python3 main.py
```

This bypasses any PyInstaller bundling issues and uses your system's Python environment directly.
