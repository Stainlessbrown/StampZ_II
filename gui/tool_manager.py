"""
Tool mode management for the StampZ application.
Handles switching between different tool modes and coordinating their behavior.
"""

from enum import Enum, auto
import tkinter as tk
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ToolMode(Enum):
    """Enumeration of available tool modes."""
    VIEW = auto()         # For panning/zooming the image
    CROP = auto()         # For creating crop shapes (includes rectangle selection)
    COORD = auto()        # For setting coordinate sample points
    STRAIGHTENING = auto() # For image straightening reference points


class ToolManager:
    """Manages tool modes and coordinates their behavior."""
    
    def __init__(self, canvas: tk.Canvas, status_callback: Optional[Callable[[str], None]] = None):
        """Initialize tool manager.
        
        Args:
            canvas: The tkinter Canvas widget
            status_callback: Optional callback for status messages
        """
        self.canvas = canvas
        self.status_callback = status_callback or (lambda _: None)
        
        # Current tool state
        self.current_tool: ToolMode = ToolMode.VIEW
        
        # Interaction states
        self.dragging: bool = False
        self.drag_mode: bool = False
        self.last_cursor: str = ''
    
    def set_tool_mode(self, mode: ToolMode) -> None:
        """Set the current tool mode.
        
        Args:
            mode: New tool mode to activate
        """
        old_mode = self.current_tool
        self.current_tool = mode
        
        # Tool mode change handled silently
        
        # Reset interaction states when switching tools
        self.dragging = False
        self.drag_mode = False
        
        # Update cursor based on mode
        if mode == ToolMode.VIEW:
            self.canvas.configure(cursor='fleur')
        elif mode in [ToolMode.CROP, ToolMode.COORD, ToolMode.STRAIGHTENING]:
            self.canvas.configure(cursor='crosshair')
        
        # Notify about mode change
        mode_names = {
            ToolMode.VIEW: "View/Pan",
            ToolMode.CROP: "Crop",
            ToolMode.COORD: "Coordinate Sampling",
            ToolMode.STRAIGHTENING: "Image Straightening"
        }
        
        if old_mode != mode:
            print(f"DEBUG: Tool mode changed from {old_mode} to {mode}")
            self.status_callback(f"Switched to {mode_names.get(mode, 'Unknown')} mode")
    
    def get_current_tool(self) -> ToolMode:
        """Get the current tool mode.
        
        Returns:
            Current tool mode
        """
        return self.current_tool
    
    def is_view_mode(self) -> bool:
        """Check if currently in view mode.
        
        Returns:
            True if in view mode
        """
        return self.current_tool == ToolMode.VIEW
    
    def is_crop_mode(self) -> bool:
        """Check if currently in crop mode.
        
        Returns:
            True if in crop mode
        """
        return self.current_tool == ToolMode.CROP
    
    def is_coord_mode(self) -> bool:
        """Check if currently in coordinate sampling mode.
        
        Returns:
            True if in coordinate sampling mode
        """
        return self.current_tool == ToolMode.COORD
    
    def is_straightening_mode(self) -> bool:
        """Check if currently in straightening mode.
        
        Returns:
            True if in straightening mode
        """
        return self.current_tool == ToolMode.STRAIGHTENING
    
    
    def set_dragging(self, dragging: bool) -> None:
        """Set the dragging state.
        
        Args:
            dragging: Whether dragging is active
        """
        self.dragging = dragging
    
    def is_dragging(self) -> bool:
        """Check if currently dragging.
        
        Returns:
            True if dragging is active
        """
        return self.dragging
    
    def set_drag_mode(self, drag_mode: bool) -> None:
        """Set the drag mode state.
        
        Args:
            drag_mode: Whether drag mode is active
        """
        self.drag_mode = drag_mode
    
    def is_drag_mode(self) -> bool:
        """Check if currently in drag mode.
        
        Returns:
            True if drag mode is active
        """
        return self.drag_mode

