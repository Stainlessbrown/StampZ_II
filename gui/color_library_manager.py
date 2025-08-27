#!/usr/bin/env python3
"""
Color Library Manager GUI for StampZ
Provides interface for managing color libraries and comparing samples.
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
from typing import List, Dict, Any
import os
from PIL import Image, ImageTk
# Add project root to path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.color_library import ColorLibrary, LibraryColor
from gui.color_comparison_manager import ColorComparisonManager
from gui.color_display import ColorDisplay

__all__ = ['ColorLibraryManager']

class ColorLibraryManager:
    """Color library management interface."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.library = None
        
        # Get default library from preferences
        try:
            from utils.user_preferences import get_preferences_manager
            prefs_manager = get_preferences_manager()
            self.current_library_name = prefs_manager.get_default_color_library()
        except Exception as e:
            print(f"Error loading default library preference: {e}")
            self.current_library_name = "basic_colors"
        
        # Create main window
        if parent is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(parent)
            # Removed transient setting to allow window to move independently
        
        self.root.title("Color Library Manager")
        
        # Set window size to 90% of screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.9)
        window_height = int(screen_height * 0.9)
        
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(800, 600)
        
        # Ensure window can be minimized and closed
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.resizable(True, True)  # Allow window resizing
        
        # Set minimum size
        self.root.minsize(800, 600)
        
        # Initialize variables
        self.display_to_file_map = {}
        self.file_to_display_map = {}
        
        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create frames for each tab
        self.library_frame = ttk.Frame(self.notebook)
        self.comparison_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.library_frame, text="Library")
        self.notebook.add(self.comparison_frame, text="Compare")
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Ensure we have a library
        if not self.library:
            self.library = ColorLibrary(self.current_library_name)
        
        # Create tab contents
        self._create_library_tab()
        self._create_settings_tab()
        
        # Load initial library
        self._load_library(self.current_library_name)
        
        # Center window
        self.root.update_idletasks()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"+{x}+{y}")
    def _create_library_tab(self):
        """Create the library management tab."""
        # Top controls
        controls_frame = ttk.Frame(self.library_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Library selection row
        library_row = ttk.Frame(controls_frame)
        library_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(library_row, text="Library:").pack(side=tk.LEFT, padx=(0, 5))
        self.library_var = tk.StringVar(value=self.current_library_name)
        self.library_combo = ttk.Combobox(library_row, textvariable=self.library_var, width=20)
        self.library_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.library_combo.bind("<<ComboboxSelected>>", self._on_library_changed)
        
        ttk.Button(library_row, text="New Library", command=self._create_new_library).pack(side=tk.LEFT, padx=(0, 5))
        self.add_color_btn = ttk.Button(library_row, text="Add Color", command=self._add_color_dialog)
        self.add_color_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Search and pagination row
        search_row = ttk.Frame(controls_frame)
        search_row.pack(fill=tk.X, pady=(0, 5))
        
        # Search functionality
        ttk.Label(search_row, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=25)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<KeyRelease>', self._on_search_changed)
        ttk.Button(search_row, text="Clear", command=self._clear_search).pack(side=tk.LEFT, padx=(0, 10))
        
        # Pagination controls
        self.page_info_label = ttk.Label(search_row, text="")
        self.page_info_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.load_more_btn = ttk.Button(search_row, text="Load More", command=self._load_more_colors)
        self.load_more_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Initialize pagination variables
        self.current_page = 0
        self.page_size = 50
        self.filtered_colors = []
        self.search_term = ""
        
        # Add explicit bindings for better click detection
        self.add_color_btn.bind('<Button-1>', lambda e: self._add_color_dialog())
        self.add_color_btn.bind('<Return>', lambda e: self._add_color_dialog())
        self.add_color_btn.bind('<space>', lambda e: self._add_color_dialog())
        
        # Removed category filter dropdown as it's not needed
        
        # Create main display frame with proper structure for scrolling
        self.display_frame = ttk.Frame(self.library_frame)
        self.display_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure library frame
        self.library_frame.rowconfigure(0, weight=1)
        self.library_frame.columnconfigure(0, weight=1)
        
        # Create and configure scroll manager for color display
        from .scroll_manager import ScrollManager
        self.scroll_manager = ScrollManager(self.display_frame)
        
        # Configure content frame
        self.colors_scroll_frame = self.scroll_manager.content_frame
        self.colors_scroll_frame.columnconfigure(0, weight=1)
        
        # Store canvas reference for compatibility
        self.colors_canvas = self.scroll_manager.canvas
        
        # Configure display frame
        self.display_frame.configure(height=600)
        self.display_frame.pack_propagate(False)
        
        # No need for additional configuration as ScrollManager handles all scrolling
    
    def _create_comparison_tab(self):
        """Create the color comparison tab."""
        # Ensure we have a library initialized first
        if not hasattr(self, 'library') or not self.library:
            self.library = ColorLibrary(self.current_library_name)
        
        # Create comparison manager with the correct parent
        self.comparison_manager = ColorComparisonManager(self.comparison_frame)
        
        # Set library
        self.comparison_manager.library = self.library
        
        # Update library binding
        self._original_load_library = self._load_library
        def wrapped_load_library(library_name: str):
            self._original_load_library(library_name)
            if hasattr(self, 'comparison_manager'):
                self.comparison_manager.library = self.library
                if hasattr(self.comparison_manager, '_update_library_display'):
                    self.comparison_manager._update_library_display()
        self._load_library = wrapped_load_library
        
    
    def _create_settings_tab(self):
        """Create the library settings tab."""
        # Library statistics
        stats_frame = ttk.LabelFrame(self.settings_frame, text="Library Statistics")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_label = ttk.Label(stats_frame, text="No library loaded")
        self.stats_label.pack(padx=10, pady=10)
        
        # Library management
        mgmt_frame = ttk.LabelFrame(self.settings_frame, text="Library Management")
        mgmt_frame.pack(fill=tk.X, pady=(0, 10))
        
        buttons_frame = ttk.Frame(mgmt_frame)
        buttons_frame.pack(padx=10, pady=10)
        
        # Library creation is handled through the New Library button
        
        # Import/Export
        io_frame = ttk.LabelFrame(self.settings_frame, text="Import/Export")
        io_frame.pack(fill=tk.X)
        
        io_buttons = ttk.Frame(io_frame)
        io_buttons.pack(padx=10, pady=10)
        
        ttk.Button(io_buttons, text="Export Library (CSV)", command=self._export_library).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(io_buttons, text="Import from CSV", command=self._import_library).pack(side=tk.LEFT)
    
    def _load_library(self, library_name: str):
        """Load a color library."""
        try:
            print(f"Loading library: {library_name}")
            # Default to basic_colors if no name provided
            if not library_name:
                library_name = "basic_colors"
            
            # Create the library object
            self.library = ColorLibrary(library_name)
            self.current_library_name = library_name
            
            # Update displays
            self._update_library_list()
            self._update_category_list()
            self._update_colors_display()
            self._update_stats()
            
            print(f"Successfully loaded library: {library_name}")
            
        except Exception as e:
            print(f"Error loading library: {e}")
            # Fall back to basic_colors on error
            try:
                print("Falling back to basic_colors library")
                self.library = ColorLibrary("basic_colors")
                self.current_library_name = "basic_colors"
                self._update_library_list()
                self._update_category_list()
                self._update_colors_display()
                self._update_stats()
            except Exception as fallback_error:
                print(f"Critical error: Failed to load basic_colors library: {fallback_error}")
                messagebox.showerror("Error", f"Failed to load library: {str(e)}")
    
    def _update_library_list(self):
        """Update the library selection combobox."""
        # Use unified path resolution
        from utils.path_utils import get_color_libraries_dir
        library_dir = get_color_libraries_dir()
        
        try:
            # Ensure library directory exists
            os.makedirs(library_dir, exist_ok=True)
            
            # Get all library files
            library_files = [f for f in os.listdir(library_dir) if f.endswith("_library.db")]
            
            # Always include basic_colors in the list
            if "basic_colors_library.db" not in library_files:
                library_files.append("basic_colors_library.db")
            
            # Process library names
            library_names = []
            file_to_display = {}
            for f in library_files:
                # Remove "_library.db" suffix
                base_name = f[:-11]
                
                # Special case for basic_colors
                if base_name == 'basic_colors':
                    display_name = 'Basic Colors'
                # Special case for SG
                elif base_name.lower() == 'sg' or base_name.lower() == 'stanley_gibbons_colors':
                    display_name = 'SG'
                    base_name = 'sg'
                # Convert to display name
                elif '_' in base_name:
                    display_name = " ".join(word.capitalize() for word in base_name.split('_'))
                else:
                    display_name = base_name.capitalize()
                
                library_names.append(display_name)
                file_to_display[display_name] = base_name
            
            # Sort alphabetically
            library_names.sort()
            
            # Store the mapping
            self.display_to_file_map = file_to_display
            self.file_to_display_map = {v: k for k, v in file_to_display.items()}
            
            # Update combobox
            self.library_combo['values'] = library_names
            
            # Set current selection
            if self.current_library_name in self.file_to_display_map:
                display_name = self.file_to_display_map[self.current_library_name]
            else:
                # Default to basic_colors
                self.current_library_name = "basic_colors"
                display_name = "Basic Colors"
            
            self.library_var.set(display_name)
            
            # Force UI refresh
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"Error updating library list: {e}")
            # Fall back to basic_colors
            self.library_combo['values'] = ["Basic Colors"]
            self.current_library_name = "basic_colors"
            self.library_var.set("Basic Colors")
            self.display_to_file_map = {"Basic Colors": "basic_colors"}
            self.file_to_display_map = {"basic_colors": "Basic Colors"}
    
    def _update_category_list(self):
        """Update the category list."""
        if not self.library:
            return
        
        # Just update the categories for use in other parts of the interface
        self.categories = ["All"] + self.library.get_categories()
    
    def _update_colors_display(self, reset_pagination=True):
        """Update the colors display in the library tab."""
        if not self.library:
            return
        
        # Get and sort all colors
        all_colors = self.library.get_all_colors()
        all_colors.sort(key=lambda x: (x.category, x.name))
        
        # Apply search filter if active
        if hasattr(self, 'search_term') and self.search_term:
            self.filtered_colors = [color for color in all_colors if 
                                  self.search_term.lower() in color.name.lower() or
                                  (color.notes and self.search_term.lower() in color.notes.lower()) or
                                  self.search_term.lower() in color.category.lower()]
        else:
            self.filtered_colors = all_colors
        
        # Reset pagination if requested
        if reset_pagination:
            self.current_page = 0
        
        # Calculate pagination
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        colors_to_display = self.filtered_colors[start_idx:end_idx]
        
        # Update pagination info
        total_colors = len(self.filtered_colors)
        showing_count = len(colors_to_display)
        start_num = start_idx + 1 if colors_to_display else 0
        end_num = start_idx + showing_count
        
        # Update page info label
        if self.search_term:
            page_text = f"Showing {start_num}-{end_num} of {total_colors} matches (filtered from {len(all_colors)} total)"
        else:
            page_text = f"Showing {start_num}-{end_num} of {total_colors} colors"
        self.page_info_label.config(text=page_text)
        
        # Enable/disable Load More button
        if end_idx >= total_colors:
            self.load_more_btn.config(state='disabled', text="No More")
        else:
            remaining = total_colors - end_idx
            self.load_more_btn.config(state='normal', text=f"Load More ({remaining} remaining)")
        
        # Clear existing content only if reset
        if reset_pagination:
            self.scroll_manager.clear_content()
        
        print(f"\nDEBUG: Loading {showing_count} colors (page {self.current_page + 1})")
        
        # Calculate frame width once
        window_width = self.root.winfo_width() or 800  # Default if not available
        frame_width = window_width - 120  # Account for scrollbar and padding
        
        # Create frames for colors
        for i, color in enumerate(colors_to_display):
            # Create main frame for each color entry
            display_frame = ttk.Frame(self.scroll_manager.content_frame)
            display_frame.pack(fill=tk.X, pady=1, padx=2, expand=True)
            
            # Show color information based on user preferences
            from utils.color_display_utils import get_conditional_color_info
            color_info = get_conditional_color_info(color.rgb, color.lab)

            # Color display on left - simplified
            color_display = ColorDisplay(
                display_frame,
                color.rgb,
                color.name,
                color_info,
                width=min(frame_width - 400, 1200),  # 4x wider (300 -> 1200)
                height=120  # Increased height to show color values properly
            )
            color_display.pack(side=tk.LEFT, fill=tk.Y)

            # Simplified notes display
            notes_frame = ttk.LabelFrame(display_frame, text="Notes", width=250)
            notes_frame.pack(side=tk.LEFT, padx=(5, 2), pady=1, fill=tk.Y)
            notes_frame.pack_propagate(False)  # Keep fixed width

            # Simple label instead of text widget for better performance
            if color.notes and color.notes.strip():
                notes_text = color.notes[:80] + "..." if len(color.notes) > 80 else color.notes
            else:
                notes_text = "No notes"
            
            notes_label = ttk.Label(notes_frame, text=notes_text, wraplength=230, 
                                  font=("Arial", 9), foreground="gray")
            notes_label.pack(padx=5, pady=2, anchor="w")

            # Button frame - positioned after notes
            button_frame = ttk.Frame(display_frame)
            button_frame.pack(side=tk.LEFT, padx=2)
            
            # Edit button
            ttk.Button(
                button_frame,
                text="Edit",
                width=6,
                command=lambda c=color: self._edit_color(c)
            ).pack(pady=1)

            # Delete button
            ttk.Button(
                button_frame,
                text="Delete",
                width=6,
                command=lambda c=color: self._delete_color(c)
            ).pack(pady=1)
            
            # Add context menu
            self._add_color_context_menu(color_display, color)
            
            # Update every 10 items to show progress
            if i % 10 == 0:
                self.root.update_idletasks()
        
        # Update scroll region after all frames are created
        self.scroll_manager.update_scroll_region()
        
        print(f"DEBUG: Display updated with {showing_count} colors")
    
    def _add_color_context_menu(self, color_display, color: LibraryColor):
        """Add context menu to color display."""
        def show_context_menu(event):
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="Edit Color", command=lambda: self._edit_color(color))
            context_menu.add_command(label="Delete Color", command=lambda: self._delete_color(color))
            context_menu.tk_popup(event.x_root, event.y_root)
        
        color_display.bind("<Button-2>", show_context_menu)  # Right-click on Mac
        color_display.bind("<Button-3>", show_context_menu)  # Right-click on Windows/Linux
    
    def _update_stats(self):
        """Update library statistics display."""
        if not self.library:
            self.stats_label.config(text="No library loaded")
            return
        
        color_count = self.library.get_color_count()
        categories = self.library.get_categories()
        
        stats_text = f"Library: {self.current_library_name}\n"
        stats_text += f"Total Colors: {color_count}\n"
        stats_text += f"Categories: {len(categories)} ({', '.join(categories)})"
        
        self.stats_label.config(text=stats_text)
    
    def _load_more_colors(self):
        """Load more colors (next page)."""
        if not self.library:
            return
        
        # Increment page and update display without clearing
        self.current_page += 1
        self._update_colors_display(reset_pagination=False)
    
    def _on_search_changed(self, event=None):
        """Handle search term change."""
        # Add a small delay to avoid too many rapid searches
        if hasattr(self, '_search_after_id'):
            self.root.after_cancel(self._search_after_id)
        
        self._search_after_id = self.root.after(300, self._perform_search)
    
    def _perform_search(self):
        """Perform the actual search."""
        self.search_term = self.search_var.get().strip()
        # Reset to first page when searching
        self.current_page = 0
        self._update_colors_display(reset_pagination=True)
    
    def _clear_search(self):
        """Clear the search and show all colors."""
        self.search_var.set("")
        self.search_term = ""
        self.current_page = 0
        self._update_colors_display(reset_pagination=True)
    
    def _on_library_changed(self, event=None):
        """Handle library selection change."""
        display_name = self.library_var.get()
        if display_name in self.display_to_file_map:
            file_name = self.display_to_file_map[display_name]
            if file_name != self.current_library_name:
                self._load_library(file_name)
    
    def _on_category_changed(self, event=None):
        """Handle category filter change."""
        pass  # Category filtering removed
    
    
    def _create_new_library(self):
        """Create a new library."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Library")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="Library Name:").pack(pady=10)
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        
        def create_library():
            display_name = name_var.get().strip()
            if not display_name:
                messagebox.showerror("Error", "Please enter a library name")
                return
                
            # Validate library name
            if len(display_name) > 50:
                messagebox.showerror(
                    "Invalid Name",
                    "Library name is too long. Please use 50 characters or less."
                )
                return
                
            # Check for invalid characters
            invalid_chars = '<>:"\\/|?*'
            if any(char in display_name for char in invalid_chars):
                messagebox.showerror(
                    "Invalid Characters",
                    f"Library name cannot contain any of these characters: {invalid_chars}\n\n"
                    f"Use letters, numbers, spaces, dashes, or underscores."
                )
                return
                
            # Check if starts/ends with space or period
            if display_name[0].isspace() or display_name[-1].isspace() or \
               display_name.startswith('.') or display_name.endswith('.'):
                messagebox.showerror(
                    "Invalid Name",
                    "Library name cannot start or end with spaces or periods."
                )
                return
            
            # Convert display name to file name (lowercase, underscores)
            file_name = "_".join(display_name.lower().split())
            
            try:
                new_library = ColorLibrary(file_name)
                dialog.destroy()
                
                # Update the display/file name mappings
                if not hasattr(self, 'display_to_file_map'):
                    self.display_to_file_map = {}
                if not hasattr(self, 'file_to_display_map'):
                    self.file_to_display_map = {}
                
                self.display_to_file_map[display_name] = file_name
                self.file_to_display_map[file_name] = display_name
                
                self._load_library(file_name)
                messagebox.showinfo("Success", f"Created new library: {display_name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create library: {str(e)}")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Create", command=create_library).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key
        dialog.bind('<Return>', lambda e: create_library())
    
    def _add_color_dialog(self, event=None):
        """Show dialog to add a new color."""
        print("DEBUG: Add color dialog method called")
        
        # Prevent multiple dialogs from opening
        if hasattr(self, '_add_color_dialog_open') and self._add_color_dialog_open:
            print("DEBUG: Add color dialog already open, ignoring click")
            return
            
        if not self.library:
            messagebox.showerror("Error", "Please load a library first")
            return
            
        try:
            # Set dialog state flag and disable button
            self._add_color_dialog_open = True
            self.add_color_btn.configure(state='disabled')
            print("DEBUG: Opening add color dialog")
            
            # Create and configure the dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Add Color")
            dialog.geometry("400x450")  # Increased height to show all elements
            dialog.transient(self.root)
            
            # Force dialog to be visible and on top
            dialog.lift()
            dialog.focus_force()
            
            print("DEBUG: Dialog window created and configured")
            
            def cleanup_dialog():
                print("DEBUG: Cleaning up add color dialog")
                self._add_color_dialog_open = False
                self.add_color_btn.configure(state='normal')
                dialog.destroy()
                
            def on_dialog_close():
                print("DEBUG: Dialog closing via window controls")
                cleanup_dialog()
            
            # Bind cleanup to dialog close button
            dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
            
            # Center the dialog on screen
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f"+{x}+{y}")
            
            print("DEBUG: Dialog window positioned and ready")
            
            # Ensure dialog stays on top
            dialog.grab_set()
            
            # Create container frames
            content_frame = ttk.Frame(dialog)
            content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
            
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=15, pady=(5, 15))
            
            # Variables
            name_var = tk.StringVar()
            notes_var = tk.StringVar()
            source_var = tk.StringVar()
            rgb_vars = [tk.StringVar(value="0.00") for _ in range(3)]
            lab_vars = [tk.StringVar(value="0.00") for _ in range(3)]
            
            # Form fields
            ttk.Label(content_frame, text="Color Name:").pack(anchor="w", pady=(0, 2))
            ttk.Entry(content_frame, textvariable=name_var, width=40).pack(fill=tk.X, pady=2)
            
            ttk.Label(content_frame, text="Notes:").pack(anchor="w", pady=(10, 2))
            ttk.Entry(content_frame, textvariable=notes_var, width=40).pack(fill=tk.X, pady=2)
            
            ttk.Label(content_frame, text="Source:").pack(anchor="w", pady=(10, 2))
            ttk.Entry(content_frame, textvariable=source_var, width=40).pack(fill=tk.X, pady=2)
            
            # Input for RGB or L*a*b* - manual entries only
            ttk.Label(content_frame, text="Enter either L*a*b* or RGB values (not both required):").pack(anchor="w", pady=(10, 5))
            
            # L*a*b* input
            lab_frame = ttk.Frame(content_frame)
            lab_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(lab_frame, text="L*a*b*:     ").pack(side=tk.LEFT)
            lab_entries = []
            for i, var in enumerate(lab_vars):
                entry = ttk.Entry(lab_frame, textvariable=var, width=8)
                entry.pack(side=tk.LEFT, padx=2)
                lab_entries.append(entry)
            
            # RGB input
            rgb_frame = ttk.Frame(content_frame)
            rgb_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(rgb_frame, text="RGB (0-255):").pack(side=tk.LEFT)
            rgb_entries = []
            for i, var in enumerate(rgb_vars):
                entry = ttk.Entry(rgb_frame, textvariable=var, width=8)
                entry.pack(side=tk.LEFT, padx=2)
                rgb_entries.append(entry)
            
            # Configure validation for decimal places
            def validate_float(action, value_if_allowed):
                if action == '1':  # insert
                    try:
                        if value_if_allowed == "" or value_if_allowed == "-":
                            return True
                        float(value_if_allowed)
                        if '.' in value_if_allowed and len(value_if_allowed.split('.')[1]) > 2:
                            return False
                        return True
                    except ValueError:
                        return False
                return True
            
            vcmd = dialog.register(validate_float)
            
            # Apply validation to all entries
            for entry in rgb_entries + lab_entries:
                entry.configure(validate="key", validatecommand=(vcmd, '%d', '%P'))
            def add_color():
                try:
                    print("DEBUG: Add color button clicked in dialog")
                    name = name_var.get().strip()
                    if not name:
                        messagebox.showerror("Error", "Please enter a color name")
                        return
                    
                    # Try to get RGB values
                    try:
                        rgb = tuple(float(var.get()) for var in rgb_vars)
                    except ValueError:
                        rgb = None
                    
                    # Try to get L*a*b* values
                    try:
                        lab = tuple(float(var.get()) for var in lab_vars)
                    except ValueError:
                        lab = None
                    
                    # Check if either RGB or L*a*b* is provided
                    if rgb is None and lab is None:
                        messagebox.showerror("Error", "Please enter either RGB or L*a*b* values")
                        return
                    
                    success = self.library.add_color(
                        name=name,
                        rgb=rgb,
                        lab=lab,
                        source=source_var.get().strip(),
                        notes=notes_var.get().strip() or None
                    )
                    
                    if success:
                        print(f"DEBUG: Successfully added color: {name}")
                        cleanup_dialog()
                        self._update_category_list()
                        self._update_colors_display()
                        self._update_stats()
                        messagebox.showinfo("Success", f"Added color: {name}")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to add color: {str(e)}")
            
            ttk.Button(button_frame, text="Save", command=add_color).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=cleanup_dialog).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            print(f"DEBUG: Error creating add color dialog: {str(e)}")
            self._add_color_dialog_open = False
            self.add_color_btn.configure(state='normal')
            messagebox.showerror("Error", f"Failed to open Add Color dialog: {str(e)}")
    
    def _edit_color(self, color: LibraryColor):
        """Edit an existing color."""
        if not self.library:
            messagebox.showerror("Error", "Please load a library first")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Color Information")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Variables
        name_var = tk.StringVar(value=color.name)
        source_var = tk.StringVar(value=color.source or "Custom")
        notes_var = tk.StringVar(value=color.notes or "")
        
        # Create frame for fields
        fields_frame = ttk.Frame(dialog)
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Form fields
        ttk.Label(fields_frame, text="Color Name:").pack(anchor="w", pady=(10, 0))
        name_entry = ttk.Entry(fields_frame, textvariable=name_var, width=40)
        name_entry.pack(fill=tk.X, pady=2)
        
        ttk.Label(fields_frame, text="Source:").pack(anchor="w", pady=(10, 0))
        source_entry = ttk.Entry(fields_frame, textvariable=source_var, width=40)
        source_entry.pack(fill=tk.X, pady=2)
        
        ttk.Label(fields_frame, text="Notes:").pack(anchor="w", pady=(10, 0))
        notes_text = tk.Text(fields_frame, height=4, width=40, wrap='word')
        notes_text.pack(fill=tk.BOTH, expand=True, pady=2)
        if color.notes:
            notes_text.insert('1.0', color.notes)

        def save_changes():
            try:
                name = name_var.get().strip()
                if not name:
                    messagebox.showerror("Error", "Please enter a color name")
                    return
                
                source = source_var.get().strip()
                notes = notes_text.get('1.0', 'end-1c').strip()
                
                # Only update if values have changed
                if (name != color.name or 
                    source != color.source or 
                    notes != color.notes):
                    
                    success = self.library.update_color(
                        color_id=color.id,
                        name=name,
                        source=source,
                        notes=notes if notes else None
                    )
                    
                    if success:
                        # Update the color object to reflect changes
                        color.name = name
                        color.source = source
                        color.notes = notes if notes else None
                        
                        dialog.destroy()
                        self._update_colors_display()
                        self._update_stats()
                        messagebox.showinfo("Success", "Changes saved successfully")
                    else:
                        messagebox.showerror("Error", "Failed to save changes")
                else:
                    dialog.destroy()  # No changes to save
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save changes: {str(e)}")

        # Buttons frame at the bottom of dialog
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, pady=10)

        # Add Save and Cancel buttons
        ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Bind Enter key to save
        dialog.bind('<Return>', lambda e: save_changes())
            
    
    def _delete_color(self, color: LibraryColor):
        """Delete a color from the library."""
        if messagebox.askyesno("Confirm Delete", f"Delete color '{color.name}'?"):
            if self.library.remove_color(color.id):
                self._update_colors_display()
                self._update_stats()
                messagebox.showinfo("Success", f"Deleted color: {color.name}")
    
    
    # Removed basic and philatelic library creation methods - users create their own libraries
    
    def _export_library(self):
        """Export library to CSV."""
        if not self.library:
            messagebox.showerror("Error", "Please load a library first")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Library",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{self.current_library_name}_library.csv"
        )
        
        if filename:
            try:
                if self.library.export_library(filename):
                    messagebox.showinfo("Success", f"Library exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {str(e)}")
    
    def _import_library(self):
        """Import library from CSV."""
        if not self.library:
            messagebox.showerror("Error", "Please load a library first")
            return
        
        filename = filedialog.askopenfilename(
            title="Import Library",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            # Ask user how to import
            dialog = tk.Toplevel(self.root)
            dialog.title("Import Options")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Center dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (200)
            y = (dialog.winfo_screenheight() // 2) - (150)
            dialog.geometry(f"400x300+{x}+{y}")
            
            # Variables
            import_type = tk.StringVar(value="current")
            new_lib_name = tk.StringVar()
            
            ttk.Label(dialog, text="Import colors into:").pack(pady=10)
            
            # Radio buttons for import type
            ttk.Radiobutton(dialog, text="Current Library", 
                          variable=import_type, value="current").pack()
            ttk.Radiobutton(dialog, text="New Library", 
                          variable=import_type, value="new").pack()
            
            # New library name entry
            name_frame = ttk.Frame(dialog)
            name_frame.pack(pady=10, fill=tk.X, padx=20)
            ttk.Label(name_frame, text="New Library Name:").pack(side=tk.LEFT)
            name_entry = ttk.Entry(name_frame, textvariable=new_lib_name)
            name_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
            
            def on_import_type_change(*args):
                # Enable/disable name entry based on selection
                if import_type.get() == "new":
                    name_entry.configure(state="normal")
                else:
                    name_entry.configure(state="disabled")
            
            import_type.trace("w", on_import_type_change)
            name_entry.configure(state="disabled")  # Initially disabled
            
            def do_import():
                try:
                    # Store the import parameters before closing dialog
                    import_type_value = import_type.get()
                    new_lib_name_value = new_lib_name.get().strip()
                    
                    # Close the import options dialog first
                    dialog.destroy()
                    
                    # Do the import without progress dialog to avoid timing issues
                    if import_type_value == "new":
                        # Validate new library name
                        if not new_lib_name_value:
                            messagebox.showerror("Error", "Please enter a library name")
                            return
                        
                        # Convert to file-safe name
                        file_name = "_".join(new_lib_name_value.lower().split())
                        
                        # Create new library instance
                        new_library = ColorLibrary(file_name)
                        
                        # Import directly into new library
                        count = new_library.import_library(filename)
                        
                        # Update mappings and refresh
                        self.display_to_file_map[new_lib_name_value] = file_name
                        self.file_to_display_map[file_name] = new_lib_name_value
                        self._update_library_list()
                        self._load_library(file_name)
                    else:
                        # Import into current library
                        count = self.library.import_library(filename, replace_existing=True)
                        self._update_category_list()
                        self._update_colors_display()
                        self._update_stats()
                    
                    # Show success message
                    messagebox.showinfo("Import Complete", f"Successfully imported {count} colors")
                    
                except Exception as e:
                    messagebox.showerror("Import Error", f"Import failed: {str(e)}")
            
            # Buttons
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=20)
            ttk.Button(btn_frame, text="Import", command=do_import).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    # Remove page navigation method as it's now handled by ScrollManager
    
    # Remove the scrolling-related methods as they're now handled by ScrollManager
        
    
    
    def init_comparison_tab(self, image_path: str = None, sample_data: List[Dict] = None):
        """Initialize the comparison tab with optional image and sample data."""
        # Force creation of tabs if they don't exist
        if not hasattr(self, 'notebook'):
            self._create_widgets()
        
        # Ensure we have a library
        if not self.library:
            self.library = ColorLibrary('basic_colors')
        
        # Create comparison tab if it doesn't exist
        if not hasattr(self, 'comparison_manager'):
            self._create_comparison_tab()
        
        # Make sure comparison manager has the library
        self.comparison_manager.library = self.library
        
        # Force update to make sure UI is ready
        self.root.update_idletasks()
        
        # Select the comparison tab (index starts at 0)
        self.notebook.select(self.notebook.index("Compare"))  # Select the tab by name for reliability
        
        # Give UI a moment to stabilize
        self.root.after(100, lambda: self._complete_comparison_init(image_path, sample_data))
    
    def _complete_comparison_init(self, image_path: str = None, sample_data: List[Dict] = None):
        """Complete the comparison tab initialization after UI is stable."""
        try:
            # If we have data to analyze, pass it to the comparison manager
            if image_path and sample_data and hasattr(self, 'comparison_manager'):
                self.comparison_manager.set_analyzed_data(
                    image_path=image_path,
                    sample_data=sample_data
                )
            
            # Final UI update
            self.root.update()
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Initialization Error",
                f"Failed to complete comparison initialization:\n\n{str(e)}"
            )
    
    def quit_app(self):
        """Close the color library manager window."""
        if hasattr(self, 'root'):
            self.root.destroy()
    
    def run(self):
        """Run the color library manager as standalone application."""
        if hasattr(self, 'root'):
            self.root.mainloop()

# Standalone usage
if __name__ == "__main__":
    app = ColorLibraryManager()
    app.run()
