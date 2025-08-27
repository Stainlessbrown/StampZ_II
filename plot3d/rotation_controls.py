import tkinter as tk
from tkinter import ttk
from .rotary_knob import RotaryKnob

class RotationControls(tk.LabelFrame):
    """Widget providing controls for 3D plot rotation using rotary knobs"""
    
    def __init__(self, master, on_rotation_change=None):
        """Initialize rotation controls
        
        Args:
            master: Parent widget
            on_rotation_change: Callback function to be called when rotation changes
        """
        super().__init__(master, text="◎ Rotation Controls - CLICK & DRAG KNOBS ◎", 
                       font=('Arial', 10, 'bold'), foreground='blue', borderwidth=2)
        
        # Initialize default values for the 3D plot (in plot coordinate system)
        # Initialize default values for the 3D plot (in plot coordinate system)
        self._elevation = 30  # Now in -180 to 180 range for full rotation
        self._azimuth = -60
        self._roll = 0
        # Initialize knob angles (0-360 range)
        self._knob_elevation = self._plot_to_knob_elevation(self._elevation)
        self._knob_azimuth = self._plot_to_knob_azimuth(self._azimuth)
        self._knob_roll = self._plot_to_knob_roll(self._roll)
        
        # Set callback function
        self.on_rotation_change = on_rotation_change
        
        # Flag to prevent recursive callbacks
        self._updating_programmatically = False
        
        # Create Tkinter variables for spinboxes
        self.elevation_var = tk.DoubleVar(value=self._knob_elevation)
        self.azimuth_var = tk.DoubleVar(value=self._knob_azimuth)
        self.roll_var = tk.DoubleVar(value=self._knob_roll)
        
        # Knob references
        self.elevation_knob = None
        self.azimuth_knob = None
        self.roll_knob = None
        
        # Create controls
        self._create_controls()
        
        # Connect variable trace callbacks for spinboxes with write and read monitoring
        # This ensures updates are detected from both programmatic and user changes
        self.elevation_var.trace_add("write", self._on_elevation_change)
        self.azimuth_var.trace_add("write", self._on_azimuth_change)
        self.roll_var.trace_add("write", self._on_roll_change)
    
    def _plot_to_knob_elevation(self, elevation):
        """Convert from plot elevation (-180 to 180) to knob angle (0-360)"""
        # Same mapping as azimuth and roll: -180 maps to 0, 180 maps to 360
        return (elevation + 180) % 360
    
    def _knob_to_plot_elevation(self, knob_angle):
        """Convert from knob angle (0-360) to plot elevation (-180 to 180)"""
        # Same mapping as azimuth and roll
        normalized = knob_angle % 360
        return normalized - 180 if normalized <= 180 else normalized - 540
    
    def _plot_to_knob_azimuth(self, azimuth):
        """Convert from plot azimuth (-180 to 180) to knob angle (0-360)"""
        # Simple offset: -180 maps to 0, 180 maps to 360
        return (azimuth + 180) % 360
    
    def _knob_to_plot_azimuth(self, knob_angle):
        """Convert from knob angle (0-360) to plot azimuth (-180 to 180)"""
        # Map 0-360 to -180 to 180
        normalized = knob_angle % 360
        return normalized - 180 if normalized <= 180 else normalized - 540
    
    def _plot_to_knob_roll(self, roll):
        """Convert from plot roll (-180 to 180) to knob angle (0-360)"""
        # Same mapping as azimuth
        return (roll + 180) % 360
    
    def _knob_to_plot_roll(self, knob_angle):
        """Convert from knob angle (0-360) to plot roll (-180 to 180)"""
        # Same mapping as azimuth
        normalized = knob_angle % 360
        return normalized - 180 if normalized <= 180 else normalized - 540
        
    def _create_controls(self):
        """Create rotation control UI elements using rotary knobs"""
        # Container frame with more horizontal room
        main_frame = tk.Frame(self)
        main_frame.grid(padx=6, pady=5)  # Minimal padding to maximize internal space
        
        # Create a frame for the knobs (horizontal layout)
        knobs_frame = tk.Frame(main_frame)
        knobs_frame.grid(row=0, column=0, padx=2, pady=3)  # Minimal horizontal padding
        
        # Configure column weights to ensure even spacing
        knobs_frame.columnconfigure(0, weight=1)
        knobs_frame.columnconfigure(1, weight=1)
        knobs_frame.columnconfigure(2, weight=1)
        
        # Create each knob with labels
        self._create_knob_column(knobs_frame, 0, "Elevation", 
                                self._knob_elevation, self._on_elevation_knob_change)
        self._create_knob_column(knobs_frame, 1, "Azimuth", 
                                self._knob_azimuth, self._on_azimuth_knob_change)
        self._create_knob_column(knobs_frame, 2, "Roll", 
                                self._knob_roll, self._on_roll_knob_change)
        
        # Spinbox frame below the knobs with more space
        spinbox_frame = tk.Frame(main_frame)
        spinbox_frame.grid(row=1, column=0, padx=3, pady=(3, 5))  # Minimal padding to save space
        
        # Configure column weights for spinbox frame too
        spinbox_frame.columnconfigure(0, weight=1)
        spinbox_frame.columnconfigure(1, weight=1)
        spinbox_frame.columnconfigure(2, weight=1)
        
        # Add spinboxes for precise control
        self._create_spinbox_row(spinbox_frame, 0, self.elevation_var)
        self._create_spinbox_row(spinbox_frame, 1, self.azimuth_var)
        self._create_spinbox_row(spinbox_frame, 2, self.roll_var)
        
        # Reset button
        reset_btn = ttk.Button(
            main_frame,
            text="Reset Rotation",
            command=self._reset_rotation
        )
        reset_btn.grid(row=2, column=0, sticky='ew', padx=5, pady=3)
        
        # Add plane view buttons frame
        self._create_plane_view_buttons(main_frame)
        
    def _create_knob_column(self, parent, column, label_text, initial_angle, callback):
        """Create a column containing a labeled rotary knob
        
        Args:
            parent: Parent widget
            column: Grid column
            label_text: Text for the control label
            initial_angle: Initial angle for the knob (0-360)
            callback: Function to call when knob value changes
        """
        # Frame for this knob column
        frame = tk.Frame(parent)
        # Use progressively narrower padding for columns from left to right
        # This ensures the rightmost column (Roll) fits properly
        col_padx = [6, 4, 2]  # Paddings for columns 0, 1, 2
        frame.grid(row=0, column=column, padx=col_padx[column], pady=2)
        
        # Label above the knob
        label = ttk.Label(frame, text=label_text, font=('Arial', 9, 'bold'))
        label.grid(row=0, column=0, pady=(0, 2))  # Minimal vertical padding
        
        # Create a frame with visible border for the knob to make it more obvious
        knob_frame = tk.Frame(frame, borderwidth=3, relief="raised", bg="#c0c0ff", 
                           highlightbackground="blue", highlightthickness=2)
        knob_frame.grid(row=1, column=0, padx=2, pady=2)
        
        # Rotary knob with slightly adjusted size (smaller size to fit better)
        knob = RotaryKnob(knob_frame, callback=callback, width=58, height=58)
        knob.pack(padx=1, pady=1)
        knob.set_angle(initial_angle)
        
        # Add active state visual feedback for knob interaction
        def on_knob_enter(e):
            knob_frame.config(bg="#a0a0ff", relief="sunken")  # Brighter blue, sunken appearance
            
        def on_knob_leave(e):
            knob_frame.config(bg="#c0c0ff", relief="raised")  # Back to normal
            
        # Add hover effect to knob and frame
        knob.bind("<Enter>", on_knob_enter)
        knob.bind("<Leave>", on_knob_leave)
        knob_frame.bind("<Enter>", on_knob_enter)
        knob_frame.bind("<Leave>", on_knob_leave)
        
        # Add a tooltip to explain knob interaction
        tooltip_text = f"CLICK and DRAG to adjust {label_text.lower()}"
        tooltip_label = ttk.Label(frame, text="↻", font=('Arial', 20, 'bold'), foreground='blue',
                                background='#f0f0ff')  # Light background for better visibility
        tooltip_label.grid(row=1, column=0, sticky='ne', padx=1, pady=1)
        
        # Add "Drag" instruction directly on the knob frame
        drag_label = ttk.Label(frame, text="Drag", font=('Arial', 8), 
                              foreground='blue', background='#f0f0ff')
        drag_label.grid(row=1, column=0, sticky='sw', padx=2, pady=0)
        
        # Create tooltip with instructions when hovering over knob or icon
        def show_tooltip(event):
            tooltip = tk.Toplevel(frame)
            tooltip.wm_overrideredirect(True)  # Remove window decorations
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=tooltip_text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()
            return tooltip
            
        def hide_tooltip(tooltip, event):
            if tooltip:
                try:
                    tooltip.destroy()
                except:
                    pass  # Ignore errors if tooltip was already destroyed
            
        # Apply tooltip to all interactive elements
        for widget in [knob, tooltip_label, drag_label, knob_frame]:
            # Create proper functions for enter and leave events
            def on_enter(e, w=widget):
                w.tooltip_ref = show_tooltip(e)
                return "break"
                
            def on_leave(e, w=widget):
                if hasattr(w, 'tooltip_ref'):
                    hide_tooltip(w.tooltip_ref, e)
                return "break"
                
            # Bind the properly defined event handlers
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        
        # Store reference to the knob
        if label_text == "Elevation":
            self.elevation_knob = knob
        elif label_text == "Azimuth":
            self.azimuth_knob = knob
        else:  # Roll
            self.roll_knob = knob
        
        return knob
    
    def _create_spinbox_row(self, parent, column, variable):
        """Create a spinbox for precise input
        
        Args:
            parent: Parent widget
            column: Grid column
            variable: Tkinter variable to bind to
        """
        # Simplified spinbox without +/- buttons, using whole numbers only
        spinbox = ttk.Spinbox(
            parent,
            from_=0,
            to=360,
            width=6,  # Smaller width since we only need space for integers
            increment=1.0,  # Smaller increments for finer control
            textvariable=variable,  # Bind to variable for immediate updating
            command=lambda: self._immediate_update(variable)  # Direct update on spinbox change
        )
        spinbox.grid(row=0, column=column, padx=4)  # Add padding around the spinbox
        
        # Bind direct update to all relevant events for immediate responsiveness
        spinbox.bind("<Return>", lambda e: self._immediate_update(variable))
        spinbox.bind("<FocusOut>", lambda e: self._immediate_update(variable))
        spinbox.bind("<KeyRelease>", lambda e: self._immediate_update(variable))
        
        # Handle button click/release events to trigger updates
        spinbox.bind("<ButtonRelease-1>", lambda e: self._immediate_update(variable))
        
        # Add up/down keys with direct updates
        spinbox.bind("<Up>", lambda e: (self._increment_spinbox(variable, 1.0), self._immediate_update(variable)))
        spinbox.bind("<Down>", lambda e: (self._increment_spinbox(variable, -1.0), self._immediate_update(variable)))
        spinbox.bind("<MouseWheel>", lambda e: (self._increment_spinbox(variable, 1.0 if e.delta > 0 else -1.0), self._immediate_update(variable)))
        
        # Add tooltip for spinbox usage
        tooltip_text = "Enter value or use up/down arrows to adjust"
        def show_tooltip(event):
            tooltip = tk.Toplevel(parent)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=tooltip_text, background="#ffffe0", relief="solid", borderwidth=1,
                            font=('Arial', 10, 'bold'))
            label.pack(padx=4, pady=4)
            return tooltip
            
        def hide_tooltip(tooltip, event):
            if tooltip:
                try:
                    tooltip.destroy()
                except:
                    pass  # Ignore errors if tooltip was already destroyed
            
        # Create proper event handlers for spinbox tooltip
        def on_spinbox_enter(e):
            spinbox.tooltip_ref = show_tooltip(e)
            return "break"
            
        def on_spinbox_leave(e):
            if hasattr(spinbox, 'tooltip_ref'):
                hide_tooltip(spinbox.tooltip_ref, e)
            return "break"
            
        spinbox.bind("<Enter>", on_spinbox_enter)
        spinbox.bind("<Leave>", on_spinbox_leave)
        
        return spinbox
    
    def _on_elevation_knob_change(self, angle):
        """Handle elevation knob rotation"""
        if self._updating_programmatically:
            return
        
        try:
            # Convert the knob angle (0-360) to plot elevation (-180 to 180)
            self._elevation = self._knob_to_plot_elevation(angle)
            
            # Update the spinbox value (showing 0-360) as an integer
            self._updating_programmatically = True
            self.elevation_var.set(round(angle))
            self._updating_programmatically = False
            
            # Trigger the callback to update the plot
            self._trigger_callback()
        except Exception as e:
            print(f"Error in elevation knob update: {e}")
    
    def _on_azimuth_knob_change(self, angle):
        """Handle azimuth knob rotation"""
        if self._updating_programmatically:
            return
        
        try:
            # Convert the knob angle (0-360) to plot azimuth (-180 to 180)
            self._azimuth = self._knob_to_plot_azimuth(angle)
            
            # Update the spinbox value (showing 0-360) as an integer
            self._updating_programmatically = True
            self.azimuth_var.set(round(angle))
            self._updating_programmatically = False
            
            # Trigger the callback to update the plot
            self._trigger_callback()
        except Exception as e:
            print(f"Error in azimuth knob update: {e}")
    
    def _on_roll_knob_change(self, angle):
        """Handle roll knob rotation"""
        if self._updating_programmatically:
            return
        
        try:
            # Convert the knob angle (0-360) to plot roll (-180 to 180)
            self._roll = self._knob_to_plot_roll(angle)
            
            # Update the spinbox value (showing 0-360) as an integer
            self._updating_programmatically = True
            self.roll_var.set(round(angle))
            self._updating_programmatically = False
            
            # Trigger the callback to update the plot
            self._trigger_callback()
        except Exception as e:
            print(f"Error in roll knob update: {e}")

    def _on_elevation_change(self, *args):
        """Handle elevation variable changes from spinbox"""
        if self._updating_programmatically:
            return
            
        try:
            # Get the spinbox value (0-360)
            knob_angle = self.elevation_var.get()
            
            # Update the knob UI
            if self.elevation_knob:
                self.elevation_knob.set_angle(knob_angle)
            
            # Convert to plot elevation (-180 to 180)
            self._elevation = self._knob_to_plot_elevation(knob_angle)
            
            # Trigger the callback
            self._trigger_callback()
        except Exception as e:
            print(f"Error updating elevation: {e}")
    
    def _on_azimuth_change(self, *args):
        """Handle azimuth variable changes from spinbox"""
        if self._updating_programmatically:
            return
            
        try:
            # Get the spinbox value (0-360)
            knob_angle = self.azimuth_var.get()
            
            # Update the knob UI
            if self.azimuth_knob:
                self.azimuth_knob.set_angle(knob_angle)
            
            # Convert to plot azimuth (-180 to 180)
            self._azimuth = self._knob_to_plot_azimuth(knob_angle)
            
            # Trigger the callback
            self._trigger_callback()
        except Exception as e:
            print(f"Error updating azimuth: {e}")
    
    def _on_roll_change(self, *args):
        """Handle roll variable changes from spinbox"""
        if self._updating_programmatically:
            return
            
        try:
            # Get the spinbox value (0-360)
            knob_angle = self.roll_var.get()
            
            # Update the knob UI
            if self.roll_knob:
                self.roll_knob.set_angle(knob_angle)
            
            # Convert to plot roll (-180 to 180)
            self._roll = self._knob_to_plot_roll(knob_angle)
            
            # Trigger the callback
            self._trigger_callback()
        except Exception as e:
            print(f"Error updating roll: {e}")
    
    def _trigger_callback(self):
        """Trigger the rotation change callback"""
        if self.on_rotation_change:
            try:
                self.on_rotation_change()
            except Exception as e:
                print(f"Error in rotation callback: {e}")
    
    def _validate_values(self, event=None):
        """Validate rotation values and ensure they are in valid ranges"""
        try:
            # Set flag to prevent recursive callbacks (only once)
            self._updating_programmatically = True
            
            # Get current values from spinboxes and normalize to 0-360
            try:
                elev_knob = float(self.elevation_var.get()) % 360
                azim_knob = float(self.azimuth_var.get()) % 360
                roll_knob = float(self.roll_var.get()) % 360
            except (ValueError, tk.TclError):
                # Use current knob values if conversion fails
                elev_knob = self._plot_to_knob_elevation(self._elevation)
                azim_knob = self._plot_to_knob_azimuth(self._azimuth)
                roll_knob = self._plot_to_knob_roll(self._roll)
            
            # Convert knob values to plot angles
            self._elevation = self._knob_to_plot_elevation(elev_knob)
            self._azimuth = self._knob_to_plot_azimuth(azim_knob)
            self._roll = self._knob_to_plot_roll(roll_knob)
            
            # Update spinbox variables with normalized knob angles as integers
            # Only update if values have changed to prevent recursive updates
            if round(self.elevation_var.get()) != round(elev_knob):
                self.elevation_var.set(round(elev_knob))
            if round(self.azimuth_var.get()) != round(azim_knob):
                self.azimuth_var.set(round(azim_knob))
            if round(self.roll_var.get()) != round(roll_knob):
                self.roll_var.set(round(roll_knob))
            
            # Update knob positions
            if self.elevation_knob:
                self.elevation_knob.set_angle(elev_knob)
            if self.azimuth_knob:
                self.azimuth_knob.set_angle(azim_knob)
            if self.roll_knob:
                self.roll_knob.set_angle(roll_knob)
            
            # Ensure UI updates
            self.update_idletasks()
            
            # Reset flag before triggering callback
            self._updating_programmatically = False
            
            # Trigger the plot update
            self._trigger_callback()

        except Exception as e:
            print(f"Error validating values: {e}")
            self._updating_programmatically = False

    def _reset_rotation(self):
        """Reset rotation to default values"""
        # Set flag to prevent recursive callbacks
        self._updating_programmatically = True
        
        try:
            # Default plot values
            default_elev = 30
            default_azim = -60
            default_roll = 0
            
            # Convert to knob angles
            default_elev_knob = self._plot_to_knob_elevation(default_elev)
            default_azim_knob = self._plot_to_knob_azimuth(default_azim)
            default_roll_knob = self._plot_to_knob_roll(default_roll)
            
            # Update internal state
            self._elevation = default_elev
            self._azimuth = default_azim
            self._roll = default_roll
            
            # Update spinbox variables with knob angles as integers
            self.elevation_var.set(round(default_elev_knob))
            self.azimuth_var.set(round(default_azim_knob))
            self.roll_var.set(round(default_roll_knob))
            
            # Update knob positions
            if self.elevation_knob:
                self.elevation_knob.set_angle(default_elev_knob)
            if self.azimuth_knob:
                self.azimuth_knob.set_angle(default_azim_knob)
            if self.roll_knob:
                self.roll_knob.set_angle(default_roll_knob)
            
            # Ensure UI updates
            self.update_idletasks()
            
        except Exception as e:
            print(f"Error resetting rotation: {e}")
            
        finally:
            # Always reset the flag and trigger callback
            self._updating_programmatically = False
            self._trigger_callback()
    def update_values(self, elev, azim, roll=0):
        """Update rotation values without triggering callbacks
        
        This is used when the plot updates the controls, rather than
        the controls updating the plot.
        
        Args:
            elev: Elevation angle in plot coordinates (-180 to 180)
            azim: Azimuth angle in plot coordinates (-180 to 180)
            roll: Roll angle in plot coordinates (-180 to 180)
        """
        try:
            # Set flag to prevent recursive callbacks
            self._updating_programmatically = True
            
            # Update internal plot angles
            self._elevation = float(elev)
            self._azimuth = float(azim)
            self._roll = float(roll)
            
            # Convert to knob angles (0-360)
            elev_knob = self._plot_to_knob_elevation(self._elevation)
            azim_knob = self._plot_to_knob_azimuth(self._azimuth)
            roll_knob = self._plot_to_knob_roll(self._roll)
            
            # Update spinbox variables as integers
            self.elevation_var.set(round(elev_knob))
            self.azimuth_var.set(round(azim_knob))
            self.roll_var.set(round(roll_knob))
            
            # Update knob positions
            if self.elevation_knob:
                self.elevation_knob.set_angle(elev_knob)
            if self.azimuth_knob:
                self.azimuth_knob.set_angle(azim_knob)
            if self.roll_knob:
                self.roll_knob.set_angle(roll_knob)
            
            # Ensure UI updates
            self.update_idletasks()
            
        except Exception as e:
            print(f"Error updating values: {e}")
        finally:
            self._updating_programmatically = False
    def _increment_spinbox(self, variable, amount):
        """Increment or decrement a spinbox value
        
        Args:
            variable: The Tkinter variable to modify
            amount: The amount to add (can be negative)
        """
        try:
            current_value = variable.get()
            # Calculate new value and round to the nearest integer
            new_value = round((current_value + amount) % 360)
            # Set flag to prevent recursive callbacks that could interfere with the update
            self._updating_programmatically = True
            variable.set(new_value)
            self._updating_programmatically = False
            
            # This will trigger the appropriate change handler through the variable trace
        except Exception as e:
            print(f"Error incrementing value: {e}")
            self._updating_programmatically = False
    
    def _immediate_update(self, variable):
        """Force immediate update from spinbox changes
        
        Args:
            variable: The Tkinter variable to update from
        """
        try:
            # Normalize and round the value
            value = round(float(variable.get())) % 360
            
            # Set the normalized value back to ensure consistency
            if variable.get() != value:
                variable.set(value)
            
            # Validate and update the plot
            self._validate_values()
        except (ValueError, tk.TclError):
            # Ignore invalid values, they'll be fixed by _validate_values later
            pass
            
    def _validate_and_update(self, event=None):
        """Validate values and explicitly trigger rotation update"""
        # Just call validate values which already triggers the callback
        self._validate_values(event)
    
    @property
    def elevation(self):
        """Get the current elevation value"""
        return self._elevation
    
    @property
    def azimuth(self):
        """Get the current azimuth value"""
        return self._azimuth
    
    @property
    def roll(self):
        """Get the current roll value"""
        return self._roll
        
    def _create_plane_view_buttons(self, parent):
        """Create buttons for preset plane views
        
        Args:
            parent: Parent widget
        """
        # Create a labeled frame for the plane view buttons
        plane_frame = ttk.LabelFrame(parent, text="Plane Views")
        plane_frame.grid(row=3, column=0, sticky='ew', padx=5, pady=5)
        
        # Create a frame for the buttons
        button_frame = ttk.Frame(plane_frame)
        button_frame.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        # Configure grid weights to distribute buttons evenly
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        
        # Create X/Y plane button
        xy_btn = ttk.Button(
            button_frame,
            text="X/Y Plane",
            command=lambda: self._set_plane_view('xy')
        )
        xy_btn.grid(row=0, column=0, padx=2, pady=2, sticky='ew')
        
        # Create X/Z plane button
        xz_btn = ttk.Button(
            button_frame,
            text="X/Z Plane",
            command=lambda: self._set_plane_view('xz')
        )
        xz_btn.grid(row=0, column=1, padx=2, pady=2, sticky='ew')
        
        # Create Y/Z plane button
        yz_btn = ttk.Button(
            button_frame,
            text="Y/Z Plane",
            command=lambda: self._set_plane_view('yz')
        )
        yz_btn.grid(row=0, column=2, padx=2, pady=2, sticky='ew')
        
        return plane_frame
        
    def _set_plane_view(self, plane):
        """Set the view angles for a specific plane view
        
        Args:
            plane: String indicating which plane view to set ('xy', 'xz', or 'yz')
        """
        try:
            # Set flag to prevent recursive callbacks
            self._updating_programmatically = True
            
            # Define the angles for each plane view (in plot coordinates -180 to 180)
            views = {
                'xy': {'elev': 90, 'azim': 0, 'roll': 0},       # X/Y plane (top view)
                'xz': {'elev': 0, 'azim': 0, 'roll': 0},        # X/Z plane (front view)
                'yz': {'elev': 0, 'azim': 90, 'roll': 0}        # Y/Z plane (side view)
            }
            
            if plane in views:
                view = views[plane]
                
                # Update internal state
                self._elevation = view['elev']
                self._azimuth = view['azim']
                self._roll = view['roll']
                
                # Convert to knob angles (0-360)
                elev_knob = self._plot_to_knob_elevation(self._elevation)
                azim_knob = self._plot_to_knob_azimuth(self._azimuth)
                roll_knob = self._plot_to_knob_roll(self._roll)
                
                # Update spinbox variables
                self.elevation_var.set(round(elev_knob))
                self.azimuth_var.set(round(azim_knob))
                self.roll_var.set(round(roll_knob))
                
                # Update knob positions
                if self.elevation_knob:
                    self.elevation_knob.set_angle(elev_knob)
                if self.azimuth_knob:
                    self.azimuth_knob.set_angle(azim_knob)
                if self.roll_knob:
                    self.roll_knob.set_angle(roll_knob)
                
                print(f"Set {plane.upper()} plane view: elev={self._elevation}, azim={self._azimuth}, roll={self._roll}")
                
        except Exception as e:
            print(f"Error setting plane view: {e}")
        finally:
            # Reset flag and trigger callback
            self._updating_programmatically = False
            self._trigger_callback()
