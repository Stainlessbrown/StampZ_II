import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
from typing import Set, List, Dict, Optional, Callable

class GroupDisplayManager:
    """
    Manages the display of selected groups of data points based on row ranges or clusters.
    Provides a minimalist UI for controlling which points are visible in the plot.
    """
    def __init__(self, master, frame, df, on_visibility_change):
        """
        Initialize the GroupDisplayManager.
        
        Args:
            master: The Tkinter root or parent window
            frame: The frame where controls should be placed
            df: The DataFrame containing the data points
            on_visibility_change: Callback function when visibility changes
        """
        self.master = master
        self.frame = frame
        self.df = df
        self.on_visibility_change = on_visibility_change
        
        # State tracking
        self.visible_indices: Set[int] = set()  # Set of visible DataFrame indices
        self.selection_mode = tk.StringVar(value='row_range')  # 'cluster' or 'row_range'
        self.visibility_enabled = tk.BooleanVar(value=False)
        self.cluster_selection = tk.StringVar(value='')  # For cluster selection dropdown
        
        # Row mapping (from spreadsheet rows to DataFrame indices)
        self.row_mapping = {}  # Will be populated in update_references
        self.index_to_row = {}
        
        # Create controls
        self.create_controls()
        
        # Initialize row mapping
        self.update_row_mapping()
        
    def create_controls(self):
        """Create the group display control panel"""
        # Main frame with bold title and prominent border
        controls_frame = ttk.LabelFrame(self.frame, text="Group Display")
        controls_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        # Force minimum size
        controls_frame.grid_propagate(False)
        controls_frame.configure(height=150, width=350)  # Set minimum dimensions
        
        # Row range controls
        range_frame = ttk.Frame(controls_frame)
        range_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        ttk.Label(range_frame, text="Row Range:").grid(row=0, column=0, sticky='w', padx=5)
        self.range_entry = ttk.Entry(range_frame, width=20)
        self.range_entry.grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Label(range_frame, text="(e.g., 8-44, 50-56)").grid(row=0, column=2, sticky='w', padx=5)
        
        # Selection mode radio buttons (simplified)
        if 'Cluster' in self.df.columns:
            mode_frame = ttk.Frame(controls_frame)
            mode_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=5)
            
            ttk.Radiobutton(
                mode_frame,
                text="Row Range",
                variable=self.selection_mode,
                value='row_range',
                command=self._on_mode_change
            ).grid(row=0, column=0, sticky='w', padx=5)
            
            ttk.Radiobutton(
                mode_frame,
                text="Cluster",
                variable=self.selection_mode,
                value='cluster',
                command=self._on_mode_change
            ).grid(row=0, column=1, sticky='w', padx=5)
        
        # Visibility controls in their own frame
        control_frame = ttk.Frame(controls_frame)
        control_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
        
        ttk.Checkbutton(
            control_frame,
            text="Show Selection",
            variable=self.visibility_enabled,
            command=self._on_visibility_toggle
        ).grid(row=0, column=0, sticky='w', padx=5)
        
        ttk.Button(
            control_frame,
            text="Apply",
            command=self._update_selection
        ).grid(row=0, column=1, sticky='w', padx=5)
        
        ttk.Button(
            control_frame,
            text="Clear",
            command=self.clear_selection
        ).grid(row=0, column=2, sticky='w', padx=5)
        
        # Configure grid weights
        controls_frame.grid_columnconfigure(0, weight=1)
        range_frame.grid_columnconfigure(1, weight=1)
        
        # Create cluster dropdown if needed (initially hidden)
        self.cluster_frame = ttk.Frame(controls_frame)
        self.cluster_frame.grid(row=3, column=0, sticky='ew', padx=5, pady=2)
        
        ttk.Label(self.cluster_frame, text="Cluster:").grid(row=0, column=0, sticky='w', padx=5)
        self.cluster_dropdown = ttk.Combobox(self.cluster_frame, textvariable=self.cluster_selection, state='readonly')
        self.cluster_dropdown.grid(row=0, column=1, sticky='ew', padx=5)
        self.cluster_dropdown.bind('<<ComboboxSelected>>', lambda e: self._update_selection())
        
        self.cluster_frame.grid_columnconfigure(1, weight=1)
        self.cluster_frame.grid_remove()  # Hide initially

    def update_row_mapping(self):
        """Create a mapping between spreadsheet row numbers and DataFrame indices"""
        try:
            # Get the dataframe length for validation
            df_length = len(self.df)
            
            # Create both mappings:
            # 1. From spreadsheet row to DataFrame index
            # 2. From DataFrame index to spreadsheet row
            self.row_mapping = {}
            self.index_to_row = {}
            
            # Check if we have an 'original_row' column for precise mapping
            if 'original_row' in self.df.columns:
                print("Group Display: Using 'original_row' column for precise row mapping")
                for idx, row in self.df.iterrows():
                    orig_row = int(row['original_row'])
                    # Adjust for header row (+1) and zero-indexing (+1) = +2
                    spreadsheet_row = orig_row + 2
                    self.row_mapping[spreadsheet_row] = idx
                    self.index_to_row[idx] = spreadsheet_row
            else:
                # Fall back to default sequential mapping
                print("Group Display: Using default sequential row mapping")
                # Row 2 in spreadsheet = index 0 in DataFrame (accounting for header row)
                self.row_mapping = {i+2: i for i in range(df_length)}
                self.index_to_row = {i: i+2 for i in range(df_length)}
            
            print(f"Group Display: Created row mapping for {df_length} data points")
            
        except Exception as e:
            print(f"Error creating row mapping: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _on_mode_change(self):
        """Handle selection mode change"""
        mode = self.selection_mode.get()
        
        if mode == 'cluster':
            # Check if clusters exist
            if 'Cluster' not in self.df.columns or self.df['Cluster'].isna().all():
                messagebox.showwarning(
                    "No Clusters Available",
                    "Please run K-means clustering first to create clusters."
                )
                self.selection_mode.set('row_range')
                return
            
            # Show cluster controls, hide range controls
            self.range_frame.grid_remove()
            self._update_cluster_dropdown()
            self.cluster_frame.grid()
        else:  # 'row_range'
            # Show range controls, hide cluster controls
            self.cluster_frame.grid_remove()
            self.range_frame.grid()
        
        # Clear current selection when changing modes
        self.visible_indices.clear()
        self.on_visibility_change()
    
    def _update_cluster_dropdown(self):
        """Update the cluster dropdown with available clusters"""
        if 'Cluster' not in self.df.columns:
            return
        
        # Get unique clusters
        clusters = sorted(self.df['Cluster'].dropna().unique())
        cluster_values = [str(c) for c in clusters]
        
        # Update dropdown
        self.cluster_dropdown['values'] = cluster_values
        if cluster_values and not self.cluster_selection.get():
            self.cluster_selection.set(cluster_values[0])
    
    def _on_visibility_toggle(self):
        """Handle visibility checkbox toggle"""
        if self.visibility_enabled.get():
            self._update_selection()
        else:
            # When toggled off, clear selection but keep the inputs
            self.visible_indices.clear()
            self.on_visibility_change()
    
    def _parse_range_str(self, range_str: str) -> Set[int]:
        """
        Parse a range string like '8-44, 50-56' into a set of DataFrame indices.
        Handles conversion from spreadsheet rows (1-based) to DataFrame indices.
        """
        indices = set()
        
        if not range_str.strip():
            return indices
            
        try:
            # Split by comma and process each range
            for range_part in range_str.split(','):
                range_part = range_part.strip()
                if not range_part:
                    continue
                    
                if '-' in range_part:
                    # Handle range like 8-44
                    start_str, end_str = range_part.split('-')
                    start_row = int(start_str.strip())
                    end_row = int(end_str.strip())
                    
                    # Convert to DataFrame indices using row mapping
                    for row in range(start_row, end_row + 1):
                        if row in self.row_mapping:
                            indices.add(self.row_mapping[row])
                else:
                    # Handle single row like 8
                    row = int(range_part.strip())
                    if row in self.row_mapping:
                        indices.add(self.row_mapping[row])
        except ValueError as e:
            messagebox.showerror("Invalid Range", f"Invalid range format: {str(e)}")
        
        return indices
    
    def _update_selection(self):
        """Update the current selection based on mode and input"""
        if not self.visibility_enabled.get():
            return
            
        self.visible_indices.clear()
        
        if self.selection_mode.get() == 'cluster':
            # Cluster-based selection
            selected_cluster = self.cluster_selection.get()
            if 'Cluster' in self.df.columns and selected_cluster:
                try:
                    # Convert string back to appropriate type (int, float, etc.)
                    cluster_value = type(self.df['Cluster'].dropna().iloc[0])(selected_cluster)
                    # Find rows with the selected cluster
                    cluster_mask = self.df['Cluster'] == cluster_value
                    self.visible_indices.update(
                        self.df[cluster_mask].index.tolist()
                    )
                except (ValueError, IndexError):
                    print(f"Error converting cluster value: {selected_cluster}")
        else:  # row_range mode
            range_str = self.range_entry.get().strip()
            if range_str:
                self.visible_indices.update(self._parse_range_str(range_str))
        
        # Trigger update in main application
        self.on_visibility_change()
    
    def clear_selection(self):
        """Clear the current selection"""
        self.visible_indices.clear()
        self.range_entry.delete(0, tk.END)
        self.visibility_enabled.set(False)
        self.on_visibility_change()
    
    def update_references(self, df):
        """Update the DataFrame reference when data changes"""
        self.df = df
        
        # Update row mapping
        self.update_row_mapping()
        
        # Update cluster dropdown if in cluster mode
        if self.selection_mode.get() == 'cluster':
            self._update_cluster_dropdown()
        
        # Reapply current selection with updated DataFrame
        if self.visibility_enabled.get():
            self._update_selection()
    
    def get_visible_mask(self) -> pd.Series:
        """
        Return a boolean mask for visible rows.
        When disabled or no selection, all points are visible.
        When enabled, only selected points are visible.
        """
        if not self.visibility_enabled.get():
            # When disabled, show all points
            return pd.Series(True, index=self.df.index)
        
        # When enabled, only show selected points
        mask = pd.Series(False, index=self.df.index)  # Start with all False
        if self.visible_indices:
            mask.loc[list(self.visible_indices)] = True  # Set True for selected indices
        return mask

