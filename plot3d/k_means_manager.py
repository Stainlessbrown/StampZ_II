import os
import logging
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from typing import Optional, Tuple, Dict, Any, Union, List
import ezodf
import tkinter as tk
from tkinter import messagebox, filedialog
import time
import fcntl
import errno

class KmeansManager:
    """
    Manager class for applying K-means clustering on normalized coordinate data.
    """
    
    # Define expected column structure
    # Define expected column structure
    EXPECTED_COLUMNS = ['Xnorm','Ynorm','Znorm','DataID','Cluster','∆E','Marker',
                        'Color','Centroid_X','Centroid_Y','Centroid_Z','Sphere']
    # Columns used for clustering
    CLUSTER_COLUMNS = ['Xnorm', 'Ynorm', 'Znorm']
    
    def __init__(self, logger: Optional[logging.Logger] = None, on_data_update=None):
        """Initialize the KmeansManager with proper logging."""
        # Set up logger
        if logger is None:
            self.logger = logging.getLogger(__name__)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger
            
        self.data = None
        self.on_data_update = on_data_update
        self.file_path = None
        
        # Initialize GUI components as None
        self.frame = None
        self.start_row = None
        self.end_row = None
        self.n_clusters = None
        self.apply_button = None
        self.save_button = None
        
        self.logger.info("KmeansManager initialized successfully")
    
    def create_gui(self, parent):
        """Create the GUI controls for K-means clustering"""
        self.frame = tk.LabelFrame(parent, text="K-means Clustering")
        
        # Create control frame
        control_frame = tk.Frame(self.frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Row range inputs
        tk.Label(control_frame, text="Rows:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.start_row = tk.Entry(control_frame, width=4)
        self.start_row.insert(0, "2")
        self.start_row.pack(side=tk.LEFT, padx=1)
        
        tk.Label(control_frame, text="-", font=("Arial", 9)).pack(side=tk.LEFT)
        self.end_row = tk.Entry(control_frame, width=4)
        self.end_row.insert(0, "999")
        self.end_row.pack(side=tk.LEFT, padx=1)
        
        # Number of clusters input
        tk.Label(control_frame, text="k=", font=("Arial", 9)).pack(side=tk.LEFT, padx=(3,0))
        self.cluster_count = tk.Entry(control_frame, width=2)
        self.cluster_count.insert(0, "3")
        self.cluster_count.pack(side=tk.LEFT, padx=1)
        
        # Action buttons
        # Create a frame for stacked buttons with full width
        button_frame = tk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT, padx=2)  # Move to right side

        # Apply button on top
        self.apply_button = tk.Button(
            button_frame,
            text="Apply",
            width=6,              # Slightly reduced width
            relief=tk.RAISED,
            bg='#e1e1e1',        # Light gray background
            font=('Arial', 9, 'bold'),
            pady=1               # Minimal vertical padding
        )
        self.apply_button.pack(side=tk.TOP, pady=1)  # Stack on top

        # Save button below
        self.save_button = tk.Button(
            button_frame,
            text="Save",
            width=6,              # Slightly reduced width
            relief=tk.RAISED,
            bg='#e6f3ff',        # Light blue background
            fg='dark blue',      # Blue text
            font=('Arial', 9, 'bold'),
            pady=1               # Minimal vertical padding
        )
        self.save_button.pack(side=tk.TOP, pady=1)  # Stack below Apply button

        # Configure command callbacks
        self.apply_button.configure(command=lambda: self._apply_kmeans_gui())
        self.save_button.configure(command=lambda: self.save_cluster_assignments())
        
        # Help button
        help_button = tk.Button(control_frame, text="?", width=2)
        help_button.pack(side=tk.LEFT, padx=2)
        help_button.configure(command=lambda: self._show_workflow_guide())
        
        return self.frame
    
    def load_data(self, dataframe: pd.DataFrame) -> None:
        """Load data into the manager."""
        if dataframe is None:
            self.logger.warning("Received None DataFrame")
            self.data = None
            return
            
        # Validate DataFrame columns
        if not all(col in dataframe.columns for col in self.EXPECTED_COLUMNS):
            missing = [col for col in self.EXPECTED_COLUMNS if col not in dataframe.columns]
            self.logger.error(f"DataFrame is missing required columns: {missing}")
            raise ValueError(f"DataFrame is missing required columns: {missing}")
        
        # Clear any existing centroid data
        dataframe = dataframe.copy()
        dataframe['Centroid_X'] = float('nan')
        dataframe['Centroid_Y'] = float('nan')
        dataframe['Centroid_Z'] = float('nan')
        dataframe['Cluster'] = None
        self.logger.info("Cleared any existing centroid data in the loaded DataFrame")
        
        self.data = dataframe.copy()
        self.logger.info(f"Loaded DataFrame with {len(dataframe)} rows")
        self.logger.info(f"Current Cluster column values after load:")
        self.logger.info(self.data['Cluster'].value_counts().to_dict())
    
    def apply_kmeans(self, start_row: int, end_row: int, n_clusters: int = 3) -> pd.DataFrame:
        """Apply K-means clustering to the specified row range."""
        try:
            # Validate input parameters
            start_row, end_row = self.validate_row_range(start_row, end_row)
            
            # Validate n_clusters
            if n_clusters < 2:
                self.logger.warning(f"Invalid n_clusters {n_clusters}, adjusting to minimum value 2")
                n_clusters = 2
            
            # Debug print the input parameters
            print(f"\nDebug: Input parameters:")
            print(f"Start row: {start_row}")
            print(f"End row: {end_row}")
            print(f"Number of clusters: {n_clusters}")
            
            # Create a working copy of the DataFrame
            df_copy = self.data.copy()
            print(f"Total rows in DataFrame: {len(df_copy)}")
            
            # Extract the subset of rows to apply K-means on
            subset_indices = list(self._get_row_indices(start_row, end_row))
            print(f"\nDebug: Subset indices: {subset_indices}")
            print(f"Number of rows selected: {len(subset_indices)}")
            
            if not subset_indices:
                raise ValueError("No rows selected for clustering")
                
            # Verify we have the expected number of rows
            expected_row_count = end_row - start_row + 1
            if len(subset_indices) != expected_row_count:
                self.logger.warning(f"Row count mismatch! Expected {expected_row_count} rows, got {len(subset_indices)}.")
                
                # Check specifically for the last row
                # Check specifically for the last row - simplify condition
                if end_row >= len(self.data):  # If requesting last row or beyond
                    last_index = len(self.data) - 1
                    if last_index not in subset_indices:
                        self.logger.warning(f"Last row (index {last_index}) is missing from the selection!")
                        # Force inclusion of the last row
                        if last_index not in subset_indices:
                            subset_indices.append(last_index)
                            self.logger.info(f"Added missing last row (index {last_index}) to the selection")
                
            # Double-check the last row is included if it was requested
            if end_row >= len(self.data):
                last_index = len(self.data) - 1
                if last_index not in subset_indices:
                    self.logger.warning(f"CRITICAL: Last row still missing after initial checks!")
                    subset_indices.append(last_index)
                    self.logger.info(f"Force-added last row (index {last_index}) as final fallback")
                        
            # Log the indices being used for clustering
            if subset_indices:
                self.logger.info(f"Row indices for clustering: first={subset_indices[0]}, last={subset_indices[-1]}, count={len(subset_indices)}")
            
            # Get the subset data and ensure we exclude any rows with invalid data
            subset_data = df_copy.iloc[subset_indices]
            
            # Check if we have a 'valid_data' column to filter by
            if 'valid_data' in subset_data.columns:
                valid_subset_data = subset_data[subset_data['valid_data'] == True]
                print(f"\nDebug: Filtered out {len(subset_data) - len(valid_subset_data)} invalid data rows")
                subset_data = valid_subset_data
            
            # Check for and remove rows with NaN or zero values in coordinate columns
            # Only exclude rows where ALL coordinates are problematic (true blank rows)
            # This preserves rows where at least one coordinate is valid
            x_valid = ~(subset_data['Xnorm'].isna() | (subset_data['Xnorm'] == 0))
            y_valid = ~(subset_data['Ynorm'].isna() | (subset_data['Ynorm'] == 0))
            z_valid = ~(subset_data['Znorm'].isna() | (subset_data['Znorm'] == 0))
            
            # A row is valid if at least one coordinate is valid (non-zero and non-NaN)
            coord_mask = x_valid | y_valid | z_valid
            
            # Check for gaps in original row numbers (indicating blank line separators)
            if 'original_row' in subset_data.columns:
                # Sort by original row to ensure proper sequence
                sorted_subset = subset_data.sort_values('original_row')
                original_rows = sorted_subset['original_row'].tolist()
                
                # Check for gaps larger than 1 (indicating blank line separators)
                gaps = []
                for i in range(len(original_rows) - 1):
                    if original_rows[i+1] - original_rows[i] > 1:
                        gaps.append((original_rows[i], original_rows[i+1]))
                
                if gaps:
                    print(f"\nDebug: Found {len(gaps)} gaps in row numbers: {gaps}")
                    self.logger.info(f"Found {len(gaps)} gaps in original row numbers")
                    
                    # If there are gaps, only include rows before the first gap
                    if len(gaps) > 0:
                        first_gap_end = gaps[0][0]
                        print(f"\nDebug: Using only rows before first gap (ends at original row {first_gap_end})")
                        self.logger.info(f"Will only use rows before first gap (ending at original row {first_gap_end})")
                        
                        # Update coord_mask to also exclude rows after the first gap
                        coord_mask = coord_mask & (subset_data['original_row'] <= first_gap_end)
            
            # Log which rows are being excluded due to zero or NaN values
            excluded_mask = ~coord_mask
            if excluded_mask.any():
                excluded_rows = subset_data[excluded_mask]
                print(f"\nDebug: Rows being excluded due to validity checks:")
                if 'original_row' in excluded_rows.columns:
                    original_rows = excluded_rows['original_row'].tolist()
                    print(f"Original row numbers: {original_rows}")
                print(excluded_rows[['DataID', 'Xnorm', 'Ynorm', 'Znorm']].to_string())
                self.logger.warning(f"Excluding {len(excluded_rows)} rows with invalid coordinates or after blank line gap")
            
            clean_subset_data = subset_data[coord_mask]
            if len(clean_subset_data) < len(subset_data):
                print(f"\nDebug: Removed {len(subset_data) - len(clean_subset_data)} rows with NaN or zero coordinates")
                subset_data = clean_subset_data
            
            # Final verification of dataset
            # Final verification of dataset
            print(f"\nDebug: Final dataset for K-means has {len(subset_data)} rows")
            print("\nDebug: First few rows of selected data:")
            print(subset_data[['DataID', 'Xnorm', 'Ynorm', 'Znorm']].head())
            print("\nDebug: Last few rows of selected data:")
            print(subset_data[['DataID', 'Xnorm', 'Ynorm', 'Znorm']].tail())
            
            # Print original row numbers to help with debugging
            if 'original_row' in subset_data.columns:
                print("\nDebug: Original row numbers included in final dataset:")
                original_rows = sorted(subset_data['original_row'].tolist())
                print(f"Row count: {len(original_rows)}, Min: {min(original_rows)}, Max: {max(original_rows)}")
                print(f"All rows: {original_rows}")
            # Additional check for blank rows - log row numbers with problematic values
            problematic_rows = subset_data[subset_data[self.CLUSTER_COLUMNS].isna().any(axis=1)]
            if not problematic_rows.empty:
                self.logger.warning(f"Found {len(problematic_rows)} rows with NaN values in coordinates")
                if 'original_row' in problematic_rows.columns:
                    self.logger.warning(f"Problematic original row numbers: {problematic_rows['original_row'].tolist()}")
                # Filter out these problematic rows
                subset_data = subset_data.dropna(subset=self.CLUSTER_COLUMNS)
                print(f"\nDebug: Removed {len(problematic_rows)} rows with NaN coordinates")
            
            # Verify we still have enough data
            if len(subset_data) == 0:
                raise ValueError("No valid data points remain after filtering - cannot perform clustering")
            
            # Prepare data for K-means clustering
            X = subset_data[self.CLUSTER_COLUMNS].values
            print(f"\nDebug: Shape of input matrix X: {X.shape}")
            
            # Verify X doesn't contain any NaN values
            if np.isnan(X).any():
                self.logger.error("X matrix contains NaN values after filtering - cannot proceed")
                nan_positions = np.isnan(X)
                if nan_positions.any():
                    nan_rows = np.where(nan_positions.any(axis=1))[0]
                    self.logger.error(f"NaN values found in rows: {nan_rows}")
                raise ValueError("Dataset contains NaN values after filtering - cannot perform clustering")
            
            # Summarize the final data being used
            print("\nDebug: Final coordinate ranges:")
            print(f"Xnorm: min={X[:,0].min():.4f}, max={X[:,0].max():.4f}")
            print(f"Ynorm: min={X[:,1].min():.4f}, max={X[:,1].max():.4f}")
            print(f"Znorm: min={X[:,2].min():.4f}, max={X[:,2].max():.4f}")
            
            # Verify we have enough data points for the requested number of clusters
            if len(X) < n_clusters:
                raise ValueError(f"Not enough data points ({len(X)}) for {n_clusters} clusters")
            
            # Apply K-means clustering
            # Apply K-means clustering
            self.logger.info(f"Applying K-means with {n_clusters} clusters to rows {start_row}-{end_row}")
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(X)
            
            # Use cluster labels directly without adding 1
            formatted_clusters = cluster_labels
            
            # Verify we have cluster assignments for all expected rows
            self.logger.info(f"Generated {len(formatted_clusters)} cluster assignments for {len(subset_data)} data points")
            if len(formatted_clusters) != len(subset_data):
                self.logger.warning(f"Mismatch between data points ({len(subset_data)}) and cluster assignments ({len(formatted_clusters)})!")
            # Get the centroids from the KMeans model
            centroids = kmeans.cluster_centers_
            self.logger.info(f"Calculated {len(centroids)} cluster centroids")
            # Update the "Cluster" column in the original DataFrame
            # Make sure we have the right number of formatted clusters
            
            # Additional verification to ensure we have assignments for all rows
            self.logger.info(f"Number of subset indices: {len(subset_indices)}")
            self.logger.info(f"Number of cluster assignments: {len(formatted_clusters)}")
            centroid_map = {}
            for cluster_idx, centroid in enumerate(centroids):
                centroid_map[cluster_idx] = centroid
                self.logger.info(f"Cluster {cluster_idx} centroid: {centroid}")
                
            # Validate that we have centroids for all clusters
            for cluster_idx in range(n_clusters):
                if cluster_idx not in centroid_map:
                    self.logger.error(f"Missing centroid for cluster {cluster_idx}")
                    raise ValueError(f"Missing centroid for cluster {cluster_idx}")
                self.logger.info(f"Cluster {cluster_idx} centroid: {centroid}")
                self.logger.info(f"Cluster {cluster_idx} centroid: {centroid}")
            
            # Update the "Cluster" column in the original DataFrame
            # Make sure we have the right number of formatted clusters
            if len(subset_indices) != len(formatted_clusters):
                self.logger.error(f"Mismatch: {len(subset_indices)} selected rows but {len(formatted_clusters)} cluster assignments")
                
                # Check which rows might be missing assignments
                self.logger.info(f"Row indices (len={len(subset_indices)}): {subset_indices}")
                self.logger.info(f"Formatted clusters (len={len(formatted_clusters)}): {formatted_clusters}")
                
                # Check if we're only off by one - likely the last row issue
                if len(subset_indices) == len(formatted_clusters) + 1:
                    self.logger.warning("One row may not receive a cluster assignment, possibly the last row")
                    # Clone the last cluster assignment as a fallback
                    if len(formatted_clusters) > 0:
                        # Get the index of the unassigned row (likely the last one)
                        unassigned_idx = subset_indices[-1]
                        self.logger.info(f"Row at index {unassigned_idx} may not have a cluster assignment")
                        
                        # Clone the last cluster
            df_copy.iloc[subset_indices, df_copy.columns.get_indexer(["Cluster"])] = formatted_clusters
            
            # Verify all rows received a cluster assignment
            null_clusters = df_copy.iloc[subset_indices]["Cluster"].isna().sum()
            if null_clusters > 0:
                self.logger.warning(f"{null_clusters} rows did not receive a cluster assignment!")
                problematic_indices = [idx for i, idx in enumerate(subset_indices) if pd.isna(df_copy.iloc[idx]["Cluster"])]
                self.logger.warning(f"Rows without assignments: {problematic_indices}")
            
            # Update the centroid coordinates (X, Y, Z) for each point based on its cluster
            for i, idx in enumerate(subset_indices):
                cluster_idx = int(formatted_clusters[i])
                centroid = centroid_map[cluster_idx]
                
                # Update Centroid_X/Y/Z columns with the centroid coordinates
                df_copy.at[idx, 'Centroid_X'] = centroid[0]  # Xnorm coordinate of centroid
                df_copy.at[idx, 'Centroid_Y'] = centroid[1]  # Ynorm coordinate of centroid
                df_copy.at[idx, 'Centroid_Z'] = centroid[2]  # Znorm coordinate of centroid
                
                # Validate centroid assignment
                if (pd.isna(df_copy.at[idx, 'Centroid_X']) or 
                    pd.isna(df_copy.at[idx, 'Centroid_Y']) or 
                    pd.isna(df_copy.at[idx, 'Centroid_Z'])):
                    point_id = df_copy.at[idx, 'DataID'] if 'DataID' in df_copy.columns else f"row {idx}"
                    self.logger.error(f"NaN values in centroid coordinates for {point_id} in cluster {cluster_idx}")
                    self.logger.error(f"Centroid: {centroid}, Centroid_X={df_copy.at[idx, 'Centroid_X']}, Centroid_Y={df_copy.at[idx, 'Centroid_Y']}, Centroid_Z={df_copy.at[idx, 'Centroid_Z']}")
                    raise ValueError(f"Invalid centroid values assigned to {point_id}")
            
            print("\nDebug: Updated centroid coordinates:")
            print("\nDebug: Updated centroid coordinates:")
            print(df_copy.iloc[subset_indices[:5]][['DataID', 'Cluster', 'Centroid_X', 'Centroid_Y', 'Centroid_Z']].to_string())
            print(df_copy.iloc[subset_indices][['DataID', 'Cluster']].head())
            
            # Verify centroid data integrity
            # Verify centroid data integrity
            self.logger.info("Verifying centroid data integrity in DataFrame...")
            null_centroids = df_copy.iloc[subset_indices][['Centroid_X', 'Centroid_Y', 'Centroid_Z']].isnull().any(axis=1)
            if null_centroids.any():
                problem_rows = df_copy.iloc[subset_indices][null_centroids]
                self.logger.error(f"Found {len(problem_rows)} rows with missing centroid data:")
                self.logger.error(problem_rows[['DataID', 'Cluster', 'Centroid_X', 'Centroid_Y', 'Centroid_Z']].to_string())
                raise ValueError("Missing centroid data detected after K-means clustering")
                
            self.logger.info("Centroid data integrity verified - all coordinates are valid")
            self.logger.info(f"K-means clustering applied successfully to {len(subset_data)} rows")
            
            # Save the updated DataFrame back to the manager
            self.data = df_copy
            
            if self.on_data_update:
                self.on_data_update(df_copy)
            
            return df_copy
            
        except Exception as e:
            self.logger.error(f"Error in apply_kmeans: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def test_kmeans_indexing(self):
        """Test method to verify K-means clustering indexing."""
        try:
            # Create test data
            import pandas as pd
            import numpy as np
            
            # Create sample data with known coordinates
            test_data = pd.DataFrame({
                'Xnorm': [0.1, 0.2, 0.8, 0.9, 0.15, 0.85, 0.1, 0.9, 0.2, 0.8],
                'Ynorm': [0.1, 0.2, 0.8, 0.9, 0.15, 0.85, 0.1, 0.9, 0.2, 0.8],
                'Znorm': [0.1, 0.2, 0.8, 0.9, 0.15, 0.85, 0.1, 0.9, 0.2, 0.8],
                'DataID': [f'Point_{i+1}' for i in range(10)],
                'Cluster': [None] * 10,
                'X': [1, 2, 8, 9, 1.5, 8.5, 1, 9, 2, 8],
                'Y': [1, 2, 8, 9, 1.5, 8.5, 1, 9, 2, 8],
                'Z': [1, 2, 8, 9, 1.5, 8.5, 1, 9, 2, 8],
                'Marker': ['.'] * 10,
                'Color': ['black'] * 10,
                'Sphere': [None] * 10,
                '∆E': [1.0, 1.2, 2.8, 2.9, 1.15, 2.85, 1.1, 2.9, 1.2, 2.8]  # Added ∆E column for future functionality
            })
            
            # Load the test data
            self.load_data(test_data)
            
            # Create a small test range
            test_start = 1
            test_end = 10
            test_clusters = 2
            
            print("\nRunning K-means indexing test")
            print("============================")
            print(f"Testing rows {test_start} to {test_end} with {test_clusters} clusters")
            
            # Before clustering, show the data for these rows
            subset_indices = list(self._get_row_indices(test_start, test_end))
            print("\nOriginal Data for Test Range:")
            print("============================")
            original_data = self.data.iloc[subset_indices][['DataID', 'Xnorm', 'Ynorm', 'Znorm']]
            print(original_data)
            
            # Apply clustering
            result = self.apply_kmeans(test_start, test_end, test_clusters)
            
            # Show results
            print("\nClustering Results:")
            print("==================")
            cluster_results = result.iloc[subset_indices][['DataID', 'Cluster', 'Xnorm', 'Ynorm', 'Znorm']]
            print(cluster_results)
            
            return True
            
        except Exception as e:
            print(f"Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def validate_row_range(self, start_row: int, end_row: int) -> Tuple[int, int]:
        """Validate that the row range is within bounds."""
        if self.data is None:
            self.logger.error("No data loaded. Call load_data() first.")
            raise ValueError("No data loaded. Call load_data() first.")
        
        # Find last non-empty row by checking each numeric column
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns
        last_valid_rows = []
        for col in numeric_cols:
            valid_indices = self.data[col].notna().values.nonzero()[0]
            if len(valid_indices) > 0:
                last_valid_rows.append(valid_indices[-1])
        
        if not last_valid_rows:
            raise ValueError("No numeric data found in the file")
        
        last_valid_row = max(last_valid_rows) + 1  # Add 1 for 1-based indexing
        
        # Validate start_row - row 2 is the first valid data row (after header)
        min_valid_row = 2  # First row is header, so data starts at row 2
        if start_row < min_valid_row:
            self.logger.warning(f"Invalid start_row {start_row}, adjusting to minimum value {min_valid_row}")
            start_row = min_valid_row
        
        # Validate end_row
        max_row = min(999, last_valid_row)
        if end_row > max_row:
            self.logger.warning(f"Invalid end_row {end_row}, adjusting to last non-empty row {max_row}")
            end_row = max_row
        
        # Ensure start_row <= end_row
        if start_row > end_row:
            self.logger.error(f"Start row {start_row} is greater than end row {end_row}")
            raise ValueError("Start row must be less than or equal to end row")
        
        self.logger.info(f"Validated row range: {start_row} to {end_row}")
        return start_row, end_row
    
    def _get_row_indices(self, start: int, end: int) -> range:
        """Get the correct row indices for the given range, including the end row.
        
        Args:
            start: 1-based start row number (where 2 is the first data row)
            end: 1-based end row number
        Returns:
            range object with 0-based indices including end row
        """
        # Validate and get proper bounds
        start, end = self.validate_row_range(start, end)
        
        # Convert to 0-based indexing
        # Convert from 1-based (user visible) to 0-based (internal) indexing
        # Convert from 1-based (user visible) to 0-based (internal) indexing
        # The rows in the UI are 1-based but Python uses 0-based indexing
        # First 6 rows are purposely blank for sequential indexing
        # Actual data starts at row 8, which should map to index 6 in the data array
        zero_based_start = start - 2  # Preserves the existing behavior
        # (range is exclusive at the upper bound, so add 1 to make it inclusive)
        # (range is exclusive at the upper bound, so add 1 to make it inclusive)
        zero_based_end = end - 2 + 1  # +1 to make the range inclusive of the end row
        
        # Force special handling for the last row if it's being requested
        if self.data is not None and end >= len(self.data):
            # This is explicitly requesting the last row
            last_idx = len(self.data) - 1
            if zero_based_end <= last_idx + 1:  # Check if our calculation would include the last row
                self.logger.warning(f"Last row requested but might be excluded with calculated range end {zero_based_end-1}")
                zero_based_end = last_idx + 1
                self.logger.info(f"Forced inclusion of last row by setting range end to {zero_based_end}")
        
        # Log detailed conversion for debugging
        self.logger.info(f"Row conversion details: UI row {end} → zero-based index {end-2} → range end {zero_based_end}")
        # Explicitly log the conversion calculation for clarity
        self.logger.info(f"Row conversion: UI row {end} → zero_based_end index {zero_based_end-1} (inclusive) → range upper bound {zero_based_end} (exclusive)")
        self.logger.info(f"Row conversion: UI row {end} → zero_based_end index {zero_based_end-1} (inclusive) → range upper bound {zero_based_end} (exclusive)")
        
        # Calculate actual data bounds to ensure we're not out of range
        if self.data is not None:
            max_row_index = len(self.data) - 1
            # Log the maximum available row index
            self.logger.info(f"DataFrame has {len(self.data)} rows, max index is {max_row_index}")
            
            # Check if the last row is being requested
            is_last_row_requested = (end >= len(self.data) + 1)
            if is_last_row_requested:
                self.logger.info(f"Last row requested (UI row {end}, index {max_row_index})")
                self.logger.info(f"Last row requested (UI row {end}, index {max_row_index})")
                
            # Always verify the zero_based_end value to ensure it includes the last row when requested
            if end >= len(self.data):  # If requesting last row or beyond
                # We need to ensure the last row's index is included
                if (zero_based_end - 1) < max_row_index:
                    self.logger.warning(f"Current index {zero_based_end-1} would exclude the last row {max_row_index}")
                    zero_based_end = max_row_index + 1  # Force inclusion of last row
                    self.logger.info(f"Adjusted end index to {zero_based_end-1} (inclusive) to include the last row")
                else:
                    self.logger.info(f"Last row {max_row_index} is already included in the range {zero_based_start}-{zero_based_end-1}")
            if zero_based_end > max_row_index + 1:  # +1 because range is exclusive at upper bound
                self.logger.warning(f"End index {zero_based_end} exceeds data bounds, adjusting to {max_row_index + 1}")
                zero_based_end = max_row_index + 1  # +1 to ensure it's included in range
                
            # Special check to ensure the last row is included when requested
            if is_last_row_requested and zero_based_end <= max_row_index:
                self.logger.warning(f"Last row might be excluded, adjusting end index to include it")
                zero_based_end = max_row_index + 1
                
            # Additional logging to verify the correct mapping for row 2 (first data row)
            if start == 2:
                self.logger.info(f"Row 2 (first data row) maps to index {zero_based_start} (should be 0)")
                
            # Check for blank rows in the range
            if 'valid_data' in self.data.columns:
                valid_rows = self.data.iloc[range(zero_based_start, zero_based_end)]['valid_data'].sum()
                total_rows = zero_based_end - zero_based_start
                if valid_rows < total_rows:
                    self.logger.warning(f"Selected range contains {total_rows - valid_rows} invalid data rows")
                    self.logger.info(f"Will filter these out during K-means processing")
        
        # Log the conversion for debugging
        self.logger.info(f"Converting rows {start}-{end} to indices {zero_based_start}-{zero_based_end-1} (inclusive)")
        # Verify the indices match exactly the user's selection (adjusted for 0-based indexing)
        self.logger.info(f"Selected row {start} corresponds to index {zero_based_start}")
        self.logger.info(f"Selected row {end} corresponds to index {zero_based_end-1}")
        
        # Validate that the row range is not empty
        if zero_based_start >= zero_based_end:
            self.logger.warning(f"Empty row range detected: {zero_based_start}-{zero_based_end}")
            # Ensure at least one row is included to prevent empty ranges
            zero_based_end = zero_based_start + 1
            self.logger.info(f"Adjusted to non-empty range: {zero_based_start}-{zero_based_end-1}")
        
        # Final validation check on the range
        if zero_based_start < 0:
            self.logger.warning(f"Negative start index {zero_based_start}, adjusting to 0")
            zero_based_start = 0
            
        # Log the final range being returned
        indices_list = list(range(zero_based_start, zero_based_end))
        self.logger.info(f"Returning row indices range: {zero_based_start}-{zero_based_end-1} (inclusive)")
        
        # Log the first and last indices for clarity
        if indices_list:
            self.logger.info(f"First index: {indices_list[0]}, Last index: {indices_list[-1]}, Total indices: {len(indices_list)}")
            
            # Extra verification for last row inclusion
            if self.data is not None:
                max_idx = len(self.data) - 1
                if indices_list[-1] == max_idx:
                    self.logger.info("✅ Last row of data is included in the selection")
                elif end >= len(self.data):  # Simplified condition for requesting last row
                    self.logger.warning("❌ Last row of data should be included but isn't!")
                    # Force inclusion of the last row as a fallback measure
                    if max_idx not in indices_list:  # Only add if not already there
                        indices_list.append(max_idx)
                        self.logger.info(f"Forcing inclusion of last row {max_idx} as fallback measure")
                        # Update the range to include the newly added last row
                        zero_based_end = max_idx + 1
                        
                        # Create a new range that includes the last row
                        final_range = range(zero_based_start, zero_based_end) 
                        # Log the final indices after correction
                        self.logger.info(f"Final indices after correction: {list(final_range)}")
                        # Return the corrected range instead
                        return final_range
        else:
            self.logger.warning("No indices selected - empty range")
            
        return range(zero_based_start, zero_based_end)
    
    def _apply_kmeans_gui(self):
        """Handle Apply button click for K-means clustering"""
        try:
            # Get values from GUI with proper validation
            self.logger.info("Retrieving values from GUI inputs")
            
            # Validate start row
            try:
                start_value = self.start_row.get().strip()
                self.logger.debug(f"Retrieved start row value: '{start_value}'")
                
                if not start_value:
                    self.logger.error("Start row value is empty")
                    messagebox.showerror("Input Error", "Start row cannot be empty.")
                    return
                    
                start = int(start_value)
                if start < 2:
                    self.logger.warning(f"Start row {start} is less than minimum (2), adjusting")
                    start = 2
                    self.start_row.delete(0, tk.END)
                    self.start_row.insert(0, str(start))
            except ValueError as e:
                self.logger.error(f"Invalid start row value: {e}")
                messagebox.showerror("Input Error", f"Start row must be a valid number.\nError: {str(e)}")
                return
            
            # Validate end row
            try:
                end_value = self.end_row.get().strip()
                self.logger.debug(f"Retrieved end row value: '{end_value}'")
                
                if not end_value:
                    self.logger.error("End row value is empty")
                    messagebox.showerror("Input Error", "End row cannot be empty.")
                    return
                    
                end = int(end_value)
                if end < start:
                    self.logger.warning(f"End row {end} is less than start row {start}, adjusting")
                    end = start
                    self.end_row.delete(0, tk.END)
                    self.end_row.insert(0, str(end))
            except ValueError as e:
                self.logger.error(f"Invalid end row value: {e}")
                messagebox.showerror("Input Error", f"End row must be a valid number.\nError: {str(e)}")
                return
            
            # Validate cluster count
            try:
                cluster_value = self.cluster_count.get().strip()
                self.logger.debug(f"Retrieved cluster count value: '{cluster_value}'")
                
                if not cluster_value:
                    self.logger.error("Cluster count value is empty")
                    messagebox.showerror("Input Error", "Number of clusters cannot be empty.")
                    return
                    
                n_clusters = int(cluster_value)
                if n_clusters < 2:
                    self.logger.warning(f"Cluster count {n_clusters} is less than minimum (2), adjusting")
                    n_clusters = 2
                    self.cluster_count.delete(0, tk.END)
                    self.cluster_count.insert(0, str(n_clusters))
            except ValueError as e:
                self.logger.error(f"Invalid cluster count value: {e}")
                messagebox.showerror("Input Error", f"Number of clusters must be a valid number.\nError: {str(e)}")
                return
            
            # Log the validated values
            self.logger.info(f"Applying K-means: start={start}, end={end}, clusters={n_clusters}")
            
            # Apply K-means clustering
            result = self.apply_kmeans(start, end, n_clusters)
            
            if result is not None:
                # Update the display if we have a callback
                if self.on_data_update:
                    self.on_data_update(result)
                
                # Show success message with cluster info
                clusters = result.iloc[self._get_row_indices(start, end)]['Cluster']
                valid_clusters = clusters[clusters.notna()]
                cluster_counts = valid_clusters.value_counts().to_dict()
                cluster_info = "\n".join(f"Cluster {k}: {v} points" for k, v in sorted(cluster_counts.items()))
                
                msg = (f"K-means clustering complete!\n\n"
                      f"Points assigned to clusters for rows {start}-{end}:\n\n"
                      f"{cluster_info}\n\n"
                      "You can now save these assignments using the Save button.")
                
                messagebox.showinfo("K-means Complete", msg)
                
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            self.logger.error(f"Error in _apply_kmeans_gui: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def set_file_path(self, file_path: str):
        """Set the current file path."""
        if not file_path:
            self.logger.error("Attempted to set empty file path")
            raise ValueError("File path cannot be empty")
            
        if not os.path.isfile(file_path):
            self.logger.error(f"File does not exist: {file_path}")
            raise ValueError(f"File does not exist: {file_path}")
            
        self.file_path = os.path.abspath(file_path)
        self.logger.info(f"Set current file path to: {self.file_path}")
        self.logger.info(f"File exists and is accessible: {os.access(self.file_path, os.R_OK | os.W_OK)}")
    
    def _verify_file_access(self) -> bool:
        """Verify that the current file is accessible for read/write operations."""
        try:
            if not self.file_path:
                self.logger.error("No file path set")
                return False
                
            abs_path = os.path.abspath(self.file_path)
            
            # Check if file exists
            if not os.path.isfile(abs_path):
                self.logger.error(f"File does not exist: {abs_path}")
                return False
                
            # Check read/write permissions
            if not os.access(abs_path, os.R_OK | os.W_OK):
                self.logger.error(f"Insufficient permissions for file: {abs_path}")
                return False
                
            self.logger.info(f"File verified: {abs_path}")
            self.logger.info(f"Working directory: {os.getcwd()}")
            
            # Try to open the file to verify access
            # Try to open the file to verify access
            pd.read_excel(abs_path, engine='odf')
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying file access: {str(e)}")
            return False
    
    def save_cluster_assignments(self):
        """
        Save cluster assignments to the current open .ods file with proper file locking.
        
        This function implements file locking to prevent conflicts when multiple
        processes try to access the same file. It also performs thorough error
        checking and provides detailed user feedback.
        """
        lockfile = None
        try:
            if self.file_path is None:
                raise ValueError("No file path set")
                
            # Check if file exists and is accessible
            if not os.path.exists(self.file_path):
                raise IOError(f"File not found: {self.file_path}")
                
            if not os.access(self.file_path, os.W_OK):
                raise IOError(f"File {self.file_path} is not writable")
                
            # Get the current row selection and validate
            start = int(self.start_row.get())
            end = int(self.end_row.get())
            start, end = self.validate_row_range(start, end)
            
            # Verify file is .ods format
            if not self.file_path.endswith('.ods'):
                raise ValueError("Only .ods files are supported for saving cluster assignments")
            
            # Inform user of the process
            msg = (f"Saving cluster assignments for rows {start}-{end}:\n\n"
                  "1. Your original .ods file will be updated directly\n"
                  "2. Only the Cluster column will be modified\n\n"
                  "Continue?")
            
            if not messagebox.askokcancel("Save Clusters", msg):
                return
                
            # Create and acquire lock file to prevent concurrent access
            lock_path = f"{self.file_path}.lock"
            self.logger.info(f"Attempting to acquire lock: {lock_path}")
            
            # Try to acquire the lock with timeout
            max_attempts = 3
            attempt = 0
            lock_acquired = False
            
            while attempt < max_attempts and not lock_acquired:
                try:
                    # Create lock file if it doesn't exist
                    lockfile = open(lock_path, 'w+')
                    
                    # Try to acquire an exclusive lock (non-blocking)
                    fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lock_acquired = True
                    self.logger.info("Lock acquired successfully")
                    
                except IOError as e:
                    if e.errno == errno.EACCES or e.errno == errno.EAGAIN:
                        # File is locked by another process
                        attempt += 1
                        self.logger.warning(f"File is locked, attempt {attempt}/{max_attempts}")
                        
                        if attempt < max_attempts:
                            # Ask user if they want to retry
                            if not messagebox.askretrycancel("File Locked", 
                                f"The file appears to be in use by another program.\n\n"
                                f"Attempt {attempt} of {max_attempts}.\n\n"
                                "Would you like to try again?"):
                                if lockfile:
                                    lockfile.close()
                                return
                            time.sleep(1)  # Wait before trying again
                        else:
                            if lockfile:
                                lockfile.close()
                            messagebox.showerror("File Locked", 
                                "The file is locked by another program and cannot be accessed.\n\n"
                                "Please close any applications that might be using this file and try again.")
                            return
                    else:
                        # Other IO error
                        if lockfile:
                            lockfile.close()
                        raise
            
            if not lock_acquired:
                if lockfile:
                    lockfile.close()
                messagebox.showerror("File Locked", 
                    "Could not acquire file lock after multiple attempts.\n\n"
                    "Please close any applications that might be using this file and try again.")
                return
                
            try:
                # Get the exact rows we're working with
                row_indices = self._get_row_indices(start, end)
                
                # Get cluster assignments for our selected range
                clusters = self.data.iloc[row_indices]['Cluster']
                valid_clusters = clusters[clusters.notna()]
                
                if not valid_clusters.empty:
                    try:
                        # First verify we can access the file
                        if not os.access(self.file_path, os.W_OK):
                            raise IOError(f"File {self.file_path} is not writable")
                        
                        # Create backup of original file
                        backup_path = f"{self.file_path}.bak"
                        self.logger.info(f"Creating backup at: {backup_path}")
                        import shutil
                        shutil.copy2(self.file_path, backup_path)
                        
                        # Get column structure
                        self.logger.info("Reading file structure")
                        df = pd.read_excel(self.file_path, engine='odf')
                        
                        # Verify required columns exist
                        required_columns = ['Cluster', 'Centroid_X', 'Centroid_Y', 'Centroid_Z']
                        missing_columns = [col for col in required_columns if col not in df.columns]
                        if missing_columns:
                            raise ValueError(f"Required columns missing from spreadsheet: {missing_columns}")
                            
                        # Get column indices
                        cluster_col_idx = df.columns.get_loc('Cluster')
                        centroid_x_col_idx = df.columns.get_loc('Centroid_X')
                        centroid_y_col_idx = df.columns.get_loc('Centroid_Y')
                        centroid_z_col_idx = df.columns.get_loc('Centroid_Z')
                        
                        self.logger.info(f"Found required columns - Cluster: {cluster_col_idx}, Centroid_X: {centroid_x_col_idx}, Centroid_Y: {centroid_y_col_idx}, Centroid_Z: {centroid_z_col_idx}")
                        # Store centroid column indices
                        centroid_col_indices = {
                            'Centroid_X': centroid_x_col_idx,
                            'Centroid_Y': centroid_y_col_idx,
                            'Centroid_Z': centroid_z_col_idx
                        }
                        
                        # Define fixed rows for storing centroids
                        # Row 2 (index 1) for Cluster 0, Row 3 (index 2) for Cluster 1, etc.
                        centroid_row_mapping = {}
                        unique_clusters = sorted(self.data['Cluster'].dropna().unique())
                        for i, cluster_id in enumerate(unique_clusters):
                            # Add 2 to start at row 2 (first data row)
                            # We want:
                            # - Cluster 0 to be at sheet row 2 (first data row)
                            # - Cluster 1 to be at sheet row 3 
                            # - and so on
                            # Map cluster_id directly to final sheet row number
                            # No additional offset needed later
                            centroid_row_mapping[int(cluster_id)] = i + 1  # Map cluster 0 to row 1, cluster 1 to row 2
                            self.logger.debug(f"Mapping cluster {cluster_id} directly to sheet row {i + 2}")
                            self.logger.info(f"Cluster {cluster_id} will be stored at sheet row {i + 2}")
                        self.logger.info(f"Centroid row mapping: {centroid_row_mapping}")
                        # Calculate centroids for each cluster
                        cluster_centroids = {}
                        for cluster_num in self.data['Cluster'].dropna().unique():
                            cluster_mask = self.data['Cluster'] == cluster_num
                            centroid = [
                                self.data.loc[cluster_mask, 'Xnorm'].mean(),
                                self.data.loc[cluster_mask, 'Ynorm'].mean(),
                                self.data.loc[cluster_mask, 'Znorm'].mean()
                            ]
                            cluster_centroids[int(cluster_num)] = centroid
                            self.logger.info(f"Calculated centroid for cluster {int(cluster_num)}: {centroid}")
                            self.logger.info(f"Calculated centroid for cluster {int(cluster_num)}: {centroid}")
                        data_point_updates = []
                        for i, idx in enumerate(row_indices):
                            sheet_row_idx = idx + 1
                            cluster_value = clusters.iloc[i]
                            if pd.notna(cluster_value):
                                cluster_int = int(cluster_value)
                                data_point_updates.append({
                                    'row': sheet_row_idx,
                                    'cluster': cluster_int
                                })
                        
                        # Prepare updates for centroid rows (fixed rows for each cluster)
                        centroid_updates = []
                        for cluster_num, centroid in cluster_centroids.items():
                            # Get the fixed row for this cluster
                            fixed_row = centroid_row_mapping.get(cluster_num)
                            # No conversion needed as mapping already contains the correct sheet row
                            sheet_row_idx = fixed_row
                            self.logger.debug(f"Using fixed_row {fixed_row} directly as sheet_row_idx (no additional offset needed)")
                            centroid_updates.append({
                                    'row': sheet_row_idx,
                                    'cluster': cluster_num,
                                    'centroid': centroid
                                })
                            self.logger.info(f"Will store cluster {cluster_num} centroid at row {sheet_row_idx} (direct mapping: cluster {cluster_num} -> sheet row {sheet_row_idx})")
                        if data_point_updates or centroid_updates:
                            self.logger.info(f"Preparing to update {len(data_point_updates)} data points and {len(centroid_updates)} centroid rows")
                            # Helper method to verify the save
                            def _verify_centroid_data(verify_doc, rows_to_verify):
                                verify_sheet = verify_doc.sheets[0]
                                verification_count = min(5, len(rows_to_verify))
                                self.logger.info(f"Verifying {verification_count} sample updates")
                                
                                for update in rows_to_verify[:verification_count]:
                                    # Use cluster value to determine the correct row for verification
                                    cluster_value = update['cluster']
                                    row_idx = int(cluster_value) + 1  # Map cluster 0 to row 1, cluster 1 to row 2, etc.
                                    centroid = update['centroid']
                                    self.logger.debug(f"Verifying centroid for cluster {cluster_value} at row {row_idx}")
                          
                                    # Verify cluster value
                                    cluster_cell = verify_sheet[row_idx, cluster_col_idx]
                                    if cluster_cell.value != cluster_value:
                                        self.logger.error(f"Cluster value mismatch at row {row_idx}: expected {cluster_value}, got {cluster_cell.value}")
                                        raise ValueError(f"Cluster save verification failed at row {row_idx}")
                                    
                                    # Verify centroid coordinates
                                    if centroid is not None:
                                        # Verify all centroid columns
                                        centroid_x_cell = verify_sheet[row_idx, centroid_col_indices['Centroid_X']]
                                        centroid_y_cell = verify_sheet[row_idx, centroid_col_indices['Centroid_Y']]
                                        centroid_z_cell = verify_sheet[row_idx, centroid_col_indices['Centroid_Z']]
                                        
                                        # Allow for minor floating point differences in verification
                                        tolerance = 0.0001  # Tolerance for floating point comparisons
                                        x_diff = abs(float(centroid_x_cell.value) - centroid[0])
                                        y_diff = abs(float(centroid_y_cell.value) - centroid[1])
                                        z_diff = abs(float(centroid_z_cell.value) - centroid[2])
                                        
                                        if x_diff > tolerance or y_diff > tolerance or z_diff > tolerance:
                                            self.logger.error(f"Centroid coordinate mismatch at row {row_idx}:")
                                            self.logger.error(f"Expected: [{centroid[0]:.6f}, {centroid[1]:.6f}, {centroid[2]:.6f}]")
                                            self.logger.error(f"Got: [{float(centroid_x_cell.value):.6f}, {float(centroid_y_cell.value):.6f}, {float(centroid_z_cell.value):.6f}]")
                                            self.logger.error(f"Diff: [{x_diff:.6f}, {y_diff:.6f}, {z_diff:.6f}]")
                                            raise ValueError(f"Centroid save verification failed at row {row_idx}")
                                
                                # Log verification results
                                centroid_cols = ", ".join([f"{col}:{idx}" for col, idx in centroid_col_indices.items()])
                                self.logger.info(f"Centroid columns successfully verified: {centroid_cols}")
                                
                            try:
                                # Open and update
                                ods_doc = ezodf.opendoc(self.file_path)
                                sheet = ods_doc.sheets[0]
                                # First, clear existing centroid data in the fixed rows
                                for row_idx in range(2, len(centroid_row_mapping) + 1):  # Changed upper bound calculation
                                    for col_name, col_idx in centroid_col_indices.items():
                                        try:
                                            cell = sheet[row_idx, col_idx]
                                            if cell is not None:
                                                cell.set_value("")
                                        except Exception:
                                            pass
                                
                                # Apply updates to data points (cluster assignments only)
                                for update in data_point_updates:
                                    try:
                                        row_idx = update['row']
                                        cluster_value = update['cluster']
                                        cluster_cell = sheet[row_idx, cluster_col_idx]
                                        cluster_cell.set_value(cluster_value)
                                        self.logger.debug(f"Updated row {row_idx} with cluster {cluster_value}")
                                    except Exception as e:
                                        self.logger.warning(f"Failed to update cluster at row {row_idx}: {str(e)}")
                                
                                # Apply updates to centroid rows
                                for update in centroid_updates:
                                    try:
                                        row_idx = update['row']
                                        cluster_value = update['cluster']
                                        centroid = update['centroid']
                                        
                                        # Update cluster value
                                        cluster_cell = sheet[row_idx, cluster_col_idx]
                                        cluster_cell.set_value(cluster_value)
                                        
                                        # Update centroid coordinates

                                        sheet[row_idx, centroid_col_indices['Centroid_X']].set_value(format(centroid[0], '.4f'))
                                        sheet[row_idx, centroid_col_indices['Centroid_Y']].set_value(format(centroid[1], '.4f'))
                                        sheet[row_idx, centroid_col_indices['Centroid_Z']].set_value(format(centroid[2], '.4f'))
                                        
                                        self.logger.info(f"Updated centroid for cluster {cluster_value} at row {row_idx} with values: {centroid}")
                                    except Exception as e:
                                        self.logger.error(f"Failed to update centroid at row {row_idx}: {str(e)}")
                                        raise
                                
                                # Define temp_path at the start of the operation
                                temp_path = f"{self.file_path}.new"
                                self.logger.info(f"Saving to temporary file: {temp_path}")
                                
                                try:
                                    # Save to temporary file first
                                    ods_doc.saveas(temp_path)
                                    
                                    # Close original document before verification
                                    del ods_doc
                                    
                                    # Verify the save
                                    verify_doc = ezodf.opendoc(temp_path)
                                    _verify_centroid_data(verify_doc, centroid_updates)
                                    del verify_doc
                                    
                                    # If verification passed, replace original with new file
                                    os.replace(temp_path, self.file_path)
                                    
                                    self.logger.info("File saved and verified successfully")
                                    
                                except Exception as e:
                                    self.logger.error(f"Error during file operations: {str(e)}")
                                    raise IOError(f"Failed to complete file operations: {str(e)}")
                                    
                                finally:
                                    # Clean up temporary file regardless of success/failure
                                    try:
                                        if os.path.exists(temp_path):
                                            os.remove(temp_path)
                                    except Exception as cleanup_error:
                                        self.logger.warning(f"Could not clean up temporary file: {str(cleanup_error)}")
                            except Exception as e:
                                self.logger.error(f"Error updating spreadsheet: {str(e)}")
                                raise
                    finally:
                        # Clean up backup file if it exists
                        try:
                            if os.path.exists(backup_path):
                                os.remove(backup_path)
                        except Exception:
                            self.logger.warning(f"Could not remove backup file: {backup_path}")
                            pass
                        
                        # Clean up document objects
                        for doc_name in ['ods_doc', 'verify_doc']:
                            try:
                                if doc_name in locals():
                                    del locals()[doc_name]
                            except Exception:
                                pass
                    
                    # Count how many clusters we saved
                    cluster_counts = valid_clusters.value_counts().to_dict()
                    cluster_info = "\n".join(f"Cluster {k}: {v} points" for k, v in sorted(cluster_counts.items()))
                    # Remove duplicate line
                    
                    # Success message
                    success_msg = (
                        f"Clusters and centroid coordinates saved for rows {start}-{end}!\n\n"
                        f"Cluster summary:\n{cluster_info}\n\n"
                        f"Original .ods file has been updated with:\n"
                        f"- Cluster assignments\n"
                        f"- Centroid_X, Centroid_Y, Centroid_Z coordinates\n\n"
                        f"NEXT STEP: You can now calculate ΔE values by clicking the 'Calculate' button in the ΔE CIE2000 panel."
                    )
                    
                    messagebox.showinfo("Clusters Saved", success_msg)
                    
                    # Update the in-memory data to match the saved version
                    self.data.iloc[row_indices, self.data.columns.get_loc('Cluster')] = clusters.values
                else:
                    messagebox.showwarning("Warning", 
                        f"No cluster assignments found for rows {start}-{end}")
            
            finally:
                # Always release the lock, even if an error occurred
                if lockfile:
                    self.logger.info("Releasing file lock")
                    fcntl.flock(lockfile, fcntl.LOCK_UN)
                    lockfile.close()
                    try:
                        os.remove(lock_path)
                        self.logger.info("Lock file removed")
                    except Exception as e:
                        self.logger.warning(f"Could not remove lock file: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", 
                "Failed to save cluster assignments.\n\n"
                "Please check file permissions and make sure the file isn't open in another program.")
            raise
