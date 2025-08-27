import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib
from matplotlib.backend_bases import MouseEvent
import json
import os

class ZoomControls(tk.LabelFrame):
    """
    Custom zoom controls for precise 3D plot zooming.
    
    This class implements a UI panel with controls for precise zoom operations,
    including input fields for specific zoom levels, center point selection,
    and preset zoom functions.
    """
    
    def __init__(self, parent, figure, canvas, ax, on_zoom_change=None):
        """
        Initialize the ZoomControls widget.
        
        Args:
            parent: Parent widget
            figure: Matplotlib figure instance
            canvas: FigureCanvasTkAgg instance
            ax: The 3D axes to control
            on_zoom_change: Callback function when zoom changes
        """
        super().__init__(parent, text="View State Controls", font=('Arial', 9, 'bold'))
        self.parent = parent
        self.figure = figure
        self.canvas = canvas
        self.ax = ax
        self.on_zoom_change = on_zoom_change
        
        # Track the current zoom state
        self.current_xlim = None
        self.current_ylim = None
        self.current_zlim = None
        self.saved_states = {}
        
        # Path for storing zoom presets
        self.presets_file = os.path.join(os.path.dirname(__file__), 'zoom_presets.json')
        
        # Variables for storing center point (rounded to 2 decimal places)
        self.center_x = tk.DoubleVar(value=0.50)
        self.center_y = tk.DoubleVar(value=0.50)
        self.center_z = tk.DoubleVar(value=0.50)
        
        # Add trace to ensure coordinates are always rounded to 2 decimal places
        self.center_x.trace_add("write", self._validate_and_round_coordinate)
        self.center_y.trace_add("write", self._validate_and_round_coordinate)
        self.center_z.trace_add("write", self._validate_and_round_coordinate)
        
        # Zoom scale factor (1.0 = 100%)
        self.zoom_factor = tk.DoubleVar(value=1.0)
        
        # Initialize UI components
        self._create_controls()
        
        # Load any saved presets from file
        self.load_presets_from_file()
        
        # Store initial limits if available
        self.update_current_limits()
        
    def _create_controls(self):
        """Create the zoom control UI elements."""
        # Main container frame
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        # Zoom factor controls
        zoom_frame = ttk.Frame(main_frame)
        zoom_frame.grid(row=0, column=0, sticky='ew', padx=2, pady=2)
        
        ttk.Label(zoom_frame, text="Zoom Factor:").grid(row=0, column=0, sticky='w', padx=2)
        zoom_entry = ttk.Entry(zoom_frame, textvariable=self.zoom_factor, width=8)
        zoom_entry.grid(row=0, column=1, padx=2)
        
        # Zoom factor buttons
        zoom_buttons_frame = ttk.Frame(main_frame)
        zoom_buttons_frame.grid(row=1, column=0, sticky='ew', padx=2, pady=2)
        
        ttk.Button(zoom_buttons_frame, text="Zoom In", command=lambda: self.apply_zoom(1.25), width=10).grid(row=0, column=0, padx=2)
        ttk.Button(zoom_buttons_frame, text="Zoom Out", command=lambda: self.apply_zoom(0.8), width=10).grid(row=0, column=1, padx=2)
        ttk.Button(zoom_buttons_frame, text="Reset", command=self.reset_zoom, width=10).grid(row=0, column=2, padx=2)
        
        # Center point selection
        center_frame = ttk.LabelFrame(main_frame, text="Zoom Center Point")
        center_frame.grid(row=2, column=0, sticky='ew', padx=2, pady=(5, 2))
        
        ttk.Label(center_frame, text="X:").grid(row=0, column=0, sticky='w', padx=2)
        ttk.Entry(center_frame, textvariable=self.center_x, width=8).grid(row=0, column=1, padx=2)
        
        ttk.Label(center_frame, text="Y:").grid(row=0, column=2, sticky='w', padx=2)
        ttk.Entry(center_frame, textvariable=self.center_y, width=8).grid(row=0, column=3, padx=2)
        
        ttk.Label(center_frame, text="Z:").grid(row=0, column=4, sticky='w', padx=2)
        ttk.Entry(center_frame, textvariable=self.center_z, width=8).grid(row=0, column=5, padx=2)
        
        # Center point selection button
        ttk.Button(center_frame, text="Set to Current View Center", command=self.set_center_to_current).grid(row=1, column=0, columnspan=6, sticky='ew', padx=2, pady=2)
        
        # Preset frame after group display
        preset_frame = ttk.LabelFrame(main_frame, text="Preset View States")
        preset_frame.grid(row=3, column=0, sticky='ew', padx=2, pady=(5, 2))
        
        # Create main buttons frame with proper space distribution
        preset_buttons_frame = ttk.Frame(preset_frame)
        preset_buttons_frame.grid(row=0, column=0, sticky='ew', padx=2, pady=2)
        preset_buttons_frame.grid_columnconfigure(0, weight=0)  # Fixed width for Save button
        preset_buttons_frame.grid_columnconfigure(1, weight=1)  # Make dropdown expandable
        
        # First row: Save button and dropdown
        ttk.Button(preset_buttons_frame, text="Save Current", command=self.save_current_state, width=12).grid(row=0, column=0, padx=2)
        
        # Create dropdown with adjusted width to ensure arrow is visible
        self.preset_var = tk.StringVar()
        self.preset_menu = ttk.Combobox(preset_buttons_frame, textvariable=self.preset_var, width=20, state="readonly")
        self.preset_menu.grid(row=0, column=1, padx=(2,15), sticky='ew')  # Add padding on right for arrow
        self.preset_menu.bind("<<ComboboxSelected>>", self.on_preset_selected)
        
        # Second row: Load under Save, Delete aligned with dropdown start
        ttk.Button(preset_buttons_frame, text="Load", command=self.load_selected_state, width=12).grid(row=1, column=0, padx=2, pady=(4,0))
        ttk.Button(preset_buttons_frame, text="Delete", command=self.delete_selected_state, width=12).grid(row=1, column=1, padx=2, pady=(4,0), sticky='w')
        
        # Add help text under the controls
        ttk.Label(preset_frame, text="Save your view settings (zoom, rotation, ranges) for quick access.", 
                 font=('Arial', 8), foreground='dark gray').grid(row=1, column=0, sticky='w', padx=5, pady=(2, 5))
        
        # Initialize dropdown with default guidance text
        self.preset_menu['values'] = ["(Click 'Save Current' to create a preset)"]
        self.preset_var.set("(Click 'Save Current' to create a preset)")
        
        # Now update with any actual saved presets
        self.update_preset_menu()
        
        # Axis-specific zoom controls
        axis_zoom_frame = ttk.LabelFrame(main_frame, text="Axis-Specific Zoom")
        axis_zoom_frame.grid(row=4, column=0, sticky='ew', padx=2, pady=(5, 2))
        
        # X-axis zoom controls
        ttk.Label(axis_zoom_frame, text="X-axis:").grid(row=0, column=0, sticky='w', padx=2)
        ttk.Button(axis_zoom_frame, text="Zoom In", command=lambda: self.apply_axis_zoom('x', 1.25), width=8).grid(row=0, column=1, padx=2)
        ttk.Button(axis_zoom_frame, text="Zoom Out", command=lambda: self.apply_axis_zoom('x', 0.8), width=8).grid(row=0, column=2, padx=2)
        
        # Y-axis zoom controls
        ttk.Label(axis_zoom_frame, text="Y-axis:").grid(row=1, column=0, sticky='w', padx=2)
        ttk.Button(axis_zoom_frame, text="Zoom In", command=lambda: self.apply_axis_zoom('y', 1.25), width=8).grid(row=1, column=1, padx=2)
        ttk.Button(axis_zoom_frame, text="Zoom Out", command=lambda: self.apply_axis_zoom('y', 0.8), width=8).grid(row=1, column=2, padx=2)
        
        # Z-axis zoom controls
        ttk.Label(axis_zoom_frame, text="Z-axis:").grid(row=2, column=0, sticky='w', padx=2)
        ttk.Button(axis_zoom_frame, text="Zoom In", command=lambda: self.apply_axis_zoom('z', 1.25), width=8).grid(row=2, column=1, padx=2)
        ttk.Button(axis_zoom_frame, text="Zoom Out", command=lambda: self.apply_axis_zoom('z', 0.8), width=8).grid(row=2, column=2, padx=2)
        
        # Add a button to connect to click events for setting center point
        click_frame = ttk.Frame(main_frame)
        click_frame.grid(row=5, column=0, sticky='ew', padx=2, pady=(5, 2))
        
        self.click_mode_var = tk.BooleanVar(value=False)
        self.click_button = ttk.Checkbutton(
            click_frame, 
            text="Click to Set Zoom Center", 
            variable=self.click_mode_var,
            command=self.toggle_click_mode
        )
        self.click_button.grid(row=0, column=0, sticky='w', padx=2)
        
        # Help button
        help_button = ttk.Button(
            click_frame, 
            text="Zoom Help", 
            command=self.show_help, 
            width=10
        )
        help_button.grid(row=0, column=1, sticky='e', padx=2)
        
    def _validate_and_round_coordinate(self, *args):
        """Validate and round coordinate values to 2 decimal places."""
        try:
            # Determine which variable was changed
            var_name = args[0]
            if var_name == str(self.center_x):
                var = self.center_x
            elif var_name == str(self.center_y):
                var = self.center_y
            elif var_name == str(self.center_z):
                var = self.center_z
            else:
                return
                
            # Get current value
            try:
                value = var.get()
                
                # Skip processing if the variable is being cleared or set to None
                if value is None:
                    return
                    
                # Round to 2 decimal places
                rounded_value = round(value, 2)
                
                # Only update if it's actually different to avoid infinite loop
                if abs(value - rounded_value) > 1e-10:
                    # Remove the trace temporarily
                    var.trace_remove("write", var.trace_info()[0][1])
                    
                    # Set the rounded value
                    var.set(rounded_value)
                    
                    # Re-add the trace
                    var.trace_add("write", self._validate_and_round_coordinate)
            except (ValueError, tk.TclError):
                # Invalid value, leave it for now (it will be validated when used)
                pass
        except Exception as e:
            print(f"Error in coordinate validation: {e}")
        
    def toggle_click_mode(self):
        """Toggle click-to-set-center mode."""
        if self.click_mode_var.get():
            # Enable click event handling
            self.canvas.mpl_connect('button_press_event', self.on_click)
            self.click_button.configure(text="Click Mode Active (Click Plot)")
        else:
            # Disable click event handling
            # Note: In a full implementation, we would disconnect the event handler
            self.click_button.configure(text="Click to Set Zoom Center")
    
    def on_click(self, event):
        """Handle click events when in click-to-set-center mode."""
        if not self.click_mode_var.get():
            return
        
        # Make sure this is a 3D axes click
        if event.inaxes != self.ax:
            return
            
        # Get the 3D data coordinates
        # Note: For a 3D plot, this is not straightforward and may require additional processing
        # Here we're getting the 2D coordinates and using them to set X and Y values
        try:
            # Get and validate the coordinates
            if event.xdata is None or event.ydata is None:
                messagebox.showerror("Invalid Coordinates", "Could not determine click coordinates.")
                return
                
            # Round coordinates to 2 decimal places
            x_value = round(event.xdata, 2)
            y_value = round(event.ydata, 2)
            
            # Update center coordinates
            self.center_x.set(x_value)
            self.center_y.set(y_value)
            # Z coordinate is left as is
            
            # For Z, we can try to estimate or leave as is
            # In a full implementation, we might use the renderer to project 3D to 2D and back
            
            messagebox.showinfo("Zoom Center Set", 
                              f"Zoom center set to X={self.center_x.get():.2f}, Y={self.center_y.get():.2f}\n"
                              f"Z coordinate is estimated or retained")
            
            # Turn off click mode after a successful selection
            self.click_mode_var.set(False)
            self.toggle_click_mode()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set zoom center: {str(e)}")
    
    def update_current_limits(self):
        """Update stored limits from the current axes state."""
        try:
            if self.ax:
                self.current_xlim = self.ax.get_xlim()
                self.current_ylim = self.ax.get_ylim()
                self.current_zlim = self.ax.get_zlim()
                
                # Calculate center points based on current limits and round to 2 decimal places
                self.center_x.set(round((self.current_xlim[0] + self.current_xlim[1]) / 2, 2))
                self.center_y.set(round((self.current_ylim[0] + self.current_ylim[1]) / 2, 2))
                self.center_z.set(round((self.current_zlim[0] + self.current_zlim[1]) / 2, 2))
        except Exception as e:
            print(f"Warning: Could not update current limits: {e}")
    
    def set_center_to_current(self):
        """Set the center point to the current view center."""
        try:
            # Get current limits directly from axes
            if self.ax is None:
                messagebox.showerror("Error", "No axes available.")
                return
                
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            zlim = self.ax.get_zlim()
            
            # Verify limits are valid
            if (xlim[0] >= xlim[1] or ylim[0] >= ylim[1] or zlim[0] >= zlim[1]):
                messagebox.showerror("Invalid Limits", "Axis limits are invalid.")
                return
                
            # Calculate center points exactly and round to 2 decimal places
            x_center = round((xlim[0] + xlim[1]) / 2, 2)
            y_center = round((ylim[0] + ylim[1]) / 2, 2)
            z_center = round((zlim[0] + zlim[1]) / 2, 2)
            
            # Set the center points
            self.center_x.set(x_center)
            self.center_y.set(y_center)
            self.center_z.set(z_center)
            
            # Update stored limits
            self.current_xlim = xlim
            self.current_ylim = ylim
            self.current_zlim = zlim
            
            messagebox.showinfo("Center Updated", 
                              f"Zoom center updated to current view center:\n"
                              f"X={self.center_x.get():.2f}, Y={self.center_y.get():.2f}, Z={self.center_z.get():.2f}")
        except Exception as e:
            print(f"Error setting center point: {e}")
            self.update_current_limits()  # Fallback to standard method
    
    def apply_zoom(self, factor=None):
        """
        Apply zoom with the specified factor centered on the current center point.
        
        Args:
            factor: Zoom factor (>1 for zoom in, <1 for zoom out).
                   If None, use the value from the zoom_factor entry.
        """
        try:
            # If no factor provided, use the one from the entry field
            if factor is None:
                try:
                    factor = self.zoom_factor.get()
                    if factor <= 0:
                        messagebox.showerror("Invalid Zoom", "Zoom factor must be positive")
                        return
                except (ValueError, tk.TclError):
                    messagebox.showerror("Invalid Zoom", "Please enter a valid number for zoom factor")
                    return
            
            # Make sure we have current limits
            if not all([self.current_xlim, self.current_ylim, self.current_zlim]):
                self.update_current_limits()
            
            # Get center point with validation
            try:
                center_x = self.center_x.get()
                center_y = self.center_y.get()
                center_z = self.center_z.get()
                
                # Validate coordinates
                if not (self._is_valid_coordinate(center_x) and 
                        self._is_valid_coordinate(center_y) and 
                        self._is_valid_coordinate(center_z)):
                    messagebox.showerror("Invalid Center", 
                                       "Zoom center coordinates must be valid numbers.")
                    return
            except (ValueError, tk.TclError):
                messagebox.showerror("Invalid Center", 
                                   "Zoom center coordinates must be valid numbers.")
                return
            
            # Calculate new limits
            new_xlim = self._calculate_new_limits(self.current_xlim, center_x, factor)
            new_ylim = self._calculate_new_limits(self.current_ylim, center_y, factor)
            new_zlim = self._calculate_new_limits(self.current_zlim, center_z, factor)
            
            # Apply the new limits
            self.ax.set_xlim(new_xlim)
            self.ax.set_ylim(new_ylim)
            self.ax.set_zlim(new_zlim)
            
            # Update current limits
            self.current_xlim = new_xlim
            self.current_ylim = new_ylim
            self.current_zlim = new_zlim
            
            # Redraw
            self.canvas.draw_idle()
            
            # Notify listener if callback is provided
            if self.on_zoom_change:
                self.on_zoom_change()
        except Exception as e:
            messagebox.showerror("Zoom Error", f"Failed to apply zoom: {str(e)}")
    
    def _calculate_new_limits(self, current_limits, center, factor):
        """
        Calculate new axis limits based on zoom factor and center point.
        
        Args:
            current_limits: Current (min, max) limits tuple
            center: Center point of zoom operation
            factor: Zoom factor (>1 for zoom in, <1 for zoom out)
            
        Returns:
            tuple: New (min, max) limits
        """
        # Calculate distances from center to min and max
        min_val, max_val = current_limits
        dist_to_min = center - min_val
        dist_to_max = max_val - center
        
        # Apply zoom factor to these distances
        new_dist_to_min = dist_to_min / factor
        new_dist_to_max = dist_to_max / factor
        
        # Calculate new limits
        new_min = center - new_dist_to_min
        new_max = center + new_dist_to_max
        
        return (new_min, new_max)
    
    def apply_axis_zoom(self, axis, factor):
        """
        Apply zoom to a specific axis.
        
        Args:
            axis: Axis to zoom ('x', 'y', or 'z')
            factor: Zoom factor (>1 for zoom in, <1 for zoom out)
        """
        try:
            # Make sure we have current limits
            if not all([self.current_xlim, self.current_ylim, self.current_zlim]):
                self.update_current_limits()
            
            # Get center point for the specified axis
            if axis == 'x':
                center = self.center_x.get()
                current_lim = self.current_xlim
                new_lim = self._calculate_new_limits(current_lim, center, factor)
                self.ax.set_xlim(new_lim)
                self.current_xlim = new_lim
            elif axis == 'y':
                center = self.center_y.get()
                current_lim = self.current_ylim
                new_lim = self._calculate_new_limits(current_lim, center, factor)
                self.ax.set_ylim(new_lim)
                self.current_ylim = new_lim
            elif axis == 'z':
                center = self.center_z.get()
                current_lim = self.current_zlim
                new_lim = self._calculate_new_limits(current_lim, center, factor)
                self.ax.set_zlim(new_lim)
                self.current_zlim = new_lim
            else:
                raise ValueError(f"Invalid axis: {axis}")
            
            # Redraw
            self.canvas.draw_idle()
            
            # Notify listener if callback is provided
            if self.on_zoom_change:
                self.on_zoom_change()
        except Exception as e:
            messagebox.showerror("Axis Zoom Error", f"Failed to apply zoom to {axis}-axis: {str(e)}")
    
    def reset_zoom(self):
        """Reset zoom to default state (0-1 range on all axes)."""
        try:
            # Set default limits
            self.ax.set_xlim([0.0, 1.0])
            self.ax.set_ylim([0.0, 1.0])
            self.ax.set_zlim([0.0, 1.0])
            
            # Update current limits
            self.current_xlim = (0.0, 1.0)
            self.current_ylim = (0.0, 1.0)
            self.current_zlim = (0.0, 1.0)
            
            # Update center point
            self.center_x.set(0.5)
            self.center_y.set(0.5)
            self.center_z.set(0.5)
            
            # Redraw
            self.canvas.draw_idle()
            
            # Notify listener if callback is provided
            if self.on_zoom_change:
                self.on_zoom_change()
                
            messagebox.showinfo("Zoom Reset", "Zoom has been reset to default state.")
        except Exception as e:
            messagebox.showerror("Reset Error", f"Failed to reset zoom: {str(e)}")
    
    def save_current_state(self):
        """Save complete view state (zoom, rotation, axis ranges) with a user-provided name."""
        try:
            # Get a name for the preset from the user
            import tkinter.simpledialog as simpledialog
            preset_name = simpledialog.askstring("Save View Preset", "Enter a name for this complete view preset:")
            
            if not preset_name:
                return  # User cancelled
            
            # Make sure we have current limits
            if not all([self.current_xlim, self.current_ylim, self.current_zlim]):
                self.update_current_limits()
            
            # Get current rotation angles from axes
            try:
                elev = self.ax.elev if hasattr(self.ax, 'elev') else 30
                azim = self.ax.azim if hasattr(self.ax, 'azim') else -60
                roll = self.ax.roll if hasattr(self.ax, 'roll') else 0
                print(f"Saving rotation angles: elev={elev}, azim={azim}, roll={roll}")
            except Exception as e:
                print(f"Warning: Could not get rotation angles: {e}")
                elev, azim, roll = 30, -60, 0  # Default values
            
            # Save the complete view state
            self.saved_states[preset_name] = {
                'xlim': self.current_xlim,
                'ylim': self.current_ylim,
                'zlim': self.current_zlim,
                'center_x': self.center_x.get(),
                'center_y': self.center_y.get(),
                'center_z': self.center_z.get(),
                # Add rotation angles
                'elevation': elev,
                'azimuth': azim,
                'roll': roll
            }
            
            # Update the preset menu
            self.update_preset_menu()
            
            # Save presets to file
            self.save_presets_to_file()
            
            messagebox.showinfo("Preset Saved", f"Complete view preset '{preset_name}' has been saved with zoom, rotation, and axis settings.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save preset: {str(e)}")
    
    def update_preset_menu(self):
        """Update the preset dropdown menu with current saved states."""
        if self.saved_states:
            # Format saved states with descriptions
            preset_items = []
            for name, state in self.saved_states.items():
                description = state.get('description', '')
                if description:
                    preset_items.append(f"{name} - {description[:20]}")
                else:
                    preset_items.append(name)
            
            # Update dropdown with actual presets
            self.preset_menu['values'] = preset_items
            
            # Select first item if nothing is currently selected
            if not self.preset_var.get() or self.preset_var.get() == "(Click 'Save Current' to create a preset)":
                self.preset_var.set(preset_items[0])
        else:
            # Show guidance text if no presets exist
            self.preset_menu['values'] = ["(Click 'Save Current' to create a preset)"]
            self.preset_var.set("(Click 'Save Current' to create a preset)")
    
    def on_preset_selected(self, event):
        """Handle preset selection from dropdown."""
        # This method is called when a preset is selected in the dropdown
        # The actual loading happens when the Load button is clicked
        pass
    
    def load_selected_state(self):
        """Load the complete view state from the currently selected preset."""
        try:
            # Get the selected preset name
            preset_name = self.preset_var.get()
            
            # Handle special case for the guidance text
            if preset_name == "(Click 'Save Current' to create a preset)":
                messagebox.showinfo("No Preset", "Please save a view preset first, then select it from the dropdown.")
                return
                
            # Check if preset exists
            if not preset_name or preset_name not in self.saved_states:
                messagebox.showwarning("Load Error", "No preset selected or preset does not exist.")
                return
            
            # Get the saved state
            state = self.saved_states[preset_name]
            
            # Debugging: Print full state info
            print(f"Loading preset '{preset_name}' with state: {state}")
            
            # Important: First update internal limits
            self.current_xlim = state['xlim'] 
            self.current_ylim = state['ylim']
            self.current_zlim = state['zlim']
            
            # Then apply the saved limits to the axes
            self.ax.set_xlim(state['xlim'])
            self.ax.set_ylim(state['ylim'])
            self.ax.set_zlim(state['zlim'])
            
            # Update center point with validation
            try:
                self.center_x.set(round(state['center_x'], 2))
                self.center_y.set(round(state['center_y'], 2))
                self.center_z.set(round(state['center_z'], 2))
            except Exception as e:
                print(f"Warning: Could not set center point: {e}")
                # Fallback to calculated center
                x_center = round((state['xlim'][0] + state['xlim'][1]) / 2, 2)
                y_center = round((state['ylim'][0] + state['ylim'][1]) / 2, 2)
                z_center = round((state['zlim'][0] + state['zlim'][1]) / 2, 2)
                self.center_x.set(x_center)
                self.center_y.set(y_center)
                self.center_z.set(z_center)
            
            # Apply rotation if available (for backward compatibility)
            if all(k in state for k in ['elevation', 'azimuth']):
                try:
                    # Handle roll parameter depending on matplotlib version
                    elev = state['elevation']
                    azim = state['azimuth']
                    roll = state.get('roll', 0)  # Default to 0 if not saved
                    
                    print(f"Applying rotation: elev={elev}, azim={azim}, roll={roll}")
                    
                    try:
                        self.ax.view_init(elev=elev, azim=azim, roll=roll)
                        print(f"Applied rotation with roll support")
                    except TypeError:
                        # Older matplotlib versions don't support roll
                        self.ax.view_init(elev=elev, azim=azim)
                        print(f"Applied rotation without roll support")
                except Exception as e:
                    print(f"Warning: Could not apply rotation: {e}")
            
            # Force redraw to ensure all changes are applied
            self.canvas.draw()
            
            # Notify listener if callback is provided - important for updating axis controls
            if self.on_zoom_change:
                # Pass axis ranges to ensure they're updated in main app
                axis_ranges = {
                    'x_min': float(state['xlim'][0]),
                    'x_max': float(state['xlim'][1]),
                    'y_min': float(state['ylim'][0]),
                    'y_max': float(state['ylim'][1]),
                    'z_min': float(state['zlim'][0]),
                    'z_max': float(state['zlim'][1])
                }
                self.on_zoom_change(axis_ranges=axis_ranges)
                
            messagebox.showinfo("Preset Loaded", f"View preset '{preset_name}' has been loaded with all settings (zoom, rotation, axes).")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load preset: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def delete_selected_state(self):
        """Delete the currently selected preset state."""
        try:
            preset_name = self.preset_var.get()
            
            # Handle special case for the guidance text
            if preset_name == "(Click 'Save Current' to create a preset)":
                messagebox.showinfo("No Preset", "Please save a view preset first, then select it from the dropdown.")
                return
                
            if not preset_name or preset_name not in self.saved_states:
                messagebox.showwarning("Delete Error", "No preset selected or preset does not exist.")
                return
            
            # Confirm deletion
            if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the zoom preset '{preset_name}'?"):
                return
            
            # Delete the preset
            del self.saved_states[preset_name]
            
            # Update the preset menu
            self.update_preset_menu()
            
            # Save updated presets to file
            self.save_presets_to_file()
            
            messagebox.showinfo("Preset Deleted", f"Zoom preset '{preset_name}' has been deleted.")
        except Exception as e:
            messagebox.showerror("Delete Error", f"Failed to delete preset: {str(e)}")
    
    def show_help(self):
        """Show help information about the zoom controls."""
        help_text = """
Precision Zoom Controls Help:

Zoom Factor:
  - Enter a value to set the zoom factor (>1 to zoom in, <1 to zoom out)
  - Click "Zoom In" to zoom in by 25%
  - Click "Zoom Out" to zoom out by 20%
  - Click "Reset" to reset to default view

Zoom Center Point:
  - Set X, Y, Z coordinates to specify the center of the zoom operation
  - Click "Set to Current View Center" to use the current view center
  - Check "Click to Set Zoom Center" and click on the plot to select a point

Preset View States:
  - Saves and restores complete view settings including:
    * Zoom level and center point
    * 3D rotation angles (elevation, azimuth, roll)
    * Axis ranges
  - Select a saved preset from the dropdown
  - Click "Load" to apply the selected preset
  - Click "Delete" to remove the selected preset
  - Presets are saved between sessions

Axis-Specific Zoom:
  - Zoom individual axes independently
  - Useful for adjusting the aspect ratio

Tips:
  - Use small zoom factors for precise adjustments
  - Set the center point to a point of interest before zooming
  - Save useful zoom states for quick access
"""
        messagebox.showinfo("Zoom Controls Help", help_text)
        
    def update_axes_reference(self, ax):
        """Update the axes reference when the plot is recreated."""
        if ax is not self.ax:
            self.ax = ax
            self.update_current_limits()

    def get_current_limits(self):
        """Get the current axis limits as a dictionary."""
        return {
            'xlim': self.current_xlim,
            'ylim': self.current_ylim,
            'zlim': self.current_zlim
        }

    def load_presets_from_file(self):
        """Load saved presets from file."""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r') as f:
                    loaded_states = json.load(f)
                    
                    # Convert loaded state back to proper format (tuples instead of lists for limits)
                    for name, state in loaded_states.items():
                        if 'xlim' in state and isinstance(state['xlim'], list):
                            state['xlim'] = tuple(state['xlim'])
                        if 'ylim' in state and isinstance(state['ylim'], list):
                            state['ylim'] = tuple(state['ylim'])
                        if 'zlim' in state and isinstance(state['zlim'], list):
                            state['zlim'] = tuple(state['zlim'])
                    
                    self.saved_states = loaded_states
                self.update_preset_menu()
                print(f"Loaded {len(self.saved_states)} zoom presets from {self.presets_file}")
        except Exception as e:
            print(f"Error loading zoom presets: {e}")
            self.saved_states = {}
    
    def save_presets_to_file(self):
        """Save presets to file."""
        try:
            if self.saved_states:
                with open(self.presets_file, 'w') as f:
                    json.dump(self.saved_states, f)
                print(f"Saved {len(self.saved_states)} zoom presets to {self.presets_file}")
        except Exception as e:
            print(f"Error saving zoom presets: {e}")
    
    def set_limits(self, xlim=None, ylim=None, zlim=None):
        """Set axis limits directly."""
        try:
            if xlim:
                self.ax.set_xlim(xlim)
                self.current_xlim = xlim
            if ylim:
                self.ax.set_ylim(ylim)
                self.current_ylim = ylim
            if zlim:
                self.ax.set_zlim(zlim)
                self.current_zlim = zlim
                
            # Redraw
            self.canvas.draw_idle()
            
            # Notify listener if callback is provided
            if self.on_zoom_change:
                self.on_zoom_change()
        except Exception as e:
            print(f"Warning: Could not set limits: {e}")

    def _is_valid_coordinate(self, value):
        """Check if a coordinate value is valid."""
        try:
            # Must be a number and not NaN
            return isinstance(value, (int, float)) and not np.isnan(value)
        except:
            return False
