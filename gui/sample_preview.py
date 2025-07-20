"""Sample area preview manager."""

import tkinter as tk
from typing import Dict, Any, Tuple

class SamplePreview:
    """Manages preview of sample areas while placing coordinates."""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.preview_color = '#FF3300'  # Bright orange
        self.dash_pattern = (3, 3)     # Short dashes
        self.preview_tag = 'preview_marker'
        self.is_active = False

    def show(self, x: int, y: int, settings: Dict[str, Any], scale: float) -> None:
        """Show preview at the given position with specified settings.

        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            settings: Shape settings (type, width, height, anchor)
            scale: Current image scale factor
        """
        # Clear any existing preview
        self.clear()
        
        try:
            # Get dimensions
            width = float(settings['width'])
            height = float(settings['height'])
            shape_type = settings['type']
            anchor = settings.get('anchor', 'center')
            
            # If circle, use width for both dimensions
            if shape_type == 'circle':
                height = width
            
            # Convert to screen coordinates
            screen_width = int(width * scale)
            screen_height = int(height * scale)
            
            # Draw preview shape
            if shape_type == 'rectangle':
                # Calculate bounds based on anchor
                if anchor == 'center':
                    x1 = x - screen_width/2
                    y1 = y - screen_height/2
                    x2 = x + screen_width/2
                    y2 = y + screen_height/2
                elif anchor == 'top_left':
                    x1, y1 = x, y
                    x2, y2 = x + screen_width, y + screen_height
                elif anchor == 'top_right':
                    x1 = x - screen_width
                    y1 = y
                    x2 = x
                    y2 = y + screen_height
                elif anchor == 'bottom_left':
                    x1 = x
                    y1 = y - screen_height
                    x2 = x + screen_width
                    y2 = y
                else:  # bottom_right
                    x1 = x - screen_width
                    y1 = y - screen_height
                    x2 = x
                    y2 = y
                
                # Draw preview rectangle
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline=self.preview_color,
                    width=2,
                    dash=self.dash_pattern,
                    tags=self.preview_tag
                )
            else:  # circle
                radius = screen_width/2
                self.canvas.create_oval(
                    x - radius, y - radius,
                    x + radius, y + radius,
                    outline=self.preview_color,
                    width=2,
                    dash=self.dash_pattern,
                    tags=self.preview_tag
                )
            
            # Draw center point
            marker_size = 4
            self.canvas.create_oval(
                x - marker_size, y - marker_size,
                x + marker_size, y + marker_size,
                fill=self.preview_color,
                outline='white',
                width=2,
                tags=self.preview_tag
            )
            
            # Force immediate update
            self.canvas.update()
            self.is_active = True
            
        except (ValueError, KeyError) as e:
            print(f"Preview error: {e}")
            self.clear()
    
    def clear(self) -> None:
        """Clear the current preview."""
        self.canvas.delete(self.preview_tag)
        self.is_active = False

