#!/usr/bin/env python3
"""
Test script to verify the window sizing improvements.
This script creates the main window to test the sizing calculations.
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_main_window():
    """Test the main window sizing."""
    root = tk.Tk()
    root.title("StampZ - Window Sizing Test")
    
    # Get screen dimensions (same logic as in main.py)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    print(f"Screen dimensions: {screen_width}x{screen_height}")
    
    # Calculate window size using the same logic as main.py
    if screen_height <= 768:  # Smaller screens (laptops)
        window_height = int(screen_height * 0.75)  # More conservative for small screens
    else:  # Larger screens
        window_height = int(screen_height * 0.80)  # Still conservative but allows more space
    
    # For width, we can be more generous since horizontal space is less constrained
    window_width = int(screen_width * 0.85)
    
    # Position window with some top margin to account for menu bars
    x_position = (screen_width - window_width) // 2
    y_position = max(50, (screen_height - window_height) // 2)  # At least 50px from top
    
    print(f"Calculated window size: {window_width}x{window_height}")
    print(f"Window position: +{x_position}+{y_position}")
    
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    
    # Set minimum size to ensure all UI elements can be visible
    root.minsize(1000, 650)  # Increased from 800x600 to accommodate control panel
    
    # Create a simple test interface
    frame = tk.Frame(root, bg='lightblue')
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Add labels to show dimensions
    info_label = tk.Label(frame, 
                         text=f"Screen: {screen_width}x{screen_height}\n"
                              f"Window: {window_width}x{window_height}\n"
                              f"Position: +{x_position}+{y_position}\n"
                              f"Height %: {window_height/screen_height:.1%}",
                         font=('Arial', 12),
                         bg='lightblue')
    info_label.pack(pady=20)
    
    # Add a test area at the bottom to simulate sample controls
    bottom_frame = tk.Frame(frame, bg='lightyellow', height=100)
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
    bottom_frame.pack_propagate(False)
    
    bottom_label = tk.Label(bottom_frame, 
                           text="Sample controls area (should be visible)",
                           bg='lightyellow',
                           font=('Arial', 10))
    bottom_label.pack(expand=True)
    
    # Add close button
    close_btn = tk.Button(frame, text="Close Test", command=root.quit)
    close_btn.pack(pady=10)
    
    print("Window created. Check that:")
    print("1. The entire window is visible on screen")
    print("2. The window is not cut off by dock/taskbar")
    print("3. The 'Sample controls area' at the bottom is visible")
    
    root.mainloop()

def test_preferences_window():
    """Test the preferences window sizing."""
    from gui.preferences_dialog import show_preferences_dialog
    
    root = tk.Tk()
    root.withdraw()  # Hide root window
    
    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    print(f"\nTesting Preferences Dialog on {screen_width}x{screen_height} screen")
    
    # Calculate expected dialog size (same logic as preferences_dialog.py)
    if screen_height <= 768:  # Small screens (laptops)
        expected_height = min(500, int(screen_height * 0.7))
    else:  # Larger screens
        expected_height = min(600, int(screen_height * 0.75))
    
    expected_width = min(700, int(screen_width * 0.6))
    
    print(f"Expected dialog size: {expected_width}x{expected_height}")
    print(f"Height %: {expected_height/screen_height:.1%}")
    
    try:
        result = show_preferences_dialog(root)
        print(f"Preferences dialog result: {result}")
    except Exception as e:
        print(f"Error testing preferences dialog: {e}")
    
    root.destroy()

if __name__ == "__main__":
    print("Testing StampZ window sizing improvements...")
    print("=" * 50)
    
    # Test main window
    print("Testing main window sizing...")
    test_main_window()
    
    # Test preferences window
    print("\nTesting preferences window sizing...")
    try:
        test_preferences_window()
    except Exception as e:
        print(f"Could not test preferences window: {e}")
    
    print("\nTesting complete!")
