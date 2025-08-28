import os
import sys

def create_app_support_dir():
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        if sys.platform == 'darwin':  # macOS
            app_support = os.path.expanduser('~/Library/Application Support/StampZ_II')
        elif sys.platform.startswith('win'):  # Windows
            app_support = os.path.expanduser('~/AppData/Local/StampZ_II')
        else:  # Linux and other Unix-like systems
            app_support = os.path.expanduser('~/.local/share/StampZ_II')
            
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
        
        # Create templates directory
        templates_dir = os.path.join(data_dir, 'templates')
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir)
        
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
                    
                    # Copy templates directory recursively if it doesn't exist
                    bundle_templates_dir = os.path.join(bundle_data_dir, 'templates')
                    if os.path.exists(bundle_templates_dir) and not os.listdir(templates_dir):
                        # Copy entire templates directory structure
                        def copy_tree(src_dir, dst_dir):
                            for item in os.listdir(src_dir):
                                src_path = os.path.join(src_dir, item)
                                dst_path = os.path.join(dst_dir, item)
                                if os.path.isdir(src_path):
                                    os.makedirs(dst_path, exist_ok=True)
                                    copy_tree(src_path, dst_path)
                                else:
                                    shutil.copy2(src_path, dst_path)
                        copy_tree(bundle_templates_dir, templates_dir)
                        print(f"DEBUG: Copied templates from bundle to {templates_dir}")
        except Exception as e:
            print(f"Warning: Could not copy initial data files: {e}")
        
        # Set environment variable for the app to use
        os.environ['STAMPZ_DATA_DIR'] = app_support
        print(f"DEBUG: StampZ data directory set to: {app_support}")

create_app_support_dir()
