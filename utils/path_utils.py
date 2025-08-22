#!/usr/bin/env python3
"""
Unified path resolution utility for StampZ
Ensures consistent data directory paths across all modules.
"""

import os
import sys
from typing import Optional


def get_base_data_dir() -> str:
    """
    Get the base data directory for StampZ.
    Uses consistent logic across all modules.
    
    Returns:
        str: Path to the base data directory
    """
    # First check environment variable (set by packaged apps)
    stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
    if stampz_data_dir:
        return os.path.join(stampz_data_dir, "data")
    
    # Check if running in PyInstaller bundle
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle - use user data directory
        if sys.platform.startswith('linux'):
            user_data_dir = os.path.expanduser('~/.local/share/StampZ_II')
        elif sys.platform == 'darwin':
            user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ_II')
        else:  # Windows
            user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ_II')
        return os.path.join(user_data_dir, "data")
    else:
        # Running from source - use relative path
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(current_dir, "data")

def get_color_analysis_dir() -> str:
    """
    Get the color analysis database directory.
    
    Returns:
        str: Path to the color analysis directory
    """
    return os.path.join(get_base_data_dir(), "color_analysis")

def get_color_libraries_dir() -> str:
    """
    Get the color libraries directory.
    
    Returns:
        str: Path to the color libraries directory
    """
    return os.path.join(get_base_data_dir(), "color_libraries")

def ensure_data_directories() -> None:
    """
    Ensure all required data directories exist.
    """
    directories = [
        get_base_data_dir(),
        get_color_analysis_dir(),
        get_color_libraries_dir()
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"DEBUG: Ensured directory exists: {directory}")

