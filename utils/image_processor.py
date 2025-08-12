"""
Image processing utilities for the StampZ application.
Handles loading, saving, and manipulating images using Pillow (PIL).
"""

from pathlib import Path
from typing import Tuple, Optional, Union
from PIL import Image, ImageTk
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ImageLoadError(Exception):
    """Exception raised when image loading fails."""
    pass

class ImageSaveError(Exception):
    """Exception raised when image saving fails."""
    pass

def load_image(file_path: Union[str, Path]) -> Image.Image:
    """
    Load an image file (JPG or PNG) and return a PIL Image object with proper color profile handling.
    
    Args:
        file_path: Path to the image file to load
        
    Returns:
        PIL Image object converted to sRGB color space
        
    Raises:
        ImageLoadError: If the file cannot be loaded or is not a valid image
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise ImageLoadError(f"File not found: {file_path}")
            
        if file_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
            raise ImageLoadError(f"Unsupported file format: {file_path.suffix}")
            
        image = Image.open(file_path)
        image.load()  # Load image data immediately
        
        # Handle color profile conversion to ensure consistent sRGB color space
        if hasattr(image, 'info') and 'icc_profile' in image.info:
            logger.info(f"Converting image with embedded color profile to sRGB: {file_path}")
            try:
                # Convert to sRGB using the embedded ICC profile
                from PIL import ImageCms
                
                # Create sRGB profile
                srgb_profile = ImageCms.createProfile('sRGB')
                
                # Get embedded profile
                input_profile = ImageCms.ImageCmsProfile(image.info['icc_profile'])
                
                # Create transformation
                transform = ImageCms.buildTransform(input_profile, srgb_profile, 'RGB', 'RGB')
                
                # Apply transformation
                image = ImageCms.applyTransform(image, transform)
                
                logger.info(f"Successfully converted to sRGB color space")
                
            except Exception as e:
                logger.warning(f"Failed to convert color profile, using image as-is: {e}")
                # Fall back to converting to RGB without profile transformation
                if image.mode != 'RGB':
                    image = image.convert('RGB')
        else:
            # No embedded profile, ensure RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
        return image
        
    except (OSError, IOError) as e:
        raise ImageLoadError(f"Failed to load image {file_path}: {str(e)}")

# Save functionality moved to save_as.py

def scale_image(
    image: Image.Image,
    max_size: Tuple[int, int],
    preserve_aspect: bool = True
) -> Image.Image:
    """
    Scale an image to fit within the specified dimensions while optionally preserving aspect ratio.
    
    Args:
        image: PIL Image object to scale
        max_size: (width, height) tuple specifying maximum dimensions
        preserve_aspect: If True, maintain aspect ratio while scaling
        
    Returns:
        Scaled PIL Image object
    """
    if not isinstance(max_size, tuple) or len(max_size) != 2:
        raise ValueError("max_size must be a (width, height) tuple")
        
    if preserve_aspect:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    else:
        return image.resize(max_size, Image.Resampling.LANCZOS)

def create_tk_image(image: Image.Image) -> ImageTk.PhotoImage:
    """
    Convert a PIL Image to a Tkinter-compatible PhotoImage.
    
    Args:
        image: PIL Image object to convert
        
    Returns:
        Tkinter-compatible PhotoImage object
    """
    return ImageTk.PhotoImage(image)

def get_image_dimensions(image: Image.Image) -> Tuple[int, int]:
    """
    Get the dimensions of an image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Tuple of (width, height)
    """
    return image.size

def crop_image(
    image: Image.Image,
    vertices: list[Tuple[int, int]]
) -> Optional[Image.Image]:
    """
    Crop an image using a polygon defined by vertices.
    
    Args:
        image: PIL Image object to crop
        vertices: List of (x, y) tuples defining the crop polygon
        
    Returns:
        Cropped PIL Image object, or None if cropping fails
        
    Note:
        This is a placeholder for the actual implementation that will be
        developed as part of the polygon cropping functionality.
    """
    # TODO: Implement polygon cropping
    # This will be implemented when we develop the geometry utilities
    pass

