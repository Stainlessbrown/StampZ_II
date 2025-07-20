#!/usr/bin/env python3
"""Database viewer for StampZ color analysis data."""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sqlite3
from typing import Optional, List, Dict
from datetime import datetime

class DatabaseViewer:
    """GUI for viewing and managing color analysis database entries."""
    
    def __init__(self, parent: tk.Tk):
        # Store parent reference
        self.parent = parent
        """Initialize the database viewer window.
        
        Args:
            parent: Parent tkinter window
        """
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("StampZ Database Viewer")
        
        # Set size and position
        dialog_width = 1000
        dialog_height = 600
        
        # Get screen dimensions
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        
        # Calculate position
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.dialog.minsize(800, 500)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Initialize variables
        self.current_sample_set = None
        self.measurements = []
        self.selected_items = set()
        
        self._create_widgets()
        self._load_sample_sets()
    
    def _create_widgets(self):
        """Create and arrange the GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Data source selector at the very top
        source_frame = ttk.Frame(main_frame)
        source_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(source_frame, text="Data Source:").pack(side=tk.LEFT, padx=(0, 5))
        self.data_source = tk.StringVar(value="color_analysis")
        ttk.Radiobutton(source_frame, text="Color Analysis", variable=self.data_source, 
                       value="color_analysis", command=self._on_source_changed).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(source_frame, text="Color Libraries", variable=self.data_source, 
                       value="color_libraries", command=self._on_source_changed).pack(side=tk.LEFT, padx=5)
        
        # Top controls - two rows
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Top row - Sample set and basic controls
        top_row = ttk.Frame(controls_frame)
        top_row.pack(fill=tk.X, pady=(0, 5))
        
        # Bottom row - Filtering and sorting
        filter_frame = ttk.Frame(controls_frame)
        filter_frame.pack(fill=tk.X)
        
        # Filter controls
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_var = tk.StringVar()
        self.filter_combo = ttk.Combobox(filter_frame, values=['Set ID', 'Image Name', 'Date', 'Notes'], width=15)
        self.filter_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.filter_combo.set('Image Name')
        
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=20)
        self.filter_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.filter_var.trace('w', self._apply_filter)
        
        # Sort controls
        ttk.Label(filter_frame, text="Sort by:").pack(side=tk.LEFT, padx=(10, 5))
        self.sort_combo = ttk.Combobox(filter_frame, values=['Set ID', 'Image Name', 'Date', 'Point'], width=15)
        self.sort_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.sort_combo.set('Date')
        
        self.sort_order = tk.BooleanVar(value=True)  # True = ascending
        ttk.Radiobutton(filter_frame, text="Asc", variable=self.sort_order, value=True, command=self._apply_sort).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Desc", variable=self.sort_order, value=False, command=self._apply_sort).pack(side=tk.LEFT, padx=(0, 10))
        
        # Sample set selection
        ttk.Label(controls_frame, text="Sample Set:").pack(side=tk.LEFT, padx=(0, 5))
        self.sample_set_combo = ttk.Combobox(controls_frame, state="readonly", width=30)
        self.sample_set_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.sample_set_combo.bind("<<ComboboxSelected>>", self._on_sample_set_changed)
        
        # Buttons
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Delete Selected", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Clear All", command=self._clear_all_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Manage Templates", command=self._open_template_manager).pack(side=tk.LEFT, padx=5)
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview
        self.tree = ttk.Treeview(tree_frame, selectmode="extended")
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")
        hsb.grid(column=0, row=1, sticky="ew")
        
        # Configure grid weights
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Configure treeview columns
        columns = [
            "set_id", "image_name", "measurement_date", "point", "l_value", "a_value", "b_value",
            "rgb_r", "rgb_g", "rgb_b", "x_pos", "y_pos",
            "shape", "size", "notes"
        ]
        
        self.tree["columns"] = columns
        self.tree["show"] = "headings"  # Hide the first empty column
        
        # Configure column headings and widths
        column_configs = {
            "set_id": ("Set ID", 60),
            "image_name": ("Image", 150),
            "measurement_date": ("Date/Time", 150),
            "point": ("Point", 50),
            "l_value": ("L*", 60),
            "a_value": ("a*", 60),
            "b_value": ("b*", 60),
            "rgb_r": ("R", 50),
            "rgb_g": ("G", 50),
            "rgb_b": ("B", 50),
            "x_pos": ("X", 60),
            "y_pos": ("Y", 60),
            "shape": ("Shape", 80),
            "size": ("Size", 80),
            "notes": ("Notes", 200)
        }
        
        for col, (heading, width) in column_configs.items():
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=50)
        
        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)
        
        # Status bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def _load_sample_sets(self):
        """Load available databases into the combobox based on selected data source."""
        try:
            import sys
            
            # Use the same path detection logic as ColorAnalysisDB
            if hasattr(sys, '_MEIPASS'):
                # Running in PyInstaller bundle - use user data directory
                if sys.platform.startswith('linux'):
                    user_data_dir = os.path.expanduser('~/.local/share/StampZ')
                elif sys.platform == 'darwin':
                    user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ')
                else:
                    user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ')
                base_data_dir = os.path.join(user_data_dir, "data")
            else:
                # Running from source - use relative path
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                base_data_dir = os.path.join(current_dir, "data")
            
            if self.data_source.get() == "color_analysis":
                from utils.color_analysis_db import ColorAnalysisDB
                data_dir = os.path.join(base_data_dir, "color_analysis")
                databases = ColorAnalysisDB.get_all_sample_set_databases(data_dir)
                source_type = "sample sets"
            else:  # color_libraries
                data_dir = os.path.join(base_data_dir, "color_libraries")
                if os.path.exists(data_dir):
                    # Color libraries have different naming - look for _library.db files
                    databases = []
                    for f in os.listdir(data_dir):
                        if f.endswith('_library.db'):
                            # Remove _library.db suffix to get library name
                            databases.append(f[:-11])
                        elif f.endswith('.db') and not f.endswith('_library.db'):
                            # Also include other .db files without suffix
                            databases.append(f[:-3])
                else:
                    databases = []
                source_type = "color libraries"
            
            print(f"DEBUG: Loading {source_type} from: {data_dir}")
            print(f"DEBUG: Found {len(databases)} {source_type}: {databases}")
            
            if databases:
                self.sample_set_combo["values"] = databases
                self.sample_set_combo.set(databases[0])
                self._on_sample_set_changed(None)  # Load first database
            else:
                self.status_var.set(f"No {source_type} found in database")
        
        except Exception as e:
            print(f"DEBUG: Error loading sample sets: {str(e)}")
            messagebox.showerror("Error", f"Failed to load sample sets: {str(e)}")
    
    def _on_source_changed(self):
        """Handle data source change."""
        self._load_sample_sets()
        # Update column headings based on source
        if self.data_source.get() == "color_libraries":
            self.tree.heading("image_name", text="Color Name")
            self.tree.heading("measurement_date", text="")
            self.tree.heading("point", text="")
        else:
            self.tree.heading("image_name", text="Image")
            self.tree.heading("measurement_date", text="Date/Time")
            self.tree.heading("point", text="Point")
    
    def _on_sample_set_changed(self, event):
        """Handle database selection change."""
        selected = self.sample_set_combo.get()
        if selected:
            self.current_sample_set = selected
            self._refresh_data()
    
    def _apply_filter(self, *args):
        """Apply the current filter to the displayed data."""
        filter_text = self.filter_var.get().strip().lower()
        filter_field = self.filter_combo.get()
        
        # Show all items if filter is empty
        if not filter_text:
            for item in self.tree.get_children():
                self.tree.reattach(item, '', 'end')
            return
        
        # Map combo selection to column index
        field_map = {
            'Set ID': 0,
            'Image Name': 1,
            'Date': 2,
            'Notes': 14  # Adjust based on your column indices
        }
        
        col_idx = field_map.get(filter_field, 1)  # Default to Image Name
        
        # Hide items that don't match filter
        for item in self.tree.get_children():
            value = str(self.tree.item(item)['values'][col_idx]).lower()
            if filter_text not in value:
                self.tree.detach(item)
            else:
                self.tree.reattach(item, '', 'end')
        
        self._apply_sort()  # Maintain sort order after filtering
    
    def _apply_sort(self):
        """Sort the currently visible items."""
        sort_field = self.sort_combo.get()
        ascending = self.sort_order.get()
        
        # Map combo selection to column index
        # Define columns list at class level for consistent reference
        columns = [
            "set_id", "image_name", "measurement_date", "point", "l_value", "a_value", "b_value",
            "rgb_r", "rgb_g", "rgb_b", "x_pos", "y_pos", "shape", "size", "notes"
        ]
        
        field_map = {
            'Set ID': 0,  # set_id column index
            'Image Name': 1,  # image_name column index
            'Date': 2,  # measurement_date column index
            'Point': 3  # point column index
        }
        
        col_idx = field_map.get(sort_field, 2)  # Default to Date
        
        # Get all visible items
        items = [(self.tree.item(item)['values'][col_idx], item) for item in self.tree.get_children()]
        
        # Sort items
        items.sort(reverse=not ascending)
        
        # Rearrange items in the tree
        for idx, (_, item) in enumerate(items):
            self.tree.move(item, '', idx)
    
    def _refresh_data(self):
        """Refresh the treeview with current database data."""
        if not self.current_sample_set:
            return
        
        try:
            # Clear existing items
            self.tree.delete(*self.tree.get_children())
            
            # Get current directory
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            if self.data_source.get() == "color_analysis":
                from utils.color_analysis_db import ColorAnalysisDB
                db = ColorAnalysisDB(self.current_sample_set)
                self.measurements = db.get_all_measurements()
                
                # Add to treeview
                for measurement in self.measurements:
                    values = [
                        measurement.get('set_id', ''),
                        measurement.get('image_name', ''),
                        measurement.get('measurement_date', ''),
                        measurement.get('coordinate_point', ''),
                        f"{measurement.get('l_value', 0):.2f}",
                        f"{measurement.get('a_value', 0):.2f}",
                        f"{measurement.get('b_value', 0):.2f}",
                        f"{measurement.get('rgb_r', 0):.2f}",
                        f"{measurement.get('rgb_g', 0):.2f}",
                        f"{measurement.get('rgb_b', 0):.2f}",
                        f"{measurement.get('x_position', 0):.1f}",
                        f"{measurement.get('y_position', 0):.1f}",
                        '',  # shape placeholder
                        '',  # size placeholder
                        measurement.get('notes', '')
                    ]
                    self.tree.insert('', 'end', values=values)
                
                self.status_var.set(f"Loaded {len(self.measurements)} measurements from {self.current_sample_set}")
            
            else:  # color_libraries
                import sys
                
                # Use the same path detection logic as loading
                if hasattr(sys, '_MEIPASS'):
                    # Running in PyInstaller bundle - use user data directory
                    if sys.platform.startswith('linux'):
                        user_data_dir = os.path.expanduser('~/.local/share/StampZ')
                    elif sys.platform == 'darwin':
                        user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ')
                    else:
                        user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ')
                    data_dir = os.path.join(user_data_dir, "data", "color_libraries")
                else:
                    # Running from source - use relative path
                    data_dir = os.path.join(current_dir, "data", "color_libraries")
                
                # Try different naming conventions for color libraries
                db_path = None
                if os.path.exists(os.path.join(data_dir, f"{self.current_sample_set}_library.db")):
                    db_path = os.path.join(data_dir, f"{self.current_sample_set}_library.db")
                elif os.path.exists(os.path.join(data_dir, f"{self.current_sample_set}.db")):
                    db_path = os.path.join(data_dir, f"{self.current_sample_set}.db")
                
                if not db_path or not os.path.exists(db_path):
                    raise Exception(f"Database file not found: {self.current_sample_set}")
                if os.path.getsize(db_path) == 0:
                    raise Exception(f"Database file is empty: {self.current_sample_set}\nTry creating a color library first.")
                
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    # First get the table name
                    cursor.execute("SELECT * FROM library_colors")
                    colors = cursor.fetchall()
                    
                    for color in colors:
                        # Adjust these indices based on your color library schema
                        values = [
                            color[0],  # ID
                            color[1],  # Name
                            color[11],  # date_added
                            "",  # No point number
                            f"{float(color[3]):.2f}",  # lab_l
                            f"{float(color[4]):.2f}",  # lab_a
                            f"{float(color[5]):.2f}",  # lab_b
                            f"{float(color[6]):.2f}",  # rgb_r
                            f"{float(color[7]):.2f}",  # rgb_g
                            f"{float(color[8]):.2f}",  # rgb_b
                            "",  # No position
                            "",
                            "",  # No shape
                            "",  # No size
                            color[12] if color[12] else ""  # notes
                        ]
                        self.tree.insert('', 'end', values=values)
                    
                    self.status_var.set(f"Loaded {len(colors)} colors from {self.current_sample_set}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
    
    def _on_selection_changed(self, event):
        """Handle treeview selection changes."""
        self.selected_items = set(self.tree.selection())
        num_selected = len(self.selected_items)
        self.status_var.set(f"Selected {num_selected} item{'s' if num_selected != 1 else ''}")
    
    def _clear_all_data(self):
        """Clear all data from the current database."""
        if not self.current_sample_set:
            messagebox.showinfo("No Database Selected", "Please select a database first")
            return
        
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if self.data_source.get() == "color_analysis":
            if not messagebox.askyesno("Confirm Clear All",
                                      f"Clear ALL measurements from {self.current_sample_set}?\n\n"
                                      "This action cannot be undone."):
                return
            
            try:
                from utils.color_analysis_db import ColorAnalysisDB
                db = ColorAnalysisDB(self.current_sample_set)
                if db.clear_all_measurements():
                    self._refresh_data()
                    messagebox.showinfo("Success", "All measurements cleared from database")
                else:
                    messagebox.showerror("Error", "Failed to clear measurements")
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear measurements: {str(e)}")
        
        else:  # color_libraries
            if not messagebox.askyesno("Confirm Delete Library",
                                      f"Delete color library '{self.current_sample_set}'?\n\n"
                                      "This action cannot be undone."):
                return
            
            try:
                db_path = os.path.join(current_dir, "data", "color_libraries", self.current_sample_set)
                if os.path.exists(db_path):
                    os.remove(db_path)
                self._load_sample_sets()  # Refresh the database list
                messagebox.showinfo("Success", f"Color library '{self.current_sample_set}' has been deleted")
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete color library: {str(e)}")

    def _open_template_manager(self):
        """Open the Template Manager window."""
        from gui.template_manager import TemplateManager
        TemplateManager(self.parent)
    
    def _delete_selected(self):
        """Delete selected items from database."""
        if not self.selected_items:
            messagebox.showinfo("No Selection", "Please select items to delete")
            return
        
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if self.data_source.get() == "color_analysis":
            if not messagebox.askyesno("Confirm Delete",
                                      f"Delete {len(self.selected_items)} selected measurements?\n\n"
                                      "This action cannot be undone."):
                return
            
            try:
                from utils.color_analysis_db import ColorAnalysisDB
                db = ColorAnalysisDB(self.current_sample_set)
                
                # Get the IDs of selected items
                selected_ids = []
                for item_id in self.selected_items:
                    values = self.tree.item(item_id)['values']
                    if values:
                        selected_ids.append(values[0])  # First column is ID
                
                # Delete from database
                with sqlite3.connect(db.db_path) as conn:
                    cursor = conn.cursor()
                    for measurement_id in selected_ids:
                        cursor.execute(
                            "DELETE FROM color_measurements WHERE id = ?",
                            (measurement_id,)
                        )
                    conn.commit()
                
                # Refresh display
                self._refresh_data()
                messagebox.showinfo("Success", f"Deleted {len(selected_ids)} measurements")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete measurements: {str(e)}")
        
        else:  # color_libraries
            if not messagebox.askyesno("Confirm Delete",
                                      f"Delete {len(self.selected_items)} selected colors?\n\n"
                                      "This action cannot be undone."):
                return
            
            try:
                db_path = os.path.join(current_dir, "data", "color_libraries", self.current_sample_set)
                
                # Get the IDs of selected items
                selected_ids = []
                for item_id in self.selected_items:
                    values = self.tree.item(item_id)['values']
                    if values:
                        selected_ids.append(values[0])  # First column is ID
                
                # Delete from database
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    for color_id in selected_ids:
                        cursor.execute(
                            "DELETE FROM library_colors WHERE id = ?",
                            (color_id,)
                        )
                    conn.commit()
                
                # Refresh display
                self._refresh_data()
                messagebox.showinfo("Success", f"Deleted {len(selected_ids)} colors")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete colors: {str(e)}")
