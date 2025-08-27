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
            
            # Table for color measurements (individual samples only)
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
                    sample_type TEXT,
                    sample_size TEXT,
                    sample_anchor TEXT,
                    measurement_date TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                    notes TEXT,
                    FOREIGN KEY(set_id) REFERENCES measurement_sets(set_id)
                )
            """)
            
            # Add essential columns to existing databases
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE color_measurements ADD COLUMN sample_type TEXT")
                print("Added sample_type column")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE color_measurements ADD COLUMN sample_size TEXT")
                print("Added sample_size column")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE color_measurements ADD COLUMN sample_anchor TEXT")
                print("Added sample_anchor column")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Index for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_set_point 
                ON color_measurements(set_id, coordinate_point)
            """)
    
    def create_measurement_set(self, image_name: str, description: str = None) -> int:
        """Create a new measurement set and return its ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if a measurement set with this image_name already exists
                cursor = conn.execute("""
                    SELECT set_id FROM measurement_sets WHERE image_name = ?
                """, (image_name,))
                existing = cursor.fetchone()
                
                if existing:
                    print(f"Using existing measurement set {existing[0]} for image '{image_name}'")
                    return existing[0]
                
                # Create new measurement set
                cursor = conn.execute("""
                    INSERT INTO measurement_sets (image_name, description)
                    VALUES (?, ?)
                """, (image_name, description))
                print(f"Created new measurement set {cursor.lastrowid} for image '{image_name}'")
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
        sample_type: Optional[str] = None,
        sample_size: Optional[str] = None,
        sample_anchor: Optional[str] = None,
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
                                sample_type = ?, sample_size = ?, sample_anchor = ?,
                                measurement_date = datetime('now', 'localtime'),
                                notes = ?
                            WHERE set_id = ? AND coordinate_point = ?
                        """, (
                            x_pos, y_pos, l_value, a_value, b_value,
                            rgb_r, rgb_g, rgb_b, sample_type, sample_size, sample_anchor,
                            notes, set_id, coordinate_point
                        ))
                        print(f"Updated existing measurement for point {coordinate_point}")
                    else:
                        # Insert new measurement
                        conn.execute("""
                            INSERT INTO color_measurements (
                                set_id, coordinate_point, x_position, y_position,
                                l_value, a_value, b_value, rgb_r, rgb_g, rgb_b,
                                sample_type, sample_size, sample_anchor, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            set_id, coordinate_point, x_pos, y_pos,
                            l_value, a_value, b_value, rgb_r, rgb_g, rgb_b,
                            sample_type, sample_size, sample_anchor, notes
                        ))
                        print(f"Inserted new measurement for set {set_id} point {coordinate_point}")
                else:
                    # Always insert (old behavior) 
                    conn.execute("""
                        INSERT INTO color_measurements (
                            set_id, coordinate_point, x_position, y_position,
                            l_value, a_value, b_value, rgb_r, rgb_g, rgb_b,
                            sample_type, sample_size, sample_anchor, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        set_id, coordinate_point, x_pos, y_pos,
                        l_value, a_value, b_value, rgb_r, rgb_g, rgb_b,
                        sample_type, sample_size, sample_anchor, notes
                    ))
                    
                return True
        except sqlite3.Error as e:
            print(f"Error saving color measurement: {e}")
            return False
    
    def save_averaged_measurement(
        self,
        set_id: int,
        averaged_lab: tuple,
        averaged_rgb: tuple,
        source_measurements: List[dict],
        image_name: str,
        notes: Optional[str] = None
    ) -> bool:
        """This method is deprecated. Use AveragedColorAnalysisDB instead.
        
        Averaged measurements are now stored in separate databases.
        Use the color analyzer's save_averaged_measurement_from_samples method instead.
        """
        print(f"WARNING: save_averaged_measurement is deprecated. Averaged measurements should be saved to separate _averages database.")
        return False
    
    def get_all_measurements(self) -> List[dict]:
        """Get all color measurements for this sample set.
        
        Returns:
            List of measurement dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First, check what columns exist in the table
                cursor = conn.execute("PRAGMA table_info(color_measurements)")
                columns = [row[1] for row in cursor.fetchall()]
                has_averaged_columns = all(col in columns for col in ['is_averaged', 'source_samples_count', 'source_sample_ids'])
                
                if has_averaged_columns:
                    # Query with averaged columns (for averaged databases)
                    cursor = conn.execute("""
                        SELECT 
                            m.id, m.set_id, s.image_name, m.measurement_date,
                            m.coordinate_point, m.x_position, m.y_position,
                            m.l_value, m.a_value, m.b_value, 
                            m.rgb_r, m.rgb_g, m.rgb_b,
                            m.sample_type, m.sample_size, m.sample_anchor,
                            m.notes, m.is_averaged, m.source_samples_count, m.source_sample_ids
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
                            'sample_type': row[13],
                            'sample_size': row[14],
                            'sample_anchor': row[15],
                            'notes': row[16],
                            'is_averaged': bool(row[17]) if row[17] is not None else False,
                            'source_samples_count': row[18],
                            'source_sample_ids': row[19]
                        })
                else:
                    # Query without averaged columns (for main databases)
                    cursor = conn.execute("""
                        SELECT 
                            m.id, m.set_id, s.image_name, m.measurement_date,
                            m.coordinate_point, m.x_position, m.y_position,
                            m.l_value, m.a_value, m.b_value, 
                            m.rgb_r, m.rgb_g, m.rgb_b,
                            m.sample_type, m.sample_size, m.sample_anchor,
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
                            'sample_type': row[13],
                            'sample_size': row[14],
                            'sample_anchor': row[15],
                            'notes': row[16],
                            'is_averaged': False,  # Main DB only contains individual measurements
                            'source_samples_count': None,
                            'source_sample_ids': None
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


class AveragedColorAnalysisDB(ColorAnalysisDB):
    """Specialized database class for averaged color measurements."""
    
    def __init__(self, sample_set_name: str):
        """Initialize averaged database with _averages suffix.
        
        Args:
            sample_set_name: Base name of the sample set (will be suffixed with _averages)
        """
        # Ensure we're working with the _averages version
        if not sample_set_name.endswith('_averages'):
            sample_set_name = f"{sample_set_name}_averages"
        
        super().__init__(sample_set_name)
    
    def _init_db(self):
        """Initialize averaged color analysis database tables with averaged measurement support."""
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
            
            # Table for averaged color measurements with extra columns
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
                    sample_type TEXT,
                    sample_size TEXT,
                    sample_anchor TEXT,
                    measurement_date TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                    notes TEXT,
                    is_averaged BOOLEAN DEFAULT 1,
                    source_samples_count INTEGER,
                    source_sample_ids TEXT,
                    FOREIGN KEY(set_id) REFERENCES measurement_sets(set_id)
                )
            """)
            
            # Add averaged measurement columns to existing databases if needed
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE color_measurements ADD COLUMN is_averaged BOOLEAN DEFAULT 1")
                print("Added is_averaged column to averaged database")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute("ALTER TABLE color_measurements ADD COLUMN source_samples_count INTEGER")
                print("Added source_samples_count column to averaged database")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute("ALTER TABLE color_measurements ADD COLUMN source_sample_ids TEXT")
                print("Added source_sample_ids column to averaged database")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Index for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_set_point 
                ON color_measurements(set_id, coordinate_point)
            """)
    
    def save_averaged_measurement(
        self,
        set_id: int,
        averaged_lab: tuple,
        averaged_rgb: tuple,
        source_measurements: List[dict],
        image_name: str,
        notes: Optional[str] = None
    ) -> bool:
        """Save an averaged color measurement to the averages database.
        
        Args:
            set_id: ID of the measurement set
            averaged_lab: Averaged L*a*b* values as (L, a, b)
            averaged_rgb: Averaged RGB values as (R, G, B)
            source_measurements: List of individual measurements that were averaged
            image_name: Name of the image being analyzed
            notes: Optional notes about the averaging
            
        Returns:
            True if save was successful
        """
        print(f"DEBUG AveragedDB: save_averaged_measurement called")
        print(f"DEBUG AveragedDB: set_id={set_id}, image_name={image_name}")
        print(f"DEBUG AveragedDB: averaged_lab={averaged_lab}, averaged_rgb={averaged_rgb}")
        print(f"DEBUG AveragedDB: source_measurements count={len(source_measurements)}")
        print(f"DEBUG AveragedDB: notes={notes}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Calculate average position from source measurements
                if source_measurements:
                    avg_x = sum(m.get('x_position', 0) for m in source_measurements) / len(source_measurements)
                    avg_y = sum(m.get('y_position', 0) for m in source_measurements) / len(source_measurements)
                else:
                    avg_x = avg_y = 0.0
                
                # Create source sample IDs string for reference
                source_ids = ','.join(str(m.get('id', '')) for m in source_measurements if m.get('id'))
                
                # Use coordinate_point = 999 to indicate this is an averaged measurement
                coordinate_point = 999
                
                # Create notes that include averaging information
                avg_notes = f"Averaged from {len(source_measurements)} samples"
                if notes:
                    avg_notes += f": {notes}"
                
                # Analyze sample parameters from source measurements
                sample_types = [m.get('sample_type', '') for m in source_measurements if m.get('sample_type')]
                sample_sizes = [m.get('sample_size', '') for m in source_measurements if m.get('sample_size')]
                sample_anchors = [m.get('sample_anchor', '') for m in source_measurements if m.get('sample_anchor')]
                
                # Determine aggregated values
                if sample_types:
                    unique_types = set(sample_types)
                    avg_sample_type = sample_types[0] if len(unique_types) == 1 else 'various'
                else:
                    avg_sample_type = 'averaged'
                
                if sample_sizes:
                    unique_sizes = set(sample_sizes)
                    avg_sample_size = sample_sizes[0] if len(unique_sizes) == 1 else 'various'
                else:
                    avg_sample_size = '20'
                
                if sample_anchors:
                    unique_anchors = set(sample_anchors)
                    avg_sample_anchor = sample_anchors[0] if len(unique_anchors) == 1 else 'various'
                else:
                    avg_sample_anchor = 'center'
                
                print(f"DEBUG AveragedDB: Averaging sample parameters - types: {set(sample_types)}, sizes: {set(sample_sizes)}, anchors: {set(sample_anchors)}")
                print(f"DEBUG AveragedDB: Result - type: {avg_sample_type}, size: {avg_sample_size}, anchor: {avg_sample_anchor}")
                
                # Insert averaged measurement
                conn.execute("""
                    INSERT INTO color_measurements (
                        set_id, coordinate_point, x_position, y_position,
                        l_value, a_value, b_value, rgb_r, rgb_g, rgb_b,
                        sample_type, sample_size, sample_anchor, notes,
                        is_averaged, source_samples_count, source_sample_ids
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    set_id, coordinate_point, avg_x, avg_y,
                    averaged_lab[0], averaged_lab[1], averaged_lab[2],
                    averaged_rgb[0], averaged_rgb[1], averaged_rgb[2],
                    avg_sample_type, avg_sample_size, avg_sample_anchor, avg_notes,
                    1, len(source_measurements), source_ids
                ))
                
                print(f"AveragedDB: Saved averaged measurement from {len(source_measurements)} samples for image '{image_name}'")
                return True
                
        except sqlite3.Error as e:
            print(f"Error saving averaged measurement to averages database: {e}")
            return False
