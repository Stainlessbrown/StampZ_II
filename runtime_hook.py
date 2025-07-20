import os
import sys

def create_app_support_dir():
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        if sys.platform == 'darwin':  # macOS
            app_support = os.path.expanduser('~/Library/Application Support/StampZ')
        else:  # Linux
            app_support = os.path.expanduser('~/.local/share/StampZ')
            
        if not os.path.exists(app_support):
            os.makedirs(app_support)
        
        # Create all necessary subdirectories
        recent_dir = os.path.join(app_support, 'recent')
        if not os.path.exists(recent_dir):
            os.makedirs(recent_dir)
        
        # Create data directory structure
        data_dir = os.path.join(app_support, 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Create color_analysis directory
        color_analysis_dir = os.path.join(data_dir, 'color_analysis')
        if not os.path.exists(color_analysis_dir):
            os.makedirs(color_analysis_dir)
        
        # Create color_libraries directory
        color_libraries_dir = os.path.join(data_dir, 'color_libraries')
        if not os.path.exists(color_libraries_dir):
            os.makedirs(color_libraries_dir)
        
        # Copy initial data files if they don't exist
        try:
            # Check if running from PyInstaller bundle
            if hasattr(sys, '_MEIPASS'):
                bundle_data_dir = os.path.join(sys._MEIPASS, 'data')
                if os.path.exists(bundle_data_dir):
                    import shutil
                    
                    # Copy color_libraries if they don't exist
                    bundle_color_libs = os.path.join(bundle_data_dir, 'color_libraries')
                    if os.path.exists(bundle_color_libs):
                        for filename in os.listdir(bundle_color_libs):
                            src = os.path.join(bundle_color_libs, filename)
                            dst = os.path.join(color_libraries_dir, filename)
                            if not os.path.exists(dst) and os.path.isfile(src):
                                shutil.copy2(src, dst)
        except Exception as e:
            print(f"Warning: Could not copy initial data files: {e}")
        
        # Set environment variable for the app to use
        os.environ['STAMPZ_DATA_DIR'] = app_support
        print(f"DEBUG: StampZ data directory set to: {app_support}")

create_app_support_dir()
