#!/usr/bin/env python3
"""
Direct Plot_3D Exporter

This module directly exports StampZ color analysis data to Plot_3D format by:
1. Copying the blank Plot3D_Template.ods file
2. Reading data directly from StampZ databases 
3. Inserting L*_norm, a*_norm, b*_norm, DataID into columns A-D starting at row 8
4. Saving with appropriate filename

This bypasses the intermediate StampZ export format and avoids column header issues.
"""

import os
import sys
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import ezodf
import time

class DirectPlot3DExporter:
    """Direct exporter from StampZ databases to Plot_3D format."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the direct exporter.
        
        Args:
            logger: Optional logger instance
        """
        if logger is None:
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger
            
        # Set up paths
        self._setup_paths()
        
        self.logger.info("DirectPlot3DExporter initialized")
    
    def _setup_paths(self):
        """Set up file paths for templates and data directories."""
        # Data directories - check environment variable first
        stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
        if stampz_data_dir:
            self.color_data_dir = os.path.join(stampz_data_dir, "data", "color_analysis")
            self.coordinates_db_path = os.path.join(stampz_data_dir, "coordinates.db")
            # Template path is now in data directory
            self.template_path = os.path.join(stampz_data_dir, "data", "templates", "plot3d", "Plot3D_Template.ods")
        else:
            # Development paths
            script_dir = os.path.dirname(os.path.dirname(__file__))
            self.color_data_dir = os.path.join(script_dir, "data", "color_analysis")
            self.coordinates_db_path = os.path.join(script_dir, "data", "coordinates.db")
            # Template path is now in data directory
            self.template_path = os.path.join(script_dir, "data", "templates", "plot3d", "Plot3D_Template.ods")
        
        self.logger.info(f"Template path: {self.template_path}")
        self.logger.info(f"Color data directory: {self.color_data_dir}")
    
    def get_available_sample_sets(self) -> List[str]:
        """Get list of available sample sets for export.
        
        Returns:
            List of sample set names
        """
        try:
            from utils.color_analysis_db import ColorAnalysisDB
            
            # Get all databases
            all_databases = ColorAnalysisDB.get_all_sample_set_databases(self.color_data_dir)
            
            # Extract base names (removing _averages suffix)
            sample_sets = set()
            for db_name in all_databases:
                if db_name.endswith('_averages'):
                    base_name = db_name[:-9]  # Remove '_averages'
                    sample_sets.add(base_name)
                else:
                    sample_sets.add(db_name)
            
            return sorted(sample_sets)
            
        except Exception as e:
            self.logger.error(f"Error getting sample sets: {e}")
            return []
    
    def get_sample_data(self, sample_set_name: str, use_averages: bool = False) -> List[Dict]:
        """Get color measurement data directly from StampZ database.
        
        Args:
            sample_set_name: Name of the sample set
            use_averages: If True, use averaged data; if False, use individual measurements
            
        Returns:
            List of data dictionaries with keys: L_norm, a_norm, b_norm, DataID
        """
        try:
            from utils.color_analysis_db import ColorAnalysisDB
            
            # Determine database name
            if use_averages:
                db_name = f"{sample_set_name}_averages"
            else:
                db_name = sample_set_name
            
            self.logger.info(f"Reading data from database: {db_name}")
            
            # Create ColorAnalysisDB instance - API only takes sample_set_name
            db = ColorAnalysisDB(sample_set_name=db_name)
            
            # Get measurements
            measurements = db.get_all_measurements()
            
            if not measurements:
                self.logger.warning(f"No measurements found for {db_name}")
                return []
            
            # Convert to Plot_3D format
            plot3d_data = []
            for measurement in measurements:
                # Skip Point 999 entries for individual measurements (these are usually test/calibration points)
                # But keep Point 999 for averaged measurements as these are legitimate averaged data
                if measurement.get('coordinate_point') == 999 and not use_averages:
                    continue
                
                # Create DataID from available information
                data_id = measurement.get('image_name', 'Unknown')
                
                # For individual measurements, add point number; for averages, keep it simple
                if measurement.get('coordinate_point') and not use_averages:
                    data_id += f"_P{measurement['coordinate_point']}"
                # For averaged data, don't add _P999 - just use the image name for cleaner DataID
                
                data_row = {
                    'L_norm': measurement['l_value'] / 100.0,  # Normalize L* from 0-100 to 0-1
                    'a_norm': (measurement['a_value'] + 128) / 255.0,  # Normalize a* from -128/+127 to 0-1
                    'b_norm': (measurement['b_value'] + 128) / 255.0,  # Normalize b* from -128/+127 to 0-1
                    'DataID': data_id
                }
                plot3d_data.append(data_row)
            
            self.logger.info(f"Retrieved {len(plot3d_data)} data points from {db_name}")
            return plot3d_data
            
        except Exception as e:
            self.logger.error(f"Error getting sample data for {sample_set_name}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def export_to_plot3d(self, sample_set_name: str, output_dir: str = None, 
                        export_individual: bool = True, export_averages: bool = True) -> List[str]:
        """Export sample set data directly to Plot_3D format.
        
        Args:
            sample_set_name: Name of the sample set to export (can be base name or with _averages suffix)
            output_dir: Directory to save files (default: ~/Desktop/Color Analysis spreadsheets)
            export_individual: Whether to export individual measurements
            export_averages: Whether to export averaged measurements
            
        Returns:
            List of created file paths
        """
        created_files = []
        
        try:
            # Check template exists
            if not os.path.exists(self.template_path):
                self.logger.error(f"Template file not found: {self.template_path}")
                return created_files
            
            # Set default output directory
            if output_dir is None:
                output_dir = os.path.expanduser("~/Desktop/StampZ Exports")
                os.makedirs(output_dir, exist_ok=True)
            
            # Determine base name and whether this is specifically an averages database
            if sample_set_name.endswith('_averages'):
                base_name = sample_set_name[:-9]  # Remove '_averages' suffix
                # If user selected an _averages database specifically, only export averages
                self.logger.info(f"Sample set '{sample_set_name}' appears to be averages-only database")
                export_individual = False  # Don't try to export individual data from averages database
                actual_sample_set = base_name  # Use base name for the export logic
            else:
                base_name = sample_set_name
                actual_sample_set = sample_set_name
            
            # Export individual measurements (only if not an averages-only database)
            if export_individual:
                individual_data = self.get_sample_data(actual_sample_set, use_averages=False)
                if individual_data:
                    individual_file = os.path.join(output_dir, f"{base_name}_Plot3D.ods")
                    
                    # Check if file already exists - if so, append data instead of creating new file
                    if os.path.exists(individual_file):
                        self.logger.info(f"File exists, appending data to: {individual_file}")
                        if self.append_data_to_plot3d_file(individual_file, actual_sample_set, use_averages=False):
                            created_files.append(individual_file)  # Still add to list for user feedback
                            self.logger.info(f"Successfully appended individual data to: {individual_file}")
                        else:
                            self.logger.warning(f"Failed to append individual data to: {individual_file}")
                    else:
                        # File doesn't exist, create new file
                        if self._create_plot3d_file(individual_file, individual_data):
                            created_files.append(individual_file)
                            self.logger.info(f"Created new individual Plot_3D file: {individual_file}")
                        else:
                            self.logger.warning(f"Failed to create individual Plot_3D file: {individual_file}")
                else:
                    self.logger.warning(f"No individual data found for {actual_sample_set}")
            
            # Export averaged measurements
            if export_averages:
                averaged_data = self.get_sample_data(actual_sample_set, use_averages=True)
                if averaged_data:
                    averaged_file = os.path.join(output_dir, f"{base_name}_Averages_Plot3D.ods")
                    
                    # Check if file already exists - if so, append data instead of creating new file
                    if os.path.exists(averaged_file):
                        self.logger.info(f"File exists, appending data to: {averaged_file}")
                        if self.append_data_to_plot3d_file(averaged_file, actual_sample_set, use_averages=True):
                            created_files.append(averaged_file)  # Still add to list for user feedback
                            self.logger.info(f"Successfully appended averaged data to: {averaged_file}")
                        else:
                            self.logger.warning(f"Failed to append averaged data to: {averaged_file}")
                    else:
                        # File doesn't exist, create new file
                        if self._create_plot3d_file(averaged_file, averaged_data):
                            created_files.append(averaged_file)
                            self.logger.info(f"Created new averaged Plot_3D file: {averaged_file}")
                        else:
                            self.logger.warning(f"Failed to create averaged Plot_3D file: {averaged_file}")
                else:
                    self.logger.warning(f"No averaged data found for {actual_sample_set}")
            
            return created_files
            
        except Exception as e:
            self.logger.error(f"Error exporting {sample_set_name} to Plot_3D: {e}")
            return created_files
    
    def _create_plot3d_file(self, output_path: str, data: List[Dict]) -> bool:
        """Create Plot_3D file by copying template and inserting data.
        
        Args:
            output_path: Path for the output file
            data: List of data dictionaries
            
        Returns:
            True if successful
        """
        try:
            # Copy template to output location
            shutil.copy2(self.template_path, output_path)
            
            # Make the copied file writable (templates are read-only)
            import stat
            os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            
            self.logger.info(f"Copied template to: {output_path}")
            
            # Open the copied file and insert data
            doc = ezodf.opendoc(output_path)
            sheet = doc.sheets[0]
            
            # Insert data starting at row 8 (index 7), columns A-D (indices 0-3)
            start_row_idx = 7  # Row 8 in 0-based indexing
            
            for row_offset, data_row in enumerate(data):
                sheet_row_idx = start_row_idx + row_offset
                
                # Column A (index 0): Xnorm (L*_norm)
                sheet[sheet_row_idx, 0].set_value(data_row['L_norm'])
                
                # Column B (index 1): Ynorm (a*_norm)
                sheet[sheet_row_idx, 1].set_value(data_row['a_norm'])
                
                # Column C (index 2): Znorm (b*_norm)
                sheet[sheet_row_idx, 2].set_value(data_row['b_norm'])
                
                # Column D (index 3): DataID
                sheet[sheet_row_idx, 3].set_value(data_row['DataID'])
                
                # Leave other columns (E-L) as they are in the template
                # Plot_3D will fill these during analysis (Cluster, ∆E, etc.)
            
            # Save the document
            temp_path = f"{output_path}.temp"
            doc.saveas(temp_path)
            os.replace(temp_path, output_path)
            
            self.logger.info(f"Successfully inserted {len(data)} rows of data into {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating Plot_3D file {output_path}: {e}")
            return False
    
    def _find_next_empty_row(self, sheet, start_row_idx: int = 7) -> int:
        """Find the next empty row in the sheet where we can append new data.
        
        Args:
            sheet: ezodf sheet object
            start_row_idx: Starting row index to search from (default: 7 for row 8)
            
        Returns:
            Row index of the next empty row
        """
        try:
            max_rows = sheet.nrows()
            
            # Search for the first row where columns A-D are all empty
            for row_idx in range(start_row_idx, max_rows):
                # Check if row is empty in the first 4 columns (A-D)
                empty_row = True
                for col_idx in range(4):
                    cell_value = sheet[row_idx, col_idx].value
                    if cell_value is not None and str(cell_value).strip():
                        empty_row = False
                        break
                
                if empty_row:
                    self.logger.debug(f"Found empty row at index {row_idx} (row {row_idx + 1})")
                    return row_idx
            
            # If no empty row found within existing sheet, return the next row after the last one
            next_row = max_rows
            self.logger.debug(f"No empty row found, will append at row index {next_row} (row {next_row + 1})")
            return next_row
            
        except Exception as e:
            self.logger.error(f"Error finding next empty row: {e}")
            # Fallback to start_row_idx if there's an error
            return start_row_idx
    
    def _get_existing_dataids_from_file(self, file_path: str) -> set:
        """Get set of DataIDs that already exist in the Plot_3D file.
        
        Args:
            file_path: Path to existing Plot_3D file
            
        Returns:
            Set of DataID strings already present in the file
        """
        existing_dataids = set()
        try:
            doc = ezodf.opendoc(file_path)
            sheet = doc.sheets[0]
            
            # Check DataID column (column D, index 3) starting from row 8
            for row_idx in range(7, sheet.nrows()):
                dataid_cell = sheet[row_idx, 3].value  # Column D
                if dataid_cell and str(dataid_cell).strip():
                    existing_dataids.add(str(dataid_cell).strip())
            
            self.logger.debug(f"Found {len(existing_dataids)} existing DataIDs in {file_path}")
            return existing_dataids
            
        except Exception as e:
            self.logger.error(f"Error reading existing DataIDs from {file_path}: {e}")
            return set()
    
    def append_data_to_plot3d_file(self, file_path: str, sample_set_name: str, 
                                 use_averages: bool = False) -> bool:
        """Append only NEW data to an existing Plot_3D file without overwriting existing data.
        
        Args:
            file_path: Path to existing Plot_3D file
            sample_set_name: Name of the sample set
            use_averages: Whether to use averaged data
            
        Returns:
            True if successful
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File does not exist: {file_path}")
                return False
            
            # Get all data from database
            all_data = self.get_sample_data(sample_set_name, use_averages=use_averages)
            if not all_data:
                self.logger.warning(f"No data found for {sample_set_name}")
                return False
            
            # Get existing DataIDs from the file
            existing_dataids = self._get_existing_dataids_from_file(file_path)
            
            # Filter out data that already exists in the file
            new_data = []
            for data_row in all_data:
                if data_row['DataID'] not in existing_dataids:
                    new_data.append(data_row)
            
            if not new_data:
                self.logger.info(f"No new data to append for {sample_set_name} - all data already exists in file")
                return True  # Not an error, just nothing new to add
            
            self.logger.info(f"Found {len(new_data)} new data points to append (out of {len(all_data)} total)")
            
            # Create backup
            backup_path = f"{file_path}.backup_{int(time.time())}"
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            
            # Open file and find where to append new data
            doc = ezodf.opendoc(file_path)
            sheet = doc.sheets[0]
            
            # Find the next empty row to start appending
            start_append_row = self._find_next_empty_row(sheet, start_row_idx=7)
            
            self.logger.info(f"Appending {len(new_data)} rows starting at row {start_append_row + 1}")
            
            # Append new data without disturbing existing data
            for row_offset, data_row in enumerate(new_data):
                sheet_row_idx = start_append_row + row_offset
                
                # Only set the first 4 columns (A-D), preserving any existing data in columns E-M
                sheet[sheet_row_idx, 0].set_value(data_row['L_norm'])
                sheet[sheet_row_idx, 1].set_value(data_row['a_norm'])
                sheet[sheet_row_idx, 2].set_value(data_row['b_norm'])
                sheet[sheet_row_idx, 3].set_value(data_row['DataID'])
                
                # Do NOT touch columns 4-12 (E-M) - these may contain user data
                # Plot_3D fills these during analysis (Cluster, ∆E, etc.)
            
            # Save
            temp_path = f"{file_path}.temp"
            doc.saveas(temp_path)
            os.replace(temp_path, file_path)
            
            # Clean up backup on success
            try:
                os.remove(backup_path)
            except Exception:
                pass  # Keep backup if cleanup fails
            
            self.logger.info(f"Successfully appended {len(new_data)} rows to {file_path} starting at row {start_append_row + 1}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error appending data to Plot_3D file {file_path}: {e}")
            return False
    
    def update_existing_plot3d_file(self, file_path: str, sample_set_name: str, 
                                  use_averages: bool = False, append_mode: bool = True) -> bool:
        """Update an existing Plot_3D file with new data.
        
        Args:
            file_path: Path to existing Plot_3D file
            sample_set_name: Name of the sample set
            use_averages: Whether to use averaged data
            append_mode: If True, append to existing data; if False, replace existing data
            
        Returns:
            True if successful
        """
        if append_mode:
            # Use the new append method by default to preserve existing data
            return self.append_data_to_plot3d_file(file_path, sample_set_name, use_averages)
        
        # Legacy replace mode (for backward compatibility)
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File does not exist: {file_path}")
                return False
            
            # Get new data
            data = self.get_sample_data(sample_set_name, use_averages=use_averages)
            if not data:
                self.logger.warning(f"No data to update for {sample_set_name}")
                return False
            
            # Create backup
            backup_path = f"{file_path}.backup_{int(time.time())}"
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            
            # Clear existing data and insert new data (LEGACY MODE - USE WITH CAUTION)
            doc = ezodf.opendoc(file_path)
            sheet = doc.sheets[0]
            
            self.logger.warning("LEGACY REPLACE MODE: This will overwrite existing data!")
            
            # Clear data rows (starting from row 8) - ONLY columns A-D
            start_row_idx = 7
            for row_idx in range(start_row_idx, sheet.nrows()):
                for col_idx in range(4):  # Clear columns A-D only, preserve E-M
                    sheet[row_idx, col_idx].set_value("")
            
            # Insert new data
            for row_offset, data_row in enumerate(data):
                sheet_row_idx = start_row_idx + row_offset
                sheet[sheet_row_idx, 0].set_value(data_row['L_norm'])
                sheet[sheet_row_idx, 1].set_value(data_row['a_norm'])
                sheet[sheet_row_idx, 2].set_value(data_row['b_norm'])
                sheet[sheet_row_idx, 3].set_value(data_row['DataID'])
            
            # Save
            temp_path = f"{file_path}.temp"
            doc.saveas(temp_path)
            os.replace(temp_path, file_path)
            
            # Clean up backup on success
            try:
                os.remove(backup_path)
            except Exception:
                pass  # Keep backup if cleanup fails
            
            self.logger.info(f"Successfully replaced data in {file_path} with {len(data)} rows")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating Plot_3D file {file_path}: {e}")
            return False


def main():
    """Example usage and testing."""
    exporter = DirectPlot3DExporter()
    
    # Get available sample sets
    sample_sets = exporter.get_available_sample_sets()
    print(f"Available sample sets: {sample_sets}")
    
    if sample_sets:
        # Export the first sample set as an example
        sample_set = sample_sets[0]
        print(f"\nExporting {sample_set}...")
        
        created_files = exporter.export_to_plot3d(sample_set)
        
        if created_files:
            print(f"Successfully created {len(created_files)} file(s):")
            for file_path in created_files:
                print(f"  - {file_path}")
        else:
            print("No files created")
    else:
        print("No sample sets available for export")


if __name__ == "__main__":
    main()
