"""
Vertex management for the StampZ application.
Handles vertex operations, validation, and polygon management.
"""

from typing import List, Optional, Tuple, Callable
from .geometry import Point, validate_polygon


class VerticesManager:
    """Manages vertex operations and polygon validation."""

    def __init__(
        self,
        min_vertices: int = 3,
        max_vertices: int = 8,
        status_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the vertices manager.
        
        Args:
            min_vertices: Minimum number of vertices allowed
            max_vertices: Maximum number of vertices allowed
            status_callback: Optional callback for status messages
        """
        self.min_vertices = min_vertices
        self.max_vertices = max_vertices
        self.vertices: List[Point] = []
        self.active_vertex: Optional[int] = None
        self.status_callback = status_callback or (lambda _: None)

    def add_vertex(self, x: float, y: float) -> bool:
        """
        Add a new vertex at the specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if vertex was added successfully, False otherwise
        """
        if len(self.vertices) >= self.max_vertices:
            self.status_callback(f"Maximum {self.max_vertices} vertices allowed")
            return False

        new_vertex = Point(x, y)
        self.vertices.append(new_vertex)

        if len(self.vertices) < self.min_vertices:
            remaining = self.min_vertices - len(self.vertices)
            self.status_callback(f"Place {remaining} more vertices to complete the polygon")
            return True

        # Validate polygon if we have enough vertices
        valid, message = validate_polygon(self.vertices)
        if not valid:
            self.vertices.pop()
            self.status_callback(message)
            return False

        return True

    def move_vertex(self, index: int, x: float, y: float) -> bool:
        """
        Move an existing vertex to new coordinates.
        
        Args:
            index: Index of the vertex to move
            x: New X coordinate
            y: New Y coordinate
            
        Returns:
            True if move was valid, False otherwise
        """
        if not 0 <= index < len(self.vertices):
            return False

        # Store original position in case we need to revert
        original_pos = self.vertices[index]
        self.vertices[index] = Point(x, y)

        # Validate the polygon if we have enough vertices
        if len(self.vertices) >= self.min_vertices:
            valid, message = validate_polygon(self.vertices)
            if not valid:
                # Revert the move if it creates an invalid polygon
                self.vertices[index] = original_pos
                self.status_callback(message)
                return False

        return True

    def remove_vertex(self, index: int) -> bool:
        """
        Remove a vertex at the specified index.
        
        Args:
            index: Index of the vertex to remove
            
        Returns:
            True if vertex was removed, False if removal would create invalid polygon
        """
        if not 0 <= index < len(self.vertices):
            return False

        # Don't allow removal if it would leave us with too few vertices
        if len(self.vertices) <= self.min_vertices:
            self.status_callback(f"Minimum {self.min_vertices} vertices required")
            return False

        self.vertices.pop(index)
        return True

    def clear_vertices(self) -> None:
        """Remove all vertices."""
        self.vertices.clear()
        self.active_vertex = None

    def get_vertices(self) -> List[Point]:
        """Get a copy of the current vertices list."""
        return self.vertices.copy()

    def set_vertices(self, vertices: List[Point]) -> bool:
        """
        Set the vertices list.
        
        Args:
            vertices: New list of vertices
            
        Returns:
            True if vertices were valid and set, False otherwise
        """
        if not self.min_vertices <= len(vertices) <= self.max_vertices:
            self.status_callback(
                f"Number of vertices must be between {self.min_vertices} and {self.max_vertices}"
            )
            return False

        valid, message = validate_polygon(vertices)
        if not valid:
            self.status_callback(message)
            return False

        self.vertices = vertices.copy()
        return True

    def get_bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Calculate the bounding box of the current polygon.
        
        Returns:
            Tuple of (min_x, min_y, max_x, max_y) or None if no vertices
        """
        if not self.vertices:
            return None

        min_x = min(v.x for v in self.vertices)
        min_y = min(v.y for v in self.vertices)
        max_x = max(v.x for v in self.vertices)
        max_y = max(v.y for v in self.vertices)

        return (min_x, min_y, max_x, max_y)

    def is_complete(self) -> bool:
        """Check if the polygon has enough vertices and is valid."""
        if len(self.vertices) < self.min_vertices:
            return False
        valid, _ = validate_polygon(self.vertices)
        return valid

    def get_vertex_at_position(
        self, x: float, y: float, max_distance: float
    ) -> Optional[int]:
        """
        Find vertex near the given coordinates within max_distance.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            max_distance: Maximum distance to consider a match
            
        Returns:
            Index of the closest vertex within range, or None if none found
        """
        for i, vertex in enumerate(self.vertices):
            dx = vertex.x - x
            dy = vertex.y - y
            if (dx * dx + dy * dy) <= max_distance * max_distance:
                return i
        return None

    @property
    def vertex_count(self) -> int:
        """Get the current number of vertices."""
        return len(self.vertices)

    @property
    def is_active(self) -> bool:
        """Check if any vertex is currently active/selected."""
        return self.active_vertex is not None

