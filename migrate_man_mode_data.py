#!/usr/bin/env python3
"""
Utility script to create a MAN_MODE sample set database.
This will help resolve the dropdown issue in DB Examine.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.color_analysis_db import ColorAnalysisDB
from datetime import datetime

def create_man_mode_database():
    """Create a sample MAN_MODE database with sample data."""
    try:
        print("Creating MAN_MODE sample set database...")
        
        # Create the database
        db = ColorAnalysisDB('MAN_MODE')
        print(f"Created database at: {db.get_database_path()}")
        
        # Create a measurement set
        set_id = db.create_measurement_set('sample_image.jpg', 'MAN_MODE analysis set')
        print(f"Created measurement set with ID: {set_id}")
        
        if set_id:
            # Add sample measurements (you can modify these or add real data later)
            sample_measurements = [
                {
                    'coordinate_point': 1,
                    'x_pos': 100.0, 'y_pos': 150.0,
                    'l_value': 45.2, 'a_value': -2.1, 'b_value': 8.7,
                    'rgb_r': 112.0, 'rgb_g': 115.0, 'rgb_b': 98.0,
                    'notes': 'Sample measurement 1'
                },
                {
                    'coordinate_point': 2,
                    'x_pos': 200.0, 'y_pos': 250.0,
                    'l_value': 62.8, 'a_value': 15.3, 'b_value': -8.2,
                    'rgb_r': 165.0, 'rgb_g': 142.0, 'rgb_b': 178.0,
                    'notes': 'Sample measurement 2'
                },
                {
                    'coordinate_point': 3,
                    'x_pos': 300.0, 'y_pos': 180.0,
                    'l_value': 38.5, 'a_value': 22.1, 'b_value': 31.4,
                    'rgb_r': 128.0, 'rgb_g': 85.0, 'rgb_b': 42.0,
                    'notes': 'Sample measurement 3'
                }
            ]
            
            # Add each measurement to the database
            for measurement in sample_measurements:
                success = db.save_color_measurement(
                    set_id=set_id,
                    coordinate_point=measurement['coordinate_point'],
                    x_pos=measurement['x_pos'],
                    y_pos=measurement['y_pos'],
                    l_value=measurement['l_value'],
                    a_value=measurement['a_value'],
                    b_value=measurement['b_value'],
                    rgb_r=measurement['rgb_r'],
                    rgb_g=measurement['rgb_g'],
                    rgb_b=measurement['rgb_b'],
                    notes=measurement['notes']
                )
                if success:
                    print(f"Added measurement {measurement['coordinate_point']}")
                else:
                    print(f"Failed to add measurement {measurement['coordinate_point']}")
        
        print("MAN_MODE database created successfully!")
        print("You can now open DB Examine and should see 'MAN_MODE' in the Sample Set dropdown.")
        
        return True
        
    except Exception as e:
        print(f"Error creating MAN_MODE database: {e}")
        return False

def list_existing_databases():
    """List all existing sample set databases."""
    try:
        from utils.color_analysis_db import ColorAnalysisDB
        from utils.path_utils import get_color_analysis_dir
        
        data_dir = get_color_analysis_dir()
        databases = ColorAnalysisDB.get_all_sample_set_databases(data_dir)
        
        print(f"Existing sample set databases in {data_dir}:")
        if databases:
            for i, db_name in enumerate(databases, 1):
                print(f"  {i}. {db_name}")
        else:
            print("  No databases found.")
        
        return databases
        
    except Exception as e:
        print(f"Error listing databases: {e}")
        return []

if __name__ == "__main__":
    print("StampZ MAN_MODE Database Creation Utility")
    print("=" * 50)
    
    # First, list existing databases
    print("\n1. Checking existing databases...")
    existing_dbs = list_existing_databases()
    
    # Check if MAN_MODE already exists
    if 'MAN_MODE' in existing_dbs:
        print("\nMAN_MODE database already exists!")
        choice = input("Do you want to recreate it? (y/n): ").lower().strip()
        if choice != 'y':
            print("Exiting without changes.")
            sys.exit(0)
    
    # Create the MAN_MODE database
    print("\n2. Creating MAN_MODE database...")
    if create_man_mode_database():
        print("\n3. Verification - Updated database list:")
        list_existing_databases()
        print("\nSuccess! The DB Examine dropdown should now work properly.")
    else:
        print("Failed to create MAN_MODE database.")
        sys.exit(1)
