import pandas as pd
import tkinter as tk
from tkinter import ttk
from matplotlib.collections import PathCollection
from mpl_toolkits.mplot3d.art3d import Line3D

class HighlightManager:
    def __init__(self, master, frame, ax, canvas, data_df, use_rgb=False):
        self.master = master
        self.frame = frame
        self.ax = ax
        self.canvas = canvas
        self.data_df = data_df
        self.use_rgb = use_rgb
        
        # Initialize highlight lists for multiple highlights
        self.highlight_scatters = []
        self.highlight_texts = []
        self.highlight_lines = []
        
        # Data tracking variables for debugging
        self.data_id_to_index = {}       # Map DataID to current DataFrame index
        self.scatter_point_order = []    # List of DataIDs in order they appear in scatter plot
        self.data_id_to_scatter_idx = {} # Map DataID to scatter plot point index
        self.original_data_order = []    # Original DataID order before any sorting
        self.pre_sort_indices = {}       # Map DataID to pre-sort DataFrame index
        self.last_highlighted_index = None
        self.last_highlighted_data_id = None
        self.dataframe_version = 0       # Track dataframe updates
        self.sorting_applied = False     # Track if sorting has been applied
        self.current_scatter = None      # Reference to current scatter plot object
        
        # Store the original row indices to handle blank rows
        self.update_row_mapping()
        
        # Create controls
        self.create_controls()
        
    def create_controls(self):
        """Create highlight controls"""
        try:
            # Main frame with border
            controls_frame = tk.Frame(self.frame, relief='sunken', bd=2)
            controls_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
            
            # Configure grid to expand
            controls_frame.grid_columnconfigure(0, weight=0)  # Label column
            controls_frame.grid_columnconfigure(1, weight=1)  # Entry/button column
            
            # Title label with correct font
            title_label = tk.Label(
                controls_frame,
                text="Highlight Controls",
                font=('Arial', 9, 'bold')
            )
            title_label.grid(row=0, column=0, columnspan=2, pady=(5,2))

            # Row number entry with proper spacing
            row_frame = tk.Frame(controls_frame)
            row_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=5)
            row_frame.grid_columnconfigure(1, weight=1)
            
            row_label = tk.Label(row_frame, text="Row #(s):")
            row_label.grid(row=0, column=0, sticky='e', padx=(5,2))
            self.row_entry = tk.Entry(row_frame, width=8)
            self.row_entry.grid(row=0, column=1, sticky='w', padx=(2,5))

            # Button frame
            button_frame = tk.Frame(controls_frame)
            button_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=(2,5))
            button_frame.grid_columnconfigure(0, weight=1)
            button_frame.grid_columnconfigure(1, weight=1)

            self.highlight_button = tk.Button(
                button_frame,
                text="Highlight Data",
                command=self._highlight_data
            )
            self.highlight_button.grid(row=0, column=0, sticky='ew', padx=2)

            self.clear_button = tk.Button(
                button_frame,
                text="Clear Highlight",
                command=self._clear_highlight
            )
            self.clear_button.grid(row=0, column=1, sticky='ew', padx=2)
            
        except Exception as e:
            print(f"Error creating controls: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def update_row_mapping(self):
        """Create a mapping between spreadsheet row numbers and DataFrame indices
        that accounts for blank rows in the original data"""
        try:
            # Get the dataframe length for validation
            df_length = len(self.data_df)
            
            # Create both mappings:
            # 1. From spreadsheet row to DataFrame index
            # 2. From DataFrame index to spreadsheet row
            self.row_mapping = {}
            self.index_to_row = {}
            
            # Check if we have a 'original_row' column that might have been added in data_processor.py
            # This would provide exact mapping between spreadsheet rows and DataFrame indices
            if 'original_row' in self.data_df.columns:
                print("DEBUG: Using 'original_row' column for precise row mapping")
                for idx, row in self.data_df.iterrows():
                    orig_row = int(row['original_row'])
                    # Adjust for header row (+1) and zero-indexing (+1) = +2
                    spreadsheet_row = orig_row + 2
                    self.row_mapping[spreadsheet_row] = idx
                    self.index_to_row[idx] = spreadsheet_row
            else:
                # Fall back to default sequential mapping
                print("DEBUG: Using default sequential row mapping")
                # Row 2 in spreadsheet = index 0 in DataFrame (accounting for header row)
                self.row_mapping = {i+2: i for i in range(df_length)}
                self.index_to_row = {i: i+2 for i in range(df_length)}
            
            # Log mapping information for debugging
            print(f"DEBUG: Created row mapping for {df_length} data points")
            if len(self.row_mapping) <= 20:  # Only print full mapping for small datasets
                print(f"DEBUG: Row mapping: {self.row_mapping}")
            else:
                print(f"DEBUG: First 5 row mappings: {dict(list(self.row_mapping.items())[:5])}")
                print(f"DEBUG: Last 5 row mappings: {dict(list(self.row_mapping.items())[-5:])}")
                
            # Build DataID to index mapping for verification
            self.data_id_to_index = {}
            for idx, row in self.data_df.iterrows():
                if 'DataID' in row:
                    data_id = row['DataID']
                    self.data_id_to_index[data_id] = idx
            
            print(f"DEBUG: Created DataID mapping for {len(self.data_id_to_index)} unique DataIDs")
            
            # Initialize scatter point tracking if not already set
            # Note: This could be incomplete if update_row_mapping is called before 
            # scatter plot is created, but update_references will fix this
            if not self.scatter_point_order and 'DataID' in self.data_df.columns:
                # Initially, scatter points will be in the same order as DataFrame
                self.scatter_point_order = self.data_df['DataID'].tolist()
                self.data_id_to_scatter_idx = {data_id: idx for idx, data_id in enumerate(self.scatter_point_order)}
                
                # Also store the original data order if not already set
                if not self.original_data_order:
                    self.original_data_order = self.scatter_point_order.copy()
                    self.pre_sort_indices = self.data_id_to_index.copy()
                    print(f"DEBUG: Stored original data order with {len(self.original_data_order)} points")
                
                print(f"DEBUG: Initialized scatter point order tracking with {len(self.scatter_point_order)} points")
        except Exception as e:
            print(f"Error creating row mapping: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def find_df_index(self, user_row):
        """
        Find the DataFrame index corresponding to a spreadsheet row number.
        Handles potential gaps in data due to blank rows and the +1 offset issue.
        """
        try:
            print(f"DEBUG: Finding DataFrame index for spreadsheet row {user_row}")
            
            # Check if this exact row exists in our mapping
            if user_row in self.row_mapping:
                df_index = self.row_mapping[user_row]
                print(f"DEBUG: Direct mapping found: spreadsheet row {user_row} → DataFrame index {df_index}")
                return df_index
            
            # If we don't have an exact match, we need to find the appropriate index
            valid_rows = sorted(self.row_mapping.keys())
            
            if not valid_rows:
                # No valid rows in mapping (should not happen)
                print("WARNING: No valid rows in mapping, using basic calculation")
                return max(0, user_row - 2)
                
            # Handle edge cases: before first valid row or after last valid row
            if user_row < min(valid_rows):
                print(f"WARNING: Row {user_row} is before the first valid row {min(valid_rows)}")
                return self.row_mapping[min(valid_rows)]  # Return first mapped index
                
            elif user_row > max(valid_rows):
                print(f"WARNING: Row {user_row} is after the last valid row {max(valid_rows)}")
                return self.row_mapping[max(valid_rows)]  # Return last mapped index
                
            # Find the closest valid row before the requested row
            prev_row = None
            next_row = None
            
            for row in valid_rows:
                if row < user_row:
                    prev_row = row
                elif row > user_row:
                    next_row = row
                    break
                    
            # Log what we found
            if prev_row is not None:
                print(f"DEBUG: Previous valid row: {prev_row} → index {self.row_mapping[prev_row]}")
            if next_row is not None:
                print(f"DEBUG: Next valid row: {next_row} → index {self.row_mapping[next_row]}")
                
            # Calculate offset from blank rows
            if prev_row is not None and next_row is not None:
                # We have valid rows both before and after
                # Check if there's a gap that suggests blank rows
                row_gap = next_row - prev_row
                index_gap = self.row_mapping[next_row] - self.row_mapping[prev_row]
                
                if row_gap > index_gap + 1:
                    # There are blank rows in between
                    print(f"DEBUG: Detected blank rows: row gap = {row_gap}, index gap = {index_gap}")
                    
                # Calculate how far we are from the previous valid row
                offset = user_row - prev_row
                
                # If we're asking for a row between prev and next, and there's a gap,
                # calculate the appropriate index
                if offset <= (row_gap - index_gap):
                    # We're in the blank row region, snap to previous index
                    df_index = self.row_mapping[prev_row]
                    print(f"DEBUG: In blank row region, snapping to previous index {df_index}")
                else:
                    # Past the blank rows, calculate adjusted index
                    df_index = self.row_mapping[prev_row] + (offset - (row_gap - index_gap))
                    print(f"DEBUG: Past blank rows, calculated adjusted index {df_index}")
                    
                return df_index
                
            elif next_row is not None:
                # We only have rows after, use the next valid row's index
                print(f"DEBUG: Only have rows after, using next valid row's index")
                return self.row_mapping[next_row]
                
            elif prev_row is not None:
                # We only have rows before, calculate based on offset from last valid row
                offset = user_row - prev_row
                # Basic check to ensure we don't go out of bounds
                df_index = min(self.row_mapping[prev_row] + offset, len(self.data_df) - 1)
                print(f"DEBUG: Only have rows before, calculated index {df_index} based on offset {offset}")
                return df_index
                
            # Final fallback - use basic calculation
            df_index = max(0, min(user_row - 2, len(self.data_df) - 1))
            print(f"DEBUG: Using fallback calculation, spreadsheet row {user_row} → DataFrame index {df_index}")
            return df_index
            
        except Exception as e:
            print(f"Error finding DataFrame index: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fallback to simple conversion with bounds checking
            return max(0, min(user_row - 2, len(self.data_df) - 1))

    def _highlight_data(self):
        """Highlight the data points for the entered row numbers"""
        try:
            # Clear existing highlights first
            self._clear_highlight(keep_entry=True)
            
            # Get the entered row numbers and split by comma
            entered_rows = self.row_entry.get()
            row_numbers = [int(row.strip()) for row in entered_rows.split(',')]

            # Iterate over each row number
            for user_row in row_numbers:
                print(f"DEBUG: Attempting to highlight row: {user_row}")
                # Find corresponding DataFrame index
                df_index = self.find_df_index(user_row)
                
                if 0 <= df_index < len(self.data_df):
                    # Highlight the point
                    self._highlight_point(df_index)
                    print(f"Highlighting data from row {user_row} (DataFrame index: {df_index})")
                else:
                    print(f"Row {user_row} is out of range. Valid rows are 2 to {len(self.data_df) + 1}")
        
        except ValueError:
            print("Please enter valid row numbers")
        except Exception as e:
            print(f"Error highlighting data points: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def _debug_row_mapping(self):
        """Debug function to test and verify row mapping"""
        try:
            print("\nDEBUG: Testing row mapping functionality")
            print(f"Current DataFrame version: {self.dataframe_version}")
            # Test a few sample rows
            test_rows = [2, 5, 10]
            
            for row in test_rows:
                try:
                    df_index = self.find_df_index(row)
                    print(f"Test: Spreadsheet row {row} → DataFrame index {df_index}")
                    
                    # Verify that we can get the row's data
                    if 0 <= df_index < len(self.data_df):
                        data_id = self.data_df.iloc[df_index]['DataID']
                        print(f"  Data at index {df_index}: DataID = {data_id}")
                    else:
                        print(f"  Index {df_index} is out of range")
                except Exception as e:
                    print(f"  Error testing row {row}: {str(e)}")
            
            # Add a verification test for DataID consistency
            print("\nDEBUG: Testing DataID consistency")
            
            # Sample a few DataIDs to verify 
            if not self.data_df.empty and 'DataID' in self.data_df.columns:
                sample_size = min(5, len(self.data_df))
                sample_indices = sorted([i for i in range(0, len(self.data_df), max(1, len(self.data_df) // sample_size))])[:sample_size]
                
                for idx in sample_indices:
                    data_id = self.data_df.iloc[idx]['DataID']
                    expected_idx = self.data_id_to_index.get(data_id)
                    scatter_idx = self.data_id_to_scatter_idx.get(data_id)
                    
                    if expected_idx != idx:
                        print(f"  CONSISTENCY ERROR: DataID {data_id} is at index {idx} but mapped to index {expected_idx}")
                    else:
                        print(f"  Verified: DataID {data_id} correctly mapped to index {idx}")
                    
                    if scatter_idx is not None:
                        print(f"  Scatter point index for DataID {data_id}: {scatter_idx}")
                    else:
                        print(f"  WARNING: No scatter point index for DataID {data_id}")
                        
            print("DEBUG: Row mapping test complete")
        except Exception as e:
            print(f"Error in debug row mapping: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def _highlight_point(self, idx):
        """Highlight the selected point"""
        try:
            print(f"DEBUG: Highlighting point at index {idx}")
            # Don't clear existing highlights to allow multiple highlights
            
            # Get normalized point coordinates and DataID from the DataFrame
            # This must be done first before any other operations
            point = self.data_df.iloc[idx]
            x, y, z = point['Xnorm'], point['Ynorm'], point['Znorm']
            data_id = point['DataID']
            print(f"DEBUG: Found point at index {idx} with coordinates ({x}, {y}, {z}) with DataID: {data_id}")
            
            # Verify the DataID is valid and update if needed
            if data_id not in self.data_id_to_index:
                print(f"WARNING: DataID {data_id} is not in the data_id_to_index mapping!")
                # Add it now to ensure it's tracked
                self.data_id_to_index[data_id] = idx
                print(f"Added DataID {data_id} to index mapping at position {idx}")
            
            # If this DataID isn't in scatter_point_order, add it now
            if data_id not in self.data_id_to_scatter_idx and self.scatter_point_order:
                print(f"WARNING: DataID {data_id} is not in the scatter_point_order mapping!")
                if not self.sorting_applied:
                    # Only add to scatter point order if sorting hasn't been applied
                    scatter_idx = len(self.scatter_point_order)
                    self.scatter_point_order.append(data_id)
                    self.data_id_to_scatter_idx[data_id] = scatter_idx
                    print(f"Added DataID {data_id} to scatter mapping at position {scatter_idx}")
            
            # If sorting has been applied, we need to handle the mismatch between 
            # DataFrame indices and scatter plot indices
            scatter_idx = None
            if self.sorting_applied and data_id in self.data_id_to_scatter_idx:
                scatter_idx = self.data_id_to_scatter_idx[data_id]
                print(f"DEBUG: Using scatter plot index {scatter_idx} for DataID {data_id} (DataFrame index {idx})")
                
                # Log comparison - this helps track if mapping is correct
                if scatter_idx < len(self.scatter_point_order):
                    expected_data_id = self.scatter_point_order[scatter_idx]
                    if expected_data_id != data_id:
                        print(f"ERROR: Scatter point mapping mismatch! DataID {data_id} maps to scatter_idx {scatter_idx}, but that position contains DataID {expected_data_id}")
                        # CRITICAL: Don't update the mapping! 
                        # If we have a mismatch, we need to find the correct scatter_idx
                        for test_idx, test_data_id in enumerate(self.scatter_point_order):
                            if test_data_id == data_id:
                                print(f"FIXING: Found correct scatter_idx {test_idx} for DataID {data_id}")
                                scatter_idx = test_idx
                                self.data_id_to_scatter_idx[data_id] = test_idx
                                break
                    else:
                        print(f"INFO: Verified scatter point mapping is correct for DataID {data_id}")
                
                # CRITICAL INSIGHT: When sorting is applied, the scatter plot points remain in their
                # original positions, but the DataFrame rows are reordered. The coordinates (x,y,z)
                # from the DataFrame are correct and should be used for highlighting.
                print("INFO: Using DataFrame coordinates for highlighting during sorting")
                
                # When sorting has been applied, we need to make sure we're highlighting the correct point
                # in the scatter plot, which may be different from the DataFrame index
                # The coordinates in the DataFrame are correct, but we should verify against original positions
                print(f"DEBUG: Original point coordinates from DataFrame: ({x}, {y}, {z})")
                
                # Check if we have access to the original (pre-sort) indices
                if data_id in self.pre_sort_indices:
                    original_idx = self.pre_sort_indices[data_id]
                    print(f"DEBUG: Original index for DataID {data_id} was {original_idx}")
            
            # If sorting has been applied, we always trust the DataID-based mapping
            # since the scatter plot points remain in their original order
            if self.sorting_applied:
                # No need to verify or correct index - the coordinates from the DataFrame
                # are correct for highlighting even when sorted
                print(f"SORTING: Using DataFrame coordinates for highlighting (no correction needed)")
            else:
                # For non-sorted data, verify DataID matches our index mapping
                expected_idx = self.data_id_to_index.get(data_id)
                if expected_idx is not None and expected_idx != idx:
                    print(f"WARNING: DataID mismatch detected! DataID {data_id} should be at index {expected_idx}, not {idx}")
                    print(f"STATE CHECK: DataFrame version: {self.dataframe_version}, Sorting applied: {self.sorting_applied}")
                    
                    # Check if we should correct the index
                    verified_idx = expected_idx
                    verified_data_id = self.data_df.iloc[verified_idx]['DataID']
                    
                    if verified_data_id == data_id:
                        print(f"CORRECTION: Using verified index {verified_idx} instead of {idx}")
                        idx = verified_idx
                        # Re-fetch point data with corrected index
                        point = self.data_df.iloc[idx]
                        x, y, z = point['Xnorm'], point['Ynorm'], point['Znorm']
                        data_id = point['DataID']
                        print(f"CORRECTION: Updated point at coordinates ({x}, {y}, {z}) with DataID: {data_id}")
                    else:
                        print(f"VALIDATION ERROR: Verification failed. DataID at index {verified_idx} is {verified_data_id}, not {data_id}")
                        # Dump a portion of the DataFrame for debugging
                        print("Current DataFrame state (first few rows):")
                        print(self.data_df.head().to_string())
                        if len(self.data_df) > 10:
                            print("Current DataFrame state (rows around the issue):")
                            start_idx = max(0, min(idx, expected_idx) - 2)
                            end_idx = min(len(self.data_df), max(idx, expected_idx) + 3)
                            print(self.data_df.iloc[start_idx:end_idx].to_string())
            
            # Store for tracking
            self.last_highlighted_index = idx
            self.last_highlighted_data_id = data_id
            
            # Create scatter plot for highlight
            # Define the coordinates for the highlight point
            highlight_coords = [x, y, z]
            
            # Log the exact coordinates we're using for the highlight
            print(f"DEBUG: Creating highlight scatter at exact coordinates: ({x}, {y}, {z})")
            
            # When sorting has been applied, the coordinates in the DataFrame are correct,
            # but the scatter plot points are still in their original order
            # We're highlighting using coordinates, which is the correct approach
            # The issue occurs when trying to match scatter plot points by index
            
            highlight_scatter = self.ax.scatter(
                [x], [y], [z],
                facecolors='none',
                edgecolors='black',
                s=100,  # Size parameter - only one 's' parameter allowed
                marker='o',
                linewidth=2,
                zorder=1000
            )
            self.highlight_scatters.append(highlight_scatter)
            
            # Store the fact that we highlighted this specific point
            print(f"DEBUG: Highlighted DataID {data_id} (DataFrame index: {idx}, Scatter index: {scatter_idx})")
            # Add DataID label
            # Calculate offset coordinates for the text
            text_x = x + 0.05
            text_y = y + 0.05
            text_z = z
            
            # Use text3D for proper 3D annotation
            print(f"DEBUG: Creating text3D at ({text_x}, {text_y}, {text_z})")
            highlight_text = self.ax.text(
                text_x, text_y, text_z,
                f'{data_id}',
                color='red',
                zorder=1000
            )
            self.highlight_texts.append(highlight_text)
            
            # Create a dotted line connecting the point and the text
            print(f"DEBUG: Creating dotted line from ({x}, {y}, {z}) to ({text_x}, {text_y}, {text_z})")
            highlight_line = Line3D(
                [x, text_x],
                [y, text_y],
                [z, text_z],
                linestyle=':',
                color='black',
                zorder=999
            )
            self.ax.add_line(highlight_line)
            self.highlight_lines.append(highlight_line)
            
            # Print selected point info
            print(f"Selected row index: {idx}")
            print("Data at this index:")
            print(self.data_df.iloc[idx])
            
            # Refresh the canvas
            self.canvas.draw()
            print("DEBUG: Canvas refreshed")
            
        except Exception as e:
            print(f"Error highlighting point: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def _clear_highlight(self, keep_entry=False):
        """Clear all current highlights"""
        try:
            print("DEBUG: Clearing all highlights")
            
            # Remove all highlight scatters
            for scatter in self.highlight_scatters:
                try:
                    if scatter in self.ax.collections:
                        scatter.remove()
                    print("DEBUG: Removed highlight scatter")
                except Exception as e:
                    print(f"DEBUG: Could not remove scatter: {e}")
            self.highlight_scatters = []
                
            # Remove all highlight texts
            for text in self.highlight_texts:
                try:
                    if text in self.ax.texts:
                        text.remove()
                    print("DEBUG: Removed highlight text")
                except Exception as e:
                    print(f"DEBUG: Could not remove text: {e}")
            self.highlight_texts = []

            # Remove all highlight lines
            for line in self.highlight_lines:
                try:
                    if line in self.ax.lines:
                        line.remove()
                    print("DEBUG: Removed highlight line")
                except Exception as e:
                    print(f"DEBUG: Could not remove line: {e}")
            self.highlight_lines = []
                
            # Clear the row entry unless keep_entry is True
            if not keep_entry:
                self.row_entry.delete(0, tk.END)
                print("DEBUG: Cleared row entry")
            
            # Refresh the canvas
            self.canvas.draw()
            
        except Exception as e:
            print(f"Warning: Non-critical error in highlight clearing: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def update_references(self, ax, data_df, use_rgb=False):
        """Update references to axis, data, and use_rgb flag"""
        try:
            # Increment DataFrame version counter
            self.dataframe_version += 1
            print(f"DEBUG: Updating references (DataFrame version: {self.dataframe_version})")
            
            # Check if DataFrame order has changed by comparing DataID order
            # This is an indicator of sorting being applied
            if 'DataID' in self.data_df.columns and 'DataID' in data_df.columns:
                old_data_ids = self.data_df['DataID'].tolist() if not self.data_df.empty else []
                new_data_ids = data_df['DataID'].tolist() if not data_df.empty else []
                
                # Before updating anything, store the pre-sort state if this is the first data load
                if not self.original_data_order and len(old_data_ids) > 0:
                    self.original_data_order = old_data_ids.copy()
                    self.pre_sort_indices = {data_id: idx for idx, data_id in enumerate(old_data_ids)}
                    
                    # Initialize scatter point order to match original data order if not already set
                    if not self.scatter_point_order:
                        self.scatter_point_order = self.original_data_order.copy()
                        self.data_id_to_scatter_idx = {data_id: idx for idx, data_id in enumerate(self.scatter_point_order)}
                    
                    print("DEBUG: Stored original data order before first sort")
                
                # Check if we have the same DataIDs but in a different order (sorted)
                if (len(old_data_ids) == len(new_data_ids) and 
                    set(old_data_ids) == set(new_data_ids) and 
                    old_data_ids != new_data_ids):
                    self.sorting_applied = True
                    print("DEBUG: DataFrame sorting detected - maintaining scatter plot to DataFrame index mapping")
                    
                    # Log the sort change details
                    print("DEBUG: Sorting details:")
                    sample_size = min(5, len(old_data_ids))
                    for i in range(sample_size):
                        old_id = old_data_ids[i]
                        if old_id in new_data_ids:
                            new_idx = new_data_ids.index(old_id)
                            print(f"  DataID {old_id} moved from index {i} to {new_idx}")
                else:
                    # Reset sorting flag if data content has changed (not just order)
                    old_sorting = self.sorting_applied
                    self.sorting_applied = False
                    if old_sorting:
                        print("DEBUG: New data detected - resetting sorting flag")
            
            # First, verify if we had a previously highlighted point
            if self.last_highlighted_data_id is not None and len(self.data_df) > 0:
                try:
                    # Check if the DataID exists in the new DataFrame
                    matches = data_df[data_df['DataID'] == self.last_highlighted_data_id]
                    if not matches.empty:
                        new_idx = matches.index[0]
                        old_idx = self.last_highlighted_index
                        if new_idx != old_idx:
                            print(f"WARNING: After data update, DataID {self.last_highlighted_data_id} moved from index {old_idx} to {new_idx}")
                except Exception as e:
                    print(f"DEBUG: Error checking previous highlight: {str(e)}")
            
            # Before updating dataframe, preserve the original scatter point order if needed
            if 'DataID' in self.data_df.columns:
                if not self.scatter_point_order:
                    print("DEBUG: Preserving original scatter point order before reference update")
                    self.scatter_point_order = self.data_df['DataID'].tolist()
                    self.data_id_to_scatter_idx = {data_id: idx for idx, data_id in enumerate(self.scatter_point_order)}
                elif self.sorting_applied:
                    # If sorting was applied, we need to keep the scatter point order the same,
                    # since the actual scatter plot points don't change order, only the DataFrame indices
                    print("DEBUG: Maintaining existing scatter point order during sort")
                    
                    # CRITICAL: We should NEVER update scatter_point_order after its initial creation
                    # The scatter plot points maintain their original positions even when the DataFrame is sorted
                    
                    # CRITICAL: We should always use the original_data_order for scatter point mapping
                    # This ensures we maintain the original plot order after sorting
                    if self.original_data_order:
                        # Verify scatter_point_order matches original_data_order
                        if self.scatter_point_order != self.original_data_order:
                            print("DEBUG: Resetting scatter_point_order to match original_data_order")
                            self.scatter_point_order = self.original_data_order.copy()
                            self.data_id_to_scatter_idx = {data_id: idx for idx, data_id in enumerate(self.scatter_point_order)}
                    elif not self.scatter_point_order:
                        print("DEBUG: Setting scatter_point_order from current data")
                        self.scatter_point_order = self.data_df['DataID'].tolist()
                        self.data_id_to_scatter_idx = {data_id: idx for idx, data_id in enumerate(self.scatter_point_order)}
            # Store the current scatter plot object reference if available
            scatter_plots = [c for c in self.ax.collections if isinstance(c, PathCollection)]
            if scatter_plots:
                self.current_scatter = scatter_plots[0]
                print(f"DEBUG: Captured reference to current scatter plot")
            
            # Update references
            self.ax = ax
            self.data_df = data_df
            self.use_rgb = use_rgb
            
            # Check if the scatter plot has been recreated
            new_scatter_plots = [c for c in self.ax.collections if isinstance(c, PathCollection)]
            if new_scatter_plots and self.current_scatter != new_scatter_plots[0]:
                print("DEBUG: Detected new scatter plot object - this is crucial to understand sorting behavior")
                self.current_scatter = new_scatter_plots[0]
            
            # Verify DataID uniqueness
            if 'DataID' in self.data_df.columns:
                data_ids = self.data_df['DataID'].tolist()
                unique_ids = set(data_ids)
                if len(data_ids) != len(unique_ids):
                    print(f"WARNING: DataFrame contains {len(data_ids) - len(unique_ids)} duplicate DataIDs!")
                    # Find and report duplicates
                    from collections import Counter
                    duplicates = [item for item, count in Counter(data_ids).items() if count > 1]
                    print(f"Duplicate DataIDs: {duplicates[:10]}")
                    for dup_id in duplicates[:3]:  # Show details for first few duplicates
                        dup_rows = self.data_df[self.data_df['DataID'] == dup_id]
                        print(f"Duplicate rows for DataID {dup_id}:")
                        print(dup_rows.to_string())
            
            # Reset tracking variables
            self.last_highlighted_index = None
            self.last_highlighted_data_id = None
            
            # Update row mapping for the new data
            self.update_row_mapping()
            
            # Clear existing highlight
            self._clear_highlight()
            
            # Update data_id_to_scatter_idx if we're in sorted mode
            if self.sorting_applied and 'DataID' in self.data_df.columns:
                # After sorting, update the DataFrame index mapping while maintaining scatter point order
                new_data_id_to_index = {}
                for idx, row in self.data_df.iterrows():
                    data_id = row['DataID']
                    new_data_id_to_index[data_id] = idx
                
                # Store the updated mapping to use for highlighting
                self.data_id_to_index = new_data_id_to_index
                print(f"DEBUG: Updated DataID to DataFrame index mapping after sorting")
                
                # Critical step: After sorting we need to verify that our scatter point mapping still works
                # Compare DataFrame order with scatter plot order
                df_data_ids = self.data_df['DataID'].tolist()
                
                # CRITICAL INFORMATION FOR DEBUGGING:
                print("\nIMPORTANT SORTING DIAGNOSTIC:")
                print("When DataFrame is sorted, scatter plot points remain in their ORIGINAL order")
                print("This means the order of DataIDs in self.scatter_point_order should be preserved")
                print("We need to ensure our DataID-to-ScatterIdx mapping remains consistent with the original order")
                
                if set(df_data_ids) != set(self.scatter_point_order):
                    print("WARNING: DataFrame DataIDs don't match scatter plot DataIDs after sorting!")
                    print(f"  DataFrame has {len(df_data_ids)} DataIDs, scatter plot has {len(self.scatter_point_order)}")
                    print(f"  First few DataFrame DataIDs: {df_data_ids[:5]}")
                    print(f"  First few scatter plot DataIDs: {self.scatter_point_order[:5]}")
                else:
                    print("DEBUG: Verified all DataIDs present in both DataFrame and scatter plot mapping")
                    
                    # Key behavior check - did the DataIDs change order in self.scatter_point_order?
                    # They should NOT change order since the scatter plot points remain in original order
                    if self.original_data_order and self.scatter_point_order != self.original_data_order:
                        print("ERROR: Scatter point order changed from original! This should not happen.")
                        print(f"Original first 5: {self.original_data_order[:5]}")
                        print(f"Current first 5: {self.scatter_point_order[:5]}")
                        
                        # Reset to original order
                        print("Resetting scatter_point_order to match original order")
                        self.scatter_point_order = self.original_data_order.copy()
                        self.data_id_to_scatter_idx = {data_id: idx for idx, data_id in enumerate(self.scatter_point_order)}
                        print(f"RESET: Reinitialized scatter_point_order with {len(self.scatter_point_order)} points")
                        print(f"RESET: First 5 points: {self.scatter_point_order[:5]}")
                    
                # Create a mapping from DataFrame index to scatter plot index
                # This is crucial for highlight_point to work correctly
                df_idx_to_scatter_idx = {}
                for df_idx, data_id in enumerate(df_data_ids):
                    if data_id in self.data_id_to_scatter_idx:
                        scatter_idx = self.data_id_to_scatter_idx[data_id]
                        df_idx_to_scatter_idx[df_idx] = scatter_idx
                        
                        # Verify mapping consistency
                        if scatter_idx < len(self.scatter_point_order):
                            expected_data_id = self.scatter_point_order[scatter_idx]
                            if expected_data_id != data_id:
                                print(f"ERROR: Scatter mapping inconsistency for DF index {df_idx}!")
                                print(f"  Data ID {data_id} maps to scatter index {scatter_idx}")
                                print(f"  But scatter index {scatter_idx} should contain {expected_data_id}")
                                
                                # Fix the mapping by finding the correct index
                                correct_scatter_idx = None
                                for i, d_id in enumerate(self.scatter_point_order):
                                    if d_id == data_id:
                                        correct_scatter_idx = i
                                        break
                                        
                                if correct_scatter_idx is not None:
                                    print(f"  FIXING: Updating scatter index for {data_id} to {correct_scatter_idx}")
                                    self.data_id_to_scatter_idx[data_id] = correct_scatter_idx
                                    df_idx_to_scatter_idx[df_idx] = correct_scatter_idx
                
                print(f"DEBUG: Created index mapping table with {len(df_idx_to_scatter_idx)} entries")
                # Sample a few mappings to verify
                sample_size = min(3, len(df_idx_to_scatter_idx))
                sample_indices = list(df_idx_to_scatter_idx.keys())[:sample_size]
                for df_idx in sample_indices:
                    data_id = df_data_ids[df_idx]
                    scatter_idx = df_idx_to_scatter_idx[df_idx]
                    print(f"  DataFrame index {df_idx} (DataID {data_id}) maps to scatter plot index {scatter_idx}")
                
                # Validate that all DataIDs in scatter_point_order exist in the new DataFrame
                missing_data_ids = [data_id for data_id in self.scatter_point_order if data_id not in new_data_id_to_index]
                if missing_data_ids:
                    print(f"WARNING: {len(missing_data_ids)} DataIDs from scatter plot are missing in new DataFrame")
                    self.sorting_applied = False  # Reset sorting flag as mapping is no longer valid
            
            # Log information about the updated data
            print(f"DEBUG: Updated highlight manager with {len(data_df)} data points, Sorting applied: {self.sorting_applied}")
            
            # After all updates, double-check that our scatter_point_order is still valid
            if self.sorting_applied and len(self.scatter_point_order) > 0:
                if set(self.data_id_to_scatter_idx.keys()) != set(self.scatter_point_order):
                    print("ERROR: data_id_to_scatter_idx keys don't match scatter_point_order!")
                    missing_ids = set(self.scatter_point_order) - set(self.data_id_to_scatter_idx.keys())
                    extra_ids = set(self.data_id_to_scatter_idx.keys()) - set(self.scatter_point_order)
                    if missing_ids:
                        print(f"Missing IDs in mapping: {list(missing_ids)[:5]}")
                    if extra_ids:
                        print(f"Extra IDs in mapping: {list(extra_ids)[:5]}")
                    
                    # Fix the mapping
                    print("FIXING: Rebuilding data_id_to_scatter_idx from scatter_point_order")
                    self.data_id_to_scatter_idx = {data_id: idx for idx, data_id in enumerate(self.scatter_point_order)}
                else:
                    print("VERIFIED: scatter_point_order and data_id_to_scatter_idx are in sync")
            
            # Add a test function call to verify mapping
            self._debug_row_mapping()
            
        except Exception as e:
            print(f"Error updating references: {str(e)}")
            import traceback
            traceback.print_exc()
