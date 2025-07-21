"""
Ruler Manager for handling ruler display and calculations in the canvas.
"""

from typing import Tuple, Optional
import tkinter as tk


class RulerManager:
    # Display and layout constants
    RULER_SIZE = 50  # Width/height of rulers (matched to coordinate system)
    RULER_TICK_SIZE = 5  # Size of tick marks
    RULER_FONT = ('Arial', 8)
    RULER_BACKGROUND = '#f5f5f5'  # Light gray background
    RULER_GRID_COLOR = '#e0e0e0'  # Color for grid lines
    MINOR_TICK_INTERVAL = 50  # Pixels between minor ticks
    MAJOR_TICK_INTERVAL = 100  # Pixels between major ticks

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.visible = False  # Rulers hidden by default
        self.on_top = False
        self.show_grid = False  # Grid hidden by default
        self.image_scale = 1.0
        self.image_offset = (0, 0)

    def set_scale(self, scale: float) -> None:
        """Update the current scale factor."""
        self.image_scale = scale

    def set_offset(self, offset: Tuple[int, int]) -> None:
        """Update the current image offset."""
        self.image_offset = offset

    def toggle_visibility(self, show: Optional[bool] = None) -> None:
        """Toggle ruler visibility."""
        if show is not None:
            self.visible = show
        else:
            self.visible = not self.visible
        
        # If rulers are being turned off, clear them immediately
        if not self.visible:
            self.canvas.delete('ruler')
            self.canvas.delete('grid')

    def toggle_position(self, on_top: Optional[bool] = None) -> None:
        """Toggle whether rulers appear on top of the image."""
        if on_top is not None:
            self.on_top = on_top
        else:
            self.on_top = not self.on_top

    def toggle_grid(self, show: Optional[bool] = None) -> None:
        """Toggle grid visibility."""
        if show is not None:
            self.show_grid = show
        else:
            self.show_grid = not self.show_grid
        
        # If grid is being turned off, clear it immediately
        if not self.show_grid:
            self.canvas.delete('grid')

    def _calculate_tick_interval(self) -> Tuple[int, int]:
        """Calculate appropriate intervals for ruler ticks based on zoom level."""
        # Scale the base intervals
        minor = self.MINOR_TICK_INTERVAL
        major = self.MAJOR_TICK_INTERVAL

        # Adjust intervals based on zoom
        if self.image_scale < 1.0:
            # When zoomed out, increase intervals
            factor = 1.0 / self.image_scale
            if factor > 2:
                minor = minor * round(factor / 2)
                major = major * round(factor / 2)
        elif self.image_scale > 2.0:
            # When zoomed in, decrease intervals
            factor = self.image_scale
            minor = max(5, minor / round(factor))
            major = max(25, major / round(factor))

        return int(minor), int(major)

    def draw(self) -> None:
        """Draw rulers and grid on the canvas."""
        # Always clear previous rulers and grids first
        self.canvas.delete('ruler')
        self.canvas.delete('grid')
        
        if not self.visible:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Get image offset and scale from canvas
        if hasattr(self.canvas, 'core'):
            image_scale = self.canvas.image_scale
            image_offset = self.canvas.image_offset
        else:
            image_scale = 1.0
            image_offset = (0, 0)

        # Draw ruler backgrounds
        self.canvas.create_rectangle(
            self.RULER_SIZE, canvas_height - self.RULER_SIZE, 
            canvas_width, canvas_height,
            fill=self.RULER_BACKGROUND, outline='gray', tags='ruler'
        )  # Horizontal ruler at bottom
        self.canvas.create_rectangle(
            0, 0, 
            self.RULER_SIZE, canvas_height - self.RULER_SIZE,
            fill=self.RULER_BACKGROUND, outline='gray', tags='ruler'
        )  # Vertical ruler
        self.canvas.create_rectangle(
            0, canvas_height - self.RULER_SIZE, 
            self.RULER_SIZE, canvas_height,
            fill=self.RULER_BACKGROUND, outline='gray', tags='ruler'
        )  # Corner square at bottom-left

        minor_interval, major_interval = self._calculate_tick_interval()

        # Draw horizontal ruler ticks and numbers
        base_step = 50  # Base step size for minor ticks (50 pixels)
        
        # Start from left edge of ruler
        x_screen = self.RULER_SIZE
        
        # Calculate first visible tick position
        x_image = (x_screen - image_offset[0]) / image_scale
        first_tick = int(x_image / base_step) * base_step
        
        # Ensure we start at zero or the first visible tick
        if first_tick < 0:
            first_tick = 0
        
        # Convert to screen coordinates
        x_screen = image_offset[0] + (first_tick * image_scale)
        
        while x_screen < canvas_width:
            # Convert screen position to image coordinates for exact pixel value
            x_image = (x_screen - image_offset[0]) / image_scale
            pixel_value = round(x_image)
            
            # Draw tick mark
            tick_size = self.RULER_TICK_SIZE
            if pixel_value % 100 == 0:  # Major tick
                tick_size = self.RULER_TICK_SIZE + 2
                # Draw number
                self.canvas.create_text(
                    x_screen, canvas_height - self.RULER_SIZE + tick_size + 2,
                    text=str(pixel_value), anchor='n',
                    font=self.RULER_FONT, tags='ruler'
                )
            elif pixel_value % 50 == 0:  # Minor tick
                tick_size = self.RULER_TICK_SIZE
            
            # Draw tick line
            self.canvas.create_line(
                x_screen, canvas_height - self.RULER_SIZE,
                x_screen, canvas_height - self.RULER_SIZE + tick_size,
                fill='black', tags='ruler'
            )
            
            # Move to next tick position
            x_screen += (base_step * image_scale)

        # Draw vertical ruler ticks and numbers
        base_step = 50  # Base step size for minor ticks (50 pixels)
        
        if not self.canvas.original_image:
            return
            
        image_height = self.canvas.original_image.height
        
        # Calculate visible range in Cartesian coordinates  
        # Convert screen coordinates to image coordinates properly
        screen_top = 0
        screen_bottom = canvas_height - self.RULER_SIZE
        
        # Convert screen Y to image Y using the same transformation as canvas_core.py
        image_top = image_height - ((screen_top - image_offset[1]) / image_scale)
        image_bottom = image_height - ((screen_bottom - image_offset[1]) / image_scale)
        
        # Ensure we include negative values and round to nearest step
        start_y = (int(min(image_bottom, image_top) / base_step) - 1) * base_step
        end_y = (int(max(image_bottom, image_top) / base_step) + 1) * base_step

        # Draw ticks from bottom to top
        y = start_y
        while y <= end_y:
            # Convert from mathematical image coordinates to screen coordinates using canvas transformation
            # This matches the transformation in canvas_core.py image_to_screen_coords
            image_relative_y = image_height - y
            screen_relative_y = image_relative_y * image_scale
            y_screen = int(screen_relative_y + image_offset[1])
            
            if y * image_scale < 5:  # Ignore tiny scales for clarity
                y += base_step
                continue
            
            # Draw tick (on the right side of the ruler)
            self.canvas.create_line(
                self.RULER_SIZE - self.RULER_TICK_SIZE, y_screen,
                self.RULER_SIZE, y_screen,
                fill='black', tags='ruler')
            
            # Draw number for major ticks
            if y % 100 == 0:
                self.canvas.create_text(
                    self.RULER_SIZE - self.RULER_TICK_SIZE - 2, y_screen,
                    text=str(int(y)), anchor='e',
                    font=self.RULER_FONT, tags='ruler'
                )

            y += base_step

        # Draw grid if enabled
        if self.show_grid:
            self._draw_grid(canvas_width, canvas_height, minor_interval, major_interval)

    def _draw_grid(self, canvas_width: int, canvas_height: int, 
                   minor_interval: int, major_interval: int) -> None:
        """Draw the measurement grid."""
        
        # Fetch scale and offset
        image_scale = self.canvas.image_scale
        image_offset = self.canvas.image_offset
        
        if not hasattr(self.canvas, 'original_image') or not self.canvas.original_image:
            return
            
        image_height = self.canvas.original_image.height

        # Calculate grid line positions based on image coordinates
        base_step = 50  # Base step size (50 pixels)

        # Calculate visible range in image coordinates
        left_image = (self.RULER_SIZE - image_offset[0]) / image_scale
        right_image = (canvas_width - image_offset[0]) / image_scale
        
        # Convert screen coordinates to image coordinates properly for Y axis
        screen_top = 0  
        screen_bottom = canvas_height - self.RULER_SIZE
        image_top = image_height - ((screen_top - image_offset[1]) / image_scale)
        image_bottom = image_height - ((screen_bottom - image_offset[1]) / image_scale)

        # Calculate grid line positions
        start_x = (int(left_image / base_step) - 1) * base_step
        end_x = (int(right_image / base_step) + 1) * base_step
        start_y = (int(min(image_bottom, image_top) / base_step) - 1) * base_step
        end_y = (int(max(image_bottom, image_top) / base_step) + 1) * base_step

        # Draw vertical grid lines
        for x in range(start_x, end_x + base_step, base_step):
            # Convert image coordinate to screen coordinate
            x_screen = x * image_scale + image_offset[0]
            
            # Skip if outside visible area
            if x_screen < self.RULER_SIZE or x_screen > canvas_width:
                continue
                
            # Draw grid line
            self.canvas.create_line(
                x_screen, self.RULER_SIZE,
                x_screen, canvas_height - self.RULER_SIZE,
                fill=self.RULER_GRID_COLOR,
                width=2 if x % 100 == 0 else 1,
                tags='grid'
            )

        # Draw horizontal grid lines
        for y in range(start_y, end_y + base_step, base_step):
            # Convert mathematical image coordinates to screen coordinates using same method as ruler
            image_relative_y = image_height - y
            screen_relative_y = image_relative_y * image_scale
            y_screen = int(screen_relative_y + image_offset[1])
            
            # Skip if outside visible area
            if y_screen < self.RULER_SIZE or y_screen > canvas_height - self.RULER_SIZE:
                continue
                
            # Draw grid line
            self.canvas.create_line(
                self.RULER_SIZE, y_screen,
                canvas_width, y_screen,
                fill=self.RULER_GRID_COLOR,
                width=2 if y % 100 == 0 else 1,
                tags='grid'
            )
