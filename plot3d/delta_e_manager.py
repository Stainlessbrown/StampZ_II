import os
import logging
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import messagebox
import time
import fcntl
import errno
import ezodf
import math
from typing import Optional, Dict, List, Tuple, Any, Union


class DeltaEManager:
    """
    Manager class for calculating ΔE CIE2000 color differences between normalized points
    and their cluster centroids.
    """
    
    # Define expected column structure
    EXPECTED_COLUMNS = ['Xnorm', 'Ynorm', 'Znorm', 'DataID', 'Cluster', '∆E', 'Marker',
                     'Color', 'Sphere', 'Centroid_X', 'Centroid_Y', 'Centroid_Z']
    
    # Reference white point for XYZ to L*a*b* conversion
    # For normalized values in 0-1 range, use these reference values
    REF_WHITE_X = 1.0
    REF_WHITE_Y = 1.0
    REF_WHITE_Z = 1.0
    

    def __init__(self, on_data_update=None, logger=None):
        """Initialize the manager."""
        # Set up logging
        if logger is None:
            # Create our own logger
            self.logger = logging.getLogger("DeltaEManager")
            # Avoid duplicate handlers
            if not self.logger.handlers:
                # Create log formatter
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler = logging.StreamHandler()
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
        self.apply_button = None
        self.save_button = None
        self.parent = None  # Store the parent widget
        
        self.logger.info("DeltaEManager initialized successfully")
    
    def load_data(self, dataframe: pd.DataFrame) -> None:
        """Load data into the manager."""
        if dataframe is None:
            self.logger.warning("Received None DataFrame")
            self.data = None
            return
            
        # Log all columns found in the dataframe for debugging
        self.logger.info(f"DataFrame contains columns: {sorted(dataframe.columns.tolist())}")
        
        # Create case-insensitive column mapping
        column_map = {}
        for col in dataframe.columns:
            column_map[col.lower()] = col
            
        self.logger.info(f"Case-insensitive column map created with {len(column_map)} entries")
        
        # Check for required columns with case-insensitive matching
        missing_columns = []
        renamed_columns = {}
        
        for expected_col in self.EXPECTED_COLUMNS:
            if expected_col in dataframe.columns:
                # Column exists with exact name
                continue
            elif expected_col.lower() in column_map:
                # Column exists with different case
                actual_col = column_map[expected_col.lower()]
                renamed_columns[actual_col] = expected_col
                self.logger.info(f"Found column '{actual_col}' matching expected '{expected_col}'")
            else:
                # Column is missing
                missing_columns.append(expected_col)
        
        # Handle missing columns with better error messages
        if missing_columns:
            # Provide more specific error information for critical columns
            critical_cols = ['Centroid_X', 'Centroid_Y', 'Centroid_Z', 'Cluster']
            critical_missing = [col for col in missing_columns if col in critical_cols]
            
            error_msg = f"DataFrame is missing required columns: {missing_columns}"
            
            if any(col in critical_missing for col in ['Centroid_X', 'Centroid_Y', 'Centroid_Z']):
                error_msg += "\n\nCentroid columns are required for ΔE calculation."
                error_msg += "\nPlease run K-means clustering first and save the results."
                
            if 'Cluster' in critical_missing:
                error_msg += "\n\nCluster column is missing. Please run K-means clustering first."
                
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Copy the dataframe and rename columns if needed
        dataframe_copy = dataframe.copy()
        
        if renamed_columns:
            self.logger.info(f"Renaming {len(renamed_columns)} columns to expected names")
            dataframe_copy.rename(columns=renamed_columns, inplace=True)
        
        # Check for centroid data in the dataframe
        centroid_cols = ['Centroid_X', 'Centroid_Y', 'Centroid_Z']
        if all(col in dataframe_copy.columns for col in centroid_cols):
            # Count rows with valid centroid data
            valid_centroid_mask = (
                dataframe_copy['Centroid_X'].notna() & 
                dataframe_copy['Centroid_Y'].notna() & 
                dataframe_copy['Centroid_Z'].notna()
            )
            valid_centroid_count = valid_centroid_mask.sum()
            
            self.logger.info(f"Found {valid_centroid_count} rows with valid centroid data")
            
            # Sample a few centroid values for debugging
            if valid_centroid_count > 0:
                sample_rows = dataframe_copy[valid_centroid_mask].head(3)
                for _, row in sample_rows.iterrows():
                    self.logger.info(f"Sample centroid data - Cluster: {row.get('Cluster', 'N/A')}, "
                                    f"Centroid: ({row['Centroid_X']:.4f}, {row['Centroid_Y']:.4f}, {row['Centroid_Z']:.4f})")
            else:
                self.logger.warning("No valid centroid data found in the dataframe")
        
        self.data = dataframe_copy
        self.logger.info(f"Loaded DataFrame with {len(dataframe_copy)} rows")
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
        
        # Convert from 1-based (user visible) to 0-based (internal) indexing
        # Row 2 in the UI (first data row) should map to index 0 in the data array
        zero_based_start = start - 2  # Row 2 maps to index 0
        # For end, we need to convert to the proper 0-based index
        zero_based_end = end - 1  # end is inclusive in the UI, but we need to convert to 0-based
        
        # Calculate actual data bounds to ensure we're not out of range
        if self.data is not None:
            max_row_index = len(self.data) - 1
            if zero_based_end > max_row_index:
                self.logger.warning(f"End index {zero_based_end} exceeds data bounds, adjusting to {max_row_index}")
                zero_based_end = max_row_index
                
            # Additional logging to verify the correct mapping for row 2 (first data row)
            if start == 2:
                self.logger.info(f"Row 2 (first data row) maps to index {zero_based_start} (should be 0)")
        
        # Log the conversion for debugging
        self.logger.info(f"Converting rows {start}-{end} to indices {zero_based_start}-{zero_based_end} (inclusive)")
        
        # Validate that the row range is not empty
        if zero_based_start > zero_based_end:
            self.logger.warning(f"Empty row range detected: {zero_based_start}-{zero_based_end}")
            # Ensure at least one row is included to prevent empty ranges
            zero_based_end = zero_based_start
        
        # Create a list of indices from start to end (inclusive)
        return range(zero_based_start, zero_based_end + 1)
    
    def xyz_to_lab(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Convert XYZ color values to L*a*b* color space.
        
        Args:
            x, y, z: Values in XYZ color space (0.0-1.0 normalized)
            
        Returns:
            Tuple of (L*, a*, b*) values
        """
        # Validate input values and clip to 0-1 range
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        z = max(0.0, min(1.0, z))
        
        # Scale XYZ values relative to reference white
        # For normalized values, we're using reference white of (1.0, 1.0, 1.0)
        # This is appropriate for normalized 0-1 range data
        x = x / self.REF_WHITE_X
        y = y / self.REF_WHITE_Y
        z = z / self.REF_WHITE_Z
        
        # Apply nonlinear transformation
        def transform(t):
            # Using standard constants from CIE Lab definition
            epsilon = 0.008856  # Intent is 216/24389
            kappa = 903.3  # Intent is 24389/27
            
            if t > epsilon:
                return t**(1/3)
            else:
                return (kappa * t + 16) / 116
        
        x = transform(x)
        y = transform(y)
        z = transform(z)
        
        # Calculate L*a*b* values
        L = 116 * y - 16
        a = 500 * (x - y)
        b = 200 * (y - z)
        
        # Validate output values to ensure they're in reasonable ranges
        # L* should be in range [0, 100]
        L = max(0.0, min(100.0, L))
        # a* and b* are typically in range [-128, 127] but can vary
        
        return L, a, b
    
    def calculate_delta_e_2000(self, lab1: Tuple[float, float, float], 
                              lab2: Tuple[float, float, float]) -> float:
        """
        Calculate ΔE CIE2000 color difference between two L*a*b* colors.
        
        Args:
            lab1: First L*a*b* color as (L*, a*, b*)
            lab2: Second L*a*b* color as (L*, a*, b*)
            
        Returns:
            Delta E CIE2000 value
        """
        # Unpack L*a*b* values
        L1, a1, b1 = lab1
        L2, a2, b2 = lab2
        
        # Set weighting factors
        kL = 1.0
        kC = 1.0
        kH = 1.0
        
        # Calculate Cab
        C1 = math.sqrt(a1**2 + b1**2)
        C2 = math.sqrt(a2**2 + b2**2)
        Cab = (C1 + C2) / 2
        
        # Calculate G (factor for a* correction)
        G = 0.5 * (1 - math.sqrt(Cab**7 / (Cab**7 + 25**7)))
        
        # Calculate a' (corrected a*)
        a1p = (1 + G) * a1
        a2p = (1 + G) * a2
        
        # Calculate C' (corrected C*)
        C1p = math.sqrt(a1p**2 + b1**2)
        C2p = math.sqrt(a2p**2 + b2**2)
        
        # Calculate h' (corrected hue angle)
        def calculate_h_prime(ap, b):
            if ap == 0 and b == 0:
                return 0
            h = math.degrees(math.atan2(b, ap))
            return h + 360 if h < 0 else h
        
        h1p = calculate_h_prime(a1p, b1)
        h2p = calculate_h_prime(a2p, b2)
        
        # Calculate ΔL', ΔC', ΔH'
        deltaLp = L2 - L1
        deltaCp = C2p - C1p
        
        # Calculate ΔH'
        deltahp = h2p - h1p
        if C1p * C2p == 0:
            deltaHp = 0
        elif abs(deltahp) <= 180:
            deltaHp = deltahp
        elif deltahp > 180:
            deltaHp = deltahp - 360
        else:
            deltaHp = deltahp + 360
            
        deltaHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(deltaHp / 2))
        
        # Calculate mean values for L', C', and h'
        Lp = (L1 + L2) / 2
        Cp = (C1p + C2p) / 2
        
        # Calculate mean hue h'
        if C1p * C2p == 0:
            hp = h1p + h2p
        elif abs(h1p - h2p) <= 180:
            hp = (h1p + h2p) / 2
        elif h1p + h2p < 360:
            hp = (h1p + h2p + 360) / 2
        else:
            hp = (h1p + h2p - 360) / 2
            
        # Calculate T
        T = (1 - 
             0.17 * math.cos(math.radians(hp - 30)) + 
             0.24 * math.cos(math.radians(2 * hp)) + 
             0.32 * math.cos(math.radians(3 * hp + 6)) - 
             0.20 * math.cos(math.radians(4 * hp - 63)))
        
        # Calculate RT (rotation term)
        deltaTheta = 30 * math.exp(-((hp - 275) / 25)**2)
        RC = 2 * math.sqrt(Cp**7 / (Cp**7 + 25**7))
        RT = -math.sin(math.radians(2 * deltaTheta)) * RC
        
        # Calculate SL, SC, SH (compensation factors)
        SL = 1 + ((0.015 * (Lp - 50)**2) / math.sqrt(20 + (Lp - 50)**2))
        SC = 1 + 0.045 * Cp
        SH = 1 + 0.015 * Cp * T
        
        # Calculate ΔE CIE2000
        deltaE = math.sqrt(
            (deltaLp / (kL * SL))**2 + 
            (deltaCp / (kC * SC))**2 + 
            (deltaHp / (kH * SH))**2 + 
            RT * (deltaCp / (kC * SC)) * (deltaHp / (kH * SH))
        )
        
        return deltaE
    
    def get_cluster_centroids(self, df: pd.DataFrame) -> Dict[int, Tuple[float, float, float]]:
        """
        Extract cluster centroids from the DataFrame.
        Uses the pre-calculated centroid values from the Centroid_X, Centroid_Y, Centroid_Z columns.
        
        Args:
            df: DataFrame containing the data
            
        Returns:
            Dictionary mapping cluster numbers to (Centroid_X, Centroid_Y, Centroid_Z) centroid coordinates
        """
        centroids = {}
        
        # Log DataFrame shape and columns
        self.logger.info(f"Retrieving centroids from DataFrame with shape {df.shape}")
        self.logger.info(f"Columns available: {sorted(df.columns.tolist())}")
        
        # Check if DataFrame has any data
        if df.empty:
            self.logger.error("DataFrame is empty, no centroids to retrieve")
            return centroids
        
        # Check for and handle case-insensitive column names
        column_map = {col.lower(): col for col in df.columns}
        
        # Check if 'Cluster' column exists (case-insensitive)
        cluster_col = None
        if 'Cluster' in df.columns:
            cluster_col = 'Cluster'
        elif 'cluster' in column_map:
            cluster_col = column_map['cluster']
            self.logger.info(f"Found cluster column with name '{cluster_col}'")
        
        if cluster_col is None:
            self.logger.error("Cluster column not found in DataFrame (case-insensitive search)")
            return centroids
            
        # Get unique clusters and their points
        clusters = df[cluster_col].dropna().unique()
        if len(clusters) == 0:
            self.logger.error("No cluster assignments found in the data")
            return centroids
            
        self.logger.info(f"Found {len(clusters)} unique clusters: {clusters}")
        
        # Check if we have Centroid_X, Centroid_Y, Centroid_Z columns in the data (case-insensitive)
        centroid_columns = {'centroid_x': None, 'centroid_y': None, 'centroid_z': None}
        for col_key in centroid_columns.keys():
            if col_key in column_map:
                centroid_columns[col_key] = column_map[col_key]
                
        # Log what we found
        centroid_cols_found = [col for col in centroid_columns.values() if col is not None]
        self.logger.info(f"Found centroid columns: {centroid_cols_found}")
        
        if not all(centroid_columns.values()):
            missing = [key for key, val in centroid_columns.items() if val is None]
            self.logger.error(f"Required centroid columns missing: {missing}")
            self.logger.error("Please run K-means clustering first and save the results")
            return centroids
        
        # Get the actual column names from the mapping
        centroid_x_col = centroid_columns['centroid_x']
        centroid_y_col = centroid_columns['centroid_y']
        centroid_z_col = centroid_columns['centroid_z']
        
        # Check for any valid centroid data
        valid_mask = (df[centroid_x_col].notna() & 
                     df[centroid_y_col].notna() & 
                     df[centroid_z_col].notna())
        
        valid_count = valid_mask.sum()
        self.logger.info(f"Found {valid_count} rows with non-null centroid values")
        
        if valid_count == 0:
            self.logger.error("No valid centroid data found in any rows")
            self.logger.error("Centroid columns exist but contain only null values")
            return centroids
            
        # Process each cluster to extract its centroid
        for cluster in clusters:
            try:
                if not pd.isna(cluster):
                    cluster_int = int(cluster)
                    
                    # Get all points belonging to this cluster
                    cluster_points = df[df[cluster_col] == cluster_int]
                    
                    if not cluster_points.empty:
                        # Log how many points are in this cluster
                        self.logger.info(f"Cluster {cluster_int} has {len(cluster_points)} points")
                        
                        # Check if centroid columns have values for this cluster
                        valid_centroid_rows = cluster_points[
                            cluster_points[centroid_x_col].notna() & 
                            cluster_points[centroid_y_col].notna() & 
                            cluster_points[centroid_z_col].notna()
                        ]
                        
                        # Log how many valid centroid rows we found
                        if not valid_centroid_rows.empty:
                            self.logger.info(f"Found {len(valid_centroid_rows)} rows with valid centroid data in cluster {cluster_int}")
                            
                            # Debug: print sample values to check data types and formats
                            sample_row = valid_centroid_rows.iloc[0]
                            
                            # Use simple string concatenation to avoid formatting issues
                            self.logger.info("Sample centroid values for cluster " + str(cluster_int) + ":")
                            
                            for col, desc in [
                                (centroid_x_col, "X"),
                                (centroid_y_col, "Y"),
                                (centroid_z_col, "Z")
                            ]:
                                try:
                                    value = float(sample_row[col])
                                    self.logger.info("  Centroid_{0}: {1:.4f} (type: {2})".format(
                                        desc, value, type(value).__name__
                                    ))
                                except Exception as e:
                                    self.logger.warning("  Failed to format Centroid_{0} value: {1}".format(desc, str(e)))
                            
                            # Get the centroid coordinates
                            centroid_x = float(sample_row[centroid_x_col])
                            centroid_y = float(sample_row[centroid_y_col])
                            centroid_z = float(sample_row[centroid_z_col])
                            
                            # Store the centroid for this cluster
                            centroids[cluster_int] = (centroid_x, centroid_y, centroid_z)
                            self.logger.info(f"Found centroid for cluster {cluster_int}: ({centroid_x:.6f}, {centroid_y:.6f}, {centroid_z:.6f})")
            except Exception as e:
                self.logger.error(f"Error processing cluster {cluster}: {str(e)}")
        
        # Final status report
        if centroids:
            self.logger.info(f"Successfully retrieved {len(centroids)} centroids")
        else:
            self.logger.error("No centroids were found. Please run K-means clustering first.")
            self.logger.error("Make sure to 'Apply' and 'Save' in the K-means panel before calculating ΔE.")
            
        return centroids
        
    def calculate_and_save_delta_e(self, start_row: int, end_row: int) -> None:
        """
        Calculate ΔE CIE2000 for each data point against its assigned cluster centroid
        and save the results to the .ods file.
        
        Args:
            start_row: 1-based start row number 
            end_row: 1-based end row number
        """
        # Reload the data from the file to ensure we have the most up-to-date information
        if self.file_path and os.path.exists(self.file_path):
            try:
                self.logger.info(f"Reloading data from file before ΔE calculation: {self.file_path}")
                updated_data = pd.read_excel(self.file_path, engine='odf')
                
                # Verify required columns
                if not all(col in updated_data.columns for col in self.EXPECTED_COLUMNS):
                    missing = [col for col in self.EXPECTED_COLUMNS if col not in updated_data.columns]
                    self.logger.error(f"Required columns missing after reload: {missing}")
                    raise ValueError(f"Required columns missing after reload: {missing}")
                
                # Update the internal data and verify
                self.data = updated_data
                self.logger.info("Successfully reloaded data with updated centroid information")
                
                # STEP 1: Verify cluster assignments exist
                self.logger.info("Verifying cluster assignments...")
                if 'Cluster' not in self.data.columns or self.data['Cluster'].isna().all():
                    self.logger.error("No cluster assignments found in file")
                    raise ValueError("No cluster assignments found. Please run K-means clustering first.")
                
                # STEP 2: Systematically check for centroid data
                self.logger.info("Checking for centroid data...")
                
                # Initialize our validation variables
                dedicated_centroid_data = False
                legacy_centroid_data = False
                
                # STEP 2A: Check for dedicated Centroid_X/Y/Z columns
                centroid_columns = ['Centroid_X', 'Centroid_Y', 'Centroid_Z']
                has_centroid_columns = all(col in self.data.columns for col in centroid_columns)
                
                if has_centroid_columns:
                    # Check if at least one row has valid centroid data in these columns
                    dedicated_centroid_data = not self.data[centroid_columns].isna().all().all()
                    self.logger.info(f"Dedicated centroid columns exist: True, contain data: {dedicated_centroid_data}")
                else:
                    self.logger.info("Dedicated centroid columns not found in file")
                
                # STEP 2B: Check for legacy X/Y/Z centroid data if needed
                if not dedicated_centroid_data:
                    # Check if legacy columns exist
                    legacy_columns = ['X', 'Y', 'Z']
                    has_legacy_columns = all(col in self.data.columns for col in legacy_columns)
                    
                    if has_legacy_columns:
                        # Check if at least one row has valid centroid data in legacy columns
                        legacy_centroid_data = not self.data[legacy_columns].isna().all().all()
                        self.logger.info(f"Legacy centroid columns exist and contain data: {legacy_centroid_data}")
                    else:
                        self.logger.warning("No legacy centroid columns found")
                
                # STEP 3: Final determination if we have valid centroid data
                centroid_data_exists = dedicated_centroid_data or legacy_centroid_data
                self.logger.info(f"Valid centroid data exists: {centroid_data_exists}")
                
                # STEP 4: If no valid centroid data, show detailed error message
                if not centroid_data_exists:
                    self.logger.error("No centroid data found in file")
                    error_msg = (
                        "No centroid data found. Please ensure you:\n"
                        "1. Run K-means clustering first (click 'Apply')\n"
                        "2. Save the cluster assignments (click 'Save')\n"
                        "3. Wait for the 'Clusters Saved' confirmation\n"
                        "4. Then try calculating ΔE values again"
                    )
                    
                    raise ValueError(error_msg)
            except Exception as e:
                self.logger.error(f"Failed to reload data from file: {str(e)}")
                self.logger.warning("Will continue with existing data in memory")
                # Don't raise here to maintain backward compatibility, but log the error
        else:
            self.logger.warning("No file path set or file does not exist. Unable to reload data.")
        
        # Validate that we have valid cluster assignments
        if self.data is None:
            raise ValueError("No data loaded. Please load data first.")
        # Check if we have cluster assignments - redundant check as a fallback
        if 'Cluster' not in self.data.columns:
            raise ValueError("Cluster column not found. Please run K-means clustering first.")
            
        # Check if any clusters are assigned - redundant check as a fallback
        if self.data['Cluster'].isna().all():
            raise ValueError("No cluster assignments found. Please run K-means clustering first.")
        # Log the clusters found in the data
        cluster_counts = self.data['Cluster'].value_counts().to_dict()
        self.logger.info(f"Cluster distribution in data: {cluster_counts}")
        
        lockfile = None
        try:
            if self.file_path is None:
                raise ValueError("No file path set")
                
            # Check if file exists and is accessible
            if not os.path.exists(self.file_path):
                raise IOError(f"File not found: {self.file_path}")
                
            if not os.access(self.file_path, os.W_OK):
                raise IOError(f"File {self.file_path} is not writable")
            
            # Verify file is .ods format
            if not self.file_path.endswith('.ods'):
                raise ValueError("Only .ods files are supported for saving ΔE calculations")
                # Inform user of the process
            msg = (f"Calculating and saving ΔE values ONLY for rows {start_row}-{end_row}:\n\n"
                  "1. Your original .ods file will be updated directly\n"
                  "2. ONLY the ΔE column will be modified\n"
                  "3. Existing centroid data will be PRESERVED\n\n"
                  "Continue?")
            
            if not messagebox.askokcancel("Calculate ΔE", msg):
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
                # Get the rows we're working with and validate using our own validation methods
                # This ensures consistency with KmeansManager's row handling
                start_row, end_row = self.validate_row_range(start_row, end_row)
                row_indices = list(self._get_row_indices(start_row, end_row))
                
                # Get data for our selected range
                subset_data = self.data.iloc[row_indices]
                
                # Get cluster assignments for each point
                clusters = subset_data['Cluster']
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
                        
                        # Check if required columns exist
                        required_columns = ['∆E', 'Centroid_X', 'Centroid_Y', 'Centroid_Z']
                        col_indices = {}
                        
                        # Get indices of existing columns
                        for col in required_columns:
                            if col in df.columns:
                                col_indices[col] = df.columns.get_loc(col)
                                self.logger.info(f"Found {col} column at index {col_indices[col]}")
                        
                        # Check for required column
                        if '∆E' not in col_indices:
                            raise ValueError("∆E column not found in spreadsheet")
                        
                        delta_e_col_idx = col_indices['∆E']
                        self.logger.info(f"Using ∆E column at index {delta_e_col_idx}")
                        
                        # Note centroid column indices for later reference
                        centroid_col_indices = {}
                        
                        # Get cluster centroids
                        self.logger.info("Retrieving cluster centroids for Delta E calculation")
                        centroids = self.get_cluster_centroids(self.data)
                        
                        if not centroids:
                            self.logger.error("No cluster centroids found. Please run K-means clustering first.")
                            self.logger.error("Make sure to click 'Apply' then 'Save' in the K-means panel, then restart this application before calculating ΔE.")
                            raise ValueError("No cluster centroids found. Please run K-means clustering first and save the results.")
                        missing_clusters = []
                        for cluster in subset_data['Cluster'].dropna().unique():
                            cluster_int = int(cluster)
                            if cluster_int not in centroids:
                                missing_clusters.append(cluster_int)
                                
                        if missing_clusters:
                            error_msg = f"Missing centroids for clusters: {missing_clusters}"
                            self.logger.error(error_msg)
                            self.logger.error("Please run K-means clustering to regenerate centroid data for all clusters")
                            raise ValueError(f"Cannot calculate Delta E: {error_msg}")
                        # Log the centroids we found
                        self.logger.info(f"Using the following centroids for Delta E calculation:")
                        for cluster, centroid in centroids.items():
                            self.logger.info(f"Cluster {cluster}: ({centroid[0]:.6f}, {centroid[1]:.6f}, {centroid[2]:.6f})")
                        # Store delta_e values for each row
                        delta_e_values = []
                        
                        # Track progress
                        processed_count = 0
                        success_count = 0
                        
                        # Process each row in the specified range
                        for i, row in subset_data.iterrows():
                            processed_count += 1
                            self.logger.info(f"Processing row {i+1} ({processed_count}/{len(subset_data)})")
                            
                            cluster = row['Cluster']
                            if pd.isna(cluster):
                                # Skip rows without cluster assignment
                                self.logger.warning(f"Row {i+1}: No cluster assignment, skipping")
                                delta_e_values.append((i, None))
                                continue
                                
                            cluster_int = int(cluster)
                            if cluster_int not in centroids:
                                self.logger.warning(f"Row {i+1}: No centroid found for cluster {cluster_int}")
                                delta_e_values.append((i, None))
                                continue
                            # Get point coordinates (normalized values)
                            point_xyz = (row['Xnorm'], row['Ynorm'], row['Znorm'])
                            
                            # Check for invalid point coordinates
                            if any(pd.isna(val) for val in point_xyz):
                                self.logger.warning(f"Invalid point coordinates at index {i}, DataID: {row.get('DataID', f'Row {i}')}")
                                delta_e_values.append((i, None))
                                continue
                            
                            # Get centroid coordinates
                            centroid_xyz = centroids[cluster_int]
                            
                            # Validate centroid once more
                            if any(pd.isna(val) for val in centroid_xyz):
                                self.logger.error(f"Invalid centroid for cluster {cluster_int}: {centroid_xyz}")
                                delta_e_values.append((i, None))
                                continue
                                
                            # Log the point and centroid for debugging
                            self.logger.debug(f"Point {row.get('DataID', f'Row {i}')} - Cluster {cluster_int}")
                            self.logger.debug(f"  Point XYZ: ({point_xyz[0]:.4f}, {point_xyz[1]:.4f}, {point_xyz[2]:.4f})")
                            self.logger.debug(f"  Centroid XYZ: ({centroid_xyz[0]:.4f}, {centroid_xyz[1]:.4f}, {centroid_xyz[2]:.4f})")
                            
                            # Convert to Lab
                            try:
                                point_lab = self.xyz_to_lab(*point_xyz)
                                centroid_lab = self.xyz_to_lab(*centroid_xyz)
                            except Exception as e:
                                self.logger.error(f"Error converting to Lab color space: {str(e)}")
                                delta_e_values.append((i, None))
                                continue
                            
                            # Calculate delta E (CIE2000)
                            try:
                                delta_e = self.calculate_delta_e_2000(point_lab, centroid_lab)
                                
                                # Delta E 2000 is already in an appropriate scale, no need to multiply by 100
                                # The scale is typically 0-100 where:
                                # 0-1: Not perceptible by human eyes
                                # 1-2: Perceptible through close observation
                                # 2-10: Perceptible at a glance
                                # 10-50: Colors are more similar than opposite
                                # 50+: Colors are very different
                                
                                # Round to 2 decimal places
                                delta_e = round(delta_e, 2)
                                
                                # Validate the calculated value
                                if pd.isna(delta_e) or delta_e < 0:
                                    self.logger.warning(f"Invalid Delta E value calculated: {delta_e} for point at index {i}")
                                    delta_e_values.append((i, None))
                                    continue
                                
                                # Additional validation - if Delta E is unreasonably large, log a warning
                                if delta_e > 100:
                                    self.logger.warning(f"Unusually large Delta E value calculated: {delta_e} for point at index {i}")
                                    # But still use the value as it could be valid for very different colors
                                    
                                self.logger.debug(f"  Calculated Delta E: {delta_e}")
                                
                            except Exception as e:
                                self.logger.error(f"Error calculating Delta E: {str(e)}")
                                delta_e_values.append((i, None))
                                continue
                            
                            delta_e_values.append((i, delta_e))
                            
                        # Prepare updates
                        updates = []
                        for idx, value in delta_e_values:
                            sheet_row_idx = idx + 1
                            if value is not None:
                                updates.append((sheet_row_idx, value))
                        
                        if updates:
                            self.logger.info(f"Preparing to update {len(updates)} cells")
                            
                            try:
                                # Open and update
                                self.logger.info(f"Opening {self.file_path} for updating")
                                ods_doc = ezodf.opendoc(self.file_path)
                                sheet = ods_doc.sheets[0]
                                
                                # Check if we need to add centroid columns
                                header_row = 0  # Header row index
                                num_cols = len(sheet.row(header_row))
                                
                                # Create centroid columns if they don't exist
                                for col_name in ['Centroid_X', 'Centroid_Y', 'Centroid_Z']:
                                    if col_name not in col_indices:
                                        # Add column to the right of the spreadsheet
                                        col_idx = num_cols
                                        num_cols += 1
                                        
                                        # Set header
                                        cell = sheet[header_row, col_idx]
                                        cell.set_value(col_name)
                                        # Removed cell.value_type assignment that was causing errors
                                        centroid_col_indices[col_name] = col_idx
                                        self.logger.info(f"Created new column '{col_name}' at index {col_idx}")
                                    else:
                                        centroid_col_indices[col_name] = col_indices[col_name]
                                
                                # Log updates for debugging
                                self.logger.info(f"Preparing to update {len(updates)} rows with ∆E values ONLY")
                                self.logger.info(f"Updates will ONLY be applied to the ∆E column at index {delta_e_col_idx}")
                                self.logger.info(f"Existing centroid data will be PRESERVED")
                                
                                if len(updates) > 0:
                                    self.logger.info(f"Sample updates (first 3):")
                                    for i, (row, val) in enumerate(updates[:3]):
                                        self.logger.info(f"  Row {row}: ∆E = {val}")
                                
                                # Apply ONLY ΔE updates - do not touch any other columns
                                for row_idx, value in updates:
                                    try:
                                        # Update ONLY the ΔE value
                                        cell = sheet[row_idx, delta_e_col_idx]
                                        cell.set_value(value)
                                        self.logger.debug(f"Updated ∆E at row {row_idx} to {value}")
                                    except Exception as cell_error:
                                        self.logger.warning(f"Failed to update cell at row {row_idx}: {str(cell_error)}")
                                
                                # Create a file backup before saving
                                pre_save_backup = f"{self.file_path}.presave"
                                self.logger.info(f"Creating pre-save backup at: {pre_save_backup}")
                                try:
                                    shutil.copy2(self.file_path, pre_save_backup)
                                except Exception as backup_error:
                                    self.logger.warning(f"Failed to create pre-save backup: {str(backup_error)}")
                                
                                # Save to a new file
                                temp_path = f"{self.file_path}.new"
                                self.logger.info(f"Saving to temporary file: {temp_path}")
                                try:
                                    ods_doc.saveas(temp_path)
                                    
                                    # Close document
                                    del ods_doc
                                    
                                    # Replace original with new file
                                    self.logger.info("Replacing original file with updated version (∆E column only)")
                                    os.replace(temp_path, self.file_path)
                                except Exception as save_error:
                                    self.logger.error(f"Failed to save file: {str(save_error)}")
                                    # Try to restore from pre-save backup
                                    if os.path.exists(pre_save_backup):
                                        self.logger.info("Attempting to restore from pre-save backup")
                                        try:
                                            shutil.copy2(pre_save_backup, self.file_path)
                                            self.logger.info("Successfully restored from pre-save backup")
                                        except Exception as restore_error:
                                            self.logger.error(f"Failed to restore from backup: {str(restore_error)}")
                                    raise save_error
                                # Verify the save
                                # Verify the save
                                try:
                                    self.logger.info("Verifying save operation")
                                    verify_doc = ezodf.opendoc(self.file_path)
                                    verify_sheet = verify_doc.sheets[0]
                                    
                                    # Check updates
                                    # Check updates
                                    for row_idx, value in updates[:min(3, len(updates))]:
                                        # Verify ∆E value was saved correctly
                                        try:
                                            delta_e_cell = verify_sheet[row_idx, delta_e_col_idx]
                                            
                                            # Get cell value, handling empty or non-numeric values
                                            cell_value = delta_e_cell.value
                                            if cell_value is None or cell_value == '':
                                                self.logger.warning(f"Empty ∆E value found at row {row_idx}")
                                                continue
                                                
                                            # Convert to float for comparison
                                            cell_float = float(cell_value)
                                            # Compare with acceptable rounding difference
                                            if abs(cell_float - value) > 0.01:
                                                self.logger.warning(f"∆E value mismatch at row {row_idx}: expected {value}, got {cell_float}")
                                        except Exception as e:
                                            self.logger.warning(f"Error verifying ∆E value at row {row_idx}: {str(e)}")
                                            continue
                                    
                                    
                                    # Before removing backup, verify centroid data was preserved
                                    centroid_preserved = True
                                    try:
                                        for col_name, col_idx in centroid_col_indices.items():
                                            if col_idx is not None:
                                                for row_idx, _ in updates[:min(3, len(updates))]:
                                                    centroid_cell = verify_sheet[row_idx, col_idx]
                                                    if centroid_cell.value is None:
                                                        self.logger.warning(f"Centroid data may have been lost for {col_name} at row {row_idx}")
                                                        centroid_preserved = False
                                                    else:
                                                        self.logger.debug(f"Verified {col_name} at row {row_idx}: {centroid_cell.value}")
                                        
                                        if not centroid_preserved:
                                            self.logger.warning("Some centroid data verification failed - keeping backup file")
                                    except Exception as verify_error:
                                        self.logger.warning(f"Error verifying centroid data: {str(verify_error)}")
                                        centroid_preserved = False
                                    
                                    # Clean up verification document before finishing
                                    del verify_doc
                                
                                except Exception as verify_exception:
                                    self.logger.error(f"Save verification failed: {str(verify_exception)}")
                                    # If verification doc was created, clean it up
                                    if 'verify_doc' in locals():
                                        del verify_doc
                                # Remove backup if everything succeeded and centroid data was preserved
                                if os.path.exists(backup_path) and centroid_preserved:
                                    try:
                                        os.remove(backup_path)
                                        self.logger.info("Backup file removed")
                                    except Exception as e:
                                        self.logger.warning(f"Could not remove backup file: {str(e)}")
                                elif os.path.exists(backup_path):
                                    self.logger.info(f"Keeping backup file at {backup_path} as a precaution")
                                # Count how many values were actually calculated
                                successful_updates = sum(1 for _, value in delta_e_values if value is not None)
                                
                                # Generate detailed completion message
                                completion_msg = (
                                    f"Successfully calculated and saved ΔE values.\n\n"
                                    f"Total points processed: {len(delta_e_values)}\n"
                                    f"Successful calculations: {successful_updates}\n"
                                    f"Failed calculations: {len(delta_e_values) - successful_updates}\n\n"
                                    f"IMPORTANT: Existing centroid data has been preserved."
                                )
                                self.logger.info(completion_msg.replace('\n', ' '))
                                
                                # Show the completion message in a way that won't block the UI
                                if self.frame and self.frame.winfo_exists():
                                    self.frame.after(100, lambda: messagebox.showinfo("ΔE Calculation Complete", completion_msg))
                                else:
                                    # Fallback if frame doesn't exist
                                    messagebox.showinfo("ΔE Calculation Complete", completion_msg)
                            except (IOError, OSError) as e:
                                self.logger.error(f"File operation failed: {str(e)}")
                                raise  # Re-raise the original exception
                            except ValueError as e:
                                self.logger.error(f"Data validation failed: {str(e)}")
                                raise  # Re-raise the original validation error
                            except Exception as e:
                                self.logger.error(f"Unexpected error during ΔE calculation: {str(e)}")
                                raise ValueError(f"Failed to complete ΔE calculation: {str(e)}")
                            finally:
                                # Clean up temporary files
                                for path in [backup_path, f"{self.file_path}.new"]:
                                    try:
                                        if os.path.exists(path):
                                            os.remove(path)
                                    except Exception:
                                        pass
                                    
                                # Clean up document objects
                                for doc_name in ['ods_doc', 'verify_doc']:
                                    try:
                                        if doc_name in locals():
                                            del locals()[doc_name]
                                    except Exception:
                                        pass
                    except Exception as e:
                        self.logger.error(f"Error in Delta E calculation: {str(e)}")
                        raise
                else:
                    messagebox.showwarning("Warning", 
                        f"No cluster assignments found for rows {start_row}-{end_row}")
            
            finally:
                # Always release the lock, even if an error occurred
                if lockfile:
                    self.logger.info("Releasing file lock")
                    fcntl.flock(lockfile, fcntl.LOCK_UN)
                    lockfile.close()
                    try:
                        os.remove(lock_path)
                        self.logger.info("Lock file removed")
                    except OSError:
                        self.logger.warning("Could not remove lock file")
                        
        except FileNotFoundError as e:
            self.logger.error(f"File not found: {str(e)}")
            error_msg = f"The file could not be found:\n{str(e)}\n\nPlease verify the file path and try again."
            if self.frame and self.frame.winfo_exists():
                self.frame.after(100, lambda: messagebox.showerror("File Not Found", error_msg))
            else:
                messagebox.showerror("File Not Found", error_msg)
        except PermissionError as e:
            self.logger.error(f"Permission error: {str(e)}")
            error_msg = f"You don't have permission to access this file:\n{str(e)}\n\nPlease check file permissions and make sure the file isn't open in another program."
            if self.frame and self.frame.winfo_exists():
                self.frame.after(100, lambda: messagebox.showerror("Permission Denied", error_msg))
            else:
                messagebox.showerror("Permission Denied", error_msg)
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self.logger.error(f"Error calculating ΔE: {str(e)}")
            self.logger.error(error_trace)
            # Show a more detailed error message
            error_msg = f"An error occurred while calculating Delta E:\n\n{str(e)}"
            if "centroid" in str(e).lower() or "cluster" in str(e).lower() or "data" in str(e).lower():
                error_msg += "\n\nThis error is related to missing centroid or cluster data."
                error_msg += "\n\nPlease follow the correct workflow:"
                error_msg += "\n1. Run K-means clustering first (click 'Apply')"
                error_msg += "\n2. Save the cluster assignments (click 'Save')"
                error_msg += "\n3. Wait for the 'Clusters Saved' confirmation"
                error_msg += "\n4. Then calculate ΔE values"
                error_msg += "\n\nIf you've already done K-means clustering, try closing and reopening the application to refresh data."
                error_msg += "\n\nTip: Look for the 'Centroid_X', 'Centroid_Y' and 'Centroid_Z' columns in your spreadsheet to confirm centroids were saved."
            
            if self.frame and self.frame.winfo_exists():
                self.frame.after(100, lambda: messagebox.showerror("Error", f"{error_msg}\n\nCheck the log for details."))
            else:
                messagebox.showerror("Error", f"{error_msg}\n\nCheck the log for details.")
            
    def create_gui(self, parent):
        """Create the ΔE calculation control panel."""
        if parent is None:
            self.logger.error("Parent widget is None, cannot create GUI components")
            raise ValueError("Parent widget cannot be None")
            
        # Store the parent widget for later reference
        self.parent = parent
            
        # Create a frame for ΔE controls
        try:
            self.frame = tk.LabelFrame(parent, text="ΔE CIE2000", padx=2, pady=1)
            # Create a single row for all controls
            control_frame = tk.Frame(self.frame)
            control_frame.pack(fill=tk.X, pady=1)
        
            # Row range inputs in a more compact layout
            tk.Label(control_frame, text="Rows:", font=("Arial", 9)).pack(side=tk.LEFT)
            self.start_row = tk.Entry(control_frame, width=3)
            self.start_row.insert(0, "2")
            self.start_row.pack(side=tk.LEFT, padx=1)
            tk.Label(control_frame, text="-").pack(side=tk.LEFT)
            self.end_row = tk.Entry(control_frame, width=3)
            self.end_row.insert(0, "999")
            self.end_row.pack(side=tk.LEFT, padx=1)
            
            # Action buttons
            self.apply_button = tk.Button(control_frame, text="Calculate", command=self._calculate_delta_e_gui,
                                        font=("Arial", 9))
            self.apply_button.pack(side=tk.LEFT, padx=1)
            
            # Help button for workflow guidance
            help_button = tk.Button(control_frame, text="?", command=self._show_workflow_guide,
                                  font=("Arial", 9), width=1, bg="lightblue")
            help_button.pack(side=tk.LEFT, padx=2)
            
            self.logger.info("ΔE GUI components created successfully")
            return self.frame
            
        except Exception as e:
            self.logger.error(f"Error creating GUI components: {str(e)}")
            raise ValueError(f"Failed to create GUI components: {str(e)}")

    def _show_workflow_guide(self):
        """Display a guide explaining the correct workflow for K-means and ΔE calculations"""
        workflow_msg = (
            "Correct Workflow for K-means and ΔE Calculations:\n\n"
            "1. First ensure K-means clustering is done:\n"
            "   - Run K-means if not already done (Apply + Save)\n"
            "   - Or verify existing centroid data is present\n"
            "   - Look for Centroid_X/Y/Z columns with values\n\n"
            "2. Then calculate ΔE values:\n"
            "   - Enter the row range containing data\n"
            "   - Click \"Calculate\" to compute ΔE values\n"
            "   - Wait for completion confirmation\n\n"
            "Important Tips:\n"
            "• Existing centroid data will be preserved\n"
            "• ΔE calculations use current centroid data\n"
            "• Check that centroids exist before calculating\n"
            "• Row range should match your data\n"
            "• If you get errors, try closing and reopening the application\n\n"
            "This sequence ensures proper ΔE calculation while preserving your centroid data."
        )
        messagebox.showinfo("Workflow Guide", workflow_msg)

    def _calculate_delta_e_gui(self):
        """Handle the Calculate ΔE button click."""
        # Check if GUI components exist
        if self.frame is None or self.apply_button is None:
            self.logger.error("GUI components not initialized")
            raise ValueError("GUI components not initialized. Please create GUI first.")
            
        try:
            # Disable the button to prevent multiple clicks
            self.apply_button.config(state=tk.DISABLED)
            self.apply_button.update()
            # Show progress indication
            self.apply_button.config(text="Working...")
            self.apply_button.update()
            # Get the row range
            start = int(self.start_row.get())
            end = int(self.end_row.get())
            
            # Function to restore button
            # Function to restore button
            def restore_button():
                if self.apply_button and self.apply_button.winfo_exists():
                    self.apply_button.config(text="Calculate", state=tk.NORMAL)
                    self.apply_button.update()
            
            try:
                # Run the calculation
                self.calculate_and_save_delta_e(start, end)
            finally:
                # Ensure button is restored even if an error occurs
                if self.frame and self.frame.winfo_exists():
                    self.frame.after(500, restore_button)
        except ValueError as e:
            self.logger.error(f"Value error in GUI: {str(e)}")
            if self.frame and self.frame.winfo_exists():
                self.frame.after(100, lambda: tk.messagebox.showerror("Error", str(e)))
            else:
                tk.messagebox.showerror("Error", str(e))
        except Exception as e:
            import traceback
            self.logger.error(f"GUI error: {str(e)}")
            self.logger.error(traceback.format_exc())
            if self.frame and self.frame.winfo_exists():
                self.frame.after(100, lambda: tk.messagebox.showerror("Error", f"An error occurred: {str(e)}"))
            else:
                tk.messagebox.showerror("Error", f"An error occurred: {str(e)}")
