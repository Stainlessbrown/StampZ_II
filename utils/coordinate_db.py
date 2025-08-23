#!/usr/bin/env python3
"""
Database utilities for storing and retrieving coordinate sample locations.
"""

import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import os

class SampleAreaType(Enum):
    """Type of sample area for a coordinate point."""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
@dataclass
class CoordinatePoint:
    """Represents a single coordinate point with its sampling properties."""
    x: float
    y: float
    sample_type: SampleAreaType
    sample_size: Tuple[float, float]  # (width, height) for rectangle, (diameter, 0) for circle
    anchor_position: str  # center, top_left, top_right, bottom_left, bottom_right
    
    def __init__(self, x: float, y: float, sample_type: SampleAreaType,
                 sample_size: Tuple[float, float], anchor_position: str = 'center'):
        self.x = x
        self.y = y
        self.sample_type = sample_type
        self.sample_size = sample_size
        self.anchor_position = anchor_position


class CoordinateDB:
    """Handle database operations for coordinate sets using a Singleton pattern."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CoordinateDB, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database connection and create tables if needed."""
        # Only initialize once
        if CoordinateDB._initialized:
            return
        
        # Use persistent user data directory instead of relative to executable
        import sys
        if hasattr(sys, '_MEIPASS'):
            if sys.platform.startswith('linux'):
                user_data_dir = os.path.expanduser('~/.local/share/StampZ_II')
            elif sys.platform == 'darwin':
                user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ_II')
            else:
                user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ_II')
            self.db_path = os.path.join(user_data_dir, "coordinates.db")
            print(f"DEBUG: Using persistent database path: {self.db_path}")
        else:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(current_dir, "data", "coordinates.db")
            print(f"DEBUG: Using development database path: {self.db_path}")
        
        self._init_db()
        self.cleanup_temporary_data()  # Clean any leftover temporary data on startup
        
        CoordinateDB._initialized = True
    
    def _init_db(self):
        """Initialize database tables."""
        # Ensure data directory exists
        db_dir = os.path.dirname(self.db_path)
        print(f"DEBUG: Creating database directory: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
        print(f"DEBUG: Database directory exists: {os.path.exists(db_dir)}")
        
        print(f"DEBUG: Attempting to connect to database: {self.db_path}")
        with sqlite3.connect(self.db_path) as conn:
            print(f"DEBUG: Database connection successful")
            print(f"DEBUG: Database file exists: {os.path.exists(self.db_path)}")
            # Create the coordinate_sets table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coordinate_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on name for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_coordinate_sets_name 
                ON coordinate_sets(name)
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coordinates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    set_id INTEGER,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    sample_type TEXT NOT NULL,
                    sample_width REAL NOT NULL,
                    sample_height REAL NOT NULL,
                    anchor_position TEXT NOT NULL,
                    point_order INTEGER NOT NULL,
                    temporary INTEGER DEFAULT 0, -- 0 for permanent, 1 for temporary
                    FOREIGN KEY (set_id) REFERENCES coordinate_sets(id)
                )
            """)
            
            # Migration: Add temporary column if it doesn't exist
            try:
                conn.execute("ALTER TABLE coordinates ADD COLUMN temporary INTEGER DEFAULT 0")
                print("DEBUG: Added temporary column to coordinates table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("DEBUG: temporary column already exists")
                else:
                    print(f"DEBUG: Error adding temporary column: {e}")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS color_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coordinate_id INTEGER,
                    l_value REAL,      -- CIE-L* value
                    a_value REAL,      -- CIE-a* value
                    b_value REAL,      -- CIE-b* value
                    rgb_r INTEGER,     -- RGB Red (0-255)
                    rgb_g INTEGER,     -- RGB Green (0-255)
                    rgb_b INTEGER,     -- RGB Blue (0-255)
                    measurement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (coordinate_id) REFERENCES coordinates(id)
                )
            """)
    
    def save_coordinate_set(
        self,
        name: str,
        image_path: str,
        coordinates: List[CoordinatePoint]
    ) -> tuple[bool, str]:
        """Save a set of coordinates with standardized naming.
        
        Args:
            name: Name of the coordinate set
            image_path: Path to the image these coordinates are for
            coordinates: List of coordinate points
            
        Returns:
            Tuple of (success, standardized_name)
        """
        from .naming_utils import standardize_name, validate_name
        
        # Validate the original name
        is_valid, error_msg = validate_name(name)
        if not is_valid:
            return False, error_msg
        
        # Standardize the name
        standardized_name = standardize_name(name)
        
        try:
            print(f"DEBUG: Attempting to save coordinate set '{standardized_name}' to database")
            print(f"DEBUG: Database path: {self.db_path}")
            print(f"DEBUG: Number of coordinates to save: {len(coordinates)}")
            
            with sqlite3.connect(self.db_path) as conn:
                # First, check if set already exists
                cursor = conn.execute(
                    "SELECT id FROM coordinate_sets WHERE name = ?",
                    (standardized_name,)
                )
                existing_set = cursor.fetchone()
                print(f"DEBUG: Existing set found: {existing_set is not None}")
                
                if existing_set:
                    # Update existing set
                    set_id = existing_set[0]
                    conn.execute(
                        "DELETE FROM coordinates WHERE set_id = ?",
                        (set_id,)
                    )
                else:
                    # Insert new set
                    cursor = conn.execute(
                        "INSERT INTO coordinate_sets (name, image_path) VALUES (?, ?)",
                        (standardized_name, image_path)
                    )
                    set_id = cursor.lastrowid
                
                # Insert all coordinates with proper order
                for i, coord in enumerate(coordinates):
                    conn.execute("""
                        INSERT INTO coordinates (
                            set_id, x, y, sample_type, sample_width, sample_height,
                            anchor_position, point_order, temporary
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """, (
                        set_id,
                        coord.x,  # x is correct (increases right)
                        coord.y,  # y is correct (increases up)
                        coord.sample_type.value,
                        coord.sample_size[0],
                        coord.sample_size[1],
                        coord.anchor_position,
                        i,  # Maintain point order
                    ))
                
                return True, standardized_name
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def load_coordinate_set(self, name: str) -> Optional[List[CoordinatePoint]]:
        """Load a coordinate set by name.
        
        Args:
            name: Name of the coordinate set to load
            
        Returns:
            List of coordinate points or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT c.x, c.y, c.sample_type, c.sample_width, c.sample_height,
                           c.anchor_position, c.point_order
                    FROM coordinates c
                    JOIN coordinate_sets s ON c.set_id = s.id
                    WHERE s.name = ? AND (c.temporary = 0 OR c.temporary IS NULL)
                    ORDER BY c.point_order
                """, (name,))
                
                coords = []
                for row in cursor:
                    coord = CoordinatePoint(
                        x=row[0],  # x is correct (increases right)
                        y=row[1],  # y is correct (increases up)
                        sample_type=SampleAreaType(row[2]),
                        sample_size=(row[3], row[4]),
                        anchor_position=row[5]
                    )
                    coords.append(coord)
                
                return coords if coords else None
                
        except sqlite3.Error:
            return None
    
    def get_sets_for_image(self, image_path: str) -> List[str]:
        """Get names of all coordinate sets for a specific image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of set names
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM coordinate_sets WHERE image_path = ?",
                    (image_path,)
                )
                return [row[0] for row in cursor]
        except sqlite3.Error:
            return []
    
    def get_all_set_names(self) -> List[str]:
        """Get names of all coordinate sets.
        
        Returns:
            List of all set names
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT name FROM coordinate_sets")
                return [row[0] for row in cursor]
        except sqlite3.Error:
            return []
    
    def save_manual_mode_coordinates(
        self,
        name: str,
        image_path: str,
        coordinates: List[CoordinatePoint]
    ) -> tuple[bool, str]:
        """Save Manual Mode coordinates as temporary data.
        
        Args:
            name: Name of the coordinate set (typically includes 'manual_mode')
            image_path: Path to the image these coordinates are for
            coordinates: List of coordinate points
            
        Returns:
            Tuple of (success, standardized_name)
        """
        from .naming_utils import standardize_name, validate_name
        
        # Validate and standardize name as usual
        is_valid, error_msg = validate_name(name)
        if not is_valid:
            return False, error_msg
        
        standardized_name = standardize_name(name)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Insert new coordinate set
                cursor = conn.execute(
                    "INSERT INTO coordinate_sets (name, image_path) VALUES (?, ?)",
                    (standardized_name, image_path)
                )
                set_id = cursor.lastrowid
                
                # Insert coordinates as temporary
                for i, coord in enumerate(coordinates):
                    conn.execute("""
                        INSERT INTO coordinates (
                            set_id, x, y, sample_type, sample_width, sample_height,
                            anchor_position, point_order, temporary
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (
                        set_id,
                        coord.x,
                        coord.y,
                        coord.sample_type.value,
                        coord.sample_size[0],
                        coord.sample_size[1],
                        coord.anchor_position,
                        i
                    ))
                
                return True, standardized_name
                
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def cleanup_temporary_data(self) -> bool:
        """Remove all temporary coordinate data and their associated sets.
        Called on startup and can be called explicitly before app exit.
        
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all set IDs that only have temporary coordinates
                cursor = conn.execute("""
                    SELECT DISTINCT set_id 
                    FROM coordinates 
                    GROUP BY set_id 
                    HAVING MIN(temporary) = 1
                """)
                temp_set_ids = [row[0] for row in cursor]
                
                # Delete temporary coordinates
                conn.execute("DELETE FROM coordinates WHERE temporary = 1")
                
                # Delete sets that only had temporary coordinates
                if temp_set_ids:
                    conn.execute(
                        "DELETE FROM coordinate_sets WHERE id IN ({})"
                        .format(','.join('?' * len(temp_set_ids))),
                        temp_set_ids
                    )
                
                return True
                
        except sqlite3.Error:
            return False
    
    def delete_coordinate_set(self, name: str) -> bool:
        """Delete a coordinate set by name.
        
        Args:
            name: Name of the coordinate set to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First get the set ID
                cursor = conn.execute(
                    "SELECT id FROM coordinate_sets WHERE name = ?",
                    (name,)
                )
                set_row = cursor.fetchone()
                if not set_row:
                    return False
                
                set_id = set_row[0]
                
                # Delete related coordinates first (due to foreign key constraint)
                conn.execute(
                    "DELETE FROM coordinates WHERE set_id = ?",
                    (set_id,)
                )
                
                # Then delete the set itself
                conn.execute(
                    "DELETE FROM coordinate_sets WHERE id = ?",
                    (set_id,)
                )
                
                return True
        except sqlite3.Error:
            return False

