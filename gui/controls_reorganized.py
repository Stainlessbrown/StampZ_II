#!/usr/bin/env python3
"""
Reorganized Control panel component for the StampZ application.
Implements a cleaner, more logical UI layout with always-visible core controls
and context-sensitive tool controls.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, Dict
import logging
from utils.image_processor import load_image, ImageLoadError

from utils.save_as import SaveOptions, SaveFormat
from gui.canvas import ShapeType
from utils.color_analyzer import PrintType
from utils.template_protection import TemplateProtectionManager

# Configure logging
logger = logging.getLogger(__name__)


class ReorganizedControlPanel(ttk.Frame):
    """Reorganized control panel with cleaner, more logical layout."""

    def __init__(
        self,
        master: tk.Widget,
        on_reset: Callable[[], None],
        on_open: Callable[[], None],
        on_save: Callable[[], None],
        on_quit: Callable[[], None],
        on_clear: Callable[[], None],
        on_vertex_count_change: Callable[[int], None],
        on_fit_to_window: Callable[[], None],
        on_transparency_change: Callable[[int], None],
        on_shape_type_change: Optional[Callable[[ShapeType], None]] = None,
        on_tool_mode_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        # Set fixed width to prevent expansion but allow all controls to be visible
        super().__init__(master, width=400, **kwargs)
        self.pack_propagate(False)  # Prevent children from changing our size
        
        # Store callbacks
        self.on_reset = on_reset
        self.on_open = on_open
        self.on_save = on_save
        self.on_quit = on_quit
        self.on_clear = on_clear
        self.on_fit_to_window = on_fit_to_window
        self.on_vertex_count_change = on_vertex_count_change
        self.on_transparency_change = on_transparency_change
        self.on_shape_type_change = on_shape_type_change
        self.on_tool_mode_change = on_tool_mode_change
        self.on_auto_position = None  # Will be set after initialization
        self.on_line_color_change = None  # Will be set after initialization
        self.on_ruler_toggle = None  # Will be set after initialization
        self.on_grid_toggle = None  # Will be set after initialization
        
        # Initialize variables
        self._init_variables()
        
        # Initialize main_app reference
        self.main_app = None
        
        # Initialize template protection manager
        self.template_protection = TemplateProtectionManager(self)
        
        # Create the reorganized layout
        self._create_always_visible_section()
        self._create_context_sensitive_sections()
        
        # Initially show view mode controls
        self._update_tool_context("view")

    def _init_variables(self):
        """Initialize all control variables."""
        # Core variables
        self.tool_mode = tk.StringVar(value="view")
        self.line_color = tk.StringVar(value="white")
        # Initialize ruler and grid as hidden by default
        self.show_rulers = tk.BooleanVar(value=False)
        self.show_grid = tk.BooleanVar(value=False)
        
        # File info
        self.current_filename = tk.StringVar(value="No file loaded")
        
        # Mouse coordinates
        self.mouse_x = tk.StringVar(value="--")
        self.mouse_y = tk.StringVar(value="--")
        
        # Tool-specific variables (created but not displayed until needed)
        self.vertex_count = tk.IntVar(value=4)
        self.mask_transparency = tk.IntVar(value=64)
        self.shape_type = tk.StringVar(value="polygon")
        self.crop_width = tk.StringVar(value="--")
        self.crop_height = tk.StringVar(value="--")
        self.crop_area = tk.StringVar(value="--")
        
        # Straightening variables
        self.straightening_points = tk.StringVar(value="0")
        self.straightening_angle = tk.StringVar(value="--")
        
        # Sample tool variables
        self.sample_set_name = tk.StringVar()
        self.analysis_name = tk.StringVar()
        self.print_type = tk.StringVar(value="solid")
        self.sample_mode = tk.StringVar(value="template")
        
        # Save options (only shown during save)
        self.save_format = tk.StringVar(value=SaveFormat.TIFF)
        self.jpg_quality = tk.IntVar(value=95)

    def _create_always_visible_section(self):
        """Create the always-visible controls section."""
        
        # SECTION 1: Core Action Buttons (ultra-compressed layout)
        core_frame = ttk.Frame(self)  # Remove LabelFrame to save space
        core_frame.pack(fill=tk.X, padx=2, pady=1)
        
        # Add section label with better readability
        ttk.Label(core_frame, text="Actions", font=('Arial', 12, 'bold')).pack(anchor='w')
        
        # Row 1: Open, Save, Reset
        row1 = ttk.Frame(core_frame)
        row1.pack(fill=tk.X, pady=1)
        
        ttk.Button(row1, text="Open", command=self.on_open).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0,1))
        ttk.Button(row1, text="Save", command=self.on_save).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ttk.Button(row1, text="Reset", command=self.on_reset).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(1,0))
        
        # Row 2: Clear, Fit, Exit
        row2 = ttk.Frame(core_frame)
        row2.pack(fill=tk.X, pady=1)
        
        ttk.Button(row2, text="Clear", command=self.on_clear).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0,1))
        ttk.Button(row2, text="Fit", command=self.on_fit_to_window).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        style = ttk.Style()
        style.configure('Exit.TButton', foreground='red')
        ttk.Button(row2, text="Exit", command=self.on_quit, style='Exit.TButton').pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(1,0))
        
        # Row 3: Open Recent, DB Examine (additional functions)
        row3 = ttk.Frame(core_frame)
        row3.pack(fill=tk.X, pady=1)
        
        ttk.Button(row3, text="Open Recent", command=self.open_recent).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0,1))
        ttk.Button(row3, text="DB Examine", command=self._open_database_viewer).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        # Empty third button to maintain layout balance
        ttk.Label(row3, text="").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(1,0))
        
        # SECTION 2: File Info (ultra-compact - no frame)
        file_row = ttk.Frame(self)
        file_row.pack(fill=tk.X, padx=2, pady=1)
        
        ttk.Label(file_row, text="File:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Label(file_row, textvariable=self.current_filename, 
                 foreground="black", font=('Arial', 14, 'italic')).pack(side=tk.LEFT, padx=(3, 0))
        
        # SECTION 3: Coordinates and Zoom (super compressed)
        coord_row = ttk.Frame(self)
        coord_row.pack(fill=tk.X, padx=2, pady=1)
        
        # Left: Coordinates
        ttk.Label(coord_row, text="X:", font=('Arial', 12)).pack(side=tk.LEFT)
        ttk.Label(coord_row, textvariable=self.mouse_x, 
                 font=('Arial', 12, 'bold'), foreground='#0066CC').pack(
                     side=tk.LEFT, padx=(2, 5))
        
        ttk.Label(coord_row, text="Y:", font=('Arial', 12)).pack(side=tk.LEFT)
        ttk.Label(coord_row, textvariable=self.mouse_y, 
                 font=('Arial', 12, 'bold'), foreground='#0066CC').pack(
                     side=tk.LEFT, padx=(2, 5))
        
        # Right: Zoom controls (compact with slider)
        zoom_frame = ttk.Frame(coord_row)
        zoom_frame.pack(side=tk.RIGHT, padx=2)
        
        self.zoom_level = tk.DoubleVar(value=1.0)
        
        # Zoom buttons and display in top row
        zoom_top = ttk.Frame(zoom_frame)
        zoom_top.pack(fill=tk.X)
        
        ttk.Button(zoom_top, text="-", width=2, command=self._zoom_out).pack(side=tk.LEFT, padx=(0,1))
        self.zoom_display = ttk.Label(zoom_top, text="100%", font=('Arial', 9, 'bold'), 
                                     foreground='#0066CC', width=5)
        self.zoom_display.pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_top, text="+", width=2, command=self._zoom_in).pack(side=tk.LEFT, padx=(1,0))
        
        # Compact zoom slider in bottom row  
        self.zoom_slider = ttk.Scale(zoom_frame, from_=0.1, to=5.0, orient=tk.HORIZONTAL,
                                    variable=self.zoom_level, length=80,
                                    command=self._on_zoom_change)
        self.zoom_slider.pack(fill=tk.X, pady=(1,0))
        
        # SECTION 4: Tool Mode (ultra-compact)
        mode_row = ttk.Frame(self)
        mode_row.pack(fill=tk.X, padx=2, pady=1)
        
        ttk.Label(mode_row, text="Mode:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 2))
        
        # Compact tool mode buttons - smaller padding
        style = ttk.Style()
        style.configure('Compact.TRadiobutton', padding=2)
        
        ttk.Radiobutton(mode_row, text="View", value="view",
                       variable=self.tool_mode, command=self._on_tool_mode_change,
                       style='Compact.TRadiobutton').pack(side=tk.LEFT, padx=1)
        ttk.Radiobutton(mode_row, text="Level", value="straighten",
                       variable=self.tool_mode, command=self._on_tool_mode_change,
                       style='Compact.TRadiobutton').pack(side=tk.LEFT, padx=1)
        ttk.Radiobutton(mode_row, text="Crop", value="crop",
                       variable=self.tool_mode, command=self._on_tool_mode_change,
                       style='Compact.TRadiobutton').pack(side=tk.LEFT, padx=1)
        ttk.Radiobutton(mode_row, text="Sample", value="coord",
                       variable=self.tool_mode, command=self._on_tool_mode_change,
                       style='Compact.TRadiobutton').pack(side=tk.LEFT, padx=1)
        
        # SECTION 5: Line Color (always visible for marker visibility)
        color_row = ttk.Frame(self)
        color_row.pack(fill=tk.X, padx=2, pady=1)
        
        ttk.Label(color_row, text="Line Color:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        color_combo = ttk.Combobox(color_row, textvariable=self.line_color, 
                                  values=["white", "red", "green", "blue", "yellow", "magenta", "cyan", "black"],
                                  state='readonly', width=8)
        color_combo.pack(side=tk.LEFT, padx=2)
        color_combo.bind('<<ComboboxSelected>>', lambda e: self._on_line_color_change())

    def _create_context_sensitive_sections(self):
        """Create tool-specific control sections (hidden by default)."""
        
        # CROP TOOL CONTROLS
        self.crop_frame = ttk.LabelFrame(self, text="Crop Tool Controls")
        
        # Crop dimensions display
        dims_container = ttk.Frame(self.crop_frame)
        dims_container.pack(fill=tk.X, padx=5, pady=5)
        
        size_row = ttk.Frame(dims_container)
        size_row.pack(fill=tk.X, pady=1)
        
        ttk.Label(size_row, text="Size:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Label(size_row, textvariable=self.crop_width, 
                 font=('Arial', 12, 'bold'), foreground='#0066CC').pack(
                     side=tk.LEFT, padx=(5, 2))
        ttk.Label(size_row, text="×", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Label(size_row, textvariable=self.crop_height, 
                 font=('Arial', 12, 'bold'), foreground='#0066CC').pack(
                     side=tk.LEFT, padx=(2, 5))
        ttk.Label(size_row, text="pixels", font=('Arial', 12)).pack(side=tk.LEFT)
        
        # Vertex count control
        vertex_frame = ttk.Frame(self.crop_frame)
        vertex_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(vertex_frame, text="Vertices:").pack(side=tk.LEFT, padx=5)
        ttk.Button(vertex_frame, text="-", width=2, 
                  command=lambda: self._adjust_vertex_count(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Spinbox(vertex_frame, from_=3, to=8, width=3, textvariable=self.vertex_count,
                   command=self._on_vertex_count_change).pack(side=tk.LEFT, padx=2)
        ttk.Button(vertex_frame, text="+", width=2, 
                  command=lambda: self._adjust_vertex_count(1)).pack(side=tk.LEFT, padx=2)
        
        # Transparency control
        trans_frame = ttk.Frame(self.crop_frame)
        trans_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(trans_frame, text="Transparency:").pack(side=tk.LEFT)
        ttk.Scale(trans_frame, from_=0, to=255, orient=tk.HORIZONTAL,
                 variable=self.mask_transparency, 
                 command=lambda _: self.on_transparency_change(self.mask_transparency.get())).pack(
                     side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Fine Square button (initially disabled, enabled when 4 vertices)
        self.fine_square_btn = ttk.Button(self.crop_frame, text="Fine Square", 
                  command=self._on_fine_square_click, state='disabled')
        self.fine_square_btn.pack(fill=tk.X, padx=5, pady=2)
        
        
        # STRAIGHTENING TOOL CONTROLS
        self.straightening_frame = ttk.LabelFrame(self, text="Leveling Tool Controls")
        
        straightening_container = ttk.Frame(self.straightening_frame)
        straightening_container.pack(fill=tk.X, padx=5, pady=5)
        
        # Mode and status
        ttk.Label(straightening_container, text="Mode: Two-Point Leveling",
                 font=('Arial', 10, 'bold')).pack(anchor="w", pady=2)
        
        status_row = ttk.Frame(straightening_container)
        status_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(status_row, text="Points:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Label(status_row, textvariable=self.straightening_points,
                 font=('Arial', 12, 'bold'), foreground='#0066CC').pack(
                     side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(status_row, text="Angle:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Label(status_row, textvariable=self.straightening_angle,
                 font=('Arial', 12, 'bold'), foreground='#CC6600').pack(
                     side=tk.LEFT, padx=(5, 0))
        
        # Buttons
        buttons_row = ttk.Frame(straightening_container)
        buttons_row.pack(fill=tk.X, pady=5)
        
        self.straighten_apply_button = ttk.Button(buttons_row, text="Apply Leveling",
                                                 command=self._apply_straightening, state='disabled')
        self.straighten_apply_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(buttons_row, text="Clear Points", 
                  command=self._clear_straightening_points).pack(side=tk.LEFT, padx=2)
        
        # SAMPLE TOOL CONTROLS  
        self.sample_frame = ttk.LabelFrame(self, text="Sample Tool")
        
        # Sample mode selection
        
        # Sample mode selection
        mode_frame = ttk.Frame(self.sample_frame)
        mode_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Template", variable=self.sample_mode, value="template",
                       command=self._on_sample_mode_change).pack(side=tk.LEFT, padx=(5, 10))
        ttk.Radiobutton(mode_frame, text="Manual", variable=self.sample_mode, value="manual",
                       command=self._on_sample_mode_change).pack(side=tk.LEFT)
        
        # Template frame with Load button integrated
        template_frame = ttk.Frame(self.sample_frame)
        template_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(template_frame, text="Template:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        # Template name entry
        self.template_entry = ttk.Entry(
            template_frame, 
            textvariable=self.sample_set_name,
            width=15  # Match Analysis entry width
        )
        self.template_entry.pack(side=tk.LEFT, padx=5)
        
        # Auto-fill MAN_MODE and keep entry enabled for input
        def on_template_change(event):
            current_text = self.sample_set_name.get().strip()
            if self.sample_mode.get() == "manual":
                if not current_text:
                    self.sample_set_name.set("MAN_MODE")
                    self.template_entry.select_range(0, 'end')  # Select text for easy replacement
            self.template_entry.configure(state='normal')  # Always keep enabled
        
        # Bind to both key events and focus events
        self.template_entry.bind('<KeyRelease>', on_template_change)
        self.template_entry.bind('<FocusIn>', on_template_change)
        self.template_entry.bind('<FocusOut>', on_template_change)
        
        # Load button right next to entry
        self.load_sample_button = ttk.Button(template_frame, text="Load", command=self._load_sample_set, width=5)
        self.load_sample_button.pack(side=tk.LEFT, padx=1)
        
        # Analysis name
        analysis_frame = ttk.Frame(self.sample_frame)
        analysis_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(analysis_frame, text="Analysis:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.analysis_entry = ttk.Entry(analysis_frame, textvariable=self.analysis_name, width=15)
        self.analysis_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(analysis_frame, text="Auto", command=self._auto_generate_analysis_name, 
                  width=4).pack(side=tk.LEFT, padx=2)
        
        # Create expanded container for sample controls (no scrolling)
        sample_controls_container = ttk.Frame(self.sample_frame)
        sample_controls_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Use the container directly as the scrollable frame
        self.sample_scrollable_frame = sample_controls_container
        
        # Create compact controls for each sample area in the scrollable frame
        self.sample_controls = []
        for i in range(5):  # 5 sample areas
            frame = ttk.Frame(self.sample_scrollable_frame)
            frame.pack(fill=tk.X, padx=1, pady=0)
            
            # Sample number label
            ttk.Label(frame, text=f"#{i+1}").pack(side=tk.LEFT, padx=2)
            
            # Create main container with bottom button row
            main_container = ttk.Frame(frame)
            main_container.pack(fill=tk.X, expand=True)
            
            # Top row for controls
            top_row = ttk.Frame(main_container)
            top_row.pack(fill=tk.X, expand=True, pady=(0, 2))
            
            # Create outer frame for centering
            outer_frame = ttk.Frame(top_row)
            outer_frame.pack(expand=True, fill=tk.X)
            
            # Center container for all controls
            control_container = ttk.Frame(outer_frame)
            control_container.pack(expand=True, anchor=tk.CENTER)
            
            # Get default values from preferences
            from utils.user_preferences import get_preferences_manager
            prefs_manager = get_preferences_manager()
            default_settings = prefs_manager.get_default_sample_settings()
            
            # Shape type selection with wider dropdown
            shape_var = tk.StringVar(value=default_settings['shape'])
            shape_combo = ttk.Combobox(
                control_container,
                textvariable=shape_var,
                values=['rectangle', 'circle'],
                state='readonly',
                width=10  # Further increased width
            )
            shape_combo.pack(side=tk.LEFT, padx=5)
            
            # Add proper event binding to ensure variable updates
            # Simplified shape selection handling without debug prints
            def on_shape_select(event, idx=i):
                shape_var.set(shape_combo.get())
            shape_combo.bind('<<ComboboxSelected>>', on_shape_select)
            
            # Size spinboxes with default values from preferences
            width_var = tk.StringVar(value=str(default_settings['width']))
            height_var = tk.StringVar(value=str(default_settings['height']))
            
            # Add traces to debug when values change
            # Remove redundant width/height change debug prints
            width_var.trace('w', lambda *args: None)
            height_var.trace('w', lambda *args: None)
            
            # Size controls in the centered container
            width_entry = ttk.Entry(control_container, textvariable=width_var, width=4)
            width_entry.pack(side=tk.LEFT, padx=3)
            ttk.Label(control_container, text="×", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
            height_entry = ttk.Entry(control_container, textvariable=height_var, width=4)
            height_entry.pack(side=tk.LEFT, padx=3)
            
            # Add event bindings to ensure variables update when user types
            def on_width_entry_change(event, idx=i):
                try:
                    new_value = width_entry.get()
                    width_var.set(new_value)
                except tk.TclError:
                    pass
            
            def on_height_entry_change(event, idx=i):
                try:
                    new_value = height_entry.get()
                    height_var.set(new_value)
                except tk.TclError:
                    pass
            
            width_entry.bind('<KeyRelease>', on_width_entry_change)
            width_entry.bind('<FocusOut>', on_width_entry_change)
            height_entry.bind('<KeyRelease>', on_height_entry_change)
            height_entry.bind('<FocusOut>', on_height_entry_change)
            
            # Set initial values to current defaults (will be overridden by preferences above)
            width_var.set(str(default_settings['width']))
            height_var.set(str(default_settings['height']))
            
            # Anchor position with default from preferences
            anchor_var = tk.StringVar(value=default_settings['anchor'])
            anchor_combo = ttk.Combobox(
                control_container,
                textvariable=anchor_var,
                values=['center', 'top_left', 'top_right', 'bottom_left', 'bottom_right'],
                state='readonly',
                width=14  # Further increased width to show full text
            )
            anchor_combo.pack(side=tk.LEFT, padx=5)
            
            # Add proper event binding for anchor combobox
            def on_anchor_select(event, idx=i):
                selected_value = anchor_combo.get()
                anchor_var.set(selected_value)
                print(f"DEBUG: Sample {idx+1} anchor changed to: {selected_value}")
            anchor_combo.bind('<<ComboboxSelected>>', on_anchor_select)
            
            # Store all control variables
            self.sample_controls.append({
                'frame': frame,
                'shape': shape_var,
                'width': width_var,
                'height': height_var,
                'anchor': anchor_var
            })
        
        # Sample set buttons inside the scrollable area
        button_frame = ttk.Frame(self.sample_scrollable_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Center-align the main buttons
        button_container = ttk.Frame(button_frame)
        button_container.pack(expand=True, anchor=tk.CENTER)
        
        print("DEBUG: Creating Save button with command=self._save_sample_set")
        self.save_sample_button = ttk.Button(button_container, text="Save", command=self._save_sample_set, width=5)
        self.save_sample_button.pack(side=tk.LEFT, padx=1)
        print("DEBUG: Save button created and packed")
        
        # Add Update Template button
        self.update_sample_button = ttk.Button(button_container, text="Update", command=self._update_sample_set, width=6)
        self.update_sample_button.pack(side=tk.LEFT, padx=1)
        
        self.delete_sample_button = ttk.Button(button_container, text="Delete", command=self._delete_sample_set, width=5)
        self.delete_sample_button.pack(side=tk.LEFT, padx=1)
        
        self.clear_sample_button = ttk.Button(button_container, text="Clear", command=self._clear_samples, width=5)
        self.clear_sample_button.pack(side=tk.LEFT, padx=1)
        
        # Add color analysis button in a separate row
        analysis_frame = ttk.Frame(button_frame)
        analysis_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Create 2x2 button grid for all 4 functions
        button_grid = ttk.Frame(analysis_frame)
        button_grid.pack(pady=2)
        
        # Row 1: Original functions
        row1 = ttk.Frame(button_grid)
        row1.pack(fill=tk.X, pady=1)
        
        analyze_btn = ttk.Button(
            row1,
            text="🔬 Analyze",
            command=self._analyze_colors,
            width=12
        )
        analyze_btn.pack(side=tk.LEFT, padx=1)
        
        spreadsheet_btn = ttk.Button(
            row1,
            text="📊 View Data",
            command=self._view_spreadsheet,
            width=12
        )
        spreadsheet_btn.pack(side=tk.LEFT, padx=1)
        
        # Row 2: Library functions
        row2 = ttk.Frame(button_grid)
        row2.pack(fill=tk.X, pady=1)
        
        compare_btn = ttk.Button(
            row2,
            text="🔍 Compare",
            command=self._compare_to_libraries,
            width=12
        )
        compare_btn.pack(side=tk.LEFT, padx=1)
        
        manage_btn = ttk.Button(
            row2,
            text="📚 Libraries",
            command=self._open_color_library_manager,
            width=12
        )
        manage_btn.pack(side=tk.LEFT, padx=1)
        
        # Row 3: Add to Library function
        row3 = ttk.Frame(button_grid)
        row3.pack(fill=tk.X, pady=1)
        
        row3_buttons = ttk.Frame(row3)
        row3_buttons.pack(fill=tk.X, pady=1)
        
        add_to_lib_btn = ttk.Button(
            row3_buttons,
            text="📖 Add to Library",
            command=self._add_analysis_to_library,
            width=25
        )
        add_to_lib_btn.pack(padx=1)
        
        # Removed verbose help text to save space
        
        # Removed redundant library selection from main controls
        
        # Fine-tune positioning frame
        self.fine_tune_frame = ttk.LabelFrame(button_frame, text="Fine-Tune Positioning")
        self.fine_tune_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Add flag to prevent multiple simultaneous operations
        self._offset_operation_in_progress = False
        
        # Global offset controls - very compact
        global_frame = ttk.Frame(self.fine_tune_frame)
        global_frame.pack(fill=tk.X, padx=3, pady=1)
        
        ttk.Label(global_frame, text="Global:", width=6).pack(side=tk.LEFT)
        
        self.global_x_offset = tk.IntVar(value=0)
        self.global_y_offset = tk.IntVar(value=0)
        
        ttk.Label(global_frame, text="X:").pack(side=tk.LEFT, padx=(2, 0))
        self.global_x_spinbox = ttk.Spinbox(
            global_frame, from_=-10, to=10, textvariable=self.global_x_offset, width=3
        )
        self.global_x_spinbox.pack(side=tk.LEFT, padx=(0, 2))
        
        ttk.Label(global_frame, text="Y:").pack(side=tk.LEFT)
        self.global_y_spinbox = ttk.Spinbox(
            global_frame, from_=-10, to=10, textvariable=self.global_y_offset, width=3
        )
        self.global_y_spinbox.pack(side=tk.LEFT, padx=(0, 2))
        
        self.global_apply_btn = ttk.Button(
            global_frame, text="Apply", command=self._apply_global_offset_safe, width=4
        )
        self.global_apply_btn.pack(side=tk.LEFT, padx=(1, 0))
        
        # Individual adjustment controls - very compact to match Global
        individual_frame = ttk.Frame(self.fine_tune_frame)
        individual_frame.pack(fill=tk.X, padx=3, pady=1)
        
        ttk.Label(individual_frame, text="Individual:", width=6).pack(side=tk.LEFT)
        
        self.selected_sample = tk.IntVar(value=1)
        sample_combo = ttk.Combobox(
            individual_frame, textvariable=self.selected_sample,
            values=[1, 2, 3, 4, 5], state='readonly', width=1
        )
        sample_combo.pack(side=tk.LEFT, padx=(2, 2))
        
        self.individual_x_offset = tk.IntVar(value=0)
        self.individual_y_offset = tk.IntVar(value=0)
        
        ttk.Label(individual_frame, text="X:").pack(side=tk.LEFT, padx=(2, 0))
        self.individual_x_spinbox = ttk.Spinbox(
            individual_frame, from_=-10, to=10, textvariable=self.individual_x_offset, width=3
        )
        self.individual_x_spinbox.pack(side=tk.LEFT, padx=(0, 2))
        
        ttk.Label(individual_frame, text="Y:").pack(side=tk.LEFT)
        self.individual_y_spinbox = ttk.Spinbox(
            individual_frame, from_=-10, to=10, textvariable=self.individual_y_offset, width=3
        )
        self.individual_y_spinbox.pack(side=tk.LEFT, padx=(0, 2))
        
        self.individual_apply_btn = ttk.Button(
            individual_frame, text="Apply", command=self._apply_individual_offset_safe, width=4
        )
        self.individual_apply_btn.pack(side=tk.LEFT, padx=(1, 0))
        
        # Reset and status row
        reset_frame = ttk.Frame(self.fine_tune_frame)
        reset_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.reset_all_btn = ttk.Button(
            reset_frame, text="Reset All", command=self._reset_all_offsets_safe, width=8
        )
        self.reset_all_btn.pack(side=tk.LEFT)
        
        self.offset_status = tk.StringVar(value="No offsets applied")
        status_label = ttk.Label(
            reset_frame, textvariable=self.offset_status, font=("Arial", 9), foreground="blue", width=25
        )
        status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Fine-tune controls are shown when sample mode is active

    def _update_tool_context(self, mode: str):
        """Show/hide tool-specific controls based on current mode."""
        # Hide all context-sensitive frames
        self.crop_frame.pack_forget()
        self.straightening_frame.pack_forget()
        self.sample_frame.pack_forget()
        
        # Show the relevant frame for the current mode
        if mode == "crop":
            self.crop_frame.pack(fill=tk.X, padx=5, pady=2)
        elif mode == "straighten":
            self.straightening_frame.pack(fill=tk.X, padx=5, pady=2)
        elif mode == "coord":
            self.sample_frame.pack(fill=tk.X, padx=5, pady=2)
        # View mode shows no additional controls (clean interface)

    def _on_tool_mode_change(self):
        """Handle tool mode changes."""
        mode = self.tool_mode.get()
        self._update_tool_context(mode)
        
        # Call the original callback
        if self.on_tool_mode_change:
            self.on_tool_mode_change(mode)


    def _on_line_color_change(self):
        """Handle line color changes."""
        if self.on_line_color_change:
            self.on_line_color_change(self.line_color.get())

    def open_recent(self):
        """Show dialog to open a file from the Recent directory."""
        # Get the application's data directory from environment
        stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
        if not stampz_data_dir:
            stampz_data_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'StampZ_II')
        recent_dir = os.path.join(stampz_data_dir, 'recent')
        
        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title("Open Recent File")
        dialog.transient(self)
        dialog.grab_set()

        # Set dialog size and position
        dialog_width = 500
        dialog_height = 300
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # Create listbox with scrollbar
        frame = ttk.Frame(dialog)
        frame.pack(expand=True, fill='both', padx=5, pady=5)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')

        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
        listbox.pack(side='left', fill='both', expand=True)

        scrollbar.config(command=listbox.yview)

        # Get list of recent files
        try:
            # Get files and their modification times
            files = [(f, os.path.getmtime(os.path.join(recent_dir, f))) 
                    for f in os.listdir(recent_dir) 
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff'))]
            # Sort by modification time, newest first
            sorted_files = sorted(files, key=lambda x: x[1], reverse=True)
            for file, _ in sorted_files:
                listbox.insert('end', file)

            if not files:
                messagebox.showinfo("No Files", "No image files found in Recent directory")
                dialog.destroy()
                return
        except Exception as e:
            messagebox.showerror("Error", f"Could not access Recent directory:\n{str(e)}")
            dialog.destroy()
            return

        # Create buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=5, pady=5)

        def open_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a file to open")
                return
            
            selected_file = listbox.get(selection[0])
            # Use the correct Application Support path
            file_path = os.path.join(recent_dir, selected_file)
            
            if os.path.exists(file_path):
                try:
                    # Load the image directly from Recent folder
                    image, metadata = load_image(file_path)
                    dialog.destroy()
                    self.main_app.canvas.load_image(image)
                    self.main_app.current_file = file_path
                    self.main_app.current_image_metadata = metadata  # Store metadata for later use
                    self.main_app.control_panel.enable_controls(True)
                    base_filename = os.path.basename(file_path)
                    self.main_app.root.title(f"StampZ_II - {base_filename}")
                    self.main_app.control_panel.update_current_filename(file_path)
                except ImageLoadError as e:
                    messagebox.showerror("Error", str(e))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image: {str(e)}")
            else:
                messagebox.showerror("Error", f"File not found:\n{file_path}")

        def delete_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a file to delete")
                return
            
            selected_file = listbox.get(selection[0])
            # Use the correct Application Support path
            file_path = os.path.join(recent_dir, selected_file)
            
            if messagebox.askyesno("Confirm Delete", f"Delete {selected_file}?"):
                try:
                    os.remove(file_path)
                    listbox.delete(selection)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete file:\n{str(e)}")

        ttk.Button(btn_frame, text="Open", command=open_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete", command=delete_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='right', padx=5)

        # Bind double-click and Enter to open
        listbox.bind('<Double-Button-1>', lambda e: open_selected())
        dialog.bind('<Return>', lambda e: open_selected())
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def _on_ruler_toggle(self):
        """Handle ruler visibility toggle."""
        if self.on_ruler_toggle:
            self.on_ruler_toggle(self.show_rulers.get())
    def _on_ruler_toggle(self):
        """Handle ruler visibility toggle."""
        if self.on_ruler_toggle:
            self.on_ruler_toggle(self.show_rulers.get())

    def _on_grid_toggle(self):
        """Handle grid visibility toggle."""
        if self.on_grid_toggle:
            self.on_grid_toggle(self.show_grid.get())

    def _adjust_vertex_count(self, delta: int):
        """Adjust vertex count by delta."""
        current = self.vertex_count.get()
        new_count = max(3, min(8, current + delta))
        self.vertex_count.set(new_count)
        self._on_vertex_count_change()

    def _on_vertex_count_change(self):
        """Handle vertex count changes."""
        if self.on_vertex_count_change:
            self.on_vertex_count_change(self.vertex_count.get())
        
        # Enable/disable Rectangle controls based on vertex count
        current_vertices = self.canvas.get_vertices() if hasattr(self, 'canvas') and self.canvas else []
        if len(current_vertices) == 4:
            # Calculate center of vertices
            min_x = min(v.x for v in current_vertices)
            max_x = max(v.x for v in current_vertices)
            min_y = min(v.y for v in current_vertices)
            max_y = max(v.y for v in current_vertices)
            
            # Set width/height based on vertex bounds
            width = int(max_x - min_x)
            height = int(max_y - min_y)
            
            # Update spinboxes
            self.rect_width.set(width)
            self.rect_height.set(height)
            
            # Show rectangle controls
            self.rect_select_btn.config(state='normal')
        else:
            # Hide rectangle controls
            self.rect_select_btn.config(state='disabled')

    # Utility methods for updating displays
    def update_current_filename(self, filename: str):
        """Update the current filename display."""
        import os
        if filename:
            base_filename = os.path.basename(filename)
            self.current_filename.set(base_filename)
        else:
            self.current_filename.set("No file loaded")

    def update_mouse_coordinates(self, x: int, y: int):
        """Update mouse coordinate display with single decimal precision."""
        self.mouse_x.set(f"{x:.1f}")
        self.mouse_y.set(f"{y:.1f}")

    def update_crop_dimensions(self, width: int, height: int):
        """Update crop dimension display."""
        self.crop_width.set(str(width))
        self.crop_height.set(str(height))
        self.crop_area.set(f"{width * height:,}")

    def update_straightening_status(self, num_points: int, angle: float = None):
        """Update straightening status display."""
        self.straightening_points.set(str(num_points))
        if angle is not None:
            self.straightening_angle.set(f"{angle:.1f}°")
        else:
            self.straightening_angle.set("--")
        
        # Enable/disable apply button
        self.straighten_apply_button.config(state='normal' if num_points >= 2 else 'disabled')

    def get_save_options(self) -> SaveOptions:
        """Get current save options."""
        return SaveOptions(
            format=self.save_format.get(),
            jpeg_quality=95,  # Not used for TIFF/PNG but kept for compatibility
            optimize=True
        )

    # Callback methods that will be connected to main app functionality
    def _on_fine_square_click(self):
        """Handle fine square button click."""
        print("DEBUG: Fine square button clicked")
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_apply_fine_square'):
                print("DEBUG: Calling main_app._apply_fine_square()")
                self.main_app._apply_fine_square()
            else:
                print("DEBUG: Error - main_app._apply_fine_square method not found")
                messagebox.showinfo("Info", "Fine square method not found in main app")
        else:
            print("DEBUG: Error - main_app not found for fine square")
            messagebox.showinfo("Info", "Fine square tool - connect to main app implementation")

    def _apply_straightening(self):
        """Handle apply straightening button click."""
        # This will be connected to the main app's straightening functionality
        if hasattr(self, 'main_app') and self.main_app:
            self.main_app._apply_straightening()
        else:
            messagebox.showinfo("Info", "Apply straightening - connect to main app implementation")

    def _clear_straightening_points(self):
        """Handle clear straightening points button click."""
        # This will be connected to the main app's straightening functionality
        if hasattr(self, 'main_app') and self.main_app:
            self.main_app._clear_straightening_points()
        else:
            messagebox.showinfo("Info", "Clear straightening points - connect to main app implementation")

    def _on_sample_mode_change(self):
        """Handle sample mode changes between template and manual."""
        mode = self.sample_mode.get()
# Use the same UI for both manual and template modes
        self._set_template_mode_ui()
        
        # Ensure MAN_MODE is set for Manual Mode
        if mode == "manual":
            self.sample_set_name.set("MAN_MODE")
    
    
    def _set_template_mode_ui(self):
        """Configure UI for template mode."""
        # Hide manual controls if they exist
        if hasattr(self, 'manual_controls_frame'):
            self.manual_controls_frame.pack_forget()
        
        # Show individual sample controls in template mode
        for control in self.sample_controls:
            control['frame'].pack(fill=tk.X, padx=1, pady=0)
        
        # Show template-specific buttons (Save/Load)
        self.save_sample_button.pack(side=tk.LEFT, padx=1)
        self.load_sample_button.pack(side=tk.LEFT, padx=1)
        
        # Enable template entry first
        self.template_entry.configure(state='normal')
        
        # Clear MAN_MODE if present
        if self.sample_set_name.get().strip() == "MAN_MODE":
            self.sample_set_name.set("")
        
        # Keep entry enabled and set focus
        self.template_entry.focus_set()
    
        

    def _auto_generate_analysis_name(self):
        """Auto-generate analysis name using image filename and template name.
        For library additions, simply use 'library' as the analysis name."""
        # Check if this is a library addition
        sample_set = self.sample_set_name.get().strip().lower()
        if 'library' in sample_set:
            # This is a library addition - use simple name
            self.analysis_name.set('library')
            return
        
        # Regular analysis name generation
        image_name = ""
        if hasattr(self, 'main_app') and self.main_app and hasattr(self.main_app, 'current_file'):
            if self.main_app.current_file:
                import os
                # Get just the filename without extension
                image_name = os.path.splitext(os.path.basename(self.main_app.current_file))[0]
        
        # Build analysis name
        if image_name and sample_set:
            # Both image and template name available: "image_template"
            self.analysis_name.set(f"{image_name}_{sample_set}")
        elif image_name:
            # Only image name available
            self.analysis_name.set(image_name)
        elif sample_set:
            # Only template name available
            self.analysis_name.set(sample_set)
        else:
            # Fallback to timestamp if neither available
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.analysis_name.set(f"analysis_{timestamp}")

    def _analyze_colors(self):
        """Handle analyze colors button click."""
        print("DEBUG: _analyze_colors called")
        
        # Check template protection before proceeding with analysis
        if hasattr(self, 'template_protection'):
            print(f"DEBUG: Template protection exists - is_protected: {self.template_protection.is_protected}")
            print(f"DEBUG: Template protection - has_modifications: {self.template_protection.has_modifications()}")
            print(f"DEBUG: Template protection - original_template_name: '{self.template_protection.original_template_name}'")
            
            if not self.template_protection.check_before_analyze():
                print("DEBUG: Analysis blocked by template protection")
                return
            else:
                print("DEBUG: Template protection check passed - proceeding with analysis")
        else:
            print("DEBUG: No template protection manager found")
        
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_analyze_colors'):
                print("DEBUG: Calling main_app._analyze_colors()")
                # Call analyze colors without print type parameter
                self.main_app._analyze_colors()
            else:
                print("DEBUG: main_app._analyze_colors method NOT found")
                messagebox.showinfo("Info", "Analyze colors method not found in main app")
        else:
            print("DEBUG: main_app not found for analyze colors")
            messagebox.showinfo("Info", "Analyze colors - connect to main app implementation")

    def _view_spreadsheet(self):
        """Handle view spreadsheet button click."""
        print("DEBUG: _view_spreadsheet called")
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_view_spreadsheet'):
                print("DEBUG: Calling main_app._view_spreadsheet()")
                self.main_app._view_spreadsheet()
            else:
                print("DEBUG: main_app._view_spreadsheet method NOT found")
                messagebox.showinfo("Info", "View spreadsheet method not found in main app")
        else:
            print("DEBUG: main_app not found for view spreadsheet")
            messagebox.showinfo("Info", "View spreadsheet - connect to main app implementation")
    
    # Additional callback methods for compatibility with main app
    def enable_controls(self, enabled: bool):
        """Enable or disable controls based on image state."""
        # This method is called by main app when image is loaded/unloaded
        # We can disable/enable specific controls as needed
        pass
    
    def update_filename(self, filename: str):
        """Update filename display (compatibility method)."""
        self.update_current_filename(filename)
    
    def get_save_format(self) -> str:
        """Get current save format (compatibility method)."""
        return self.save_format.get()
    
    def get_jpeg_quality(self) -> int:
        """Get current JPEG quality (compatibility method)."""
        return self.jpg_quality.get()
    
    def get_vertex_count(self) -> int:
        """Get current vertex count (compatibility method)."""
        return self.vertex_count.get()
    
    def get_transparency(self) -> int:
        """Get current transparency value (compatibility method)."""
        return self.mask_transparency.get()
    
    def get_tool_mode(self) -> str:
        """Get current tool mode (compatibility method)."""
        return self.tool_mode.get()
    
    def get_line_color(self) -> str:
        """Get current line color (compatibility method)."""
        return self.line_color.get()
    
    def is_manual_mode(self) -> bool:
        """Check if sample tool is in manual mode (compatibility method)."""
        return self.sample_mode.get() == "manual"
    
    def get_applied_settings(self, sample_index: int) -> dict:
        """Get applied settings for a specific sample index (compatibility method)."""
        if sample_index < len(self.sample_controls):
            control = self.sample_controls[sample_index]
            return {
                'sample_type': control['shape'].get(),
                'width': float(control['width'].get()),
                'height': float(control['height'].get()),
                'anchor': control['anchor'].get()
            }
        else:
            # Return default settings for sample indices beyond our controls
                return {
                    'sample_type': 'circle',
                    'width': 10,
                    'height': 10,
                    'anchor': 'center'
                }
    
    def get_manual_sample_settings(self) -> dict:
        """Get manual mode sample settings by using the first row of sample controls."""
        if len(self.sample_controls) > 0:
            control = self.sample_controls[0]  # Use first row settings for manual mode
            try:
                width = float(control['width'].get())
                height = float(control['height'].get())
                return {
                    'sample_type': control['shape'].get(),
                    'width': width,
                    'height': height,
                    'anchor': control['anchor'].get()
                }
            except (ValueError, tk.TclError) as e:
                print(f"DEBUG: Error reading control values, using defaults: {e}")

        # Return defaults if no controls or error reading values
        return {
            'sample_type': 'circle',
            'width': 10,
            'height': 10,
            'anchor': 'center'
        }
    
    def update_sample_controls_from_coordinates(self, coordinates):
        """Update the sample control UI to show loaded coordinate settings."""
        print(f"DEBUG: Updating sample controls for {len(coordinates)} coordinates")
        
        # Update each sample control with the loaded coordinate data
        for i, coord in enumerate(coordinates[:5]):  # Limit to 5 sample areas
            if i < len(self.sample_controls):
                control = self.sample_controls[i]
                
                # Update shape type
                shape_type = 'circle' if coord.sample_type.value == 'circle' else 'rectangle'
                control['shape'].set(shape_type)
                
                # Update dimensions
                control['width'].set(str(int(coord.sample_size[0])))
                if coord.sample_type.value == 'circle':
                    control['height'].set(str(int(coord.sample_size[0])))  # Circle uses width for both
                else:
                    control['height'].set(str(int(coord.sample_size[1])))
                
                # Update anchor position
                control['anchor'].set(coord.anchor_position)
                
                print(f"DEBUG: Updated sample {i+1}: {shape_type} {coord.sample_size[0]}x{coord.sample_size[1]} {coord.anchor_position}")
        
        # After updating controls, protect the loaded template
        template_name = self.sample_set_name.get().strip()
        if template_name and template_name != "MAN_MODE":
            print(f"DEBUG: Protecting loaded template '{template_name}'")
            self.template_protection.protect_template(template_name, coordinates)
    
    # Sample tool callback methods
    def _standardize_template_name(self, event=None):
        """Standardize template name for consistency."""
        # Placeholder for template name standardization
        pass
    
    def _apply_sample(self, idx: int):
        """Apply sample settings for sample index."""
        # This will be connected to the main app's sample functionality
        if hasattr(self, 'main_app') and self.main_app:
            # Call main app method if available
            if hasattr(self.main_app, '_apply_sample'):
                self.main_app._apply_sample(idx)
        else:
            print(f"Apply sample {idx+1} - connect to main app implementation")
    
    def _edit_sample(self, idx: int):
        """Edit sample settings for sample index."""
        # Show warning about editing
        if not messagebox.askyesno(
            "Edit Sample",
            "You are about to edit this sample's position and size.\n" +
            "When saved, the original sample coordinates will be replaced.\n\n" +
            "Do you want to proceed?"
        ):
            return
            
        # Call main app's edit method if available
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_edit_sample'):
                print(f"DEBUG: Calling main_app._edit_sample({idx})")
                self.main_app._edit_sample(idx)
            else:
                print("DEBUG: main_app._edit_sample method NOT found")
                messagebox.showinfo("Info", "Edit sample method not found in main app")
        else:
            print("DEBUG: main_app not found for edit sample")
            messagebox.showinfo("Info", "Edit sample - connect to main app implementation")
    
    def _save_sample_set(self):
        """Save sample set template with protection logic."""
        print("DEBUG: _save_sample_set() called in controls_reorganized.py")
        
        # Check template protection first
        if not self.template_protection.handle_protected_save():
            print("DEBUG: Save cancelled due to template protection")
            return
        
        print(f"DEBUG: hasattr(self, 'main_app') = {hasattr(self, 'main_app')}")
        if hasattr(self, 'main_app'):
            print(f"DEBUG: self.main_app = {self.main_app}")
            print(f"DEBUG: hasattr(self.main_app, '_save_sample_set') = {hasattr(self.main_app, '_save_sample_set')}")
        
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_save_sample_set'):
                print("DEBUG: Calling self.main_app._save_sample_set()")
                self.main_app._save_sample_set()
            else:
                print("DEBUG: main_app._save_sample_set method not found")
                messagebox.showinfo("Info", "Save sample set method not found in main app")
        else:
            print("DEBUG: main_app not found or not set")
            messagebox.showinfo("Info", "Save sample set - connect to main app implementation")
    
    def _update_sample_set(self):
        """Update existing template with current changes (positions and settings)."""
        print("DEBUG: _update_sample_set() called in controls_reorganized.py")
        
        # Check if we have a template name to update
        template_name = self.sample_set_name.get().strip()
        if not template_name:
            messagebox.showwarning(
                "No Template Selected",
                "Please load or enter a template name before updating."
            )
            return
        
        # Don't allow updating MAN_MODE
        if template_name == "MAN_MODE":
            messagebox.showwarning(
                "Cannot Update Manual Mode",
                "Manual mode samples cannot be updated. Use Save to create a new template."
            )
            return
        
        # Check if template exists in database
        try:
            from utils.coordinate_db import CoordinateDB
            db = CoordinateDB()
            existing_sets = db.get_all_set_names()
            
            if template_name not in existing_sets:
                # Template doesn't exist - suggest using Save instead
                if messagebox.askyesno(
                    "Template Not Found",
                    f"Template '{template_name}' doesn't exist in the database.\n\n"
                    "Would you like to save it as a new template instead?"
                ):
                    self._save_sample_set()
                return
        except Exception as e:
            print(f"DEBUG: Error checking existing templates: {e}")
            messagebox.showerror("Error", f"Failed to check existing templates: {str(e)}")
            return
        
        # Confirm the update operation
        if not messagebox.askyesno(
            "Update Template",
            f"Are you sure you want to update template '{template_name}'?\n\n"
            "This will overwrite the existing template with:\n"
            "• Current marker positions (including fine adjustments)\n"
            "• Current shape, size, and anchor settings\n\n"
            "This action cannot be undone."
        ):
            return
        
        # Call main app update method
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_update_sample_set'):
                print("DEBUG: Calling self.main_app._update_sample_set()")
                self.main_app._update_sample_set()
            else:
                print("DEBUG: main_app._update_sample_set method not found")
                messagebox.showinfo("Info", "Update sample set method not found in main app")
        else:
            print("DEBUG: main_app not found or not set")
            messagebox.showinfo("Info", "Update sample set - connect to main app implementation")
    
    def _load_sample_set(self):
        """Load sample set template."""
        print("DEBUG: _load_sample_set called - starting load process")
        if hasattr(self, 'main_app') and self.main_app:
            print("DEBUG: main_app found, checking for _load_sample_set method")
            if hasattr(self.main_app, '_load_sample_set'):
                print("DEBUG: main_app._load_sample_set method found, calling it")
                self.main_app._load_sample_set()
            else:
                print("DEBUG: main_app._load_sample_set method NOT found")
                messagebox.showinfo("Info", "Load sample set method not found in main app")
        else:
            print("DEBUG: main_app not found or not set")
            messagebox.showinfo("Info", "Load sample set - connect to main app implementation")
            
    
    def _clear_samples(self):
        """Clear all sample areas."""
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_clear_samples'):
                self.main_app._clear_samples()
        else:
            messagebox.showinfo("Info", "Clear samples - connect to main app implementation")
            
    def _delete_sample_set(self):
        """Delete sample set template."""
        # Get the currently selected template name
        template_name = self.sample_set_name.get().strip()
        if not template_name:
            messagebox.showwarning("No Template Selected", "Please select a template to delete.")
            return
            
        # Confirm deletion with user
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the template '{template_name}'?\n\n" +
            "This action cannot be undone."
        ):
            return
            
        try:
            # Delete the template from the database
            from utils.coordinate_db import CoordinateDB
            db = CoordinateDB()
            if db.delete_coordinate_set(template_name):
                # Clear current selection
                self.sample_set_name.set('')
                
                # Refresh the dropdown list
                self._refresh_sample_sets()
                
                messagebox.showinfo(
                    "Success",
                    f"Template '{template_name}' has been deleted."
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"Could not delete template '{template_name}'."
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"An error occurred while deleting the template:\n\n{str(e)}"
            )
    
    def _compare_to_libraries(self):
        """Compare samples to color libraries."""
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, 'compare_sample_to_library'):
                print("DEBUG: Calling main_app.compare_sample_to_library()")
                self.main_app.compare_sample_to_library()
            else:
                print("DEBUG: main_app.compare_sample_to_library method NOT found")
                messagebox.showinfo("Info", "Compare to libraries method not found in main app")
        else:
            print("DEBUG: main_app not found for compare to libraries")
            messagebox.showinfo("Info", "Compare to libraries - connect to main app implementation")
    
    def _open_color_library_manager(self):
        """Open color library manager."""
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, 'open_color_library'):
                print("DEBUG: Calling main_app.open_color_library()")
                self.main_app.open_color_library()
            else:
                print("DEBUG: main_app.open_color_library method NOT found")
                messagebox.showinfo("Info", "Color library manager method not found in main app")
        else:
            print("DEBUG: main_app not found for color library manager")
            messagebox.showinfo("Info", "Color library manager - connect to main app implementation")
    
    def _apply_global_offset(self):
        """Apply global position offset to all samples."""
        print(f"DEBUG: _apply_global_offset called with X={self.global_x_offset.get()}, Y={self.global_y_offset.get()}")
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_apply_global_offset'):
                print("DEBUG: Calling main_app._apply_global_offset()")
                self.main_app._apply_global_offset()
            else:
                print("DEBUG: main_app._apply_global_offset method NOT found")
                messagebox.showinfo("Info", "Apply global offset method not found in main app")
        else:
            print("DEBUG: main_app not found for global offset")
            messagebox.showinfo("Info", "Apply global offset - connect to main app implementation")
    
    def _apply_individual_offset(self):
        """Apply individual position offset to selected sample."""
        print(f"DEBUG: _apply_individual_offset called with sample={self.selected_sample.get()}, X={self.individual_x_offset.get()}, Y={self.individual_y_offset.get()}")
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_apply_individual_offset'):
                print("DEBUG: Calling main_app._apply_individual_offset()")
                self.main_app._apply_individual_offset()
            else:
                print("DEBUG: main_app._apply_individual_offset method NOT found")
                messagebox.showinfo("Info", "Apply individual offset method not found in main app")
        else:
            print("DEBUG: main_app not found for individual offset")
            messagebox.showinfo("Info", "Apply individual offset - connect to main app implementation")
    
    def _reset_all_offsets(self):
        """Reset all position offsets."""
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_reset_all_offsets'):
                self.main_app._reset_all_offsets()
        else:
            self.global_x_offset.set(0)
            self.global_y_offset.set(0)
            self.individual_x_offset.set(0)
            self.individual_y_offset.set(0)
            self.offset_status.set("No offsets applied")
            messagebox.showinfo("Info", "Reset all offsets - connect to main app implementation")
    
    def _apply_global_offset_safe(self):
        """Apply global offset with operation lock to prevent UI conflicts."""
        if self._offset_operation_in_progress:
            print("DEBUG: Global offset operation already in progress, skipping")
            return
        
        try:
            self._offset_operation_in_progress = True
            self.global_apply_btn.config(state='disabled')
            self.individual_apply_btn.config(state='disabled')
            self.reset_all_btn.config(state='disabled')
            
            # Disable spinboxes during operation
            self.global_x_spinbox.config(state='disabled')
            self.global_y_spinbox.config(state='disabled')
            self.individual_x_spinbox.config(state='disabled')
            self.individual_y_spinbox.config(state='disabled')
            
            self._apply_global_offset()
            
        finally:
            # Re-enable controls
            self._offset_operation_in_progress = False
            self.global_apply_btn.config(state='normal')
            self.individual_apply_btn.config(state='normal')
            self.reset_all_btn.config(state='normal')
            
            self.global_x_spinbox.config(state='normal')
            self.global_y_spinbox.config(state='normal')
            self.individual_x_spinbox.config(state='normal')
            self.individual_y_spinbox.config(state='normal')
    
    def _apply_individual_offset_safe(self):
        """Apply individual offset with operation lock to prevent UI conflicts."""
        if self._offset_operation_in_progress:
            print("DEBUG: Individual offset operation already in progress, skipping")
            return
        
        try:
            self._offset_operation_in_progress = True
            self.global_apply_btn.config(state='disabled')
            self.individual_apply_btn.config(state='disabled')
            self.reset_all_btn.config(state='disabled')
            
            # Disable spinboxes during operation
            self.global_x_spinbox.config(state='disabled')
            self.global_y_spinbox.config(state='disabled')
            self.individual_x_spinbox.config(state='disabled')
            self.individual_y_spinbox.config(state='disabled')
            
            self._apply_individual_offset()
            
        finally:
            # Re-enable controls
            self._offset_operation_in_progress = False
            self.global_apply_btn.config(state='normal')
            self.individual_apply_btn.config(state='normal')
            self.reset_all_btn.config(state='normal')
            
            self.global_x_spinbox.config(state='normal')
            self.global_y_spinbox.config(state='normal')
            self.individual_x_spinbox.config(state='normal')
            self.individual_y_spinbox.config(state='normal')
    
    def _reset_all_offsets_safe(self):
        """Reset all offsets with operation lock to prevent UI conflicts."""
        if self._offset_operation_in_progress:
            print("DEBUG: Reset offsets operation already in progress, skipping")
            return
        
        try:
            self._offset_operation_in_progress = True
            self.global_apply_btn.config(state='disabled')
            self.individual_apply_btn.config(state='disabled')
            self.reset_all_btn.config(state='disabled')
            
            # Disable spinboxes during operation
            self.global_x_spinbox.config(state='disabled')
            self.global_y_spinbox.config(state='disabled')
            self.individual_x_spinbox.config(state='disabled')
            self.individual_y_spinbox.config(state='disabled')
            
            self._reset_all_offsets()
            
        finally:
            # Re-enable controls
            self._offset_operation_in_progress = False
            self.global_apply_btn.config(state='normal')
            self.individual_apply_btn.config(state='normal')
            self.reset_all_btn.config(state='normal')
            
            self.global_x_spinbox.config(state='normal')
            self.global_y_spinbox.config(state='normal')
            self.individual_x_spinbox.config(state='normal')
            self.individual_y_spinbox.config(state='normal')
    
    def _get_available_sample_sets(self):
        """Get list of available sample set names from existing databases."""
        try:
            from utils.coordinate_db import CoordinateDB
            db = CoordinateDB()
            sets = db.get_all_set_names()
            pass  # Sample sets found silently
            return sorted(sets)  # Sort alphabetically for better UX
        except Exception as e:
            print(f"DEBUG: Error getting sample sets: {e}")
            return []  # Return empty list if there's an error
    
    def _refresh_sample_sets(self, show_feedback=True):
        """Refresh the sample set dropdown with current database contents.
        
        Args:
            show_feedback: Whether to show user feedback dialogs
        """
        try:
            # Get updated list of sample sets
            updated_sets = self._get_available_sample_sets()
            
            # Update the combobox values
            self.sample_set_combo['values'] = updated_sets
            
            # Show feedback to user if requested
            if show_feedback:
                if updated_sets:
                    messagebox.showinfo(
                        "Sample Sets Refreshed", 
                        f"Found {len(updated_sets)} sample sets:\n\n" + "\n".join(updated_sets[:10]) +
                        ("\n...and more" if len(updated_sets) > 10 else "")
                    )
                else:
                    messagebox.showinfo(
                        "Sample Sets Refreshed", 
                        "No existing sample sets found.\nCreate a new one by entering a name and saving."
                    )
            
            print(f"DEBUG: Refreshed sample set dropdown with {len(updated_sets)} sets (feedback: {show_feedback})")
            
        except Exception as e:
            print(f"DEBUG: Error refreshing sample sets: {e}")
            if show_feedback:
                messagebox.showerror(
                    "Refresh Error", 
                    f"Could not refresh sample set list:\n\n{str(e)}"
                )
    
    def _add_analysis_to_library(self):
        """Add color analysis results to a color library with user-friendly names."""
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, '_add_analysis_to_library'):
                print("DEBUG: Calling main_app._add_analysis_to_library()")
                self.main_app._add_analysis_to_library()
            else:
                print("DEBUG: main_app._add_analysis_to_library method NOT found")
                messagebox.showinfo("Info", "Add to library method not found in main app")
        else:
            print("DEBUG: main_app not found for add to library")
            messagebox.showinfo("Info", "Add to library - connect to main app implementation")
    
    def refresh_sample_defaults_from_preferences(self):
        """Refresh sample controls with current preference defaults."""
        print("DEBUG: Refreshing sample controls with current preferences")
        try:
            # Get current preference defaults
            from utils.user_preferences import get_preferences_manager
            prefs_manager = get_preferences_manager()
            default_settings = prefs_manager.get_default_sample_settings()
            
            print(f"DEBUG: New default settings: {default_settings}")
            
            # Update each sample control with the new defaults
            for i, control in enumerate(self.sample_controls):
                # Update shape
                control['shape'].set(default_settings['shape'])
                
                # Update width and height
                control['width'].set(str(default_settings['width']))
                control['height'].set(str(default_settings['height']))
                
                # Update anchor
                control['anchor'].set(default_settings['anchor'])
                
                print(f"DEBUG: Updated sample {i+1} with new defaults")
                
        except Exception as e:
            print(f"DEBUG: Error refreshing sample defaults: {e}")
            messagebox.showerror("Error", f"Failed to refresh sample defaults:\n{e}")
    
    def _open_database_viewer(self):
        """Open database viewer for examining color analysis data."""
        if hasattr(self, 'main_app') and self.main_app:
            if hasattr(self.main_app, 'open_database_viewer'):
                print("DEBUG: Calling main_app.open_database_viewer()")
                self.main_app.open_database_viewer()
            else:
                print("DEBUG: main_app.open_database_viewer method NOT found")
                messagebox.showinfo("Info", "Database viewer method not found in main app")
        else:
            print("DEBUG: main_app not found for database viewer")
            messagebox.showinfo("Info", "Database viewer - connect to main app implementation")
    
    # Zoom control methods
    def _on_zoom_change(self, value):
        """Handle zoom slider changes."""
        try:
            zoom_level = float(value)
            # Update zoom level through canvas
            if hasattr(self, 'main_app') and self.main_app and hasattr(self.main_app, 'canvas'):
                self.main_app.canvas.core.set_zoom_level(zoom_level)
                # Important: Update the full canvas display to redraw markers
                self.main_app.canvas.update_display()
            
            # Update display text
            percentage = int(zoom_level * 100)
            self.zoom_display.config(text=f"{percentage}%")
        except ValueError:
            pass
    
    def _zoom_in(self):
        """Zoom in by 20%."""
        current = self.zoom_level.get()
        new_zoom = min(10.0, current * 1.2)
        self.zoom_level.set(new_zoom)
        self._on_zoom_change(new_zoom)
    
    def _zoom_out(self):
        """Zoom out by 20%."""
        current = self.zoom_level.get()
        new_zoom = max(0.1, current / 1.2)
        self.zoom_level.set(new_zoom)
        self._on_zoom_change(new_zoom)
    
    def _reset_zoom(self):
        """Reset zoom to 100% (1.0)."""
        self.zoom_level.set(1.0)
        self._on_zoom_change(1.0)
    
    def update_zoom_display(self, zoom_level: float):
        """Update zoom display from external source (like mouse wheel)."""
        self.zoom_level.set(zoom_level)
        percentage = int(zoom_level * 100)
        self.zoom_display.config(text=f"{percentage}%")
    
