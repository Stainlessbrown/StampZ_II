#!/usr/bin/env python3
"""
Integration module for transferring StampZ color analysis data to Plot_3D format.

This module handles the seamless transfer of normalized L*a*b* data from StampZ 
color analysis exports to Plot_3D's expected format, starting at row 8 to avoid 
overwriting existing data.

Key Features:
- Maps normalized L*a*b* → Xnorm, Ynorm, Znorm for Plot_3D
- Preserves DataID from StampZ exports
- Starts data insertion at row 8
- Handles both individual and averaged measurements
- Supports semi-real-time updates as StampZ data is saved
- Non-destructive: doesn't overwrite existing Plot_3D data
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import ezodf
import tempfile
import shutil
import time

class StampZPlot3DIntegrator:
    """Integrates StampZ color analysis data with Plot_3D visualization."""
    
    # Plot_3D expected column structure
    PLOT3D_COLUMNS = [
        'Xnorm', 'Ynorm', 'Znorm', 'DataID', 'Cluster', '∆E', 'Marker',
        'Color', 'Centroid_X', 'Centroid_Y', 'Centroid_Z', 'Sphere'
    ]
    
    # Default values for Plot_3D columns not provided by StampZ
    PLOT3D_DEFAULTS = {
        'Cluster': None,
        '∆E': None,  # Leave blank - Plot_3D will calculate when ∆E function is initiated
        'Marker': '.',
        'Color': 'blue',
        'Centroid_X': float('nan'),
        'Centroid_Y': float('nan'), 
        'Centroid_Z': float('nan'),
        'Sphere': None
    }
    
    # Starting row for data insertion (row 8 = index 7)
    DATA_START_ROW = 8
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the integrator.
        
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
            
        self.logger.info("StampZ-Plot3D Integrator initialized")
    
    def read_stampz_export(self, export_file_path: str) -> Optional[pd.DataFrame]:
        """Read StampZ normalized export data.
        
        Args:
            export_file_path: Path to StampZ export file (.ods, .xlsx, or .csv)
            
        Returns:
            DataFrame with normalized L*a*b* data, or None if read fails
        """
        try:
            if not os.path.exists(export_file_path):
                self.logger.error(f"Export file not found: {export_file_path}")
                return None
                
            file_ext = os.path.splitext(export_file_path)[1].lower()
            
            if file_ext == '.ods':
                df = pd.read_excel(export_file_path, engine='odf')
            elif file_ext == '.xlsx':
                df = pd.read_excel(export_file_path)
            elif file_ext == '.csv':
                df = pd.read_csv(export_file_path)
            else:
                self.logger.error(f"Unsupported file format: {file_ext}")
                return None
                
            self.logger.info(f"Successfully read {len(df)} rows from {os.path.basename(export_file_path)}")
            self.logger.info(f"Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error reading StampZ export: {e}")
            return None
    
    def convert_to_plot3d_format(self, stampz_data: pd.DataFrame) -> pd.DataFrame:
        """Convert StampZ export data to Plot_3D format.
        
        Args:
            stampz_data: DataFrame from StampZ export
            
        Returns:
            DataFrame formatted for Plot_3D
        """
        try:
            # Create new DataFrame with Plot_3D structure
            plot3d_data = pd.DataFrame(columns=self.PLOT3D_COLUMNS)
            
            # Map normalized L*a*b* to Plot_3D coordinates
            # Column mapping: L*_norm → Xnorm, a*_norm → Ynorm, b*_norm → Znorm
            coord_mappings = [
                ('L*_norm', 'Xnorm'),
                ('a*_norm', 'Ynorm'), 
                ('b*_norm', 'Znorm')
            ]
            
            # Check if required columns exist
            required_cols = ['L*_norm', 'a*_norm', 'b*_norm', 'DataID']
            missing_cols = [col for col in required_cols if col not in stampz_data.columns]
            
            if missing_cols:
                self.logger.error(f"Missing required columns: {missing_cols}")
                self.logger.info(f"Available columns: {list(stampz_data.columns)}")
                return None
                
            # Copy coordinate data
            for stampz_col, plot3d_col in coord_mappings:
                if stampz_col in stampz_data.columns:
                    plot3d_data[plot3d_col] = stampz_data[stampz_col].copy()
                    self.logger.debug(f"Mapped {stampz_col} → {plot3d_col}")
            
            # Copy DataID
            if 'DataID' in stampz_data.columns:
                plot3d_data['DataID'] = stampz_data['DataID'].copy()
                self.logger.debug("Mapped DataID → DataID")
            
            # Set default values for other Plot_3D columns
            for col, default_val in self.PLOT3D_DEFAULTS.items():
                plot3d_data[col] = default_val
                
            # Assign different colors based on DataID patterns (optional enhancement)
            if 'DataID' in plot3d_data.columns:
                plot3d_data['Color'] = plot3d_data['DataID'].apply(self._assign_color_by_pattern)
            
            self.logger.info(f"Converted {len(plot3d_data)} rows to Plot_3D format")
            return plot3d_data
            
        except Exception as e:
            self.logger.error(f"Error converting to Plot_3D format: {e}")
            return None
    
    def _assign_color_by_pattern(self, data_id: str) -> str:
        """Assign colors based on DataID patterns.
        
        Args:
            data_id: DataID string from StampZ
            
        Returns:
            Color string for Plot_3D
        """
        if pd.isna(data_id) or not data_id:
            return 'gray'
            
        data_id = str(data_id).upper()
        
        # Color mapping based on common patterns
        if 'AVERAGED' in data_id or '_AVG' in data_id:
            return 'red'  # Averaged measurements in red
        elif 'SAMPLE' in data_id:
            return 'blue'  # Individual samples in blue
        elif any(char.isdigit() for char in data_id):
            return 'green'  # Data with numbers in green
        else:
            return 'purple'  # Everything else in purple
    
    def find_plot3d_file(self, search_dir: str = None) -> Optional[str]:
        """Find existing Plot_3D .ods file to update.
        
        Args:
            search_dir: Directory to search in. If None, searches common locations.
            
        Returns:
            Path to Plot_3D file, or None if not found
        """
        try:
            search_paths = []
            
            if search_dir:
                search_paths.append(search_dir)
            else:
                # Common search locations
                search_paths.extend([
                    os.getcwd(),  # Current directory
                    os.path.expanduser("~/Desktop"),  # Desktop
                    os.path.expanduser("~/Documents"),  # Documents
                    os.path.join(os.getcwd(), "exports"),  # StampZ exports
                    os.path.join(os.getcwd(), "data"),  # Data directory
                ])
            
            # Look for .ods files that might be Plot_3D files
            for search_path in search_paths:
                if not os.path.exists(search_path):
                    continue
                    
                for filename in os.listdir(search_path):
                    if filename.endswith('.ods'):
                        file_path = os.path.join(search_path, filename)
                        if self._is_plot3d_file(file_path):
                            self.logger.info(f"Found Plot_3D file: {file_path}")
                            return file_path
            
            self.logger.warning("No existing Plot_3D file found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error searching for Plot_3D file: {e}")
            return None
    
    def _is_plot3d_file(self, file_path: str) -> bool:
        """Check if a file is a Plot_3D format file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file appears to be Plot_3D format
        """
        try:
            # Read first few rows to check column structure
            df = pd.read_excel(file_path, engine='odf', nrows=5)
            
            # Check for Plot_3D column patterns
            required_plot3d_cols = ['Xnorm', 'Ynorm', 'Znorm', 'DataID']
            found_cols = [col for col in required_plot3d_cols if col in df.columns]
            
            return len(found_cols) >= 3  # At least 3 of 4 required columns
            
        except Exception:
            return False
    
    def insert_data_to_plot3d(self, plot3d_file_path: str, new_data: pd.DataFrame, 
                              start_row: int = None) -> bool:
        """Insert new data into existing Plot_3D file starting at specified row.
        
        Args:
            plot3d_file_path: Path to existing Plot_3D .ods file
            new_data: DataFrame with Plot_3D formatted data to insert
            start_row: Row to start insertion (default: DATA_START_ROW = 8)
            
        Returns:
            True if insertion successful, False otherwise
        """
        if start_row is None:
            start_row = self.DATA_START_ROW
            
        try:
            # Create backup
            backup_path = f"{plot3d_file_path}.backup_{int(time.time())}"
            shutil.copy2(plot3d_file_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            
            # Open the ODS file
            doc = ezodf.opendoc(plot3d_file_path)
            sheet = doc.sheets[0]
            
            # Find column indices for Plot_3D columns
            header_row_idx = 0  # Assuming headers are in first row
            col_indices = {}
            
            for col_idx in range(len(sheet.row(header_row_idx))):
                cell_value = sheet[header_row_idx, col_idx].value
                if cell_value in self.PLOT3D_COLUMNS:
                    col_indices[cell_value] = col_idx
            
            self.logger.info(f"Found column mappings: {col_indices}")
            
            # Insert new data starting at specified row
            for row_offset, (_, row_data) in enumerate(new_data.iterrows()):
                sheet_row_idx = start_row - 1 + row_offset  # Convert to 0-based
                
                for col_name in self.PLOT3D_COLUMNS:
                    if col_name in col_indices and col_name in new_data.columns:
                        col_idx = col_indices[col_name]
                        value = row_data[col_name]
                        
                        # Handle different data types
                        if pd.isna(value):
                            cell_value = ""
                        elif isinstance(value, (int, float)):
                            cell_value = float(value) if not np.isnan(value) else ""
                        else:
                            cell_value = str(value)
                        
                        # Set cell value
                        sheet[sheet_row_idx, col_idx].set_value(cell_value)
                        
                        if row_offset < 3:  # Log first few updates
                            self.logger.debug(f"Set cell [{sheet_row_idx}, {col_idx}] = {cell_value}")
            
            # Save the document
            temp_path = f"{plot3d_file_path}.temp"
            doc.saveas(temp_path)
            
            # Replace original with updated file
            os.replace(temp_path, plot3d_file_path)
            
            self.logger.info(f"Successfully inserted {len(new_data)} rows starting at row {start_row}")
            
            # Clean up backup after successful operation
            try:
                os.remove(backup_path)
            except Exception:
                pass  # Keep backup if cleanup fails
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting data to Plot_3D file: {e}")
            return False
    
    def create_new_plot3d_file(self, output_path: str, data: pd.DataFrame = None) -> bool:
        """Create a new Plot_3D format .ods file using template.
        
        Args:
            output_path: Path where to create the new file
            data: Optional initial data to include
            
        Returns:
            True if file creation successful
        """
        try:
            # Find the template file
            template_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),  # Go up from utils/
                'templates', 'plot3d', 'Plot3D_Template.ods'
            )
            
            if not os.path.exists(template_path):
                self.logger.error(f"Template file not found: {template_path}")
                # Fallback to programmatic creation if template doesn't exist
                return self._create_plot3d_file_programmatically(output_path, data)
            
            # Copy template to output location
            shutil.copy2(template_path, output_path)
            self.logger.info(f"Copied template to: {output_path}")
            
            # If data is provided, insert it starting at row 8
            if data is not None and not data.empty:
                success = self.insert_data_to_plot3d(output_path, data, start_row=self.DATA_START_ROW)
                if not success:
                    self.logger.error("Failed to insert data into template")
                    return False
                self.logger.info(f"Inserted {len(data)} rows of data starting at row {self.DATA_START_ROW}")
            
            self.logger.info(f"Created new Plot_3D file from template: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating new Plot_3D file from template: {e}")
            return False
    
    def _create_plot3d_file_programmatically(self, output_path: str, data: pd.DataFrame = None) -> bool:
        """Fallback method to create Plot_3D file programmatically if template is missing.
        
        Args:
            output_path: Path where to create the new file
            data: Optional initial data to include
            
        Returns:
            True if file creation successful
        """
        try:
            self.logger.warning("Using fallback programmatic creation (template preferred)")
            
            # Create new ODS document
            doc = ezodf.opendocument.OpenDocumentSpreadsheet()
            
            # Create table
            table = ezodf.Table(name="Plot3D_Data")
            
            # Add header row
            header_row = ezodf.TableRow()
            for col_name in self.PLOT3D_COLUMNS:
                cell = ezodf.TableCell()
                cell.addElement(ezodf.text.P(text=col_name))
                header_row.addElement(cell)
            table.addElement(header_row)
            
            # Add empty rows 2-7 (rows before data starts at row 8)
            for row_idx in range(1, self.DATA_START_ROW - 1):
                empty_row = ezodf.TableRow()
                for col_idx in range(len(self.PLOT3D_COLUMNS)):
                    cell = ezodf.TableCell()
                    cell.addElement(ezodf.text.P(text=""))
                    empty_row.addElement(cell)
                table.addElement(empty_row)
            
            # Add data if provided
            if data is not None and not data.empty:
                for _, row_data in data.iterrows():
                    data_row = ezodf.TableRow()
                    for col_name in self.PLOT3D_COLUMNS:
                        cell = ezodf.TableCell()
                        value = row_data.get(col_name, "")
                        if pd.isna(value):
                            value = ""
                        cell.addElement(ezodf.text.P(text=str(value)))
                        data_row.addElement(cell)
                    table.addElement(data_row)
            
            # Add table to document
            doc.spreadsheet.addElement(table)
            
            # Save document
            doc.save(output_path)
            
            self.logger.info(f"Created new Plot_3D file programmatically: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating new Plot_3D file programmatically: {e}")
            return False
    
    def integrate_stampz_data(self, stampz_export_path: str, 
                             plot3d_file_path: str = None,
                             create_if_missing: bool = True,
                             template_name: str = None) -> bool:
        """Main integration function to transfer StampZ data to Plot_3D.
        
        Args:
            stampz_export_path: Path to StampZ export file
            plot3d_file_path: Path to Plot_3D file (auto-detected if None)
            create_if_missing: Create new Plot_3D file if none exists
            
        Returns:
            True if integration successful
        """
        try:
            self.logger.info("=== StampZ to Plot_3D Integration Started ===")
            
            # Read StampZ export data
            stampz_data = self.read_stampz_export(stampz_export_path)
            if stampz_data is None or stampz_data.empty:
                self.logger.error("No data read from StampZ export")
                return False
                
            # Convert to Plot_3D format
            plot3d_data = self.convert_to_plot3d_format(stampz_data)
            if plot3d_data is None or plot3d_data.empty:
                self.logger.error("Failed to convert data to Plot_3D format")
                return False
            
            # Handle Plot_3D file creation/detection
            file_needs_creation = False
            
            if plot3d_file_path is None:
                # Auto-detect existing Plot_3D file
                plot3d_file_path = self.find_plot3d_file()
                if plot3d_file_path is None:
                    file_needs_creation = True
            else:
                # Specific file path provided - check if it exists
                if not os.path.exists(plot3d_file_path):
                    file_needs_creation = True
                    
            # Create new file if needed
            if file_needs_creation:
                if create_if_missing:
                    # Determine file path if not already set
                    if plot3d_file_path is None:
                        if template_name:
                            base_name = template_name
                        else:
                            base_name = self._extract_template_name_from_export(stampz_export_path)
                        
                        plot3d_file_path = os.path.join(
                            os.path.dirname(stampz_export_path),
                            f"{base_name}_Plot3D.ods"
                        )
                    
                    # Create the new file using template
                    if not self.create_new_plot3d_file(plot3d_file_path, plot3d_data):
                        return False
                    
                    self.logger.info(f"Created new Plot_3D file: {plot3d_file_path}")
                    return True
                else:
                    self.logger.error("No Plot_3D file found and create_if_missing=False")
                    return False
            
            # Insert data into existing Plot_3D file
            success = self.insert_data_to_plot3d(plot3d_file_path, plot3d_data)
            
            if success:
                self.logger.info("=== Integration Completed Successfully ===")
                self.logger.info(f"Updated file: {plot3d_file_path}")
                self.logger.info(f"Added {len(plot3d_data)} data points")
            else:
                self.logger.error("=== Integration Failed ===")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error in integration: {e}")
            return False
    
    def auto_detect_stampz_exports(self, sample_set_name: str = None) -> List[str]:
        """Auto-detect StampZ export files for integration.
        
        Args:
            sample_set_name: Optional sample set to filter by
            
        Returns:
            List of paths to detected StampZ export files
        """
        try:
            search_paths = [
                os.path.join(os.getcwd(), "exports"),
                os.getcwd(),
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Downloads")
            ]
            
            export_files = []
            
            for search_path in search_paths:
                if not os.path.exists(search_path):
                    continue
                    
                for filename in os.listdir(search_path):
                    if any(filename.endswith(ext) for ext in ['.ods', '.xlsx', '.csv']):
                        # Check if it's a StampZ export file
                        file_path = os.path.join(search_path, filename)
                        if self._is_stampz_export_file(file_path):
                            if sample_set_name is None or sample_set_name in filename:
                                export_files.append(file_path)
            
            self.logger.info(f"Found {len(export_files)} StampZ export files")
            return export_files
            
        except Exception as e:
            self.logger.error(f"Error detecting StampZ exports: {e}")
            return []
    
    def _extract_template_name_from_export(self, export_path: str) -> str:
        """Extract the template/sample set name from an export filename.
        
        Args:
            export_path: Path to the StampZ export file
            
        Returns:
            Template name extracted from filename
        """
        try:
            filename = os.path.basename(export_path)
            base_name = os.path.splitext(filename)[0]
            
            # Remove common export suffixes to get the template name
            # Examples: 
            #   "137_averages_20250827" -> "137" 
            #   "F-137_export_20250827" -> "F-137"
            #   "Color_Test_normalized_data" -> "Color_Test"
            
            # Common patterns to remove
            suffixes_to_remove = [
                '_averages',
                '_export', 
                '_normalized', 
                '_data',
                '_norm',
                '_individual'
            ]
            
            # Remove date patterns (YYYYMMDD format)
            import re
            base_name = re.sub(r'_\d{8}$', '', base_name)  # Remove trailing _YYYYMMDD
            base_name = re.sub(r'_\d{8}_\d{6}$', '', base_name)  # Remove _YYYYMMDD_HHMMSS
            
            # Remove common suffixes
            for suffix in suffixes_to_remove:
                if base_name.endswith(suffix):
                    base_name = base_name[:-len(suffix)]
                    break  # Only remove first match to avoid over-trimming
            
            # If we still have underscores followed by what looks like timestamps or version numbers
            # Keep only the first part
            parts = base_name.split('_')
            if len(parts) > 1:
                # Check if later parts look like version numbers or timestamps
                for i, part in enumerate(parts[1:], 1):
                    if (part.isdigit() or  # Pure numbers
                        re.match(r'^v?\d+(\.\d+)*$', part) or  # Version numbers
                        len(part) >= 6 and part.replace('-', '').replace(':', '').isdigit()):  # Timestamps
                        base_name = '_'.join(parts[:i])
                        break
            
            # Final cleanup - ensure we have a reasonable template name
            if not base_name or base_name.isdigit():
                # If we ended up with just numbers or empty string, use the original base
                base_name = os.path.splitext(os.path.basename(export_path))[0]
                # Try a simpler approach - just take the first meaningful part
                first_part = base_name.split('_')[0]
                if first_part and not first_part.isdigit():
                    base_name = first_part
            
            self.logger.debug(f"Extracted template name '{base_name}' from '{filename}'")
            return base_name
            
        except Exception as e:
            self.logger.warning(f"Error extracting template name from '{export_path}': {e}")
            # Fallback to just the filename without extension
            return os.path.splitext(os.path.basename(export_path))[0]
    
    def _is_stampz_export_file(self, file_path: str) -> bool:
        """Check if file is a StampZ export file.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if appears to be StampZ export
        """
        try:
            # Quick check based on filename patterns
            filename = os.path.basename(file_path).lower()
            if any(pattern in filename for pattern in ['_export', 'stampz', '_norm']):
                return True
                
            # Check column headers
            df = pd.read_excel(file_path, engine='odf' if file_path.endswith('.ods') else None, nrows=1)
            
            # Look for StampZ export column patterns
            stampz_patterns = ['l*_norm', 'a*_norm', 'b*_norm', 'dataid']
            found_patterns = sum(1 for col in df.columns if any(pattern in col.lower() for pattern in stampz_patterns))
            
            return found_patterns >= 3
            
        except Exception:
            return False


def main():
    """Example usage and testing."""
    integrator = StampZPlot3DIntegrator()
    
    # Example: integrate a specific StampZ export
    stampz_file = "exports/137_averages_20250827.ods"  # Example path
    
    if os.path.exists(stampz_file):
        success = integrator.integrate_stampz_data(stampz_file)
        if success:
            print("Integration successful!")
        else:
            print("Integration failed!")
    else:
        print(f"Example file not found: {stampz_file}")
        
        # Show auto-detected files
        exports = integrator.auto_detect_stampz_exports()
        if exports:
            print(f"\nFound {len(exports)} StampZ export files:")
            for export_file in exports:
                print(f"  - {export_file}")
        else:
            print("\nNo StampZ export files detected")


if __name__ == "__main__":
    main()
