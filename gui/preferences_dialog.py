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
        self.root.title("StampZ Preferences")
        self.root.geometry("650x550")  # Increased height to ensure buttons are visible
        self.root.resizable(True, True)  # Allow resizing both ways
        
        # Make dialog modal
        self.root.transient(self.parent)
        self.root.grab_set()
        
        # Center the dialog
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
        
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
        
        # Export preferences tab
        self._create_export_tab(notebook)
        
        # File dialog preferences tab
        self._create_file_dialog_tab(notebook)
        
        # Future tabs can be added here
        # self._create_general_tab(notebook)
        # self._create_appearance_tab(notebook)
        
        # Button frame - fixed at bottom, never gets pushed off-screen
        button_frame = ttk.Frame(main_frame, relief='solid', borderwidth=1)  # Added border for debugging
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        # Make sure button frame doesn't expand
        button_frame.pack_propagate(False)
        button_frame.configure(height=50)  # Fixed height
        
        # Buttons with explicit styling to make them more visible
        reset_btn = ttk.Button(
            button_frame, 
            text="Reset to Defaults", 
            command=self._reset_to_defaults
        )
        reset_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        apply_btn = ttk.Button(
            button_frame, 
            text="Apply", 
            command=self._on_apply
        )
        apply_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        ok_btn = ttk.Button(
            button_frame, 
            text="OK", 
            command=self._on_ok
        )
        ok_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Debug label to confirm buttons are created
        debug_label = ttk.Label(button_frame, text="Buttons should be here:", foreground="red")
        debug_label.pack(side=tk.LEFT, padx=(20, 5))
    
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
        
        # Export behavior section
        behavior_frame = ttk.LabelFrame(export_frame, text="Export Behavior", padding="10")
        behavior_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_open_var = tk.BooleanVar()
        ttk.Checkbutton(
            behavior_frame,
            text="Automatically open exported files in LibreOffice",
            variable=self.auto_open_var
        ).pack(anchor=tk.W)
        
        # Info section
        info_frame = ttk.LabelFrame(export_frame, text="Information", padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = (
            "• Export files are saved as .ods (LibreOffice Calc) format\n"
            "• Files can be opened with LibreOffice Calc, Excel, or other spreadsheet apps\n"
            "• Default location is Desktop/StampZ Exports (easier to find than hidden folders)\n"
            "• Template variables: {sample_set} = template name, {date} = YYYYMMDD, {datetime} = YYYYMMDD_HHMMSS"
        )
        
        ttk.Label(
            info_frame,
            text=info_text,
            wraplength=550,
            justify=tk.LEFT,
            font=("TkDefaultFont", 9)
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
    
    def _load_current_settings(self):
        """Load current settings into the dialog."""
        prefs = self.prefs_manager.preferences.export_prefs
        
        # Export directory
        current_dir = self.prefs_manager.get_export_directory()
        self.export_dir_var.set(current_dir)
        
        # Filename template
        self.filename_template_var.set(prefs.export_filename_format)
        self.include_timestamp_var.set(prefs.include_timestamp)
        
        # Export behavior
        self.auto_open_var.set(prefs.auto_open_after_export)
        
        # File dialog preferences
        dialog_prefs = self.prefs_manager.preferences.file_dialog_prefs
        self.remember_directories_var.set(dialog_prefs.remember_directories)
        
        # Show current remembered directories
        last_open = self.prefs_manager.get_last_open_directory()
        self.last_open_var.set(last_open or "(none)")
        
        last_save = self.prefs_manager.get_last_save_directory()
        self.last_save_var.set(last_save or "(none)")
        
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
            
            # Export behavior
            self.prefs_manager.preferences.export_prefs.auto_open_after_export = self.auto_open_var.get()
            
            # File dialog preferences
            self.prefs_manager.set_remember_directories(self.remember_directories_var.get())
            
            # Save preferences
            success = self.prefs_manager.save_preferences()
            
            if success:
                messagebox.showinfo("Success", "Preferences saved successfully!")
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
