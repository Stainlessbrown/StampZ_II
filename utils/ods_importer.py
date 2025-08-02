#!/usr/bin/env python3
"""
ODS Importer for StampZ - Import corrected ODS data back into database
This script completely overwrites existing database data with corrected ODS data.
"""

import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

try:
    from odf.opendocument import load
    from odf.table import Table, TableRow, TableCell
    from odf.text import P
    ODF_AVAILABLE = True
except ImportError:
    ODF_AVAILABLE = False

class ODSImporter:
    """Import corrected ODS data back into StampZ database format."""
    
    def __init__(self):
        """Initialize the ODS importer."""
        if not ODF_AVAILABLE:
            raise ImportError("odfpy library not available. Install with: pip install odfpy==1.4.1")
    
    def parse_ods_file(self, ods_path: str) -> List[Dict]:
        """Parse ODS file and extract measurement data.
        
        Args:
            ods_path: Path to the ODS file
            
        Returns:
            List of measurement dictionaries
        """
        measurements = []
        
        try:
            # Load the ODS document
            doc = load(ods_path)
            
            # Get the first table
            tables = doc.getElementsByType(Table)
            if not tables:
                raise ValueError("No tables found in ODS file")
            
            table = tables[0]
            rows = table.getElementsByType(TableRow)
            
            if len(rows) < 2:
                raise ValueError("ODS file must have at least a header row and one data row")
            
            print(f"Found {len(rows)-1} data rows in ODS file")
            
            # Parse header row to understand column positions
            header_row = rows[0]
            header_cells = header_row.getElementsByType(TableCell)
            headers = []
            for cell in header_cells:
                text_elements = cell.getElementsByType(P)
                if text_elements:
                    headers.append(str(text_elements[0]).strip())
                else:
                    headers.append("")
            
            print(f"Headers: {headers}")
            
            # Expected column mappings based on your ODS structure
            col_mapping = {
                'L*': 0, 'a*': 1, 'b*': 2, 'DataID': 3, 'X': 4, 'Y': 5,
                'Shape': 6, 'Size': 7, 'Anchor': 8, 'R': 9, 'G': 10, 'B': 11,
                'Date': 13, 'Notes': 14
            }
            
            # Process data rows
            for row_idx, row in enumerate(rows[1:], 1):  # Skip header row
                cells = row.getElementsByType(TableCell)
                row_data = []
                
                # Extract text from each cell
                for cell in cells:
                    text_elements = cell.getElementsByType(P)
                    if text_elements:
                        cell_text = str(text_elements[0]).strip()
                        row_data.append(cell_text)
                    else:
                        row_data.append("")
                
                # Skip empty rows
                if not any(row_data):
                    continue
                
                try:
                    # Extract measurement data
                    measurement = {
                        'l_value': float(row_data[col_mapping['L*']]) if row_data[col_mapping['L*']] else 0.0,
                        'a_value': float(row_data[col_mapping['a*']]) if row_data[col_mapping['a*']] else 0.0,
                        'b_value': float(row_data[col_mapping['b*']]) if row_data[col_mapping['b*']] else 0.0,
                        'data_id': row_data[col_mapping['DataID']],
                        'x_position': float(row_data[col_mapping['X']]) if row_data[col_mapping['X']] else 0.0,
                        'y_position': float(row_data[col_mapping['Y']]) if row_data[col_mapping['Y']] else 0.0,
                        'sample_shape': row_data[col_mapping['Shape']] if col_mapping['Shape'] < len(row_data) else '',
                        'sample_size': row_data[col_mapping['Size']] if col_mapping['Size'] < len(row_data) else '',
                        'sample_anchor': row_data[col_mapping['Anchor']] if col_mapping['Anchor'] < len(row_data) else '',
                        'rgb_r': float(row_data[col_mapping['R']]) if col_mapping['R'] < len(row_data) and row_data[col_mapping['R']] else 0.0,
                        'rgb_g': float(row_data[col_mapping['G']]) if col_mapping['G'] < len(row_data) and row_data[col_mapping['G']] else 0.0,
                        'rgb_b': float(row_data[col_mapping['B']]) if col_mapping['B'] < len(row_data) and row_data[col_mapping['B']] else 0.0,
                        'measurement_date': row_data[col_mapping['Date']] if col_mapping['Date'] < len(row_data) else '',
                        'notes': row_data[col_mapping['Notes']] if col_mapping['Notes'] < len(row_data) else ''
                    }
                    
                    # Parse the data_id to extract image name and coordinate point
                    # Expected format: F137-S1-crp_sample1, F137-S1-crp_sample2, etc.
                    data_id = measurement['data_id']
                    
                    # Extract coordinate point from data_id (sample1 -> 1, sample2 -> 2, etc.)
                    sample_match = re.search(r'sample(\d+)$', data_id)
                    if sample_match:
                        measurement['coordinate_point'] = int(sample_match.group(1))
                        # Extract image name (everything before _sample)
                        measurement['image_name'] = re.sub(r'_sample\d+$', '', data_id)
                    else:
                        print(f"Warning: Could not parse coordinate point from data_id: {data_id}")
                        measurement['coordinate_point'] = row_idx
                        measurement['image_name'] = data_id
                    
                    measurements.append(measurement)
                    
                except (ValueError, IndexError) as e:
                    print(f"Error parsing row {row_idx}: {e}")
                    print(f"Row data: {row_data}")
                    continue
            
            print(f"Successfully parsed {len(measurements)} measurements from ODS file")
            return measurements
            
        except Exception as e:
            print(f"Error parsing ODS file: {e}")
            raise
    
    def import_to_database(self, measurements: List[Dict], sample_set_name: str) -> bool:
        """Import measurements to the specified database, completely overwriting existing data.
        
        Args:
            measurements: List of measurement dictionaries
            sample_set_name: Name of the sample set (database name)
            
        Returns:
            True if import was successful
        """
        try:
            # Get database path using same logic as ColorAnalysisDB
            from utils.naming_utils import standardize_name
            
            standardized_name = standardize_name(sample_set_name)
            clean_name = self._clean_filename(standardized_name)
            
            # Use same path resolution as ColorAnalysisDB
            stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
            if stampz_data_dir:
                color_data_dir = os.path.join(stampz_data_dir, "data", "color_analysis")
            else:
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                color_data_dir = os.path.join(current_dir, "data", "color_analysis")
            
            os.makedirs(color_data_dir, exist_ok=True)
            db_path = os.path.join(color_data_dir, f"{clean_name}.db")
            
            print(f"Importing to database: {db_path}")
            
            # Backup existing database
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(db_path):
                import shutil
                shutil.copy2(db_path, backup_path)
                print(f"Created backup: {backup_path}")
            
            # Connect and completely recreate the database
            with sqlite3.connect(db_path) as conn:
                # Drop existing tables
                conn.execute("DROP TABLE IF EXISTS color_measurements")
                conn.execute("DROP TABLE IF EXISTS measurement_sets")
                
                # Recreate tables with proper schema
                conn.execute("""
                    CREATE TABLE measurement_sets (
                        set_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        image_name TEXT NOT NULL,
                        measurement_date TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                        description TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE color_measurements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        set_id INTEGER NOT NULL,
                        coordinate_point INTEGER NOT NULL,
                        x_position REAL NOT NULL,
                        y_position REAL NOT NULL,
                        l_value REAL NOT NULL,
                        a_value REAL NOT NULL,
                        b_value REAL NOT NULL,
                        rgb_r REAL NOT NULL,
                        rgb_g REAL NOT NULL,
                        rgb_b REAL NOT NULL,
                        sample_type TEXT,
                        sample_size TEXT,
                        sample_anchor TEXT,
                        measurement_date TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                        notes TEXT,
                        FOREIGN KEY(set_id) REFERENCES measurement_sets(set_id)
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX idx_set_point 
                    ON color_measurements(set_id, coordinate_point)
                """)
                
                # Group measurements by image name
                image_groups = {}
                for measurement in measurements:
                    image_name = measurement['image_name']
                    if image_name not in image_groups:
                        image_groups[image_name] = []
                    image_groups[image_name].append(measurement)
                
                print(f"Found {len(image_groups)} unique images in the data")
                
                # Insert measurement sets and measurements
                total_inserted = 0
                for image_name, image_measurements in image_groups.items():
                    # Create measurement set
                    cursor = conn.execute("""
                        INSERT INTO measurement_sets (image_name, description)
                        VALUES (?, ?)
                    """, (image_name, f"Imported from corrected ODS file"))
                    
                    set_id = cursor.lastrowid
                    
                    # Insert measurements for this set
                    for measurement in image_measurements:
                        conn.execute("""
                            INSERT INTO color_measurements (
                                set_id, coordinate_point, x_position, y_position,
                                l_value, a_value, b_value, rgb_r, rgb_g, rgb_b,
                                sample_type, sample_size, sample_anchor,
                                measurement_date, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            set_id, measurement['coordinate_point'],
                            measurement['x_position'], measurement['y_position'],
                            measurement['l_value'], measurement['a_value'], measurement['b_value'],
                            measurement['rgb_r'], measurement['rgb_g'], measurement['rgb_b'],
                            measurement['sample_shape'], measurement['sample_size'], measurement['sample_anchor'],
                            measurement['measurement_date'], measurement['notes']
                        ))
                        total_inserted += 1
                
                conn.commit()
                print(f"Successfully imported {total_inserted} measurements across {len(image_groups)} image sets")
                
                # Verify the import
                cursor = conn.execute("SELECT COUNT(*) FROM color_measurements")
                count = cursor.fetchone()[0]
                print(f"Database now contains {count} total measurements")
                
                return True
                
        except Exception as e:
            print(f"Error importing to database: {e}")
            return False
    
    def _clean_filename(self, name: str) -> str:
        """Clean a name to be safe for use as a filename."""
        # Replace spaces and special characters with underscores
        clean = re.sub(r'[^\w\-_\.]', '_', name)
        # Remove multiple consecutive underscores
        clean = re.sub(r'_+', '_', clean)
        # Remove leading/trailing underscores
        clean = clean.strip('_')
        return clean

def main():
    """Main function to import ODS file."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import corrected ODS file back to StampZ database")
    parser.add_argument("ods_file", help="Path to the corrected ODS file")
    parser.add_argument("--sample-set", default="Semeuse_137", help="Sample set name (default: Semeuse_137)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.ods_file):
        print(f"Error: ODS file not found: {args.ods_file}")
        return False
    
    try:
        importer = ODSImporter()
        
        print(f"Parsing ODS file: {args.ods_file}")
        measurements = importer.parse_ods_file(args.ods_file)
        
        if not measurements:
            print("No measurements found in ODS file")
            return False
        
        print(f"Importing {len(measurements)} measurements to sample set: {args.sample_set}")
        success = importer.import_to_database(measurements, args.sample_set)
        
        if success:
            print("Import completed successfully!")
            return True
        else:
            print("Import failed!")
            return False
            
    except Exception as e:
        print(f"Import failed with error: {e}")
        return False

if __name__ == "__main__":
    main()
