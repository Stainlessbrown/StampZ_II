import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List, Callable
from .coordinate_db import CoordinateDB, CoordinatePoint, SampleAreaType

class CoordinateManager:
    def __init__(self, canvas, parent: tk.Widget):
        self.canvas = canvas
        self.parent = parent
        self.db = CoordinateDB()
        self.current_coordinates: List[CoordinatePoint] = []
        self.current_set_name: Optional[str] = None
        self.current_image_path: Optional[str] = None
        
        # Share color mapping with canvas
        self.COLOR_MAP = self.canvas.COLOR_MAP
        
        # Coordinate marker configuration
        self.marker_size = 5
        self.marker_color = self.COLOR_MAP["blue"]  # Start with blue
        self.preview_color = "#FF9900"  # Orange for preview
        self.active_marker = None
        self.marker_tags = []
        self.preview_tag = "preview_marker"
        self.is_previewing = False
        
        # Sample area configuration
        self.sample_type = SampleAreaType.RECTANGLE
        self.sample_size = (20, 20)  # default size
        self.anchor_position = 'center'
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Instead of creating UI elements, we'll use the existing Sample Settings controls
        # Get references to the control panel variables
        if hasattr(self.parent, 'control_panel'):
            panel = self.parent.control_panel
            self.sample_type_var = panel.sample_controls[0]['shape']
            self.width_var = panel.sample_controls[0]['width']
            self.height_var = panel.sample_controls[0]['height']
            self.anchor_var = panel.sample_controls[0]['anchor']
            self.set_name_var = panel.sample_set_name
    
    def _on_sample_type_change(self, event):
        """Handle sample type change"""
        if self.sample_type_var.get() == 'circle':
            self.height_entry.configure(state='disabled')
            self.sample_type = SampleAreaType.CIRCLE
        else:
            self.height_entry.configure(state='normal')
            self.sample_type = SampleAreaType.RECTANGLE
    
    def show_preview(self, x: float, y: float):
        """Show preview of coordinate marker at position"""
        try:
            width = float(self.width_var.get())
            height = float(self.height_var.get()) if self.sample_type == SampleAreaType.RECTANGLE else width
            
            # Get current scale from canvas
            scale = getattr(self.canvas, 'image_scale', 1.0)
            
            # Convert dimensions to screen coordinates
            screen_width = width * scale
            screen_height = height * scale
            
            # Clear any existing preview
            self.canvas.delete(self.preview_tag)
            
            # Draw preview marker (center point)
            marker_size = 4
            self.canvas.create_oval(
                x - marker_size, y - marker_size,
                x + marker_size, y + marker_size,
                fill=self.preview_color,
                outline='white',
                width=1,
                tags=self.preview_tag
            )
            
            # Draw preview shape
            if self.sample_type == SampleAreaType.RECTANGLE:
                # Calculate position based on anchor
                if self.anchor_var.get() == 'center':
                    x1 = x - screen_width/2
                    y1 = y - screen_height/2
                    x2 = x + screen_width/2
                    y2 = y + screen_height/2
                elif self.anchor_var.get() == 'top_left':
                    x1, y1 = x, y + screen_height
                    x2, y2 = x + screen_width, y
                elif self.anchor_var.get() == 'top_right':
                    x1 = x - screen_width
                    y1 = y + screen_height
                    x2 = x
                    y2 = y
                elif self.anchor_var.get() == 'bottom_left':
                    x1 = x
                    y1 = y
                    x2 = x + screen_width
                    y2 = y + screen_height
                else:  # bottom_right
                    x1 = x - screen_width
                    y1 = y
                    x2 = x
                    y2 = y + screen_height
                
                # Draw rectangle with dashed outline
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline=self.preview_color,
                    width=2,
                    dash=(5,5),
                    tags=self.preview_tag
                )
            else:  # Circle
                radius = screen_width/2
                self.canvas.create_oval(
                    x - radius, y - radius,
                    x + radius, y + radius,
                    outline=self.preview_color,
                    width=2,
                    dash=(5,5),
                    tags=self.preview_tag
                )
            
            self.is_previewing = True
            self.canvas.update_idletasks()
            
        except ValueError:
            pass
    
    def clear_preview(self):
        """Clear the preview marker"""
        self.canvas.delete(self.preview_tag)
        self.is_previewing = False
    
    def add_coordinate(self, x: float, y: float):
        """Add a new coordinate point"""
        if len(self.current_coordinates) >= 5:
            messagebox.showwarning("Limit Reached", "Maximum 5 coordinates allowed per set")
            return
        
        try:
            width = float(self.width_var.get())
            height = float(self.height_var.get()) if self.sample_type == SampleAreaType.RECTANGLE else 0
            
            new_coord = CoordinatePoint(
                x=x,
                y=y,
                sample_type=self.sample_type,
                sample_size=(width, height),
                anchor_position=self.anchor_var.get()
            )
            
            self.current_coordinates.append(new_coord)
            self._draw_coordinate_marker(new_coord)
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values for size")
    
    def _draw_coordinate_marker(self, coord: CoordinatePoint):
        """Draw a marker for a coordinate point"""
        x, y = coord.x, coord.y
        tag = f"marker_{len(self.marker_tags)}"
        self.marker_tags.append(tag)
        
        # Draw marker point
        self.canvas.create_oval(
            x - self.marker_size, y - self.marker_size,
            x + self.marker_size, y + self.marker_size,
            fill=self.marker_color,
            tags=(tag, 'coordinate_marker')
        )
        
        # Draw sample area outline
        if coord.sample_type == SampleAreaType.RECTANGLE:
            width, height = coord.sample_size
            if coord.anchor_position == 'center':
                x1, y1 = x - width/2, y - height/2
                x2, y2 = x + width/2, y + height/2
            elif coord.anchor_position == 'top_left':
                x1, y1 = x, y + height
                x2, y2 = x + width, y
            elif coord.anchor_position == 'top_right':
                x1, y1 = x - width, y + height
                x2, y2 = x, y
            elif coord.anchor_position == 'bottom_left':
                x1, y1 = x, y
                x2, y2 = x + width, y + height
            else:  # bottom_right
                x1, y1 = x - width, y
                x2, y2 = x, y + height
            
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=self.marker_color,
                tags=(tag, 'coordinate_marker')
            )
        else:  # Circle
            radius = coord.sample_size[0]
            self.canvas.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                outline=self.marker_color,
                tags=(tag, 'coordinate_marker')
            )
    
    def set_marker_color(self, color: str):
        """Set the color for coordinate markers"""
        if color in self.COLOR_MAP:
            self.marker_color = self.COLOR_MAP[color]
            # Redraw all existing markers with new color
            self.redraw_markers()
    
    def redraw_markers(self):
        """Redraw all coordinate markers"""
        self.canvas.delete('coordinate_marker')
        self.marker_tags.clear()
        for coord in self.current_coordinates:
            self._draw_coordinate_marker(coord)
    
    def clear_coordinates(self):
        """Clear all current coordinates"""
        self.current_coordinates.clear()
        self.canvas.delete('coordinate_marker')
        self.marker_tags.clear()
    
    def set_current_image(self, image_path: str):
        """Set the current image being worked on."""
        self.current_image_path = image_path
        # Auto-suggest name based on image
        if image_path:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            self.set_name_var.set(f"{base_name}-samples")
    
    def save_current_set(self):
        """Save the current coordinate set"""
        print("DEBUG: save_current_set() called")
        name = self.set_name_var.get().strip()
        print(f"DEBUG: Template name: '{name}'")
        if not name:
            print("DEBUG: No name provided")
            messagebox.showerror("Error", "Please enter a name for the coordinate set")
            return
        
        if not self.current_coordinates:
            print("DEBUG: No coordinates to save")
            messagebox.showerror("Error", "No coordinates to save")
            return
        
        print(f"DEBUG: Number of coordinates: {len(self.current_coordinates)}")
        
        if not self.current_image_path:
            print("DEBUG: No image loaded")
            messagebox.showerror("Error", "No image loaded")
            return
        
        print(f"DEBUG: Image path: '{self.current_image_path}'")
        print(f"DEBUG: Database path: '{self.db.db_path}'")
        
        try:
            success, result = self.db.save_coordinate_set(name, self.current_image_path, self.current_coordinates)
            print(f"DEBUG: Save result: success={success}, result='{result}'")
            if success:
                messagebox.showinfo("Success", f"Coordinate set '{result}' saved successfully")
            else:
                messagebox.showerror("Error", f"Failed to save coordinate set: {result}")
        except Exception as e:
            print(f"DEBUG: Exception during save: {e}")
            messagebox.showerror("Error", f"Exception during save: {e}")
    
    def load_set(self):
        """Load a coordinate set"""
        if not self.current_image_path:
            messagebox.showerror("Error", "Please load an image first")
            return
        
        # Get sets for current image
        set_names = self.db.get_sets_for_image(self.current_image_path)
        if not set_names:
            messagebox.showinfo("No Sets", "No coordinate sets found for this image")
            return
        
        # Create dialog for set selection
        dialog = tk.Toplevel(self.parent)
        dialog.title("Load Coordinate Set")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select a coordinate set:").pack(pady=5)
        
        set_var = tk.StringVar()
        set_list = ttk.Combobox(dialog, textvariable=set_var, values=set_names, state='readonly')
        set_list.pack(pady=5, padx=10)
        
        def on_select():
            selected = set_var.get()
            if selected:
                coords = self.db.load_coordinate_set(selected)
                if coords:
                    self.clear_coordinates()
                    self.current_coordinates = coords
                    self.set_name_var.set(selected)
                    for coord in coords:
                        self._draw_coordinate_marker(coord)
                dialog.destroy()
        
        ttk.Button(dialog, text="Load", command=on_select).pack(pady=5)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)
        
        # Center dialog on parent window
        dialog.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - dialog.winfo_width()) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

