import tkinter as tk
from tkinter import ttk
from typing import Tuple

class ColorDisplay(tk.Frame):
    """Widget to display a color with its information."""
    
    def __init__(self, parent, color_rgb: Tuple[float, float, float], 
                 color_name: str, color_info: str = "", notes: str = "",
                 width: int = 1200, height: int = 120):
        super().__init__(parent)
        
        self.color_rgb = color_rgb
        self.color_name = color_name
        self.color_info = color_info
        self.notes = notes
        
        # Calculate swatch width and text width
        swatch_width = int(width * 0.75)  # Make swatch 3/4 of frame width
        text_width = 300
        
        # Convert RGB to hex for display
        hex_color = self._rgb_to_hex(color_rgb)
        
        # Main container frame to hold everything
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # Left side - color swatch
        self.color_frame = tk.Frame(container, width=swatch_width, height=height, bg=hex_color, relief="solid", borderwidth=2)
        self.color_frame.pack(side=tk.LEFT, padx=(0, 25))
        self.color_frame.pack_propagate(False)
        
        # Right side - info frame with fixed width
        right_frame = ttk.Frame(container, width=text_width)
        right_frame.pack(side=tk.LEFT, fill=tk.Y)
        right_frame.pack_propagate(False)  # Prevent frame from expanding
        
        # Top section - name and values
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(fill=tk.X, expand=False)
        
        # Color name
        self.name_label = ttk.Label(info_frame, text=color_name, font=("Arial", 18, "bold"))
        self.name_label.pack(anchor="w", pady=(2, 5))
        
        # L*a*b* and RGB values
        if color_info:
            info_lines = color_info.split('\n')
            for line in info_lines:
                self.info_label = ttk.Label(info_frame, text=line, font=("Arial", 14))
                self.info_label.pack(anchor="w", pady=1)
    
    def _rgb_to_hex(self, rgb: Tuple[float, float, float]) -> str:
        """Convert RGB values to hex color string."""
        return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"

