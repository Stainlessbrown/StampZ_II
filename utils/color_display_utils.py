#!/usr/bin/env python3
"""
Color display utility functions for StampZ
Handles conditional display of RGB and L*a*b* values based on user preferences.
"""

from typing import Tuple, Optional


def get_conditional_color_info(
    rgb: Tuple[float, float, float], 
    lab: Optional[Tuple[float, float, float]] = None
) -> str:
    """Generate color information string based on user preferences.
    
    Args:
        rgb: RGB color values (0-255)
        lab: L*a*b* color values (optional)
        
    Returns:
        Formatted color information string based on user preferences
    """
    try:
        from utils.user_preferences import get_preferences_manager
        prefs = get_preferences_manager()
        
        # Get user preferences for what to display
        show_rgb = prefs.get_export_include_rgb()
        show_lab = prefs.get_export_include_lab()
        
        # Always show at least one color space to avoid empty display
        if not show_rgb and not show_lab:
            show_rgb = True
            show_lab = True
        
        color_info_parts = []
        
        # Add L*a*b* info if enabled and available
        if show_lab and lab is not None:
            color_info_parts.append(f"L*a*b*: {lab[0]:.1f}, {lab[1]:.1f}, {lab[2]:.1f}")
        
        # Add RGB info if enabled
        if show_rgb:
            color_info_parts.append(f"RGB: {rgb[0]:.0f}, {rgb[1]:.0f}, {rgb[2]:.0f}")
        
        return "\n".join(color_info_parts)
        
    except Exception as e:
        print(f"Error getting color display preferences: {e}")
        # Fallback to showing both values
        fallback_parts = []
        if lab is not None:
            fallback_parts.append(f"L*a*b*: {lab[0]:.1f}, {lab[1]:.1f}, {lab[2]:.1f}")
        fallback_parts.append(f"RGB: {rgb[0]:.0f}, {rgb[1]:.0f}, {rgb[2]:.0f}")
        return "\n".join(fallback_parts)


def get_conditional_color_values_text(
    rgb: Tuple[float, float, float], 
    lab: Optional[Tuple[float, float, float]] = None,
    compact: bool = False
) -> str:
    """Generate color values text in a more compact format for comparison views.
    
    Args:
        rgb: RGB color values (0-255)
        lab: L*a*b* color values (optional)
        compact: If True, use compact single-line format
        
    Returns:
        Formatted color values text based on user preferences
    """
    try:
        from utils.user_preferences import get_preferences_manager
        prefs = get_preferences_manager()
        
        # Get user preferences for what to display
        show_rgb = prefs.get_export_include_rgb()
        show_lab = prefs.get_export_include_lab()
        
        # Always show at least one color space to avoid empty display
        if not show_rgb and not show_lab:
            show_rgb = True
            show_lab = True
        
        if compact:
            # Single-line compact format for comparison views
            parts = []
            if show_lab and lab is not None:
                parts.append(f"L*: {lab[0]:>6.1f}  a*: {lab[1]:>6.1f}  b*: {lab[2]:>6.1f}")
            if show_rgb:
                parts.append(f"R: {int(rgb[0]):>3}  G: {int(rgb[1]):>3}  B: {int(rgb[2]):>3}")
            return "\n".join(parts)
        else:
            # Multi-line format for library views
            return get_conditional_color_info(rgb, lab)
            
    except Exception as e:
        print(f"Error getting color display preferences: {e}")
        # Fallback based on format
        if compact:
            fallback_parts = []
            if lab is not None:
                fallback_parts.append(f"L*: {lab[0]:>6.1f}  a*: {lab[1]:>6.1f}  b*: {lab[2]:>6.1f}")
            fallback_parts.append(f"R: {int(rgb[0]):>3}  G: {int(rgb[1]):>3}  B: {int(rgb[2]):>3}")
            return "\n".join(fallback_parts)
        else:
            return get_conditional_color_info(rgb, lab)
