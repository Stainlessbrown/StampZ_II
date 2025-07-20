#!/usr/bin/env python3
"""
Naming utilities for StampZ application.
Standardizes naming conventions for coordinate sets and sample sets.
"""

import re
from typing import Tuple


def standardize_name(name: str) -> str:
    """
    Standardize a name by converting to underscore-separated format.
    
    This function:
    - Replaces spaces and dashes with underscores
    - Removes any characters that aren't alphanumeric, underscore, or dash
    - Collapses multiple underscores into single underscores
    - Removes leading/trailing underscores
    
    Args:
        name: The name to standardize
        
    Returns:
        Standardized name using underscores only
        
    Examples:
        "My Sample Set" -> "My_Sample_Set"
        "Color-Test-1" -> "Color_Test_1"
        "F-137" -> "F_137"
        "Test__Set___Name" -> "Test_Set_Name"
    """
    if not name or not isinstance(name, str):
        return ""
    
    # Strip whitespace
    name = name.strip()
    
    # Replace spaces and dashes with underscores
    name = name.replace(' ', '_').replace('-', '_')
    
    # Remove any characters that aren't alphanumeric or underscore
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # Collapse multiple underscores into single underscores
    name = re.sub(r'_+', '_', name)
    
    # Remove leading and trailing underscores
    name = name.strip('_')
    
    return name


def standardize_with_feedback(original_name: str) -> tuple[str, bool]:
    """
    Standardize a name and return both the standardized name and whether it changed.
    
    Args:
        original_name: The original name to standardize
        
    Returns:
        Tuple of (standardized_name, was_changed)
    """
    standardized = standardize_name(original_name)
    was_changed = standardized != original_name.strip()
    
    return standardized, was_changed


def format_name_change_message(original: str, standardized: str) -> str:
    """
    Format a user-friendly message about name standardization.
    
    Args:
        original: The original name
        standardized: The standardized name
        
    Returns:
        Formatted message string
    """
    return f"Name standardized: '{original}' → '{standardized}'"


def validate_name(name: str) -> tuple[bool, str]:
    """
    Validate that a name meets our standards.
    
    Args:
        name: The name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not isinstance(name, str):
        return False, "Name cannot be empty"
    
    name = name.strip()
    
    if not name:
        return False, "Name cannot be empty"
    
    if len(name) > 100:
        return False, "Name is too long (maximum 100 characters)"
    
    # Check for any problematic characters that might cause issues
    if re.search(r'[<>:"/\\|?*]', name):
        return False, "Name contains invalid characters"
    
    return True, ""

