#!/usr/bin/env python3
"""
ODS (Open Document Spreadsheet) export utilities for StampZ color analysis data.
Creates .ods files that can be opened in LibreOffice Calc on Mac.
"""

import sqlite3
import os
import subprocess
import csv
from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass

try:
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableRow, TableCell
    from odf.text import P
    from odf.style import Style, TableColumnProperties, ParagraphProperties
    from odf import number
    ODF_AVAILABLE = True
except ImportError:
    ODF_AVAILABLE = False

@dataclass
class ColorMeasurement:
    """Represents a single color measurement for export."""
    data_id: str
    sample_set_number: int
    coordinate_point: int
    l_value: float
    a_value: float
    b_value: float
    rgb_r: float
    rgb_g: float
    rgb_b: float
    x_position: float
    y_position: float
    sample_shape: str
    sample_size: str
    sample_anchor: str
    measurement_date: str
    notes: Optional[str] = None

class ODSExporter:
    """Export StampZ color analysis data to ODS format."""
    
    def __init__(self, sample_set_name: str = None):
        """Initialize the exporter with optional specific sample set.
        
        Args:
            sample_set_name: If provided, export only this sample set's data
        """
        self.sample_set_name = sample_set_name
        
        # Use STAMPZ_DATA_DIR environment variable if available (consistent with ColorAnalysisDB)
        stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
        if stampz_data_dir:
            self.coordinates_db_path = os.path.join(stampz_data_dir, "coordinates.db")
            self.color_data_dir = os.path.join(stampz_data_dir, "data", "color_analysis")
            print(f"DEBUG ODSExporter: Using STAMPZ_DATA_DIR: {stampz_data_dir}")
        else:
            # Running from source - use relative path
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.coordinates_db_path = os.path.join(current_dir, "data", "coordinates.db")
            self.color_data_dir = os.path.join(current_dir, "data", "color_analysis")
            print(f"DEBUG ODSExporter: Using relative path from: {current_dir}")
        
        # Initialize preferences manager for export settings
        try:
            from .user_preferences import get_preferences_manager
            self.prefs_manager = get_preferences_manager()
            print(f"DEBUG ODSExporter: Initialized preferences manager")
        except ImportError as e:
            print(f"DEBUG ODSExporter: Could not load preferences manager: {e}")
            self.prefs_manager = None
            
        if not ODF_AVAILABLE:
            raise ImportError("odfpy library not available. Install with: pip install odfpy==1.4.1")
    
    def get_color_measurements(self, deduplicate: bool = True) -> List[ColorMeasurement]:
        """Retrieve all color measurements from separate sample set databases.
        
        Args:
            deduplicate: If True, removes duplicates by keeping only the most recent measurement
                        If False, returns all measurements for accumulation in spreadsheet
        """
        measurements = []
        
        try:
            print(f"DEBUG ODSExporter: Starting get_color_measurements, deduplicate={deduplicate}")
            print(f"DEBUG ODSExporter: self.sample_set_name = {repr(self.sample_set_name)}")
            
            from utils.color_analysis_db import ColorAnalysisDB
            
            # Get all sample set databases - use the persistent directory
            color_data_dir = self.color_data_dir
            print(f"DEBUG ODSExporter: Using color_data_dir = {color_data_dir}")
            print(f"DEBUG ODSExporter: Directory exists = {os.path.exists(color_data_dir)}")
            
            if not os.path.exists(color_data_dir):
                print(f"DEBUG ODSExporter: Directory does not exist, returning empty list")
                return measurements
            
            # Get sample set databases - filter by specific sample set if provided
            sample_sets = ColorAnalysisDB.get_all_sample_set_databases(color_data_dir)
            print(f"DEBUG ODSExporter: Found sample sets: {sample_sets}")
            
            if self.sample_set_name:
                print(f"DEBUG ODSExporter: Filtering for sample_set_name = {repr(self.sample_set_name)} (type: {type(self.sample_set_name)})")
                print(f"DEBUG ODSExporter: Available sample sets for comparison: {[repr(s) for s in sample_sets]}")
                
                # Standardize the target name using the same function as ColorAnalysisDB
                from utils.naming_utils import standardize_name
                standardized_target = standardize_name(self.sample_set_name)
                print(f"DEBUG ODSExporter: Standardized target name: '{self.sample_set_name}' -> '{standardized_target}'")
                
                # Debug the filtering process
                filtered = []
                for s in sample_sets:
                    # Try both exact match and standardized match
                    exact_match = (s == self.sample_set_name)
                    standardized_match = (s == standardized_target)
                    matches = exact_match or standardized_match
                    print(f"DEBUG ODSExporter: '{s}' == '{self.sample_set_name}' ? {exact_match}")
                    print(f"DEBUG ODSExporter: '{s}' == '{standardized_target}' ? {standardized_match}")
                    print(f"DEBUG ODSExporter: Overall match for '{s}': {matches}")
                    if matches:
                        filtered.append(s)
                
                sample_sets = filtered
                print(f"DEBUG ODSExporter: After filtering: {sample_sets}")
            else:
                print(f"DEBUG ODSExporter: No filtering (sample_set_name is {repr(self.sample_set_name)})")
            
            print(f"DEBUG ODSExporter: Processing {len(sample_sets)} sample sets")
            
            sample_set_counter = 1
            for sample_set_name in sample_sets:
                try:
                    # Create color analysis DB for this sample set
                    color_db = ColorAnalysisDB(sample_set_name)
                    
                    # Get all measurements for this sample set
                    color_measurements = color_db.get_all_measurements()
                    
                    if deduplicate:
                        # Remove duplicates by keeping only the most recent measurement for each coordinate point
                        # Sort by measurement_date to ensure we get the latest one
                        sorted_measurements = sorted(color_measurements, key=lambda x: x['measurement_date'])
                        
                        unique_measurements = {}
                        for measurement in sorted_measurements:
                            coord_point = measurement['coordinate_point']
                            # Always keep the latest measurement (due to sorting, later ones overwrite earlier)
                            unique_measurements[coord_point] = measurement
                        
                        measurements_to_process = unique_measurements.values()
                    else:
                        # Return all measurements for accumulation
                        measurements_to_process = color_measurements
                    
                    # Get coordinate template information for this sample set
                    coordinate_info = self._get_coordinate_info(sample_set_name)
                    
                    # Convert to our ColorMeasurement objects
                    for measurement in measurements_to_process:
                        # Create data_id from image filename + timestamp + sample number
                        image_basename = os.path.splitext(os.path.basename(measurement['image_name']))[0]
                        
                        # Extract timestamp from measurement_date and format it
                        # measurement_date format is usually "2025-07-21 17:36:02"
                        try:
                            from datetime import datetime
                            # Parse the measurement date
                            date_obj = datetime.strptime(measurement['measurement_date'], '%Y-%m-%d %H:%M:%S')
                            # Format as compact timestamp: YYYYMMDD_HHMMSS
                            timestamp = date_obj.strftime('%Y%m%d_%H%M%S')
                        except:
                            # Fallback if date parsing fails
                            timestamp = measurement['measurement_date'].replace(' ', '_').replace(':', '').replace('-', '')
                        
                        data_id = f"{image_basename}_{timestamp}_sample{measurement['coordinate_point']}"
                        
                        # Get coordinate details - FIRST try from the measurement itself (has actual values)
                        coord_point = measurement['coordinate_point']
                        
                        # Try to get sample info from the measurement data itself
                        coord_details = {
                            'shape': measurement.get('sample_type', 'unknown'),
                            'size': measurement.get('sample_size', 'unknown'),
                            'anchor': measurement.get('sample_anchor', 'unknown')
                        }
                        
                        # If we don't have sample info in the measurement, fall back to coordinate template
                        if coord_details['shape'] == 'unknown' or not coord_details['shape']:
                            template_details = coordinate_info.get(coord_point, {})
                            coord_details = {
                                'shape': template_details.get('shape', 'unknown'),
                                'size': template_details.get('size', 'unknown'),
                                'anchor': template_details.get('anchor', 'unknown')
                            }
                        
                        measurements.append(ColorMeasurement(
                            data_id=data_id,
                            sample_set_number=sample_set_counter,
                            coordinate_point=measurement['coordinate_point'],
                            l_value=measurement['l_value'],
                            a_value=measurement['a_value'],
                            b_value=measurement['b_value'],
                            rgb_r=measurement['rgb_r'],
                            rgb_g=measurement['rgb_g'],
                            rgb_b=measurement['rgb_b'],
                            x_position=measurement['x_position'],
                            y_position=measurement['y_position'],
                            sample_shape=coord_details['shape'],
                            sample_size=coord_details['size'],
                            sample_anchor=coord_details['anchor'],
                            measurement_date=measurement['measurement_date'],
                            notes=measurement['notes']
                        ))
                    
                    sample_set_counter += 1
                    
                except Exception as e:
                    print(f"Error reading color data for sample set '{sample_set_name}': {e}")
                    continue
                    
        except ImportError as e:
            print(f"Import error: {e}")
        except Exception as e:
            print(f"Error retrieving color measurements: {e}")
            
        return measurements
    
    def _get_coordinate_info(self, sample_set_name: str) -> dict:
        """Get coordinate template information for a sample set.
        
        Args:
            sample_set_name: Name of the sample set
            
        Returns:
            Dictionary mapping coordinate point numbers to coordinate details
        """
        coordinate_info = {}
        
        try:
            from utils.coordinate_db import CoordinateDB
            
            db = CoordinateDB()
            
            # Check if this is a manual mode sample set
            is_manual_mode = sample_set_name.upper().startswith('MAN_MODE')
            
            if is_manual_mode:
                # For manual mode, try to get temporary coordinates
                from utils.color_analysis_db import ColorAnalysisDB
                color_db = ColorAnalysisDB(sample_set_name)
                color_measurements = color_db.get_all_measurements()
                
                if color_measurements:
                    for i, measurement in enumerate(color_measurements, 1):
                        coordinate_info[i] = {
                            'shape': 'circle',  # Default to circle for manual mode
                            'size': '20',      # Default size
                            'anchor': 'center' # Default anchor
                        }
                    print(f"Retrieved manual mode coordinate info for {len(color_measurements)} points")
                    return coordinate_info
            
            # For non-manual mode, try exact match first
            coordinates = db.load_coordinate_set(sample_set_name)
            
            # If no exact match, try common name variations
            if not coordinates:
                # Get all available coordinate set names
                all_coord_sets = db.get_all_set_names()
                
                # Try different name variations
                variations = [
                    sample_set_name.replace('_', ' '),  # Color_Test -> Color Test
                    sample_set_name.replace(' ', '_'),  # Color Test -> Color_Test
                    sample_set_name.replace('-', '_'),  # F-137 -> F_137
                    sample_set_name.replace('_', '-'),  # F_137 -> F-137
                ]
                
                for variation in variations:
                    if variation in all_coord_sets:
                        coordinates = db.load_coordinate_set(variation)
                        if coordinates:
                            print(f"Found coordinate template '{variation}' for sample set '{sample_set_name}'")
                            break
            
            if coordinates:
                for i, coord in enumerate(coordinates, 1):
                    # Format the shape type
                    shape = coord.sample_type.value if hasattr(coord.sample_type, 'value') else str(coord.sample_type)
                    
                    # Format the size
                    if len(coord.sample_size) == 2:
                        width, height = coord.sample_size
                        if shape.lower() == 'circle':
                            size = f"{width:.1f}" # Circles only need one dimension
                        else:
                            size = f"{width:.1f}×{height:.1f}"
                    else:
                        size = str(coord.sample_size)
                    
                    coordinate_info[i] = {
                        'shape': shape,
                        'size': size,
                        'anchor': coord.anchor_position
                    }
            else:
                print(f"No coordinate template found for sample set '{sample_set_name}' (tried variations too)")
            
        except Exception as e:
            print(f"Error getting coordinate info for {sample_set_name}: {e}")
        
        return coordinate_info
    
    def _normalize_rgb(self, rgb_value: float) -> str:
        """Convert RGB (0-255) to normalized (0.0-1.0) with 4 decimal places."""
        return f"{rgb_value/255.0:.4f}"
    
    def _normalize_lab_l(self, l_value: float) -> str:
        """Convert L* (0-100) to normalized (0.0-1.0) with 4 decimal places."""
        return f"{l_value/100.0:.4f}"
    
    def _normalize_lab_ab(self, ab_value: float) -> str:
        """Convert a*/b* (-128 to +127) to normalized (0.0-1.0) with 4 decimal places.
        
        Note: This assumes typical a*/b* range of -128 to +127 (256 total range).
        The formula is: (value + 128) / 255 to map to 0.0-1.0
        """
        return f"{(ab_value + 128.0)/255.0:.4f}"
    
    def _get_export_headers(self, use_normalized: bool) -> List[str]:
        """Get column headers based on normalization preference."""
        if use_normalized:
            return ["L*_norm", "a*_norm", "b*_norm", "DataID", "X", "Y", "Shape", "Size", "Anchor", 
                   "R_norm", "G_norm", "B_norm", "DataID_2", "Date", "Notes", "Calculations", "Averages", "Analysis"]
        else:
            return ["L*", "a*", "b*", "DataID", "X", "Y", "Shape", "Size", "Anchor", 
                   "R", "G", "B", "DataID_2", "Date", "Notes", "Calculations", "Averages", "Analysis"]
    
    def _format_measurement_values(self, measurement: ColorMeasurement, use_normalized: bool) -> List[str]:
        """Format measurement values based on normalization preference."""
        if use_normalized:
            return [
                self._normalize_lab_l(measurement.l_value),
                self._normalize_lab_ab(measurement.a_value),
                self._normalize_lab_ab(measurement.b_value),
                measurement.data_id,
                f"{measurement.x_position:.1f}",
                f"{measurement.y_position:.1f}",
                measurement.sample_shape,
                measurement.sample_size,
                measurement.sample_anchor,
                self._normalize_rgb(measurement.rgb_r),
                self._normalize_rgb(measurement.rgb_g),
                self._normalize_rgb(measurement.rgb_b),
                measurement.data_id,  # Duplicate DataID column
                measurement.measurement_date,
                measurement.notes or '',
                '',  # Calculations column
                '',  # Averages column
                ''   # Analysis column
            ]
        else:
            return [
                f"{measurement.l_value:.2f}",
                f"{measurement.a_value:.2f}",
                f"{measurement.b_value:.2f}",
                measurement.data_id,
                f"{measurement.x_position:.1f}",
                f"{measurement.y_position:.1f}",
                measurement.sample_shape,
                measurement.sample_size,
                measurement.sample_anchor,
                f"{measurement.rgb_r:.2f}",
                f"{measurement.rgb_g:.2f}",
                f"{measurement.rgb_b:.2f}",
                measurement.data_id,  # Duplicate DataID column
                measurement.measurement_date,
                measurement.notes or '',
                '',  # Calculations column
                '',  # Averages column
                ''   # Analysis column
            ]
    
    def create_ods_document(self, measurements: List[ColorMeasurement]) -> OpenDocumentSpreadsheet:
        """Create an ODS document with the color measurements."""
        if not ODF_AVAILABLE:
            raise RuntimeError("odfpy library not available. Cannot create ODS document.")
        
        # Check if normalized export is enabled
        use_normalized = False
        if self.prefs_manager:
            use_normalized = self.prefs_manager.get_export_normalized_values()
            if use_normalized:
                print("DEBUG: Using normalized export format (0.0-1.0 range)")
            else:
                print("DEBUG: Using standard export format")
        
        # Create new document
        doc = OpenDocumentSpreadsheet()
        
        # Create table
        table = Table(name="Color Analysis Data")
        
        # Add header row
        header_row = TableRow()
        headers = self._get_export_headers(use_normalized)
        
        for header in headers:
            cell = TableCell()
            cell.addElement(P(text=header))
            header_row.addElement(cell)
        
        table.addElement(header_row)
        
        # Add data rows
        for measurement in measurements:
            row = TableRow()
            
            # Create cells for each column using normalized or standard formatting
            data = self._format_measurement_values(measurement, use_normalized)
            
            # Define which columns contain numeric data
            numeric_columns = [0, 1, 2, 4, 5, 9, 10, 11]  # L*, a*, b*, X, Y, R, G, B
            
            for i, value in enumerate(data):
                cell = TableCell()
                
                # Set proper value type for numeric columns
                if i in numeric_columns and value and value != "":
                    try:
                        # Convert to float and set as numeric value
                        numeric_value = float(value)
                        cell.setAttribute('valuetype', 'float')
                        cell.setAttribute('value', str(numeric_value))
                        cell.addElement(P(text=value))  # Display text
                    except (ValueError, TypeError):
                        # If conversion fails, treat as text
                        cell.addElement(P(text=str(value)))
                else:
                    # Text columns or empty values
                    cell.addElement(P(text=str(value)))
                
                row.addElement(cell)
            
            table.addElement(row)
        
        # Add table to document
        doc.spreadsheet.addElement(table)
        
        return doc
    
    def export_to_ods(self, output_path: str) -> bool:
        """Export color analysis data to an ODS file.
        For accumulation mode, includes ALL measurements from database (no deduplication).
        """
        try:
            # Get ALL measurements from database (no deduplication for accumulation)
            measurements = self.get_color_measurements(deduplicate=False)
            
            if not measurements:
                print("No color measurements found in database")
                return False
            
            # Sort measurements by date for chronological order in spreadsheet
            measurements.sort(key=lambda x: x.measurement_date)
            
            # Create ODS document
            doc = self.create_ods_document(measurements)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save document
            doc.save(output_path)
            
            print(f"Successfully exported {len(measurements)} measurements to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting to ODS: {e}")
            return False
    
    def export_to_xlsx(self, output_path: str) -> bool:
        """Export color analysis data to an Excel (.xlsx) file using pandas.
        For accumulation mode, includes ALL measurements from database (no deduplication).
        """
        try:
            # Check if pandas is available
            try:
                import pandas as pd
            except ImportError:
                print("Error: pandas library not available. Install with: pip install pandas")
                return False
            
            # Get ALL measurements from database (no deduplication for accumulation)
            measurements = self.get_color_measurements(deduplicate=False)
            
            if not measurements:
                print("No color measurements found in database")
                return False
            
            # Sort measurements by date for chronological order in spreadsheet
            measurements.sort(key=lambda x: x.measurement_date)
            
            # Check if normalized export is enabled
            use_normalized = False
            if self.prefs_manager:
                use_normalized = self.prefs_manager.get_export_normalized_values()
                if use_normalized:
                    print("DEBUG: Using normalized export format (0.0-1.0 range) for XLSX")
                else:
                    print("DEBUG: Using standard export format for XLSX")
            
            # Convert measurements to DataFrame
            data = []
            for measurement in measurements:
                if use_normalized:
                    # Use normalized values
                    data.append({
                        'L*_norm': float(self._normalize_lab_l(measurement.l_value)),
                        'a*_norm': float(self._normalize_lab_ab(measurement.a_value)),
                        'b*_norm': float(self._normalize_lab_ab(measurement.b_value)),
                        'DataID': measurement.data_id,
                        'X': measurement.x_position,
                        'Y': measurement.y_position,
                        'Shape': measurement.sample_shape,
                        'Size': measurement.sample_size,
                        'Anchor': measurement.sample_anchor,
                        'R_norm': float(self._normalize_rgb(measurement.rgb_r)),
                        'G_norm': float(self._normalize_rgb(measurement.rgb_g)),
                        'B_norm': float(self._normalize_rgb(measurement.rgb_b)),
                        'DataID_2': measurement.data_id,  # Duplicate column for compatibility
                        'Date': measurement.measurement_date,
                        'Notes': measurement.notes or '',
                        'Calculations': '',  # Empty column for user calculations
                        'Averages': '',      # Empty column for user averages
                        'Analysis': ''       # Empty column for user analysis
                    })
                else:
                    # Use standard values
                    data.append({
                        'L*': measurement.l_value,
                        'a*': measurement.a_value,
                        'b*': measurement.b_value,
                        'DataID': measurement.data_id,
                        'X': measurement.x_position,
                        'Y': measurement.y_position,
                        'Shape': measurement.sample_shape,
                        'Size': measurement.sample_size,
                        'Anchor': measurement.sample_anchor,
                        'R': measurement.rgb_r,
                        'G': measurement.rgb_g,
                        'B': measurement.rgb_b,
                        'DataID_2': measurement.data_id,  # Duplicate column for compatibility
                        'Date': measurement.measurement_date,
                        'Notes': measurement.notes or '',
                        'Calculations': '',  # Empty column for user calculations
                        'Averages': '',      # Empty column for user averages
                        'Analysis': ''       # Empty column for user analysis
                    })
            
            df = pd.DataFrame(data)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save to Excel with proper formatting
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Color Analysis Data', index=False)
                
                # Get the workbook and worksheet to apply formatting
                workbook = writer.book
                worksheet = writer.sheets['Color Analysis Data']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"Successfully exported {len(measurements)} measurements to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting to XLSX: {e}")
            return False
    
    def export_to_csv(self, output_path: str) -> bool:
        """Export color analysis data to a CSV file.
        For accumulation mode, includes ALL measurements from database (no deduplication).
        """
        try:
            # Get ALL measurements from database (no deduplication for accumulation)
            measurements = self.get_color_measurements(deduplicate=False)
            
            if not measurements:
                print("No color measurements found in database")
                return False
            
            # Sort measurements by date for chronological order in spreadsheet
            measurements.sort(key=lambda x: x.measurement_date)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Check if normalized export is enabled
            use_normalized = False
            if self.prefs_manager:
                use_normalized = self.prefs_manager.get_export_normalized_values()
                if use_normalized:
                    print("DEBUG: Using normalized export format (0.0-1.0 range) for CSV")
                else:
                    print("DEBUG: Using standard export format for CSV")
            
            # Define headers based on normalization preference
            headers = self._get_export_headers(use_normalized)
            
            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header row
                writer.writerow(headers)
                
                # Write data rows
                for measurement in measurements:
                    row = self._format_measurement_values(measurement, use_normalized)
                    writer.writerow(row)
            
            print(f"Successfully exported {len(measurements)} measurements to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    def export_to_sample_set_file(self, base_filename: str = None, format_type: str = "ods") -> str:
        """Export to a single file per sample set using user preferences.
        
        Args:
            base_filename: Optional base filename. If None, uses sample set name or default
            format_type: Export format ('ods', 'xlsx', or 'csv')
        """
        try:
            # Validate format type
            if format_type not in ['ods', 'xlsx', 'csv']:
                print(f"Error: Unsupported format type '{format_type}'. Use 'ods', 'xlsx', or 'csv'.")
                return None
            
            # Determine file extension
            extension = f".{format_type}"
            
            # Use preferences for export directory and filename
            if self.prefs_manager:
                export_dir = self.prefs_manager.get_export_directory()
                filename = self.prefs_manager.get_export_filename(
                    sample_set_name=self.sample_set_name or base_filename,
                    extension=extension
                )
                output_path = os.path.join(export_dir, filename)
                print(f"DEBUG ODSExporter: Using preferences - directory: {export_dir}, filename: {filename}")
            else:
                # Fallback to old method if preferences not available
                print(f"DEBUG ODSExporter: Preferences not available, using fallback method")
                
                # Determine the base filename
                if base_filename is None:
                    if self.sample_set_name:
                        base_filename = self.sample_set_name
                    else:
                        # Use a default name for the current export
                        base_filename = "stampz_color_data"
                
                filename = f"{base_filename}{extension}"
                
                # Save to exports directory using consistent path resolution
                stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
                if stampz_data_dir:
                    output_path = os.path.join(stampz_data_dir, "exports", filename)
                else:
                    # Running from source - use relative path
                    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    output_path = os.path.join(current_dir, "exports", filename)
            
            # Export using the appropriate method
            success = False
            if format_type == "ods":
                success = self.export_to_ods(output_path)
            elif format_type == "xlsx":
                success = self.export_to_xlsx(output_path)
            elif format_type == "csv":
                success = self.export_to_csv(output_path)
            
            if success:
                self.last_saved_file = output_path  # Store for potential opening
                return output_path
            return None
            
        except Exception as e:
            print(f"DEBUG ODSExporter: Error in export_to_sample_set_file: {e}")
            return None
    
    def export_to_excel_file(self, base_filename: str = None) -> str:
        """Convenience method to export to Excel format.
        
        Args:
            base_filename: Optional base filename. If None, uses sample set name or default
        """
        return self.export_to_sample_set_file(base_filename, "xlsx")
    
    def export_to_csv_file(self, base_filename: str = None) -> str:
        """Convenience method to export to CSV format.
        
        Args:
            base_filename: Optional base filename. If None, uses sample set name or default
        """
        return self.export_to_sample_set_file(base_filename, "csv")
    
    def export_with_timestamp(self, base_filename: str = None) -> str:
        """Export with a timestamped filename (legacy method for compatibility).
        
        Args:
            base_filename: Optional base filename. If None, uses sample set name or default
        """
        # For backwards compatibility, redirect to sample set file export
        return self.export_to_sample_set_file(base_filename)
    
    def open_file_with_default_app(self, file_path: str) -> bool:
        """Open a file with the default system application (LibreOffice Calc for .ods)."""
        try:
            # Use the last saved file path if available
            actual_path = getattr(self, 'last_saved_file', file_path)
            print(f"DEBUG: Attempting to open file: {actual_path}")
            
            if not os.path.exists(actual_path):
                print(f"ERROR: File not found: {actual_path}")
                return False
            
            import sys
            
            if sys.platform == 'darwin':  # macOS
                # Use macOS 'open' command which will open with default app
                subprocess.Popen(['open', actual_path])
                print(f"DEBUG: Opened file on macOS with 'open' command")
            elif sys.platform.startswith('linux'):  # Linux
                # Try different LibreOffice commands in order of preference
                commands_to_try = [
                    ['libreoffice', '--calc', actual_path],
                    ['soffice', '--calc', actual_path],
                    ['xdg-open', actual_path]  # Fallback to system default
                ]
                
                success = False
                for cmd in commands_to_try:
                    try:
                        subprocess.Popen(cmd)
                        print(f"DEBUG: Successfully launched with command: {' '.join(cmd)}")
                        success = True
                        break
                    except FileNotFoundError:
                        print(f"DEBUG: Command not found: {' '.join(cmd)}")
                        continue
                
                if not success:
                    print(f"ERROR: Could not find LibreOffice or system open command")
                    return False
            elif sys.platform.startswith('win'):  # Windows
                # Use Windows start command
                subprocess.Popen(['start', actual_path], shell=True)
                print(f"DEBUG: Opened file on Windows with 'start' command")
            else:
                print(f"WARNING: Unsupported platform: {sys.platform}")
                return False
            
            # Add a small delay to ensure application has time to start
            import time
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"Error opening file: {e}")
            return False
    
    def _bring_libreoffice_to_front(self):
        """Use AppleScript to bring LibreOffice window to the front on macOS."""
        try:
            applescript = '''
            tell application "LibreOffice"
                activate
            end tell
            '''
            subprocess.run(['osascript', '-e', applescript], capture_output=True, timeout=5)
            print("DEBUG: Sent AppleScript command to bring LibreOffice to front")
        except Exception as e:
            print(f"DEBUG: Failed to bring LibreOffice to front: {e}")
    
    def export_and_open(self, output_path: str = None) -> bool:
        """Export to ODS and conditionally open based on user preferences."""
        if output_path is None:
            output_path = self.export_with_timestamp()
        else:
            success = self.export_to_ods(output_path)
            if not success:
                return False
        
        if output_path:
            # Check user preferences for auto-opening
            should_auto_open = True  # Default behavior
            if self.prefs_manager:
                should_auto_open = self.prefs_manager.preferences.export_prefs.auto_open_after_export
                print(f"DEBUG ODSExporter: Auto-open preference: {should_auto_open}")
            
            if should_auto_open:
                return self.open_file_with_default_app(output_path)
            else:
                print(f"DEBUG ODSExporter: Auto-open disabled, file saved to: {output_path}")
                return True  # Export was successful, just didn't open
        return False
    
    def get_latest_export_file(self) -> str:
        """Get the path to the most recent export file."""
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        exports_dir = os.path.join(current_dir, "exports")
        
        if not os.path.exists(exports_dir):
            return None
        
        # Find all .ods files in exports directory
        ods_files = [f for f in os.listdir(exports_dir) if f.endswith('.ods')]
        
        if not ods_files:
            return None
        
        # Get the most recent file by modification time
        latest_file = max(ods_files, key=lambda f: os.path.getmtime(os.path.join(exports_dir, f)))
        return os.path.join(exports_dir, latest_file)
    
    def view_latest_spreadsheet(self) -> bool:
        """Create a new export with the preferred format and open it."""
        from .user_preferences import get_preferences_manager

        prefs_manager = get_preferences_manager()
        preferred_format = prefs_manager.get_preferred_export_format()
        
        output_file = self.export_to_sample_set_file(format_type=preferred_format)
        
        if output_file:
            return self.open_file_with_default_app(output_file)
        return False

def main():
    """Test the exporter."""
    exporter = ODSExporter()
    
    # Export with timestamp
    output_file = exporter.export_with_timestamp()
    
    if output_file:
        print(f"Export completed: {output_file}")
        print("You can now open this file in LibreOffice Calc")
    else:
        print("Export failed")

if __name__ == "__main__":
    main()

