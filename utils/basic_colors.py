#!/usr/bin/env python3
"""
Basic colors display utility for StampZ calibration.
Shows pure reference colors that can be screenshotted for calibration.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Tuple

def show_basic_colors():
    """Show a window with basic reference colors for calibration screenshots."""
    
    # Define the 6 basic calibration colors
    colors = {
        'Red': (255, 0, 0),
        'Green': (0, 255, 0), 
        'Blue': (0, 0, 255),
        'White': (255, 255, 255),
        'Gray': (128, 128, 128),
        'Black': (0, 0, 0)
    }
    
    # Create main window
    root = tk.Toplevel()
    root.title("StampZ Basic Colors - Screenshot These for Calibration")
    root.geometry("800x600")
    root.resizable(True, True)
    
    # Instructions frame
    inst_frame = ttk.Frame(root, padding="10")
    inst_frame.pack(fill=tk.X)
    
    instructions = """
📸 CALIBRATION INSTRUCTIONS:
1. Click on each color below to display it full-screen
2. Take a screenshot of each displayed color 
3. Save screenshots with clear names (red.png, green.png, etc.)
4. Use "Create Grid from Screenshots" in calibration wizard
5. Select screenshots in this order: Red, Green, Blue, White, Gray, Black
"""
    
    ttk.Label(inst_frame, text=instructions, 
             font=('Arial', 11), justify=tk.LEFT,
             background='lightblue', relief='solid', padding="10").pack()
    
    # Colors frame
    colors_frame = ttk.Frame(root, padding="20")
    colors_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create color buttons in a 2x3 grid
    for i, (color_name, rgb) in enumerate(colors.items()):
        row = i // 3
        col = i % 3
        
        # Convert RGB to hex
        hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
        # Determine text color for contrast
        text_color = 'white' if color_name in ['Blue', 'Black'] else 'black'
        
        # Create color button
        color_button = tk.Button(
            colors_frame,
            text=f"{color_name}\nRGB{rgb}",
            bg=hex_color,
            fg=text_color,
            font=('Arial', 16, 'bold'),
            width=15,
            height=5,
            command=lambda name=color_name, rgb=rgb: _show_color_fullscreen(name, rgb)
        )
        color_button.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
        
        # Configure grid weights for expansion
        colors_frame.grid_rowconfigure(row, weight=1)
        colors_frame.grid_columnconfigure(col, weight=1)
    
    # Instructions for closing
    close_frame = ttk.Frame(root, padding="10")
    close_frame.pack(fill=tk.X)
    
    ttk.Label(close_frame, 
             text="💡 Tip: Keep this window open while taking screenshots, then close when done.",
             font=('Arial', 10, 'italic')).pack()
    
    ttk.Button(close_frame, text="Close Basic Colors", 
              command=root.destroy).pack(pady=10)

def _show_color_fullscreen(color_name: str, rgb: Tuple[int, int, int]):
    """Display a single color in fullscreen for easy screenshots."""
    
    # Create fullscreen window
    color_window = tk.Toplevel()
    color_window.title(f"Screenshot This: {color_name}")
    color_window.geometry("800x600")
    color_window.configure(bg=f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
    
    # Determine text color for visibility
    text_color = 'white' if color_name in ['Blue', 'Black'] else 'black'
    
    # Add color information text
    info_text = f"{color_name}\nRGB({rgb[0]}, {rgb[1]}, {rgb[2]})\n\n📸 Take Screenshot Now"
    
    info_label = tk.Label(
        color_window,
        text=info_text,
        bg=f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
        fg=text_color,
        font=('Arial', 24, 'bold'),
        justify=tk.CENTER
    )
    info_label.pack(expand=True)
    
    # Add close button (small, in corner)
    close_btn = tk.Button(
        color_window,
        text="✕",
        command=color_window.destroy,
        bg='gray',
        fg='white',
        font=('Arial', 12, 'bold'),
        width=3,
        height=1
    )
    close_btn.place(x=10, y=10)  # Top-left corner
    
    # Bind Escape key to close
    color_window.bind('<Escape>', lambda e: color_window.destroy())
    color_window.bind('<Button-1>', lambda e: color_window.destroy())  # Click anywhere to close

if __name__ == "__main__":
    # Test the basic colors display
    root = tk.Tk()
    root.withdraw()  # Hide main window
    show_basic_colors()
    root.mainloop()
