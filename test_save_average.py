#!/usr/bin/env python3
"""
Test script to simulate the Save Average functionality
"""

import sys
import os
sys.path.insert(0, '.')

# Initialize environment first
import initialize_env

from utils.color_analyzer import ColorAnalyzer

def test_save_average():
    print("=== Testing Save Average Functionality ===")
    
    # Create sample measurements like Compare view would
    sample_measurements = [
        {
            'id': 'compare_1',
            'l_value': 50.0,
            'a_value': 10.0,
            'b_value': -5.0,
            'rgb_r': 120.0,
            'rgb_g': 130.0,
            'rgb_b': 140.0,
            'x_position': 100.0,
            'y_position': 200.0,
            'sample_type': 'circle',
            'sample_width': 20,
            'sample_height': 20,
            'anchor': 'center'
        },
        {
            'id': 'compare_2',
            'l_value': 55.0,
            'a_value': 12.0,
            'b_value': -3.0,
            'rgb_r': 125.0,
            'rgb_g': 135.0,
            'rgb_b': 145.0,
            'x_position': 150.0,
            'y_position': 250.0,
            'sample_type': 'circle',
            'sample_width': 20,
            'sample_height': 20,
            'anchor': 'center'
        },
        {
            'id': 'compare_3',
            'l_value': 52.0,
            'a_value': 11.0,
            'b_value': -4.0,
            'rgb_r': 122.0,
            'rgb_g': 132.0,
            'rgb_b': 142.0,
            'x_position': 200.0,
            'y_position': 300.0,
            'sample_type': 'circle',
            'sample_width': 20,
            'sample_height': 20,
            'anchor': 'center'
        }
    ]
    
    # Create analyzer and test saving averaged measurement
    analyzer = ColorAnalyzer()
    
    sample_set_name = "NEW_TEST2"
    image_name = "TEST_IMAGE"
    notes = "Test averaged measurement from Compare mode"
    
    print(f"Calling save_averaged_measurement_from_samples...")
    print(f"  sample_set_name: {sample_set_name}")
    print(f"  image_name: {image_name}")
    print(f"  sample_measurements: {len(sample_measurements)} items")
    print(f"  notes: {notes}")
    
    success = analyzer.save_averaged_measurement_from_samples(
        sample_measurements=sample_measurements,
        sample_set_name=sample_set_name,
        image_name=image_name,
        notes=notes
    )
    
    print(f"\nResult: {success}")
    
    if success:
        print("\n=== Checking database for the saved average ===")
        # Check if it was actually saved
        import sqlite3
        db_path = f"data/color_analysis/{sample_set_name}.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM color_measurements WHERE is_averaged = 1')
        avg_count = cursor.fetchone()[0]
        print(f'Averaged measurements in database: {avg_count}')
        
        if avg_count > 0:
            cursor.execute('SELECT id, coordinate_point, l_value, a_value, b_value, rgb_r, rgb_g, rgb_b, source_samples_count FROM color_measurements WHERE is_averaged = 1')
            rows = cursor.fetchall()
            for row in rows:
                print(f'  ID: {row[0]}, Point: {row[1]}, Lab: ({row[2]:.2f}, {row[3]:.2f}, {row[4]:.2f}), RGB: ({row[5]:.2f}, {row[6]:.2f}, {row[7]:.2f}), Count: {row[8]}')
        
        conn.close()
    
    return success

if __name__ == "__main__":
    test_save_average()
