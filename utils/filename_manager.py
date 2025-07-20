"""
Filename management utilities for the StampZ application.
Handles dynamic filename generation with image dimensions.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import logging

# Configure logging
logger = logging.getLogger(__name__)

class FilenameManager:
    """Manages dynamic filename generation with image dimensions."""
    
    def __init__(self):
        """Initialize FilenameManager."""
        pass
    
    @staticmethod
    def get_image_dimensions(image: Image.Image) -> Tuple[int, int]:
        """
        Get the dimensions of an image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (width, height)
        """
        return image.size
    
    @staticmethod
    def format_dimensions(width: int, height: int, remove_spaces: bool = True) -> str:
        """
        Format dimensions as a string for filename inclusion.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
            remove_spaces: Whether to remove spaces (default True)
            
        Returns:
            Formatted dimension string (e.g., "458x550")
        """
        if remove_spaces:
            return f"{width}x{height}"
        else:
            return f"{width} x {height}"
    
    @classmethod
    def generate_cropped_filename(
        cls,
        original_file: Optional[str],
        cropped_image: Image.Image,
        extension: str = None,
        use_dimensions: bool = True,
        fallback_name: str = "cropped"
    ) -> str:
        """
        Generate a filename for a cropped image with dimensions.
        
        Args:
            original_file: Path to the original file (can be None)
            cropped_image: The cropped PIL Image object
            extension: File extension to use (e.g., '.jpg'). If None, detected from original
            use_dimensions: Whether to include dimensions in filename
            fallback_name: Name to use if no original file provided
            
        Returns:
            Generated filename with dimensions
            
        Examples:
            "stamp_458x550.jpg" (from "stamp.jpg" with 458x550 cropped image)
            "document_1200x800.tif" (from "document.tif" with 1200x800 cropped image)
            "cropped_640x480.png" (no original file, 640x480 cropped image)
        """
        # Get base name
        if original_file:
            base = os.path.splitext(os.path.basename(original_file))[0]
            # Get original extension if none provided
            if extension is None:
                extension = os.path.splitext(original_file)[1]
        else:
            base = fallback_name
            # Default extension if none provided
            if extension is None:
                extension = '.jpg'
        
        # Ensure extension starts with a dot
        if extension and not extension.startswith('.'):
            extension = f'.{extension}'
        
        if use_dimensions:
            # Use simplified "-crp" suffix instead of dimensions
            filename = f"{base}-crp{extension}"
        else:
            # Fallback to old behavior
            filename = f"{base}_cropped{extension}"
        
        logger.debug(f"Generated filename: {filename} (dimensions: {use_dimensions})")
        return filename
    
    @classmethod
    def update_filename_with_dimensions(
        cls,
        current_filename: str,
        cropped_image: Image.Image
    ) -> str:
        """
        Update an existing filename to include dimensions.
        
        Args:
            current_filename: Current filename
            cropped_image: The cropped PIL Image object
            
        Returns:
            Updated filename with dimensions
            
        Examples:
            "stamp_cropped.jpg" -> "stamp_458x550.jpg"
            "document_cropped.tif" -> "document_1200x800.tif"
        """
        # Split filename and extension
        base_name, extension = os.path.splitext(current_filename)
        
        # Remove "_cropped" suffix if present
        if base_name.endswith('_cropped'):
            base_name = base_name[:-8]  # Remove "_cropped"
        
        # Get dimensions and create new filename
        width, height = cls.get_image_dimensions(cropped_image)
        dimensions_str = cls.format_dimensions(width, height)
        
        new_filename = f"{base_name}_{dimensions_str}{extension}"
        logger.debug(f"Updated filename: {current_filename} -> {new_filename}")
        return new_filename
    
    @staticmethod
    def sanitize_filename(filename: str, replacement_char: str = '_') -> str:
        """
        Sanitize a filename by removing or replacing invalid characters.
        
        Args:
            filename: Original filename
            replacement_char: Character to use for replacements
            
        Returns:
            Sanitized filename
        """
        # Characters that are invalid in filenames on most systems
        invalid_chars = '<>:"/\\|?*'
        
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, replacement_char)
        
        # Remove any duplicate replacement characters
        while f'{replacement_char}{replacement_char}' in sanitized:
            sanitized = sanitized.replace(f'{replacement_char}{replacement_char}', replacement_char)
        
        return sanitized
    
    @classmethod
    def validate_filename_length(cls, filename: str, max_length: int = 255) -> str:
        """
        Ensure filename doesn't exceed maximum length.
        
        Args:
            filename: Filename to validate
            max_length: Maximum allowed length
            
        Returns:
            Truncated filename if necessary
        """
        if len(filename) <= max_length:
            return filename
        
        # Split name and extension
        base_name, extension = os.path.splitext(filename)
        
        # Calculate how much we need to truncate
        max_base_length = max_length - len(extension)
        
        if max_base_length > 0:
            truncated_base = base_name[:max_base_length]
            result = f"{truncated_base}{extension}"
            logger.warning(f"Filename truncated: {filename} -> {result}")
            return result
        else:
            # If even the extension is too long, just return the extension
            logger.warning(f"Filename too long, using extension only: {extension}")
            return extension[:max_length]


# Convenience functions for easy integration
def get_cropped_filename(
    original_file: Optional[str],
    cropped_image: Image.Image,
    extension: str = None
) -> str:
    """
    Convenience function to generate a cropped filename with dimensions.
    
    Args:
        original_file: Path to the original file
        cropped_image: The cropped PIL Image object
        extension: File extension (optional)
        
    Returns:
        Generated filename with dimensions
    """
    return FilenameManager.generate_cropped_filename(
        original_file=original_file,
        cropped_image=cropped_image,
        extension=extension,
        use_dimensions=True
    )


def update_filename_with_dimensions(filename: str, cropped_image: Image.Image) -> str:
    """
    Convenience function to update a filename with dimensions.
    
    Args:
        filename: Current filename
        cropped_image: The cropped PIL Image object
        
    Returns:
        Updated filename with dimensions
    """
    return FilenameManager.update_filename_with_dimensions(filename, cropped_image)

