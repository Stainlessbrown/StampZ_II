"""
Image straightening utilities for the StampZ application.
Handles image rotation and skew correction for philatelic analysis.
"""

import math
import numpy as np
from PIL import Image, ImageDraw
from typing import Tuple, Optional, List
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ImageStraightener:
    """Handles image straightening and skew correction."""
    
    def __init__(self):
        """Initialize ImageStraightener."""
        pass
    
    @staticmethod
    def rotate_image(
        image: Image.Image, 
        angle_degrees: float, 
        background_color: str = 'white',
        expand: bool = True,
        auto_crop: bool = True
    ) -> Image.Image:
        """
        Rotate an image by the specified angle.
        
        Args:
            image: PIL Image to rotate
            angle_degrees: Rotation angle in degrees (positive = counterclockwise)
            background_color: Background color for areas outside original image
            expand: Whether to expand canvas to fit entire rotated image
            auto_crop: Whether to automatically crop away background padding
            
        Returns:
            Rotated PIL Image
        """
        try:
            # Convert angle to what PIL expects (negative for counterclockwise)
            pil_angle = -angle_degrees
            
            # Rotate the image
            rotated = image.rotate(
                pil_angle,
                expand=expand,
                fillcolor=background_color,
                resample=Image.Resampling.BICUBIC
            )
            
            # Auto-crop background padding if requested
            if auto_crop and expand:
                rotated = ImageStraightener._crop_background_padding(rotated, background_color)
            
            logger.debug(f"Rotated image by {angle_degrees} degrees")
            return rotated
            
        except Exception as e:
            logger.error(f"Error rotating image: {e}")
            return image
    
    @staticmethod
    def calculate_rotation_angle_from_points(
        point1: Tuple[float, float], 
        point2: Tuple[float, float]
    ) -> float:
        """
        Calculate the rotation angle needed to make a line horizontal.
        
        Args:
            point1: First point (x, y)
            point2: Second point (x, y)
            
        Returns:
            Angle in degrees needed to make the line horizontal
        """
        dx = point2[0] - point1[0]
        # Y coordinates are in screen coordinates (y=0 at top)
        dy = point2[1] - point1[1]  # Direct difference for screen coordinates
        
        if dx == 0:
            # Vertical line
            return -90.0 if dy > 0 else 90.0  # Flipped for Cartesian
        
        # Calculate angle from horizontal in Cartesian coordinates
        angle_radians = math.atan2(dy, dx)
        angle_degrees = math.degrees(angle_radians)
        
        # Return the angle needed to make line horizontal
        return angle_degrees
    
    
    @classmethod
    def straighten_image_by_points(
        cls,
        image: Image.Image,
        point1: Tuple[float, float],
        point2: Tuple[float, float],
        background_color: str = 'white'
    ) -> Tuple[Image.Image, float]:
        """
        Straighten an image using two reference points.
        
        Args:
            image: PIL Image to straighten
            point1: First reference point (x, y)
            point2: Second reference point (x, y)
            background_color: Background color for rotation
            
        Returns:
            Tuple of (straightened_image, rotation_angle_applied)
        """
        angle = cls.calculate_rotation_angle_from_points(point1, point2)
        straightened = cls.rotate_image(image, angle, background_color, expand=True, auto_crop=True)
        
        logger.info(f"Straightened image by {angle:.2f} degrees")
        return straightened, angle
    
    
    @staticmethod
    def get_image_center(image: Image.Image) -> Tuple[float, float]:
        """
        Get the center point of an image.
        
        Args:
            image: PIL Image
            
        Returns:
            Center point as (x, y) tuple
        """
        return (image.width / 2.0, image.height / 2.0)
    
    @staticmethod
    def validate_rotation_angle(angle: float, max_angle: float = 45.0) -> bool:
        """
        Validate that a rotation angle is reasonable.
        
        Args:
            angle: Rotation angle in degrees
            max_angle: Maximum allowed angle
            
        Returns:
            True if angle is within reasonable bounds
        """
        return abs(angle) <= max_angle
    
    @staticmethod
    def _crop_background_padding(image: Image.Image, background_color: str = 'white') -> Image.Image:
        """
        Automatically crop background padding from a rotated image.
        Uses multiple detection methods for better padding removal.
        
        Args:
            image: PIL Image with background padding
            background_color: Background color to detect and crop
            
        Returns:
            Cropped PIL Image with padding removed
        """
        try:
            # Convert image to numpy array for analysis
            img_array = np.array(image)
            
            # Handle different image modes
            if image.mode == 'RGBA':
                # For RGBA, check alpha channel first, then color
                alpha_channel = img_array[:, :, 3]
                mask = alpha_channel > 0  # Non-transparent pixels
                
                # Also check color if alpha is opaque
                if background_color.lower() == 'white':
                    bg_color = np.array([255, 255, 255])
                elif background_color.lower() == 'black':
                    bg_color = np.array([0, 0, 0])
                else:
                    bg_color = np.array([255, 255, 255])
                
                # Check RGB channels for background color (with more aggressive tolerance)
                rgb_diff = np.abs(img_array[:, :, :3].astype(int) - bg_color)
                color_mask = np.any(rgb_diff > 10, axis=2)  # More aggressive: 10 instead of 3
                
                # Combine alpha and color masks
                mask = mask & color_mask
                
            elif image.mode == 'RGB':
                # For RGB, use multiple detection strategies
                if background_color.lower() == 'white':
                    bg_color = np.array([255, 255, 255])
                elif background_color.lower() == 'black':
                    bg_color = np.array([0, 0, 0])
                else:
                    bg_color = np.array([255, 255, 255])
                
                # Method 1: Direct color comparison with aggressive tolerance
                diff = np.abs(img_array.astype(int) - bg_color)
                mask1 = np.any(diff > 15, axis=2)  # Very aggressive: 15 pixel tolerance
                
                # Method 2: Statistical approach - detect outliers
                # Calculate mean and std for each channel
                mean_vals = np.mean(img_array, axis=(0, 1))
                std_vals = np.std(img_array, axis=(0, 1))
                
                # Pixels that deviate significantly from background
                bg_threshold = 2.0  # 2 standard deviations
                mask2 = np.any(np.abs(img_array - mean_vals) > bg_threshold * std_vals, axis=2)
                
                # Method 3: Edge detection approach
                # Look for significant brightness changes
                gray = np.mean(img_array, axis=2)
                
                # Detect edges using gradient
                from scipy import ndimage
                gradient_x = ndimage.sobel(gray, axis=1)
                gradient_y = ndimage.sobel(gray, axis=0)
                gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
                
                # Areas with significant edges are likely content
                edge_threshold = np.std(gradient_magnitude) * 0.5
                mask3 = gradient_magnitude > edge_threshold
                
                # Combine all methods (union of detections)
                mask = mask1 | mask2 | mask3
                
            else:
                # For other modes, convert to RGB first
                rgb_image = image.convert('RGB')
                return ImageStraightener._crop_background_padding(rgb_image, background_color)
            
            # Apply morphological operations to clean up the mask
            from scipy import ndimage
            
            # Fill small holes
            mask = ndimage.binary_fill_holes(mask)
            
            # Remove small noise with opening operation
            struct_elem = np.ones((3, 3))
            mask = ndimage.binary_opening(mask, structure=struct_elem)
            
            # Dilate slightly to ensure we don't cut into content
            mask = ndimage.binary_dilation(mask, structure=struct_elem, iterations=2)
            
            # Find bounding box of content
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            
            if not np.any(rows) or not np.any(cols):
                # No content found, return original image
                logger.warning("No content found during auto-crop, returning original")
                return image
            
            # Get the bounding box coordinates
            top, bottom = np.where(rows)[0][[0, -1]]
            left, right = np.where(cols)[0][[0, -1]]
            
            # Add small margin to avoid cutting content (but keep aggressive)
            margin = 2
            top = max(0, top - margin)
            left = max(0, left - margin)
            bottom = min(image.height - 1, bottom + margin)
            right = min(image.width - 1, right + margin)
            
            # Crop the image
            cropped = image.crop((left, top, right + 1, bottom + 1))
            
            logger.debug(f"Auto-cropped image from {image.size} to {cropped.size}")
            logger.debug(f"Removed padding: left={left}, top={top}, right={image.width-right-1}, bottom={image.height-bottom-1}")
            
            return cropped
            
        except Exception as e:
            logger.error(f"Error during auto-crop: {e}")
            # Fallback: try simpler approach
            return ImageStraightener._simple_crop_fallback(image, background_color)
    
    @staticmethod
    def _simple_crop_fallback(image: Image.Image, background_color: str = 'white') -> Image.Image:
        """
        Simple fallback crop method when advanced detection fails.
        
        Args:
            image: PIL Image with background padding
            background_color: Background color to detect and crop
            
        Returns:
            Cropped PIL Image with padding removed
        """
        try:
            # Convert to numpy for simple analysis
            img_array = np.array(image.convert('RGB'))
            
            # Define background color
            if background_color.lower() == 'white':
                bg_color = np.array([255, 255, 255])
            elif background_color.lower() == 'black':
                bg_color = np.array([0, 0, 0])
            else:
                bg_color = np.array([255, 255, 255])
            
            # Simple threshold-based detection
            diff = np.abs(img_array.astype(int) - bg_color)
            mask = np.any(diff > 20, axis=2)  # Simple 20-pixel threshold
            
            # Find bounding box
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            
            if not np.any(rows) or not np.any(cols):
                return image
            
            top, bottom = np.where(rows)[0][[0, -1]]
            left, right = np.where(cols)[0][[0, -1]]
            
            # Small margin
            margin = 5
            top = max(0, top - margin)
            left = max(0, left - margin)
            bottom = min(image.height - 1, bottom + margin)
            right = min(image.width - 1, right + margin)
            
            return image.crop((left, top, right + 1, bottom + 1))
            
        except Exception:
            # Ultimate fallback - return original
            return image


class StraighteningTool:
    """Interactive tool for image straightening."""
    
    def __init__(self):
        """Initialize StraighteningTool."""
        self.reference_points: List[Tuple[float, float]] = []
        self.max_points = 2  # Only allow 2 reference points for two-point leveling
        self.straightener = ImageStraightener()
    
    def add_reference_point(self, x: float, y: float) -> bool:
        """
        Add a reference point for leveling.
        
        Args:
            x: X coordinate
            y: Y coordinate (in screen coordinates, y=0 at top)
            
        Returns:
            True if point was added successfully
        """
        if len(self.reference_points) < self.max_points:
            # Store points in screen coordinates
            self.reference_points.append((x, y))
            logger.debug(f"Added reference point: ({x}, {y})")
            print(f"DEBUG: Added reference point: ({x}, {y}) in screen coordinates")
            return True
        return False
    
    def remove_last_point(self) -> bool:
        """
        Remove the last added reference point.
        
        Returns:
            True if a point was removed
        """
        if self.reference_points:
            removed = self.reference_points.pop()
            logger.debug(f"Removed reference point: {removed}")
            return True
        return False
    
    def clear_points(self) -> None:
        """
        Clear all reference points.
        """
        self.reference_points.clear()
        logger.debug("Cleared all reference points")
    
    def get_point_count(self) -> int:
        """
        Get the number of reference points.
        
        Returns:
            Number of reference points
        """
        return len(self.reference_points)
    
    def can_straighten(self) -> bool:
        """
        Check if we have enough points to perform straightening.
        
        Returns:
            True if straightening is possible
        """
        return len(self.reference_points) >= 2
    
    def calculate_angle(self) -> Optional[float]:
        """
        Calculate the straightening angle from current reference points.
        
        Returns:
            Rotation angle in degrees, or None if not enough points
        """
        if not self.can_straighten():
            return None
        
        # Points are already in mathematical/Cartesian coordinates
        return self.straightener.calculate_rotation_angle_from_points(
            self.reference_points[0], 
            self.reference_points[1]
        )
    
    def straighten_image(self, image: Image.Image, background_color: str = 'white') -> Tuple[Image.Image, float]:
        """
        Straighten an image using the current reference points.
        
        Args:
            image: PIL Image to straighten
            background_color: Background color for rotation
            
        Returns:
            Tuple of (straightened_image, rotation_angle_applied)
        """
        if not self.can_straighten():
            return image, 0.0
        
        # Only two-point straightening is supported
        return self.straightener.straighten_image_by_points(
            image, 
            self.reference_points[0], 
            self.reference_points[1],
            background_color
        )


# Convenience functions
def straighten_by_two_points(
    image: Image.Image,
    point1: Tuple[float, float],
    point2: Tuple[float, float],
    background_color: str = 'white'
) -> Tuple[Image.Image, float]:
    """
    Convenience function to straighten an image using two points.
    
    Args:
        image: PIL Image to straighten
        point1: First reference point
        point2: Second reference point
        background_color: Background color for rotation
        
    Returns:
        Tuple of (straightened_image, rotation_angle_applied)
    """
    return ImageStraightener.straighten_image_by_points(
        image, point1, point2, background_color
    )


def rotate_image_by_angle(
    image: Image.Image,
    angle: float,
    background_color: str = 'white'
) -> Image.Image:
    """
    Convenience function to rotate an image by a specific angle.
    
    Args:
        image: PIL Image to rotate
        angle: Rotation angle in degrees
        background_color: Background color for rotation
        
    Returns:
        Rotated PIL Image
    """
    return ImageStraightener.rotate_image(image, angle, background_color)

