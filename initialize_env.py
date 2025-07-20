
import os
import sys
import shutil
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_app_data_dir():
    """Get the appropriate application data directory based on platform."""
    if sys.platform == 'darwin':  # macOS
        return Path.home() / 'Library' / 'Application Support' / 'StampZ'
    elif sys.platform == 'win32':  # Windows
        app_data = os.getenv('APPDATA')
        return Path(app_data) / 'StampZ' if app_data else Path.home() / '.stampz'
    else:  # Linux and others
        return Path.home() / '.local' / 'share' / 'StampZ'

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

# Get the application directories
if getattr(sys, 'frozen', False):
    app_bundle_dir = Path(sys._MEIPASS)
    logger.info(f"Running from app bundle: {app_bundle_dir}")
else:
    app_bundle_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logger.info(f"Running from Python environment: {app_bundle_dir}")

# Get user data directory
user_data_dir = get_app_data_dir()
logger.info(f"User data directory: {user_data_dir}")

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
