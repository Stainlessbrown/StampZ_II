#!/usr/bin/env python3
"""
Preferences dialog for StampZ
Allows users to configure export settings and other preferences.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional


class PreferencesDialog:
    """Dialog for configuring user preferences."""
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.prefs_manager = None
        self.result = None
        
        # Import here to avoid circular imports
        from utils.user_preferences import get_preferences_manager
        self.prefs_manager = get_preferences_manager()
        
        self._setup_dialog()
        self._create_widgets()
        self._load_current_settings()
        
    def _setup_dialog(self):
        """Set up the dialog window."""
        self.root.title("Preferences & Setup")
        
        # Get screen dimensions to calculate optimal dialog size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate dialog size based on screen size, leaving space for dock/taskbar
        if screen_height <= 768:  # Small screens (laptops)
            dialog_height = min(700, int(screen_height * 0.90))  # Much taller for small screens
        else:  # Larger screens
            dialog_height = min(850, int(screen_height * 0.90))  # Much taller for large screens
        
        dialog_width = min(800, int(screen_width * 0.70))  # Wider to accommodate content
        
        # Wait for parent window to be fully initialized
        self.parent.update_idletasks()
        
        # Position relative to parent window, but with fallback to screen center
        try:
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # Calculate position relative to parent window
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
        except tk.TclError:
            # Fallback to screen center if parent info not available
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
        
        # Ensure dialog stays on screen
        x = max(50, min(x, screen_width - dialog_width - 50))
        y = max(50, min(y, screen_height - dialog_height - 50))
        
        # Set size and position in one call to prevent flashing
        self.root.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.root.resizable(True, True)
        
        # Set minimum size to ensure all content is usable
        self.root.minsize(650, 600)  # Increased minimum height significantly
        
        # Make dialog modal without transient relationship to avoid multi-monitor issues
        # The transient() call causes the dialog to disappear when moved between screens on macOS
        # We'll use grab_set() for modality without the problematic parent-child relationship
        
        # Skip transient() entirely to prevent multi-monitor disappearing issue
        # This means the dialog won't automatically minimize when parent minimizes,
        # but it will stay visible when moved between screens
        
        # Set modal behavior - this blocks interaction with parent window
        self.root.grab_set()
        
        # Make the dialog appear on top and focus on it
        self.root.lift()
        self.root.focus_force()
        
        # Brief topmost to ensure visibility, then allow normal behavior
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
    def _create_widgets(self):
        """Create the dialog widgets."""
        # Main container with fixed layout to prevent button overflow
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Content area (notebook) - this gets the expandable space
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for different preference categories
        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Migration tab (only show if migration is possible) - First priority
        self._create_migration_tab(notebook)
        
        # File dialog preferences tab - Basic workflow setup
        self._create_file_dialog_tab(notebook)
        
        # Export preferences tab - Core functionality setup
        self._create_export_tab(notebook)
        
        # Sampling preferences tab - Advanced configuration
        self._create_sampling_tab(notebook)
        
        # Future tabs can be added here
        # self._create_general_tab(notebook)
        # self._create_appearance_tab(notebook)
        
        # Button frame - fixed at bottom with proper spacing
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        # Create buttons with proper spacing and visibility
        reset_btn = ttk.Button(
            button_frame, 
            text="Reset to Defaults", 
            command=self._reset_to_defaults
        )
        reset_btn.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Create a frame for right-aligned buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT, padx=5, pady=10)
        
        cancel_btn = ttk.Button(
            right_buttons, 
            text="Cancel", 
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        apply_btn = ttk.Button(
            right_buttons, 
            text="Apply", 
            command=self._on_apply
        )
        apply_btn.pack(side=tk.RIGHT, padx=5)
        
        ok_btn = ttk.Button(
            right_buttons, 
            text="OK", 
            command=self._on_ok
        )
        ok_btn.pack(side=tk.RIGHT, padx=5)
    
    def _create_export_tab(self, notebook):
        """Create the export preferences tab."""
        export_frame = ttk.Frame(notebook, padding="10")
        notebook.add(export_frame, text="Export Settings")
        
        # Export directory section
        dir_frame = ttk.LabelFrame(export_frame, text="Export Directory", padding="10")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Current directory display
        ttk.Label(dir_frame, text="Current directory:").pack(anchor=tk.W)
        
        self.export_dir_var = tk.StringVar()
        self.export_dir_entry = ttk.Entry(
            dir_frame, 
            textvariable=self.export_dir_var,
            state="readonly",
            width=60
        )
        self.export_dir_entry.pack(fill=tk.X, pady=(5, 10))
        
        # Directory selection buttons
        dir_button_frame = ttk.Frame(dir_frame)
        dir_button_frame.pack(fill=tk.X)
        
        ttk.Button(
            dir_button_frame,
            text="Browse...",
            command=self._browse_export_directory
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            dir_button_frame,
            text="Use Default",
            command=self._use_default_directory
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Save button to immediately apply directory changes
        ttk.Button(
            dir_button_frame,
            text="Save Settings",
            command=self._apply_settings,
            style="Accent.TButton"  # Make it stand out
        ).pack(side=tk.LEFT, padx=(20, 0))
        
        ttk.Button(
            dir_button_frame,
            text="Open Directory",
            command=self._open_current_directory
        ).pack(side=tk.RIGHT)
        
        # Filename format section
        filename_frame = ttk.LabelFrame(export_frame, text="Filename Format", padding="10")
        filename_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            filename_frame, 
            text="Template (use {sample_set}, {date}, {datetime}):"
        ).pack(anchor=tk.W)
        
        self.filename_template_var = tk.StringVar()
        ttk.Entry(
            filename_frame,
            textvariable=self.filename_template_var,
            width=40
        ).pack(fill=tk.X, pady=(5, 10))
        
        # Filename options
        self.include_timestamp_var = tk.BooleanVar()
        ttk.Checkbutton(
            filename_frame,
            text="Include timestamp in filename",
            variable=self.include_timestamp_var
        ).pack(anchor=tk.W)
        
        # Preview
        preview_frame = ttk.Frame(filename_frame)
        preview_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(preview_frame, text="Preview:").pack(side=tk.LEFT)
        self.filename_preview = ttk.Label(
            preview_frame, 
            text="", 
            foreground="blue",
            font=("TkDefaultFont", 9, "italic")
        )
        self.filename_preview.pack(side=tk.LEFT, padx=(10, 0))
        
        # Update preview when template changes
        self.filename_template_var.trace_add("write", self._update_filename_preview)
        self.include_timestamp_var.trace_add("write", self._update_filename_preview)
        
        # Export format section
        format_frame = ttk.LabelFrame(export_frame, text="Export Format", padding="10")
        format_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(format_frame, text="Preferred export format:").pack(anchor=tk.W, pady=(0, 5))
        
        self.export_format_var = tk.StringVar()
        format_radio_frame = ttk.Frame(format_frame)
        format_radio_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(
            format_radio_frame,
            text="ODS (LibreOffice Calc) - Recommended",
            variable=self.export_format_var,
            value="ods"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            format_radio_frame,
            text="XLSX (Microsoft Excel)",
            variable=self.export_format_var,
            value="xlsx"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            format_radio_frame,
            text="CSV (Comma Separated Values)",
            variable=self.export_format_var,
            value="csv"
        ).pack(anchor=tk.W)
        
        # Format info
        format_info = ttk.Label(
            format_frame,
            text="Note: Files will open in the appropriate application based on format",
            font=("TkDefaultFont", 9),
            foreground="blue"
        )
        format_info.pack(anchor=tk.W, pady=(5, 0))
        
        # Export behavior section
        behavior_frame = ttk.LabelFrame(export_frame, text="Export Behavior", padding="10")
        behavior_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_open_var = tk.BooleanVar()
        ttk.Checkbutton(
            behavior_frame,
            text="Automatically open exported files after export",
            variable=self.auto_open_var
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Color value format section
        self.export_normalized_var = tk.BooleanVar()
        ttk.Checkbutton(
            behavior_frame,
            text="Export color values normalized to 0.0-1.0 range",
            variable=self.export_normalized_var
        ).pack(anchor=tk.W)
        
        ttk.Label(
            behavior_frame,
            text="When enabled, RGB and L*a*b* values are exported as normalized decimals (0.0-1.0).\nWhen disabled, standard ranges are used (RGB: 0-255, L*a*b*: full scale).",
            font=("TkDefaultFont", 9),
            foreground="gray"
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # Color space selection section
        color_space_frame = ttk.LabelFrame(export_frame, text="Color Space Selection", padding="10")
        color_space_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(
            color_space_frame,
            text="Choose which color spaces to include in exports:",
            font=("TkDefaultFont", 10, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        self.export_include_rgb_var = tk.BooleanVar()
        self.rgb_checkbox = ttk.Checkbutton(
            color_space_frame,
            text="Include RGB color values (Red, Green, Blue)",
            variable=self.export_include_rgb_var,
            command=self._on_color_space_change
        )
        self.rgb_checkbox.pack(anchor=tk.W, pady=(0, 5))
        
        self.export_include_lab_var = tk.BooleanVar()
        self.lab_checkbox = ttk.Checkbutton(
            color_space_frame,
            text="Include L*a*b* color values (CIE L*a*b*)",
            variable=self.export_include_lab_var,
            command=self._on_color_space_change
        )
        self.lab_checkbox.pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(
            color_space_frame,
            text="• RGB: Scanned image native format (0-255 per channel)\n• L*a*b*: Perceptually uniform color space, better for color analysis\n• Selecting only one color space reduces export column count\n• At least one color space must be selected",
            font=("TkDefaultFont", 9),
            foreground="gray"
        ).pack(anchor=tk.W)
    
    def _create_file_dialog_tab(self, notebook):
        """Create the file dialog preferences tab."""
        dialog_frame = ttk.Frame(notebook, padding="10")
        notebook.add(dialog_frame, text="File Dialogs")
        
        # Remember directories section
        remember_frame = ttk.LabelFrame(dialog_frame, text="Directory Memory", padding="10")
        remember_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.remember_directories_var = tk.BooleanVar()
        ttk.Checkbutton(
            remember_frame,
            text="Remember last used directories for Open and Save dialogs",
            variable=self.remember_directories_var
        ).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(
            remember_frame,
            text="When enabled, file dialogs will start in the directory you last used.",
            font=("TkDefaultFont", 9),
            foreground="gray"
        ).pack(anchor=tk.W)
        
        # Current directories section
        current_frame = ttk.LabelFrame(dialog_frame, text="Current Remembered Directories", padding="10")
        current_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Last open directory
        ttk.Label(current_frame, text="Last Open directory:").pack(anchor=tk.W)
        self.last_open_var = tk.StringVar()
        ttk.Entry(
            current_frame,
            textvariable=self.last_open_var,
            state="readonly",
            width=60
        ).pack(fill=tk.X, pady=(2, 10))
        
        # Last save directory
        ttk.Label(current_frame, text="Last Save directory:").pack(anchor=tk.W)
        self.last_save_var = tk.StringVar()
        ttk.Entry(
            current_frame,
            textvariable=self.last_save_var,
            state="readonly",
            width=60
        ).pack(fill=tk.X, pady=(2, 10))
        
        # Clear directories button
        clear_button_frame = ttk.Frame(current_frame)
        clear_button_frame.pack(fill=tk.X)
        
        ttk.Button(
            clear_button_frame,
            text="Clear Remembered Directories",
            command=self._clear_remembered_directories
        ).pack(side=tk.LEFT)
        
        # Color Library section
        library_frame = ttk.LabelFrame(dialog_frame, text="Color Library Defaults", padding="10")
        library_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(library_frame, text="Default color library:").pack(anchor=tk.W, pady=(0, 5))
        
        self.default_library_var = tk.StringVar()
        self.library_combo = ttk.Combobox(
            library_frame,
            textvariable=self.default_library_var,
            state="readonly",
            width=30
        )
        self.library_combo.pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(
            library_frame,
            text="This library will be automatically selected when opening the Color Library Manager\nand when using the Compare feature in color analysis.",
            font=("TkDefaultFont", 9),
            foreground="gray"
        ).pack(anchor=tk.W)
        
        # Info section
        info_frame = ttk.LabelFrame(dialog_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = (
            "• When directory memory is enabled, Open and Save dialogs will start in the last directory you used\n"
            "• Open and Save directories are remembered separately\n"
            "• Directories are only remembered if they still exist when you use them\n"
            "• You can clear the remembered directories at any time using the button above"
        )
        
        ttk.Label(
            info_frame,
            text=info_text,
            wraplength=550,
            justify=tk.LEFT,
            font=("TkDefaultFont", 9)
        ).pack(anchor=tk.W)
    
    def _create_sampling_tab(self, notebook):
        """Create the sampling preferences tab."""
        sampling_frame = ttk.Frame(notebook, padding="10")
        notebook.add(sampling_frame, text="Sampling")
        
        # Sample area defaults section
        sample_frame = ttk.LabelFrame(sampling_frame, text="Sample Area Defaults", padding="10")
        sample_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            sample_frame, 
            text="Set default shape, size, and anchor for new sample areas:",
            font=("TkDefaultFont", 10, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Sample controls layout
        sample_controls_frame = ttk.Frame(sample_frame)
        sample_controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Shape selection
        shape_frame = ttk.Frame(sample_controls_frame)
        shape_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(shape_frame, text="Shape:", width=10).pack(side=tk.LEFT)
        self.sample_shape_var = tk.StringVar()
        shape_combo = ttk.Combobox(
            shape_frame,
            textvariable=self.sample_shape_var,
            values=['circle', 'rectangle'],
            state='readonly',
            width=15
        )
        shape_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Size selection
        size_frame = ttk.Frame(sample_controls_frame)
        size_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(size_frame, text="Size:", width=10).pack(side=tk.LEFT)
        
        # Width
        width_frame = ttk.Frame(size_frame)
        width_frame.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(width_frame, text="W:").pack(side=tk.LEFT)
        self.sample_width_var = tk.StringVar()
        width_spin = ttk.Spinbox(
            width_frame,
            textvariable=self.sample_width_var,
            from_=1, to=100,
            width=6
        )
        width_spin.pack(side=tk.LEFT, padx=(2, 0))
        
        # Height
        height_frame = ttk.Frame(size_frame)
        height_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(height_frame, text="H:").pack(side=tk.LEFT)
        self.sample_height_var = tk.StringVar()
        height_spin = ttk.Spinbox(
            height_frame,
            textvariable=self.sample_height_var,
            from_=1, to=100,
            width=6
        )
        height_spin.pack(side=tk.LEFT, padx=(2, 0))
        
        ttk.Label(size_frame, text="pixels", font=("TkDefaultFont", 9)).pack(side=tk.LEFT, padx=(10, 0))
        
        # Anchor selection
        anchor_frame = ttk.Frame(sample_controls_frame)
        anchor_frame.pack(fill=tk.X)
        
        ttk.Label(anchor_frame, text="Anchor:", width=10).pack(side=tk.LEFT)
        self.sample_anchor_var = tk.StringVar()
        anchor_combo = ttk.Combobox(
            anchor_frame,
            textvariable=self.sample_anchor_var,
            values=['center', 'top_left', 'top_right', 'bottom_left', 'bottom_right'],
            state='readonly',
            width=15
        )
        anchor_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Sample defaults info
        sample_info_text = (
            "These settings will be used as defaults when creating new sample areas. "
            "You can still adjust individual samples after placing them."
        )
        
        ttk.Label(
            sample_frame,
            text=sample_info_text,
            wraplength=550,
            justify=tk.LEFT,
            font=("TkDefaultFont", 9),
            foreground="gray"
        ).pack(anchor=tk.W, pady=(10, 0))
        
        # Information section
        info_frame = ttk.LabelFrame(sampling_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        info_text = (
            "• Sample area defaults apply to all new samples created in the application\n"
            "• You can override these defaults for individual samples after placement\n"
            "• Circle samples are recommended for most color analysis tasks\n"
            "• Rectangle samples are useful for analyzing larger color areas or patterns"
        )
        
        ttk.Label(
            info_frame,
            text=info_text,
            wraplength=550,
            justify=tk.LEFT,
            font=("TkDefaultFont", 9)
        ).pack(anchor=tk.W)
    
    def _create_migration_tab(self, notebook):
        """Create the migration tab (only if migration is possible)."""
        try:
            from utils.migration import StampZMigration
            migration = StampZMigration()
            
            # Only create tab if migration is needed or already completed
            if not migration.is_migration_needed() and not migration.is_migration_completed():
                return  # No migration tab needed for new users
            
        except ImportError:
            return  # Migration utility not available
        
        migration_frame = ttk.Frame(notebook, padding="10")
        notebook.add(migration_frame, text="Migration")
        
        # Title
        title_frame = ttk.Frame(migration_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            title_frame,
            text="StampZ to StampZ_II Migration",
            font=("TkDefaultFont", 12, "bold")
        ).pack(anchor=tk.W)
        
        if migration.is_migration_completed():
            # Show migration completion status
            self._create_migration_completed_section(migration_frame, migration)
        elif migration.is_migration_needed():
            # Show migration options
            self._create_migration_needed_section(migration_frame, migration)
    
    def _create_migration_completed_section(self, parent, migration):
        """Create section for completed migration."""
        status_frame = ttk.LabelFrame(parent, text="Migration Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Success message
        ttk.Label(
            status_frame,
            text="✅ Migration completed successfully!",
            font=("TkDefaultFont", 11, "bold"),
            foreground="green"
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Get migration info
        info = migration.get_migration_info()
        if info:
            info_text = f"Migration Date: {info.get('Migration completed', 'Unknown')}\n"
            info_text += f"Files Migrated: {info.get('Migrated files', 'Unknown')}\n"
            info_text += f"Backup Created: {info.get('Backup created', 'Unknown')}"
            
            ttk.Label(
                status_frame,
                text=info_text,
                font=("TkDefaultFont", 10)
            ).pack(anchor=tk.W, pady=(0, 10))
        
        # Info about old directory
        info_frame = ttk.LabelFrame(parent, text="Information", padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = (
            "Your data has been successfully migrated from the old StampZ directory to StampZ_II.\n\n"
            "• All your color libraries, analysis data, and templates are now in StampZ_II\n"
            "• The old StampZ directory has been left unchanged as a backup\n"
            "• StampZ_II now uses the migrated data exclusively\n\n"
            "You can safely delete the old StampZ directory if you no longer need it, "
            "but it's recommended to keep it as a backup until you're sure everything works correctly."
        )
        
        ttk.Label(
            info_frame,
            text=info_text,
            wraplength=600,
            justify=tk.LEFT,
            font=("TkDefaultFont", 10)
        ).pack(anchor=tk.W)
    
    def _create_migration_needed_section(self, parent, migration):
        """Create section for needed migration."""
        # Warning
        warning_frame = ttk.LabelFrame(parent, text="Migration Available", padding="10")
        warning_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            warning_frame,
            text="⚠️ StampZ data found that can be migrated to StampZ_II",
            font=("TkDefaultFont", 11, "bold"),
            foreground="orange"
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Get migration summary
        summary = migration.get_migration_summary()
        
        # Summary of what will be migrated
        summary_frame = ttk.LabelFrame(parent, text="Migration Summary", padding="10")
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        summary_text = f"The following data from your old StampZ installation can be migrated:\n\n"
        
        if summary['color_libraries']:
            summary_text += f"📚 Color Libraries ({len(summary['color_libraries'])}):"
            for lib in summary['color_libraries']:
                summary_text += f"\n  • {lib['name']} ({lib['size_mb']} MB)"
            summary_text += "\n\n"
        
        if summary['color_analysis']:
            summary_text += f"🔬 Color Analysis ({len(summary['color_analysis'])}):"
            for analysis in summary['color_analysis']:
                summary_text += f"\n  • {analysis['name']} ({analysis['size_mb']} MB)"
            summary_text += "\n\n"
        
        if summary['coordinates']:
            summary_text += f"📍 Coordinate Templates ({len(summary['coordinates'])}):"
            for coord in summary['coordinates']:
                summary_text += f"\n  • {coord['path']} ({coord['size_mb']} MB)"
            summary_text += "\n\n"
        
        summary_text += f"Total: {summary['total_files']} files, {summary['total_size_mb']} MB"
        
        ttk.Label(
            summary_frame,
            text=summary_text,
            font=("TkDefaultFont", 10),
            justify=tk.LEFT
        ).pack(anchor=tk.W)
        
        # Migration options
        options_frame = ttk.LabelFrame(parent, text="Migration Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Create backup of original StampZ directory (recommended)",
            variable=self.create_backup_var
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Migration button
        button_frame = ttk.Frame(options_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="Migrate Data to StampZ_II",
            command=lambda: self._perform_migration(migration),
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="Skip Migration",
            command=self._skip_migration
        ).pack(side=tk.LEFT)
        
        # Info about the process
        info_frame = ttk.LabelFrame(parent, text="What happens during migration?", padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = (
            "1. Your old StampZ directory will be backed up (if selected)\n"
            "2. Data will be copied to the new StampZ_II directory structure\n"
            "3. StampZ_II will use the migrated data going forward\n"
            "4. Your original StampZ directory remains unchanged\n\n"
            "This process is safe and reversible - your original data is never deleted."
        )
        
        ttk.Label(
            info_frame,
            text=info_text,
            font=("TkDefaultFont", 10),
            justify=tk.LEFT
        ).pack(anchor=tk.W)
    
    def _perform_migration(self, migration):
        """Perform the data migration."""
        # Confirm with user
        result = messagebox.askyesno(
            "Confirm Migration",
            "This will migrate your StampZ data to StampZ_II.\n\n"
            "Your original StampZ directory will be preserved.\n\n"
            "Continue with migration?"
        )
        
        if not result:
            return
        
        # Show progress dialog
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Migrating Data...")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        # Center the progress dialog
        progress_dialog.update_idletasks()
        x = (progress_dialog.winfo_screenwidth() // 2) - (progress_dialog.winfo_width() // 2)
        y = (progress_dialog.winfo_screenheight() // 2) - (progress_dialog.winfo_height() // 2)
        progress_dialog.geometry(f"+{x}+{y}")
        
        progress_label = ttk.Label(progress_dialog, text="Migrating your data to StampZ_II...\nPlease wait...")
        progress_label.pack(expand=True)
        
        progress_dialog.update()
        
        try:
            # Perform the migration
            create_backup = self.create_backup_var.get()
            success, message = migration.perform_migration(create_backup=create_backup)
            
            progress_dialog.destroy()
            
            if success:
                messagebox.showinfo("Migration Successful", message)
                # Recreate the migration tab to show completed status
                self._recreate_migration_tab()
            else:
                messagebox.showerror("Migration Failed", message)
                
        except Exception as e:
            progress_dialog.destroy()
            messagebox.showerror("Migration Error", f"An error occurred during migration:\n\n{str(e)}")
    
    def _skip_migration(self):
        """Skip the migration (user chooses not to migrate)."""
        result = messagebox.askyesno(
            "Skip Migration",
            "Are you sure you want to skip migrating your StampZ data?\n\n"
            "You can always migrate later from this preferences dialog.\n\n"
            "StampZ_II will start with empty libraries and no previous data."
        )
        
        if result:
            messagebox.showinfo(
                "Migration Skipped",
                "Migration has been skipped. You can migrate your data later \n"
                "by returning to this preferences dialog."
            )
    
    def _recreate_migration_tab(self):
        """Recreate the migration tab (after migration completion)."""
        # This would require rebuilding the entire notebook, which is complex
        # For now, just show a message that restart is recommended
        messagebox.showinfo(
            "Restart Recommended",
            "Migration completed successfully!\n\n"
            "Please restart StampZ_II to see the updated migration status.\n\n"
            "Your migrated data is now available in StampZ_II."
        )
    
    def _clear_remembered_directories(self):
        """Clear the remembered directories."""
        result = messagebox.askyesno(
            "Clear Directories",
            "This will clear the remembered Open and Save directories.\n\nAre you sure?"
        )
        
        if result:
            # Clear the directories in preferences
            self.prefs_manager.preferences.file_dialog_prefs.last_open_directory = ""
            self.prefs_manager.preferences.file_dialog_prefs.last_save_directory = ""
            self.prefs_manager.save_preferences()
            
            # Update the display
            self.last_open_var.set("")
            self.last_save_var.set("")
            
            messagebox.showinfo("Cleared", "Remembered directories have been cleared.")
    
    def _load_color_library_preferences(self):
        """Load color library preferences."""
        try:
            # Get available libraries
            available_libraries = self.prefs_manager.get_available_color_libraries()
            
            # Convert to display names for better UX
            display_names = []
            library_mapping = {}  # display_name -> library_name
            
            for lib_name in available_libraries:
                if lib_name == 'basic_colors':
                    display_name = 'Basic Colors'
                elif lib_name.lower() == 'sg' or lib_name.lower() == 'stanley_gibbons_colors':
                    display_name = 'SG (Stanley Gibbons)'
                    lib_name = 'sg'  # Normalize
                elif '_' in lib_name:
                    display_name = ' '.join(word.capitalize() for word in lib_name.split('_'))
                else:
                    display_name = lib_name.capitalize()
                
                display_names.append(display_name)
                library_mapping[display_name] = lib_name
            
            # Update combobox
            self.library_combo['values'] = display_names
            
            # Set current selection
            current_library = self.prefs_manager.get_default_color_library()
            display_name = None
            for display, lib in library_mapping.items():
                if lib == current_library:
                    display_name = display
                    break
            
            if display_name:
                self.default_library_var.set(display_name)
            elif display_names:  # Fallback to first available
                self.default_library_var.set(display_names[0])
                
            # Store mapping for later use
            self._library_mapping = library_mapping
            
        except Exception as e:
            print(f"Error loading color library preferences: {e}")
            # Fallback
            self.library_combo['values'] = ['Basic Colors']
            self.default_library_var.set('Basic Colors')
            self._library_mapping = {'Basic Colors': 'basic_colors'}
    
    def _load_current_settings(self):
        """Load current settings into the dialog."""
        prefs = self.prefs_manager.preferences.export_prefs
        
        # Export directory
        current_dir = self.prefs_manager.get_export_directory()
        self.export_dir_var.set(current_dir)
        
        # Filename template
        self.filename_template_var.set(prefs.export_filename_format)
        self.include_timestamp_var.set(prefs.include_timestamp)
        
        # Export format
        self.export_format_var.set(prefs.preferred_export_format)
        
        # Export behavior
        self.auto_open_var.set(prefs.auto_open_after_export)
        
        # Normalized export values
        self.export_normalized_var.set(prefs.export_normalized_values)
        
        # File dialog preferences
        dialog_prefs = self.prefs_manager.preferences.file_dialog_prefs
        self.remember_directories_var.set(dialog_prefs.remember_directories)
        
        # Show current remembered directories
        last_open = self.prefs_manager.get_last_open_directory()
        self.last_open_var.set(last_open or "(none)")
        
        last_save = self.prefs_manager.get_last_save_directory()
        self.last_save_var.set(last_save or "(none)")
        
        # Color library preferences
        self._load_color_library_preferences()
        
        # Interface mode preference removed
        
        # Sample area preferences
        self.sample_shape_var.set(self.prefs_manager.get_default_sample_shape())
        self.sample_width_var.set(str(self.prefs_manager.get_default_sample_width()))
        self.sample_height_var.set(str(self.prefs_manager.get_default_sample_height()))
        self.sample_anchor_var.set(self.prefs_manager.get_default_sample_anchor())
        
        # Color space preferences
        self.export_include_rgb_var.set(self.prefs_manager.get_export_include_rgb())
        self.export_include_lab_var.set(self.prefs_manager.get_export_include_lab())
        
        # Update preview
        self._update_filename_preview()
    
    def _update_filename_preview(self, *args):
        """Update the filename preview."""
        try:
            # Create a temporary preferences manager with current settings
            template = self.filename_template_var.get()
            include_timestamp = self.include_timestamp_var.get()
            
            # Create preview filename
            from datetime import datetime
            variables = {
                "sample_set": "my_template",
                "date": datetime.now().strftime("%Y%m%d"),
                "datetime": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
            try:
                filename = template.format(**variables)
            except (KeyError, ValueError) as e:
                filename = f"my_template_{variables['date']} (invalid template)"
            
            if include_timestamp:
                timestamp = datetime.now().strftime("_%H%M%S")
                filename += timestamp
            
            filename += ".ods"
            
            self.filename_preview.config(text=filename, foreground="blue")
        except Exception:
            self.filename_preview.config(text="(preview error)", foreground="red")
    
    def _browse_export_directory(self):
        """Browse for export directory."""
        current_dir = self.export_dir_var.get()
        
        directory = filedialog.askdirectory(
            title="Choose Export Directory",
            initialdir=current_dir if current_dir else str(Path.home() / "Desktop")
        )
        
        if directory:
            self.export_dir_var.set(directory)
    
    def _use_default_directory(self):
        """Set export directory to default."""
        default_dir = self.prefs_manager._get_default_export_directory()
        self.export_dir_var.set(default_dir)
    
    def _open_current_directory(self):
        """Open the current export directory in file explorer."""
        current_dir = self.export_dir_var.get()
        
        if not current_dir:
            messagebox.showwarning("No Directory", "No export directory is set.")
            return
        
        try:
            import subprocess
            import sys
            
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', current_dir])
            elif sys.platform.startswith('linux'):  # Linux
                subprocess.run(['xdg-open', current_dir])
            elif sys.platform.startswith('win'):  # Windows
                subprocess.run(['explorer', current_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open directory:\n{e}")
    
    def _apply_settings(self):
        """Apply the current settings."""
        try:
            # Export directory
            new_dir = self.export_dir_var.get()
            if new_dir:
                self.prefs_manager.set_export_directory(new_dir)
            
            # Filename settings
            self.prefs_manager.preferences.export_prefs.export_filename_format = self.filename_template_var.get()
            self.prefs_manager.preferences.export_prefs.include_timestamp = self.include_timestamp_var.get()
            
            # Export format
            self.prefs_manager.set_preferred_export_format(self.export_format_var.get())
            
            # Export behavior
            self.prefs_manager.preferences.export_prefs.auto_open_after_export = self.auto_open_var.get()
            
            # Normalized export values
            self.prefs_manager.set_export_normalized_values(self.export_normalized_var.get())
            
            # File dialog preferences
            self.prefs_manager.set_remember_directories(self.remember_directories_var.get())
            
            # Color library preference
            if hasattr(self, '_library_mapping') and hasattr(self, 'default_library_var'):
                display_name = self.default_library_var.get()
                if display_name in self._library_mapping:
                    library_name = self._library_mapping[display_name]
                    self.prefs_manager.set_default_color_library(library_name)
            
            # Interface mode preference removed
            
            # Sample area preferences
            self.prefs_manager.set_default_sample_shape(self.sample_shape_var.get())
            try:
                width = int(self.sample_width_var.get())
                height = int(self.sample_height_var.get())
                self.prefs_manager.set_default_sample_width(width)
                self.prefs_manager.set_default_sample_height(height)
            except ValueError:
                messagebox.showerror("Invalid Input", "Sample width and height must be valid numbers.")
                return False
            self.prefs_manager.set_default_sample_anchor(self.sample_anchor_var.get())
            
            # Color space preferences
            self.prefs_manager.set_export_include_rgb(self.export_include_rgb_var.get())
            self.prefs_manager.set_export_include_lab(self.export_include_lab_var.get())
            
            # Save preferences
            success = self.prefs_manager.save_preferences()
            
            if success:
                messagebox.showinfo(
                    "Preferences Saved", 
                    "Preferences saved successfully!\n\n"
                    "Please restart StampZ_II to ensure all changes take effect."
                )
                return True
            else:
                messagebox.showerror("Error", "Failed to save preferences.")
                return False
                
        except Exception as e:
            messagebox.showerror("Error", f"Error saving preferences:\n{e}")
            return False
    
    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        result = messagebox.askyesno(
            "Reset to Defaults",
            "This will reset all preferences to their default values.\n\nAre you sure?"
        )
        
        if result:
            self.prefs_manager.reset_to_defaults()
            self._load_current_settings()
            messagebox.showinfo("Reset Complete", "All preferences have been reset to defaults.")
    
    def _on_ok(self):
        """Handle OK button."""
        if self._apply_settings():
            self.result = "ok"
            self.root.destroy()
    
    def _on_apply(self):
        """Handle Apply button."""
        self._apply_settings()
    
    def _on_color_space_change(self):
        """Handle color space checkbox changes to ensure at least one is selected."""
        rgb_checked = self.export_include_rgb_var.get()
        lab_checked = self.export_include_lab_var.get()
        
        # Ensure at least one color space is selected
        if not rgb_checked and not lab_checked:
            # If both are unchecked, recheck the one that was just unchecked
            # We can't tell which was just unchecked, so default to re-enabling RGB
            self.export_include_rgb_var.set(True)
            messagebox.showwarning(
                "Color Space Required",
                "At least one color space (RGB or L*a*b*) must be selected for exports.\n\nRGB has been re-enabled."
            )
    
    def _on_cancel(self):
        """Handle Cancel button."""
        self.result = "cancel"
        self.root.destroy()
    
    def show(self) -> Optional[str]:
        """Show the dialog and return result."""
        self.root.focus_force()
        self.root.wait_window()
        return self.result


def show_preferences_dialog(parent: tk.Tk) -> Optional[str]:
    """Convenience function to show preferences dialog."""
    dialog = PreferencesDialog(parent)
    return dialog.show()


if __name__ == "__main__":
    # Test the dialog
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    result = show_preferences_dialog(root)
    print(f"Dialog result: {result}")
    
    root.destroy()
