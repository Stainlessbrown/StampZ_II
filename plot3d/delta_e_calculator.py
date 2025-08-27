import os
import logging
import math
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import messagebox
import ezodf
from typing import Tuple, Dict, List, Optional

class DeltaECalculator:
    """
    A focused calculator for ΔE CIE2000 color differences between normalized points and their cluster centroids.
    
    This calculator works with normalized color values (0.0-1.0 range) in both Lab and RGB color spaces.
    While ΔE CIE2000 was designed for Lab color space, it can provide useful relative differences 
    for RGB data as well.
    """
    
    # Reference white point for XYZ to L*a*b* conversion
    REF_WHITE_X = 1.0
    REF_WHITE_Y = 1.0
    REF_WHITE_Z = 1.0
    
    def __init__(self, logger=None):
        """Initialize the calculator with optional logger."""
        # Set up logging
        if logger is None:
            self.logger = logging.getLogger("DeltaECalculator")
            if not self.logger.handlers:
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler = logging.StreamHandler()
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger
            
        self.file_path = None
        self.frame = None
        self.start_row_entry = None
        self.end_row_entry = None
        self.ref_row_entry = None
        self.calculate_button = None
        
        self.logger.info("DeltaECalculator initialized")
    
    def set_file_path(self, file_path: str) -> None:
        """Set the file path for the .ods file."""
        if not file_path:
            self.logger.error("Empty file path provided")
            raise ValueError("File path cannot be empty")
            
        if not os.path.isfile(file_path):
            self.logger.error(f"File does not exist: {file_path}")
            raise ValueError(f"File does not exist: {file_path}")
            
        if not file_path.endswith('.ods'):
            self.logger.error(f"File is not an .ods file: {file_path}")
            raise ValueError("Only .ods files are supported")
            
        self.file_path = file_path
        self.logger.info(f"Set file path to: {file_path}")
    
    def validate_row_range(self, start_row: int, end_row: int) -> Tuple[int, int]:
        """
        Validate that the row range is within bounds.
        
        Args:
            start_row: 1-based start row number (where 2 is first data row after header)
            end_row: 1-based end row number
            
        Returns:
            Tuple of validated (start_row, end_row)
        """
        # Load the data to validate against
        try:
            df = pd.read_excel(self.file_path, engine='odf')
            self.logger.info(f"Loaded data with {len(df)} rows for validation")
        except Exception as e:
            self.logger.error(f"Failed to load data for validation: {e}")
            raise ValueError(f"Could not validate row range: {e}")
        
        # Find the last row with valid numeric data
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        last_valid_rows = []
        
        for col in numeric_cols:
            valid_indices = df[col].notna().values.nonzero()[0]
            if len(valid_indices) > 0:
                last_valid_rows.append(valid_indices[-1])
        
        if not last_valid_rows:
            self.logger.error("No numeric data found in file")
            raise ValueError("No numeric data found in the file")
        
        last_valid_row = max(last_valid_rows) + 1  # Add 1 for 1-based indexing
        
        # Minimum valid row is 2 (first data row after header)
        min_valid_row = 2
        
        if start_row < min_valid_row:
            self.logger.error(f"Invalid start_row {start_row}, must be at least {min_valid_row}")
            raise ValueError(f"Start row must be at least {min_valid_row} (first data row)")
        
        max_row = min(999, last_valid_row)  # Limit to 999 rows or last valid row
        if end_row > max_row:
            self.logger.error(f"Invalid end_row {end_row}, exceeds last valid row {max_row}")
            raise ValueError(f"End row exceeds last valid row ({max_row})")
        
        if start_row > end_row:
            self.logger.error(f"Start row {start_row} is greater than end row {end_row}")
            raise ValueError("Start row must be less than or equal to end row")
        
        self.logger.info(f"Validated row range: {start_row} to {end_row}")
        return start_row, end_row
    
    def _get_data_indices(self, start_row: int, end_row: int) -> range:
        """
        Convert from 1-based row numbers to 0-based DataFrame indices.
        
        Args:
            start_row: 1-based start row number (where 2 is first data row)
            end_row: 1-based end row number
            
        Returns:
            Range of 0-based DataFrame indices
        """
        # Validate row range
        start_row, end_row = self.validate_row_range(start_row, end_row)
        
        # Convert to 0-based indices (row 2 maps to index 0)
        zero_based_start = start_row - 2
        zero_based_end = end_row - 2
        
        self.logger.info(f"Converting rows {start_row}-{end_row} to indices {zero_based_start}-{zero_based_end}")
        
        return range(zero_based_start, zero_based_end + 1)
    
    def xyz_to_lab(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Convert XYZ color values to L*a*b* color space.
        
        Args:
            x, y, z: Values in XYZ color space (0.0-1.0 normalized)
            
        Returns:
            Tuple of (L*, a*, b*) values
        """
        # Validate and clip input values to 0-1 range
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        z = max(0.0, min(1.0, z))
        
        # Scale XYZ values relative to reference white
        x = x / self.REF_WHITE_X
        y = y / self.REF_WHITE_Y
        z = z / self.REF_WHITE_Z
        
        # Apply nonlinear transformation
        def transform(t):
            epsilon = 0.008856  # Intent is 216/24389
            kappa = 903.3      # Intent is 24389/27
            
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
        
        # Validate output values
        L = max(0.0, min(100.0, L))
        
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
    
    def validate_data(self, data: pd.DataFrame, row_indices: range, ref_row_idx: int = None) -> None:
        """
        Validate data for ΔE calculation.
        
        Args:
            data: DataFrame containing the data
            row_indices: Range of row indices to validate
            ref_row_idx: Index of the row containing reference centroid values (0-based)
            
        Raises:
            ValueError: If data validation fails
        """
        # Check required columns
        required_columns = ['Xnorm', 'Ynorm', 'Znorm', 'Centroid_X', 'Centroid_Y', 'Centroid_Z', '∆E']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            self.logger.error(f"Missing required columns: {missing_columns}")
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Subset data to the selected row range
        subset = data.iloc[row_indices]
        
        coordinate_columns = ['Xnorm', 'Ynorm', 'Znorm']
        centroid_columns = ['Centroid_X', 'Centroid_Y', 'Centroid_Z']
        
        # For each row, only validate if it contains any coordinate data
        for idx, row in subset.iterrows():
            # Skip completely blank rows
            if row[coordinate_columns].isna().all():
                self.logger.debug(f"Skipping blank row {idx + 2}")
                continue
                
            # If row has any coordinate data, validate all coordinates are present
            if row[coordinate_columns].notna().any():
                missing_coords = [col for col in coordinate_columns if pd.isna(row[col])]
                if missing_coords:
                    row_num = idx + 2  # Convert to 1-based row number
                    self.logger.error(f"Row {row_num} has partial coordinate data: missing {missing_coords}")
                    raise ValueError(f"Row {row_num} has incomplete coordinate data.\n"
                                   f"If any coordinate is provided, all coordinates (Xnorm, Ynorm, Znorm) must be present.")
                
                # Validate coordinate ranges
                for col in coordinate_columns:
                    if not (0 <= row[col] <= 1):
                        row_num = idx + 2
                        self.logger.error(f"Row {row_num} has {col} value outside 0-1 range: {row[col]}")
                        raise ValueError(f"Row {row_num} has {col} value outside the valid range.\n"
                                       f"All coordinate values must be between 0.0 and 1.0.")
        
        # Validate reference row if specified
        if ref_row_idx is not None:
            if ref_row_idx >= len(data):
                self.logger.error(f"Reference row index {ref_row_idx} is out of bounds")
                raise ValueError(f"Reference row {ref_row_idx + 2} is out of bounds")
                
            ref_row = data.iloc[ref_row_idx]
            ref_row_num = ref_row_idx + 2
            
            # For Reference Point calculation, we only need valid coordinate data in the reference row
            # Skip validation if the reference row is completely blank
            if ref_row[coordinate_columns].isna().all():
                self.logger.debug(f"Reference row {ref_row_num} is blank, skipping validation")
                return
                
            # Check for missing coordinate values
            missing_coords = [col for col in coordinate_columns if pd.isna(ref_row[col])]
            if missing_coords:
                self.logger.error(f"Reference row {ref_row_num} has missing coordinate values")
                raise ValueError(f"Reference row {ref_row_num} is missing required coordinate values: "
                               f"{', '.join(missing_coords)}.\n"
                               f"The reference row must have valid X, Y, Z coordinates.")
            
            # Validate coordinate ranges for reference point
            for col in coordinate_columns:
                if not (0 <= ref_row[col] <= 1):
                    self.logger.error(f"Reference row {ref_row_num} has {col} value outside 0-1 range: {ref_row[col]}")
                    raise ValueError(f"Reference row {ref_row_num} has {col} value outside the valid range.\n"
                                   f"All coordinate values must be between 0.0 and 1.0.")
        # Check for values outside the normalized 0-1 range
        # First check coordinate columns in all rows
        for col in coordinate_columns:
            out_of_range = ((subset[col] < 0) | (subset[col] > 1)).any()
            if out_of_range:
                self.logger.error(f"Column {col} contains values outside the 0-1 normalized range")
                raise ValueError(f"Column {col} contains values outside the 0-1 normalized range.\n"
                                f"All coordinate values must be between 0.0 and 1.0.")
        
        # Then check centroid columns in reference row only if specified
        if ref_row_idx is not None:
            ref_row = data.iloc[ref_row_idx]
            for col in centroid_columns:
                if not pd.isna(ref_row[col]) and (ref_row[col] < 0 or ref_row[col] > 1):
                    ref_row_num = ref_row_idx + 2  # Convert to 1-based for display
                    self.logger.error(f"Reference row {ref_row_num} has {col} value outside the 0-1 normalized range")
                    raise ValueError(f"Reference row {ref_row_num} has {col} value outside the 0-1 normalized range.\n"
                                    f"All centroid values must be between 0.0 and 1.0.")

    def calculate_delta_e(self, start_row: int, end_row: int, ref_row: int = None) -> None:
        """
        Calculate ΔE CIE2000 for the specified row range and update the .ods file.
        
        Args:
            start_row: 1-based start row number
            end_row: 1-based end row number
            ref_row: 1-based reference row number containing centroid values (optional)
                     If not specified, each row must have its own centroid values
        """
        if self.file_path is None:
            self.logger.error("No file path set")
            raise ValueError("No file path set. Call set_file_path() first.")
            
        if not os.path.exists(self.file_path):
            self.logger.error(f"File not found: {self.file_path}")
            raise ValueError(f"File not found: {self.file_path}")
        
        # Convert ref_row to 0-based index if specified
        ref_row_idx = None
        ref_row_display = "each row's own"
        
        if ref_row is not None:
            ref_row_idx = ref_row - 2  # Convert from 1-based to 0-based
            ref_row_display = f"row {ref_row}"
            
        # Confirm with user
        confirmation_message = (
            f"Calculate ΔE values for rows {start_row}-{end_row}?\n\n"
        )
        
        if ref_row is not None:
            confirmation_message += f"Using reference point coordinates from row {ref_row}.\n\n"
        else:
            confirmation_message += "Using each row's own centroid values.\n\n"
            
        confirmation_message += "ONLY the ΔE column will be updated, all other data will be preserved."
        
        confirmation = messagebox.askokcancel(
            "Calculate ΔE", 
            confirmation_message
        )
        
        if not confirmation:
            self.logger.info("Operation cancelled by user")
            return
            
        try:
            # Load data from file
            self.logger.info(f"Loading data from {self.file_path}")
            data = pd.read_excel(self.file_path, engine='odf')
            
            # Verify required columns exist
            required_columns = ['Xnorm', 'Ynorm', 'Znorm', 'Centroid_X', 'Centroid_Y', 'Centroid_Z', '∆E']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Get indices for the selected row range
            row_indices = self._get_data_indices(start_row, end_row)
            
            # Open the .ods file for direct editing
            ods_doc = ezodf.opendoc(self.file_path)
            sheet = ods_doc.sheets[0]
            
            # Validate data in selected range
            self.logger.info("Validating data in selected range")
            
            # Pass the reference row index to validation if specified
            self.validate_data(data, row_indices, ref_row_idx)
            
            # Get reference point coordinates if using a reference row
            reference_point = None
            if ref_row_idx is not None:
                ref_data = data.iloc[ref_row_idx]
                reference_point = (ref_data['Xnorm'], ref_data['Ynorm'], ref_data['Znorm'])
                self.logger.info(f"Using reference point from row {ref_row}: ({reference_point[0]:.4f}, {reference_point[1]:.4f}, {reference_point[2]:.4f})")
            
            # Find the ∆E column index
            header_row = 0  # Header is in row 0 (first row)
            delta_e_col_idx = None
            
            for col_idx in range(len(sheet.row(header_row))):
                cell_value = sheet[header_row, col_idx].value
                if cell_value == '∆E':
                    delta_e_col_idx = col_idx
                    break
                    
            if delta_e_col_idx is None:
                self.logger.error("∆E column not found in spreadsheet")
                raise ValueError("∆E column not found in spreadsheet")
                
            self.logger.info(f"Found ∆E column at index {delta_e_col_idx}")
            
            # Calculate ∆E for each row and update the spreadsheet
            subset = data.iloc[row_indices]
            self.logger.info(f"Calculating ∆E for {len(subset)} rows")
            
            # Track successful updates
            updates = []
            
            # Process each row
            for i, (idx, row) in enumerate(subset.iterrows()):
                try:
                    # Skip completely blank rows
                    if row[['Xnorm', 'Ynorm', 'Znorm']].isna().all():
                        self.logger.debug(f"Skipping blank row {idx+2}")
                        continue
                        
                    # Skip rows with missing coordinate data
                    if row[['Xnorm', 'Ynorm', 'Znorm']].isna().any():
                        self.logger.debug(f"Skipping row {idx+2} due to missing coordinates")
                        continue
                    
                    # Get point coordinates
                    point_xyz = (row['Xnorm'], row['Ynorm'], row['Znorm'])
                    
                    # Get second point coordinates - either from reference row or centroid values
                    if ref_row_idx is not None:
                        # Use reference point coordinates directly
                        if reference_point is None:
                            self.logger.error("Reference point coordinates are missing")
                            raise ValueError(f"Reference row {ref_row} is missing coordinate values")
                        second_point = reference_point
                    else:
                        # Use this row's own centroid values
                        if row[['Centroid_X', 'Centroid_Y', 'Centroid_Z']].isna().any():
                            self.logger.debug(f"Skipping row {idx+2} due to missing centroid values")
                            continue
                        second_point = (row['Centroid_X'], row['Centroid_Y'], row['Centroid_Z'])
                    
                    # Convert to Lab
                    point_lab = self.xyz_to_lab(*point_xyz)
                    second_point_lab = self.xyz_to_lab(*second_point)
                    
                    # Calculate ∆E CIE2000
                    delta_e = self.calculate_delta_e_2000(point_lab, second_point_lab)
                    
                    # Round to 2 decimal places
                    delta_e = round(delta_e, 2)
                    
                    # Update the ∆E column in the spreadsheet (1-based row indexing)
                    sheet_row_idx = idx + 2  # Add 2 to convert from 0-based DataFrame index to 1-based sheet row
                    
                    # Update ∆E cell
                    cell = sheet[sheet_row_idx, delta_e_col_idx]
                    cell.set_value(delta_e)
                    
                    updates.append(sheet_row_idx)
                    
                    # Log progress every 10 rows
                    if (i + 1) % 10 == 0 or i == len(subset) - 1:
                        self.logger.info(f"Processed {i + 1}/{len(subset)} rows")
                        
                except Exception as e:
                    self.logger.error(f"Error processing row {idx + 2}: {e}")
                    # Continue with the next row
            
            # Save the updated file
            if updates:
                try:
                    self.logger.info(f"Saving updates for {len(updates)} rows")
                    
                    # Create a backup before saving
                    backup_path = f"{self.file_path}.bak"
                    self.logger.info(f"Creating backup at: {backup_path}")
                    import shutil
                    shutil.copy2(self.file_path, backup_path)
                    
                    # Save to a temporary file first
                    temp_path = f"{self.file_path}.new"
                    ods_doc.saveas(temp_path)
                    
                    # Close document
                    del ods_doc
                    
                    # Replace original with new file
                    os.replace(temp_path, self.file_path)
                    
                    # Clean up backup file
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                        
                    # Show success message
                    messagebox.showinfo("Success", 
                                      f"Successfully calculated and updated ΔE values for {len(updates)} rows.\n\n"
                                      f"Row range: {start_row}-{end_row}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to save updates: {e}")
                    
                    # Attempt to restore from backup if save failed
                    if os.path.exists(backup_path):
                        try:
                            self.logger.info("Restoring from backup")
                            os.replace(backup_path, self.file_path)
                            messagebox.showwarning("Save Failed", 
                                               f"Failed to save updates: {e}\n\nRestored file from backup.")
                        except Exception as restore_error:
                            self.logger.error(f"Failed to restore from backup: {restore_error}")
                            messagebox.showerror("Error", 
                                              f"Failed to save updates AND restore from backup.\n\n"
                                              f"Original error: {e}\n\nRestore error: {restore_error}")
                    else:
                        messagebox.showerror("Save Failed", f"Failed to save updates: {e}")
            else:
                self.logger.warning("No updates made")
                messagebox.showinfo("No Updates", "No ΔE values were calculated or updated.")
                
        except ValueError as ve:
            self.logger.error(f"Validation error: {ve}")
            messagebox.showerror("Validation Error", str(ve))
        except Exception as e:
            self.logger.error(f"Error calculating ΔE: {e}")
            messagebox.showerror("Error", f"An error occurred while calculating ΔE:\n\n{e}")
    
    def create_gui(self, parent):
        """Create the ΔE calculation control panel."""
        if parent is None:
            self.logger.error("Parent widget is None, cannot create GUI components")
            raise ValueError("Parent widget cannot be None")
            
        # Create a frame for ΔE controls
        self.frame = tk.LabelFrame(parent, text="ΔE CIE2000", padx=2, pady=1)
        
        # Create a single row for all controls
        control_frame = tk.Frame(self.frame)
        control_frame.pack(fill=tk.X, pady=1)
        
        # Row range inputs in a compact layout
        tk.Label(control_frame, text="Rows:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.start_row_entry = tk.Entry(control_frame, width=3)
        self.start_row_entry.insert(0, "2")
        self.start_row_entry.pack(side=tk.LEFT, padx=1)
        tk.Label(control_frame, text="-").pack(side=tk.LEFT)
        self.end_row_entry = tk.Entry(control_frame, width=3)
        self.end_row_entry.insert(0, "999")
        self.end_row_entry.pack(side=tk.LEFT, padx=1)
        
        # Reference row input
        tk.Label(control_frame, text="Ref Row:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(5,0))
        self.ref_row_entry = tk.Entry(control_frame, width=3)
        self.ref_row_entry.pack(side=tk.LEFT, padx=1)
        
        # Calculate button
        self.calculate_button = tk.Button(
            control_frame, 
            text="Calculate", 
            command=self._calculate_button_clicked,
            font=("Arial", 9)
        )
        self.calculate_button.pack(side=tk.LEFT, padx=1)
        
        # Help button
        help_button = tk.Button(
            control_frame, 
            text="?", 
            command=self._show_help,
            font=("Arial", 9), 
            width=1, 
            bg="lightblue"
        )
        help_button.pack(side=tk.LEFT, padx=2)
        
        self.logger.info("ΔE GUI components created successfully")
        return self.frame
    
    def _calculate_button_clicked(self):
        """Handle Calculate button click."""
        try:
            # Disable the button to prevent multiple clicks
            self.calculate_button.config(state=tk.DISABLED)
            self.calculate_button.update()
            
            # Show progress indication
            self.calculate_button.config(text="Working...")
            self.calculate_button.update()
            
            # Get row range from inputs
            try:
                start_row = int(self.start_row_entry.get())
                end_row = int(self.end_row_entry.get())
                
                # Get reference row if provided
                ref_row = None
                if self.ref_row_entry.get().strip():
                    ref_row = int(self.ref_row_entry.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Row values must be integers.")
                return
            finally:
                # Restore button state
                self.calculate_button.config(text="Calculate", state=tk.NORMAL)
            
            # Run calculation
            self.calculate_delta_e(start_row, end_row, ref_row)
            
        except Exception as e:
            self.logger.error(f"Error in calculate button handler: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            # Ensure button is restored
            if self.calculate_button and self.calculate_button.winfo_exists():
                self.calculate_button.config(text="Calculate", state=tk.NORMAL)
    
    def _show_help(self):
        """Display help information about ΔE calculation."""
        help_msg = (
            "ΔE CIE2000 Color Difference Calculator\n\n"
            "This tool calculates the perceived color difference between normalized points "
            "and their cluster centroids using the ΔE CIE2000 formula.\n\n"
            "Usage:\n"
            "1. Enter the row range to process (first data row is 2)\n"
            "2. Optional: Enter a reference row number to use its centroid values\n"
            "   (leave empty to use each row's own centroid values)\n"
            "3. Click 'Calculate' to compute ΔE values\n"
            "4. Values will be saved to the '∆E' column\n\n"
            "Requirements:\n"
            "• Data must be normalized (0.0-1.0 range)\n"
            "• Required columns: Xnorm, Ynorm, Znorm, Centroid_X/Y/Z, ∆E\n"
            "• All rows need valid Xnorm, Ynorm, Znorm values\n"
            "• If using a reference row, only that row needs valid centroid values\n\n"
            "Notes:\n"
            "• While designed for Lab color space, this calculator works\n"
            "  with RGB normalized data too, providing useful relative differences\n"
            "• Only the ∆E column will be modified; all other data is preserved\n"
            "• ΔE scale: 0-1 = not perceptible, 1-2 = perceptible by close observation,\n"
            "  2-10 = perceptible at a glance, 10-50 = colors are more similar than opposite"
        )
        messagebox.showinfo("ΔE Calculator Help", help_msg)
