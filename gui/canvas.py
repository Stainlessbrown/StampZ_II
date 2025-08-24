"""
Main canvas component for the StampZ application.
Coordinates all canvas functionality through modular components.
"""

import tkinter as tk
from typing import Optional, List, Tuple, Callable
from PIL import Image
import logging
import time

from .canvas_core import CanvasCore
from .tool_manager import ToolManager, ToolMode
from .shape_manager import ShapeManager, ShapeType
from utils.geometry import Point
from utils.ruler_manager import RulerManager

# Export enums for backward compatibility
__all__ = ['CropCanvas', 'ToolMode', 'ShapeType']

logger = logging.getLogger(__name__)


class CropCanvas(tk.Canvas):
    """Main interactive canvas for image cropping operations."""
    
    # Color constants
    COLOR_MAP = {
        "blue": "#0066CC",
        "red": "#CC0000", 
        "green": "#00CC00",
        "black": "#000000",
        "white": "#FFFFFF"
    }
    
    def __init__(
        self,
        master: tk.Widget,
        status_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """Initialize the crop canvas.
        
        Args:
            master: Parent widget
            status_callback: Optional callback for status messages
            **kwargs: Additional canvas arguments
        """
        super().__init__(master, **kwargs)
        
        # Initialize coordinate database
        from utils.coordinate_db import CoordinateDB
        self.coord_db = CoordinateDB()
        
        # Initialize coordinate tracking
        self._coord_markers = []
        
        # Initialize coordinate sampling properties
        self.sample_type = 'circle'
        self.sample_width = 10
        self.sample_height = 10
        self.anchor_position = 'center'
        self.dragging_preview = False
        
        # Status callback
        self.status_callback = status_callback or (lambda _: None)
        
        # Initialize core components
        self.core = CanvasCore(self, status_callback)
        self.tool_manager = ToolManager(self, status_callback)
        self.shape_manager = ShapeManager(self, self.core, status_callback)
        
        # Initialize ruler manager
        self.ruler_manager = RulerManager(self)
        self.ruler_manager.toggle_visibility(False)  # Make rulers hidden by default
        self.ruler_manager.toggle_grid(False)  # Make grid hidden by default
        
        # Set up event bindings
        self._bind_events()
        
        # Set initial tool mode
        self.tool_manager.set_tool_mode(ToolMode.VIEW)
    
    # Property accessors for compatibility
    @property
    def original_image(self) -> Optional[Image.Image]:
        """Get the original image."""
        return self.core.original_image
    
    @property
    def image_scale(self) -> float:
        """Get the current image scale."""
        return self.core.image_scale
    
    @property
    def image_offset(self) -> Tuple[int, int]:
        """Get the current image offset."""
        return self.core.image_offset
    
    @property
    def vertices(self) -> List[Point]:
        """Get current vertices."""
        return self.shape_manager.vertices
    
    @property
    def current_tool(self) -> ToolMode:
        """Get current tool mode."""
        return self.tool_manager.current_tool
    
    @property
    def current_shape_type(self) -> ShapeType:
        """Get current shape type."""
        return self.shape_manager.current_shape_type
    
    # Public interface methods
    def load_image(self, image: Image.Image) -> None:
        """Load a new image into the canvas.
        
        Args:
            image: PIL Image to load
        """
        # Clear coordinate markers when loading new image
        self._coord_markers.clear()
        
        # Load image through core
        self.core.load_image(image)
        
        # Clear shape
        self.shape_manager.clear_shape()
        
        # Update ruler
        self.ruler_manager.set_scale(self.core.image_scale)
        self.ruler_manager.set_offset(self.core.image_offset)
        
        # Update full display
        self.update_display()
    
    def reset_view(self) -> None:
        """Reset zoom and pan to default values."""
        self.core.reset_view()
        self.shape_manager.clear_shape()
        self.update_display()
    
    def fit_to_window(self) -> None:
        """Scale and center the image to fit the current canvas dimensions."""
        # Force rulers on for precise positioning
        if not self.ruler_manager.visible:
            self.ruler_manager.toggle_visibility(True)
        ruler_size = self.ruler_manager.RULER_SIZE
        self.core.fit_to_window(ruler_size)        
        # Update ruler
        self.ruler_manager.set_scale(self.core.image_scale)
        self.ruler_manager.set_offset(self.core.image_offset)
        
        self.update_display()
    
    
    def set_tool_mode(self, mode: ToolMode) -> None:
        """Set the current tool mode.
        
        Args:
            mode: New tool mode
        """
        self.tool_manager.set_tool_mode(mode)
    
    def set_shape_type(self, shape_type: ShapeType) -> None:
        """Set the current shape type.
        
        Args:
            shape_type: New shape type
        """
        self.shape_manager.set_shape_type(shape_type)
    
    def set_line_color(self, color: str) -> None:
        """Set the line and vertex color.
        
        Args:
            color: Color name ('blue', 'red', 'green', 'black', 'white')
        """
        if color in self.COLOR_MAP:
            hex_color = self.COLOR_MAP[color]
            self.shape_manager.set_color(hex_color)
            
    
    def set_mask_alpha(self, alpha: int) -> None:
        """Set the alpha value for the mask.
        
        Args:
            alpha: Alpha value (0-255)
        """
        self.shape_manager.set_mask_alpha(alpha)  # Use direct value
    
    def set_dimensions_callback(self, callback: Callable[[int, int], None]) -> None:
        """Set callback function to call when crop dimensions change.
        
        Args:
            callback: Function to call with (width, height)
        """
        self.shape_manager.set_dimensions_callback(callback)
    
    def get_vertices(self) -> List[Point]:
        """Get the current vertex list.
        
        Returns:
            Copy of current vertices
        """
        return self.shape_manager.get_vertices()
    
    def set_max_vertices(self, count: int) -> None:
        """Set the maximum number of vertices allowed.
        
        Args:
            count: Maximum number of vertices (3-8)
        """
        self.shape_manager.set_max_vertices(count)
    
    def set_vertices(self, vertices: List[Point]) -> None:
        """Set new vertices and update display.
        
        Args:
            vertices: New vertices to set
        """
        self.shape_manager.set_vertices(vertices)
    
    def get_cropped_image(self) -> Image.Image:
        """Get the cropped version of the image based on the current selection.
        
        Returns:
            Cropped PIL Image
            
        Raises:
            ValueError: If no valid shape is defined
        """
        return self.shape_manager.get_cropped_image()
    
    def clear_image(self) -> None:
        """Clear the current image and reset canvas state."""
        # Clear core image data
        self.core.original_image = None
        self.core.display_image = None
        self.core.image_scale = 1.0
        self.core.image_offset = (0, 0)
        
        # Clear coordinate markers
        self._coord_markers.clear()
        
        # Clear shape
        self.shape_manager.clear_shape()
        
        # Clear all canvas items
        self.delete("all")
    
    def toggle_rulers(self, show: bool) -> None:
        """Toggle ruler visibility.
        
        Args:
            show: Whether to show rulers
        """
        self.ruler_manager.toggle_visibility(show)
        self.update_display()
    
    def toggle_grid(self, show: bool) -> None:
        """Toggle grid visibility.
        
        Args:
            show: Whether to show grid
        """
        self.ruler_manager.toggle_grid(show)
        self.update_display()
    
    def update_display(self) -> None:
        """Update the complete canvas display."""
        if not self.core.original_image:
            return
        
        # Update core image display
        self.core.update_display()
        
        # Always update ruler (it will clear itself if not visible)
        self.ruler_manager.draw()
        
        # Update shape display
        self.shape_manager.update_display()
        
        # Draw coordinate markers
        self._redraw_all_coordinate_markers()
        
        # Draw straightening points if in straightening mode
        if self.tool_manager.is_straightening_mode():
            self._draw_straightening_points()
    
    def _update_coordinate_display(self, screen_x: int, screen_y: int) -> None:
        """Update coordinate display with current mouse position.
        
        Args:
            screen_x, screen_y: Screen coordinates of mouse
        """
        if not self.core.original_image:
            return
        
        # Get mathematical coordinates directly (Y=0 at bottom)
        math_x, math_y = self.core.screen_to_image_coords(screen_x, screen_y)
        
        # Update coordinate display through callback if available
        if hasattr(self, 'coordinate_callback') and self.coordinate_callback:
            self.coordinate_callback(math_x, math_y)
    
    def set_coordinate_callback(self, callback: Callable[[float, float], None]) -> None:
        """Set callback for coordinate updates.
        
        Args:
            callback: Function to call with (x, y) image coordinates
        """
        self.coordinate_callback = callback
    
    # Coordinate transformation helpers
    def _image_to_screen_coords(self, image_x: float, image_y: float) -> Tuple[int, int]:
        """Convert image coordinates to screen coordinates."""
        return self.core.image_to_screen_coords(image_x, image_y)
    
    def _screen_to_image_coords(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """Convert screen coordinates to image coordinates."""
        return self.core.screen_to_image_coords(screen_x, screen_y)
    
    # Event handling
    def _bind_events(self) -> None:
        """Set up event bindings."""
        # Left click for normal operations
        self.bind('<Button-1>', self._on_click)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<ButtonRelease-1>', self._on_release)
        
        # Right click for panning (handle both Button-2 and Button-3 for cross-platform compatibility)
        self.bind('<Button-2>', self._on_pan_start)  # Right click (macOS/some systems)
        self.bind('<Button-3>', self._on_pan_start)  # Right click (Linux/Windows)
        self.bind('<B2-Motion>', self._on_pan)       # Right drag (macOS/some systems)
        self.bind('<B3-Motion>', self._on_pan)       # Right drag (Linux/Windows)
        self.bind('<ButtonRelease-2>', self._on_pan_end)  # Right release (macOS/some systems)
        self.bind('<ButtonRelease-3>', self._on_pan_end)  # Right release (Linux/Windows)
        
        # Mouse wheel for zooming
        self.bind('<MouseWheel>', self._on_zoom)
        self.bind('<Button-4>', self._on_zoom)
        self.bind('<Button-5>', self._on_zoom)
        
        # Other events
        self.bind('<Motion>', self._on_motion)
        self.bind('<Configure>', self._on_resize)
        
        # Make sure canvas can get focus for events
        self.focus_set()
    
    def _on_click(self, event: tk.Event) -> None:
        """Handle mouse click events."""
        print(f"DEBUG: Canvas click at ({event.x}, {event.y})")
        
        if not self.core.original_image:
            print("DEBUG: No original image loaded")
            return
        
        # Convert to image coordinates
        image_x, image_y = self.core.screen_to_image_coords(event.x, event.y)
        print(f"DEBUG: Image coordinates: ({image_x:.1f}, {image_y:.1f})")
        
        # Handle different tool modes (left click only)
        if self.tool_manager.is_view_mode():
            print("DEBUG: Handling view mode click")
            # Start panning
            self.core.handle_pan_start(event.x, event.y)
        
        elif self.tool_manager.is_crop_mode():
            print("DEBUG: Handling crop mode click")
            # Use normal crop mode with vertices
            self._handle_crop_click(event.x, event.y, image_x, image_y)
        
        elif self.tool_manager.is_coord_mode():
            print("DEBUG: Handling coord mode click")
            self._handle_coord_click(image_x, image_y)
        
        elif self.tool_manager.is_straightening_mode():
            print("DEBUG: Handling straightening mode click")
            self._handle_straightening_click(image_x, image_y)
        
    
    def _on_drag(self, event: tk.Event) -> None:
        """Handle mouse drag events."""
        if not self.core.original_image:
            return
        
        # Handle panning in view mode
        if self.tool_manager.is_view_mode() and self.core.panning:
            self.core.handle_pan(event.x, event.y)
            self.update_display()
        
        # Handle shape creation/editing in crop mode
        elif self.tool_manager.is_crop_mode():
            self._handle_crop_drag(event.x, event.y)
        
        # Handle coordinate sampling drag
        elif self.tool_manager.is_coord_mode() and self.tool_manager.is_dragging():
            self._handle_coord_drag(event.x, event.y)
    
    def _on_release(self, event: tk.Event) -> None:
        """Handle mouse release events."""
        # Handle coordinate sampling release
        if self.tool_manager.is_coord_mode() and self.tool_manager.is_dragging():
            self._handle_coord_release(event.x, event.y)
        
        # End any active operations
        if self.core.panning:
            self.core.handle_pan_end()
        
        # Reset all drag states
        self.tool_manager.set_dragging(False)
        self.shape_manager.active_vertex = None
        
        # Clear active marker index for coordinate tool
        if hasattr(self, '_active_marker_index'):
            self._active_marker_index = None
    
    def _on_motion(self, event: tk.Event) -> None:
        """Handle mouse motion events."""
        if not self.core.original_image:
            return
        
        # Update coordinate tracking for all modes
        self._update_coordinate_display(event.x, event.y)
        
        # Update hover states for crop mode
        if self.tool_manager.is_crop_mode():
            self._handle_crop_motion(event.x, event.y)
    
    def _on_pan_start(self, event: tk.Event) -> None:
        """Handle right-click pan start."""
        print(f"DEBUG: Right-click pan start at ({event.x}, {event.y})")
        if not self.core.original_image:
            print("DEBUG: No original image for panning")
            return
        print("DEBUG: Starting pan operation")
        self.core.handle_pan_start(event.x, event.y)
        self.configure(cursor='fleur')
    
    def _on_pan(self, event: tk.Event) -> None:
        """Handle right-click panning."""
        print(f"DEBUG: Right-click pan motion at ({event.x}, {event.y})")
        if not self.core.original_image:
            return
        if self.core.panning:
            print(f"DEBUG: Panning to ({event.x}, {event.y})")
            self.core.handle_pan(event.x, event.y)
            self.update_display()
        else:
            print("DEBUG: Panning not active")
    
    def _on_pan_end(self, event: tk.Event) -> None:
        """Handle right-click pan end."""
        print(f"DEBUG: Right-click pan end at ({event.x}, {event.y})")
        if not self.core.original_image:
            return
        print("DEBUG: Ending pan operation")
        self.core.handle_pan_end()
        self.configure(cursor='')
    
    def _on_zoom(self, event: tk.Event) -> None:
        """Handle zoom events."""
        if not self.core.original_image:
            return
            
        # Handle direct mouse wheel event
        self.core.handle_zoom(event)
        
        # Update ruler if visible
        if self.ruler_manager.visible:
            self.ruler_manager.set_scale(self.core.image_scale)
            self.ruler_manager.set_offset(self.core.image_offset)
        
        # Update zoom display in control panel if available
        if hasattr(self, 'main_app') and hasattr(self.main_app, 'control_panel'):
            self.main_app.control_panel.update_zoom_display(self.core.image_scale)
        
        # Update display
        self.update_display()
    
    def _on_resize(self, event: tk.Event) -> None:
        """Handle window resize events."""
        if self.core.original_image:
            self.update_display()
    
    # Tool-specific event handlers
    def _handle_crop_click(self, screen_x: int, screen_y: int, image_x: float, image_y: float) -> None:
        """Handle clicks in crop mode."""
        print(f"DEBUG: _handle_crop_click called with shape_type: {self.shape_manager.current_shape_type}")
        
        if self.shape_manager.current_shape_type == ShapeType.POLYGON:
            print("DEBUG: Handling polygon click")
            # Check if clicking on existing vertex
            vertex_index = self.shape_manager.find_vertex_at_point(screen_x, screen_y)
            print(f"DEBUG: Vertex index at point: {vertex_index}")
            if vertex_index is not None:
                print(f"DEBUG: Activating existing vertex {vertex_index}")
                self.shape_manager.active_vertex = vertex_index
                self.tool_manager.set_dragging(True)
            else:
                # Keep coordinates in Cartesian system (y=0 at bottom)
                image_height = self.core.original_image.height
                cartesian_y = image_height - image_y
                print(f"DEBUG: Adding new vertex at ({image_x:.1f}, {cartesian_y:.1f}) [Cartesian coords]")
                # Add new vertex
                self.shape_manager.add_vertex(image_x, cartesian_y)
                
    
    def _handle_crop_drag(self, screen_x: int, screen_y: int) -> None:
        """Handle dragging in crop mode."""
        if not self.tool_manager.is_dragging():
            return
        
        image_x, image_y = self.core.screen_to_image_coords(screen_x, screen_y)
        # Convert to Cartesian coordinates (y=0 at bottom)
        image_height = self.core.original_image.height
        cartesian_y = image_height - image_y
        
        if self.shape_manager.current_shape_type == ShapeType.POLYGON:
            if self.shape_manager.active_vertex is not None:
                self.shape_manager.move_vertex(self.shape_manager.active_vertex, image_x, cartesian_y)
        
        elif self.shape_manager.current_shape_type == ShapeType.CIRCLE:
            self.shape_manager.update_circle(image_x, image_y)
        
        elif self.shape_manager.current_shape_type == ShapeType.OVAL:
            self.shape_manager.update_oval(image_x, image_y)
    
    def _handle_crop_motion(self, screen_x: int, screen_y: int) -> None:
        """Handle mouse motion in crop mode."""
        if self.shape_manager.current_shape_type == ShapeType.POLYGON:
            # Update hover vertex
            old_hover = self.shape_manager.hover_vertex
            self.shape_manager.hover_vertex = self.shape_manager.find_vertex_at_point(screen_x, screen_y)
            
            # Update display if hover changed
            if old_hover != self.shape_manager.hover_vertex:
                self.shape_manager.update_display()
    
    def _handle_coord_click(self, image_x: float, image_y: float) -> None:
        """Handle mouse press in coordinate sampling mode - start drag operation."""
        print(f"DEBUG: Coordinate mouse press at image position: ({image_x:.1f}, {image_y:.1f}) [mathematical coords]")
        
        # First check if clicking on an existing marker (like crop vertices)
        # Convert image coords back to screen coords to use the screen-based finder
        screen_x, screen_y = self.core.image_to_screen_coords(image_x, image_y)
        marker_index = self._find_marker_at_screen_position(screen_x, screen_y)
        
        if marker_index is not None:
            print(f"DEBUG: Clicked on existing marker {marker_index}, starting drag")
            # Set up marker dragging (similar to vertex dragging)
            self._active_marker_index = marker_index
            self.tool_manager.set_dragging(True)
            
            # Update status
            marker = self._coord_markers[marker_index]
            self.status_callback(f"Dragging sample {marker.get('index', marker_index + 1)}")
            return
        
        # Get main app for access to control panel
        main_app = None
        if hasattr(self, "main_app"):
            main_app = self.main_app
        elif hasattr(self, "master") and hasattr(self.master, "master"):
            main_app = self.master.master
        
        if not main_app or not hasattr(main_app, "control_panel"):
            print("DEBUG: Cannot access control panel")
            self.status_callback("Error: Cannot access sample settings")
            return
        
        # Check if we're in manual mode
        is_manual_mode = main_app.control_panel.is_manual_mode()
        print(f"DEBUG: Is manual mode: {is_manual_mode}")
        
        if is_manual_mode:
            # Manual mode: Use the first row of sample settings
            next_sample_index = len([m for m in self._coord_markers if not m.get("is_preview", False)])
            
            print(f"DEBUG: Manual mode - using sample index {next_sample_index}")
            
            # Check 5-sample limit in manual mode
            if next_sample_index >= 5:
                print("DEBUG: Manual mode - maximum 5 samples reached")
                self.status_callback("Manual mode: Maximum 5 samples reached")
                return
            
            # In Manual Mode, use settings from the corresponding row
            settings = main_app.control_panel.get_applied_settings(next_sample_index)
            
            # Debug info
            print(f"DEBUG: Manual mode - {settings['sample_type']} {settings['width']}x{settings['height']} at {settings['anchor']}")
            
            # Create preview marker for dragging (use image_y in mathematical coordinates)
            self._coord_preview = {
                "index": next_sample_index + 1,
                "image_pos": (image_x, image_y),
                "sample_type": settings["sample_type"],
                "sample_width": settings["width"],
                "sample_height": settings["height"],
                "anchor": settings["anchor"],
                "is_preview": True,
                "tag": "coord_preview"
            }
            
            # Draw preview marker with dashed outline
            self._draw_coordinate_preview(self._coord_preview)
            
            # Set dragging state
            self.tool_manager.set_dragging(True)
            
            # Notify
            self.status_callback(f"Manual mode: Drag to position sample {self._coord_preview['index']} (release to place)")
            print(f"DEBUG: Manual mode - started dragging sample {self._coord_preview['index']} with settings {settings['sample_type']} {settings['width']}x{settings['height']}")
            return
        
        # Template mode: Use existing template-based logic
        # Find the next available sample area index
        next_sample_index = len([m for m in self._coord_markers if not m.get("is_preview", False)])
        
        print(f"DEBUG: Template mode - using sample index {next_sample_index}")
        
        # Get settings for this sample (up to 5 samples)
        if next_sample_index >= 5:
            print("DEBUG: Maximum samples reached")
            self.status_callback("Maximum 5 samples reached")
            return
        
        settings = main_app.control_panel.get_applied_settings(next_sample_index)
        
        # Check if settings are actually applied for this sample
        print(f"DEBUG: Checking if sample {next_sample_index + 1} (index {next_sample_index}) is applied")
        # TEMP: Disable Apply requirement for easier testing
        if False:  # Disabled - was: if not settings.get("is_applied", False):
            print(f"DEBUG: Sample {next_sample_index + 1} settings not applied yet")
            self.status_callback(f"Please apply settings for sample {next_sample_index + 1} first")
            return
        
        # Store preview marker for dragging (using mathematical coordinates)
        self._coord_preview = {
            "index": next_sample_index + 1,
            "image_pos": (image_x, image_y),
            "sample_type": settings["sample_type"],
            "sample_width": settings["width"],
            "sample_height": settings["height"],
            "anchor": settings["anchor"],
            "is_preview": True,
            "tag": "coord_preview"
        }
        
        # Draw preview marker with dashed outline
        self._draw_coordinate_preview(self._coord_preview)
        
        # Set dragging state
        self.tool_manager.set_dragging(True)
        
        # Notify
        self.status_callback(f"Drag to position sample {self._coord_preview['index']} (release to place)")
        print(f"DEBUG: Started dragging sample {self._coord_preview['index']} with settings {settings['sample_type']} {settings['width']}x{settings['height']}")
    
    def _handle_coord_drag(self, screen_x: int, screen_y: int) -> None:
        """Handle mouse drag in coordinate sampling mode - update preview or marker position."""
        # Convert to image coordinates (image_y in mathematical space)
        image_x, image_y = self.core.screen_to_image_coords(screen_x, screen_y)
        
        # Check if we're dragging an existing marker
        if hasattr(self, '_active_marker_index') and self._active_marker_index is not None:
            # Move existing marker directly
            self._move_marker(self._active_marker_index, image_x, image_y)
            return
        
        # Handle preview dragging (new marker creation)
        if hasattr(self, '_coord_preview'):
            # Update preview position with mathematical coordinate
            self._coord_preview["image_pos"] = (image_x, image_y)
            
            # Redraw preview at new position
            self._draw_coordinate_preview(self._coord_preview)
            
            # Update status with mathematical coordinates
            self.status_callback(f"Positioning sample {self._coord_preview['index']} at ({image_x:.1f}, {image_y:.1f}) [math coords]")
    
    def _handle_coord_release(self, screen_x: int, screen_y: int) -> None:
        """Handle mouse release in coordinate sampling mode - place the marker."""
        if not hasattr(self, '_coord_preview'):
            return
        
        print(f"DEBUG: Coordinate mouse release at screen position: ({screen_x}, {screen_y})")
        
        # Convert to image coordinates (image_y in mathematical space)
        image_x, image_y = self.core.screen_to_image_coords(screen_x, screen_y)
        
        marker = {
            "index": self._coord_preview["index"],
            "image_pos": (image_x, image_y),
            "sample_type": self._coord_preview["sample_type"],
            "sample_width": self._coord_preview["sample_width"],
            "sample_height": self._coord_preview["sample_height"],
            "anchor": self._coord_preview["anchor"],
            "is_preview": False,
            "tag": f"coord_marker_{self._coord_preview['index']}"
        }
        
        # Add to markers list
        self._coord_markers.append(marker)
        
        # Clear preview
        self.delete("coord_preview")
        
        # Draw permanent marker
        self._draw_coordinate_marker(marker)
        
        # Check if we're in manual mode and save to database
        if hasattr(self, 'main_app') and hasattr(self.main_app, 'control_panel'):
            if self.main_app.control_panel.is_manual_mode():
                # Save to database as temporary data
                from utils.coordinate_db import CoordinateDB, CoordinatePoint, SampleAreaType
                db = CoordinateDB()
                coord_point = CoordinatePoint(
                    x=image_x,
                    y=image_y,
                    sample_type=SampleAreaType.CIRCLE if marker['sample_type'].lower() == 'circle' else SampleAreaType.RECTANGLE,
                    sample_size=(float(marker['sample_width']), float(marker['sample_height'])),
                    anchor_position=marker['anchor']
                )
                db.save_manual_mode_coordinates(
                    name='manual_mode',
                    image_path=self.main_app.current_file if hasattr(self.main_app, 'current_file') else '',
                    coordinates=[coord_point]
                )
        
        # Clean up preview data
        delattr(self, '_coord_preview')
        
        # Notify
        self.status_callback(f"Placed sample {marker['index']} at ({image_x:.1f}, {image_y:.1f}) [math coords]")
        print(f"DEBUG: Placed permanent marker {marker['index']} with settings {marker['sample_type']} {marker['sample_width']}x{marker['sample_height']}")
    
    def _find_marker_at_position(self, image_x: float, image_y: float, tolerance: float = 20) -> Optional[dict]:
        """Find if there's an existing marker at the given position.
        
        Args:
            image_x, image_y: Position to check in image coordinates
            tolerance: Distance tolerance in image pixels
            
        Returns:
            Marker dict if found, None otherwise
        """
        for marker in self._coord_markers:
            if marker.get('is_preview', False):
                continue
                
            marker_x, marker_y = marker['image_pos']
            distance = ((image_x - marker_x) ** 2 + (image_y - marker_y) ** 2) ** 0.5
            
            if distance <= tolerance:
                return marker
        
        return None
    
    def _find_marker_at_screen_position(self, screen_x: int, screen_y: int) -> Optional[int]:
        """Find marker index at given screen coordinates (similar to vertex finding).
        
        Args:
            screen_x, screen_y: Screen coordinates to check
            
        Returns:
            Marker index if found, None otherwise
        """
        MARKER_GRAB_RADIUS = 15  # Slightly larger than vertex grab radius for easier selection
        
        for i, marker in enumerate(self._coord_markers):
            if marker.get('is_preview', False):
                continue
                
            # Convert marker position to screen coordinates
            marker_screen_x, marker_screen_y = self.core.image_to_screen_coords(*marker['image_pos'])
            
            # Check distance
            distance = ((screen_x - marker_screen_x) ** 2 + (screen_y - marker_screen_y) ** 2) ** 0.5
            
            if distance <= MARKER_GRAB_RADIUS:
                return i
        
        return None
    
    def _move_marker(self, marker_index: int, image_x: float, image_y: float) -> None:
        """Move a marker to new coordinates.
        
        Args:
            marker_index: Index of marker to move
            image_x, image_y: New coordinates in image space
        """
        if 0 <= marker_index < len(self._coord_markers):
            marker = self._coord_markers[marker_index]
            marker['image_pos'] = (image_x, image_y)
            
            # Redraw the marker at its new position
            self._draw_coordinate_marker(marker)
            
            # Update status
            self.status_callback(f"Moving sample {marker.get('index', marker_index + 1)} to ({image_x:.1f}, {image_y:.1f})")

    def _draw_coordinate_marker(self, marker):
        """Draw a coordinate marker on the canvas"""
        screen_x, screen_y = self.core.image_to_screen_coords(*marker["image_pos"])
        
        # Clear any existing marker with this tag
        self.delete(marker["tag"])
        
        # Get sample dimensions from marker with debug output
        sample_width = marker.get("sample_width", 10)
        sample_height = marker.get("sample_height", 10)
        sample_type = marker.get("sample_type", "circle")
        anchor = marker.get("anchor", "center")
        
        print(f"DEBUG: Drawing marker with settings: {sample_type} {sample_width}x{sample_height} {anchor}")
        print(f"DEBUG: Marker data: {marker}")
        
        # If circle, use width for both dimensions
        if sample_type == "circle":
            sample_height = sample_width
            print(f"DEBUG: Circle detected, using width {sample_width} for both dimensions")
        
        # Convert to screen coordinates - always use current scale for consistent appearance
        screen_width = sample_width * self.core.image_scale
        screen_height = sample_height * self.core.image_scale
        
        print(f"DEBUG: Screen dimensions: {screen_width}x{screen_height} (scale: {self.core.image_scale})")
        
        # Calculate bounds based on anchor
        if anchor == "center":
            x1 = screen_x - screen_width/2
            y1 = screen_y - screen_height/2
            x2 = screen_x + screen_width/2
            y2 = screen_y + screen_height/2
        elif anchor == "top_left":
            x1, y1 = screen_x, screen_y
            x2, y2 = screen_x + screen_width, screen_y + screen_height
        elif anchor == "top_right":
            x1 = screen_x - screen_width
            y1 = screen_y
            x2 = screen_x
            y2 = screen_y + screen_height
        elif anchor == "bottom_left":
            x1 = screen_x
            y1 = screen_y - screen_height
            x2 = screen_x + screen_width
            y2 = screen_y
        else:  # bottom_right
            x1 = screen_x - screen_width
            y1 = screen_y - screen_height
            x2 = screen_x
            y2 = screen_y
        
        # Draw the sample shape
        if sample_type == "circle":
            radius = screen_width/2
            self.create_oval(
                screen_x - radius, screen_y - radius,
                screen_x + radius, screen_y + radius,
                outline=self.shape_manager.current_color,
                width=2, fill="", tags=marker["tag"]
            )
        else:  # rectangle
            self.create_rectangle(
                x1, y1, x2, y2,
                outline=self.shape_manager.current_color,
                width=2, fill="", tags=marker["tag"]
            )
        
        # Draw cross marker
        size = 8
        self.create_line(
            screen_x - size, screen_y,
            screen_x + size, screen_y,
            fill=self.shape_manager.current_color, width=2, tags=marker["tag"]
        )
        self.create_line(
            screen_x, screen_y - size,
            screen_x, screen_y + size,
            fill=self.shape_manager.current_color, width=2, tags=marker["tag"]
        )
        
        # Draw sample number
        self.create_text(
            screen_x + 12, screen_y - 12,
            text=str(marker["index"]),
            fill=self.shape_manager.current_color, font=("Arial", 10, "bold"),
            tags=marker["tag"]
        )
    
    def start_marker_edit(self, marker_idx: int) -> None:
        """Start editing a specific marker."""
        if not self._coord_markers or marker_idx < 0 or marker_idx >= len(self._coord_markers):
            return
        
        print(f"DEBUG: Starting edit for marker {marker_idx}")
        
        # Get the marker to edit
        marker = self._coord_markers[marker_idx]
        if not marker:
            print("DEBUG: No marker found at index")
            return
            
        print(f"DEBUG: Found marker: {marker}")
        
        # Store marker index and original data
        self._edit_marker_index = marker_idx
        self._edit_original_marker = marker.copy()
        
        # Remove the original marker visually
        if 'tag' in marker:
            self.delete(marker['tag'])
        
        # Create preview for editing
        self._preview_data = {
            "index": marker.get('index', marker_idx + 1),
            "image_pos": marker['image_pos'],
            "sample_type": marker['sample_type'],
            "sample_width": marker['sample_width'],
            "sample_height": marker['sample_height'],
            "anchor": marker['anchor'],
            "is_preview": True,
            "tag": "coord_preview"
        }
        
        # Show preview at current position
        screen_x, screen_y = self.core.image_to_screen_coords(*marker['image_pos'])
        self._draw_coordinate_preview(self._preview_data)
        
        # Enable dragging and coordinate mode
        self.tool_manager.set_tool_mode(ToolMode.COORD)
        self.tool_manager.set_dragging(True)
        
        # Update canvas
        self.update_idletasks()
        
        print(f"DEBUG: Edit mode started for marker {marker_idx}")
        
        # Notify user
        self.status_callback(f"Editing sample {marker.get('index', marker_idx + 1)} - drag to new position")
    
    def _draw_coordinate_preview(self, marker):
        """Draw a coordinate preview marker with dashed outline"""
        screen_x, screen_y = self.core.image_to_screen_coords(*marker["image_pos"])
        
        # Clear any existing preview
        self.delete(marker["tag"])
        
        # Get sample dimensions
        sample_width = marker.get("sample_width", 10)
        sample_height = marker.get("sample_height", 10)
        sample_type = marker.get("sample_type", "circle")
        anchor = marker.get("anchor", "center")
        
        # If circle, use width for both dimensions
        if sample_type == "circle":
            sample_height = sample_width
        
        # Convert to screen coordinates
        screen_width = sample_width * self.core.image_scale
        screen_height = sample_height * self.core.image_scale
        
        # Calculate bounds based on anchor
        if anchor == "center":
            x1 = screen_x - screen_width/2
            y1 = screen_y - screen_height/2
            x2 = screen_x + screen_width/2
            y2 = screen_y + screen_height/2
        elif anchor == "top_left":
            x1, y1 = screen_x, screen_y
            x2, y2 = screen_x + screen_width, screen_y + screen_height
        elif anchor == "top_right":
            x1 = screen_x - screen_width
            y1 = screen_y
            x2 = screen_x
            y2 = screen_y + screen_height
        elif anchor == "bottom_left":
            x1 = screen_x
            y1 = screen_y - screen_height
            x2 = screen_x + screen_width
            y2 = screen_y
        else:  # bottom_right
            x1 = screen_x - screen_width
            y1 = screen_y - screen_height
            x2 = screen_x
            y2 = screen_y
        
        # Draw preview shape with dashed outline
        if sample_type == "circle":
            radius = screen_width/2
            self.create_oval(
                screen_x - radius, screen_y - radius,
                screen_x + radius, screen_y + radius,
                outline=self.shape_manager.current_color,
                width=2, fill="", dash=(5, 5), tags=marker["tag"]
            )
        else:  # rectangle
            self.create_rectangle(
                x1, y1, x2, y2,
                outline=self.shape_manager.current_color,
                width=2, fill="", dash=(5, 5), tags=marker["tag"]
            )
        
        # Draw cross marker
        size = 8
        self.create_line(
            screen_x - size, screen_y,
            screen_x + size, screen_y,
            fill=self.shape_manager.current_color, width=2, tags=marker["tag"]
        )
        self.create_line(
            screen_x, screen_y - size,
            screen_x, screen_y + size,
            fill=self.shape_manager.current_color, width=2, tags=marker["tag"]
        )
        
        # Draw sample number
        self.create_text(
            screen_x + 12, screen_y - 12,
            text=str(marker["index"]),
            fill=self.shape_manager.current_color, font=("Arial", 10, "bold"),
            tags=marker["tag"]
        )
    def _handle_straightening_click(self, image_x: float, image_y: float) -> None:
        """Handle clicks in straightening/leveling mode."""
        # Use direct reference to main app (set during initialization)
        if hasattr(self, 'main_app') and hasattr(self.main_app, 'straightening_tool'):
            straightening_tool = self.main_app.straightening_tool
            
            print(f"DEBUG: Adding point at ({image_x}, {image_y}) [screen coordinates]")
            if straightening_tool.add_reference_point(image_x, image_y):
                self.status_callback(f"Added leveling point {straightening_tool.get_point_count()}")
                self.update_display()
                
                # Update control panel
                if hasattr(self.main_app, 'control_panel'):
                    angle = straightening_tool.calculate_angle()
                    self.main_app.control_panel.update_straightening_status(
                        straightening_tool.get_point_count(), angle
                    )
    
    # Coordinate marker methods (simplified)
    def clear_coordinate_markers(self) -> None:
        """Clear all coordinate markers from the canvas and internal list."""
        # Clear visual markers from canvas
        for marker in self._coord_markers:
            if 'tag' in marker:
                self.delete(marker['tag'])
        
        # Clear the internal markers list
        self._coord_markers.clear()
        
        # Also clear any preview markers
        self.delete("coord_preview")
        self.delete("preview_marker")
        
        print("DEBUG: Cleared all coordinate markers")
    
    def draw_coordinate_markers(self) -> None:
        """Draw coordinate markers from main app coordinates."""
        if not hasattr(self, 'main_app') or not self.main_app:
            print("DEBUG: No main app reference for drawing coordinate markers")
            return
            
        if not hasattr(self.main_app, 'coordinates') or not self.main_app.coordinates:
            print("DEBUG: No coordinates available in main app")
            return
        
        print(f"DEBUG: Drawing {len(self.main_app.coordinates)} coordinate markers from main app")
        
        # Clear existing markers first
        self.clear_coordinate_markers()
        
        # Convert main app coordinates to canvas markers
        for i, coord in enumerate(self.main_app.coordinates):
            from utils.coordinate_db import SampleAreaType
            
            marker = {
                "index": i + 1,
                "image_pos": (coord.x, coord.y),
                "sample_type": "circle" if coord.sample_type == SampleAreaType.CIRCLE else "rectangle",
                "sample_width": coord.sample_size[0],
                "sample_height": coord.sample_size[1],
                "anchor": coord.anchor_position,
                "is_preview": False,
                "tag": f"coord_marker_{i + 1}"
            }
            
            # Add to internal list
            self._coord_markers.append(marker)
            
            # Draw the marker
            self._draw_coordinate_marker(marker)
            
            print(f"DEBUG: Drew marker {i + 1} at ({coord.x:.1f}, {coord.y:.1f}) type={marker['sample_type']}")
    
    def _redraw_all_coordinate_markers(self) -> None:
        """Redraw all coordinate markers with updated parameters."""
        print(f"DEBUG: _redraw_all_coordinate_markers called with {len(self._coord_markers)} markers")
        
        # Clear existing visual markers first
        for marker in self._coord_markers:
            if 'tag' in marker:
                self.delete(marker['tag'])
                print(f"DEBUG: Cleared visual marker with tag {marker['tag']}")
        
        # Redraw all markers with updated parameters
        for i, marker in enumerate(self._coord_markers):
            try:
                image_x, image_y = marker['image_pos']
                screen_x, screen_y = self.core.image_to_screen_coords(image_x, image_y)
                marker['screen_pos'] = (screen_x, screen_y)
                
                # Update tag for uniqueness
                marker['tag'] = f"coord_marker_{i + 1}_updated"
                
                # Draw the marker with updated parameters
                self._draw_coordinate_marker(marker)
                print(f"DEBUG: Redrawn marker {i + 1}: {marker['sample_type']} {marker['sample_width']}x{marker['sample_height']} at ({image_x:.1f}, {image_y:.1f})")
            except Exception as e:
                print(f"ERROR: Error redrawing marker {i}: {e}")
                import traceback
                traceback.print_exc()
    
    # Straightening visualization
    def _draw_straightening_points(self) -> None:
        """Draw visual indicators for straightening reference points."""
        if not hasattr(self, 'main_app') or not hasattr(self.main_app, 'straightening_tool'):
            return
        
        straightening_tool = self.main_app.straightening_tool
        
        # Clear existing points
        self.delete('straightening_point')
        
        # Draw each reference point (already in screen coordinates)
        for i, (image_x, image_y) in enumerate(straightening_tool.reference_points):
            # Convert to screen coordinates
            screen_x, screen_y = self.core.image_to_screen_coords(image_x, image_y)
            
            # Draw point
            point_size = 6
            self.create_oval(
                screen_x - point_size, screen_y - point_size,
                screen_x + point_size, screen_y + point_size,
                fill='#FF6600', outline='white', width=2,
                tags='straightening_point'
            )
            
            # Draw number
            self.create_text(
                screen_x + point_size + 8, screen_y - point_size - 8,
                text=str(i + 1), fill='#FF6600',
                font=('Arial', 10, 'bold'), tags='straightening_point'
            )
        
        # Draw line between points if we have 2
        if len(straightening_tool.reference_points) >= 2:
            points = []
            for image_x, image_y in straightening_tool.reference_points:
                # Convert from image to screen coordinates
                screen_x, screen_y = self.core.image_to_screen_coords(image_x, image_y)
                points.extend([screen_x, screen_y])
            
            if len(points) >= 4:
                self.create_line(
                    *points, fill='#FF6600', width=2, dash=(5, 5),
                    tags='straightening_point'
                )


    def _create_preview_marker(self, screen_x, screen_y, image_x, image_y, settings):
        """Create a preview marker that shows while dragging."""
        # Clear any existing preview
        self.delete("preview_marker")
        
        # Store preview data
        self._preview_data = {
            "image_pos": (image_x, image_y),
            "screen_pos": (screen_x, screen_y),
            "settings": settings.copy()
        }
        
        # Draw preview shape (dashed)
        self._draw_preview_shape(screen_x, screen_y, settings)

    def _draw_preview_shape(self, screen_x, screen_y, settings):
        """Draw the preview shape with dashed lines."""
        sample_width = settings.get("width", 10)
        sample_height = settings.get("height", 10)
        sample_type = settings.get("sample_type", "circle")
        anchor = settings.get("anchor", "center")
        
        # If circle, use width for both dimensions
        if sample_type == "circle":
            sample_height = sample_width
        
        # Convert to screen coordinates
        screen_width = sample_width * self.core.image_scale
        screen_height = sample_height * self.core.image_scale
        
        # Calculate bounds based on anchor
        if anchor == "center":
            x1 = screen_x - screen_width/2
            y1 = screen_y - screen_height/2
            x2 = screen_x + screen_width/2
            y2 = screen_y + screen_height/2
        else:
            # Default to center for now
            x1 = screen_x - screen_width/2
            y1 = screen_y - screen_height/2
            x2 = screen_x + screen_width/2
            y2 = screen_y + screen_height/2
        
        # Draw preview shape with dashed lines
        if sample_type == "circle":
            radius = screen_width/2
            self.create_oval(
                screen_x - radius, screen_y - radius,
                screen_x + radius, screen_y + radius,
                outline=self.shape_manager.current_color,
                width=2, dash=(4, 4), tags="preview_marker"
            )
        else:  # rectangle
            self.create_rectangle(
                x1, y1, x2, y2,
                outline=self.shape_manager.current_color,
                width=2, dash=(4, 4), tags="preview_marker"
            )
        
        # Small center dot
        self.create_oval(
            screen_x - 2, screen_y - 2,
            screen_x + 2, screen_y + 2,
            fill=self.shape_manager.current_color, tags="preview_marker"
        )


    def _place_preview_marker(self):
        """Convert preview to permanent marker on mouse release."""
        if not hasattr(self, '_preview_data'):
            return
        
        # Get data from preview
        image_x, image_y = self._preview_data["image_pos"]
        settings = self._preview_data["settings"]
        
        # Find next sample index
        next_sample_index = len([m for m in self._coord_markers if not m.get("is_preview", False)])
        
        # Create permanent marker
        marker = {
            "index": next_sample_index + 1,
            "image_pos": (image_x, image_y),
            "sample_type": settings["sample_type"],
            "sample_width": settings["width"],
            "sample_height": settings["height"],
            "anchor": settings["anchor"],
            "is_preview": False,
            "tag": f"coord_marker_{next_sample_index + 1}"
        }
        
        # Add to markers list
        self._coord_markers.append(marker)
        
        # Clear preview
        self.delete("preview_marker")
        self._preview_data = None
        
        # Draw permanent marker
        self._draw_coordinate_marker(marker)
        
        # Notify
        self.status_callback(f"Placed sample {marker['index']} at ({image_x:.1f}, {image_y:.1f})")

