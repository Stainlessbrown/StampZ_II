"""
Geometry utilities for the StampZ application.
Handles vertex management, polygon validation, and geometric calculations.
"""

from typing import List, Tuple, Optional
import math
from enum import Enum, auto


class Point:
    """
    Represents a 2D point/vertex with x, y coordinates.
    """
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"
    
    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y

    def distance_to(self, other: 'Point') -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def as_tuple(self) -> Tuple[float, float]:
        """Return point as (x, y) tuple."""
        return (self.x, self.y)


def orientation(p: Point, q: Point, r: Point) -> int:
    """
    Determine the orientation of triplet (p, q, r).
    
    Returns:
     0 --> Points are collinear
     1 --> Clockwise
    -1 --> Counterclockwise
    """
    val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)
    if val == 0:
        return 0
    return 1 if val > 0 else -1


def is_convex_polygon(vertices: List[Point]) -> bool:
    """
    Check if a polygon is convex.
    
    Args:
        vertices: List of vertices defining the polygon
        
    Returns:
        True if the polygon is convex, False otherwise
    """
    if len(vertices) < 3:
        return False

    # Get orientation of first triplet
    prev_orientation = orientation(vertices[-2], vertices[-1], vertices[0])
    
    for i in range(len(vertices)):
        curr_orientation = orientation(
            vertices[i-1],
            vertices[i],
            vertices[(i+1) % len(vertices)]
        )
        
        # If orientation changes, polygon is not convex
        if curr_orientation != prev_orientation and curr_orientation != 0:
            return False
            
        prev_orientation = curr_orientation

    return True


def is_self_intersecting(vertices: List[Point]) -> bool:
    """
    Check if a polygon's edges intersect with each other.
    
    Args:
        vertices: List of vertices defining the polygon
        
    Returns:
        True if the polygon is self-intersecting, False otherwise
    """
    def lines_intersect(p1: Point, q1: Point, p2: Point, q2: Point) -> bool:
        """Check if line segments (p1,q1) and (p2,q2) intersect."""
        o1 = orientation(p1, q1, p2)
        o2 = orientation(p1, q1, q2)
        o3 = orientation(p2, q2, p1)
        o4 = orientation(p2, q2, q1)

        # General case
        if o1 != o2 and o3 != o4:
            return True

        # Special cases (collinear points)
        return False

    n = len(vertices)
    if n < 4:
        return False

    # Check all pairs of non-adjacent edges
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if lines_intersect(
                vertices[i],
                vertices[(i + 1) % n],
                vertices[j],
                vertices[(j + 1) % n]
            ):
                return True

    return False


def get_bounding_box(vertices: List[Point]) -> Tuple[Point, Point]:
    """
    Calculate the bounding box of a polygon.
    
    Args:
        vertices: List of vertices defining the polygon
        
    Returns:
        Tuple of (min_point, max_point) representing the bounding box
    """
    if not vertices:
        raise ValueError("Empty vertex list")
        
    min_x = min(v.x for v in vertices)
    min_y = min(v.y for v in vertices)
    max_x = max(v.x for v in vertices)
    max_y = max(v.y for v in vertices)
    
    return (Point(min_x, min_y), Point(max_x, max_y))


def calculate_area(vertices: List[Point]) -> float:
    """
    Calculate the area of a polygon using the shoelace formula.
    
    Args:
        vertices: List of vertices defining the polygon
        
    Returns:
        Area of the polygon
    """
    if len(vertices) < 3:
        return 0.0
        
    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        area += vertices[i].x * vertices[j].y
        area -= vertices[j].x * vertices[i].y
        
    return abs(area) / 2.0


def point_in_polygon(point: Point, vertices: List[Point]) -> bool:
    """
    Determine if a point lies inside a polygon using ray casting algorithm.
    
    Args:
        point: The point to test
        vertices: List of vertices defining the polygon
        
    Returns:
        True if the point is inside the polygon, False otherwise
    """
    if len(vertices) < 3:
        return False

    inside = False
    j = len(vertices) - 1
    
    for i in range(len(vertices)):
        if ((vertices[i].y > point.y) != (vertices[j].y > point.y) and
            point.x < (vertices[j].x - vertices[i].x) * 
            (point.y - vertices[i].y) / 
            (vertices[j].y - vertices[i].y) + vertices[i].x):
            inside = not inside
        j = i
        
    return inside


def validate_polygon(vertices: List[Point], min_vertices: int = 3, max_vertices: int = 8) -> Tuple[bool, str]:
    """
    Validate a polygon against multiple criteria.
    
    Args:
        vertices: List of vertices defining the polygon
        min_vertices: Minimum number of vertices required
        max_vertices: Maximum number of vertices allowed
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(vertices) < min_vertices:
        return False, f"At least {min_vertices} vertices required"
        
    if len(vertices) > max_vertices:
        return False, f"Maximum {max_vertices} vertices allowed"
        
    if is_self_intersecting(vertices):
        return False, "Polygon edges cannot intersect"
        
    if not is_convex_polygon(vertices):
        return False, "Polygon must be convex"
        
    return True, ""


class PolygonValidationState(Enum):
    """Enumeration of polygon validation states for visual feedback."""
    INVALID = auto()           # Basic polygon invalid (self-intersecting, etc.)
    PARTIAL_VALID = auto()     # Some sides parallel, but not all criteria met
    FULLY_VALID = auto()       # All criteria met (parallel sides + square corners)
    ODD_VERTICES = auto()      # Odd number of vertices (always solid lines)


def calculate_side_angle(p1: Point, p2: Point) -> float:
    """Calculate the angle of a line segment in radians.
    
    Args:
        p1: Start point of the line
        p2: End point of the line
        
    Returns:
        Angle in radians (-π to π)
    """
    return math.atan2(p2.y - p1.y, p2.x - p1.x)


def are_sides_parallel(side1_start: Point, side1_end: Point, 
                      side2_start: Point, side2_end: Point, 
                      tolerance_degrees: float = 2.0) -> bool:
    """Check if two line segments are parallel within tolerance.
    
    Args:
        side1_start, side1_end: Points defining first line segment
        side2_start, side2_end: Points defining second line segment
        tolerance_degrees: Tolerance in degrees for parallel check
        
    Returns:
        True if sides are parallel within tolerance
    """
    angle1 = calculate_side_angle(side1_start, side1_end)
    angle2 = calculate_side_angle(side2_start, side2_end)
    
    # Calculate angle difference
    angle_diff = abs(angle1 - angle2)
    
    # Normalize to 0-π range (parallel lines can differ by π radians)
    if angle_diff > math.pi:
        angle_diff = 2 * math.pi - angle_diff
    if angle_diff > math.pi / 2:
        angle_diff = math.pi - angle_diff
    
    tolerance_radians = math.radians(tolerance_degrees)
    return angle_diff < tolerance_radians


def calculate_corner_angle(prev_vertex: Point, vertex: Point, next_vertex: Point) -> float:
    """Calculate the interior angle at a vertex in degrees.
    
    Args:
        prev_vertex: Previous vertex in the polygon
        vertex: The vertex where we're measuring the angle
        next_vertex: Next vertex in the polygon
        
    Returns:
        Interior angle in degrees (0-180)
    """
    # Create vectors from vertex to adjacent points
    vec1_x = prev_vertex.x - vertex.x
    vec1_y = prev_vertex.y - vertex.y
    vec2_x = next_vertex.x - vertex.x
    vec2_y = next_vertex.y - vertex.y
    
    # Calculate dot product and magnitudes
    dot_product = vec1_x * vec2_x + vec1_y * vec2_y
    mag1 = math.sqrt(vec1_x * vec1_x + vec1_y * vec1_y)
    mag2 = math.sqrt(vec2_x * vec2_x + vec2_y * vec2_y)
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    # Calculate angle using dot product formula
    cos_angle = dot_product / (mag1 * mag2)
    
    # Clamp to valid range to avoid floating point errors
    cos_angle = max(-1.0, min(1.0, cos_angle))
    
    angle_radians = math.acos(cos_angle)
    return math.degrees(angle_radians)


def are_opposite_sides_parallel(vertices: List[Point], tolerance_degrees: float = 2.0) -> bool:
    """Check if opposite sides of a polygon are parallel.
    
    Args:
        vertices: List of polygon vertices
        tolerance_degrees: Tolerance in degrees for parallel check
        
    Returns:
        True if all opposite sides are parallel within tolerance
    """
    n = len(vertices)
    if n < 4 or n % 2 != 0:
        return False  # Only valid for even-sided polygons with 4+ vertices
    
    # Check each pair of opposite sides
    for i in range(n // 2):
        opposite_index = i + n // 2
        
        # Get current side
        side1_start = vertices[i]
        side1_end = vertices[(i + 1) % n]
        
        # Get opposite side
        side2_start = vertices[opposite_index]
        side2_end = vertices[(opposite_index + 1) % n]
        
        if not are_sides_parallel(side1_start, side1_end, side2_start, side2_end, tolerance_degrees):
            return False
    
    return True


def are_corners_square(vertices: List[Point], tolerance_degrees: float = 5.0) -> bool:
    """Check if all corners of a polygon are approximately 90 degrees.
    
    Args:
        vertices: List of polygon vertices
        tolerance_degrees: Tolerance in degrees for right angle check
        
    Returns:
        True if all corners are square within tolerance
    """
    n = len(vertices)
    if n < 3:
        return False
    
    for i in range(n):
        prev_vertex = vertices[(i - 1) % n]
        vertex = vertices[i]
        next_vertex = vertices[(i + 1) % n]
        
        angle = calculate_corner_angle(prev_vertex, vertex, next_vertex)
        
        # Check if angle is close to 90 degrees
        if abs(angle - 90.0) > tolerance_degrees:
            return False
    
    return True


def get_polygon_validation_state(vertices: List[Point], 
                                parallel_tolerance: float = 0.15,
                                angle_tolerance: float = 1.0) -> PolygonValidationState:
    """Get the validation state of a polygon for visual feedback.
    
    Args:
        vertices: List of polygon vertices
        parallel_tolerance: Tolerance in degrees for parallel side check
        angle_tolerance: Tolerance in degrees for right angle check
        
    Returns:
        PolygonValidationState indicating current validation level
    """
    n = len(vertices)
    
    # Odd number of vertices always use solid lines
    if n % 2 != 0:
        return PolygonValidationState.ODD_VERTICES
    
    # Check basic polygon validity first
    is_valid, _ = validate_polygon(vertices)
    if not is_valid:
        return PolygonValidationState.INVALID
    
    # For even-sided polygons, check geometric criteria
    if n >= 4:
        sides_parallel = are_opposite_sides_parallel(vertices, parallel_tolerance)
        corners_square = are_corners_square(vertices, angle_tolerance)
        
        if sides_parallel and corners_square:
            return PolygonValidationState.FULLY_VALID
        elif sides_parallel:
            return PolygonValidationState.PARTIAL_VALID
        else:
            return PolygonValidationState.INVALID
    
    return PolygonValidationState.INVALID

