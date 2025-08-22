"""
Image processing utilities for the StampZ application.
Handles loading, saving, and manipulating images using Pillow (PIL).
"""

from pathlib import Path
from typing import Tuple, Optional, Union
from PIL import Image, ImageTk
import logging
import numpy as np

# Import 16-bit TIFF loader
try:
    from .true_16bit_loader import load_16bit_tiff
    HAS_16BIT_LOADER = True
except ImportError:
    HAS_16BIT_LOADER = False

# Configure logging
logger = logging.getLogger(__name__)

class ImageLoadError(Exception):
    """Exception raised when image loading fails."""
    pass

class ImageSaveError(Exception):
    """Exception raised when image saving fails."""
    pass

def load_image(file_path: Union[str, Path]) -> Tuple[Image.Image, dict]:
    """
    Load an image file and return a PIL Image object with proper color profile handling.
    For TIFF files, attempts to preserve 16-bit precision when possible.
    
    Args:
        file_path: Path to the image file to load
        
    Returns:
        Tuple of (PIL Image object converted to sRGB color space, metadata dict)
        
    Raises:
        ImageLoadError: If the file cannot be loaded or is not a valid image
    """
    metadata = {'format_info': '', 'precision_preserved': False, 'original_bit_depth': None}
    
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise ImageLoadError(f"File not found: {file_path}")
            
        if file_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
            raise ImageLoadError(f"Unsupported file format: {file_path.suffix}")
        
        # Handle TIFF files with 16-bit loader if available
        if file_path.suffix.lower() in ['.tif', '.tiff'] and HAS_16BIT_LOADER:
            try:
                img_array, tiff_metadata = load_16bit_tiff(str(file_path), preserve_16bit=True)
                
                # Update our metadata
                metadata.update({
                    'format_info': f"TIFF loaded with {'16-bit' if tiff_metadata.get('true_16bit') else '8-bit'} precision",
                    'precision_preserved': tiff_metadata.get('true_16bit', False),
                    'original_bit_depth': tiff_metadata.get('bits_per_sample'),
                    'data_type': tiff_metadata.get('data_type'),
                    'value_range': tiff_metadata.get('value_range')
                })
                
                # Convert numpy array to PIL Image
                if tiff_metadata.get('true_16bit', False):
                    # For 16-bit data, we need to scale down to 8-bit for display
                    # but preserve the original precision info
                    img_array_8bit = (img_array / 65535.0 * 255.0).astype(np.uint8)
                    image = Image.fromarray(img_array_8bit)
                    logger.info(f"Loaded 16-bit TIFF with full precision: {file_path}")
                else:
                    image = Image.fromarray(img_array)
                    logger.info(f"Loaded TIFF as 8-bit: {file_path}")
                    
            except Exception as e:
                logger.warning(f"16-bit TIFF loading failed, falling back to PIL: {e}")
                metadata['format_info'] = "TIFF loaded with PIL (may be downsampled)"
                image = Image.open(file_path)
                image.load()
        else:
            # Use PIL for non-TIFF files or when 16-bit loader not available
            image = Image.open(file_path)
            image.load()  # Load image data immediately
            
            # Set format info for non-TIFF files
            if file_path.suffix.lower() == '.png':
                metadata['format_info'] = "PNG loaded (lossless, good for color analysis)"
            elif file_path.suffix.lower() in ['.jpg', '.jpeg']:
                metadata['format_info'] = "JPEG loaded (compressed, not ideal for precise color analysis)"
            elif file_path.suffix.lower() in ['.tif', '.tiff']:
                metadata['format_info'] = "TIFF loaded with PIL (install 'tifffile' for 16-bit support)"
        
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
                metadata['color_profile'] = "Converted from embedded profile to sRGB"
                
            except Exception as e:
                logger.warning(f"Failed to convert color profile, using image as-is: {e}")
                # Fall back to converting to RGB without profile transformation
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                metadata['color_profile'] = "Profile conversion failed, using as RGB"
        else:
            # No embedded profile, ensure RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            metadata['color_profile'] = "No embedded profile, converted to RGB"
                
        return image, metadata
        
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

