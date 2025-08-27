import tkinter as tk
from tkinter import ttk

def create_button_frame(parent, on_refresh):
    """Create a frame with refresh button"""
    button_frame = tk.Frame(parent)
    refresh_button = tk.Button(button_frame, text='Refresh Data', command=on_refresh)
    refresh_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=2)
    return button_frame

class AxisControls(tk.LabelFrame):
    def __init__(self, parent, axis_vars, on_update=None):
        super().__init__(parent, text="Axis Range Adjust", font=('Arial', 9, 'bold'))
        self.parent = parent
        self.axis_vars = axis_vars
        self.on_update = on_update
        self.using_rgb = False  # Default to L*a*b* mode
        
        # Create shared variables for all axes
        self.min_var = tk.StringVar(value="0.0")
        self.max_var = tk.StringVar(value="1.0")
        
        # Create variables for tick label visibility
        self.x_tick_visible = tk.BooleanVar(value=True)
        self.y_tick_visible = tk.BooleanVar(value=True)
        self.z_tick_visible = tk.BooleanVar(value=True)
        
        # Create controls
        self._create_controls()
    def _create_controls(self):
        # Main container
        control_frame = tk.Frame(self)
        control_frame.grid(padx=2, pady=2)
        
        # Range entry frame
        range_frame = tk.Frame(control_frame)
        range_frame.grid(row=0, column=0, sticky='ew')
        
        # Min control
        tk.Label(range_frame, text="Range:").grid(row=0, column=0, padx=2)
        min_entry = tk.Entry(
            range_frame,
            textvariable=self.min_var,
            width=6
        )
        min_entry.grid(row=0, column=1, padx=2)
        
        # Max control
        tk.Label(range_frame, text="to").grid(row=0, column=2, padx=2)
        max_entry = tk.Entry(
            range_frame,
            textvariable=self.max_var,
            width=6
        )
        max_entry.grid(row=0, column=3, padx=2)
        
        # Button frame under the range controls
        button_frame = tk.Frame(control_frame)
        button_frame.grid(row=1, column=0, sticky='ew', pady=(2, 0))
        
        # Apply and Reset buttons in the button frame
        tk.Button(
            button_frame,
            text="Apply",
            command=self._apply_changes,
            width=8
        ).grid(row=0, column=0, padx=1)
        
        tk.Button(
            button_frame,
            text="Reset",
            command=self._reset_range,
            width=8
        ).grid(row=0, column=1, padx=1)
        
        # Tick label visibility frame
        tick_frame = tk.Frame(control_frame)
        tick_frame.grid(row=2, column=0, sticky='ew', pady=(2, 0))
        
        # Label for tick visibility section
        tk.Label(tick_frame, text="Show Tick Labels:", anchor='w').grid(row=0, column=0, sticky='w', columnspan=3, padx=2)
        
        # X axis tick label checkbox - save reference to update text later
        self.x_checkbox = tk.Checkbutton(
            tick_frame,
            text="L* (Lightness)",  # Initial label
            variable=self.x_tick_visible,
            command=self._on_tick_visibility_changed
        )
        self.x_checkbox.grid(row=1, column=0, sticky='w', padx=2)
        
        # Y axis tick label checkbox - save reference to update text later
        self.y_checkbox = tk.Checkbutton(
            tick_frame,
            text="a* (Green-Red)",  # Initial label
            variable=self.y_tick_visible,
            command=self._on_tick_visibility_changed
        )
        self.y_checkbox.grid(row=1, column=1, sticky='w', padx=2)
        
        # Z axis tick label checkbox - save reference to update text later
        self.z_checkbox = tk.Checkbutton(
            tick_frame,
            text="b* (Blue-Yellow)",  # Initial label
            variable=self.z_tick_visible,
            command=self._on_tick_visibility_changed
        )
        self.z_checkbox.grid(row=1, column=2, sticky='w', padx=2)
    
    def _on_tick_visibility_changed(self):
        """Called when any tick label visibility checkbox is toggled"""
        if self.on_update:
            self.on_update()
    
    def _apply_changes(self):
        try:
            min_val = float(self.min_var.get())
            max_val = float(self.max_var.get())
            
            # Validate range
            if min_val >= max_val:
                return
            
            # Update all axes
            for axis in ['x', 'y', 'z']:
                self.axis_vars[f'{axis}_min'].set(min_val)
                self.axis_vars[f'{axis}_max'].set(max_val)
            
            if self.on_update:
                self.on_update()
        except ValueError:
            # Reset to current values if invalid input
            self._reset_range()
    
    def _reset_range(self):
        self.min_var.set("0.0")
        self.max_var.set("1.0")
        self._apply_changes()

    def update_checkbox_labels(self, using_rgb=False):
        """Update the checkbox labels based on the axis labeling system"""
        self.using_rgb = using_rgb
        
        if using_rgb:
            # RGB mode
            self.x_checkbox.config(text="R (Red)")
            self.y_checkbox.config(text="G (Green)")
            self.z_checkbox.config(text="B (Blue)")
        else:
            # L*a*b* mode
            self.x_checkbox.config(text="L* (Lightness)")
            self.y_checkbox.config(text="a* (Green-Red)")
            self.z_checkbox.config(text="b* (Blue-Yellow)")
