#!/usr/bin/env python3
"""
User preferences system for StampZ
Manages user-configurable settings like export locations.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ExportPreferences:
    """Preferences for file exports."""
    ods_export_directory: str = ""  # Empty means use default
    auto_open_after_export: bool = True
    export_filename_format: str = "{sample_set}_{date}"  # Template for filename
    include_timestamp: bool = False  # Whether to include timestamp in filename
    preferred_export_format: str = "ods"  # Preferred export format: 'ods', 'xlsx', or 'csv'


@dataclass
class FileDialogPreferences:
    """Preferences for file dialogs."""
    last_open_directory: str = ""  # Last directory used for opening files
    last_save_directory: str = ""  # Last directory used for saving files
    remember_directories: bool = True  # Whether to remember last used directories
    
    
@dataclass 
class UserPreferences:
    """Main user preferences container."""
    export_prefs: ExportPreferences
    file_dialog_prefs: FileDialogPreferences
    
    def __init__(self):
        self.export_prefs = ExportPreferences()
        self.file_dialog_prefs = FileDialogPreferences()


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
                        preferred_export_format=export_data.get('preferred_export_format', 'ods')
                    )
                
                # Load file dialog preferences
                if 'file_dialog_prefs' in data:
                    dialog_data = data['file_dialog_prefs']
                    self.preferences.file_dialog_prefs = FileDialogPreferences(
                        last_open_directory=dialog_data.get('last_open_directory', ''),
                        last_save_directory=dialog_data.get('last_save_directory', ''),
                        remember_directories=dialog_data.get('remember_directories', True)
                    )
                
                print(f"Loaded preferences from {self.prefs_file}")
                return True
        except Exception as e:
            print(f"Error loading preferences: {e}")
            
        # Use defaults if loading failed
        self.preferences = UserPreferences()
        return False
    
    def save_preferences(self) -> bool:
        """Save preferences to file."""
        try:
            # Ensure the preferences directory exists
            self.prefs_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dictionary for JSON serialization
            data = {
                'export_prefs': asdict(self.preferences.export_prefs),
                'file_dialog_prefs': asdict(self.preferences.file_dialog_prefs)
            }
            
            with open(self.prefs_file, 'w') as f:
                json.dump(data, f, indent=2)
                
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
