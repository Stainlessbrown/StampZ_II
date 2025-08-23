
import os
import sys
import shutil
from pathlib import Path
import logging
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_app_data_dir():
    """Get the appropriate application data directory based on platform."""
    if sys.platform == 'darwin':  # macOS
        return Path.home() / 'Library' / 'Application Support' / 'StampZ_II'
    elif sys.platform == 'win32':  # Windows
        app_data = os.getenv('APPDATA')
        return Path(app_data) / 'StampZ_II' if app_data else Path.home() / '.stampz_ii'
    else:  # Linux and others
        return Path.home() / '.local' / 'share' / 'StampZ_II'

def copy_directory_contents(src_dir: Path, dest_dir: Path):
    """Copy contents of src_dir to dest_dir, preserving directory structure."""
    try:
        if not src_dir.exists():
            logger.warning(f"Source directory does not exist: {src_dir}")
            return
            
        for item in src_dir.rglob('*'):
            if item.name == '.DS_Store':  # Skip macOS system files
                continue
                
            relative_path = item.relative_to(src_dir)
            destination = dest_dir / relative_path
            
            if item.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists() or item.stat().st_mtime > destination.stat().st_mtime:
                    shutil.copy2(item, destination)
                    logger.info(f"Copied {item} to {destination}")
    except Exception as e:
        logger.error(f"Error copying directory contents from {src_dir} to {dest_dir}: {e}")

def create_backup(user_data_dir: Path) -> bool:
    """Create a timestamped backup of critical user data.
    
    Args:
        user_data_dir: Path to user data directory
        
    Returns:
        bool: True if backup was successful
    """
    try:
        # Create backups directory
        backups_dir = user_data_dir / 'backups'
        backups_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamp for this backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = backups_dir / f'backup_{timestamp}'
        
        # Critical directories to backup
        critical_dirs = ['data']
        backup_created = False
        
        for dir_name in critical_dirs:
            source_dir = user_data_dir / dir_name
            if source_dir.exists() and any(source_dir.iterdir()):
                backup_subdir = backup_dir / dir_name
                backup_subdir.mkdir(parents=True, exist_ok=True)
                
                logger.info(f"Creating backup: {source_dir} -> {backup_subdir}")
                copy_directory_contents(source_dir, backup_subdir)
                backup_created = True
        
        if backup_created:
            # Create backup metadata
            metadata = {
                'timestamp': timestamp,
                'created': datetime.now().isoformat(),
                'directories': critical_dirs,
                'platform': sys.platform
            }
            
            metadata_file = backup_dir / 'backup_info.json'
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Backup created successfully: {backup_dir}")
            return True
        else:
            logger.info("No data found to backup")
            # Remove empty backup directory
            if backup_dir.exists():
                backup_dir.rmdir()
            return False
            
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return False

def get_latest_backup(user_data_dir: Path) -> Path:
    """Get the path to the most recent backup.
    
    Args:
        user_data_dir: Path to user data directory
        
    Returns:
        Path: Path to latest backup directory, or None if no backups exist
    """
    try:
        backups_dir = user_data_dir / 'backups'
        if not backups_dir.exists():
            return None
            
        backup_dirs = [d for d in backups_dir.iterdir() if d.is_dir() and d.name.startswith('backup_')]
        if not backup_dirs:
            return None
            
        # Sort by timestamp (embedded in directory name)
        backup_dirs.sort(key=lambda x: x.name, reverse=True)
        return backup_dirs[0]
        
    except Exception as e:
        logger.error(f"Error finding latest backup: {e}")
        return None

def restore_from_backup(user_data_dir: Path, backup_dir: Path = None) -> bool:
    """Restore user data from the latest backup.
    
    Args:
        user_data_dir: Path to user data directory
        backup_dir: Specific backup to restore from (optional)
        
    Returns:
        bool: True if restore was successful
    """
    try:
        if backup_dir is None:
            backup_dir = get_latest_backup(user_data_dir)
            
        if backup_dir is None or not backup_dir.exists():
            logger.warning("No backup found to restore from")
            return False
            
        logger.info(f"Restoring from backup: {backup_dir}")
        
        # Load backup metadata if available
        metadata_file = backup_dir / 'backup_info.json'
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
                logger.info(f"Restoring backup from {metadata['created']}")
        
        # Restore critical directories
        critical_dirs = ['data']
        restored_count = 0
        
        for dir_name in critical_dirs:
            backup_source = backup_dir / dir_name
            restore_target = user_data_dir / dir_name
            
            if backup_source.exists():
                logger.info(f"Restoring: {backup_source} -> {restore_target}")
                
                # Ensure target directory exists
                restore_target.mkdir(parents=True, exist_ok=True)
                
                # Copy backup contents to target
                copy_directory_contents(backup_source, restore_target)
                restored_count += 1
        
        if restored_count > 0:
            logger.info(f"Successfully restored {restored_count} directories from backup")
            return True
        else:
            logger.warning("No directories were restored from backup")
            return False
            
    except Exception as e:
        logger.error(f"Error restoring from backup: {e}")
        return False

def cleanup_old_backups(user_data_dir: Path, keep_count: int = 5) -> None:
    """Clean up old backups, keeping only the most recent ones.
    
    Args:
        user_data_dir: Path to user data directory
        keep_count: Number of recent backups to keep
    """
    try:
        backups_dir = user_data_dir / 'backups'
        if not backups_dir.exists():
            return
            
        backup_dirs = [d for d in backups_dir.iterdir() if d.is_dir() and d.name.startswith('backup_')]
        if len(backup_dirs) <= keep_count:
            return
            
        # Sort by timestamp (newest first)
        backup_dirs.sort(key=lambda x: x.name, reverse=True)
        
        # Remove old backups
        for old_backup in backup_dirs[keep_count:]:
            logger.info(f"Removing old backup: {old_backup}")
            shutil.rmtree(old_backup)
            
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")

def check_and_preserve_data(user_data_dir: Path) -> None:
    """Check if user data exists and create backup, or restore if data is missing.
    
    Args:
        user_data_dir: Path to user data directory
    """
    try:
        data_dir = user_data_dir / 'data'
        
        # Check if critical data directories exist and have content
        critical_subdirs = ['color_libraries', 'coordinates.db']
        has_existing_data = False
        
        if data_dir.exists():
            # Check for color libraries
            color_libs_dir = data_dir / 'color_libraries'
            if color_libs_dir.exists() and any(color_libs_dir.glob('*.db')):
                has_existing_data = True
                logger.info("Found existing color libraries")
            
            # Check for coordinates database
            coordinates_db = data_dir / 'coordinates.db'
            if coordinates_db.exists() and coordinates_db.stat().st_size > 0:
                has_existing_data = True
                logger.info("Found existing coordinates database")
        
        if has_existing_data:
            # Create backup of existing data
            logger.info("Creating backup of existing user data...")
            if create_backup(user_data_dir):
                logger.info("✓ Backup created successfully")
            else:
                logger.warning("⚠ Backup creation failed")
        else:
            # No existing data found, try to restore from backup
            logger.info("No existing user data found, checking for backups...")
            latest_backup = get_latest_backup(user_data_dir)
            
            if latest_backup:
                logger.info(f"Found backup: {latest_backup.name}")
                if restore_from_backup(user_data_dir, latest_backup):
                    logger.info("✓ Successfully restored user data from backup")
                else:
                    logger.warning("⚠ Failed to restore from backup")
            else:
                logger.info("No backups found - this appears to be a fresh installation")
        
        # Clean up old backups to save space
        cleanup_old_backups(user_data_dir, keep_count=5)
        
    except Exception as e:
        logger.error(f"Error in data preservation check: {e}")

# Get the application directories
if getattr(sys, 'frozen', False):
    app_bundle_dir = Path(sys._MEIPASS)
    logger.info(f"Running from app bundle: {app_bundle_dir}")
else:
    app_bundle_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logger.info(f"Running from Python environment: {app_bundle_dir}")

# Get user data directory - check if we're in development mode first
if getattr(sys, 'frozen', False):
    # Running as packaged app - use system directories
    user_data_dir = get_app_data_dir()
    logger.info(f"Packaged app mode - User data directory: {user_data_dir}")
else:
    # Running from source - check if we're in a development directory
    script_dir = Path(__file__).parent.absolute()
    
    # If running from a directory that looks like development (contains main.py, gui/, utils/)
    if (script_dir / 'main.py').exists() and (script_dir / 'gui').exists():
        # Development mode - use relative data directory
        user_data_dir = script_dir
        logger.info(f"Development mode - Using local directory: {user_data_dir}")
    else:
        # Running from installed Python but not in dev folder - use system directories
        user_data_dir = get_app_data_dir()
        logger.info(f"Installed Python mode - User data directory: {user_data_dir}")

# *** DATA PRESERVATION SYSTEM ***
# Backup system is available but disabled for normal operation
# Uncomment the lines below if backup/restore functionality is needed during development
# logger.info("=== Starting Data Preservation Check ===")
# check_and_preserve_data(user_data_dir)
# logger.info("=== Data Preservation Check Complete ===")
logger.info("Data preservation system available but not running automatically")

# Add our app directories to Python path
for dir_name in ['gui', 'utils']:
    dir_path = app_bundle_dir / dir_name
    if str(dir_path) not in sys.path:
        sys.path.insert(0, str(dir_path))
        logger.info(f"Added to Python path: {dir_path}")

# Ensure user data directories exist and copy initial data
data_dirs = ['data', 'exports', 'recent']
for dir_name in data_dirs:
    user_dir = user_data_dir / dir_name
    user_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured directory exists: {user_dir}")
    
    # Copy initial data files on first run
    if dir_name == 'data':
        bundle_data_dir = app_bundle_dir / 'data'
        if bundle_data_dir.exists():
            logger.info(f"Copying data from {bundle_data_dir} to {user_dir}")
            copy_directory_contents(bundle_data_dir, user_dir)

# Set environment variable for app data directory
os.environ['STAMPZ_DATA_DIR'] = str(user_data_dir)
logger.info("Initialization complete")
