#!/usr/bin/env python3
"""
Separate database utilities for color analysis data.
Each sample set gets its own database file for perfect data separation.
"""

import sqlite3
import os
import re
from typing import List, Optional
from datetime import datetime

class ColorAnalysisDB:
    """Handle database operations for color analysis data."""
    
    def __init__(self, sample_set_name: str):
        """Initialize database connection for a specific sample set with standardized naming.
        
        Args:
            sample_set_name: Name of the sample set (becomes the database name)
        """
        from .naming_utils import standardize_name
        
        # Standardize the sample set name
        self.sample_set_name = standardize_name(sample_set_name)
        
        # Clean the standardized name for use as filename
        clean_name = self._clean_filename(self.sample_set_name)
        
        # Use STAMPZ_DATA_DIR environment variable if available (for packaged apps)
        stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
        if stampz_data_dir:
            color_data_dir = os.path.join(stampz_data_dir, "data", "color_analysis")
            print(f"DEBUG: Using persistent color analysis directory: {color_data_dir}")
        else:
            # Running from source - use relative path
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            color_data_dir = os.path.join(current_dir, "data", "color_analysis")
            print(f"DEBUG: Using development color analysis directory: {color_data_dir}")
        
        os.makedirs(color_data_dir, exist_ok=True)
        
        self.db_path = os.path.join(color_data_dir, f"{clean_name}.db")
        print(f"DEBUG: Color analysis database path: {self.db_path}")
        self._init_db()
    
    def _clean_filename(self, name: str) -> str:
        """Clean a name to be safe for use as a filename."""
        # Replace spaces and special characters with underscores
        clean = re.sub(r'[^\w\-_\.]', '_', name)
        # Remove multiple consecutive underscores
        clean = re.sub(r'_+', '_', clean)
        # Remove leading/trailing underscores
        clean = clean.strip('_')
        return clean
    
    def _init_db(self):
        """Initialize color analysis database tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Table for measurement sets
            conn.execute("""
                CREATE TABLE IF NOT EXISTS measurement_sets (
                    set_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_name TEXT NOT NULL,
                    measurement_date TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                    description TEXT
                )
            """)
            
            # Table for color measurements
            conn.execute("""
                CREATE TABLE IF NOT EXISTS color_measurements (
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
                    measurement_date TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                    notes TEXT,
                    FOREIGN KEY(set_id) REFERENCES measurement_sets(set_id)
                )
            """)
            
            # Index for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_set_point 
                ON color_measurements(set_id, coordinate_point)
            """)
    
    def create_measurement_set(self, image_name: str, description: str = None) -> int:
        """Create a new measurement set and return its ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO measurement_sets (image_name, description)
                    VALUES (?, ?)
                """, (image_name, description))
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error creating measurement set: {e}")
            return None

    def save_color_measurement(
        self,
        set_id: int,
        coordinate_point: int,
        x_pos: float,
        y_pos: float,
        l_value: float,
        a_value: float,
        b_value: float,
        rgb_r: float,
        rgb_g: float,
        rgb_b: float,
        notes: Optional[str] = None,
        replace_existing: bool = True
    ) -> bool:
        """Save a color measurement with deduplication.
        
        Args:
            set_id: ID of the measurement set
            coordinate_point: Which coordinate point (1-based)
            x_pos, y_pos: Position coordinates
            l_value, a_value, b_value: CIE Lab values
            rgb_r, rgb_g, rgb_b: RGB values
            notes: Optional notes
            replace_existing: If True, replace existing measurements for same set/point
            
        Returns:
            True if save was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if replace_existing:
                    # Check if measurement already exists
                    cursor = conn.execute("""
                        SELECT id FROM color_measurements 
                        WHERE set_id = ? AND coordinate_point = ?
                    """, (set_id, coordinate_point))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing measurement
                        conn.execute("""
                            UPDATE color_measurements SET
                                x_position = ?, y_position = ?,
                                l_value = ?, a_value = ?, b_value = ?,
                                rgb_r = ?, rgb_g = ?, rgb_b = ?,
                                measurement_date = datetime('now', 'localtime'),
                                notes = ?
                            WHERE set_id = ? AND coordinate_point = ?
                        """, (
                            x_pos, y_pos, l_value, a_value, b_value,
                            rgb_r, rgb_g, rgb_b, notes, set_id, coordinate_point
                        ))
                        print(f"Updated existing measurement for point {coordinate_point}")
                    else:
                        # Insert new measurement
                        conn.execute("""
                            INSERT INTO color_measurements (
                                set_id, coordinate_point, x_position, y_position,
                                l_value, a_value, b_value, rgb_r, rgb_g, rgb_b, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            set_id, coordinate_point, x_pos, y_pos,
                            l_value, a_value, b_value, rgb_r, rgb_g, rgb_b, notes
                        ))
                        print(f"Inserted new measurement for set {set_id} point {coordinate_point}")
                else:
                    # Always insert (old behavior)
                    conn.execute("""
                        INSERT INTO color_measurements (
                            set_id, coordinate_point, x_position, y_position,
                            l_value, a_value, b_value, rgb_r, rgb_g, rgb_b, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        set_id, coordinate_point, x_pos, y_pos,
                        l_value, a_value, b_value, rgb_r, rgb_g, rgb_b, notes
                    ))
                    
                return True
        except sqlite3.Error as e:
            print(f"Error saving color measurement: {e}")
            return False
    
    def get_all_measurements(self) -> List[dict]:
        """Get all color measurements for this sample set.
        
        Returns:
            List of measurement dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        m.id, m.set_id, s.image_name, m.measurement_date,
                        m.coordinate_point, m.x_position, m.y_position,
                        m.l_value, m.a_value, m.b_value, 
                        m.rgb_r, m.rgb_g, m.rgb_b,
                        m.notes
                    FROM color_measurements m
                    JOIN measurement_sets s ON m.set_id = s.set_id
                    ORDER BY s.image_name, m.coordinate_point, m.measurement_date
                """)
                
                measurements = []
                for row in cursor:
                    measurements.append({
                        'id': row[0],
                        'set_id': row[1],
                        'image_name': row[2],
                        'measurement_date': row[3],
                        'coordinate_point': row[4],
                        'x_position': row[5],
                        'y_position': row[6],
                        'l_value': row[7],
                        'a_value': row[8],
                        'b_value': row[9],
                        'rgb_r': row[10],
                        'rgb_g': row[11],
                        'rgb_b': row[12],
                        'notes': row[13]
                    })
                
                return measurements
        except sqlite3.Error as e:
            print(f"Error retrieving measurements: {e}")
            return []
    
    def get_measurements_for_image(self, image_name: str) -> List[dict]:
        """Get all measurements for a specific image.
        
        Args:
            image_name: Name of the image
            
        Returns:
            List of measurement dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        m.id, m.set_id, s.image_name, m.measurement_date,
                        m.coordinate_point, m.x_position, m.y_position,
                        m.l_value, m.a_value, m.b_value,
                        m.rgb_r, m.rgb_g, m.rgb_b, m.notes
                    FROM color_measurements m
                    JOIN measurement_sets s ON m.set_id = s.set_id
                    WHERE s.image_name = ?
                    ORDER BY m.coordinate_point, m.measurement_date
                """, (image_name,))
                
                measurements = []
                for row in cursor:
                    measurements.append({
                        'id': row[0],
                        'set_id': row[1],
                        'image_name': row[2],
                        'measurement_date': row[3],
                        'coordinate_point': row[4],
                        'x_position': row[5],
                        'y_position': row[6],
                        'l_value': row[7],
                        'a_value': row[8],
                        'b_value': row[9],
                        'rgb_r': row[10],
                        'rgb_g': row[11],
                        'rgb_b': row[12],
                        'notes': row[13]
                    })
                
                return measurements
        except sqlite3.Error as e:
            print(f"Error retrieving measurements for image: {e}")
            return []
    
    def clear_all_measurements(self) -> bool:
        """Clear all measurements from this sample set's database.
        
        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM color_measurements")
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error clearing measurements: {e}")
            return False
    
    def cleanup_duplicates(self) -> int:
        """Remove duplicate measurements, keeping only the latest for each image/coordinate point.
        
        Returns:
            Number of duplicate measurements removed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First, count total duplicates
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM color_measurements
                """)
                total_before = cursor.fetchone()[0]
                
                # Remove duplicates, keeping only the latest measurement_date for each image/point
                conn.execute("""
                    DELETE FROM color_measurements
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id, 
                                   ROW_NUMBER() OVER (
                                       PARTITION BY set_id, coordinate_point 
                                       ORDER BY measurement_date DESC
                                   ) as rn
                            FROM color_measurements
                        ) ranked
                        WHERE rn = 1
                    )
                """)
                
                # Count remaining
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM color_measurements
                """)
                total_after = cursor.fetchone()[0]
                
                duplicates_removed = total_before - total_after
                print(f"Removed {duplicates_removed} duplicate measurements from {self.sample_set_name}")
                return duplicates_removed
                
        except sqlite3.Error as e:
            print(f"Error cleaning duplicates: {e}")
            return 0
    
    def get_database_path(self) -> str:
        """Get the path to this sample set's database file."""
        return self.db_path
    
    @staticmethod
    def get_all_sample_set_databases(data_dir: str = None) -> List[str]:
        """Get all sample set database names.
        
        Args:
            data_dir: Optional data directory path
            
        Returns:
            List of sample set names (without .db extension)
        """
        if data_dir is None:
            # Use STAMPZ_DATA_DIR environment variable if available (for packaged apps)
            stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
            if stampz_data_dir:
                data_dir = os.path.join(stampz_data_dir, "data", "color_analysis")
            else:
                # Running from source - use relative path
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                data_dir = os.path.join(current_dir, "data", "color_analysis")
        
        if not os.path.exists(data_dir):
            return []
        
        sample_sets = []
        for filename in os.listdir(data_dir):
            if filename.endswith('.db'):
                sample_sets.append(filename[:-3])  # Remove .db extension
        
        return sorted(sample_sets)

