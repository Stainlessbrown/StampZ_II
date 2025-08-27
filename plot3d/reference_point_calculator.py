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
import shutil
import tempfile
import traceback
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple, Any, Union, Generator

class ReferencePointCalculator:
    """
    Calculator class for computing ΔE CIE2000 color differences between normalized points
    and a reference point specified by row number.
    
    This calculator uses the same CIE2000 formula as the DeltaECalculator but doesn't 
    rely on K-means clustering. Instead, it uses a single reference point specified by row number
    and calculates Delta E values against this reference point.
    """
    
    # Define expected column structure
    EXPECTED_COLUMNS = ['Xnorm', 'Ynorm', 'Znorm', 'DataID', 'Cluster', '∆E', 'Marker',
                     'Color', 'Sphere', 'Centroid_X', 'Centroid_Y', 'Centroid_Z']
    
    # Define critical columns that must be present
    CRITICAL_COLUMNS = ['Xnorm', 'Ynorm', 'Znorm', 'Centroid_X', 'Centroid_Y', 'Centroid_Z', '∆E']
    
    # Define file operation configurations
    MAX_RETRIES = 3        # Maximum retry attempts for file operations
    RETRY_DELAY = 1        # Seconds between retry attempts
    LOCK_TIMEOUT = 5       # Seconds to wait for a file lock
    
    # Emergency recovery configuration
    EMERGENCY_MODE = True  # Enable emergency recovery by default
    FILE_SIZE_THRESHOLD = 0.5  # Size ratio threshold for detecting file corruption (e.g., 0.5 means main file < 50% of backup size is suspicious)
    MIN_FILE_SIZE = 1024   # Minimum file size in bytes (files smaller than this are likely corrupted)
    MAX_RECOVERY_ATTEMPTS = 3  # Maximum attempts for emergency recovery
    
    # Reference white point for XYZ to L*a*b* conversion
    # For normalized values in 0-1 range, use these reference values
    REF_WHITE_X = 1.0
    REF_WHITE_Y = 1.0
    REF_WHITE_Z = 1.0
    
    def __init__(self, logger=None):
        """Initialize the ReferencePointCalculator with proper logging."""
        # Set up logger
        if logger is None:
            # Create our own logger
            self.logger = logging.getLogger("ReferencePointCalculator")
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
        self.file_path = None
        
        # Reference point data
        self.reference_point_row = 2  # Default to row 2 (first data row)
        self.reference_coordinates = None
        
        # File state tracking
        self.last_backup_path = None
        self.is_file_valid = False
        self.column_validation_passed = False
        self.data_validation_passed = False
        
        # Emergency recovery tracking
        self.recovery_attempts = 0
        self.last_recovery_time = None
        self.recovery_logs = []
        self.performed_emergency_recovery = False
        
        self.logger.info("ReferencePointCalculator initialized successfully")
    
    def debug_data(self, dataframe: pd.DataFrame) -> None:
        """
        Debug helper to analyze DataFrame structure and contents.
        Logs detailed information about the DataFrame.
        """
        if dataframe is None:
            self.logger.error("Cannot debug None DataFrame")
            return
            
        # Log DataFrame basic info
        self.logger.info(f"DataFrame debug information:")
        self.logger.info(f"  Shape: {dataframe.shape}")
        self.logger.info(f"  Memory usage: {dataframe.memory_usage().sum() / 1024:.2f} KB")
        
        # Log column information
        self.logger.info(f"  Columns: {sorted(dataframe.columns.tolist())}")
        
        # Log data types
        dtype_info = []
        for col, dtype in dataframe.dtypes.items():
            dtype_info.append(f"{col}: {dtype}")
        self.logger.info(f"  Data types: {', '.join(dtype_info)}")
        
        # Check for null values in critical columns
        critical_cols = ['Xnorm', 'Ynorm', 'Znorm', 'Centroid_X', 'Centroid_Y', 'Centroid_Z', '∆E']
        for col in critical_cols:
            if col in dataframe.columns:
                null_count = dataframe[col].isna().sum()
                total_count = len(dataframe)
                self.logger.info(f"  Null values in {col}: {null_count}/{total_count} ({null_count/total_count*100:.1f}%)")

        # Check value ranges for normalized columns
        norm_cols = ['Xnorm', 'Ynorm', 'Znorm']
        for col in norm_cols:
            if col in dataframe.columns:
                non_null_data = dataframe[col].dropna()
                if len(non_null_data) > 0:
                    min_val = non_null_data.min()
                    max_val = non_null_data.max()
                    mean_val = non_null_data.mean()
                    self.logger.info(f"  {col} range: min={min_val:.4f}, max={max_val:.4f}, mean={mean_val:.4f}")
                    
                    # Flag values outside expected 0-1 range for normalized data
                    outside_range = ((non_null_data < 0) | (non_null_data > 1)).sum()
                    if outside_range > 0:
                        self.logger.warning(f"  WARNING: {outside_range} values in {col} are outside expected 0-1 range")
        
        # Log first few rows as sample
        if len(dataframe) > 0:
            sample_size = min(3, len(dataframe))
            self.logger.info(f"  Sample data (first {sample_size} rows):")
            for i in range(sample_size):
                row = dataframe.iloc[i]
                self.logger.info(f"  Row {i+1}:")
                for col in ['Xnorm', 'Ynorm', 'Znorm', 'Centroid_X', 'Centroid_Y', 'Centroid_Z']:
                    if col in row.index:
                        if pd.notna(row[col]):
                            self.logger.info(f"    {col}: {row[col]}")
                        else:
                            self.logger.info(f"    {col}: NULL")

    @contextmanager
    def safe_file_access(self, file_path: str, mode: str = 'r') -> Generator:
        """
        Context manager for safe file access with proper locking.
        
        Args:
            file_path: Path to the file to access
            mode: File open mode ('r', 'w', etc.)
            
        Yields:
            The opened file object with appropriate locks
        """
        lock_path = f"{file_path}.lock"
        lockfile = None
        f = None
        
        try:
            # Create lock file
            self.logger.info(f"Attempting to acquire lock: {lock_path}")
            
            # Try to acquire lock with timeout
            start_time = time.time()
            while time.time() - start_time < self.LOCK_TIMEOUT:
                try:
                    lockfile = open(lock_path, 'w+')
                    fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.logger.info("Lock acquired successfully")
                    break
                except (IOError, OSError) as e:
                    if e.errno == errno.EACCES or e.errno == errno.EAGAIN:
                        self.logger.warning(f"File is locked, waiting...")
                        time.sleep(0.5)
                    else:
                        raise
            else:
                raise TimeoutError(f"Could not acquire lock on {lock_path} after {self.LOCK_TIMEOUT} seconds")
            
            # Open the requested file now that we have the lock
            f = open(file_path, mode)
            yield f
            
        except Exception as e:
            self.logger.error(f"Error in safe_file_access: {e}")
            raise
        finally:
            # Always clean up resources
            if f:
                try:
                    f.close()
                except Exception as e:
                    self.logger.warning(f"Error closing file: {e}")
            
            if lockfile:
                try:
                    fcntl.flock(lockfile, fcntl.LOCK_UN)
                    lockfile.close()
                    os.remove(lock_path)
                    self.logger.info("Lock released and removed")
                except Exception as e:
                    self.logger.warning(f"Error releasing lock: {e}")

    def check_file_validity(self, file_path: str) -> bool:
        """
        Verify that the file exists, is accessible, and has valid data.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file is valid, False otherwise
        """
        # Check if file exists
        if not os.path.exists(file_path):
            self.logger.error(f"File does not exist: {file_path}")
            return False
            
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            self.logger.error(f"File is not readable: {file_path}")
            return False
            
        # Check if file is writable (needed for saving results)
        if not os.access(file_path, os.W_OK):
            self.logger.error(f"File is not writable: {file_path}")
            return False
            
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            self.logger.error(f"File is empty: {file_path}")
            return False
        elif file_size < self.MIN_FILE_SIZE:
            self.logger.error(f"File is suspiciously small ({file_size} bytes): {file_path}")
            return False
        
        # Check if it's a valid ODS file by attempting to open it
        try:
            doc = ezodf.opendoc(file_path)
            if not doc.sheets:
                self.logger.error(f"File has no sheets: {file_path}")
                return False
            
            # Check first sheet for content
            sheet = doc.sheets[0]
            if len(sheet.rows()) < 2:  # Need at least header + 1 data row
                self.logger.error(f"Sheet has insufficient data (fewer than 2 rows): {file_path}")
                return False
                
            self.logger.info(f"File validation passed: {file_path} (size: {file_size} bytes)")
            return True
        except Exception as e:
            self.logger.error(f"Error validating ODS file: {e}")
            return False
    
    def emergency_file_check(self, file_path: str) -> bool:
        """
        Perform emergency validation of file integrity, comparing file sizes
        between main and backup files to detect corruption.
        
        Args:
            file_path: Path to the main file
            
        Returns:
            bool: True if file is valid, False if corruption detected
        """
        self.logger.info("===== EMERGENCY FILE INTEGRITY CHECK =====")
        
        # Check if file exists and has minimum size
        basic_valid = self.check_file_validity(file_path)
        if not basic_valid:
            self.logger.error("Basic file validity check failed")
            self._log_recovery_event("EMERGENCY_CHECK_FAILED", 
                                    f"File failed basic validity check: {file_path}")
            return False
        
        backup_path = f"{file_path}.bak"
        
        # Check if backup exists
        if not os.path.exists(backup_path):
            self.logger.info(f"No backup file found at {backup_path}, skipping size comparison")
            self._log_recovery_event("NO_BACKUP", f"No backup file found: {backup_path}")
            
            # Try creating a backup if none exists
            try:
                # Create a backup if file seems valid
                if os.path.getsize(file_path) > self.MIN_FILE_SIZE:
                    shutil.copy2(file_path, backup_path)
                    self.logger.info(f"Created new backup file: {backup_path}")
                    self._log_recovery_event("BACKUP_CREATED", f"Created new backup: {backup_path}")
            except Exception as e:
                self.logger.error(f"Error creating backup: {e}")
                
            return basic_valid
        
        # Compare file sizes
        main_size = os.path.getsize(file_path)
        backup_size = os.path.getsize(backup_path)
        
        self.logger.info(f"File size: {main_size} bytes, Backup size: {backup_size} bytes")
        
        # If backup is significantly larger than main file, it suggests corruption
        if main_size > 0 and backup_size > 0:
            size_ratio = main_size / backup_size
            self.logger.info(f"File size ratio (main/backup): {size_ratio:.2f}")
            
            if size_ratio < self.FILE_SIZE_THRESHOLD:
                self.logger.error(f"POTENTIAL CORRUPTION DETECTED: Main file ({main_size} bytes) is "
                                 f"significantly smaller than backup ({backup_size} bytes)")
                self._log_recovery_event("SIZE_MISMATCH", 
                                       f"File size ratio {size_ratio:.2f} below threshold {self.FILE_SIZE_THRESHOLD}")
                return False
                
        # Check if we can open the file
        try:
            doc = ezodf.opendoc(file_path)
            sheet_count = len(doc.sheets)
            if sheet_count == 0:
                self.logger.error("File contains no sheets")
                self._log_recovery_event("NO_SHEETS", f"File contains no sheets: {file_path}")
                return False
                
            # Check content validity
            sheet = doc.sheets[0]
            row_count = len(sheet.rows())
            col_count = len(sheet.column_dimensions)
            
            self.logger.info(f"File contains {sheet_count} sheet(s), {row_count} rows, {col_count} columns")
            
            if row_count < 2:  # Need at least a header row and one data row
                self.logger.error(f"File contains insufficient data (only {row_count} rows)")
                self._log_recovery_event("INSUFFICIENT_DATA", f"File contains only {row_count} rows")
                return False
                
            # Check header row
            header_row = sheet.rows()[0]
            header_values = [cell.value for cell in header_row if cell.value]
            
            # Check for critical headers
            critical_found = [col for col in self.CRITICAL_COLUMNS if col in header_values]
            self.logger.info(f"Found {len(critical_found)}/{len(self.CRITICAL_COLUMNS)} critical columns")
            
            if len(critical_found) < len(self.CRITICAL_COLUMNS) / 2:  # At least half should be present
                self.logger.error(f"File is missing most critical columns. Found: {critical_found}")
                self._log_recovery_event("MISSING_COLUMNS", 
                                       f"File missing critical columns: {[c for c in self.CRITICAL_COLUMNS if c not in critical_found]}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating file content: {e}")
            self._log_recovery_event("VALIDATION_ERROR", f"Error: {str(e)}")
            return False
            
        self.logger.info("File passed emergency integrity check")
        self._log_recovery_event("CHECK_PASSED", f"File integrity verified: {file_path}")
        return True

    def _log_recovery_event(self, event_type: str, details: str):
        """
        Log a recovery event for tracking purposes.
        
        Args:
            event_type: Type of recovery event
            details: Details about the event
        """
        timestamp = time.time()
        event = {
            "timestamp": timestamp,
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
            "event": event_type,
            "details": details
        }
        self.recovery_logs.append(event)
        self.logger.info(f"RECOVERY LOG: [{event_type}] {details}")

    def detect_and_recover_from_backup(self, file_path: str) -> bool:
        """
        Check for backup files and recover if needed.
        
        Args:
            file_path: Path to the main file
            
        Returns:
            bool: True if recovery was successful or not needed, False if recovery failed
        """
        self.logger.info("===== BACKUP DETECTION AND RECOVERY =====")
        backup_path = f"{file_path}.bak"
        temp_path = f"{file_path}.tmp"
            
        # Main file is invalid, check for backup
        if os.path.exists(backup_path):
            backup_valid = self.check_file_validity(backup_path)
            
            if backup_valid:
                self.logger.info(f"Found valid backup file: {backup_path}")
                
                try:
                    # Create a safety backup of the current file before replacing
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        safety_backup = f"{file_path}.corrupted"
                        shutil.copy2(file_path, safety_backup)
                        self.logger.info(f"Created safety backup of corrupted file: {safety_backup}")
                    
                    # Copy backup to main file
                    shutil.copy2(backup_path, file_path)
                    self.logger.info(f"Successfully restored from backup: {backup_path} -> {file_path}")
                    
                    # Verify the restored file
                    if self.check_file_validity(file_path):
                        self.logger.info("Restored file validation passed")
                        return True
                    else:
                        self.logger.error("Restored file validation failed")
                        return False
                except Exception as e:
                    self.logger.error(f"Error restoring from backup: {e}")
                    return False
            else:
                self.logger.error(f"Backup file exists but is invalid: {backup_path}")
        else:
            self.logger.error(f"No backup file found: {backup_path}")
            
        # Check for temp file as last resort
        if os.path.exists(temp_path):
            temp_valid = self.check_file_validity(temp_path)
            
            if temp_valid:
                self.logger.info(f"Found valid temp file: {temp_path}")
                
                try:
                    # Create a safety backup of the current file before replacing
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        safety_backup = f"{file_path}.corrupted"
                        shutil.copy2(file_path, safety_backup)
                        self.logger.info(f"Created safety backup of corrupted file: {safety_backup}")
                    
                    # Copy temp file to main file
                    shutil.copy2(temp_path, file_path)
                    self.logger.info(f"Successfully restored from temp file: {temp_path} -> {file_path}")
                    
                    # Verify the restored file
                    if self.check_file_validity(file_path):
                        self.logger.info("Restored file validation passed")
                        return True
                    else:
                        self.logger.error("Restored file validation failed")
                        return False
                except Exception as e:
                    self.logger.error(f"Error restoring from temp file: {e}")
                    return False
            else:
                self.logger.error(f"Temp file exists but is invalid: {temp_path}")
                
        return False

    def load_data(self, dataframe: pd.DataFrame) -> None:
        """Load data into the calculator."""
        if dataframe is None:
            self.logger.error("Received None DataFrame - Data loading failed")
            self.data = None
            self.data_validation_passed = False
            return
            
        # Get basic DataFrame info
        self.logger.info(f"Loading DataFrame with shape {dataframe.shape}")
        row_count = len(dataframe)
        column_count = len(dataframe.columns)
        self.logger.info(f"DataFrame contains {row_count} rows and {column_count} columns")
        
        # Log data quality info
        null_counts = dataframe.isna().sum().sum()
        self.logger.info(f"Total null values in DataFrame: {null_counts}")
        
        # Log all columns found in the dataframe for debugging
        self.logger.info(f"DataFrame contains columns: {sorted(dataframe.columns.tolist())}")
        
        # Create case-insensitive column mapping
        column_map = {}
        for col in dataframe.columns:
            column_map[col.lower()] = col
        
        # Provide schema analysis
        expected_cols_lower = [col.lower() for col in self.EXPECTED_COLUMNS]
        found_cols_lower = [col.lower() for col in dataframe.columns]
        common_cols = set(expected_cols_lower).intersection(set(found_cols_lower))
        self.logger.info(f"Found {len(common_cols)}/{len(self.EXPECTED_COLUMNS)} expected columns (case-insensitive)")
            
        # Check for required columns with case-insensitive matching
        missing_columns = []
        
        for expected_col in self.EXPECTED_COLUMNS:
            if expected_col in dataframe.columns:
                # Column exists with exact name
                continue
            elif expected_col.lower() in column_map:
                # Column exists with different case
                actual_col = column_map[expected_col.lower()]
                self.logger.info(f"Case mismatch: Found '{actual_col}' matching expected '{expected_col}'")
            else:
                # Column is missing
                missing_columns.append(expected_col)
        
        # Handle missing columns with enhanced diagnostics
        if missing_columns:
            # Provide more specific error information for critical columns
            critical_cols = ['Xnorm', 'Ynorm', 'Znorm', 'Centroid_X', 'Centroid_Y', 'Centroid_Z', '∆E']
            critical_missing = [col for col in missing_columns if col in critical_cols]
            
            error_msg = f"DataFrame is missing required columns: {missing_columns}"
            
            # Enhanced diagnostic info
            if critical_missing:
                self.logger.error(f"CRITICAL COLUMNS MISSING: {critical_missing}")
                error_msg += f"\n\nMissing critical columns: {critical_missing}"
                error_msg += "\nThese columns are essential for calculations."
                
                if any(col in critical_missing for col in ['Centroid_X', 'Centroid_Y', 'Centroid_Z']):
                    error_msg += "\n\nCentroid columns are required for reference point calculations."
                    error_msg += "\nPlease ensure these columns exist in your data file."
                
                if any(col in critical_missing for col in ['Xnorm', 'Ynorm', 'Znorm']):
                    error_msg += "\n\nNormalized coordinate columns (Xnorm, Ynorm, Znorm) are missing."
                    error_msg += "\nThese are required for color space calculations."
            
            # Debug the dataframe to help diagnose issues
            self.logger.error("Running DataFrame diagnostic to help identify issues:")
            self.debug_data(dataframe)
            
            self.logger.error(error_msg)
            self.column_validation_passed = False
            raise ValueError(error_msg)
        
        # Column validation has passed at this point
        self.column_validation_passed = True
        self.logger.info("Column validation successful - all required columns present")
        
        # Store the data
        self.data = dataframe.copy()
        self.logger.info(f"Loaded DataFrame with {len(dataframe)} rows")
        
        # Convert numeric columns to appropriate type
        numeric_columns = ['Xnorm', 'Ynorm', 'Znorm', 'Centroid_X', 'Centroid_Y', 'Centroid_Z', '∆E']
        for col in numeric_columns:
            if col in self.data.columns:
                try:
                    self.data[col] = pd.to_numeric(self.data[col], errors='coerce')
                    self.logger.info(f"Successfully converted {col} to numeric with {self.data[col].isna().sum()} NaN values")
                except Exception as e:
                    self.logger.error(f"Failed to convert {col} to numeric: {e}")
        
        # Check for centroid data in the dataframe
        centroid_cols = ['Centroid_X', 'Centroid_Y', 'Centroid_Z']
        if all(col in self.data.columns for col in centroid_cols):
            # Count rows with valid centroid data
            valid_centroid_mask = (
                self.data['Centroid_X'].notna() & 
                self.data['Centroid_Y'].notna() & 
                self.data['Centroid_Z'].notna()
            )
            valid_centroid_count = valid_centroid_mask.sum()
            self.logger.info(f"Found {valid_centroid_count} rows with valid centroid data")
        else:
            self.logger.warning("Missing centroid columns in the data")
    def set_file_path(self, file_path: str):
        """Set the current file path."""
        if not file_path:
            self.logger.error("Attempted to set empty file path")
            raise ValueError("File path cannot be empty")
                 
        self.file_path = os.path.abspath(file_path)
        self.logger.info(f"Set current file path to: {self.file_path}")

    def _safe_save_document(self, doc, file_path):
        """
        Helper method to safely save document with verification.
        Uses atomic operations to ensure data integrity.
        """
        temp_path = f"{file_path}.temp"
        try:
            # First save to temporary file
            self.logger.info(f"Saving to temporary file: {temp_path}")
            doc.saveas(temp_path)
            
            # Verify temp file exists and has content
            if not os.path.exists(temp_path):
                raise IOError("Temporary file save failed - file does not exist")
            if os.path.getsize(temp_path) == 0:
                raise IOError("Temporary file is empty")
                
            # Force sync the temporary file - use binary mode for better compatibility
            with open(temp_path, 'rb+') as f:
                f.flush()
                os.fsync(f.fileno())
            
            # Rename temp file to original (atomic operation)
            self.logger.info("Replacing original file with temp file")
            os.replace(temp_path, file_path)
            
            # Sync the directory to ensure rename is persisted - moved outside try block
            dir_fd = None
            try:
                dir_fd = os.open(os.path.dirname(file_path), os.O_RDONLY)
                os.fsync(dir_fd)
            except Exception as dir_sync_error:
                self.logger.warning(f"Directory sync warning (non-critical): {dir_sync_error}")
            finally:
                if dir_fd is not None:
                    try:
                        os.close(dir_fd)
                    except Exception as close_error:
                        self.logger.warning(f"Error closing directory handle: {close_error}")
                
            return True
        except Exception as e:
            self.logger.error(f"Safe save failed: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    self.logger.info(f"Removed temporary file after failed save")
                except Exception as rm_error:
                    self.logger.error(f"Failed to remove temp file: {rm_error}")
            return False
    
    
    def set_reference_point_row(self, row_num: int) -> bool:
        """
        Set the reference point row number.
        
        Args:
            row_num: 1-based row number to use as reference point
            
        Returns:
            bool: True if successful, False if reference point is invalid
        """
        if self.data is None:
            self.logger.error("No data loaded. Call load_data() first.")
            return False
        
        # Convert 1-based row number to 0-based index
        index = row_num - 2  # Row 2 (first data row) corresponds to index 0
        
        if index < 0 or index >= len(self.data):
            self.logger.error(f"Invalid row number {row_num}, must be between 2 and {len(self.data) + 1}")
            return False
        
        # Check if the reference row has valid centroid data
        centroid_cols = ['Centroid_X', 'Centroid_Y', 'Centroid_Z']
        row = self.data.iloc[index]
        
        if any(pd.isna(row[col]) for col in centroid_cols):
            self.logger.error(f"Reference row {row_num} missing centroid data")
            return False
        
        # Store the reference point row number
        self.reference_point_row = row_num
        self.logger.info(f"Set reference point to row {row_num}")
        
        # Update reference coordinates
        self.reference_coordinates = (
            float(row['Centroid_X']),
            float(row['Centroid_Y']),
            float(row['Centroid_Z'])
        )
        
        self.logger.info(f"Reference coordinates: ({self.reference_coordinates[0]:.4f}, "
                        f"{self.reference_coordinates[1]:.4f}, {self.reference_coordinates[2]:.4f})")
        
        return True
    
    def get_reference_point_coordinates(self) -> Tuple[float, float, float]:
        """
        Get the reference point coordinates.
        
        Returns:
            Tuple of (Centroid_X, Centroid_Y, Centroid_Z) for the reference point
        """
        if self.reference_coordinates is None:
            self.logger.error("Reference point not set or has invalid coordinates")
            raise ValueError("Reference point not set or has invalid coordinates")
            
        return self.reference_coordinates
    
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
        """
        Get the correct row indices for the given range, including the end row.
        
        Args:
            start: 1-based start row number (where 2 is the first data row)
            end: 1-based end row number
        Returns:
            range object with 0-based indices including end row
        """
        # Validate and get proper bounds
        start, end = self.validate_row_range(start, end)
        
        # CRITICAL DEBUGGING: Print exact values received
        self.logger.info(f"_get_row_indices called with start={start}, end={end}")
        
        # Convert from 1-based (user visible) to 0-based (internal) indexing
        # Row 1 in the UI is the header row, Row 2 is the first data row
        df_start = start - 2  # Row 2 maps to index 0 (adjust for header)
        # For end, we need to convert to the proper 0-based index
        df_end = end - 2      # Same adjustment for end row
        
        # Add debug logging
        self.logger.info(f"Converting UI rows {start}-{end} to DataFrame indices {df_start}-{df_end}")
        
        # Calculate actual data bounds to ensure we're not out of range
        if self.data is not None:
            max_row_index = len(self.data) - 1
            if df_end > max_row_index:
                self.logger.warning(f"End index {df_end} exceeds data bounds, adjusting to {max_row_index}")
                df_end = min(df_end, max_row_index)
        
        # Log the conversion for debugging
        self.logger.info(f"Final row range: UI rows {start}-{end} map to DataFrame indices {df_start}-{df_end} (inclusive)")
        
        # Validate that the row range is not empty
        if df_start > df_end:
            self.logger.warning(f"Empty row range detected: {df_start}-{df_end}")
            # Ensure at least one row is included to prevent empty ranges
            df_end = df_start
        
        # Create a range of indices from start to end (inclusive)
        row_indices = range(df_start, df_end + 1)
        
        # Additional verification logging
        self.logger.info(f"Generated {len(row_indices)} row indices starting with {row_indices[0] if len(row_indices) > 0 else 'N/A'}")
        
        return row_indices
    
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

    def create_gui(self, parent):
        """Create the Reference Point ΔE calculation control panel."""
        if parent is None:
            self.logger.error("Parent widget is None, cannot create GUI components")
            raise ValueError("Parent widget cannot be None")
            
        # Store the parent widget for later reference
        self.parent = parent
            
        # Create a frame for Reference Point ΔE controls
        try:
            self.frame = tk.LabelFrame(parent, text="Reference Point ΔE", padx=2, pady=1)
            
            # Create a frame for all controls
            control_frame = tk.Frame(self.frame)
            control_frame.pack(fill=tk.X, pady=1)
            
            # Reference point row input
            tk.Label(control_frame, text="Ref Row:", font=("Arial", 9)).pack(side=tk.LEFT)
            self.reference_row = tk.Entry(control_frame, width=3)
            self.reference_row.insert(0, "2")  # Default to first data row
            self.reference_row.pack(side=tk.LEFT, padx=1)
            
            # Row range inputs in a compact layout
            tk.Label(control_frame, text="Rows:", font=("Arial", 9)).pack(side=tk.LEFT)
            self.start_row = tk.Entry(control_frame, width=3)
            self.start_row.insert(0, "2")
            self.start_row.pack(side=tk.LEFT, padx=1)
            tk.Label(control_frame, text="-").pack(side=tk.LEFT)
            self.end_row = tk.Entry(control_frame, width=3)
            self.end_row.insert(0, "999")
            self.end_row.pack(side=tk.LEFT, padx=1)
            
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
            
            self.logger.info("Reference Point ΔE GUI components created successfully")
            return self.frame
            
        except Exception as e:
            self.logger.error(f"Error creating GUI components: {str(e)}")
            raise ValueError(f"Failed to create GUI components: {str(e)}")
    
    def _calculate_button_clicked(self):
        """Handle Calculate button click."""
        try:
            # Disable the button to prevent multiple clicks
            self.calculate_button.config(state=tk.DISABLED)
            self.calculate_button.update()
            
            # Show progress indication
            self.calculate_button.config(text="Working...")
            self.calculate_button.update()
            
            # Get reference row
            try:
                ref_row = int(self.reference_row.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Reference row must be an integer.")
                return
            finally:
                # Restore button state
                self.calculate_button.config(text="Calculate", state=tk.NORMAL)
            
            # Get start and end rows
            try:
                start_row = int(self.start_row.get())
                end_row = int(self.end_row.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Row values must be integers.")
                return
            
            # Set the reference point
            if not self.set_reference_point_row(ref_row):
                messagebox.showerror(
                    "Invalid Reference Row", 
                    f"Row {ref_row} does not have valid centroid data.\n\n"
                    "Please select a row with valid Centroid_X/Y/Z values."
                )
                return
            
            # Run calculation
            self.calculate_and_save_delta_e(start_row, end_row)
            
        except Exception as e:
            self.logger.error(f"Error in calculate button handler: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            # Ensure button is restored
            if self.calculate_button and self.calculate_button.winfo_exists():
                self.calculate_button.config(text="Calculate", state=tk.NORMAL)
    
    def _show_help(self):
        """Display help information about Reference Point ΔE calculation."""
        help_msg = (
            "Reference Point ΔE Color Difference Calculator\n\n"
            "This tool calculates the perceived color difference between points "
            "and a single reference point using the ΔE CIE2000 formula.\n\n"
            "Usage:\n"
            "1. Enter the row number for the reference point (must have valid Centroid_X/Y/Z data)\n"
            "2. Enter the row range to process (first data row is 2)\n"
            "3. Click 'Calculate' to compute ΔE values\n"
            "4. Values will be saved to the '∆E' column\n\n"
            "Requirements:\n"
            "• Data must be normalized (0.0-1.0 range)\n"
            "• Required columns: Xnorm, Ynorm, Znorm, Centroid_X/Y/Z, ∆E\n"
            "• Reference point must have valid centroid data\n\n"
            "Notes:\n"
            "• ΔE values measure the perceptual color difference\n"
            "• Lower values mean colors are more similar\n"
            "• ΔE < 1.0 is generally not perceivable by human eye\n"
            "• The calculation uses the ΔE CIE2000 formula which accounts for\n"
            "  human perception differences in various color regions"
        )
        
        # Show help message
        messagebox.showinfo("Reference Point ΔE Help", help_msg)

    def calculate_and_save_delta_e(self, start_row: int, end_row: int):
        """
        Calculate and save Delta E values for the specified row range.
        
        Args:
            start_row: 1-based start row number (where 2 is the first data row)
            end_row: 1-based end row number
        """
        if self.file_path is None:
            self.logger.error("No file path set")
            raise ValueError("No file path set. Call set_file_path() first.")
            
        if not os.path.exists(self.file_path):
            self.logger.error(f"File not found: {self.file_path}")
            raise ValueError(f"File not found: {self.file_path}")
        
        # Ensure reference coordinates are available
        if self.reference_coordinates is None:
            self.logger.error("Reference point coordinates not available")
            raise ValueError("Reference point coordinates not available. Please set a valid reference point.")
        
        # Confirm with user
        confirmation = messagebox.askokcancel(
            "Calculate ΔE", 
            f"Calculate ΔE values for rows {start_row}-{end_row} using reference row {self.reference_point_row}?\n\n"
            "ONLY the ΔE column will be updated, all other data will be preserved."
        )
        
        if not confirmation:
            self.logger.info("Operation cancelled by user")
            return
        
        lockfile = None
        lock_path = f"{self.file_path}.lock"
        ods_doc = None
        sheet = None
        
        try:
            # Create and acquire lock file to prevent concurrent access
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
            
            # Get the rows we're working with
            row_indices = list(self._get_row_indices(start_row, end_row))
            self.logger.info(f"Processing row indices: {row_indices}")
            self.logger.info(f"Number of rows to process: {len(row_indices)}")
            
            # Get data for our selected range WITHOUT resetting indices
            subset_data = self.data.iloc[row_indices].copy()
            
            # Create mapping from DataFrame index to sheet row
            df_idx_to_sheet_row = {}
            for i, idx in enumerate(row_indices):
                # Use direct position-based mapping for consistent row handling
                sheet_row = start_row + i  # Direct position-based mapping
                df_idx_to_sheet_row[idx] = sheet_row
                
                if i < 3:  # Log first few mappings for verification
                    self.logger.info(f"Row mapping {i}: DataFrame idx {idx} → Sheet row {sheet_row}")
            
            self.logger.info(f"First selected row_indices value: {row_indices[0]}")
            self.logger.info(f"This will map to sheet row: {df_idx_to_sheet_row[row_indices[0]]}")
            self.logger.info(f"Got subset data with {len(subset_data)} rows")
            
            # Verify required columns exist
            required_columns = ['Xnorm', 'Ynorm', 'Znorm', '∆E']
            missing_columns = [col for col in required_columns if col not in self.data.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Create backup of original file
            backup_path = f"{self.file_path}.bak"
            self.logger.info(f"Creating backup at: {backup_path}")
            import shutil
            shutil.copy2(self.file_path, backup_path)
            self.logger.info(f"Backup created successfully")
            
            # Open the .ods file for editing
            self.logger.info("Opening .ods file for editing")
            ods_doc = ezodf.opendoc(self.file_path)
            sheet = ods_doc.sheets[0]
            
            # Find the ∆E column index - header is in row 1 (zero-based index 0)
            header_row = 0  # Zero-based index for header row
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
            
            # Get reference point coordinates
            ref_x, ref_y, ref_z = self.reference_coordinates
            self.logger.info(f"Using reference coordinates: ({ref_x:.4f}, {ref_y:.4f}, {ref_z:.4f})")
            
            # Convert reference coordinates to Lab
            # Convert reference coordinates to Lab
            ref_lab = self.xyz_to_lab(ref_x, ref_y, ref_z)
            self.logger.info(f"Reference Lab: L={ref_lab[0]:.2f}, a={ref_lab[1]:.2f}, b={ref_lab[2]:.2f}")
            
            # Calculate ∆E for each row and update the spreadsheet
            self.logger.info(f"Calculating ∆E for {len(subset_data)} rows")
            self.logger.info(f"Processing rows: Start={start_row}, End={end_row}")
            
            # Track successful updates
            updates = []
            
            # Process each row
            for i, (idx, row) in enumerate(subset_data.iterrows()):
                try:
                    # Check for blank row
                    if pd.isna(row['Xnorm']) and pd.isna(row['Ynorm']) and pd.isna(row['Znorm']):
                        continue
                        
                    # Get point coordinates
                    point_xyz = (row['Xnorm'], row['Ynorm'], row['Znorm'])
                    
                    # Check for invalid coordinates
                    if any(pd.isna(coord) for coord in point_xyz):
                        self.logger.warning(f"Row {idx+2}: Invalid coordinates, skipping")
                        continue
                    
                    # Convert to Lab
                    point_lab = self.xyz_to_lab(*point_xyz)
                    
                    # Calculate ∆E CIE2000
                    delta_e = self.calculate_delta_e_2000(point_lab, ref_lab)
                    
                    # Round to 2 decimal places
                    delta_e = round(delta_e, 2)
                    
                    # Log key information
                    self.logger.info(f"Row {idx+2}: Delta E = {delta_e:.2f}")
                    
                    # Calculate sheet row - use simple formula
                    sheet_row_idx = start_row + i - 1  # Adjust for zero-based indexing
                    
                    # Update ∆E cell
                    try:
                        sheet[sheet_row_idx, delta_e_col_idx].set_value(delta_e)
                        updates.append((sheet_row_idx, delta_e))
                    except Exception as cell_error:
                        self.logger.error(f"Error writing to cell at row {sheet_row_idx}: {cell_error}")
                        continue
                    
                    # Log progress every 10 rows
                    if (i + 1) % 10 == 0 or i == len(subset_data) - 1:
                        self.logger.info(f"Processed {i + 1}/{len(subset_data)} rows")
                
                except Exception as e:
                    self.logger.error(f"Error processing row {idx + 2}: {e}")
                    # Continue with the next row

            # Save the updated document
            if updates:
                self.logger.info(f"Saving updates for {len(updates)} rows")
                try:
                    # Save document
                    self.logger.info("Saving document")
                    ods_doc.save()
                    self.logger.info("Document saved successfully")
                
                    # Ensure document is closed properly
                    try:
                        self.logger.info("Closing document after save")
                        ods_doc.close()
                    except Exception as close_error:
                        self.logger.error(f"Error closing document: {close_error}")
                    
                    # Verify the save worked
                    verify_doc = None
                    try:
                        self.logger.info("Performing save verification")
                        verify_doc = ezodf.opendoc(self.file_path)
                        verify_sheet = verify_doc.sheets[0]
                        
                        # Check first few updates
                        check_count = min(5, len(updates))
                        self.logger.info(f"Verifying {check_count} rows")
                        
                        verification_passed = True
                        for i, (row_idx, expected_value) in enumerate(updates[:check_count]):
                            actual = verify_sheet[row_idx, delta_e_col_idx].value
                            
                            if actual is None:
                                self.logger.error(f"Verification failed - cell at row {row_idx} is empty")
                                verification_passed = False
                                break
                            elif abs(float(actual) - expected_value) > 0.01:
                                self.logger.error(f"Verification failed at row {row_idx}: expected {expected_value}, got {actual}")
                                verification_passed = False
                                break
                            
                            # Special logging for first row
                            if i == 0:
                                self.logger.info(f"First row verified: row={row_idx}, value={actual}")
                        
                        if verification_passed:
                            self.logger.info("Save verification successful")
                        else:
                            self.logger.error("Save verification failed")
                            # Keep the backup for potential recovery
                            messagebox.showwarning("Verification Issue", 
                                "There may have been an issue saving some values.\nA backup has been kept for safety.")
                    except Exception as verify_error:
                        self.logger.error(f"Save verification failed: {verify_error}")
                    finally:
                        # Always close verification document
                        if verify_doc is not None:
                            try:
                                verify_doc.close()
                                self.logger.info("Verification document closed")
                            except Exception as close_error:
                                self.logger.error(f"Error closing verification document: {close_error}")
                    
                    # Show success message
                    messagebox.showinfo("Success", 
                                      f"Successfully calculated and updated ΔE values for {len(updates)} rows.\n\n"
                                      f"Using reference point from row {self.reference_point_row}.\n"
                                      f"Row range: {start_row}-{end_row}")
                except ValueError as ve:
                    self.logger.error(f"Validation error: {ve}")
                    messagebox.showerror("Validation Error", str(ve))
                except Exception as e:
                    self.logger.error(f"Error calculating ΔE: {e}")
                    messagebox.showerror("Error", f"An error occurred while calculating ΔE:\n\n{e}")
                    
                    # Attempt to restore from backup if save failed
                    if os.path.exists(backup_path):
                        try:
                            self.logger.info("Restoring from backup")
                            shutil.copy2(backup_path, self.file_path)
                            messagebox.showwarning("Save Failed", 
                                           f"Failed to save updates: {e}\n\nRestored file from backup.")
                        except Exception as restore_error:
                            self.logger.error(f"Failed to restore from backup: {restore_error}")
                finally:
                    # Ensure document is properly closed if it exists
                    if 'ods_doc' in locals() and ods_doc is not None:
                        try:
                            ods_doc.close()
                            self.logger.info("Document closed in finally block")
                        except Exception as close_error:
                            self.logger.error(f"Error closing document: {close_error}")
            else:
                self.logger.warning("No updates made")
                messagebox.showinfo("No Updates", "No ΔE values were calculated or updated.")
                
        except Exception as e:
            self.logger.error(f"Error in calculate_and_save_delta_e: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
            # Log the full stack trace for better debugging
            self.logger.error(f"Full stack trace: {traceback.format_exc()}")
        finally:
            # Always release the lock, even if an error occurred
            if lockfile:
                self.logger.info("Releasing file lock")
                try:
                    fcntl.flock(lockfile, fcntl.LOCK_UN)
                    lockfile.close()
                    os.remove(lock_path)
                    self.logger.info("Lock file removed")
                except Exception as e:
                    self.logger.warning(f"Could not remove lock file: {e}")
