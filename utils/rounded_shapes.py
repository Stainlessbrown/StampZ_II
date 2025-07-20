#!/usr/bin/env python3
"""
Rounded shape definitions for StampZ.
Provides Circle and Oval classes with mask generation capabilities.
"""

from dataclasses import dataclass
from typing import Tuple
from PIL import Image, ImageDraw
from .geometry import Point


@dataclass
class Circle:
    """Represents a circle with a center point and radius."""
    center: Point
    radius: float
    
    def generate_mask(self, image_size: Tuple[int, int]) -> Image.Image:
        """Generate a mask image for the circle.
        
        Args:
            image_size: Tuple of (width, height) for the mask image
            
        Returns:
            PIL Image with the circle mask (white on black)
        """
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        # Calculate bounding box for the circle
        x0 = self.center.x - self.radius
        y0 = self.center.y - self.radius
        x1 = self.center.x + self.radius
        y1 = self.center.y + self.radius
        
        draw.ellipse([x0, y0, x1, y1], fill=255)
        return mask


@dataclass
class Oval:
    """Represents an oval with a center point and width/height dimensions."""
    center: Point
    width: float
    height: float
    
    def generate_mask(self, image_size: Tuple[int, int]) -> Image.Image:
        """Generate a mask image for the oval.
        
        Args:
            image_size: Tuple of (width, height) for the mask image
            
        Returns:
            PIL Image with the oval mask (white on black)
        """
        mask = Image.new('L', image_size, 0)
        draw = ImageDraw.Draw(mask)
        
        # Calculate bounding box for the oval
        x0 = self.center.x - (self.width / 2)
        y0 = self.center.y - (self.height / 2)
        x1 = self.center.x + (self.width / 2)
        y1 = self.center.y + (self.height / 2)
        
        draw.ellipse([x0, y0, x1, y1], fill=255)
        return mask


