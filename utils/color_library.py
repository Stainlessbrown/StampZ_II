#!/usr/bin/env python3
"""
Color Library System for StampZ
Manages a library of reference colors with CIE L*a*b* and Delta E 2000 comparison.
Optimized for accurate perceptual color matching.
"""

import sqlite3
import os
import math
import io
from typing import List, Tuple, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime

# Color space conversion functions - prioritizing CIE L*a*b* and Delta E 2000
try:
    from colorspacious import cspace_convert, deltaE
    HAS_COLORSPACIOUS = True
except ImportError:
    HAS_COLORSPACIOUS = False
    print("Warning: colorspacious not installed. Install with: pip install colorspacious")
    print("Delta E calculations will use approximation (less accurate).")

@dataclass
class LibraryColor:
    """Represents a reference color in the library."""
    id: Optional[int]
    name: str
    description: str
    rgb: Tuple[float, float, float]   # RGB values (0-255) for display
    lab: Tuple[float, float, float]   # CIE L*a*b* values (primary storage)
    category: str                     # e.g., "Red", "Blue", "Historical", etc.
    source: str                       # e.g., "Pantone", "Custom", "Stamp Catalog"
    date_added: str
    notes: Optional[str] = None

@dataclass
class ColorMatch:
    """Represents a color match result with Delta E 2000."""
    library_color: LibraryColor
    delta_e_2000: float
    match_quality: str  # "Excellent", "Good", "Fair", "Poor", "None"
    library_name: Optional[str] = None  # Name of the library this match came from

class ColorLibrary:
    """Manages a library of reference colors with CIE L*a*b* and Delta E 2000 comparison."""
    
    def __init__(self, library_name: str = "default"):
        """Initialize the color library.
        
        Args:
            library_name: Name of the library (creates separate database)
        """
        self.library_name = library_name
        
        # Create database path in data/color_libraries/ directory
        from .path_utils import get_color_libraries_dir
        library_dir = get_color_libraries_dir()
        
        os.makedirs(library_dir, exist_ok=True)
        
        # Clean library name for filename
        clean_name = self._clean_filename(library_name)
        self.db_path = os.path.join(library_dir, f"{clean_name}_library.db")
        
        print(f"DEBUG: ColorLibrary init - library_name: {library_name}")
        print(f"DEBUG: ColorLibrary init - library_dir: {library_dir}")
        print(f"DEBUG: ColorLibrary init - db_path: {self.db_path}")
        
        self._init_db()
    
    def _clean_filename(self, name: str) -> str:
        """Clean a name to be safe for use as a filename."""
        import re
        clean = re.sub(r'[^\w\-_\.]', '_', name)
        clean = re.sub(r'_+', '_', clean)
        clean = clean.strip('_')
        return clean

    def _validate_color_name(self, name: str) -> bool:
        """Validate color name according to the rules:

        1. Only underscores between words (no spaces)
        2. Can use Title_Case (first letter of each word can be capital)
        3. Numbers only allowed when immediately preceded by a capital letter

        Returns:
            bool: True if name is valid, False otherwise
        """
        import re

        # Check for spaces
        if ' ' in name:
            return False

        # Split into parts by underscore
        parts = name.split('_')

        # Check each part
        for part in parts:
            if not part:  # Empty part (caused by double underscore)
                return False

            # Check for numbers not preceded by capital letter
            matches = re.finditer(r'\d+', part)
            for match in matches:
                # Get the character before the number
                start = match.start()
                if start == 0 or not part[start-1].isupper():
                    return False

        return True
    
    def _init_db(self):
        """Initialize the color library database with CIE L*a*b* as primary storage."""
        with sqlite3.connect(self.db_path) as conn:
            # Library colors table - CIE L*a*b* is the authoritative color definition
            conn.execute("""
CREATE TABLE IF NOT EXISTS library_colors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    lab_l REAL NOT NULL,        -- L* (lightness) 0-100
                    lab_a REAL NOT NULL,        -- a* (green-red) typically -128 to +127
                    lab_b REAL NOT NULL,        -- b* (blue-yellow) typically -128 to +127
                    rgb_r REAL NOT NULL,        -- RGB for display purposes only
                    rgb_g REAL NOT NULL,
                    rgb_b REAL NOT NULL,
                    category TEXT NOT NULL DEFAULT 'General',
                    source TEXT NOT NULL DEFAULT 'Custom',
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    shape_type TEXT,            -- rectangle or circle
                    sample_width REAL,          -- width in pixels
                    sample_height REAL,         -- height in pixels
                    anchor_position TEXT        -- center, top_left, etc.
                )
            """)
            
            # Create indexes for faster searching
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON library_colors(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON library_colors(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON library_colors(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lab ON library_colors(lab_l, lab_a, lab_b)")
    
    def rgb_to_lab(self, rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Convert RGB to CIE L*a*b* color space using precise conversion.
        
        Args:
            rgb: RGB values as (r, g, b) floats 0-255
            
        Returns:
            L*a*b* values as (L, a, b) floats
        """
        if HAS_COLORSPACIOUS:
            # Use precise conversion via colorspacious (recommended)
            rgb_float = [c/255.0 for c in rgb]
            lab = cspace_convert(rgb_float, "sRGB1", "CIELab")
            return tuple(lab)
        else:
            # Use approximation if colorspacious not available
            print("Warning: Using approximation for RGB->Lab conversion. Install colorspacious for accuracy.")
            return self._rgb_to_lab_approximation(rgb)
    
    def lab_to_rgb(self, lab: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Convert CIE L*a*b* to RGB for display purposes.
        
        Args:
            lab: L*a*b* values as (L, a, b) floats
            
        Returns:
            RGB values as (r, g, b) floats 0-255
        """
        if HAS_COLORSPACIOUS:
            # Use precise conversion via colorspacious
            rgb_float = cspace_convert(lab, "CIELab", "sRGB1")
            # Clamp to valid RGB range and convert to 0-255
            rgb = [max(0, min(1, c)) * 255.0 for c in rgb_float]
            return tuple(rgb)
        else:
            # Use approximation if colorspacious not available
            print("Warning: Using approximation for Lab->RGB conversion. Install colorspacious for accuracy.")
            return self._lab_to_rgb_approximation(lab)
    
    def _rgb_to_lab_approximation(self, rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Approximate RGB to L*a*b* conversion (same as color_analyzer.py)."""
        r, g, b = [c/255.0 for c in rgb]
        
        # Convert to linear RGB
        def gamma_correct(c):
            return c/12.92 if c <= 0.04045 else ((c + 0.055)/1.055) ** 2.4
        
        r_lin = gamma_correct(r)
        g_lin = gamma_correct(g)
        b_lin = gamma_correct(b)
        
        # Convert to XYZ (using sRGB matrix)
        x = 0.4124564 * r_lin + 0.3575761 * g_lin + 0.1804375 * b_lin
        y = 0.2126729 * r_lin + 0.7151522 * g_lin + 0.0721750 * b_lin
        z = 0.0193339 * r_lin + 0.1191920 * g_lin + 0.9503041 * b_lin
        
        # Normalize by D65 white point
        xn, yn, zn = 0.95047, 1.0, 1.08883
        x, y, z = x/xn, y/yn, z/zn
        
        # Convert to Lab
        def f(t):
            return t**(1/3) if t > 0.008856 else (7.787 * t + 16/116)
        
        fx, fy, fz = f(x), f(y), f(z)
        
        L = 116 * fy - 16
        a = 500 * (fx - fy)
        b = 200 * (fy - fz)
        
        return (L, a, b)
    
    def _lab_to_rgb_approximation(self, lab: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Approximate L*a*b* to RGB conversion."""
        L, a, b = lab
        
        # Convert Lab to XYZ
        fy = (L + 16) / 116
        fx = a / 500 + fy
        fz = fy - b / 200
        
        def f_inv(t):
            return t**3 if t**3 > 0.008856 else (t - 16/116) / 7.787
        
        x = f_inv(fx) * 0.95047  # D65 white point
        y = f_inv(fy) * 1.0
        z = f_inv(fz) * 1.08883
        
        # Convert XYZ to linear RGB
        r_lin = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
        g_lin = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
        b_lin = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z
        
        # Convert to sRGB
        def gamma_uncorrect(c):
            c = max(0, min(1, c))  # Clamp
            return 12.92 * c if c <= 0.0031308 else 1.055 * (c**(1/2.4)) - 0.055
        
        r = gamma_uncorrect(r_lin) * 255
        g = gamma_uncorrect(g_lin) * 255
        b = gamma_uncorrect(b_lin) * 255
        
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    
    def calculate_delta_e_2000(self, lab1: Tuple[float, float, float], 
                              lab2: Tuple[float, float, float]) -> float:
        """Calculate Delta E using CAM02-UCS (available) or CIE76 as fallback.
        
        Args:
            lab1: First Lab color (L, a, b)
            lab2: Second Lab color (L, a, b)
            
        Returns:
            Delta E value (CAM02-UCS if colorspacious available, otherwise CIE76)
        """
        if HAS_COLORSPACIOUS:
            import numpy as np
            lab1_array = np.array(lab1)
            lab2_array = np.array(lab2)
            return deltaE(lab1_array, lab2_array, input_space="CIELab", uniform_space="CAM02-UCS")
        else:
            return self._delta_e_76_approximation(lab1, lab2)
    
    def _delta_e_76_approximation(self, lab1: Tuple[float, float, float], 
                                 lab2: Tuple[float, float, float]) -> float:
        """Approximate CIE76 Delta E calculation (less accurate than Delta E 2000)."""
        l1, a1, b1 = lab1
        l2, a2, b2 = lab2
        
        delta_l = l1 - l2
        delta_a = a1 - a2
        delta_b = b1 - b2
        
        return math.sqrt(delta_l**2 + delta_a**2 + delta_b**2)
    
    def add_color(self, name: str, rgb: Tuple[float, float, float] = None,
                  lab: Tuple[float, float, float] = None,
                  description: str = "", category: str = "General",
                  source: str = "Custom", notes: str = None) -> bool:
        """Add a new color to the library. Preferred input is CIE L*a*b*.
        
        Args:
            name: Base name for the color (will be auto-incremented if exists).
                 Must follow naming rules:
                 - Only underscores between words (no spaces)
                 - Can use Title_Case (first letter of each word can be capital)
                 - Numbers only allowed when immediately preceded by a capital letter
            rgb: RGB values (0-255) - will be converted to Lab
            lab: CIE L*a*b* values - preferred input method
            description: Description of the color
            category: Color category
            source: Source of the color definition
            notes: Optional notes
            
        Returns:
            True if successful, False on error
        """
        if lab is None and rgb is None:
            raise ValueError("Either rgb or lab values must be provided")
            
        # Validate color name - relaxed validation for imports
        if not name or not name.strip():
            raise ValueError("Color name cannot be empty")
        
        try:
            print(f"\nDEBUG: add_color called with name='{name}', rgb={rgb}, lab={lab}")
            print(f"DEBUG: Database path: {self.db_path}")
            
            # If Lab values provided, use them as authoritative
            if lab is not None:
                lab_values = lab
                # Convert to RGB for display
                rgb_values = self.lab_to_rgb(lab)
            else:
                # Convert RGB to Lab as authoritative
                lab_values = self.rgb_to_lab(rgb)
                rgb_values = rgb
            
            print(f"DEBUG: Final values - Lab: {lab_values}, RGB: {rgb_values}")
            
            with sqlite3.connect(self.db_path) as conn:
                # Check if name exists and generate unique name if needed
                base_name = name
                counter = 0
                final_name = base_name
                
                while True:
                    try:
                        print(f"DEBUG: Attempting to insert color '{final_name}' into database")
                        conn.execute("""
                            INSERT INTO library_colors (
                                name, description, lab_l, lab_a, lab_b,
                                rgb_r, rgb_g, rgb_b, category, source, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            final_name, description, lab_values[0], lab_values[1], lab_values[2],
                            rgb_values[0], rgb_values[1], rgb_values[2], category, source, notes
                        ))
                        print(f"DEBUG: INSERT statement executed, now committing...")
                        
                        # Explicit commit with detailed error handling
                        try:
                            conn.commit()
                            print(f"DEBUG: Commit successful for '{final_name}'")
                        except sqlite3.DatabaseError as commit_err:
                            print(f"DEBUG: Commit failed: {commit_err}")
                            raise
                        except Exception as commit_err:
                            print(f"DEBUG: Unexpected commit error: {commit_err}")
                            raise
                        
                        print(f"DEBUG: Successfully inserted color '{final_name}' into database")
                        
                        # Verify the insert by querying back
                        cursor = conn.execute("SELECT COUNT(*) FROM library_colors WHERE name = ?", (final_name,))
                        count = cursor.fetchone()[0]
                        print(f"DEBUG: Verification - Found {count} rows with name '{final_name}'")
                        
                        # Also check total rows in database
                        cursor = conn.execute("SELECT COUNT(*) FROM library_colors")
                        total_count = cursor.fetchone()[0]
                        print(f"DEBUG: Total colors in database: {total_count}")
                        
                        break  # If successful, exit loop
                    except sqlite3.IntegrityError as e:
                        # Name exists, try next number
                        print(f"DEBUG: Name '{final_name}' already exists, trying next number")
                        counter += 1
                        final_name = f"{base_name}_{counter}" if counter > 0 else base_name
                
                print(f"Added color '{final_name}' to library (L*a*b*: {lab_values[0]:.2f}, {lab_values[1]:.2f}, {lab_values[2]:.2f}, RGB: {rgb_values[0]:.2f}, {rgb_values[1]:.2f}, {rgb_values[2]:.2f})")
                return True
                
        except Exception as e:
            print(f"Error adding color: {e}")
            return False
    
    def get_color_by_name(self, name: str) -> Optional[LibraryColor]:
        """Get a color by name from the library."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, name, description, lab_l, lab_a, lab_b,
                           rgb_r, rgb_g, rgb_b, category, source, date_added, notes
                    FROM library_colors WHERE name = ?
                """, (name,))
                
                row = cursor.fetchone()
                if row:
                    return LibraryColor(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        lab=(row[3], row[4], row[5]),
                        rgb=(row[6], row[7], row[8]),
                        category=row[9],
                        source=row[10],
                        date_added=row[11],
                        notes=row[12]
                    )
                    
        except Exception as e:
            print(f"Error retrieving color: {e}")
            
        return None
    
    def get_all_colors(self, category: str = None) -> List[LibraryColor]:
        """Get all colors from the library, optionally filtered by category."""
        colors = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                if category:
                    cursor = conn.execute("""
                        SELECT id, name, description, lab_l, lab_a, lab_b,
                               rgb_r, rgb_g, rgb_b, category, source, date_added, notes
                        FROM library_colors WHERE category = ?
                        ORDER BY name
                    """, (category,))
                else:
                    cursor = conn.execute("""
                        SELECT id, name, description, lab_l, lab_a, lab_b,
                               rgb_r, rgb_g, rgb_b, category, source, date_added, notes
                        FROM library_colors
                        ORDER BY category, name
                    """)
                
                for row in cursor:
                    colors.append(LibraryColor(
                        id=row[0], name=row[1], description=row[2],
                        lab=(row[3], row[4], row[5]),  # Lab is primary
                        rgb=(row[6], row[7], row[8]),  # RGB for display
                        category=row[9], source=row[10],
                        date_added=row[11], notes=row[12]
                    ))
                    
        except Exception as e:
            print(f"Error retrieving colors: {e}")
            
        return colors
    
    def get_categories(self) -> List[str]:
        """Get all categories in the library."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT DISTINCT category FROM library_colors ORDER BY category")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error retrieving categories: {e}")
            return []
    
    def find_closest_matches(self, sample_lab: Tuple[float, float, float] = None,
                           sample_rgb: Tuple[float, float, float] = None,
                           max_delta_e: float = 5.0,
                           max_results: int = 3,
                           include_library_name: bool = False) -> List[ColorMatch]:
        """Find the closest color matches using Delta E 2000.
        
        Args:
            sample_lab: CIE L*a*b* color to match against (preferred)
            sample_rgb: RGB color to match against (will be converted to Lab)
            max_delta_e: Maximum Delta E for a match (default 5.0)
            max_results: Maximum number of results to return
            
        Returns:
            List of ColorMatch objects, sorted by Delta E 2000 (best first)
            Returns empty list if no matches within threshold
        """
        if sample_lab is None and sample_rgb is None:
            raise ValueError("Either sample_lab or sample_rgb must be provided")
        
        # Convert to Lab if RGB provided
        if sample_lab is None:
            sample_lab = self.rgb_to_lab(sample_rgb)
        
        matches = []
        library_colors = self.get_all_colors()
        
        for lib_color in library_colors:
            # Calculate Delta E 2000 using Lab values
            delta_e_value = self.calculate_delta_e_2000(sample_lab, lib_color.lab)
            
            # Only include if within threshold
            if delta_e_value <= max_delta_e:
                # Determine match quality based on Delta E 2000 standards
                if delta_e_value <= 1.0:
                    quality = "Excellent"  # Imperceptible difference
                elif delta_e_value <= 2.5:
                    quality = "Good"       # Perceptible but acceptable
                elif delta_e_value <= 5.0:
                    quality = "Fair"       # Clearly perceptible
                else:
                    quality = "Poor"       # Very noticeable difference
                
                matches.append(ColorMatch(
                    library_color=lib_color,
                    delta_e_2000=delta_e_value,
                    match_quality=quality,
                    library_name=self.library_name if include_library_name else None
                ))
        
        # Sort by Delta E 2000 (best matches first)
        matches.sort(key=lambda m: m.delta_e_2000)
        
        # Return top results
        return matches[:max_results]
    
    def compare_sample_to_library(self, sample_lab: Tuple[float, float, float] = None,
                                 sample_rgb: Tuple[float, float, float] = None,
                                 threshold: float = 5.0) -> Dict[str, Any]:
        """Compare a sample color to the entire library and return comprehensive results.
        
        Args:
            sample_lab: CIE L*a*b* color to compare (preferred)
            sample_rgb: RGB color to compare (will be converted to Lab)
            threshold: Delta E threshold for matches
            
        Returns:
            Dictionary with sample info, matches, and statistics
        """
        if sample_lab is None and sample_rgb is None:
            raise ValueError("Either sample_lab or sample_rgb must be provided")
        
        # Ensure we have both Lab and RGB
        if sample_lab is None:
            sample_lab = self.rgb_to_lab(sample_rgb)
            sample_rgb_display = sample_rgb
        else:
            sample_rgb_display = self.lab_to_rgb(sample_lab)
        
        # Find matches
        matches = self.find_closest_matches(sample_lab=sample_lab, max_delta_e=threshold, max_results=3)
        
        # Calculate statistics
        total_colors = self.get_color_count()
        matches_found = len(matches)
        
        # Determine overall result
        if matches_found == 0:
            overall_result = "none"
            best_match_delta_e = None
        else:
            overall_result = "matches_found"
            best_match_delta_e = matches[0].delta_e_2000
        
        return {
            'sample': {
                'lab': sample_lab,
                'rgb': sample_rgb_display
            },
            'matches': matches,
            'statistics': {
                'total_library_colors': total_colors,
                'matches_found': matches_found,
                'threshold_used': threshold,
                'best_match_delta_e': best_match_delta_e
            },
            'result': overall_result
        }
    
    def update_color(self, color_id: int, **kwargs) -> bool:
        """Update an existing color in the library."""
        try:
            # Build update query dynamically
            update_fields = []
            values = []
            
            for field, value in kwargs.items():
                if field == 'name':
                    # Validate new name if it's being updated
                    if not self._validate_color_name(value):
                        raise ValueError(
                            "Invalid color name. Rules:\n"
                            "- Use underscores between words (no spaces)\n"
                            "- Can use Title_Case\n"
                            "- Numbers must be preceded by a capital letter (e.g., F137_crimson)"
                        )
                    update_fields.append(f"{field} = ?")
                    values.append(value)
                elif field in ['description', 'category', 'source', 'notes']:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
                elif field == 'lab':
                    # Update Lab values and recalculate RGB
                    lab = value
                    rgb = self.lab_to_rgb(lab)
                    update_fields.extend(['lab_l = ?', 'lab_a = ?', 'lab_b = ?'])
                    update_fields.extend(['rgb_r = ?', 'rgb_g = ?', 'rgb_b = ?'])
                    values.extend([lab[0], lab[1], lab[2], rgb[0], rgb[1], rgb[2]])
                elif field == 'rgb':
                    # Update RGB and recalculate Lab
                    rgb = value
                    lab = self.rgb_to_lab(rgb)
                    update_fields.extend(['rgb_r = ?', 'rgb_g = ?', 'rgb_b = ?'])
                    update_fields.extend(['lab_l = ?', 'lab_a = ?', 'lab_b = ?'])
                    values.extend([rgb[0], rgb[1], rgb[2], lab[0], lab[1], lab[2]])
            
            if not update_fields:
                return False
            
            values.append(color_id)
            
            with sqlite3.connect(self.db_path) as conn:
                query = f"UPDATE library_colors SET {', '.join(update_fields)} WHERE id = ?"
                conn.execute(query, values)
                return True
                
        except Exception as e:
            print(f"Error updating color: {e}")
            return False
    
    def remove_color(self, color_id: int) -> bool:
        """Remove a color from the library."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM library_colors WHERE id = ?", (color_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error removing color: {e}")
            return False
    
    def get_color_count(self) -> int:
        """Get the total number of colors in the library."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM library_colors")
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting color count: {e}")
            return 0

    def export_library(self, filename: str) -> bool:
        """Export library to CSV format with L*a*b* values.
        
        CSV Format:
        name,description,lab_l,lab_a,lab_b,category,source,notes
        
        Args:
            filename: Path to save CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import csv
            
            colors = self.get_all_colors()
            
            # Use 'wb' mode and encode manually to ensure consistent line endings
            with open(filename, 'wb') as csvfile:
                # Create a text IO wrapper with universal newlines
                text_wrapper = io.TextIOWrapper(
                    csvfile,
                    encoding='utf-8',
                    newline='',
                    write_through=True
                )
                
                writer = csv.writer(text_wrapper)
                
                # Write header
                writer.writerow(['name', 'description', 'lab_l', 'lab_a', 'lab_b', 'category', 'source', 'notes'])
                
                # Write color data
                for color in colors:
                    writer.writerow([
                        color.name,
                        color.description,
                        color.lab[0],  # L*
                        color.lab[1],  # a*
                        color.lab[2],  # b*
                        color.category,
                        color.source,
                        color.notes or ''
                    ])
            
            print(f"Exported {len(colors)} colors to {filename}")
            return True
            
        except Exception as e:
            print(f"Error exporting library: {e}")
            return False
    
    def import_library(self, filename: str, library_name: Optional[str] = None, replace_existing: bool = False, debug_callback: Optional[Callable[[str], None]] = None) -> int:
        """Import library from CSV format with L*a*b* values.
        If library_name is provided and doesn't exist, a new library is created.
        
        Expected CSV Format (flexible column order):
        - Required: name, lab_l, lab_a, lab_b
        - Optional: description, category, source, notes
        - Alternative L*a*b* column names: L*, a*, b*, L, a, b
        
        Args:
            filename: Path to CSV file
            replace_existing: If True, replace colors with same name
            
        Returns:
            Number of colors imported
        """
        try:
            import csv
            
            imported_count = 0
            
            # Override current library if specified
            if library_name:
                self.library_name = library_name
                self._init_db()
            # Open file with universal newline handling
            with open(filename, 'r', encoding='utf-8', newline='') as csv_file:
                # Create reader with explicit header handling
                reader = csv.DictReader(csv_file)
                
                # Map column names (case-insensitive, flexible naming)
                header_map = {}
                has_rgb = False
                has_lab = False
                
                for col in reader.fieldnames:
                    col_lower = col.lower().strip()
                    
                    # Name mapping
                    if col_lower in ['name', 'color_name', 'color']:
                        header_map['name'] = col
                    
                    # L*a*b* mapping - flexible column names
                    elif col_lower in ['lab_l', 'l*', 'l_star', 'l', 'lightness']:
                        header_map['lab_l'] = col
                        has_lab = True
                    elif col_lower in ['lab_a', 'a*', 'a_star', 'a', 'green_red']:
                        header_map['lab_a'] = col
                        has_lab = True
                    elif col_lower in ['lab_b', 'b*', 'b_star', 'b', 'blue_yellow']:
                        header_map['lab_b'] = col
                        has_lab = True
                    
                    # RGB mapping - support various common formats
                    elif col_lower in ['rgb_r', 'r', 'red']:
                        header_map['rgb_r'] = col
                        has_rgb = True
                    elif col_lower in ['rgb_g', 'g', 'green']:
                        header_map['rgb_g'] = col
                        has_rgb = True
                    elif col_lower in ['rgb_b', 'b', 'blue']:
                        header_map['rgb_b'] = col
                        has_rgb = True
                    
                    # Optional fields
                    elif col_lower in ['description', 'desc', 'comment']:
                        header_map['description'] = col
                    elif col_lower in ['category', 'type', 'group']:
                        header_map['category'] = col
                    elif col_lower in ['source', 'origin', 'reference']:
                        header_map['source'] = col
                    elif col_lower in ['notes', 'note', 'remarks']:
                        header_map['notes'] = col
                
                # Store all rows in memory to ensure we capture everything
                all_rows = list(reader)
                print(f"DEBUG: Total rows read from CSV: {len(all_rows)}")
                print("DEBUG: First few rows:")
                for i, row in enumerate(all_rows[:5]):
                    print(f"Row {i+1}: {dict(row)}")
                
                # Validate required columns based on color space
                if not has_lab and not has_rgb:
                    raise ValueError(
                        "CSV must contain either LAB values (lab_l,lab_a,lab_b) or "
                        "RGB values (rgb_r,rgb_g,rgb_b). Neither found."
                    )
                
                if has_rgb and not all(x in header_map for x in ['rgb_r', 'rgb_g', 'rgb_b']):
                    raise ValueError("If using RGB, all components (R,G,B) must be present")
                
                if has_lab and not all(x in header_map for x in ['lab_l', 'lab_a', 'lab_b']):
                    raise ValueError("If using LAB, all components (L,a,b) must be present")
                
                if 'name' not in header_map:
                    raise ValueError("Column 'name' is required")
                
                if debug_callback:
                    debug_callback(f"Importing colors with columns: {list(header_map.keys())}")
                else:
                    print(f"Importing colors with columns: {list(header_map.keys())}")
                
                if debug_callback:
                    debug_callback("Starting color import...")
                else:
                    print("DEBUG: Starting color import...")
                # Store original names for comparison
                original_names = []
                # Import colors from stored rows
                for row_num, row in enumerate(all_rows, start=1):
                    try:
                        # Store original name before processing
                        try:
                            orig_name = row[header_map['name']]
                            if orig_name is None:
                                print(f"Row {row_num}: Skipping - name is None")
                                continue
                            orig_name = orig_name.strip()
                            if not orig_name:
                                print(f"Row {row_num}: Skipping - name is empty after stripping")
                                continue
                            original_names.append(orig_name)
                        except Exception as e:
                            print(f"Error processing name in row {row_num}: {e}")
                            continue

                        # Debug print each row with more detail
                        if debug_callback:
                            debug_callback(f"Processing row {row_num}: Name='{orig_name}' | {dict(row)}")
                        else:
                            print(f"DEBUG: Processing row {row_num}: Name='{orig_name}' | {dict(row)}")
                        # Extract and validate required values
                        try:
                            name = row[header_map['name']].strip()
                        except KeyError as e:
                            if debug_callback:
                                debug_callback(f"KeyError accessing name: {e}")
                                debug_callback(f"Available columns: {list(row.keys())}")
                                debug_callback(f"Header map: {header_map}")
                            else:
                                print(f"DEBUG: KeyError accessing name: {e}")
                                print(f"DEBUG: Available columns: {list(row.keys())}")
                                print(f"DEBUG: Header map: {header_map}")
                            continue
                            
                        if not name:
                            print(f"Row {row_num}: Skipping - empty name")
                            continue
                        
                        try:
                            # Get color values based on what's available
                            if has_lab:
                                lab_l = float(row[header_map['lab_l']])
                                lab_a = float(row[header_map['lab_a']])
                                lab_b = float(row[header_map['lab_b']])
                                lab = (lab_l, lab_a, lab_b)
                                rgb = self.lab_to_rgb(lab)  # Convert to RGB for display
                            else:  # Using RGB
                                rgb_r = float(row[header_map['rgb_r']])
                                rgb_g = float(row[header_map['rgb_g']])
                                rgb_b = float(row[header_map['rgb_b']])
                                rgb = (rgb_r, rgb_g, rgb_b)
                                lab = self.rgb_to_lab(rgb)  # Convert to LAB for storage
                                lab_l, lab_a, lab_b = lab
                        except (KeyError, ValueError) as e:
                            if debug_callback:
                                debug_callback(f"Error processing LAB values in row {row_num}: {e}")
                                debug_callback(f"Row values: {dict(row)}")
                            else:
                                print(f"DEBUG: Error processing LAB values in row {row_num}: {e}")
                                print(f"DEBUG: Row values: {dict(row)}")
                            continue
                        lab = (lab_l, lab_a, lab_b)
                        
                        # Validate L*a*b* ranges
                        if not (0 <= lab_l <= 100):
                            print(f"Row {row_num}: Warning - L* value {lab_l} outside normal range (0-100)")
                        if not (-128 <= lab_a <= 127):
                            print(f"Row {row_num}: Warning - a* value {lab_a} outside normal range (-128 to 127)")
                        if not (-128 <= lab_b <= 127):
                            print(f"Row {row_num}: Warning - b* value {lab_b} outside normal range (-128 to 127)")
                        
                        # Extract optional values
                        description = row.get(header_map.get('description', ''), name).strip()
                        category = row.get(header_map.get('category', ''), 'Imported').strip()
                        source = row.get(header_map.get('source', ''), 'CSV Import').strip()
                        notes = row.get(header_map.get('notes', ''), '').strip() or None
                        
                        # Debug print the values being processed
                        print(f"DEBUG: Processing '{name}' with LAB values: {lab}")
                        
                        # Handle duplicates by appending numbers if needed
                        if not replace_existing:
                            base_name = name
                            counter = 0
                            final_name = base_name
                            
                            while self.get_color_by_name(final_name):
                                counter += 1
                                final_name = f"{base_name}_{counter}"
                            
                            if counter > 0:
                                print(f"Row {row_num}: Renaming '{name}' to '{final_name}' to avoid duplicate")
                                name = final_name
                        
                        # Add or update color
                        success = self.add_color(
                            name=name,
                            lab=lab,
                            description=description,
                            category=category,
                            source=source,
                            notes=notes
                        )
                        
                        if success:
                            imported_count += 1
                            if row_num <= 10:  # Show first 10 for verification
                                print(f"Imported: {name} - L*a*b*({lab_l:.2f}, {lab_a:.2f}, {lab_b:.2f})")
                        else:
                            print(f"Row {row_num}: Failed to import '{name}'")
                            
                    except (ValueError, KeyError) as e:
                        print(f"Row {row_num}: Error importing '{row.get(header_map.get('name', ''), 'unnamed')}': {e}")
                        continue
            
                # Get accurate row count, ensuring proper handling of last line
                with open(filename, 'r', encoding='utf-8') as f:
                    # Add temporary newline if missing
                    content = f.read()
                    if not content.endswith('\n'):
                        content += '\n'
                    from io import StringIO
                    csv_io = StringIO(content)
                    total_rows = sum(1 for row in csv.DictReader(csv_io))
                print(f"\nTotal rows in CSV (excluding header): {total_rows}")
                print("\nProcessed rows:")
                for i, name in enumerate(original_names, 1):
                    print(f"Row {i}: {name}")
                if debug_callback:
                    debug_callback(f"Successfully imported {imported_count} colors from {filename} (total rows: {total_rows})")
                if imported_count != total_rows:
                        debug_callback("Warning: Some rows were skipped during import:")
                        debug_callback(f"Total rows in file: {total_rows}")
                        debug_callback(f"Successfully imported: {imported_count}")
                        debug_callback(f"Difference: {total_rows - imported_count}")
                        # Compare with final state
                        final_colors = self.get_all_colors()
                        final_names = set(c.name for c in final_colors)
                        original_names_set = set(original_names)
                        missing_names = original_names_set - final_names
                        if missing_names:
                            debug_callback("\nMissing colors:")
                            for name in sorted(missing_names):
                                debug_callback(f"  - {name}")
                else:
                    print(f"Successfully imported {imported_count} colors from {filename} (total rows: {total_rows})")
                    if imported_count != total_rows:
                        print("Warning: Some rows were skipped during import:")
                        print(f"Total rows in file: {total_rows}")
                        print(f"Successfully imported: {imported_count}")
                        print(f"Difference: {total_rows - imported_count}")
            return imported_count
            
        except Exception as e:
            print(f"Error importing library: {e}")
            return 0
    
    def _row_to_color(self, row) -> LibraryColor:
        """Convert database row to LibraryColor object."""
        return LibraryColor(
            id=row[0], name=row[1], description=row[2],
            lab=(row[3], row[4], row[5]),  # Lab is primary
            rgb=(row[6], row[7], row[8]),  # RGB for display
            category=row[9], source=row[10],
            date_added=row[11], notes=row[12]
        )


# Utility functions for creating specialized color libraries

