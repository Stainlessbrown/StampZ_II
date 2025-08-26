#!/usr/bin/env python3
"""
Collapsible Control Panel for StampZ
Provides a clean, expandable interface for managing tools and settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, Dict, Any
import logging

from utils.save_as import SaveOptions, SaveFormat
from gui.canvas import ShapeType

logger = logging.getLogger(__name__)

class CollapsibleSection(ttk.Frame):
    """A collapsible section widget that can expand/collapse its content."""
    
    def __init__(self, parent, title: str, expanded: bool = True):
        super().__init__(parent)
        
        self.title = title
        self.expanded = tk.BooleanVar(value=expanded)
        self.content_frame = None
        
        self._create_header()
        self._create_content()
        
        # Bind the expansion state
        self.expanded.trace('w', self._toggle_content)
    
    def _create_header(self):
        """Create the clickable header."""
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill=tk.X, pady=(0, 2))
        
        # Use a button-like frame for better click area
        self.header_button = ttk.Button(
            self.header_frame,
            text=self._get_header_text(),
            command=self._toggle_expanded,
            style="Header.TButton"
        )
        self.header_button.pack(fill=tk.X)
    
    def _create_content(self):
        """Create the content container."""
        self.content_frame = ttk.Frame(self)
        self._toggle_content()  # Apply initial state
    
    def _get_header_text(self) -> str:
        """Get the header text with expand/collapse indicator."""
        indicator = "▼" if self.expanded.get() else "►"
        return f"{indicator} {self.title}"
    
    def _toggle_expanded(self):
        """Toggle the expanded state."""
        self.expanded.set(not self.expanded.get())
    
    def _toggle_content(self, *args):
        """Show/hide content based on expanded state."""
        self.header_button.config(text=self._get_header_text())
        
        if self.expanded.get():
            self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        else:
            self.content_frame.pack_forget()
    
    def add_content(self, widget):
        """Add content to this section."""
        widget.configure(master=self.content_frame)
        return widget

class CollapsibleControlPanel(ttk.Frame):
    """Modern collapsible control panel with organized sections."""
    
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
        super().__init__(master, **kwargs)
        
        # Store callbacks
        self.callbacks = {
            'on_reset': on_reset,
            'on_open': on_open,
            'on_save': on_save,
            'on_quit': on_quit,
            'on_clear': on_clear,
            'on_vertex_count_change': on_vertex_count_change,
            'on_fit_to_window': on_fit_to_window,
            'on_transparency_change': on_transparency_change,
            'on_shape_type_change': on_shape_type_change,
            'on_tool_mode_change': on_tool_mode_change,
        }
        
        # Initialize variables
        self._init_variables()
        
        # Create collapsible sections
        self._create_sections()
        
        # Configure styles
        self._configure_styles()
    
    def _init_variables(self):
        """Initialize all control variables."""
        self.save_format = tk.StringVar(value=SaveFormat.TIFF)
        self.jpg_quality = tk.IntVar(value=95)
        self.vertex_count = tk.IntVar(value=4)
        self.mask_transparency = tk.IntVar(value=64)
        self.max_vertices = 8
        self.min_vertices = 3
        self.shape_type = tk.StringVar(value="polygon")
        self.line_color = tk.StringVar(value="white")
        self.tool_mode = tk.StringVar(value="view")
        
        # Display variables
        self.crop_width = tk.StringVar(value="--")
        self.crop_height = tk.StringVar(value="--")
        self.crop_area = tk.StringVar(value="--")
        self.mouse_x = tk.StringVar(value="--")
        self.mouse_y = tk.StringVar(value="--")
    
    def _configure_styles(self):
        """Configure custom styles for the collapsible interface."""
        style = ttk.Style()
        
        # Configure header button style
        style.configure(
            "Header.TButton",
            relief="flat",
            padding=(5, 3),
            anchor="w"
        )
        
        style.map(
            "Header.TButton",
            background=[('active', '#e1e1e1'), ('pressed', '#d1d1d1')]
        )
    
    def _create_sections(self):
        """Create all collapsible sections."""
        # Always visible: Quick Actions
        self._create_quick_actions()
        
        # Tool Mode (always expanded when in use)
        self.tool_section = CollapsibleSection(self, "Tool Mode", expanded=True)
        self.tool_section.pack(fill=tk.X, pady=2)
        self._create_tool_mode_section()
        
        # Current Status (always visible but compact)
        self.status_section = CollapsibleSection(self, "Status", expanded=True)
        self.status_section.pack(fill=tk.X, pady=2)
        self._create_status_section()
        
        # Tool Settings (context-sensitive)
        self.settings_section = CollapsibleSection(self, "Tool Settings", expanded=False)
        self.settings_section.pack(fill=tk.X, pady=2)
        self._create_settings_section()
        
        # Color Analysis (new section for color library)
        self.color_section = CollapsibleSection(self, "Color Analysis", expanded=False)
        self.color_section.pack(fill=tk.X, pady=2)
        self._create_color_analysis_section()
        
        # Advanced Tools (collapsed by default)
        self.advanced_section = CollapsibleSection(self, "Advanced Tools", expanded=False)
        self.advanced_section.pack(fill=tk.X, pady=2)
        self._create_advanced_section()
        
        # Save Options (collapsed by default)
        self.save_section = CollapsibleSection(self, "Save Options", expanded=False)
        self.save_section.pack(fill=tk.X, pady=2)
        self._create_save_section()
    
    def _create_quick_actions(self):
        """Create always-visible quick action buttons."""
        quick_frame = ttk.Frame(self)
        quick_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Main action buttons in a compact layout
        btn_frame1 = ttk.Frame(quick_frame)
        btn_frame1.pack(fill=tk.X, pady=1)
        
        ttk.Button(btn_frame1, text="Open", command=self.callbacks['on_open'], width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame1, text="Save", command=self.callbacks['on_save'], width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame1, text="Clear", command=self.callbacks['on_clear'], width=8).pack(side=tk.LEFT, padx=1)
        
        btn_frame2 = ttk.Frame(quick_frame)
        btn_frame2.pack(fill=tk.X, pady=1)
        
        ttk.Button(btn_frame2, text="Reset View", command=self.callbacks['on_reset'], width=12).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame2, text="Fit Window", command=self.callbacks['on_fit_to_window'], width=12).pack(side=tk.LEFT, padx=1)
    
    def _create_tool_mode_section(self):
        """Create tool mode selection."""
        content = self.tool_section.content_frame
        
        # Tool mode radio buttons in a grid
        modes = [
            ("View/Pan", "view"),
            ("Straighten", "straighten"),
            ("Crop", "crop"),
            ("Sample", "coord")
        ]
        
        for i, (text, value) in enumerate(modes):
            row = i // 2
            col = i % 2
            
            radio = ttk.Radiobutton(
                content,
                text=text,
                value=value,
                variable=self.tool_mode,
                command=self._on_tool_mode_change
            )
            radio.grid(row=row, column=col, sticky="w", padx=5, pady=1)
    
    def _create_status_section(self):
        """Create compact status display."""
        content = self.status_section.content_frame
        
        # Mouse coordinates (single line)
        coord_frame = ttk.Frame(content)
        coord_frame.pack(fill=tk.X, pady=1)
        
        ttk.Label(coord_frame, text="Mouse:", font=('Arial', 9)).pack(side=tk.LEFT)
        ttk.Label(coord_frame, textvariable=self.mouse_x, font=('Arial', 9, 'bold'), foreground='blue').pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(coord_frame, text=",", font=('Arial', 9)).pack(side=tk.LEFT)
        ttk.Label(coord_frame, textvariable=self.mouse_y, font=('Arial', 9, 'bold'), foreground='blue').pack(side=tk.LEFT, padx=(2, 5))
        
        # Crop dimensions (single line)
        crop_frame = ttk.Frame(content)
        crop_frame.pack(fill=tk.X, pady=1)
        
        ttk.Label(crop_frame, text="Crop:", font=('Arial', 9)).pack(side=tk.LEFT)
        ttk.Label(crop_frame, textvariable=self.crop_width, font=('Arial', 9, 'bold'), foreground='green').pack(side=tk.LEFT, padx=(5, 1))
        ttk.Label(crop_frame, text="×", font=('Arial', 9)).pack(side=tk.LEFT)
        ttk.Label(crop_frame, textvariable=self.crop_height, font=('Arial', 9, 'bold'), foreground='green').pack(side=tk.LEFT, padx=(1, 5))
    
    def _create_settings_section(self):
        """Create tool-specific settings."""
        content = self.settings_section.content_frame
        
        # Shape settings
        shape_frame = ttk.LabelFrame(content, text="Shape Settings")
        shape_frame.pack(fill=tk.X, pady=2)
        
        # Vertices
        vertex_frame = ttk.Frame(shape_frame)
        vertex_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(vertex_frame, text="Vertices:").pack(side=tk.LEFT)
        ttk.Scale(
            vertex_frame,
            from_=self.min_vertices,
            to=self.max_vertices,
            variable=self.vertex_count,
            orient=tk.HORIZONTAL,
            command=self._on_vertex_count_change,
            length=100
        ).pack(side=tk.LEFT, padx=5)
        ttk.Label(vertex_frame, textvariable=self.vertex_count).pack(side=tk.LEFT)
        
        # Transparency
        trans_frame = ttk.Frame(shape_frame)
        trans_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(trans_frame, text="Transparency:").pack(side=tk.LEFT)
        ttk.Scale(
            trans_frame,
            from_=0,
            to=255,
            variable=self.mask_transparency,
            orient=tk.HORIZONTAL,
            command=self._on_transparency_change,
            length=100
        ).pack(side=tk.LEFT, padx=5)
    
    def _create_color_analysis_section(self):
        """Create color analysis and library tools."""
        content = self.color_section.content_frame
        
        # Color Library Tools
        library_frame = ttk.Frame(content)
        library_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(
            library_frame,
            text="Color Library Manager",
            command=self._open_color_library
        ).pack(fill=tk.X, pady=1)
        
        ttk.Button(
            library_frame,
            text="Compare Sample to Library",
            command=self._compare_sample
        ).pack(fill=tk.X, pady=1)
        
        ttk.Button(
            library_frame,
            text="Export Color Analysis",
            command=self._export_color_analysis
        ).pack(fill=tk.X, pady=1)
        
        # Quick library selection
        lib_select_frame = ttk.Frame(content)
        lib_select_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lib_select_frame, text="Active Library:").pack(anchor="w")
        self.active_library = tk.StringVar(value="None")
        self.library_combo = ttk.Combobox(
            lib_select_frame,
            textvariable=self.active_library,
            state="readonly",
            width=20
        )
        self.library_combo.pack(fill=tk.X, pady=1)
        
        # Update library list
        self._update_library_list()
    
    def _create_advanced_section(self):
        """Create advanced tools section."""
        content = self.advanced_section.content_frame
        
        # Image processing tools
        ttk.Button(content, text="Auto Square Tool", command=self._apply_fine_square).pack(fill=tk.X, pady=1)
        ttk.Button(content, text="White Balance Correction", command=self._open_white_balance).pack(fill=tk.X, pady=1)
        ttk.Button(content, text="Straightening Tool", command=self._toggle_straightening).pack(fill=tk.X, pady=1)
    
    def _create_save_section(self):
        """Create save options section."""
        content = self.save_section.content_frame
        
        # Save format selection
        format_frame = ttk.Frame(content)
        format_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(format_frame, text="Format:").pack(anchor="w")
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.save_format,
            values=[SaveFormat.TIFF, SaveFormat.PNG],
            state="readonly"
        )
        format_combo.pack(fill=tk.X, pady=1)
        
        # JPEG quality (only show when JPEG selected)
        self.quality_frame = ttk.Frame(content)
        ttk.Label(self.quality_frame, text="JPEG Quality:").pack(anchor="w")
        quality_scale = ttk.Scale(
            self.quality_frame,
            from_=1,
            to=100,
            variable=self.jpg_quality,
            orient=tk.HORIZONTAL
        )
        quality_scale.pack(fill=tk.X, padx=5)
        
        # Show/hide quality based on format
        self.save_format.trace('w', self._on_save_format_change)
        self._on_save_format_change()
    
    # Event handlers
    def _on_tool_mode_change(self, *args):
        """Handle tool mode changes and adjust UI accordingly."""
        mode = self.tool_mode.get()
        
        # Auto-expand relevant sections based on tool mode
        if mode == "coord":
            self.color_section.expanded.set(True)
            self.settings_section.expanded.set(True)
        elif mode == "crop":
            self.settings_section.expanded.set(True)
            self.color_section.expanded.set(False)
        elif mode == "straighten":
            self.advanced_section.expanded.set(True)
            self.color_section.expanded.set(False)
        else:  # view mode
            self.settings_section.expanded.set(False)
            self.color_section.expanded.set(False)
        
        # Call original callback
        if self.callbacks['on_tool_mode_change']:
            self.callbacks['on_tool_mode_change'](mode)
    
    def _on_vertex_count_change(self, value):
        """Handle vertex count changes."""
        count = int(float(value))
        if self.callbacks['on_vertex_count_change']:
            self.callbacks['on_vertex_count_change'](count)
    
    def _on_transparency_change(self, value):
        """Handle transparency changes."""
        transparency = int(float(value))
        if self.callbacks['on_transparency_change']:
            self.callbacks['on_transparency_change'](transparency)
    
    def _on_save_format_change(self, *args):
        """Show/hide JPEG quality based on format selection (JPEG no longer supported for saving)."""
        # JPEG is no longer supported for saving, so always hide quality frame
        self.quality_frame.pack_forget()
    
    # Color library integration
    def _open_color_library(self):
        """Open the color library manager."""
        try:
            from gui.color_library_manager import ColorLibraryManager
            ColorLibraryManager(self.master)
        except ImportError as e:
            messagebox.showerror("Error", f"Color library not available: {e}")
    
    def _compare_sample(self):
        """Compare current sample to active library."""
        if self.active_library.get() == "None":
            messagebox.showwarning("Warning", "Please select an active library first")
            return
        
        # This would integrate with your sample analysis
        messagebox.showinfo("Info", "Sample comparison feature - integrate with your analysis system")
    
    def _export_color_analysis(self):
        """Export color analysis data."""
        try:
            from utils.ods_exporter import ODSExporter
            # This would export the current analysis
            messagebox.showinfo("Info", "Color analysis export - integrate with your ODS system")
        except ImportError as e:
            messagebox.showerror("Error", f"Export not available: {e}")
    
    def _update_library_list(self):
        """Update the available libraries list."""
        # This would scan for available libraries
        libraries = ["None", "philatelic_colors", "basic_colors", "scott_catalog"]
        self.library_combo['values'] = libraries
    
    # Utility methods that might be called by main app
    def update_mouse_coordinates(self, x: int, y: int):
        """Update mouse coordinate display."""
        self.mouse_x.set(str(x))
        self.mouse_y.set(str(y))
    
    def update_crop_dimensions(self, width: int, height: int):
        """Update crop dimension display."""
        self.crop_width.set(str(width))
        self.crop_height.set(str(height))
        self.crop_area.set(f"{width * height:,}")
    
    # Placeholder methods for advanced tools
    def _apply_fine_square(self):
        """Apply fine square tool."""
        messagebox.showinfo("Info", "Fine square tool - integrate with existing implementation")
    
    def _open_white_balance(self):
        """Open white balance correction."""
        messagebox.showinfo("Info", "White balance tool - integrate with existing implementation")
    
    def _toggle_straightening(self):
        """Toggle straightening mode."""
        messagebox.showinfo("Info", "Straightening tool - integrate with existing implementation")
