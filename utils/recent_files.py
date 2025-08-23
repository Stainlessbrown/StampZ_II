"""Manages the recent files functionality."""

import os
import sys
import shutil
import time
from pathlib import Path
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class RecentFilesManager:
    """Manages a list of recently saved files."""
    
    def __init__(self, recent_dir: str = None, max_files: int = 10):
        """
        Initialize the recent files manager.
        
        Args:
            recent_dir: Path to the recent files directory. If None, uses app-specific recent directory
            max_files: Maximum number of recent files to maintain
        """
        self.max_files = max_files
        
        # Use the environment variable if set, otherwise use centralized path logic
        stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
        
        if recent_dir:
            self.recent_dir = Path(recent_dir)
        elif stampz_data_dir:
            self.recent_dir = Path(stampz_data_dir) / 'recent'
            logger.info(f"Using recent directory from STAMPZ_DATA_DIR: {self.recent_dir}")
        else:
            # Use centralized path logic to be consistent with rest of app
            try:
                from .path_utils import get_base_data_dir
                base_data_dir = Path(get_base_data_dir())
                self.recent_dir = base_data_dir.parent / 'recent'
                logger.info(f"Using centralized recent directory: {self.recent_dir}")
            except ImportError:
                # Fallback to original logic if path_utils not available
                if sys.platform == 'win32':
                    app_data = os.getenv('APPDATA')
                    if app_data:
                        self.recent_dir = Path(app_data) / 'StampZ_II' / 'recent'
                    else:
                        self.recent_dir = Path.home() / '.stampz_ii' / 'recent'
                elif sys.platform == 'darwin':
                    self.recent_dir = Path.home() / 'Library' / 'Application Support' / 'StampZ_II' / 'recent'
                else:  # Linux and others
                    self.recent_dir = Path.home() / '.stampz_ii' / 'recent'
                logger.info(f"Using fallback recent directory: {self.recent_dir}")
        
        # Ensure recent directory exists
        try:
            self.recent_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Recent files directory initialized at: {self.recent_dir}")
        except Exception as e:
            logger.error(f"Failed to create recent directory at {self.recent_dir}: {e}")
            # Fallback to temporary directory if we can't create in preferred location
            import tempfile
            self.recent_dir = Path(tempfile.gettempdir()) / 'stampz_recent'
            self.recent_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback recent directory: {self.recent_dir}")
        
    def add_file(self, filepath: str) -> Optional[str]:
        """
        Add a file to recent files.
        
        Args:
            filepath: Path to the file to add
            
        Returns:
            Path to the copied file in recent directory, or None if copy failed
        """
        try:
            # Use original filename, handling duplicates if needed
            orig_name = Path(filepath).name
            dest_path = self.recent_dir / orig_name
            
            # If file exists, add a number to make it unique
            counter = 1
            while dest_path.exists():
                base, ext = os.path.splitext(orig_name)
                dest_path = self.recent_dir / f"{base}_{counter}{ext}"
                counter += 1
            
            # Copy the file
            shutil.copy2(filepath, dest_path)
            
            # Set access and modification times to now
            current_time = time.time()
            os.utime(dest_path, (current_time, current_time))
            
            logger.info(f"Added {filepath} to recent files as {dest_path}")
            
            # Cleanup old files if needed
            self._cleanup_old_files()
            
            return str(dest_path)
            
        except (OSError, shutil.Error) as e:
            logger.error(f"Failed to add file to recent: {e}")
            return None
    
    def get_recent_files(self) -> List[str]:
        """
        Get list of recent files, newest first.
        
        Returns:
            List of paths to recent files
        """
        try:
            logger.debug("Starting to get and sort recent files.")
            
            # Get all files with their modification times
            files_with_times = []
            for f in os.listdir(self.recent_dir):
                full_path = os.path.join(self.recent_dir, f)
                if os.path.isfile(full_path):
                    try:
                        mtime = os.path.getmtime(full_path)
                        logger.debug(f"File: {f}, MTime: {datetime.fromtimestamp(mtime)}")
                        files_with_times.append((full_path, mtime))
                    except OSError as e:
                        logger.error(f"Error getting mtime for {f}: {e}")
                        continue
            
            # Sort by modification time, newest first
            files_with_times.sort(key=lambda x: (-max(os.path.getmtime(x[0]), os.path.getctime(x[0])), x[0]))  # Sort by newest time first
            logger.debug("Files sorted by modification time (newest first):")
            for f, mt in files_with_times:
                logger.debug(f"  {datetime.fromtimestamp(mt)}: {f}")
            
            # Return just the file paths
            return [str(path) for path, _ in files_with_times]
        except OSError as e:
            logger.error(f"Failed to list recent files: {e}")
            return []
    
    def _cleanup_old_files(self):
        """Remove oldest files if we're over the limit.
        Ensures only the most recent 'max_files' files are kept.
        """
        try:
            logger.debug(f"Starting cleanup of old files (keeping max {self.max_files} files)")
            
            # Get all files with their modification times using Path objects
            files_with_times = []
            for path in self.recent_dir.iterdir():
                if path.is_file():
                    try:
                        # Get both mtime and ctime to handle copied files
                        mtime = path.stat().st_mtime
                        ctime = path.stat().st_ctime
                        # Use the more recent of mtime and ctime
                        timestamp = max(mtime, ctime)
                        logger.debug(f"File: {path.name}, Time: {datetime.fromtimestamp(timestamp)}")
                        files_with_times.append((path, timestamp))
                    except (OSError, PermissionError) as e:
                        logger.error(f"Error accessing file {path}: {e}")
                        continue
            
            # Early exit if we're under the limit
            if len(files_with_times) <= self.max_files:
                logger.debug(f"No cleanup needed. Current files: {len(files_with_times)}, Max: {self.max_files}")
                return
            
            # Sort by timestamp, newest first
            files_with_times.sort(key=lambda x: x[1], reverse=True)
            
            # Identify files to remove (everything after max_files)
            files_to_remove = files_with_times[self.max_files:]
            
            # Remove old files
            for file_path, timestamp in files_to_remove:
                try:
                    # Use pathlib's unlink with missing_ok=True to handle race conditions
                    file_path.unlink(missing_ok=True)
                    logger.info(f"Removed old recent file: {file_path.name} "
                             f"(modified: {datetime.fromtimestamp(timestamp)})")
                except (OSError, PermissionError) as e:
                    logger.error(f"Failed to remove old file {file_path}: {e}")
                    # Continue trying to remove other files
                    continue
            
            # Verify cleanup
            remaining_files = list(self.recent_dir.iterdir())
            logger.info(f"Cleanup complete. Remaining files: {len(remaining_files)}")
            
        except Exception as e:
            logger.error(f"Error during cleanup of old files: {e}")
        finally:
            logger.debug("Cleanup of old files complete.")
            
    def __del__(self):
        """Ensure cleanup is performed when the manager is destroyed."""
        try:
            self._cleanup_old_files()
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")

