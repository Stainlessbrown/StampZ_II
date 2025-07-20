"""Preview manager for sample area visualization."""

import tkinter as tk
from typing import Optional, Dict, Tuple, Any

class PreviewManager:
    """Manages preview visualization for sample areas."""

    def __init__(self, canvas: tk.Canvas):
        """Initialize the preview manager.
        
        Args:
            canvas: The canvas widget to draw previews on
        """
        self.canvas = canvas
        self.preview_visible = False
        self.preview_color = '#FF9900'  # Orange for better visibility
        self.preview_dash = (5, 5)      # Dashed line pattern
        self.preview_tag = 'preview_marker'

    def update_preview(self, x: int, y: int, settings: Dict[str, Any], scale: float) -> None:
        """Update the shape preview at the cursor position.
        
        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            settings: Dictionary containing shape settings (type, width, height, anchor)
            scale: Current image scale factor
        """
        # Clear any existing preview
        self.clear_preview()
        
        try:
            # Get dimensions and convert to screen coordinates
            width = float(settings['width'])
            height = float(settings['height'])
            shape_type = settings['type']
            
            # If circle, use width for both dimensions
            if shape_type == 'circle':
                height = width
            
            # Convert to screen coordinates
            screen_width = int(width * scale)
            screen_height = int(height * scale)
            
            # Draw shape preview
            if shape_type == 'rectangle':
                # Draw rectangle centered on cursor
                x1 = x - screen_width // 2
                y1 = y - screen_height // 2
                x2 = x + screen_width // 2
                y2 = y + screen_height // 2
                
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline=self.preview_color,
                    width=2,
                    dash=self.preview_dash,
                    tags=self.preview_tag
                )
            else:  # circle
                radius = screen_width // 2
                self.canvas.create_oval(
                    x - radius, y - radius,
                    x + radius, y + radius,
                    outline=self.preview_color,
                    width=2,
                    dash=self.preview_dash,
                    tags=self.preview_tag
                )
            
            # Draw center point
            marker_size = 3
            self.canvas.create_oval(
                x - marker_size, y - marker_size,
                x + marker_size, y + marker_size,
                fill=self.preview_color,
                outline='white',
                width=1,
                tags=self.preview_tag
            )
            
            # Force immediate update
            self.canvas.update_idletasks()
            self.preview_visible = True
            
        except (ValueError, KeyError) as e:
            print(f"Preview error: {e}")
            pass

    def clear_preview(self) -> None:
        """Clear the current preview."""
        self.canvas.delete(self.preview_tag)
        self.preview_visible = False

    def is_visible(self) -> bool:
        """Check if preview is currently visible."""
        return self.preview_visible

