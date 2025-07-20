#!/usr/bin/env python3
"""
Mask generator utilities for StampZ.
Handles creation of selection masks for various shapes.
"""

from enum import Enum
from PIL import Image, ImageDraw
from typing import List, Union, Tuple
from .geometry import Point
from .rounded_shapes import Circle, Oval


class MaskColor(Enum):
    """Enumeration of available mask colors."""
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    GRAY = (128, 128, 128)


def create_shape_mask(
    image: Image.Image,
    shape: Union[List[Point], Circle, Oval],
    alpha: int = 128,
    highlight_vertices: bool = True,
    highlight_color: MaskColor = MaskColor.GRAY
) -> Image.Image:
    """Create a mask for the specified shape.
    
    Args:
        image: Base image to create mask for
        shape: Shape definition (polygon vertices, Circle, or Oval)
        alpha: Mask transparency (0-255)
        highlight_vertices: Whether to highlight control points
        highlight_color: Color to use for highlights
        
    Returns:
        PIL Image with the shape mask
    """
    # Create base mask
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    
    if isinstance(shape, (Circle, Oval)):
        # Use shape's own mask generation
        mask = shape.generate_mask(image.size)
    else:
        # Handle polygon
        vertices = shape
        if len(vertices) >= 3:
            # Draw polygon
            vertex_coords = [(v.x, v.y) for v in vertices]
            draw.polygon(vertex_coords, fill=255)
            
            # Highlight vertices if requested
            if highlight_vertices:
                radius = 5
                for vertex in vertices:
                    x, y = vertex.x, vertex.y
                    draw.ellipse(
                        [x - radius, y - radius, x + radius, y + radius],
                        fill=255
                    )
    
    # Create result image
    result = Image.new('RGBA', image.size, (0, 0, 0, 0))
    
    # Apply highlight color with alpha
    color = highlight_color.value + (alpha,)
    color_layer = Image.new('RGBA', image.size, color)
    
    # Compose final image using the mask
    result.paste(color_layer, mask=mask)
    
    return result


def get_shape_bbox(shape: Union[List[Point], Circle, Oval]) -> Tuple[int, int, int, int]:
    """Get the bounding box for a shape.
    
    Args:
        shape: Shape to get bounding box for
        
    Returns:
        Tuple of (left, top, right, bottom) coordinates
    """
    if isinstance(shape, Circle):
        return (
            int(shape.center.x - shape.radius),
            int(shape.center.y - shape.radius),
            int(shape.center.x + shape.radius),
            int(shape.center.y + shape.radius)
        )
    elif isinstance(shape, Oval):
        return (
            int(shape.center.x - shape.width / 2),
            int(shape.center.y - shape.height / 2),
            int(shape.center.x + shape.width / 2),
            int(shape.center.y + shape.height / 2)
        )
    else:
        # Handle polygon
        vertices = shape
        min_x = min(v.x for v in vertices)
        min_y = min(v.y for v in vertices)
        max_x = max(v.x for v in vertices)
        max_y = max(v.y for v in vertices)
        return (int(min_x), int(min_y), int(max_x), int(max_y))



def create_polygon_mask(
    image_size: Tuple[int, int],
    vertices: List[Point],
    mask_color: Tuple[int, int, int] = (128, 128, 128),  # Default gray color
    alpha: int = 128,
    invert: bool = False
) -> Image.Image:
    """
    Create a semi-transparent polygon mask.
    
    Args:
        image_size: (width, height) of the target image
        vertices: List of vertices defining the polygon
        mask_color: RGB color tuple for the mask
        alpha: Transparency level (0-255)
        invert: If True, mask outside the polygon instead of inside
        
    Returns:
        PIL Image with the mask
    """
    # Create a new RGBA image for the mask
    mask = Image.new('RGBA', image_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    
    # Convert vertices to coordinate pairs
    polygon_coords = [(v.x, v.y) for v in vertices]
    
    if invert:
        # Draw the exterior mask (everything outside the polygon)
        # First create a full image mask
        draw.rectangle([(0, 0), image_size], fill=(*mask_color, alpha))
        # Then clear the polygon area
        draw.polygon(polygon_coords, fill=(0, 0, 0, 0))
    else:
        # Draw the interior mask (the polygon itself)
        draw.polygon(polygon_coords, fill=(*mask_color, alpha))
    
    return mask


def apply_mask_to_image(
    image: Image.Image,
    mask: Image.Image,
    blend_mode: str = 'alpha_composite'
) -> Image.Image:
    """
    Apply a mask to an image.
    
    Args:
        image: Source image
        mask: Mask to apply
        blend_mode: Blending mode ('alpha_composite' or 'blend')
        
    Returns:
        New image with mask applied
    """
    # Ensure the image has an alpha channel
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create a new image for the result
    result = Image.new('RGBA', image.size, (0, 0, 0, 0))
    
    # Composite the original image and mask
    if blend_mode == 'alpha_composite':
        result = Image.alpha_composite(result, image)
        result = Image.alpha_composite(result, mask)
    else:  # blend mode
        result = Image.blend(image, mask, 0.5)
    
    return result


def create_selection_preview(
    image: Image.Image,
    vertices: List[Point],
    mask_color: Tuple[int, int, int] = (128, 128, 128),  # Default gray color
    alpha: int = 128,
    highlight_vertices: bool = True,
    vertex_color: Tuple[int, int, int] = (0, 0, 255),  # Default blue color
    vertex_size: int = 5
) -> Image.Image:
    """
    Create a preview image with mask and optional vertex highlights.
    
    Args:
        image: Source image
        vertices: List of polygon vertices
        mask_color: Color for the mask
        alpha: Mask transparency (0-255)
        highlight_vertices: Whether to draw vertex markers
        vertex_color: Color for vertex markers
        vertex_size: Size of vertex markers in pixels
        
    Returns:
        New image with mask and optional vertex markers
    """
    # Create the base mask
    mask = create_polygon_mask(image.size, vertices, mask_color, alpha)
    
    if highlight_vertices:
        # Draw vertex markers on the mask
        draw = ImageDraw.Draw(mask)
        for vertex in vertices:
            x, y = vertex.x, vertex.y
            rect = [
                (x - vertex_size, y - vertex_size),
                (x + vertex_size, y + vertex_size)
            ]
            draw.ellipse(rect, fill=(*vertex_color, 255))
    
    # Apply the mask to the image
    return apply_mask_to_image(image, mask)


def create_highlight_mask(
    image_size: Tuple[int, int],
    region: Tuple[float, float, float, float],  # x1, y1, x2, y2
    color: Tuple[int, int, int] = (0, 0, 255),  # Default blue color
    alpha: int = 64
) -> Image.Image:
    """
    Create a highlight mask for vertex or region selection.
    
    Args:
        image_size: Size of the target image
        region: Rectangle coordinates to highlight
        color: Highlight color
        alpha: Transparency level
        
    Returns:
        Highlight mask image
    """
    mask = Image.new('RGBA', image_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    
    draw.rectangle(region, fill=(*color, alpha))
    
    return mask


def update_mask_alpha(mask: Image.Image, new_alpha: int) -> Image.Image:
    """
    Update the transparency of an existing mask.
    
    Args:
        mask: Existing mask image
        new_alpha: New alpha value (0-255)
        
    Returns:
        Updated mask with new transparency
    """
    # Get the RGBA data
    r, g, b, a = mask.split()
    
    # Create a new alpha channel with the desired transparency
    new_alpha_channel = Image.new('L', mask.size, new_alpha)
    
    # Combine the original RGB with the new alpha
    return Image.merge('RGBA', (r, g, b, new_alpha_channel))

