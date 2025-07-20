"""
Auto-square functionality for StampZ application.
Automatically corrects nearly-square crop areas to be perfectly square.
"""

import math
from typing import List, Tuple, Optional
from utils.geometry import Point, get_bounding_box, calculate_area


class AutoSquare:
    """Handles automatic squaring of rectangular crop areas."""
    
    @staticmethod
    def should_auto_square(vertices: List[Point], tolerance_degrees: float = 0.5) -> bool:
        """
        Determine if a polygon should be auto-squared.
        
        Args:
            vertices: List of polygon vertices
            tolerance_degrees: Tolerance for considering sides parallel
            
        Returns:
            True if polygon should be auto-squared
        """
        # Only auto-square 4-vertex polygons (rectangles/squares)
        if len(vertices) != 4:
            return False
        
        # Check if it's approximately rectangular
        return AutoSquare._is_approximately_rectangular(vertices, tolerance_degrees)
    
    @staticmethod
    def _is_approximately_rectangular(vertices: List[Point], tolerance_degrees: float) -> bool:
        """Check if a 4-vertex polygon is approximately rectangular."""
        if len(vertices) != 4:
            return False
        
        # Calculate angles between consecutive sides
        angles = []
        for i in range(4):
            p1 = vertices[(i - 1) % 4]
            p2 = vertices[i]
            p3 = vertices[(i + 1) % 4]
            
            # Calculate vectors
            v1_x, v1_y = p1.x - p2.x, p1.y - p2.y
            v2_x, v2_y = p3.x - p2.x, p3.y - p2.y
            
            # Calculate angle between vectors
            dot_product = v1_x * v2_x + v1_y * v2_y
            mag1 = math.sqrt(v1_x * v1_x + v1_y * v1_y)
            mag2 = math.sqrt(v2_x * v2_x + v2_y * v2_y)
            
            if mag1 == 0 or mag2 == 0:
                continue
                
            cos_angle = dot_product / (mag1 * mag2)
            cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp for numerical stability
            angle_rad = math.acos(cos_angle)
            angle_deg = math.degrees(angle_rad)
            angles.append(angle_deg)
        
        # Check if all angles are approximately 90 degrees
        tolerance_range = 90.0 - tolerance_degrees, 90.0 + tolerance_degrees
        return all(tolerance_range[0] <= angle <= tolerance_range[1] for angle in angles)
    
    @staticmethod
    def create_perfect_square(vertices: List[Point], method: str = 'average_side') -> List[Point]:
        """
        Create a perfect square from an approximately rectangular polygon.
        
        Args:
            vertices: List of 4 vertices defining the approximate rectangle
            method: Method to determine square size ('average_side', 'min_side', 'max_side', 'area_based')
            
        Returns:
            List of 4 vertices defining a perfect square
        """
        if len(vertices) != 4:
            raise ValueError("Auto-square only works with 4-vertex polygons")
        
        # Calculate the center point
        center_x = sum(v.x for v in vertices) / 4
        center_y = sum(v.y for v in vertices) / 4
        
        # Calculate side lengths
        side_lengths = []
        for i in range(4):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % 4]
            length = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
            side_lengths.append(length)
        
        # Determine square size based on method
        if method == 'average_side':
            square_size = sum(side_lengths) / 4
        elif method == 'min_side':
            square_size = min(side_lengths)
        elif method == 'max_side':
            square_size = max(side_lengths)
        elif method == 'area_based':
            # Calculate area and derive square size
            area = calculate_area(vertices)
            square_size = math.sqrt(area)
        else:
            square_size = sum(side_lengths) / 4  # Default to average
        
        # Calculate half diagonal (from center to corner)
        half_diagonal = square_size / math.sqrt(2)
        
        # Create perfect square vertices centered at the calculated center
        # Oriented with sides parallel to x and y axes
        square_vertices = [
            Point(center_x - half_diagonal, center_y - half_diagonal),  # Bottom-left
            Point(center_x + half_diagonal, center_y - half_diagonal),  # Bottom-right
            Point(center_x + half_diagonal, center_y + half_diagonal),  # Top-right
            Point(center_x - half_diagonal, center_y + half_diagonal),  # Top-left
        ]
        
        return square_vertices
    
    @staticmethod
    def create_oriented_square(vertices: List[Point], method: str = 'average_side') -> List[Point]:
        """
        Create a perfect square that maintains the orientation of the original polygon.
        
        Args:
            vertices: List of 4 vertices defining the approximate rectangle
            method: Method to determine square size
            
        Returns:
            List of 4 vertices defining a perfect oriented square
        """
        if len(vertices) != 4:
            raise ValueError("Auto-square only works with 4-vertex polygons")
        
        # Calculate the center point
        center_x = sum(v.x for v in vertices) / 4
        center_y = sum(v.y for v in vertices) / 4
        
        # Calculate side lengths
        side_lengths = []
        for i in range(4):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % 4]
            length = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
            side_lengths.append(length)
        
        # Determine square size
        if method == 'average_side':
            square_size = sum(side_lengths) / 4
        elif method == 'min_side':
            square_size = min(side_lengths)
        elif method == 'max_side':
            square_size = max(side_lengths)
        elif method == 'area_based':
            area = calculate_area(vertices)
            square_size = math.sqrt(area)
        else:
            square_size = sum(side_lengths) / 4
        
        # Calculate the dominant orientation from the first side
        first_side_x = vertices[1].x - vertices[0].x
        first_side_y = vertices[1].y - vertices[0].y
        first_side_angle = math.atan2(first_side_y, first_side_x)
        
        # Calculate half diagonal
        half_diagonal = square_size / math.sqrt(2)
        
        # Create square vertices maintaining the orientation
        # Start from the first vertex direction and create perpendicular sides
        angles = [
            first_side_angle - math.pi/4,      # From center to first corner
            first_side_angle + math.pi/4,      # To second corner
            first_side_angle + 3*math.pi/4,    # To third corner
            first_side_angle + 5*math.pi/4,    # To fourth corner
        ]
        
        square_vertices = []
        for angle in angles:
            x = center_x + half_diagonal * math.cos(angle)
            y = center_y + half_diagonal * math.sin(angle)
            square_vertices.append(Point(x, y))
        
        return square_vertices
    
    @staticmethod
    def get_square_crop_bounds(vertices: List[Point]) -> Tuple[float, float, float, float]:
        """
        Get the bounding box of a perfect square created from the vertices.
        
        Args:
            vertices: List of vertices
            
        Returns:
            Tuple of (min_x, min_y, max_x, max_y) for the square bounds
        """
        if AutoSquare.should_auto_square(vertices):
            # Create perfect square and get its bounds
            square_vertices = AutoSquare.create_perfect_square(vertices)
            min_point, max_point = get_bounding_box(square_vertices)
            return (min_point.x, min_point.y, max_point.x, max_point.y)
        else:
            # Return original bounds
            min_point, max_point = get_bounding_box(vertices)
            return (min_point.x, min_point.y, max_point.x, max_point.y)


# Convenience functions for integration
def auto_square_if_applicable(vertices: List[Point], 
                            tolerance_degrees: float = 0.5,
                            method: str = 'average_side') -> List[Point]:
    """
    Automatically square vertices if they represent an approximate rectangle.
    
    Args:
        vertices: Original vertices
        tolerance_degrees: Tolerance for rectangular detection
        method: Squaring method to use
        
    Returns:
        Perfect square vertices if applicable, otherwise original vertices
    """
    if AutoSquare.should_auto_square(vertices, tolerance_degrees):
        return AutoSquare.create_perfect_square(vertices, method)
    return vertices


def get_auto_square_bounds(vertices: List[Point], 
                          tolerance_degrees: float = 0.5) -> Tuple[float, float, float, float]:
    """
    Get crop bounds, auto-squaring if applicable.
    
    Args:
        vertices: Crop vertices
        tolerance_degrees: Tolerance for auto-square detection
        
    Returns:
        Crop bounds tuple (min_x, min_y, max_x, max_y)
    """
    return AutoSquare.get_square_crop_bounds(vertices)


def fine_square_adjustment(vertices: List[Point], method: str = 'preserve_center_level') -> List[Point]:
    """
    Apply fine adjustments to make a 4-sided polygon perfectly square/rectangular
    with all corners at exactly 90 degrees, regardless of initial tolerance.
    
    This is intended as a user-initiated refinement step after manual cropping.
    
    Args:
        vertices: List of 4 vertices defining the approximate rectangle
        method: Method for adjustment ('preserve_center', 'minimize_change', 'oriented_square')
        
    Returns:
        List of 4 vertices defining a perfect rectangle/square with 90° corners
        
    Raises:
        ValueError: If not exactly 4 vertices provided
    """
    if len(vertices) != 4:
        raise ValueError("Fine square adjustment only works with 4-vertex polygons")
    
    if method == 'preserve_center':
        return _fine_square_preserve_center(vertices)
    elif method == 'preserve_center_level':
        return _fine_square_preserve_center_level(vertices)
    elif method == 'minimize_change':
        return _fine_square_minimize_change(vertices)
    elif method == 'oriented_square':
        return AutoSquare.create_oriented_square(vertices, 'average_side')
    else:
        return _fine_square_preserve_center(vertices)  # Default


def _fine_square_preserve_center(vertices: List[Point]) -> List[Point]:
    """
    Create a perfect rectangle preserving the center point and average orientation.
    
    This method:
    1. Calculates the center of the current shape
    2. Determines the dominant orientation from the longest side
    3. Creates a rectangle with sides parallel to x/y axes or the dominant orientation
    4. Ensures all corners are exactly 90 degrees
    """
    # Calculate center point
    center_x = sum(v.x for v in vertices) / 4
    center_y = sum(v.y for v in vertices) / 4
    
    # Calculate side lengths to determine if we want a square or rectangle
    side_lengths = []
    for i in range(4):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % 4]
        length = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
        side_lengths.append(length)
    
    # Find the dominant orientation from the longest side
    max_length = 0
    dominant_angle = 0
    
    for i in range(4):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % 4]
        
        # Calculate length and angle of this side
        length = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
        angle = math.atan2(p2.y - p1.y, p2.x - p1.x)
        
        # Use the longest side to determine orientation
        if length > max_length:
            max_length = length
            dominant_angle = angle
    
    # Normalize angle to 0-π range (since rectangle has 180° rotational symmetry)
    best_angle = dominant_angle % math.pi
    
    # Decide on dimensions: if sides are similar, make it square
    avg_width = (side_lengths[0] + side_lengths[2]) / 2  # opposite sides
    avg_height = (side_lengths[1] + side_lengths[3]) / 2
    
    # If the sides are within 10% of each other, make it a perfect square
    size_ratio = min(avg_width, avg_height) / max(avg_width, avg_height)
    if size_ratio > 0.9:
        # Make it square using average of all sides
        size = sum(side_lengths) / 4
        width = height = size
    else:
        # Keep as rectangle but with corrected proportions
        width = avg_width
        height = avg_height
    
    # Create rectangle with the determined orientation
    half_width = width / 2
    half_height = height / 2
    
    if abs(best_angle) < 0.1 or abs(best_angle - math.pi) < 0.1:  # Horizontal alignment
        # Create axis-aligned rectangle
        return [
            Point(center_x - half_width, center_y - half_height),  # Bottom-left
            Point(center_x + half_width, center_y - half_height),  # Bottom-right
            Point(center_x + half_width, center_y + half_height),  # Top-right
            Point(center_x - half_width, center_y + half_height),  # Top-left
        ]
    else:
        # Create rotated rectangle with exact 90° corners
        cos_angle = math.cos(best_angle)
        sin_angle = math.sin(best_angle)
        
        # Calculate corner offsets
        corners = [
            (-half_width, -half_height),
            (half_width, -half_height),
            (half_width, half_height),
            (-half_width, half_height)
        ]
        
        # Rotate and translate corners
        result = []
        for dx, dy in corners:
            x = center_x + dx * cos_angle - dy * sin_angle
            y = center_y + dx * sin_angle + dy * cos_angle
            result.append(Point(x, y))
        
        return result


def _fine_square_preserve_center_level(vertices: List[Point]) -> List[Point]:
    """
    Create a perfect rectangle preserving the center point but forcing level alignment.
    
    This method:
    1. Calculates the center of the current shape
    2. Preserves the original width/height proportions (rectangular shape)
    3. Forces sides to be exactly horizontal and vertical (level/plumb)
    4. Ensures all corners are exactly 90 degrees
    5. Only makes it square if the original was already very close to square
    """
    # Calculate center point
    center_x = sum(v.x for v in vertices) / 4
    center_y = sum(v.y for v in vertices) / 4
    
    # Calculate the actual width and height of the current shape
    # by finding the bounding box
    min_x = min(v.x for v in vertices)
    max_x = max(v.x for v in vertices)
    min_y = min(v.y for v in vertices)
    max_y = max(v.y for v in vertices)
    
    current_width = max_x - min_x
    current_height = max_y - min_y
    
    # Only force it to be square if it's already very close (within 5%)
    size_ratio = min(current_width, current_height) / max(current_width, current_height)
    if size_ratio > 0.95:
        # Very close to square - make it a perfect square
        size = (current_width + current_height) / 2
        width = height = size
    else:
        # Keep as rectangle - preserve the original proportions
        width = current_width
        height = current_height
    
    # Create perfectly level rectangle (sides parallel to x/y axes)
    half_width = width / 2
    half_height = height / 2
    
    return [
        Point(center_x - half_width, center_y - half_height),  # Bottom-left
        Point(center_x + half_width, center_y - half_height),  # Bottom-right
        Point(center_x + half_width, center_y + half_height),  # Top-right
        Point(center_x - half_width, center_y + half_height),  # Top-left
    ]


def _fine_square_minimize_change(vertices: List[Point]) -> List[Point]:
    """
    Create a perfect rectangle that minimizes the change from the original vertices.
    
    This method tries to keep the vertices as close to their original positions
    as possible while ensuring 90° corners.
    """
    # This is a more complex algorithm that would solve an optimization problem
    # For now, fall back to the preserve_center method
    # TODO: Implement least-squares optimization to minimize vertex movement
    return _fine_square_preserve_center(vertices)

