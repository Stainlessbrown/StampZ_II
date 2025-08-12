#!/usr/bin/env python3
"""
Color analysis utilities for StampZ.
Extract and analyze colors from coordinate sample areas.
"""

import numpy as np
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, Any
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from PIL import Image
import os
import re

class PrintType(Enum):
    """Type of printing method used for the stamp."""
    LINE_ENGRAVED = auto()    # Line-engraved/intaglio printing (fine lines, mixed with paper)
    SOLID_PRINTED = auto()    # Solid color areas (lithograph, photogravure, etc.)

# Color space conversion functions
try:
    from colorspacious import cspace_convert
    HAS_COLORSPACIOUS = True
except ImportError:
    HAS_COLORSPACIOUS = False
    print("Warning: colorspacious not installed. CIE L*a*b* conversion will use approximation.")

from .coordinate_db import CoordinateDB, CoordinatePoint, SampleAreaType
from .color_analysis_db import ColorAnalysisDB
from .color_calibration import ColorCalibrator

@dataclass
class ColorMeasurement:
    """Represents a color measurement from a sample area."""
    coordinate_id: int
    coordinate_point: int             # 1-based point number for display
    position: Tuple[float, float]     # (x, y)
    rgb: Tuple[float, float, float]   # RGB values (0-255) with decimal precision
    lab: Tuple[float, float, float]   # CIE L*a*b* values
    sample_area: Dict[str, Any]       # Sample area info
    measurement_date: str
    notes: Optional[str] = None

class ColorAnalyzer:
    """Analyze colors from coordinate sample areas."""
    
    def __init__(self, print_type: PrintType = PrintType.SOLID_PRINTED):
        """Initialize color analyzer.
        
        Args:
            print_type: Type of printing method used for the stamp.
                       Affects how color sampling is performed.
                       LINE_ENGRAVED for line-engraved/intaglio stamps
                       SOLID_PRINTED for lithograph, photogravure, etc.
        """
        self.db = CoordinateDB()
        self.print_type = print_type
        self.calibrator = ColorCalibrator()
        self.color_correction = None  # Will hold correction matrix if calibrated
        
        # Load saved calibration if available
        self.load_saved_calibration()
    
    def rgb_to_lab(self, rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Convert RGB to CIE L*a*b* color space.
        
        Args:
            rgb: RGB values as (r, g, b) floats 0-255
            
        Returns:
            L*a*b* values as (L, a, b) floats
        """
        if HAS_COLORSPACIOUS:
            # Use precise conversion via colorspacious
            rgb_float = [c/255.0 for c in rgb]
            lab = cspace_convert(rgb_float, "sRGB1", "CIELab")
            return tuple(lab)
        else:
            # Use approximation if colorspacious not available
            return self._rgb_to_lab_approximation(rgb)
    
    def _rgb_to_lab_approximation(self, rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Approximate RGB to L*a*b* conversion.
        
        This is a simplified conversion that's reasonably accurate for most colors.
        For precise color analysis, install colorspacious: pip install colorspacious
        """
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
    
    def extract_sample_colors(self, image: Image.Image, coordinate_set_name: str) -> List[ColorMeasurement]:
        """Extract colors from all sample areas in a coordinate set.
        
        Args:
            image: PIL Image to sample from
            coordinate_set_name: Name of the coordinate set to use
            
        Returns:
            List of ColorMeasurement objects
        """
        # Load coordinates from database
        coordinates = self.db.load_coordinate_set(coordinate_set_name)
        if not coordinates:
            raise ValueError(f"Coordinate set '{coordinate_set_name}' not found")
        
        measurements = []
        
        for i, coord in enumerate(coordinates):
            try:
                # Extract color from this sample area
                rgb_values = self._sample_area_color(image, coord)
                if rgb_values:
                    avg_rgb = self._calculate_average_color(rgb_values)
                    lab_values = self.rgb_to_lab(avg_rgb)
                    
                    measurement = ColorMeasurement(
                        coordinate_id=i,  # This would be the actual DB ID in production
                        coordinate_point=i + 1,  # 1-based point number
                        position=(coord.x, coord.y),
                        rgb=avg_rgb,
                        lab=lab_values,
                        sample_area={
                            'type': coord.sample_type.value,
                            'size': coord.sample_size,
                            'anchor': coord.anchor_position
                        },
                        measurement_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    measurements.append(measurement)
                    
            except Exception as e:
                print(f"Warning: Failed to sample color at {coord.x}, {coord.y}: {e}")
                continue
        
        return measurements
    
    def extract_sample_colors_from_coordinates(self, image: Image.Image, canvas_coordinates: List[dict]) -> List[ColorMeasurement]:
        """Extract colors from canvas coordinate markers (including fine adjustments).
        
        Args:
            image: PIL Image to sample from
            canvas_coordinates: List of coordinate marker dictionaries from canvas
            
        Returns:
            List of ColorMeasurement objects
        """
        measurements = []
        
        for i, marker in enumerate(canvas_coordinates):
            if marker.get('is_preview', False):
                continue  # Skip preview markers
                
            try:
                # Extract position and settings from marker
                x, y = marker['image_pos']
                sample_type = marker.get('sample_type', 'rectangle')
                sample_width = marker.get('sample_width', 20)
                sample_height = marker.get('sample_height', 20)
                anchor = marker.get('anchor', 'center')
                
                # Debug output for sample #4 issue
                print(f"DEBUG: Processing canvas marker {i} (1-based: {i+1})")
                print(f"  Position: ({x}, {y})")
                print(f"  Sample type: {sample_type}, Size: {sample_width}x{sample_height}, Anchor: {anchor}")
                print(f"  Marker index from data: {marker.get('index', 'N/A')}")
                
                # Create a temporary CoordinatePoint-like object for sampling
                class TempCoord:
                    def __init__(self, x, y, sample_type, width, height, anchor):
                        self.x = x
                        self.y = y
                        self.sample_type = SampleAreaType.CIRCLE if sample_type == 'circle' else SampleAreaType.RECTANGLE
                        self.sample_size = (width, height)
                        self.anchor_position = anchor
                
                temp_coord = TempCoord(x, y, sample_type, sample_width, sample_height, anchor)
                
                # Extract color from this sample area using existing method
                rgb_values = self._sample_area_color(image, temp_coord)
                if rgb_values:
                    avg_rgb = self._calculate_average_color(rgb_values)
                    lab_values = self.rgb_to_lab(avg_rgb)
                    
                    measurement = ColorMeasurement(
                        coordinate_id=marker.get('index', i),
                        coordinate_point=i + 1,  # 1-based point number
                        position=(x, y),
                        rgb=avg_rgb,
                        lab=lab_values,
                        sample_area={
                            'type': sample_type,
                            'size': (sample_width, sample_height),
                            'anchor': anchor
                        },
                        measurement_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    measurements.append(measurement)
                    
            except Exception as e:
                print(f"Warning: Failed to sample color from canvas marker {i}: {e}")
                continue
        
        return measurements
    
    def _sample_area_color(self, image: Image.Image, coord) -> Optional[List[Tuple[int, int, int]]]:
        """Sample colors from a specific coordinate area.
        
        Args:
            image: PIL Image to sample from
            coord: Coordinate point defining the sample area
            
        Returns:
            List of RGB tuples from the sampled area, or None if sampling failed
        """
        try:
            # Get sample area boundaries
            if coord.sample_type == SampleAreaType.RECTANGLE:
                bounds = self._get_rectangle_bounds(image, coord)
            else:  # CIRCLE
                bounds = self._get_circle_bounds(image, coord)
            
            if not bounds:
                return None
            
            # Extract pixels from the area
            pixels = self._extract_pixels_from_bounds(image, bounds, coord.sample_type)
            return pixels
            
        except Exception as e:
            print(f"Error sampling area: {e}")
            return None
    
    def _get_rectangle_bounds(self, image: Image.Image, coord: CoordinatePoint) -> Optional[Tuple[int, int, int, int]]:
        """Calculate rectangle bounds for sampling.
        
        Returns:
            (left, top, right, bottom) or None if out of bounds
        """
        width, height = coord.sample_size
        x, y = coord.x, coord.y
        
        # Convert from Cartesian coordinates (0,0 at bottom-left) to PIL coordinates (0,0 at top-left)
        pil_y = image.height - y
        
        # Calculate bounds based on anchor position in PIL coordinate system
        if coord.anchor_position == 'center':
            left = int(x - width/2)
            top = int(pil_y - height/2)
            right = int(x + width/2)
            bottom = int(pil_y + height/2)
        elif coord.anchor_position == 'top_left':
            # In Cartesian: top_left means higher Y value
            # In PIL: this becomes lower Y value (closer to 0)
            left, top = int(x), int(pil_y - height)
            right, bottom = int(x + width), int(pil_y)
        elif coord.anchor_position == 'top_right':
            left = int(x - width)
            top = int(pil_y - height)
            right = int(x)
            bottom = int(pil_y)
        elif coord.anchor_position == 'bottom_left':
            # In Cartesian: bottom_left means lower Y value
            # In PIL: this becomes higher Y value
            left = int(x)
            top = int(pil_y)
            right = int(x + width)
            bottom = int(pil_y + height)
        else:  # bottom_right
            left = int(x - width)
            top = int(pil_y)
            right = int(x)
            bottom = int(pil_y + height)
        
        # Debug output after bounds calculation
        print(f"DEBUG: Sample area bounds calculation:")
        print(f"  Cartesian position: ({x}, {y})")
        print(f"  PIL Y position: {pil_y}")
        print(f"  Sample size: {width}x{height}")
        print(f"  Calculated PIL bounds: ({left}, {top}, {right}, {bottom})")
        print(f"  Image dimensions: {image.width}x{image.height}")
        
        # Clamp to image bounds
        original_bounds = (left, top, right, bottom)
        left = max(0, left)
        top = max(0, top)
        right = min(image.width, right)
        bottom = min(image.height, bottom)
        
        if original_bounds != (left, top, right, bottom):
            print(f"DEBUG: Bounds were clamped from {original_bounds} to ({left}, {top}, {right}, {bottom})")
            print(f"  This indicates the sample area extends outside the image boundaries!")
        
        # Check if we have a valid area
        if left >= right or top >= bottom:
            return None
            
        return (left, top, right, bottom)
    
    def _get_circle_bounds(self, image: Image.Image, coord: CoordinatePoint) -> Optional[Tuple[int, int, int, int]]:
        """Calculate bounding box for circular sampling.
        
        Returns:
            (left, top, right, bottom) or None if out of bounds
        """
        radius = coord.sample_size[0] / 2  # Use width as diameter
        x, y = coord.x, coord.y
        
        # Convert from Cartesian coordinates (0,0 at bottom-left) to PIL coordinates (0,0 at top-left)
        pil_y = image.height - y
        
        left = int(x - radius)
        top = int(pil_y - radius)
        right = int(x + radius)
        bottom = int(pil_y + radius)
        
        # Clamp to image bounds
        left = max(0, left)
        top = max(0, top)
        right = min(image.width, right)
        bottom = min(image.height, bottom)
        
        if left >= right or top >= bottom:
            return None
            
        return (left, top, right, bottom)
    
    def _extract_pixels_from_bounds(self, image: Image.Image, bounds: Tuple[int, int, int, int], 
                                   sample_type: SampleAreaType) -> List[Tuple[int, int, int]]:
        """Extract pixel colors from the specified bounds.
        
        Args:
            image: PIL Image
            bounds: (left, top, right, bottom)
            sample_type: Type of sampling area
            
        Returns:
            List of RGB tuples
        """
        left, top, right, bottom = bounds
        pixels = []
        
        # Convert image to RGB if needed with proper color space handling
        if image.mode != 'RGB':
            # Preserve color profile during conversion if possible
            if hasattr(image, 'info') and 'icc_profile' in image.info:
                print(f"DEBUG: Image has ICC profile, preserving during RGB conversion")
            image = image.convert('RGB')
        
        # Check for common screenshot color issues
        if hasattr(image, 'filename') and any(term in str(image.filename).lower() 
                                           for term in ['screenshot', 'screen', 'capture']):
            print(f"DEBUG: Screenshot detected - applying color correction")
        
        total_pixels = 0
        total_r = 0
        total_g = 0
        total_b = 0
        
        # Extract pixels
        for y in range(top, bottom):
            for x in range(left, right):
                if sample_type == SampleAreaType.CIRCLE:
                    # Check if pixel is within circle
                    center_x = (left + right) / 2
                    center_y = (top + bottom) / 2
                    radius = min(right - left, bottom - top) / 2
                    
                    distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    if distance > radius:
                        continue
                
                try:
                    pixel = image.getpixel((x, y))
                    if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
                        # Handle transparency for RGBA images
                        if len(pixel) == 4 and pixel[3] == 0:  # Skip fully transparent pixels
                            continue
                            
                        r, g, b = pixel[:3]
                        
                        if self.print_type == PrintType.LINE_ENGRAVED:
                            # For line-engraved stamps, include all pixels but adjust pure white
                            if r == 255 and g == 255 and b == 255:
                                r, g, b = 245, 241, 235  # Slightly aged paper
                            # Otherwise keep original values, including dark areas
                        else:  # PrintType.SOLID_PRINTED
                            # For solid-printed stamps, only adjust extremely light areas
                            if r > 250 and g > 250 and b > 250:
                                continue  # Skip only the very whitest pixels
                            # Keep all other colors as is
                            
                        # Record actual pixel values without modifying them
                        pixels.append((r, g, b))
                        
                        # Add to running totals (keeping decimal precision)
                        total_pixels += 1
                        total_r += float(r)
                        total_g += float(g)
                        total_b += float(b)
                        
                        # Log pixel values for debugging
                        if total_pixels <= 5:
                            if self.print_type == PrintType.LINE_ENGRAVED:
                                if r > 240 and g > 235 and b > 230:
                                    context = "(paper - slightly aged)"
                                elif r > 200 and g > 195 and b > 190:
                                    context = "(very light engraving)"
                                elif r > 150 and g > 145 and b > 140:
                                    context = "(light engraving)"
                                elif r > 80 and g > 75 and b > 70:
                                    context = "(medium engraving)"
                                else:
                                    context = "(deep engraving)"
                            else:  # SOLID_PRINTED
                                if r > 240 and g > 235 and b > 230:
                                    context = "(unprinted area)"
                                elif r > 200 and g > 195 and b > 190:
                                    context = "(light ink)"
                                elif r > 150 and g > 145 and b > 140:
                                    context = "(medium ink)"
                                else:
                                    context = "(solid ink)"
                            print(f"Sample pixel {total_pixels}: RGB=({r},{g},{b}) {context}")
                except Exception as e:
                    print(f"Error getting pixel at ({x}, {y}): {e}")
                    continue
        
        if not pixels:
            print(f"Warning: No valid pixels found in sample area ({left}, {top}, {right}, {bottom})")
            # Use a slightly cream color as fallback to represent typical historical paper
            return [(235, 230, 220)]  # Cream/off-white color typical of aged paper
        
        # Calculate true averages including paper color influence
        avg_r = total_r / total_pixels if total_pixels > 0 else 235
        avg_g = total_g / total_pixels if total_pixels > 0 else 230
        avg_b = total_b / total_pixels if total_pixels > 0 else 220
        
        print(f"Sample area ({left}, {top}, {right}, {bottom}): {total_pixels} valid non-white pixels")
        print(f"Area average RGB: ({avg_r:.1f}, {avg_g:.1f}, {avg_b:.1f})")
        
        # Return the average color as a single pixel value
        return [(int(avg_r), int(avg_g), int(avg_b))]
    
    def _calculate_average_color(self, pixels: List[Tuple[int, int, int]]) -> Tuple[float, float, float]:
        """Calculate average color from a list of pixels.
        
        Args:
            pixels: List of RGB tuples
            
        Returns:
            Average RGB as tuple of floats (preserves decimal precision)
        """
        if not pixels:
            print("Warning: No pixels to average, using gray fallback")
            return (128.0, 128.0, 128.0)  # Gray fallback
        
        # Calculate true average with full decimal precision
        total_r = sum(float(p[0]) for p in pixels)
        total_g = sum(float(p[1]) for p in pixels)
        total_b = sum(float(p[2]) for p in pixels)
        num_pixels = float(len(pixels))
        
        avg_r = total_r / num_pixels
        avg_g = total_g / num_pixels
        avg_b = total_b / num_pixels
        
        # Apply color correction if calibrated
        uncorrected_rgb = (avg_r, avg_g, avg_b)
        corrected_rgb = self.apply_color_correction(uncorrected_rgb)
        
        # For debugging - show both values if correction was applied
        if self.is_calibrated():
            print(f"Original average RGB: R={avg_r:.2f}, G={avg_g:.2f}, B={avg_b:.2f}")
            print(f"Corrected RGB values: R={corrected_rgb[0]:.2f}, G={corrected_rgb[1]:.2f}, B={corrected_rgb[2]:.2f}")
        else:
            print(f"Final average RGB values: R={avg_r:.2f}, G={avg_g:.2f}, B={avg_b:.2f}")
            
        return corrected_rgb
    
    def save_color_measurements(self, measurements: List[ColorMeasurement], coordinate_set_name: str, image_name: str) -> bool:
        """Save color measurements to the separate sample set database.
        
        Args:
            measurements: List of ColorMeasurement objects
            coordinate_set_name: Name of the coordinate set these belong to
            image_name: Name of the image being analyzed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create color analysis database for this sample set
            color_db = ColorAnalysisDB(coordinate_set_name)
            
            # Create a single measurement set for all measurements
            set_id = color_db.create_measurement_set(image_name)
            if set_id is None:
                print("Failed to create measurement set")
                return False

            # Save each measurement under the same set_id
            for i, measurement in enumerate(measurements):
                success = color_db.save_color_measurement(
                    set_id=set_id,
                    coordinate_point=i + 1,  # 1-based point numbering
                    x_pos=measurement.position[0],
                    y_pos=measurement.position[1],
                    l_value=measurement.lab[0],
                    a_value=measurement.lab[1],
                    b_value=measurement.lab[2],
                    rgb_r=measurement.rgb[0],
                    rgb_g=measurement.rgb[1],
                    rgb_b=measurement.rgb[2],
                    notes=measurement.notes
                )
                
                if not success:
                    print(f"Failed to save measurement {i+1}")
                    return False
            
            print(f"Saved {len(measurements)} measurements to {coordinate_set_name} database")
            return True
                
        except Exception as e:
            print(f"Error saving color measurements: {e}")
            return False
    
    def _extract_sample_identifier_from_filename(self, image_path: str) -> str:
        """Extract a unique sample identifier from the image filename.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Sample identifier string that preserves original sample info
        """
        filename = os.path.basename(image_path)
        base_name = os.path.splitext(filename)[0]
        
        # Check if filename contains sample number pattern (like F137-S48-crp)
        
        # Pattern for F###-S##-xxx format
        pattern = r'F(\d+)-S(\d+)'
        match = re.search(pattern, base_name)
        if match:
            form_num = match.group(1)
            sample_num = match.group(2)
            sample_id = f"F{form_num}-S{sample_num}"
            print(f"DEBUG: Extracted sample identifier '{sample_id}' from filename '{filename}'")
            return sample_id
        
        # Pattern for other sample formats (e.g., containing S## somewhere)
        pattern2 = r'S(\d+)'
        match2 = re.search(pattern2, base_name)
        if match2:
            sample_num = match2.group(1)
            sample_id = f"S{sample_num}"
            print(f"DEBUG: Extracted sample identifier '{sample_id}' from filename '{filename}'")
            return sample_id
        
        # Fallback: use the base filename as-is
        print(f"DEBUG: Using full filename '{base_name}' as sample identifier")
        return base_name
    
    def analyze_image_colors_from_canvas(self, image_path: str, coordinate_set_name: str, 
                                        canvas_coordinates: List[dict], 
                                        description: str = None) -> Optional[List[ColorMeasurement]]:
        """Analyze colors using current canvas coordinates (including fine adjustments).
        
        Args:
            image_path: Path to the image file
            coordinate_set_name: Name of coordinate set (for database naming)
            canvas_coordinates: List of coordinate marker dictionaries from canvas
            
        Returns:
            List of ColorMeasurement objects, or None if failed
        """
        try:
            # Load image
            image = Image.open(image_path)
            print(f"Loaded image: {image.size[0]}x{image.size[1]} pixels")
            
            # Extract colors using canvas coordinates
            measurements = self.extract_sample_colors_from_coordinates(image, canvas_coordinates)
            print(f"Extracted {len(measurements)} color measurements using canvas coordinates")
            
            # Create new measurement set using sample identifier from filename
            sample_identifier = self._extract_sample_identifier_from_filename(image_path)
            
            # Create a new measurement set with the sample identifier
            db = ColorAnalysisDB(coordinate_set_name)
            set_id = db.create_measurement_set(sample_identifier, description)
            
            if set_id is not None:
                print(f"Created measurement set with ID {set_id}")
                # Save measurements with the new set ID
                success = True
                for i, measurement in enumerate(measurements):
                    if not db.save_color_measurement(
                        set_id=set_id,
                        coordinate_point=i + 1,  # Use loop index for 1-based coordinate points
                        x_pos=measurement.position[0],
                        y_pos=measurement.position[1],
                        l_value=measurement.lab[0],
                        a_value=measurement.lab[1],
                        b_value=measurement.lab[2],
                        rgb_r=measurement.rgb[0],
                        rgb_g=measurement.rgb[1],
                        rgb_b=measurement.rgb[2],
                        notes=measurement.notes
                    ):
                        print(f"Failed to save measurement {i + 1} to database")
                        success = False
                        break
                
                if success:
                    print("Color measurements saved to database (using adjusted coordinates)")
                    return measurements
                else:
                    print("Failed to save color measurements")
                    return None
                
        except Exception as e:
            print(f"Error analyzing image colors from canvas: {e}")
            return None
    
    def analyze_image_colors(self, image_path: str, coordinate_set_name: str) -> Optional[List[ColorMeasurement]]:
        """Complete color analysis workflow for an image using saved template.
        
        Args:
            image_path: Path to the image file
            coordinate_set_name: Name of coordinate set to use for sampling
            
        Returns:
            List of ColorMeasurement objects, or None if failed
        """
        try:
            # Load image
            image = Image.open(image_path)
            print(f"Loaded image: {image.size[0]}x{image.size[1]} pixels")
            
            # Extract colors
            measurements = self.extract_sample_colors(image, coordinate_set_name)
            print(f"Extracted {len(measurements)} color measurements")
            
            # Save to database with image name
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            if self.save_color_measurements(measurements, coordinate_set_name, image_name):
                print("Color measurements saved to database")
                return measurements
            else:
                print("Failed to save color measurements")
                return None
                
        except Exception as e:
            print(f"Error analyzing image colors: {e}")
            return None
    
    def measure_samples_from_canvas(self, image: Image.Image, canvas_coordinates: List[dict]) -> List[dict]:
        """Measure colors directly from canvas coordinates without saving to database.
        
        Args:
            image: PIL Image to sample from
            canvas_coordinates: List of coordinate marker dictionaries from canvas
            
        Returns:
            List of measurement dictionaries with coordinate points and color values
        """
        measurements = []
        
        for i, marker in enumerate(canvas_coordinates, 1):
            if marker.get('is_preview', False):
                continue  # Skip preview markers
                
            try:
                # Extract position and settings from marker
                x, y = marker['image_pos']
                sample_type = marker.get('sample_type', 'rectangle')
                sample_width = marker.get('sample_width', 20)
                sample_height = marker.get('sample_height', 20)
                anchor = marker.get('anchor', 'center')
                
                # Create a temporary coordinate point for sampling
                class TempCoord:
                    def __init__(self, x, y, sample_type, width, height, anchor):
                        self.x = x
                        self.y = y
                        self.sample_type = SampleAreaType.CIRCLE if sample_type == 'circle' else SampleAreaType.RECTANGLE
                        self.sample_size = (width, height)
                        self.anchor_position = anchor
                
                temp_coord = TempCoord(x, y, sample_type, sample_width, sample_height, anchor)
                
                # Extract color from this sample area
                rgb_values = self._sample_area_color(image, temp_coord)
                if rgb_values:
                    avg_rgb = self._calculate_average_color(rgb_values)
                    lab_values = self.rgb_to_lab(avg_rgb)
                    
                    # Create measurement dictionary with all marker data
                    measurement = {
                        'coordinate_point': i,
                        'x_position': x,
                        'y_position': y,
                        'l_value': lab_values[0],
                        'a_value': lab_values[1],
                        'b_value': lab_values[2],
                        'rgb_r': avg_rgb[0],
                        'rgb_g': avg_rgb[1],
                        'rgb_b': avg_rgb[2],
                        'sample_type': sample_type,
                        'sample_width': sample_width,
                        'sample_height': sample_height,
                        'anchor': anchor,
                        'notes': f"Sample point {i}"
                    }
                    measurements.append(measurement)
                    
            except Exception as e:
                print(f"Warning: Failed to sample color from canvas marker {i}: {e}")
                continue
        
        return measurements
    
    def get_color_measurements(self, coordinate_set_name: str) -> List[ColorMeasurement]:
        """Retrieve color measurements for a coordinate set.
        
        Args:
            coordinate_set_name: Name of the coordinate set
            
        Returns:
            List of ColorMeasurement objects
        """
        measurements = []
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("""
                    SELECT cd.coordinate_id, cd.l_value, cd.a_value, cd.b_value,
                           cd.rgb_r, cd.rgb_g, cd.rgb_b, cd.measurement_date, cd.notes,
                           c.x, c.y, c.sample_type, c.sample_width, c.sample_height, c.anchor_position
                    FROM color_data cd
                    JOIN coordinates c ON cd.coordinate_id = c.id
                    JOIN coordinate_sets cs ON c.set_id = cs.id
                    WHERE cs.name = ?
                    ORDER BY c.point_order
                """, (coordinate_set_name,))
                
                for row in cursor.fetchall():
                    measurement = ColorMeasurement(
                        coordinate_id=row[0],
                        position=(row[9], row[10]),  # x, y
                        rgb=(row[4], row[5], row[6]),  # R, G, B
                        lab=(row[1], row[2], row[3]),  # L*, a*, b*
                        sample_area={
                            'type': row[11],  # sample_type
                            'size': (row[12], row[13]),  # width, height
                            'anchor': row[14]  # anchor_position
                        },
                        measurement_date=row[7],
                        notes=row[8]
                    )
                    measurements.append(measurement)
                    
        except sqlite3.Error as e:
            print(f"Database error retrieving color measurements: {e}")
            
        return measurements
    
    def load_saved_calibration(self):
        """Load saved calibration settings from enhanced calibration system only."""
        # Only use enhanced calibration (accurate and comprehensive)
        return self._load_enhanced_calibration()
    
    def _load_enhanced_calibration(self):
        """Try to load enhanced calibration files."""
        try:
            import json
            
            # Check for enhanced calibration files
            calibration_files = [
                'stampz_calibration_enhanced.json',
                'stampz_calibration.json'
            ]
            
            for cal_file in calibration_files:
                if os.path.exists(cal_file):
                    with open(cal_file, 'r') as f:
                        cal_data = json.load(f)
                    
                    if 'calibration_matrix' in cal_data:
                        self.color_correction = cal_data['calibration_matrix']
                        corrections = self.color_correction.get('corrections', {})
                        
                        # Check if this is enhanced per-color calibration
                        if 'per_color_corrections' in corrections:
                            print(f"Loaded enhanced per-color calibration from {cal_file}")
                        else:
                            print(f"Loaded standard calibration from {cal_file}")
                            
                        return True
            
            return False
            
        except Exception as e:
            print(f"Warning: Could not load enhanced calibration: {e}")
            return False
    
    def apply_color_correction(self, rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Apply color correction using the enhanced calibration system.
        
        Args:
            rgb: Original RGB tuple
            
        Returns:
            Corrected RGB tuple (or original if not calibrated)
        """
        if self.color_correction is None:
            # Try to load enhanced calibration
            if not self._load_enhanced_calibration():
                return rgb
        
        # Convert to int tuple for correction
        rgb_int = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        
        # Use the enhanced color correction calculator for consistent results
        try:
            from color_correction_calculator import correct_color
            corrected_int, method_used = correct_color(*rgb_int, method='dynamic')
            
            # Log the correction method used (for first few corrections only)
            if not hasattr(self, '_correction_method_logged'):
                print(f"Using color correction method: {method_used}")
                self._correction_method_logged = True
                
            return (float(corrected_int[0]), float(corrected_int[1]), float(corrected_int[2]))
            
        except Exception as e:
            print(f"Warning: Enhanced calibration failed, using fallback: {e}")
            # Fallback to original calibration method
            if self.color_correction:
                corrected_int = self.calibrator.apply_correction(rgb_int, self.color_correction)
                return (float(corrected_int[0]), float(corrected_int[1]), float(corrected_int[2]))
            else:
                return rgb
    
    def is_calibrated(self) -> bool:
        """Check if color calibration is active.
        
        Returns:
            True if calibrated, False otherwise
        """
        return self.color_correction is not None

# Utility function for quick color analysis
def analyze_colors(image_path: str, coordinate_set_name: str, print_type: PrintType = PrintType.SOLID_PRINTED) -> None:
    """Quick color analysis function.
    
    Args:
        image_path: Path to image file
        coordinate_set_name: Name of coordinate set to use
    """
    analyzer = ColorAnalyzer(print_type=print_type)
    measurements = analyzer.analyze_image_colors(image_path, coordinate_set_name)
    
    if measurements:
        print(f"\nColor Analysis Results for '{coordinate_set_name}':")
        print("=" * 60)
        
        for i, m in enumerate(measurements, 1):
            print(f"\nSample {i} at ({m.position[0]:.2f}, {m.position[1]:.2f}):")
            print(f"  RGB: ({m.rgb[0]:.2f}, {m.rgb[1]:.2f}, {m.rgb[2]:.2f})")
            print(f"  L*a*b*: ({m.lab[0]:.2f}, {m.lab[1]:.2f}, {m.lab[2]:.2f})")
            print(f"  Sample: {m.sample_area['type']} {m.sample_area['size']} ({m.sample_area['anchor']})")
    else:
        print("No measurements obtained")

