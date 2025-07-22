"""
Core canvas functionality for the StampZ application.
Handles basic image display, pan, zoom, and coordinate transformations.
"""

import tkinter as tk
from typing import Optional, Tuple, Callable
from PIL import Image, ImageTk
import logging

logger = logging.getLogger(__name__)


class CanvasCore:
    """Core canvas functionality for image display and basic operations."""
    
    def __init__(self, canvas: tk.Canvas, status_callback: Optional[Callable[[str], None]] = None):
        """Initialize core canvas functionality.
        
        Args:
            canvas: The tkinter Canvas widget
            status_callback: Optional callback for status messages
        """
        self.canvas = canvas
        self.status_callback = status_callback or (lambda _: None)
        
        # Image management
        self.original_image: Optional[Image.Image] = None
        self.display_image: Optional[ImageTk.PhotoImage] = None
        self.image_scale: float = 1.0
        self.image_offset: Tuple[int, int] = (0, 0)
        
        # Pan state
        self.panning: bool = False
        self.pan_start: Optional[Tuple[int, int]] = None
    
    def load_image(self, image: Image.Image) -> None:
        """Load a new image into the canvas.
        
        Args:
            image: PIL Image to load
        """
        self.original_image = image
        self.display_image = None
        
        # Reset view state
        self.image_scale = 1.0
        self.image_offset = (0, 0)
        
        # Clear canvas
        self.canvas.delete('all')
        
        # Force geometry update
        self.canvas.update()
        self.canvas.update_idletasks()
        
        self.update_display()
    
    def reset_view(self) -> None:
        """Reset zoom and pan to default values."""
        self.image_scale = 1.0
        self.image_offset = (0, 0)
        self.update_display()
    
    def fit_to_window(self, ruler_size: int = 0) -> None:
        """Scale and center the image to fit the current canvas dimensions.
        
        Args:
            ruler_size: Size of ruler area to account for
        """
        if not self.original_image:
            return
        
        # Clear display
        self.canvas.delete('all')
        self.display_image = None
        
        # Force geometry update
        self.canvas.update()
        self.canvas.update_idletasks()
        
        # Get dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        image_width = self.original_image.width
        image_height = self.original_image.height
        
        # Account for ruler space
        canvas_width -= ruler_size * 2
        canvas_height -= ruler_size * 2
        
        # Calculate scale with padding
        padding = 20
        usable_width = max(1, canvas_width - padding)
        usable_height = max(1, canvas_height - padding)
        
        width_scale = usable_width / float(image_width)
        height_scale = usable_height / float(image_height)
        
        self.image_scale = min(width_scale, height_scale)
        self.image_scale = round(self.image_scale, 6)
        
        # Calculate scaled dimensions and center
        scaled_width = image_width * self.image_scale
        scaled_height = image_height * self.image_scale
        
        self.image_offset = (
            int((canvas_width - scaled_width) / 2) + ruler_size,
            int((canvas_height - scaled_height) / 2) + ruler_size
        )
        
        self.update_display()
    
    
    def handle_pan_start(self, x: int, y: int) -> None:
        """Start panning operation.
        
        Args:
            x, y: Mouse coordinates
        """
        self.panning = True
        self.pan_start = (x - self.image_offset[0], y - self.image_offset[1])
        self.canvas.configure(cursor='fleur')
    
    def handle_pan(self, x: int, y: int) -> None:
        """Handle panning during drag.
        
        Args:
            x, y: Current mouse coordinates
        """
        if self.panning and self.pan_start:
            self.image_offset = (x - self.pan_start[0], y - self.pan_start[1])
            self.update_display()
    
    def handle_pan_end(self) -> None:
        """End panning operation."""
        self.panning = False
        self.pan_start = None
        self.canvas.configure(cursor='')
    
    def handle_zoom(self, event: tk.Event, zoom_factor: float = None) -> None:
        """Handle zoom events.
        
        Args:
            event: Mouse wheel event
            zoom_factor: Optional explicit zoom factor
        """
        if not self.original_image:
            return
        
        # Determine zoom direction and factor
        if zoom_factor is not None:
            factor = 1.1 if zoom_factor > 0 else 0.9
        else:
            # Use event information
            if event.num == 4 or event.delta > 0:  # Zoom in
                factor = 1.1
            else:  # Zoom out
                factor = 0.9
        
        new_scale = self.image_scale * factor
        
        # Limit zoom range (0.1x to 10x for high DPI)
        if 0.1 <= new_scale <= 10.0:
            # Get mouse position relative to image
            mouse_x = event.x - self.image_offset[0]
            mouse_y = event.y - self.image_offset[1]
            
            self.image_scale = new_scale
            
            # Adjust offset to zoom toward mouse position
            self.image_offset = (
                event.x - mouse_x * factor,
                event.y - mouse_y * factor
            )
            
            self.update_display()
    
    def set_zoom_level(self, zoom_level: float) -> None:
        """Set specific zoom level.
        
        Args:
            zoom_level: Zoom level (0.1 to 10.0)
        """
        if not self.original_image:
            return
        
        # Clamp zoom level to valid range
        zoom_level = max(0.1, min(10.0, zoom_level))
        
        # Get center of canvas for zoom center point
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        
        # Calculate zoom factor
        factor = zoom_level / self.image_scale
        
        # Get center position relative to image
        image_center_x = center_x - self.image_offset[0]
        image_center_y = center_y - self.image_offset[1]
        
        # Update scale
        self.image_scale = zoom_level
        
        # Adjust offset to zoom toward center
        self.image_offset = (
            center_x - image_center_x * factor,
            center_y - image_center_y * factor
        )
        
        self.update_display()
    
    def image_to_screen_coords(self, image_x: float, image_y: float) -> Tuple[int, int]:
        """Convert image coordinates to screen coordinates.
        
        Args:
            image_x, image_y: Coordinates in mathematical coordinate space (origin at bottom-left)
            
        Returns:
            Screen coordinates as (x, y) tuple
        """
        if not self.original_image:
            return 0, 0
            
        # X coordinate: scale and offset
        screen_x = int(image_x * self.image_scale + self.image_offset[0])
        
        # Y coordinate: convert from mathematical space (bottom-left) to screen space (top-left)
        # 1. Invert relative to image height to make 0 at top
        image_relative_y = self.original_image.height - image_y
        # 2. Scale to screen coordinates
        screen_relative_y = image_relative_y * self.image_scale
        # Add offset (consider grid visibility and adjust)
        screen_y = int(screen_relative_y + self.image_offset[1])
        
        return screen_x, screen_y
    
    def screen_to_image_coords(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """Convert screen coordinates to image coordinates.
        
        Args:
            screen_x, screen_y: Coordinates in screen space
            
        Returns:
            Image coordinates as (x, y) tuple in mathematical coordinate space (origin at bottom-left)
        """
        if not self.original_image:
            return 0, 0
            
        # X coordinate: compensate for ruler offset and scale
        image_x = (screen_x - self.image_offset[0]) / self.image_scale
        
        # Y coordinate: convert from screen space (top-left) to mathematical space (bottom-left)
        # Convert directly to image coordinates
        screen_relative_y = screen_y
        # Convert to image scale
        image_relative_y = (screen_relative_y - self.image_offset[1]) / self.image_scale
        # Invert relative to image height to make 0 at bottom
        image_y = self.original_image.height - image_relative_y
        
        return image_x, image_y
    
    def update_display(self) -> None:
        """Update the image display on canvas."""
        if not self.original_image:
            return
        
        try:
            # Calculate display size
            display_width = int(self.original_image.width * self.image_scale)
            display_height = int(self.original_image.height * self.image_scale)
            
            # Skip if size is too small
            if display_width < 1 or display_height < 1:
                return
            
            # Resize image for display
            resized_image = self.original_image.resize(
                (display_width, display_height),
                Image.Resampling.LANCZOS
            )
            
            # Convert to PhotoImage
            self.display_image = ImageTk.PhotoImage(resized_image)
            
            # Clear previous image
            self.canvas.delete('image')
            
            # Draw new image
            self.canvas.create_image(
                self.image_offset[0], self.image_offset[1],
                anchor=tk.NW,
                image=self.display_image,
                tags='image'
            )
            
            # Ensure image is at the back
            self.canvas.tag_lower('image')
            
        except Exception as e:
            logger.error(f"Error updating display: {e}")
