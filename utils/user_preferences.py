#!/usr/bin/env python3
"""
User preferences system for StampZ
Manages user-configurable settings like export locations.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class ExportPreferences:
    """Preferences for file exports."""
    ods_export_directory: str = ""  # Empty means use default
    auto_open_after_export: bool = True
    export_filename_format: str = "{sample_set}_{date}"  # Template for filename
    include_timestamp: bool = False  # Whether to include timestamp in filename
    preferred_export_format: str = "ods"  # Preferred export format: 'ods', 'xlsx', or 'csv'
    export_normalized_values: bool = False  # Export color values normalized to 0.0-1.0 range
    export_include_rgb: bool = True  # Include RGB color values in export
    export_include_lab: bool = True  # Include L*a*b* color values in export


@dataclass
class FileDialogPreferences:
    """Preferences for file dialogs."""
    last_open_directory: str = ""  # Last directory used for opening files
    last_save_directory: str = ""  # Last directory used for saving files
    remember_directories: bool = True  # Whether to remember last used directories


@dataclass
class ColorLibraryPreferences:
    """Preferences for color library system."""
    default_library: str = "basic_colors"  # Default color library to use
    hide_non_selected_standards: bool = False  # Hide non-selected standard values in Compare and Libraries


@dataclass
class SampleAreaPreferences:
    """Preferences for default sample area settings."""
    default_shape: str = "circle"  # Default shape: "circle" or "rectangle"
    default_width: int = 10  # Default width/diameter in pixels
    default_height: int = 10  # Default height in pixels (same as width for circles)
    default_anchor: str = "center"  # Default anchor position


# InterfacePreferences class removed - complexity levels no longer used
@dataclass 
class UserPreferences:
    """Main user preferences container."""
    export_prefs: ExportPreferences
    file_dialog_prefs: FileDialogPreferences
    color_library_prefs: ColorLibraryPreferences
    sample_area_prefs: SampleAreaPreferences
    # interface_prefs removed - complexity levels no longer used
    
    def __init__(self):
        self.export_prefs = ExportPreferences()
        self.file_dialog_prefs = FileDialogPreferences()
        self.color_library_prefs = ColorLibraryPreferences()
        self.sample_area_prefs = SampleAreaPreferences()
        # self.interface_prefs removed - complexity levels no longer used


class PreferencesManager:
    """Manages user preferences with persistent storage."""
    
    def __init__(self):
        self.preferences = UserPreferences()
        self.prefs_file = self._get_preferences_file_path()
        self.load_preferences()
    
    def _get_preferences_file_path(self) -> Path:
        """Get the path to the preferences file."""
        # Use the same user data directory as other app data
        from .path_utils import get_base_data_dir
        
        base_dir = Path(get_base_data_dir()).parent  # Go up one level from /data
        prefs_file = base_dir / "preferences.json"
        
        return prefs_file
    
    def _get_default_export_directory(self) -> str:
        """Get the default export directory."""
        # Default to user's Desktop/StampZ Exports directory
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            default_dir = desktop / "StampZ Exports"
        else:
            # Fallback to Documents if Desktop doesn't exist
            documents = Path.home() / "Documents" 
            default_dir = documents / "StampZ Exports"
        
        return str(default_dir)
    
    def get_export_directory(self) -> str:
        """Get the current export directory, creating it if needed."""
        export_dir = self.preferences.export_prefs.ods_export_directory
        
        if not export_dir:
            # Use default if not set
            export_dir = self._get_default_export_directory()
            
        # Ensure directory exists
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        
        return export_dir
    
    def set_export_directory(self, directory: str) -> bool:
        """Set the export directory."""
        try:
            # Validate that the directory exists or can be created
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            
            # Update preferences
            self.preferences.export_prefs.ods_export_directory = str(path)
            self.save_preferences()
            
            return True
        except Exception as e:
            print(f"Error setting export directory: {e}")
            return False
    
    def get_last_open_directory(self) -> Optional[str]:
        """Get the last directory used for opening files."""
        if not self.preferences.file_dialog_prefs.remember_directories:
            return None
            
        last_dir = self.preferences.file_dialog_prefs.last_open_directory
        if last_dir and Path(last_dir).exists():
            return last_dir
        return None
    
    def set_last_open_directory(self, directory: str) -> bool:
        """Set the last directory used for opening files."""
        if not self.preferences.file_dialog_prefs.remember_directories:
            return True  # Don't save if remembering is disabled
            
        try:
            path = Path(directory)
            if path.is_file():
                # If it's a file, get the parent directory
                directory = str(path.parent)
            
            self.preferences.file_dialog_prefs.last_open_directory = directory
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting last open directory: {e}")
            return False
    
    def get_last_save_directory(self) -> Optional[str]:
        """Get the last directory used for saving files."""
        if not self.preferences.file_dialog_prefs.remember_directories:
            return None
            
        last_dir = self.preferences.file_dialog_prefs.last_save_directory
        if last_dir and Path(last_dir).exists():
            return last_dir
        return None
    
    def set_last_save_directory(self, directory: str) -> bool:
        """Set the last directory used for saving files."""
        if not self.preferences.file_dialog_prefs.remember_directories:
            return True  # Don't save if remembering is disabled
            
        try:
            path = Path(directory)
            if path.is_file():
                # If it's a file, get the parent directory
                directory = str(path.parent)
            
            self.preferences.file_dialog_prefs.last_save_directory = directory
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting last save directory: {e}")
            return False
    
    def get_remember_directories(self) -> bool:
        """Get whether to remember last used directories."""
        return self.preferences.file_dialog_prefs.remember_directories
    
    def set_remember_directories(self, remember: bool) -> bool:
        """Set whether to remember last used directories."""
        try:
            self.preferences.file_dialog_prefs.remember_directories = remember
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting remember directories preference: {e}")
            return False
    
    def get_preferred_export_format(self) -> str:
        """Get the preferred export format."""
        return self.preferences.export_prefs.preferred_export_format
    
    def set_preferred_export_format(self, format_type: str) -> bool:
        """Set the preferred export format.
        
        Args:
            format_type: Export format ('ods', 'xlsx', or 'csv')
        """
        if format_type not in ['ods', 'xlsx', 'csv']:
            print(f"Error: Invalid export format '{format_type}'. Use 'ods', 'xlsx', or 'csv'.")
            return False
        
        try:
            self.preferences.export_prefs.preferred_export_format = format_type
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting preferred export format: {e}")
            return False
    
    def get_export_normalized_values(self) -> bool:
        """Get whether to export color values normalized to 0.0-1.0 range."""
        return self.preferences.export_prefs.export_normalized_values
    
    def set_export_normalized_values(self, normalized: bool) -> bool:
        """Set whether to export color values normalized to 0.0-1.0 range.
        
        Args:
            normalized: True to export normalized values (0.0-1.0), False for standard ranges
        """
        try:
            self.preferences.export_prefs.export_normalized_values = normalized
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting normalized export preference: {e}")
            return False
    
    def get_export_include_rgb(self) -> bool:
        """Get whether to include RGB color values in exports."""
        return self.preferences.export_prefs.export_include_rgb
    
    def set_export_include_rgb(self, include_rgb: bool) -> bool:
        """Set whether to include RGB color values in exports.
        
        Args:
            include_rgb: True to include RGB values, False to exclude them
        """
        try:
            self.preferences.export_prefs.export_include_rgb = include_rgb
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting RGB export preference: {e}")
            return False
    
    def get_export_include_lab(self) -> bool:
        """Get whether to include L*a*b* color values in exports."""
        return self.preferences.export_prefs.export_include_lab
    
    def set_export_include_lab(self, include_lab: bool) -> bool:
        """Set whether to include L*a*b* color values in exports.
        
        Args:
            include_lab: True to include L*a*b* values, False to exclude them
        """
        try:
            # Ensure at least one color space is always included
            if not include_lab and not self.preferences.export_prefs.export_include_rgb:
                print("Error: At least one color space (RGB or L*a*b*) must be included in exports")
                return False
            
            self.preferences.export_prefs.export_include_lab = include_lab
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting L*a*b* export preference: {e}")
            return False
    
    def get_default_color_library(self) -> str:
        """Get the default color library."""
        return self.preferences.color_library_prefs.default_library
    
    def set_default_color_library(self, library_name: str) -> bool:
        """Set the default color library.
        
        Args:
            library_name: Name of the color library to set as default
        """
        try:
            self.preferences.color_library_prefs.default_library = library_name
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting default color library: {e}")
            return False
    
    def get_hide_non_selected_standards(self) -> bool:
        """Get whether to hide non-selected standard values in Compare and Libraries."""
        return self.preferences.color_library_prefs.hide_non_selected_standards
    
    def set_hide_non_selected_standards(self, hide: bool) -> bool:
        """Set whether to hide non-selected standard values in Compare and Libraries.
        
        Args:
            hide: True to hide non-selected values, False to show all values
        """
        try:
            self.preferences.color_library_prefs.hide_non_selected_standards = hide
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting hide non-selected standards preference: {e}")
            return False
    
    def get_available_color_libraries(self) -> List[str]:
        """Get a list of available color libraries."""
        try:
            from .path_utils import get_color_libraries_dir
            library_dir = get_color_libraries_dir()
            
            # Ensure library directory exists
            os.makedirs(library_dir, exist_ok=True)
            
            # Get all library files
            library_files = [f for f in os.listdir(library_dir) if f.endswith("_library.db")]
            
            # Always include basic_colors if not found
            if "basic_colors_library.db" not in library_files:
                library_files.append("basic_colors_library.db")
            
            # Convert to library names (remove "_library.db" suffix)
            library_names = [f[:-11] for f in library_files]
            
            return sorted(library_names)
        except Exception as e:
            print(f"Error getting available color libraries: {e}")
            return ["basic_colors"]
    
    # Interface mode methods removed - complexity levels no longer used
    
    def get_default_sample_shape(self) -> str:
        """Get the default sample area shape."""
        return self.preferences.sample_area_prefs.default_shape
    
    def set_default_sample_shape(self, shape: str) -> bool:
        """Set the default sample area shape.
        
        Args:
            shape: Shape type ('circle' or 'rectangle')
        """
        if shape not in ['circle', 'rectangle']:
            print(f"Error: Invalid shape '{shape}'. Use 'circle' or 'rectangle'.")
            return False
        
        try:
            self.preferences.sample_area_prefs.default_shape = shape
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting default sample shape: {e}")
            return False
    
    def get_default_sample_width(self) -> int:
        """Get the default sample area width/diameter."""
        return self.preferences.sample_area_prefs.default_width
    
    def set_default_sample_width(self, width: int) -> bool:
        """Set the default sample area width/diameter.
        
        Args:
            width: Width in pixels (must be positive)
        """
        if width <= 0:
            print(f"Error: Width must be positive, got {width}")
            return False
        
        try:
            self.preferences.sample_area_prefs.default_width = width
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting default sample width: {e}")
            return False
    
    def get_default_sample_height(self) -> int:
        """Get the default sample area height."""
        return self.preferences.sample_area_prefs.default_height
    
    def set_default_sample_height(self, height: int) -> bool:
        """Set the default sample area height.
        
        Args:
            height: Height in pixels (must be positive)
        """
        if height <= 0:
            print(f"Error: Height must be positive, got {height}")
            return False
        
        try:
            self.preferences.sample_area_prefs.default_height = height
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting default sample height: {e}")
            return False
    
    def get_default_sample_anchor(self) -> str:
        """Get the default sample area anchor position."""
        return self.preferences.sample_area_prefs.default_anchor
    
    def set_default_sample_anchor(self, anchor: str) -> bool:
        """Set the default sample area anchor position.
        
        Args:
            anchor: Anchor position ('center', 'top_left', 'top_right', 'bottom_left', 'bottom_right')
        """
        valid_anchors = ['center', 'top_left', 'top_right', 'bottom_left', 'bottom_right']
        if anchor not in valid_anchors:
            print(f"Error: Invalid anchor '{anchor}'. Use one of: {', '.join(valid_anchors)}")
            return False
        
        try:
            self.preferences.sample_area_prefs.default_anchor = anchor
            self.save_preferences()
            return True
        except Exception as e:
            print(f"Error setting default sample anchor: {e}")
            return False
    
    def get_default_sample_settings(self) -> dict:
        """Get all default sample area settings as a dictionary."""
        return {
            'shape': self.preferences.sample_area_prefs.default_shape,
            'width': self.preferences.sample_area_prefs.default_width,
            'height': self.preferences.sample_area_prefs.default_height,
            'anchor': self.preferences.sample_area_prefs.default_anchor
        }
    
    def get_export_filename(self, sample_set_name: str = None, extension: str = ".ods") -> str:
        """Generate export filename based on preferences."""
        from datetime import datetime
        
        # Get template and preferences
        template = self.preferences.export_prefs.export_filename_format
        include_timestamp = self.preferences.export_prefs.include_timestamp
        
        # Prepare template variables
        variables = {
            "sample_set": sample_set_name or "color_analysis",
            "date": datetime.now().strftime("%Y%m%d"),
            "datetime": datetime.now().strftime("%Y%m%d_%H%M%S")
        }
        
        # Format the filename
        try:
            filename = template.format(**variables)
        except (KeyError, ValueError):
            # Fallback to simple format if template fails
            filename = f"{variables['sample_set']}_{variables['date']}"
        
        # Add timestamp if requested
        if include_timestamp:
            timestamp = datetime.now().strftime("_%H%M%S")
            filename += timestamp
            
        return filename + extension
    
    def load_preferences(self) -> bool:
        """Load preferences from file."""
        try:
            if self.prefs_file.exists():
                with open(self.prefs_file, 'r') as f:
                    data = json.load(f)
                
                # Load export preferences
                if 'export_prefs' in data:
                    export_data = data['export_prefs']
                    self.preferences.export_prefs = ExportPreferences(
                        ods_export_directory=export_data.get('ods_export_directory', ''),
                        auto_open_after_export=export_data.get('auto_open_after_export', True),
                        export_filename_format=export_data.get('export_filename_format', '{sample_set}_{date}'),
                        include_timestamp=export_data.get('include_timestamp', False),
                        preferred_export_format=export_data.get('preferred_export_format', 'ods'),
                        export_normalized_values=export_data.get('export_normalized_values', False),
                        export_include_rgb=export_data.get('export_include_rgb', True),
                        export_include_lab=export_data.get('export_include_lab', True)
                    )
                
                # Load file dialog preferences
                if 'file_dialog_prefs' in data:
                    dialog_data = data['file_dialog_prefs']
                    self.preferences.file_dialog_prefs = FileDialogPreferences(
                        last_open_directory=dialog_data.get('last_open_directory', ''),
                        last_save_directory=dialog_data.get('last_save_directory', ''),
                        remember_directories=dialog_data.get('remember_directories', True)
                    )
                
                # Load color library preferences
                if 'color_library_prefs' in data:
                    library_data = data['color_library_prefs']
                    self.preferences.color_library_prefs = ColorLibraryPreferences(
                        default_library=library_data.get('default_library', 'basic_colors'),
                        hide_non_selected_standards=library_data.get('hide_non_selected_standards', False)
                    )
                
                # Load sample area preferences
                if 'sample_area_prefs' in data:
                    sample_data = data['sample_area_prefs']
                    self.preferences.sample_area_prefs = SampleAreaPreferences(
                        default_shape=sample_data.get('default_shape', 'circle'),
                        default_width=sample_data.get('default_width', 10),
                        default_height=sample_data.get('default_height', 10),
                        default_anchor=sample_data.get('default_anchor', 'center')
                    )
                
                # Interface preferences removed - complexity levels no longer used
                
                print(f"Loaded preferences from {self.prefs_file}")
                return True
        except Exception as e:
            print(f"Error loading preferences: {e}")
            
        # Use defaults if loading failed
        self.preferences = UserPreferences()
        return False
    
    def save_preferences(self) -> bool:
        """Save preferences to file, preserving any existing data."""
        try:
            # Ensure the preferences directory exists
            self.prefs_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing preferences to preserve other sections
            existing_data = {}
            if self.prefs_file.exists():
                try:
                    with open(self.prefs_file, 'r') as f:
                        existing_data = json.load(f)
                except json.JSONDecodeError:
                    # If file is corrupted, start fresh but preserve structure
                    existing_data = {}
            
            # Update only the preferences we manage, preserving everything else
            existing_data.update({
                'export_prefs': asdict(self.preferences.export_prefs),
                'file_dialog_prefs': asdict(self.preferences.file_dialog_prefs),
                'color_library_prefs': asdict(self.preferences.color_library_prefs),
                'sample_area_prefs': asdict(self.preferences.sample_area_prefs),
                # 'interface_prefs': removed - complexity levels no longer used
            })
            
            with open(self.prefs_file, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
            print(f"Saved preferences to {self.prefs_file}")
            return True
        except Exception as e:
            print(f"Error saving preferences: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset all preferences to defaults."""
        self.preferences = UserPreferences()
        return self.save_preferences()
    
    def get_preferences_summary(self) -> Dict[str, Any]:
        """Get a summary of current preferences."""
        return {
            'Export Directory': self.get_export_directory(),
            'Auto-open after export': self.preferences.export_prefs.auto_open_after_export,
            'Filename format': self.preferences.export_prefs.export_filename_format,
            'Include timestamp': self.preferences.export_prefs.include_timestamp,
            'Preferences file': str(self.prefs_file)
        }


# Global instance for easy access
_prefs_manager = None

def get_preferences_manager() -> PreferencesManager:
    """Get the global preferences manager instance."""
    global _prefs_manager
    if _prefs_manager is None:
        _prefs_manager = PreferencesManager()
    return _prefs_manager


def get_export_directory() -> str:
    """Convenience function to get current export directory."""
    return get_preferences_manager().get_export_directory()


def set_export_directory(directory: str) -> bool:
    """Convenience function to set export directory."""
    return get_preferences_manager().set_export_directory(directory)


# Interface mode convenience functions removed - complexity levels no longer used
