import tkinter as tk
import math


class RotaryKnob(tk.Canvas):
    """A custom Tkinter widget that simulates a rotary knob with continuous rotation."""
    
    def __init__(self, master, callback=None, **kwargs):
        """
        Initialize the rotary knob widget.
        
        Parameters:
        - master: the parent widget
        - callback: function to call when value changes, receives angle in degrees
        - **kwargs: additional arguments to pass to the Canvas constructor
        """
        # Set default size if not specified
        kwargs.setdefault('width', 100)
        kwargs.setdefault('height', 100)
        
        # Initialize the canvas
        super().__init__(master, **kwargs)
        
        self.callback = callback
        self.angle = 0  # Current angle in degrees
        self.dragging = False
        self.last_x = 0
        self.last_y = 0
        
        # Configure appearance
        self.configure(highlightthickness=0)
        
        # Bind mouse events
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<B1-Motion>", self.on_drag)
        
        # Draw the initial knob
        self.draw_knob()
    
    def draw_knob(self):
        """Draw the knob on the canvas."""
        # Clear the canvas
        self.delete("all")
        
        # Calculate dimensions
        width = self.winfo_width() or int(self['width'])
        height = self.winfo_height() or int(self['height'])
        center_x = width // 2
        center_y = height // 2
        radius = min(center_x, center_y) - 10
        
        # Draw the outer circle (the knob body)
        self.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            fill="lightgray", outline="gray", width=2, tags="knob"
        )
        
        # Draw the inner circle
        inner_radius = radius * 0.7
        self.create_oval(
            center_x - inner_radius, center_y - inner_radius,
            center_x + inner_radius, center_y + inner_radius,
            fill="white", outline="gray", width=1, tags="knob"
        )
        
        # Draw the indicator line
        angle_rad = math.radians(self.angle)
        indicator_length = radius * 0.8
        indicator_x = center_x + indicator_length * math.sin(angle_rad)
        indicator_y = center_y - indicator_length * math.cos(angle_rad)
        
        self.create_line(
            center_x, center_y, indicator_x, indicator_y,
            fill="red", width=3, tags="indicator"
        )
        
        # Draw a small circle at the center
        center_radius = radius * 0.1
        self.create_oval(
            center_x - center_radius, center_y - center_radius,
            center_x + center_radius, center_y + center_radius,
            fill="gray", outline="", tags="knob"
        )
    
    def get_angle(self):
        """Return the current angle in degrees (0-360)."""
        return self.angle % 360
    
    def set_angle(self, angle):
        """Set the knob to a specific angle."""
        self.angle = angle
        self.draw_knob()
        if self.callback:
            self.callback(self.get_angle())
    
    def on_press(self, event):
        """Handle mouse button press events."""
        self.dragging = True
        self.last_x = event.x
        self.last_y = event.y
    
    def on_release(self, event):
        """Handle mouse button release events."""
        self.dragging = False
    
    def on_drag(self, event):
        """Handle mouse drag events to rotate the knob."""
        if not self.dragging:
            return
        
        # Calculate center of the widget
        width = self.winfo_width() or int(self['width'])
        height = self.winfo_height() or int(self['height'])
        center_x = width // 2
        center_y = height // 2
        
        # Calculate angles from center to previous and current positions
        prev_angle = math.atan2(self.last_y - center_y, self.last_x - center_x)
        curr_angle = math.atan2(event.y - center_y, event.x - center_x)
        
        # Convert to degrees and calculate the difference
        prev_deg = math.degrees(prev_angle)
        curr_deg = math.degrees(curr_angle)
        delta = curr_deg - prev_deg
        
        # Adjust for wrap-around
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        
        # Update the angle and redraw
        self.angle += delta
        self.draw_knob()
        
        # Update last position
        self.last_x = event.x
        self.last_y = event.y
        
        # Call the callback with the normalized angle (0-360)
        if self.callback:
            self.callback(self.get_angle())


# Demo application
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Rotary Knob Demo")
    root.geometry("300x400")
    
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Create a label to display the angle
    angle_var = tk.StringVar(value="Angle: 0°")
    angle_label = tk.Label(frame, textvariable=angle_var, font=("Arial", 14))
    angle_label.pack(pady=10)
    
    # Create a function to update the label when the knob changes
    def on_knob_change(angle):
        angle_var.set(f"Angle: {angle:.1f}°")
    
    # Create the knob
    knob = RotaryKnob(frame, callback=on_knob_change, width=200, height=200)
    knob.pack(pady=20)
    
    # Create a label with instructions
    instructions = tk.Label(
        frame, 
        text="Click and drag to rotate the knob.\nThe rotation is continuous with no limits.",
        justify=tk.CENTER
    )
    instructions.pack(pady=10)
    
    # Add a spinbox to directly set the angle (for testing)
    control_frame = tk.Frame(frame)
    control_frame.pack(pady=10)
    
    tk.Label(control_frame, text="Set angle:").pack(side=tk.LEFT, padx=5)
    
    def set_angle(event=None):
        try:
            angle = float(spinbox.get())
            knob.set_angle(angle)
        except ValueError:
            pass
    
    spinbox = tk.Spinbox(
        control_frame, 
        from_=0, 
        to=359.9, 
        increment=15,
        width=5,
        command=set_angle
    )
    spinbox.pack(side=tk.LEFT, padx=5)
    spinbox.bind("<Return>", set_angle)
    
    tk.Button(control_frame, text="Set", command=set_angle).pack(side=tk.LEFT, padx=5)
    
    root.mainloop()

