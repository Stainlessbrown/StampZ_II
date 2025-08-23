#!/usr/bin/env python3
"""Template manager for StampZ templates stored in coordinates.db."""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sqlite3
from typing import Optional, List, Dict
from datetime import datetime

class TemplateManager:
    """GUI for viewing and managing templates stored in coordinates.db."""
    
    def __init__(self, parent: tk.Tk):
        """Initialize the template manager window.
        
        Args:
            parent: Parent tkinter window
        """
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("StampZ Template Manager")
        
        # Set size and position
        dialog_width = 800
        dialog_height = 500
        
        # Get screen dimensions
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        
        # Calculate position
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.dialog.minsize(600, 400)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_templates()
    
    def _create_widgets(self):
        """Create and arrange the GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Refresh and Delete buttons
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Delete Selected", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        
        # Create template list view
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview
        self.tree = ttk.Treeview(list_frame, selectmode="extended")
        
        # Scrollbars
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")
        hsb.grid(column=0, row=1, sticky="ew")
        
        # Configure grid weights
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        # Configure treeview columns
        columns = ["id", "name", "image_path", "created_at", "coord_count"]
        self.tree["columns"] = columns
        self.tree["show"] = "headings"
        
        # Configure column headings and widths
        column_configs = {
            "id": ("ID", 50),
            "name": ("Template Name", 200),
            "image_path": ("Image Path", 300),
            "created_at": ("Created", 150),
            "coord_count": ("Coordinates", 80)
        }
        
        for col, (heading, width) in column_configs.items():
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=50)
        
        # Status bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Bind double-click to view details
        self.tree.bind("<Double-1>", self._show_template_details)
    
    def _get_db_path(self) -> str:
        """Get the path to coordinates.db."""
        import sys
        if hasattr(sys, '_MEIPASS'):
            # Running as packaged app - use persistent user directory
            if sys.platform.startswith('linux'):
                user_data_dir = os.path.expanduser('~/.local/share/StampZ_II')
            elif sys.platform == 'darwin':
                user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ_II')
            else:
                user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ_II')
            return os.path.join(user_data_dir, "coordinates.db")
        else:
            # Running in development - use project data directory
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(current_dir, "data", "coordinates.db")
    
    def _load_templates(self):
        """Load templates from coordinates.db into the treeview."""
        try:
            db_path = self._get_db_path()
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Get all templates with their coordinate counts (excluding temporary/manual mode)
                cursor.execute("""
                    SELECT 
                        cs.id,
                        cs.name,
                        cs.image_path,
                        cs.created_at,
                        COUNT(c.id) as coord_count
                    FROM coordinate_sets cs
                    LEFT JOIN coordinates c ON cs.id = c.set_id
                    WHERE NOT EXISTS (
                        SELECT 1 FROM coordinates c2 
                        WHERE c2.set_id = cs.id AND c2.temporary = 1
                    )
                    GROUP BY cs.id
                    ORDER BY cs.created_at DESC
                """)
                
                templates = cursor.fetchall()
                
                # Clear existing items
                self.tree.delete(*self.tree.get_children())
                
                # Add templates to treeview
                for template in templates:
                    self.tree.insert('', 'end', values=template)
                
                self.status_var.set(f"Loaded {len(templates)} templates")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load templates: {str(e)}")
    
    def _refresh_data(self):
        """Refresh the template list."""
        self._load_templates()
    
    def _delete_selected(self):
        """Delete selected templates from coordinates.db."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select templates to delete")
            return
        
        if not messagebox.askyesno("Confirm Delete",
                                f"Delete {len(selected)} selected template(s)?\n\n"
                                "This action cannot be undone."):
            return
        
        try:
            db_path = self._get_db_path()
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                for item_id in selected:
                    template_id = self.tree.item(item_id)['values'][0]
                    
                    # Delete related color data first
                    cursor.execute(
                        "DELETE FROM color_data WHERE coordinate_id IN "
                        "(SELECT id FROM coordinates WHERE set_id = ?)",
                        (template_id,)
                    )
                    
                    # Delete coordinates
                    cursor.execute(
                        "DELETE FROM coordinates WHERE set_id = ?",
                        (template_id,)
                    )
                    
                    # Delete template
                    cursor.execute(
                        "DELETE FROM coordinate_sets WHERE id = ?",
                        (template_id,)
                    )
                
                conn.commit()
            
            self._refresh_data()
            messagebox.showinfo("Success", f"Deleted {len(selected)} template(s)")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete templates: {str(e)}")
    
    def _show_template_details(self, event):
        """Show details for the selected template."""
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        template_id = self.tree.item(item)['values'][0]
        
        try:
            db_path = self._get_db_path()
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Get coordinates for template
                cursor.execute("""
                    SELECT 
                        c.point_order,
                        c.x,
                        c.y,
                        c.sample_type,
                        c.sample_width,
                        c.sample_height,
                        c.anchor_position
                    FROM coordinates c
                    WHERE c.set_id = ?
                    ORDER BY c.point_order
                """, (template_id,))
                
                coordinates = cursor.fetchall()
                
                # Create details window
                details = tk.Toplevel(self.dialog)
                details.title("Template Details")
                details.geometry("600x400")
                
                # Make modal
                details.transient(self.dialog)
                details.grab_set()
                
                # Create treeview for coordinates
                tree = ttk.Treeview(details)
                tree["columns"] = ["point", "x", "y", "type", "width", "height", "anchor"]
                tree["show"] = "headings"
                
                for col, width in [
                    ("point", 50),
                    ("x", 80),
                    ("y", 80),
                    ("type", 100),
                    ("width", 80),
                    ("height", 80),
                    ("anchor", 100)
                ]:
                    tree.heading(col, text=col.title())
                    tree.column(col, width=width)
                
                # Add scrollbars
                vsb = ttk.Scrollbar(details, orient="vertical", command=tree.yview)
                hsb = ttk.Scrollbar(details, orient="horizontal", command=tree.xview)
                tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
                
                # Grid layout
                tree.grid(column=0, row=0, sticky="nsew")
                vsb.grid(column=1, row=0, sticky="ns")
                hsb.grid(column=0, row=1, sticky="ew")
                
                # Configure grid weights
                details.grid_columnconfigure(0, weight=1)
                details.grid_rowconfigure(0, weight=1)
                
                # Add coordinates to treeview
                for coord in coordinates:
                    tree.insert('', 'end', values=coord)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show template details: {str(e)}")
