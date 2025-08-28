#!/usr/bin/env python3
"""StampZ - Main Application Entry Point
A image analysis application optimized for philatelic images"""

# Import initialize_env first to set up data preservation system
import initialize_env

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import logging
from datetime import datetime

from gui.canvas import CropCanvas, ShapeType, ToolMode
from gui.controls_reorganized import ReorganizedControlPanel as ControlPanel
from utils.image_processor import load_image, ImageLoadError, ImageSaveError
from utils.save_as import SaveManager, SaveOptions, SaveFormat
from utils.recent_files import RecentFilesManager
from utils.filename_manager import FilenameManager
from utils.image_straightener import StraighteningTool
from utils.ods_exporter import ODSExporter
from gui.preferences_dialog import show_preferences_dialog
from utils.path_utils import ensure_data_directories
# DependencyChecker imported at function level to avoid CI/CD issues

logger = logging.getLogger(__name__)

class StampZApp:
    """Main application window for StampZ."""
    def __init__(self, root: tk.Tk):
        # Ensure data directories exist first
        ensure_data_directories()
        
        self.root = root
        self.root.title("StampZ_II")
        self._set_application_name()
        try:
            self.root.tk.call('wm', 'class', self.root, 'StampZ_II')
        except:
            pass
        # Use the environment variable for recent files directory
        stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
        if stampz_data_dir:
            recent_dir = os.path.join(stampz_data_dir, 'recent')
            self.recent_files = RecentFilesManager(recent_dir=recent_dir)
        else:
            self.recent_files = RecentFilesManager()
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Account for dock/taskbar - be very conservative for smaller monitors
        # Base sizing on 13" MacBooks (1440x900) and smaller screens first
        if screen_height <= 768:  # 13" laptops and smaller (1366x768)
            window_height = int(screen_height * 0.55)  # Very aggressive - max 422px on 768px screen
        elif screen_height <= 900:  # 13" MacBooks (1440x900)
            window_height = int(screen_height * 0.58)  # Aggressive - max 522px on 900px screen
        elif screen_height <= 1080:  # 21.5" iMacs and similar (1920x1080)
            window_height = int(screen_height * 0.62)  # Conservative - max 670px on 1080px screen
        else:  # Larger monitors
            window_height = int(screen_height * 0.68)  # More room for large displays
        
        # For width, we can be more generous since horizontal space is less constrained
        window_width = int(screen_width * 0.85)
        
        # Position window with some top margin to account for menu bars
        x_position = (screen_width - window_width) // 2
        y_position = max(50, (screen_height - window_height) // 2)  # At least 50px from top
        
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Set minimum size to ensure all UI elements can be visible, but smaller for small monitors
        self.root.minsize(900, 780)  # Reduced to fit on 1366x768 and smaller screens
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.resizable(True, True)
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self._create_menu()
        self._create_widgets()
        self._bind_shortcuts()
        self.current_file = None
        self.control_panel.on_ruler_toggle = self._handle_ruler_toggle
        self.control_panel.on_grid_toggle = self._handle_grid_toggle
        self.control_panel.tool_mode.set("view")
        self._handle_tool_mode_change("view")
        self._apply_default_settings()
        self.current_image_metadata = None
        
        # Check optional dependencies at startup
        self._check_dependencies()

    def _set_application_name(self):
        try:
            self.root.tk.call('tk', 'appname', 'StampZ_II')
        except:
            pass

    def _create_menu(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Open...", command=self.open_image, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Clear", command=self.clear_image, accelerator="Ctrl+W")
        self.file_menu.add_command(label="Save As...", command=self.save_image, accelerator="Ctrl+S")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export Color Data to ODS...", command=self.export_color_data)
        self.file_menu.add_command(label="Database Viewer...", command=self.open_database_viewer)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit_app, accelerator="Ctrl+Q")

        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Reset View", command=self.reset_view, accelerator="Ctrl+R")
        self.edit_menu.add_command(label="Fit to Window", command=self.fit_to_window, accelerator="F11")

        self.color_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Color Analysis", menu=self.color_menu)
        self.color_menu.add_command(label="Color Library Manager...", command=self.open_color_library)
        self.color_menu.add_command(label="Compare Sample to Library...", command=self.compare_sample_to_library)
        self.color_menu.add_separator()
        self.color_menu.add_command(label="Create Standard Libraries", command=self.create_standard_libraries)
        self.color_menu.add_separator()
        self.color_menu.add_command(label="Spectral Analysis...", command=self.open_spectral_analysis)
        self.color_menu.add_command(label="3D Color Space Analysis...", command=self.open_3d_analysis)
        self.color_menu.add_command(label="Export Analysis with Library Matches...", command=self.export_with_library_matches)

        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="About", command=self.show_about)
        self.help_menu.add_command(label="Preferences...", command=self.open_preferences)

    def _create_widgets(self):
        self.canvas = CropCanvas(self.main_container, bg='white', width=800, height=600)
        self.canvas.set_dimensions_callback(self._update_crop_dimensions)
        self.straightening_tool = StraighteningTool()
        self.canvas.main_app = self
        self.control_panel = ControlPanel(
            self.main_container,
            on_reset=self.reset_view,
            on_open=self.open_image,
            on_save=self.save_image,
            on_clear=self.clear_image,
            on_quit=self.quit_app,
            on_vertex_count_change=self._handle_vertex_count_change,
            on_fit_to_window=self.fit_to_window,
            on_transparency_change=self._handle_transparency_change,
            on_shape_type_change=self._handle_shape_type_change,
            on_tool_mode_change=self._handle_tool_mode_change,
        )
        self.control_panel.main_app = self
        self._handle_shape_type_change(ShapeType.POLYGON)
        self.control_panel.on_line_color_change = self._handle_line_color_change
        self.control_panel.canvas = self.canvas
        self.control_panel.main_app = self
        self.canvas.set_coordinate_callback(self.control_panel.update_mouse_coordinates)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.control_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

    def _bind_shortcuts(self):
        self.root.bind('<Control-o>', lambda e: self.open_image())
        self.root.bind('<Control-s>', lambda e: self.save_image())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        self.root.bind('<Control-w>', lambda e: self.clear_image())
        self.root.bind('<Control-r>', lambda e: self.reset_view())
        self.root.bind('<Escape>', lambda e: self.reset_view())
        self.root.bind('<F11>', lambda e: self.fit_to_window())
        self.root.bind('<plus>', lambda e: self._adjust_vertex_count(1))
        self.root.bind('<minus>', lambda e: self._adjust_vertex_count(-1))

    def open_image(self, filename=None):
        # Reorder file types to prioritize formats best for color analysis
        filetypes = [
            ('Recommended for Color Analysis', '*.tif *.png'),
            ('16-bit TIFF (Best)', '*.tif *.tiff'),
            ('PNG (Lossless)', '*.png'),
            ('All Image files', '*.tif *.tiff *.png *.jpg *.jpeg'),
            ('JPEG (Not Recommended)', '*.jpg *.jpeg')
        ]
        
        # Use provided filename, otherwise ask user
        if not filename:
            from utils.user_preferences import get_preferences_manager
            prefs_manager = get_preferences_manager()
            
            # Get the last used directory for opening files
            initial_dir = prefs_manager.get_last_open_directory()
            
            filename = filedialog.askopenfilename(
                title="Open Image", 
                filetypes=filetypes,
                initialdir=initial_dir
            )
            
            # Save the directory for next time if a file was selected
            if filename:
                prefs_manager.set_last_open_directory(filename)

        if filename:
            try:
                image, metadata = load_image(filename)
                self.canvas.load_image(image)
                self.current_file = filename
                self.current_image_metadata = metadata  # Store metadata for later use
                self.control_panel.enable_controls(True)
                base_filename = os.path.basename(filename)
                self.root.title(f"StampZ - {base_filename}")
                self.control_panel.update_current_filename(filename)
                
                # Show format information to user
                self._show_format_info(filename, metadata)
                
            except ImageLoadError as e:
                messagebox.showerror("Error", str(e))
    
    def _show_format_info(self, filename, metadata):
        """Show format information to the user based on loaded image metadata."""
        try:
            format_info = metadata.get('format_info', 'Unknown format')
            precision_preserved = metadata.get('precision_preserved', False)
            
            # Only show informational dialogs for significant format situations
            if precision_preserved:
                # 16-bit TIFF loaded successfully - brief positive confirmation
                print(f"✅ Loaded 16-bit TIFF with full precision: {os.path.basename(filename)}")
            elif '16-bit support' in format_info:
                # Could be 16-bit but tifffile not available - show warning
                response = messagebox.askyesno(
                    "16-bit TIFF Detected", 
                    f"This appears to be a 16-bit TIFF file, but it's being loaded as 8-bit.\n\n"
                    f"For maximum color accuracy, install the 'tifffile' library:\n"
                    f"pip install tifffile\n\n"
                    f"Would you like to continue with 8-bit loading?"
                )
                if not response:
                    # User chose not to continue, could implement auto-install here
                    pass
            elif 'compressed' in format_info.lower() or 'jpeg' in format_info.lower():
                # JPEG format - show brief warning about compression
                if 'first_jpeg_warning' not in self.__dict__:
                    messagebox.showinfo(
                        "JPEG Format Notice", 
                        f"JPEG format detected: {os.path.basename(filename)}\n\n"
                        f"Note: JPEG uses lossy compression which may affect color analysis precision.\n"
                        f"For best results, use TIFF or PNG formats.\n\n"
                        f"This notice will only appear once per session."
                    )
                    self.first_jpeg_warning = True
            
            # Always log the format info for debugging
            logger.info(f"Loaded {os.path.basename(filename)}: {format_info}")
            
        except Exception as e:
            logger.warning(f"Error showing format info: {e}")
    
    def _check_dependencies(self):
        """Check optional dependencies and show guidance if needed."""
        try:
            from utils.dependency_checker import DependencyChecker
            checker = DependencyChecker()
            
            # Only show dialog if important dependencies are missing
            if checker.should_show_dependency_dialog():
                self._show_dependency_dialog(checker)
                
        except Exception as e:
            logger.warning(f"Error checking dependencies: {e}")
    
    def _show_dependency_dialog(self, checker):
        """Show dependency status dialog to user."""
        try:
            from tkinter import Toplevel, Text, Scrollbar, Button, Frame, Label
            
            status = checker.get_dependency_status_summary()
            
            # Create dialog
            dialog = Toplevel(self.root)
            dialog.title("Optional Dependencies")
            dialog.geometry("700x500")
            dialog.resizable(True, True)
            
            # Center dialog
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Position dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            
            # Title
            title_label = Label(dialog, 
                               text=f"Optional Dependencies ({status['available_count']}/{status['total_dependencies']} available)",
                               font=("Arial", 14, "bold"))
            title_label.pack(pady=10)
            
            # Main content frame
            content_frame = Frame(dialog)
            content_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Status text area
            text_frame = Frame(content_frame)
            text_frame.pack(fill="both", expand=True)
            
            text_area = Text(text_frame, wrap="word", font=("Courier", 10))
            scrollbar = Scrollbar(text_frame, orient="vertical", command=text_area.yview)
            text_area.configure(yscrollcommand=scrollbar.set)
            
            text_area.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Insert dependency report
            report = checker.format_dependency_report()
            text_area.insert("1.0", report)
            text_area.configure(state="disabled")
            
            # Button frame
            button_frame = Frame(dialog)
            button_frame.pack(fill="x", padx=20, pady=10)
            
            def copy_install_commands():
                """Copy installation commands to clipboard."""
                try:
                    commands = "\n".join([dep.installation_command for dep in checker.get_missing_dependencies()])
                    dialog.clipboard_clear()
                    dialog.clipboard_append(commands)
                    messagebox.showinfo("Copied", "Installation commands copied to clipboard!")
                except Exception as e:
                    messagebox.showerror("Copy Error", f"Failed to copy commands: {e}")
            
            def save_install_script():
                """Save installation script to file."""
                try:
                    from tkinter import filedialog
                    
                    script_path = filedialog.asksaveasfilename(
                        title="Save Installation Script",
                        defaultextension=".sh",
                        filetypes=[
                            ('Shell Script', '*.sh'),
                            ('Text files', '*.txt'),
                            ('All files', '*.*')
                        ],
                        initialfile="install_stampz_deps.sh"
                    )
                    
                    if script_path:
                        script_content = checker.get_installation_script()
                        with open(script_path, 'w') as f:
                            f.write(script_content)
                        messagebox.showinfo("Script Saved", 
                                           f"Installation script saved to:\n{script_path}\n\n"
                                           f"Make it executable with:\nchmod +x {script_path}")
                        
                except Exception as e:
                    messagebox.showerror("Save Error", f"Failed to save script: {e}")
            
            # Add buttons
            if checker.get_missing_dependencies():
                Button(button_frame, text="Copy Install Commands", 
                      command=copy_install_commands).pack(side="left", padx=5)
                Button(button_frame, text="Save Install Script", 
                      command=save_install_script).pack(side="left", padx=5)
            
            Button(button_frame, text="Continue", 
                  command=dialog.destroy).pack(side="right", padx=5)
            
            # Initial focus
            text_area.focus_set()
            
        except Exception as e:
            logger.error(f"Error showing dependency dialog: {e}")
            # Fallback to console output
            print(checker.format_dependency_report())

    def save_image(self):
        if not self.canvas.original_image:
            messagebox.showwarning("No Image", "Please open an image before saving.")
            return
        try:
            _ = self.canvas.get_cropped_image()
        except ValueError as e:
            messagebox.showwarning("Invalid Selection", str(e))
            return
        try:
            cropped = self.canvas.get_cropped_image()
            panel_options = self.control_panel.get_save_options()
            save_manager = SaveManager()
            
            # Only show formats suitable for color analysis
            filetypes = [
                ('Recommended for Analysis', '*.tif *.png'),
                ('16-bit TIFF (Best Quality)', '*.tif *.tiff'),
                ('PNG (Lossless)', '*.png'),
                ('All Supported files', '*.tif *.tiff *.png')
            ]
            
            # Set default extension based on panel selection
            if panel_options.format == SaveFormat.PNG:
                default_ext = '.png'
            else:  # TIFF (default and best choice for color analysis)
                default_ext = '.tif'

            filename_manager = FilenameManager()
            suggested_name = filename_manager.generate_cropped_filename(
                original_file=self.current_file,
                cropped_image=cropped,
                extension=default_ext,
                use_dimensions=True
            )

            from utils.user_preferences import get_preferences_manager
            prefs_manager = get_preferences_manager()
            
            # Get the last used directory for saving files
            initial_dir = prefs_manager.get_last_save_directory()
            
            filepath = filedialog.asksaveasfilename(
                title="Save Cropped Image",
                defaultextension=default_ext,
                initialfile=suggested_name,
                filetypes=filetypes,
                initialdir=initial_dir
            )
            
            # Save the directory for next time if a file was selected
            if filepath:
                prefs_manager.set_last_save_directory(filepath)

            if filepath:
                ext = os.path.splitext(filepath)[1].lower()
                if ext in ['.jpg', '.jpeg']:
                    # JPEG is not supported for saving - show error and suggest alternatives
                    messagebox.showerror(
                        "JPEG Format Not Supported for Saving",
                        "⚠️  JPEG format is not supported for saving in this application.\n\n"
                        "JPEG uses lossy compression which reduces color analysis accuracy.\n\n"
                        "Please choose a lossless format:\n"
                        "• .tif extension (16-bit support, best for analysis)\n"
                        "• .png extension (lossless compression)\n\n"
                        "Note: You can still open JPEG files for analysis."
                    )
                    return  # Cancel save operation
                elif ext in ['.tif', '.tiff']:
                    selected_format = SaveFormat.TIFF
                elif ext == '.png':
                    selected_format = SaveFormat.PNG
                else:
                    selected_format = panel_options.format
                    base_name = os.path.splitext(filepath)[0]
                    filepath = f"{base_name}{SaveFormat.get_extension(selected_format)}"

                if selected_format != panel_options.format:
                    panel_options = SaveOptions(
                        format=selected_format,
                        jpeg_quality=95,  # Not used for TIFF/PNG but kept for compatibility
                        optimize=True
                    )

                save_manager.save_image(cropped, filepath, panel_options)
                self.recent_files.add_file(filepath)

                replace_response = messagebox.askyesno(
                    "Replace Original?", 
                    f"Cropped image saved successfully!\n\n"
                    f"Would you like to replace the original image with the cropped version?\n\n"
                    f"This will load the cropped image for further editing."
                )

                if replace_response:
                    try:
                        new_image, new_metadata = load_image(filepath)
                        self.canvas.load_image(new_image)
                        self.current_file = filepath
                        self.current_image_metadata = new_metadata
                        base_filename = os.path.basename(filepath)
                        self.root.title(f"StampZ - {base_filename}")
                        self.control_panel.update_current_filename(filepath)
                    except ImageLoadError as e:
                        messagebox.showerror("Error", f"Failed to load cropped image: {str(e)}")

        except (ImageSaveError, OSError) as e:
            messagebox.showerror("Save Error", str(e))

    def reset_view(self):
        if self.canvas.original_image:
            self.canvas.reset_view()

    def fit_to_window(self):
        if self.canvas and self.canvas.original_image:
            self.canvas.fit_to_window()

    def quit_app(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            # Clean up any temporary coordinate data
            try:
                from utils.coordinate_db import CoordinateDB
                db = CoordinateDB()
                db.cleanup_temporary_data()
            except Exception as e:
                print(f"Warning: Failed to clean up temporary data: {e}")
            
            self.root.quit()
            self.root.destroy()

    def _handle_vertex_count_change(self, count: int):
        if self.canvas:
            self.canvas.set_max_vertices(count)
            self.control_panel.vertex_count.set(count)

    def show_about(self):
        try:
            from __init__ import __version__, __app_name__, __description__
        except ImportError:
            __version__ = "2.0.3"
            __app_name__ = "StampZ_II"
            __description__ = "Image analysis and color analysis tool"
        
        messagebox.showinfo(
            f"About {__app_name__}",
            f"{__app_name__} v{__version__}\n\n"
            f"{__description__}\n\n"
            "Features:\n"
            "• Image cropping with polygon selection\n"
            "• Color analysis and measurement\n"
            "• Compare mode for color averaging\n"
            "• Export to ODS, XLSX, and CSV formats\n"
            "• Color library management\n"
            "• Spectral analysis tools\n\n"
            "Built for precision philatelic analysis."
        )

    def _adjust_vertex_count(self, delta: int):
        current = self.control_panel.vertex_count.get()
        new_count = current + delta
        if 3 <= new_count <= 8:
            self._handle_vertex_count_change(new_count)

    def _handle_transparency_change(self, value: int):
        if self.canvas:
            self.canvas.set_mask_alpha(value)

    def _handle_tool_mode_change(self, mode: str):
        if self.canvas:
            if mode == "view":
                self.canvas.set_tool_mode(ToolMode.VIEW)
                self.canvas.configure(cursor='fleur')
            elif mode == "crop":
                self.canvas.set_tool_mode(ToolMode.CROP)
                self.canvas.configure(cursor='crosshair')
            elif mode == "coord":
                self.canvas.set_tool_mode(ToolMode.COORD)
                self.canvas.configure(cursor='crosshair')
            elif mode == "straighten":
                self.canvas.set_tool_mode(ToolMode.STRAIGHTENING)
                self.canvas.configure(cursor='crosshair')

    def _handle_ruler_toggle(self, show: bool):
        if self.canvas:
            self.canvas.ruler_manager.toggle_visibility(show)
            self.canvas.update_display()

    def _handle_grid_toggle(self, show: bool):
        if self.canvas:
            self.canvas.ruler_manager.toggle_grid(show)
            self.canvas.update_display()

    def _handle_shape_type_change(self, shape_type: ShapeType):
        if self.canvas:
            self.canvas.set_shape_type(shape_type)

    def clear_image(self):
        """Clear the current image and reset the application to its opening state."""
        if self.canvas:
            # Clear canvas and reset image
            self.canvas.clear_image()  # Use canvas's clear method
            self.current_file = None
            self.canvas.configure(width=800, height=600)  # Reset to default size
            
            # Clear all sample markers and reset sample window state
            self._clear_samples(skip_confirmation=True, reset_all=True)  # Use existing method to clear samples
            
            # Reset window title
            self.root.title("StampZ_II")
            
            # Reset control panel state
            if hasattr(self.control_panel, 'sample_set_name'):
                self.control_panel.sample_set_name.set('')
            if hasattr(self.control_panel, 'analysis_name'):
                self.control_panel.analysis_name.set('')
            
            # Reset all sample controls to defaults
            if hasattr(self.control_panel, 'sample_controls'):
                for control in self.control_panel.sample_controls:
                    control['shape'].set('rectangle')
                    control['width'].set('20')
                    control['height'].set('20')
                    control['anchor'].set('center')
            
            # Reset mode to template if in sample mode
            if hasattr(self.control_panel, 'sample_mode'):
                self.control_panel.sample_mode.set('template')
                if hasattr(self.control_panel, '_set_template_mode_ui'):
                    self.control_panel._set_template_mode_ui()
            
            # Update display
            self.canvas.update()

    def initialize_modes(self) -> None:
        self._handle_tool_mode_change("view")

    def _handle_line_color_change(self, color: str):
        if self.canvas:
            self.canvas.set_line_color(color)

    def _update_crop_dimensions(self, width: int, height: int):
        if self.control_panel:
            self.control_panel.update_crop_dimensions(width, height)

    def _save_sample_set(self):
        """Save the current coordinate sample set."""
        print("DEBUG: _save_sample_set() called in main.py")
        try:
            # Check if we have sample markers to save
            print(f"DEBUG: Checking for coord markers: hasattr={hasattr(self.canvas, '_coord_markers')}")
            if hasattr(self.canvas, '_coord_markers'):
                print(f"DEBUG: Number of coord markers: {len(self.canvas._coord_markers)}")
            
            if not hasattr(self.canvas, '_coord_markers') or not self.canvas._coord_markers:
                print("DEBUG: No sample markers found")
                messagebox.showwarning(
                    "No Samples",
                    "No sample points found. Please place some sample markers first."
                )
                return

            if not self.canvas.original_image:
                print("DEBUG: No original image found")
                messagebox.showwarning(
                    "No Image",
                    "Please open an image before saving samples."
                )
                return

            # Get sample set name
            sample_set_name = self.control_panel.sample_set_name.get().strip()
            print(f"DEBUG: Sample set name: '{sample_set_name}'")
            if not sample_set_name:
                print("DEBUG: No sample set name provided")
                messagebox.showwarning(
                    "No Name",
                    "Please enter a name for the sample set in the Template field."
                )
                return

            # Create coordinate points from markers
            from utils.coordinate_db import CoordinateDB, CoordinatePoint, SampleAreaType
            print("DEBUG: About to create coordinates from markers")
            coordinates = []
            for marker in self.canvas._coord_markers:
                if marker.get('is_preview', False):
                    continue

                # Get marker data
                image_x, image_y = marker['image_pos']
                sample_type = SampleAreaType.CIRCLE if marker['sample_type'] == 'circle' else SampleAreaType.RECTANGLE
                width = float(marker['sample_width'])
                height = float(marker['sample_height'])
                anchor = marker['anchor']

                # Create coordinate point
                coord = CoordinatePoint(
                    x=image_x,
                    y=image_y,
                    sample_type=sample_type,
                    sample_size=(width, height),
                    anchor_position=anchor
                )
                coordinates.append(coord)
                print(f"DEBUG: Added coordinate: x={image_x}, y={image_y}, type={sample_type}, size=({width}, {height})")

            print(f"DEBUG: Created {len(coordinates)} coordinates, about to save to database")
            # Save coordinates to database
            db = CoordinateDB()
            print("DEBUG: Created CoordinateDB instance")
            success, standardized_name = db.save_coordinate_set(
                name=sample_set_name,
                image_path=self.current_file,
                coordinates=coordinates
            )
            print(f"DEBUG: Database save result: success={success}, standardized_name={standardized_name}")

            if success:
                # Update the template name in control panel to the standardized name
                self.control_panel.sample_set_name.set(standardized_name)
                
                # Protect the newly saved template
                print(f"DEBUG: Protecting newly saved template '{standardized_name}'")
                self.control_panel.template_protection.protect_template(standardized_name, coordinates)
                
                messagebox.showinfo(
                    "Success",
                    f"Successfully saved {len(coordinates)} sample points to set '{standardized_name}'.\n\n"
                    f"Template is now protected from accidental modification."
                )
            else:
                messagebox.showerror(
                    "Save Error",
                    f"Failed to save sample set '{sample_set_name}'. Please try again."
                )

        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"Failed to save sample set:\n\n{str(e)}"
            )
    
    def _update_sample_set(self):
        """Update existing template with current changes (positions and settings)."""
        print("DEBUG: _update_sample_set() called in main.py")
        try:
            # Check if we have sample markers to save
            if not hasattr(self.canvas, '_coord_markers') or not self.canvas._coord_markers:
                print("DEBUG: No sample markers found")
                messagebox.showwarning(
                    "No Samples",
                    "No sample points found. Please place some sample markers first."
                )
                return

            if not self.canvas.original_image:
                print("DEBUG: No original image found")
                messagebox.showwarning(
                    "No Image",
                    "Please open an image before updating template."
                )
                return

            # Get template name
            template_name = self.control_panel.sample_set_name.get().strip()
            print(f"DEBUG: Template name for update: '{template_name}'")
            if not template_name:
                print("DEBUG: No template name provided")
                messagebox.showwarning(
                    "No Template Name",
                    "Please enter or load a template name before updating."
                )
                return
            
            # Don't allow updating MAN_MODE
            if template_name == "MAN_MODE":
                messagebox.showwarning(
                    "Cannot Update Manual Mode",
                    "Manual mode samples cannot be updated. Use Save to create a new template."
                )
                return

            # Create coordinate points from current markers AND current control panel settings
            from utils.coordinate_db import CoordinateDB, CoordinatePoint, SampleAreaType
            print("DEBUG: About to create coordinates from current markers and control panel settings")
            coordinates = []
            non_preview_markers = [m for m in self.canvas._coord_markers if not m.get('is_preview', False)]
            
            for i, marker in enumerate(non_preview_markers):
                # Get marker position (this includes any position changes from fine adjustments)
                image_x, image_y = marker['image_pos']
                
                # Get current sample parameters from control panel (may have been modified)
                if i < len(self.control_panel.sample_controls):
                    control = self.control_panel.sample_controls[i]
                    sample_shape = control['shape'].get()
                    width = float(control['width'].get())
                    height = float(control['height'].get())
                    anchor = control['anchor'].get()
                    print(f"DEBUG: Using control panel settings for sample {i+1}: {sample_shape} {width}x{height} {anchor}")
                else:
                    # Fallback to marker data if no control panel data available
                    sample_shape = marker['sample_type']
                    width = float(marker['sample_width'])
                    height = float(marker['sample_height'])
                    anchor = marker['anchor']
                    print(f"DEBUG: Using marker settings for sample {i+1}: {sample_shape} {width}x{height} {anchor}")
                
                sample_type = SampleAreaType.CIRCLE if sample_shape == 'circle' else SampleAreaType.RECTANGLE

                # Create coordinate point with current settings
                coord = CoordinatePoint(
                    x=image_x,
                    y=image_y,
                    sample_type=sample_type,
                    sample_size=(width, height),
                    anchor_position=anchor
                )
                coordinates.append(coord)
                print(f"DEBUG: Added coordinate for update: x={image_x}, y={image_y}, type={sample_type}, size=({width}, {height}), anchor={anchor}")

            print(f"DEBUG: Created {len(coordinates)} coordinates for template update")
            
            # Update coordinates in database (existing save_coordinate_set handles updates)
            db = CoordinateDB()
            success, standardized_name = db.save_coordinate_set(
                name=template_name,
                image_path=self.current_file,
                coordinates=coordinates
            )
            print(f"DEBUG: Database update result: success={success}, standardized_name={standardized_name}")

            if success:
                # Update the template protection to reflect the new state
                print(f"DEBUG: Updating template protection for '{standardized_name}'")
                self.control_panel.template_protection.protect_template(standardized_name, coordinates)
                
                # Refresh the visual display to show the updated parameters
                print(f"DEBUG: Refreshing visual display after template update")
                self._refresh_sample_markers_display(coordinates)
                
                messagebox.showinfo(
                    "Template Updated",
                    f"Successfully updated template '{standardized_name}' with {len(coordinates)} sample points.\n\n"
                    "All changes including marker positions and settings have been saved and are now visible."
                )
            else:
                messagebox.showerror(
                    "Update Error",
                    f"Failed to update template '{template_name}': {standardized_name}"
                )

        except Exception as e:
            print(f"DEBUG: Error in _update_sample_set: {e}")
            messagebox.showerror(
                "Update Error",
                f"Failed to update template:\n\n{str(e)}"
            )

    def _apply_straightening(self):
        if not self.canvas.original_image:
            messagebox.showwarning("No Image", "Please open an image before straightening.")
            return

        if not self.straightening_tool.can_straighten():
            messagebox.showwarning("Insufficient Points", "Please place at least 2 reference points.")
            return

        try:
            straightened_image, angle = self.straightening_tool.straighten_image(
                self.canvas.original_image,
                background_color='white'
            )
            self.canvas.load_image(straightened_image)
            self.straightening_tool.clear_points()
            self.control_panel.update_straightening_status(0)
        except Exception as e:
            messagebox.showerror("Straightening Error", f"Failed to straighten image: {str(e)}")

    def _view_spreadsheet(self):
        """Open spreadsheet view of color analysis data.
        
        Logic:
        1. If there's a current image with analysis data -> show that specific analysis
        2. If there's no current image/analysis -> show dialog to choose which data to view
        """
        try:
            # Get sample set name from control panel
            sample_set_name = self.control_panel.sample_set_name.get().strip()
            
            # Check if we have a current image with analysis data
            has_current_analysis = False
            if sample_set_name and self.current_file:
                # Check if there's analysis data for the current sample set
                from utils.ods_exporter import ODSExporter
                test_exporter = ODSExporter(sample_set_name=sample_set_name)
                test_measurements = test_exporter.get_color_measurements()
                has_current_analysis = bool(test_measurements)
            
            if has_current_analysis:
                # Case 1: We have current analysis data, show it directly
                print(f"DEBUG: Showing analysis for current sample set: {sample_set_name}")
                exporter = ODSExporter(sample_set_name=sample_set_name)
                success = exporter.view_latest_spreadsheet()
                
                if not success:
                    messagebox.showerror(
                        "View Error",
                        "Failed to open spreadsheet. Please check that LibreOffice Calc is installed."
                    )
            else:
                # Case 2: No current analysis, show selection dialog
                print("DEBUG: No current analysis found, showing selection dialog")
                self._show_data_selection_dialog()
            
        except ImportError as e:
            messagebox.showerror(
                "Missing Dependency",
                f"The spreadsheet viewing feature requires additional libraries:\n\n{str(e)}"
            )
        except Exception as e:
            messagebox.showerror(
                "View Error",
                f"Failed to open spreadsheet view:\n\n{str(e)}"
            )
    
    def _show_data_selection_dialog(self):
        """Show dialog to select which spreadsheet data to view."""
        try:
            from tkinter import Toplevel, Listbox, Button, Frame, Label, Scrollbar
            from utils.color_analysis_db import ColorAnalysisDB
            from utils.path_utils import get_color_analysis_dir
            
            # Get available sample sets
            color_data_dir = get_color_analysis_dir()
            if not os.path.exists(color_data_dir):
                messagebox.showinfo(
                    "No Data",
                    "No color analysis data found.\n\n"
                    "Please run color analysis first using the Sample tool."
                )
                return
            
            available_sets = ColorAnalysisDB.get_all_sample_set_databases(color_data_dir)
            if not available_sets:
                messagebox.showinfo(
                    "No Data",
                    "No color analysis data found.\n\n"
                    "Please run color analysis first using the Sample tool."
                )
                return
            
            # Create dialog
            dialog = Toplevel(self.root)
            dialog.title("Select Data to View")
            
            dialog_width = 450
            dialog_height = 350
            
            # Center the dialog
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
            
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.focus_force()
            
            # Header
            Label(dialog, text="Choose which data to view:", font=("Arial", 12, "bold")).pack(pady=10)
            
            # Sample sets listbox frame
            sets_frame = Frame(dialog)
            sets_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            
            Label(sets_frame, text="Available Sample Sets:", font=("Arial", 10)).pack(anchor="w")
            
            # Listbox with scrollbar
            listbox_frame = Frame(sets_frame)
            listbox_frame.pack(fill="both", expand=True, pady=5)
            
            sets_listbox = Listbox(listbox_frame, font=("Arial", 13, "bold"))
            sets_listbox.pack(side="left", fill="both", expand=True)
            
            scrollbar = Scrollbar(listbox_frame)
            scrollbar.pack(side="right", fill="y")
            sets_listbox.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=sets_listbox.yview)
            
            # Populate listbox with sample sets
            for sample_set in available_sets:
                sets_listbox.insert("end", sample_set)
            
            # Select first item by default
            if available_sets:
                sets_listbox.selection_set(0)
            
            # Variables to store selection
            selected_option = None
            selected_sample_set = None
            
            def on_view_selected():
                nonlocal selected_option, selected_sample_set
                selection = sets_listbox.curselection()
                if not selection:
                    messagebox.showwarning("No Selection", "Please select a sample set to view")
                    return
                
                selected_option = "specific"
                selected_sample_set = available_sets[selection[0]]
                dialog.quit()
                dialog.destroy()
            
            def on_view_all():
                nonlocal selected_option
                selected_option = "all"
                dialog.quit()
                dialog.destroy()
            
            def on_export_plot3d():
                nonlocal selected_option, selected_sample_set
                selection = sets_listbox.curselection()
                if not selection:
                    messagebox.showwarning("No Selection", "Please select a sample set to export for Plot_3D")
                    return
                
                selected_option = "plot3d"
                selected_sample_set = available_sets[selection[0]]
                dialog.quit()
                dialog.destroy()
            
            def on_cancel():
                nonlocal selected_option
                selected_option = None
                dialog.quit()
                dialog.destroy()
            
            # Buttons frame
            buttons_frame = Frame(dialog)
            buttons_frame.pack(pady=10)
            
            Button(buttons_frame, text="View Selected Set", command=on_view_selected, width=15).pack(side="left", padx=3)
            Button(buttons_frame, text="View All Data", command=on_view_all, width=12).pack(side="left", padx=3)
            Button(buttons_frame, text="Export for Plot_3D", command=on_export_plot3d, width=15).pack(side="left", padx=3)
            Button(buttons_frame, text="Cancel", command=on_cancel, width=8).pack(side="left", padx=3)
            
            # Keyboard bindings
            dialog.bind('<Return>', lambda e: on_view_selected())
            dialog.bind('<Escape>', lambda e: on_cancel())
            sets_listbox.bind("<Double-Button-1>", lambda e: on_view_selected())
            
            # Focus on listbox
            sets_listbox.focus_set()
            
            # Wait for dialog result
            dialog.mainloop()
            
            # Process the result
            if selected_option == "specific" and selected_sample_set:
                print(f"DEBUG: User selected specific sample set: {selected_sample_set}")
                from utils.ods_exporter import ODSExporter
                
                # Check if this is an averages database
                if selected_sample_set.endswith('_averages'):
                    # For averaged measurements, extract the base name and use the specialized method
                    base_name = selected_sample_set[:-9]  # Remove '_averages' suffix
                    print(f"DEBUG: Detected averages database, base name: {base_name}")
                    exporter = ODSExporter(sample_set_name=base_name)
                    success = exporter.view_averaged_measurements_spreadsheet()
                else:
                    # For regular individual measurements
                    exporter = ODSExporter(sample_set_name=selected_sample_set)
                    success = exporter.view_latest_spreadsheet()
                
                if not success:
                    messagebox.showerror(
                        "View Error",
                        "Failed to open spreadsheet. Please check that LibreOffice Calc is installed."
                    )
            elif selected_option == "all":
                print("DEBUG: User selected to view all data combined")
                from utils.ods_exporter import ODSExporter
                exporter = ODSExporter(sample_set_name=None)  # None means all data
                success = exporter.view_latest_spreadsheet()
                
                if not success:
                    messagebox.showerror(
                        "View Error",
                        "Failed to open spreadsheet. Please check that LibreOffice Calc is installed."
                    )
            elif selected_option == "plot3d" and selected_sample_set:
                print(f"DEBUG: User selected Plot_3D export for sample set: {selected_sample_set}")
                from utils.direct_plot3d_exporter import DirectPlot3DExporter
                
                # Handle averages database - use full name for clarity
                actual_sample_set = selected_sample_set
                display_name = selected_sample_set  # Use full name including _averages for clarity
                
                if selected_sample_set.endswith('_averages'):
                    print(f"DEBUG: Detected averages database: {actual_sample_set}")
                    print(f"DEBUG: Display name: {display_name}")
                
                exporter = DirectPlot3DExporter()
                created_files = exporter.export_to_plot3d(actual_sample_set)
                
                if created_files:
                    # Show success message with all created files
                    files_list = "\n".join([f"  - {os.path.basename(f)}" for f in created_files])
                    messagebox.showinfo(
                        "Export Complete",
                        f"Successfully exported Plot_3D data for sample set '{display_name}'.\n\n"
                        f"Created {len(created_files)} file(s):\n{files_list}\n\n"
                        f"These files can be loaded in Plot_3D for 3D color space analysis."
                    )
                else:
                    messagebox.showerror(
                        "Export Error",
                        f"Failed to export Plot_3D data for sample set '{display_name}'.\n\n"
                        f"No files were created. Please check the sample set has valid data."
                    )
            # If selected_option is None, user cancelled - do nothing
            
        except Exception as e:
            messagebox.showerror(
                "Dialog Error",
                f"Failed to show data selection dialog:\n\n{str(e)}"
            )

    def _clear_samples(self, skip_confirmation=False, reset_all=False):
        """Clear all sample markers and reset sample-related UI elements.
        
        Args:
            skip_confirmation (bool): If True, skips the confirmation dialog
            reset_all (bool): If True, resets all UI elements to default state
        """
        if not hasattr(self.canvas, '_coord_markers'):
            self.canvas._coord_markers = []
        
        # Ask for confirmation if there are sample markers and confirmation is not skipped
        if self.canvas._coord_markers and not skip_confirmation:
            result = messagebox.askyesno(
                "Clear All Samples",
                f"This will clear all {len(self.canvas._coord_markers)} sample markers.\n\n"
                "Are you sure you want to continue?"
            )
            if not result:
                return
        
        try:
            # Delete visual markers from canvas
            for marker in self.canvas._coord_markers:
                tag = marker.get('tag')
                if tag:
                    self.canvas.delete(tag)
            
            # Clear the markers list
            self.canvas._coord_markers.clear()
            
            # Reset control UI to defaults
            if hasattr(self.control_panel, 'sample_controls'):
                for control in self.control_panel.sample_controls:
                    control['shape'].set('circle')
                    control['width'].set('10')
                    control['height'].set('10')
                    control['anchor'].set('center')
            
            # Clear template and analysis names
            if hasattr(self.control_panel, 'sample_set_name'):
                self.control_panel.sample_set_name.set("")
            if hasattr(self.control_panel, 'analysis_name'):
                self.control_panel.analysis_name.set("")
            
            # Reset offset values and status
            if hasattr(self.control_panel, 'global_x_offset'):
                self.control_panel.global_x_offset.set(0)
            if hasattr(self.control_panel, 'global_y_offset'):
                self.control_panel.global_y_offset.set(0)
            if hasattr(self.control_panel, 'individual_x_offset'):
                self.control_panel.individual_x_offset.set(0)
            if hasattr(self.control_panel, 'individual_y_offset'):
                self.control_panel.individual_y_offset.set(0)
            if hasattr(self.control_panel, 'offset_status'):
                self.control_panel.offset_status.set("No offsets applied")
            
            # If resetting all, also reset additional UI elements
            if reset_all:
                if hasattr(self.control_panel, 'sample_mode'):
                    self.control_panel.sample_mode.set("template")
                    # This will trigger the UI update for template mode
                    if hasattr(self.control_panel, '_set_template_mode_ui'):
                        self.control_panel._set_template_mode_ui()
                
                # Reset any manual mode settings if they exist
                if hasattr(self.control_panel, 'manual_shape'):
                    self.control_panel.manual_shape.set('circle')
                if hasattr(self.control_panel, 'manual_width'):
                    self.control_panel.manual_width.set('10')
                if hasattr(self.control_panel, 'manual_height'):
                    self.control_panel.manual_height.set('10')
                if hasattr(self.control_panel, 'manual_anchor'):
                    self.control_panel.manual_anchor.set('center')
            
            # Force canvas update
            self.canvas.update_display()
            
        except Exception as e:
            messagebox.showerror(
                "Clear Error", 
                f"Failed to clear sample markers:\n\n{str(e)}"
            )

    def _clear_straightening_points(self):
        self.straightening_tool.clear_points()
        self.control_panel.update_straightening_status(0)
        if self.canvas:
            self.canvas.delete('straightening_point')

    def _load_sample_set(self):
        from utils.coordinate_db import CoordinateDB
        from tkinter import Toplevel, Listbox, Button, Frame, Label, Scrollbar
        
        canvas = self.canvas
        if not canvas:
            messagebox.showerror("Error", "Cannot access canvas for loading coordinates")
            return
        
        db = CoordinateDB()
        all_sets = db.get_all_set_names()
        
        if not all_sets:
            messagebox.showinfo("No Sets", "No coordinate sets found in database")
            return
        
        dialog = Toplevel(self.root)
        dialog.title("Load Template")
        
        dialog_width = 400
        dialog_height = 300
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = screen_width - dialog_width - 50
        y = (screen_height - dialog_height) // 2
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        dialog.resizable(False, False)
        
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()
        
        Label(dialog, text="Select a coordinate set to load:", font=("Arial", 12)).pack(pady=10)
        
        listbox_frame = Frame(dialog)
        listbox_frame.pack(fill="both", expand=True, padx=20)
        
        listbox = Listbox(listbox_frame, font=("Arial", 14))
        listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)
        
        for set_name in all_sets:
            listbox.insert("end", set_name)
        
        selected_set = None
        
        def on_load(event=None):
            nonlocal selected_set
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a coordinate set to load")
                return
            
            selected_set = all_sets[selection[0]]
            dialog.quit()
            dialog.destroy()
        
        def on_cancel(event=None):
            dialog.quit()
            dialog.destroy()
        
        button_frame = Frame(dialog)
        button_frame.pack(pady=10)
        
        load_button = Button(button_frame, text="Load", command=on_load, width=10)
        load_button.pack(side="left", padx=5)
        cancel_button = Button(button_frame, text="Cancel", command=on_cancel, width=10)
        cancel_button.pack(side="left", padx=5)
        
        dialog.bind('<Return>', on_load)
        dialog.bind('<Escape>', on_cancel)
        
        listbox.bind("<Double-Button-1>", on_load)
        
        listbox.focus_set()
        if listbox.size() > 0:
            listbox.selection_set(0)
        
        dialog.mainloop()
        
        if not selected_set:
            return
        
        coordinates = db.load_coordinate_set(selected_set)
        
        if not coordinates:
            messagebox.showerror("Error", f"Failed to load coordinate set '{selected_set}'")
            return
        
        if hasattr(canvas, '_coord_markers'):
            for marker in canvas._coord_markers:
                canvas.delete(marker.get('tag', 'unknown_tag'))
            canvas._coord_markers.clear()
        else:
            canvas._coord_markers = []
        
        from utils.coordinate_db import SampleAreaType
        for i, coord in enumerate(coordinates):
            canvas_x, canvas_y = canvas._image_to_screen_coords(coord.x, coord.y)
            
            sample_type = 'circle' if coord.sample_type == SampleAreaType.CIRCLE else 'rectangle'
            
            marker = {
                'index': i + 1,  # 1-based sample numbering
                'image_pos': (coord.x, coord.y),
                'canvas_pos': (canvas_x, canvas_y),
                'sample_type': sample_type,
                'sample_width': coord.sample_size[0],
                'sample_height': coord.sample_size[1],
                'anchor': coord.anchor_position,
                'is_preview': False
            }
            
            tag = f"coord_marker_{len(canvas._coord_markers)}"
            marker['tag'] = tag
            
            line_color = self.control_panel.get_line_color()
            if sample_type == 'circle':
                radius = coord.sample_size[0] / 2
                canvas.create_oval(
                    canvas_x - radius, canvas_y - radius,
                    canvas_x + radius, canvas_y + radius,
                    outline=line_color, width=2, tags=tag
                )
            else:
                half_w = coord.sample_size[0] / 2
                half_h = coord.sample_size[1] / 2
                canvas.create_rectangle(
                    canvas_x - half_w, canvas_y - half_h,
                    canvas_x + half_w, canvas_y + half_h,
                    outline=line_color, width=2, tags=tag
                )
            
            cross_size = 8
            canvas.create_line(
                canvas_x - cross_size, canvas_y,
                canvas_x + cross_size, canvas_y,
                fill=line_color, width=2, tags=tag
            )
            canvas.create_line(
                canvas_x, canvas_y - cross_size,
                canvas_x, canvas_y + cross_size,
                fill=line_color, width=2, tags=tag
            )
            
            canvas.create_text(
                canvas_x + 12, canvas_y - 12,
                text=str(i + 1),
                fill=line_color, font=("Arial", 10, "bold"),
                tags=tag
            )
            
            canvas._coord_markers.append(marker)
        
        self.control_panel.sample_set_name.set(selected_set)
        self.control_panel.update_sample_controls_from_coordinates(coordinates)

    def _apply_default_settings(self):
        if self.canvas:
            default_vertex_count = self.control_panel.vertex_count.get()
            self.canvas.set_max_vertices(default_vertex_count)
            default_transparency = self.control_panel.mask_transparency.get()
            self.canvas.set_mask_alpha(default_transparency)
            default_color = self.control_panel.line_color.get()
            self.canvas.set_line_color(default_color)

    def _analyze_colors(self):
        if not hasattr(self.canvas, '_coord_markers') or not self.canvas._coord_markers:
            messagebox.showwarning(
                "No Samples", 
                "No sample points found. Please place some sample markers using the Sample tool first."
            )
            return
        
        if not self.canvas.original_image:
            messagebox.showwarning(
                "No Image", 
                "Please open an image before analyzing colors."
            )
            return
        
        sample_set_name = self.control_panel.sample_set_name.get().strip()
        if not sample_set_name:
            messagebox.showwarning(
                "No Sample Set Name", 
                "Please enter a sample set name in the Template field before analyzing."
            )
            return
        
        try:
            from utils.color_analyzer import ColorAnalyzer
            # Create analyzer
            analyzer = ColorAnalyzer()
            
            if not self.current_file:
                messagebox.showerror("Error", "No image loaded. Please open an image first.")
                return
            
            actual_sample_set = sample_set_name
            if '_' in sample_set_name:
                parts = sample_set_name.split('_')
                if len(parts) >= 2:
                    potential_sample_set = '_'.join(parts[1:])
                    
                    try:
                        from utils.coordinate_db import CoordinateDB
                        coord_db = CoordinateDB()
                        available_sets = coord_db.get_all_set_names()
                        
                        if potential_sample_set in available_sets:
                            actual_sample_set = potential_sample_set
                    except:
                        pass
            
            print(f"DEBUG: About to call analyze_image_colors_from_canvas with:")
            print(f"  - image_path: {self.current_file}")
            print(f"  - sample_set_name: {actual_sample_set}")
            print(f"  - number of markers: {len(self.canvas._coord_markers)}")
            
            measurements = analyzer.analyze_image_colors_from_canvas(
                self.current_file, actual_sample_set, self.canvas._coord_markers
            )
            
            print(f"DEBUG: analyze_image_colors_from_canvas returned: {measurements is not None}")
            if measurements:
                print(f"DEBUG: Number of measurements: {len(measurements)}")
            
            if measurements:
                dialog = tk.Toplevel(self.root)
                dialog.title("Analysis Complete")
                
                dialog_width = 400
                dialog_height = 200
                
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                
                x = screen_width - dialog_width - 50
                y = (screen_height - dialog_height) // 2
                
                dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
                
                message = f"Successfully analyzed {len(measurements)} color samples from set '{actual_sample_set}'.\n\n"
                message += f"Color data has been saved to the database.\n\n"
                message += f"You can now view the spreadsheet or export the data."
                
                ttk.Label(dialog, text=message, wraplength=350, justify="left").pack(padx=20, pady=20)
                
                ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=10)
                
                dialog.transient(self.root)
                dialog.grab_set()
                
                self.root.wait_window(dialog)
            else:
                messagebox.showwarning(
                    "Analysis Failed", 
                    "No color samples could be analyzed. Please check your sample markers."
                )
                
        except Exception as e:
            import traceback
            messagebox.showerror(
                "Analysis Error", 
                f"Failed to analyze color samples:\n\n{str(e)}"
            )

    def export_color_data(self):
        try:
            current_sample_set = None
            if (hasattr(self, 'control_panel') and 
                hasattr(self.control_panel, 'sample_set_name') and 
                self.control_panel.sample_set_name.get().strip()):
                current_sample_set = self.control_panel.sample_set_name.get().strip()

            exporter = ODSExporter(sample_set_name=current_sample_set)
            measurements = exporter.get_color_measurements()

            if not measurements:
                if current_sample_set:
                    messagebox.showinfo(
                        "No Data", 
                        f"No color analysis data found for sample set '{current_sample_set}'.\n\n"
                        "Please run some color analysis first using the coordinate sampling tool."
                    )
                else:
                    messagebox.showinfo(
                        "No Data", 
                        "No color analysis data found in the database.\n\n"
                        "Please run some color analysis first using the coordinate sampling tool."
                    )
                return

            if current_sample_set:
                default_filename = f"{current_sample_set}_{datetime.now().strftime('%Y%m%d')}.ods"
            else:
                default_filename = f"stampz_color_data_{datetime.now().strftime('%Y%m%d')}.ods"

            filepath = filedialog.asksaveasfilename(
                title="Export Color Data",
                defaultextension=".ods",
                filetypes=[
                    ('OpenDocument Spreadsheet', '*.ods'),
                    ('All files', '*.*')
                ],
                initialfile=default_filename
            )

            if filepath:
                success = exporter.export_and_open(filepath)
                if success:
                    if current_sample_set:
                        messagebox.showinfo(
                            "Export Successful",
                            f"Successfully exported {len(measurements)} color measurements from sample set '{current_sample_set}' to:\n\n"
                            f"{os.path.basename(filepath)}\n\n"
                            f"The spreadsheet has been opened in LibreOffice Calc for analysis."
                        )
                    else:
                        messagebox.showinfo(
                            "Export Successful",
                            f"Successfully exported {len(measurements)} color measurements to:\n\n"
                            f"{os.path.basename(filepath)}\n\n"
                            f"The spreadsheet has been opened in LibreOffice Calc for analysis."
                        )
                else:
                    messagebox.showerror(
                        "Export Failed",
                        "Failed to export color data or open spreadsheet. Please check that LibreOffice Calc is installed."
                    )

        except ImportError:
            messagebox.showerror(
                "Missing Dependency",
                "The ODS export feature requires the 'odfpy' library.\n\n"
                "Please install it with: pip install odfpy==1.4.1"
            )
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                f"An error occurred during export:\n\n{str(e)}"
            )

    def open_color_library(self):
        try:
            from gui.color_library_manager import ColorLibraryManager
            library_manager = ColorLibraryManager(parent=self.root)
            library_manager.root.update()
        except ImportError as e:
            messagebox.showerror(
                "Missing Component",
                f"Color Library Manager not available:\n\n{str(e)}\n\n"
                "Please ensure all color library components are properly installed."
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to open Color Library Manager:\n\n{str(e)}"
            )

    def compare_sample_to_library(self):
        try:
            from gui.color_library_manager import ColorLibraryManager
            from utils.color_analyzer import ColorAnalyzer

            if not hasattr(self.canvas, '_coord_markers') or not self.canvas._coord_markers:
                messagebox.showwarning(
                    "No Samples",
                    "Please analyze some color samples first using the Sample tool."
                )
                return

            if not self.current_file:
                messagebox.showwarning(
                    "No Image",
                    "Please open an image before comparing colors."
                )
                return

            analyzer = ColorAnalyzer()
            sample_data = []
            non_preview_markers = [m for m in self.canvas._coord_markers if not m.get('is_preview', False)]

            for marker in non_preview_markers:
                try:
                    image_x, image_y = marker['image_pos']
                    sample_type = marker.get('sample_type', 'rectangle')
                    sample_width = float(marker.get('sample_width', 20))
                    sample_height = float(marker.get('sample_height', 20))

                    measurement = {
                        'position': (image_x, image_y),
                        'type': sample_type,
                        'size': (sample_width, sample_height),
                        'anchor': marker.get('anchor', 'center')
                    }
                    sample_data.append(measurement)
                except Exception as e:
                    continue

            try:
                library_manager = ColorLibraryManager(parent=self.root)
                if not library_manager.library:
                    library_manager.library = ColorLibrary('basic_colors')
                library_manager._create_comparison_tab()
                library_manager.comparison_manager.set_analyzed_data(
                    image_path=self.current_file,
                    sample_data=sample_data
                )
                library_manager.notebook.select(1)
                library_manager.root.update()
                library_manager.root.lift()
                library_manager.root.focus_force()
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to initialize comparison window: {str(e)}"
                )

        except ImportError as e:
            messagebox.showerror(
                "Missing Component",
                f"Color Library Manager not available:\n\n{str(e)}\n\n"
                "Please ensure all color library components are properly installed."
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to open Color Library Manager:\n\n{str(e)}"
            )

    def create_standard_libraries(self):
        try:
            from utils.color_library_integration import create_standard_philatelic_libraries

            result = messagebox.askyesno(
                "Create Standard Libraries",
                "This will create standard color libraries for philatelic analysis:\n\n"
                "• Basic Colors (primary, secondary, neutral colors)\n"
                "• Philatelic Colors (common stamp colors)\n\n"
                "If these libraries already exist, they will be updated.\n\n"
                "Do you want to continue?"
            )

            if result:
                progress_dialog = tk.Toplevel(self.root)
                progress_dialog.title("Creating Libraries")
                progress_dialog.geometry("300x100")
                progress_dialog.transient(self.root)
                progress_dialog.grab_set()

                progress_dialog.update_idletasks()
                x = (progress_dialog.winfo_screenwidth() // 2) - (progress_dialog.winfo_width() // 2)
                y = (progress_dialog.winfo_screenheight() // 2) - (progress_dialog.winfo_height() // 2)
                progress_dialog.geometry(f"+{x}+{y}")

                progress_label = ttk.Label(progress_dialog, text="Creating standard libraries...")
                progress_label.pack(expand=True)

                progress_dialog.update()

                created_libraries = create_standard_philatelic_libraries()

                progress_dialog.destroy()

                messagebox.showinfo(
                    "Libraries Created",
                    f"Successfully created standard libraries:\n\n"
                    f"• {created_libraries[0]}\n"
                    f"• {created_libraries[1]}\n\n"
                    f"You can now access these through the Color Library Manager."
                )

        except ImportError as e:
            messagebox.showerror(
                "Missing Component",
                f"Color library system not available:\n\n{str(e)}"
            )
        except Exception as e:
            messagebox.showerror(
                "Creation Error",
                f"Failed to create standard libraries:\n\n{str(e)}"
            )

    def export_with_library_matches(self, sample_set_name=None):
        try:
            from utils.color_library_integration import ColorLibraryIntegration

            if not sample_set_name:
                if (hasattr(self, 'control_panel') and 
                    hasattr(self.control_panel, 'sample_set_name') and 
                    self.control_panel.sample_set_name.get().strip()):
                    sample_set_name = self.control_panel.sample_set_name.get().strip()
                else:
                    messagebox.showwarning(
                        "No Sample Set",
                        "Please enter a sample set name in the control panel first."
                    )
                    return

            integration = ColorLibraryIntegration(['philatelic_colors', 'basic_colors'])

            default_filename = f"{sample_set_name}_with_library_matches_{datetime.now().strftime('%Y%m%d')}.ods"
            filepath = filedialog.asksaveasfilename(
                title="Export Analysis with Library Matches",
                defaultextension=".ods",
                filetypes=[
                    ('OpenDocument Spreadsheet', '*.ods'),
                    ('All files', '*.*')
                ],
                initialfile=default_filename
            )

            if filepath:
                workflow = integration.get_analysis_workflow_summary(sample_set_name, threshold=5.0)

                if workflow['status'] == 'analyzed':
                    messagebox.showinfo(
                        "Export Complete",
                        f"Would export analysis with library matches to:\n\n"
                        f"{os.path.basename(filepath)}\n\n"
                        f"This would include:\n"
                        f"• {workflow['summary']['total_samples']} color samples\n"
                        f"• Library matches with ΔE values\n"
                        f"• Match quality ratings\n"
                        f"• Complete analysis metadata\n\n"
                        f"Note: This feature requires ODSExporter integration."
                    )
                else:
                    messagebox.showwarning(
                        "No Data",
                        f"No analysis data found for sample set '{sample_set_name}'"
                    )

        except ImportError as e:
            messagebox.showerror(
                "Missing Component",
                f"Export functionality not available:\n\n{str(e)}"
            )
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                f"Failed to export analysis:\n\n{str(e)}"
            )

    def open_spectral_analysis(self):
        """Open spectral analysis dialog for current color measurements."""
        try:
            from utils.spectral_analyzer import SpectralAnalyzer, analyze_spectral_deviation_from_measurements
            from utils.color_analyzer import ColorAnalyzer, ColorMeasurement
            from tkinter import Toplevel, Text, Scrollbar, Button, Frame, messagebox
            
            # Check if we have color measurement data
            current_sample_set = None
            if (hasattr(self, 'control_panel') and 
                hasattr(self.control_panel, 'sample_set_name') and 
                self.control_panel.sample_set_name.get().strip()):
                current_sample_set = self.control_panel.sample_set_name.get().strip()
            
            # Try to get measurements from current data or database
            measurements = []
            
            if current_sample_set and self.current_file:
                # Get measurements from database for current sample set
                try:
                    from utils.color_analysis_db import ColorAnalysisDB
                    db = ColorAnalysisDB(current_sample_set)
                    raw_measurements = db.get_all_measurements()
                    
                    # Convert to ColorMeasurement objects
                    measurements = []
                    for raw in raw_measurements:
                        measurement = ColorMeasurement(
                            coordinate_id=raw.get('id', 0),
                            coordinate_point=raw.get('coordinate_point', 0),
                            position=(raw.get('x_position', 0.0), raw.get('y_position', 0.0)),
                            rgb=(raw.get('rgb_r', 0), raw.get('rgb_g', 0), raw.get('rgb_b', 0)),
                            lab=(raw.get('l_value', 0.0), raw.get('a_value', 0.0), raw.get('b_value', 0.0)),
                            sample_area={
                                'type': raw.get('sample_type', 'circle'),
                                'size': (raw.get('sample_width', 10.0), raw.get('sample_height', 10.0)),
                                'anchor': raw.get('anchor', 'center')
                            },
                            measurement_date=raw.get('measurement_date', ''),
                            notes=raw.get('notes', '')
                        )
                        measurements.append(measurement)
                    
                    print(f"DEBUG: Loaded {len(measurements)} measurements from ColorAnalysisDB for {current_sample_set}")
                        
                except Exception as e:
                    print(f"Could not load measurements from database: {e}")
            
            if not measurements:
                messagebox.showwarning(
                    "No Data",
                    "No color measurement data found for spectral analysis.\n\n"
                    "Please run color analysis first using the Sample tool."
                )
                return
            
            # Create spectral analysis dialog
            dialog = Toplevel(self.root)
            dialog.title(f"Spectral Analysis - {current_sample_set}")
            dialog.geometry("800x600")
            dialog.resizable(True, True)
            
            # Center dialog
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Create text area with scrollbar for results
            text_frame = Frame(dialog)
            text_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            text_area = Text(text_frame, wrap="word", font=("Courier", 11))
            scrollbar = Scrollbar(text_frame, orient="vertical", command=text_area.yview)
            text_area.configure(yscrollcommand=scrollbar.set)
            
            text_area.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Button frame
            button_frame = Frame(dialog)
            button_frame.pack(fill="x", padx=10, pady=5)
            
            def run_analysis():
                text_area.delete(1.0, "end")
                text_area.insert("end", f"=== SPECTRAL ANALYSIS FOR {current_sample_set} ===\n")
                text_area.insert("end", f"Analyzing {len(measurements)} color measurements...\n\n")
                text_area.update()
                
                try:
                    # Initialize spectral analyzer
                    spectral_analyzer = SpectralAnalyzer()
                    
                    # Perform wavelength deviation analysis
                    text_area.insert("end", "WAVELENGTH DEVIATION ANALYSIS\n")
                    text_area.insert("end", "=" * 40 + "\n")
                    text_area.insert("end", "This shows how RGB channels deviate across spectral regions:\n\n")
                    text_area.update()
                    
                    # Capture the analysis output
                    import io
                    import contextlib
                    
                    # Redirect stdout to capture print statements
                    old_stdout = __import__('sys').stdout
                    captured_output = io.StringIO()
                    
                    try:
                        __import__('sys').stdout = captured_output
                        analyze_spectral_deviation_from_measurements(measurements)
                        captured_text = captured_output.getvalue()
                        text_area.insert("end", captured_text)
                    finally:
                        __import__('sys').stdout = old_stdout
                    
                    text_area.insert("end", "\n" + "=" * 60 + "\n\n")
                    
                    # Generate spectral response analysis
                    text_area.insert("end", "SPECTRAL RESPONSE ANALYSIS\n")
                    text_area.insert("end", "=" * 40 + "\n")
                    text_area.update()
                    
                    illuminants = ['D65', 'A', 'F2']  # Daylight, Incandescent, Fluorescent
                    
                    for illuminant in illuminants:
                        text_area.insert("end", f"\n--- Analysis under {illuminant} illuminant ---\n")
                        spectral_data = spectral_analyzer.analyze_spectral_response(measurements, illuminant)
                        
                        sample_count = len(set(m.sample_id for m in spectral_data))
                        wavelength_count = len(set(m.wavelength for m in spectral_data))
                        
                        text_area.insert("end", f"Generated {len(spectral_data)} spectral measurements\n")
                        text_area.insert("end", f"Covers {sample_count} samples across {wavelength_count} wavelength points\n")
                        
                        if spectral_data:
                            sample_1_data = [m for m in spectral_data if m.sample_id == 'sample_1']
                            if sample_1_data:
                                text_area.insert("end", f"Spectral range: {min(m.wavelength for m in sample_1_data):.0f}-{max(m.wavelength for m in sample_1_data):.0f}nm\n")
                                
                                max_r = max(sample_1_data, key=lambda m: m.rgb_response[0])
                                max_g = max(sample_1_data, key=lambda m: m.rgb_response[1])
                                max_b = max(sample_1_data, key=lambda m: m.rgb_response[2])
                                
                                text_area.insert("end", f"Peak responses - R: {max_r.wavelength:.0f}nm, G: {max_g.wavelength:.0f}nm, B: {max_b.wavelength:.0f}nm\n")
                        text_area.update()
                    
                    # Metamerism analysis
                    text_area.insert("end", "\n" + "=" * 60 + "\n")
                    text_area.insert("end", "METAMERISM ANALYSIS\n")
                    text_area.insert("end", "=" * 40 + "\n")
                    text_area.insert("end", "Analyzing how colors appear under different lighting...\n\n")
                    text_area.update()
                    
                    # Compare first few measurements for metamerism
                    sample_limit = min(4, len(measurements))
                    for i in range(sample_limit):
                        for j in range(i+1, sample_limit):
                            metamerism_index = spectral_analyzer.calculate_metamerism_index(measurements[i], measurements[j])
                            
                            text_area.insert("end", f"Sample {i+1} vs Sample {j+1}: Metamerism Index = {metamerism_index:.3f}\n")
                            if metamerism_index > 2.0:
                                text_area.insert("end", "  → High metamerism - colors may appear different under various lights\n")
                            elif metamerism_index > 1.0:
                                text_area.insert("end", "  → Moderate metamerism - some color shift possible\n")
                            else:
                                text_area.insert("end", "  → Low metamerism - colors should appear consistent\n")
                            text_area.update()
                    
                    text_area.insert("end", "\n" + "=" * 60 + "\n")
                    text_area.insert("end", "PRACTICAL APPLICATIONS\n")
                    text_area.insert("end", "=" * 40 + "\n")
                    text_area.insert("end", "This spectral analysis can help you:\n")
                    text_area.insert("end", "• Identify pigments with unique spectral signatures\n")
                    text_area.insert("end", "• Detect printing method differences (line-engraved vs lithographic)\n")
                    text_area.insert("end", "• Analyze paper aging effects on color reproduction\n")
                    text_area.insert("end", "• Compare stamps printed in different eras with different inks\n")
                    text_area.insert("end", "• Identify potential forgeries through spectral inconsistencies\n")
                    text_area.insert("end", "• Optimize photography lighting for accurate color capture\n\n")
                    
                    text_area.insert("end", "Analysis complete!\n")
                    text_area.see("end")
                    
                except Exception as e:
                    text_area.insert("end", f"\nError during spectral analysis: {str(e)}\n")
                    import traceback
                    text_area.insert("end", traceback.format_exc())
            
            def export_results():
                try:
                    from tkinter import filedialog
                    from datetime import datetime
                    
                    default_filename = f"spectral_analysis_{current_sample_set}_{datetime.now().strftime('%Y%m%d')}.txt"
                    
                    filepath = filedialog.asksaveasfilename(
                        title="Export Spectral Analysis",
                        defaultextension=".txt",
                        filetypes=[
                            ('Text files', '*.txt'),
                            ('All files', '*.*')
                        ],
                        initialfile=default_filename
                    )
                    
                    if filepath:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(text_area.get(1.0, "end"))
                        messagebox.showinfo("Export Complete", f"Spectral analysis exported to:\n{filepath}")
                        
                except Exception as e:
                    messagebox.showerror("Export Error", f"Failed to export analysis:\n{str(e)}")
            
            def plot_spectral_curves():
                try:
                    from tkinter import filedialog
                    from datetime import datetime
                    
                    spectral_analyzer = SpectralAnalyzer()
                    spectral_data = spectral_analyzer.analyze_spectral_response(measurements, 'D65')
                    
                    # Ask user if they want to save the plot
                    save_plot = messagebox.askyesno(
                        "Save Plot?",
                        "Would you like to save the spectral plot as an image file?"
                    )
                    
                    if save_plot:
                        default_plot_name = f"{current_sample_set}_spectral_plot_{datetime.now().strftime('%Y%m%d')}.png"
                        plot_filepath = filedialog.asksaveasfilename(
                            title="Save Spectral Plot",
                            defaultextension=".png",
                            filetypes=[
                                ('PNG files', '*.png'),
                                ('SVG files', '*.svg'),
                                ('PDF files', '*.pdf'),
                                ('All files', '*.*')
                            ],
                            initialfile=default_plot_name
                        )
                        
                        if plot_filepath:
                            spectral_analyzer._save_plot_path = plot_filepath
                    
                    spectral_analyzer.plot_spectral_response(spectral_data, interactive=True)
                    
                    if save_plot and hasattr(spectral_analyzer, '_save_plot_path'):
                        del spectral_analyzer._save_plot_path  # Clean up
                        
                except ImportError:
                    messagebox.showwarning("Missing Dependency", "Install matplotlib to generate spectral plots:\npip install matplotlib")
                except Exception as e:
                    messagebox.showerror("Plot Error", f"Failed to generate plots:\n{str(e)}")
            
            def export_csv_data():
                try:
                    from tkinter import filedialog
                    from datetime import datetime
                    
                    # Generate spectral data for CSV export
                    spectral_analyzer = SpectralAnalyzer()
                    spectral_data = spectral_analyzer.analyze_spectral_response(measurements, 'D65')
                    
                    default_csv_name = f"{current_sample_set}_spectral_data_{datetime.now().strftime('%Y%m%d')}.csv"
                    
                    csv_filepath = filedialog.asksaveasfilename(
                        title="Export Spectral Data CSV",
                        defaultextension=".csv",
                        filetypes=[
                            ('CSV files', '*.csv'),
                            ('All files', '*.*')
                        ],
                        initialfile=default_csv_name
                    )
                    
                    if csv_filepath:
                        success = spectral_analyzer.export_spectral_analysis(spectral_data, csv_filepath)
                        if success:
                            messagebox.showinfo(
                                "CSV Export Complete", 
                                f"Detailed spectral data exported to:\n{csv_filepath}"
                            )
                        else:
                            messagebox.showerror("CSV Export Error", "Failed to export spectral data CSV")
                            
                except Exception as e:
                    messagebox.showerror("CSV Export Error", f"Failed to export CSV data:\n{str(e)}")
            
            # Add buttons
            Button(button_frame, text="Run Analysis", command=run_analysis, font=("Arial", 10, "bold")).pack(side="left", padx=5)
            Button(button_frame, text="Export Results", command=export_results).pack(side="left", padx=5)
            Button(button_frame, text="Export CSV Data", command=export_csv_data).pack(side="left", padx=5)
            Button(button_frame, text="Plot Curves", command=plot_spectral_curves).pack(side="left", padx=5)
            Button(button_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
            
            # Initial message
            text_area.insert("end", f"Spectral Analysis Tool\n")
            text_area.insert("end", f"Sample Set: {current_sample_set}\n")
            text_area.insert("end", f"Measurements: {len(measurements)}\n\n")
            text_area.insert("end", "Click 'Run Analysis' to analyze RGB channel behavior across the visible spectrum (380-700nm).\n\n")
            text_area.insert("end", "This analysis will show:\n")
            text_area.insert("end", "• How RGB channels deviate across wavelength ranges\n")
            text_area.insert("end", "• Spectral response characteristics under different illuminants\n")
            text_area.insert("end", "• Metamerism analysis (color appearance under different lights)\n")
            text_area.insert("end", "• Practical applications for philatelic analysis\n\n")
            
        except ImportError as e:
            messagebox.showerror(
                "Missing Component",
                f"Spectral analysis not available:\n\n{str(e)}\n\n"
                "Please ensure the spectral analyzer module is properly installed."
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to open spectral analysis:\n\n{str(e)}"
            )


    def open_preferences(self):
        """Open the preferences dialog."""
        result = show_preferences_dialog(self.root)
        if result == "ok":
            print("Preferences updated successfully.")

    def _get_available_libraries(self):
        """Get list of available color libraries."""
        try:
            # Use persistent user data directory for color libraries
            import sys
            
            # Use centralized path logic instead of hardcoded paths
            try:
                from utils.path_utils import get_color_libraries_dir
                library_dir = get_color_libraries_dir()
            except ImportError:
                # Fallback if path_utils not available
                if hasattr(sys, '_MEIPASS'):
                    # Running in PyInstaller bundle - use user data directory
                    if sys.platform.startswith('linux'):
                        user_data_dir = os.path.expanduser('~/.local/share/StampZ_II')
                    elif sys.platform == 'darwin':
                        user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ_II')
                    else:
                        user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ_II')
                    library_dir = os.path.join(user_data_dir, "data", "color_libraries")
                else:
                    # Running from source - use relative path
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    library_dir = os.path.join(current_dir, "data", "color_libraries")
            
            # Ensure directory exists
            os.makedirs(library_dir, exist_ok=True)
            
            libraries = []
            if os.path.exists(library_dir):
                for filename in os.listdir(library_dir):
                    if filename.endswith('_library.db'):
                        # Remove '_library.db' suffix to get library name
                        lib_name = filename[:-11]
                        libraries.append(lib_name)
            
            # Add some default options if no libraries exist
            if not libraries:
                libraries = ['user_samples', 'basic_colors']
            else:
                # Ensure user_samples is always available
                if 'user_samples' not in libraries:
                    libraries.append('user_samples')
                libraries.sort()
            
            print(f"DEBUG: Available libraries from {library_dir}: {libraries}")
            return libraries
            
        except Exception as e:
            print(f"Error getting available libraries: {e}")
            return ['user_samples', 'basic_colors']
    
    def _show_library_selection_dialog(self, sample_count, avg_lab, avg_rgb):
        """Show dialog to select library, name the color, and preview the averaged color."""
        from tkinter import Toplevel, Listbox, Button, Frame, Label, Entry, StringVar, Text, Canvas
        
        # Get available libraries
        available_libraries = self._get_available_libraries()
        
        # Create dialog
        dialog = Toplevel(self.root)
        dialog.title("Add Averaged Color to Library")
        dialog.geometry("600x600")
        dialog.resizable(True, True)
        
        # Position dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        selected_library = None
        color_name = None
        
        # Title
        title_label = Label(dialog, text=f"Add averaged color from {sample_count} samples", 
                           font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Color preview frame
        color_frame = Frame(dialog)
        color_frame.pack(fill="x", padx=20, pady=5)
        
        Label(color_frame, text="Color Preview (averaged):", font=("Arial", 12)).pack(anchor="w")
        
        # Color swatch
        color_canvas = Canvas(color_frame, width=100, height=50, bg="white", relief="sunken", bd=2)
        color_canvas.pack(pady=5)
        
        # Convert RGB to hex for display
        r, g, b = [int(c) for c in avg_rgb]
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        color_canvas.create_rectangle(0, 0, 100, 50, fill=hex_color, outline="")
        
        # Color values
        color_info = Label(color_frame, 
                          text=f"RGB: ({r}, {g}, {b})\nLab: ({avg_lab[0]:.1f}, {avg_lab[1]:.1f}, {avg_lab[2]:.1f})\nHex: {hex_color}",
                          font=("Arial", 10), justify="left")
        color_info.pack(pady=5)
        
        # Color name frame
        name_frame = Frame(dialog)
        name_frame.pack(fill="x", padx=20, pady=5)
        
        Label(name_frame, text="Color Name:", font=("Arial", 12)).pack(anchor="w")
        name_var = StringVar(value="New_Color")
        name_entry = Entry(name_frame, textvariable=name_var, font=("Arial", 12))
        name_entry.pack(fill="x", pady=5)
        
        # Naming rules
        rules_text = Label(name_frame, 
                          text="Rules: Use underscores instead of spaces, numbers must follow capital letters (e.g., Red_F137)",
                          font=("Arial", 9), fg="gray", wraplength=550)
        rules_text.pack(pady=2)
        
        # Library selection frame
        lib_frame = Frame(dialog)
        lib_frame.pack(fill="x", padx=20, pady=5)
        
        Label(lib_frame, text="Select Library:", font=("Arial", 12)).pack(anchor="w")
        
        # Library listbox
        lib_listbox = Listbox(lib_frame, height=4, font=("Arial", 11))
        lib_listbox.pack(fill="x", pady=5)
        
        for lib in available_libraries:
            lib_listbox.insert("end", lib)
        
        # Select first library by default
        if available_libraries:
            lib_listbox.selection_set(0)
        
        # New library option
        new_lib_frame = Frame(dialog)
        new_lib_frame.pack(fill="x", padx=20, pady=5)
        
        Label(new_lib_frame, text="Or create new library:", font=("Arial", 12)).pack(anchor="w")
        new_lib_var = StringVar()
        new_lib_entry = Entry(new_lib_frame, textvariable=new_lib_var, font=("Arial", 11))
        new_lib_entry.pack(fill="x", pady=5)
        
        # Summary frame
        summary_frame = Frame(dialog)
        summary_frame.pack(fill="x", padx=20, pady=5)
        
        Label(summary_frame, text="Summary:", font=("Arial", 12)).pack(anchor="w")
        summary_text = Text(summary_frame, height=4, width=60, font=("Arial", 10))
        summary_text.pack(fill="x", pady=5)
        
        summary_text.insert("end", f"This will add ONE color entry to the library:\n")
        summary_text.insert("end", f"• Averaged from {sample_count} sample points\n")
        summary_text.insert("end", f"• Lab values: L*={avg_lab[0]:.1f}, a*={avg_lab[1]:.1f}, b*={avg_lab[2]:.1f}\n")
        summary_text.insert("end", f"• RGB values: R={r}, G={g}, B={b}")
        summary_text.config(state="disabled")
        
        # Button frame
        button_frame = Frame(dialog)
        button_frame.pack(pady=20, fill="x")
        
        def on_ok():
            nonlocal selected_library, color_name
            
            # Get color name
            color_name = name_var.get().strip()
            if not color_name:
                messagebox.showwarning("No Name", "Please enter a name for the color.")
                return
            
            # Check if user entered a new library name
            new_lib_name = new_lib_var.get().strip()
            if new_lib_name:
                selected_library = new_lib_name
            else:
                # Get selected library from listbox
                selection = lib_listbox.curselection()
                if selection:
                    selected_library = available_libraries[selection[0]]
                else:
                    messagebox.showwarning("No Selection", "Please select a library or enter a new library name.")
                    return
            
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Create buttons directly in button_frame with grid layout for better control
        save_button = Button(button_frame, text="Save", command=on_ok, width=15, 
                           font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", 
                           relief="raised", bd=2, height=2)
        save_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        cancel_button = Button(button_frame, text="Cancel", command=on_cancel, width=15,
                             font=("Arial", 11), relief="raised", bd=2, height=2)
        cancel_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Configure grid weights for centering
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # Force button visibility and ensure dialog is large enough
        dialog.update_idletasks()
        dialog.minsize(600, 700)
        
        # Ensure buttons are visible
        save_button.tkraise()
        cancel_button.tkraise()
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return selected_library, color_name
    
    def _add_analysis_to_library(self):
        """Add averaged color from existing analysis results to a color library."""
        try:
            # Check if we have an image loaded
            if not self.current_file:
                messagebox.showwarning(
                    "No Image",
                    "Please load an image first."
                )
                return
            
            # First, try to get measurements from current canvas markers if they exist
            if hasattr(self.canvas, '_coord_markers') and self.canvas._coord_markers:
                non_preview_markers = [m for m in self.canvas._coord_markers if not m.get('is_preview', False)]
                if non_preview_markers:
                    # We have current markers, get the actual count from them
                    current_sample_count = len(non_preview_markers)
                    print(f"DEBUG: Using current canvas markers: {current_sample_count} samples")
                    
                    # Now get the corresponding database measurements for these markers
                    base_image_name = os.path.splitext(os.path.basename(self.current_file))[0]
                    from utils.color_analysis_db import ColorAnalysisDB
                    from utils.color_library_integration import ColorLibraryIntegration
                    
                    sample_set_name = None
                    if (hasattr(self, 'control_panel') and 
                        hasattr(self.control_panel, 'sample_set_name') and 
                        self.control_panel.sample_set_name.get().strip()):
                        sample_set_name = self.control_panel.sample_set_name.get().strip()
                    
                    measurements = []
                    if sample_set_name:
                        try:
                            db = ColorAnalysisDB(sample_set_name)
                            all_measurements = db.get_all_measurements()
                            # Get measurements for this image
                            image_measurements = [m for m in all_measurements if m['image_name'].startswith(base_image_name)]
                            
                            # Sort by timestamp or id and take the most recent ones matching our marker count
                            if image_measurements:
                                if 'analysis_timestamp' in image_measurements[0]:
                                    image_measurements.sort(key=lambda x: x.get('analysis_timestamp', ''), reverse=True)
                                else:
                                    image_measurements.sort(key=lambda x: x.get('id', 0), reverse=True)
                                
                                # Take only the number of measurements that match our current markers
                                measurements = image_measurements[:current_sample_count]
                            
                            print(f"DEBUG: Found {len(measurements)} measurements for {current_sample_count} current markers")
                        except Exception as e:
                            print(f"DEBUG: Error accessing sample set '{sample_set_name}': {e}")
                    
                    # Process the measurements if we found them
                    if measurements:
                        # Calculate average Lab and RGB values
                        lab_values = []
                        rgb_values = []
                        
                        for measurement in measurements:
                            try:
                                lab = (
                                    measurement.get('l_value', 0),
                                    measurement.get('a_value', 0),
                                    measurement.get('b_value', 0)
                                )
                                rgb = (
                                    measurement.get('rgb_r', 0),
                                    measurement.get('rgb_g', 0),
                                    measurement.get('rgb_b', 0)
                                )
                                lab_values.append(lab)
                                rgb_values.append(rgb)
                            except Exception as e:
                                print(f"Error processing measurement: {e}")
                                continue
                        
                        if lab_values:
                            # Calculate averages
                            avg_lab = (
                                sum(lab[0] for lab in lab_values) / len(lab_values),
                                sum(lab[1] for lab in lab_values) / len(lab_values),
                                sum(lab[2] for lab in lab_values) / len(lab_values)
                            )
                            avg_rgb = (
                                sum(rgb[0] for rgb in rgb_values) / len(rgb_values),
                                sum(rgb[1] for rgb in rgb_values) / len(rgb_values),
                                sum(rgb[2] for rgb in rgb_values) / len(rgb_values)
                            )
                            
                            # Show dialog with actual sample count
                            library_name, color_name = self._show_library_selection_dialog(
                                current_sample_count, avg_lab, avg_rgb
                            )
                            
                            if library_name and color_name:
                                # Create integration instance and save
                                integration = ColorLibraryIntegration()
                                metadata = {
                                    'image_name': base_image_name,
                                    'sample_count': current_sample_count,
                                    'averaged_from': f"{current_sample_count} analyzed sample points",
                                    'analysis_date': datetime.now().isoformat(),
                                    'source_sample_set': sample_set_name if sample_set_name else 'auto-detected'
                                }
                                
                                success = integration.add_sample_to_library(
                                    library_name=library_name,
                                    sample_lab=avg_lab,
                                    user_name=color_name,
                                    category="Averaged Colors",
                                    description=f"Averaged color from {current_sample_count} analyzed sample points",
                                    source="StampZ Analysis",
                                    notes=f"RGB: ({avg_rgb[0]:.0f}, {avg_rgb[1]:.0f}, {avg_rgb[2]:.0f}), Lab: ({avg_lab[0]:.1f}, {avg_lab[1]:.1f}, {avg_lab[2]:.1f})",
                                    sample_metadata=metadata
                                )
                                
                                if success:
                                    messagebox.showinfo(
                                        "Success",
                                        f"Successfully added averaged color '{color_name}' to library '{library_name}'.\n\n"
                                        f"Color was averaged from {current_sample_count} analyzed sample points for image '{base_image_name}'.\n\n"
                                        f"You can view and manage this color using the Color Library Manager."
                                    )
                                else:
                                    messagebox.showerror(
                                        "Failed",
                                        f"Failed to add color '{color_name}' to library '{library_name}'.\n\n"
                                        f"Please check the color name follows the naming rules."
                                    )
                            return
            
            # Fallback to old method if no current markers
            base_image_name = os.path.splitext(os.path.basename(self.current_file))[0]
            from utils.color_analysis_db import ColorAnalysisDB
            from utils.color_library_integration import ColorLibraryIntegration
            
            sample_set_name = None
            if (hasattr(self, 'control_panel') and 
                hasattr(self.control_panel, 'sample_set_name') and 
                self.control_panel.sample_set_name.get().strip()):
                sample_set_name = self.control_panel.sample_set_name.get().strip()
            measurements = []

            if sample_set_name:
                try:
                    db = ColorAnalysisDB(sample_set_name)
                    all_measurements = db.get_all_measurements()
                    # Filter measurements for this image
                    image_measurements = [m for m in all_measurements if m['image_name'].startswith(base_image_name)]
                    
                    # Sort by timestamp (most recent first) and take only the most recent batch
                    if image_measurements:
                        # Sort by analysis_timestamp if available, otherwise by id
                        if 'analysis_timestamp' in image_measurements[0]:
                            image_measurements.sort(key=lambda x: x.get('analysis_timestamp', ''), reverse=True)
                        else:
                            image_measurements.sort(key=lambda x: x.get('id', 0), reverse=True)
                        
                        # Take only the most recent batch (max 5 samples)
                        measurements = image_measurements[:5]
                    
                    print(f"DEBUG: Found {len(measurements)} most recent measurements for image '{base_image_name}' in sample set '{sample_set_name}'")
                except Exception as e:
                    print(f"DEBUG: Error accessing sample set '{sample_set_name}': {e}")
                    
            if not measurements:
                try:
                    all_sample_sets = ColorAnalysisDB.get_all_sample_set_databases()
                    print(f"DEBUG: Searching through {len(all_sample_sets)} sample sets for image '{base_image_name}'")
                    
                    for set_name in all_sample_sets:
                        try:
                            db = ColorAnalysisDB(set_name)
                            all_measurements = db.get_all_measurements()
                            # Filter measurements for this image
                            image_measurements = [m for m in all_measurements if m['image_name'].startswith(base_image_name)]
                            
                            if image_measurements:
                                # Sort by timestamp (most recent first) and take only the most recent batch
                                if 'analysis_timestamp' in image_measurements[0]:
                                    image_measurements.sort(key=lambda x: x.get('analysis_timestamp', ''), reverse=True)
                                else:
                                    image_measurements.sort(key=lambda x: x.get('id', 0), reverse=True)
                                
                                # Take only the most recent batch (max 5 samples)
                                set_measurements = image_measurements[:5]
                                measurements.extend(set_measurements)
                                print(f"DEBUG: Found {len(set_measurements)} most recent measurements in sample set '{set_name}'")
                                if not sample_set_name:
                                    sample_set_name = set_name
                                break  # Stop after finding the first set with measurements
                        except Exception as e:
                            print(f"Debug: Error checking sample set '{set_name}': {e}")
                            continue
                except Exception as e:
                    print(f"Debug: Error getting sample set list: {e}")
            
            if not measurements:
                messagebox.showwarning(
                    "No Analysis Data",
                    f"No color analysis data found for image '{base_image_name}'.\n\n"
                    f"Please run color analysis first using the Sample tool."
                )
                return
            
            # Calculate average Lab and RGB values from existing measurements
            lab_values = []
            rgb_values = []
            
            for measurement in measurements:
                try:
                    # Get Lab values (using correct column names from ColorAnalysisDB)
                    lab = (
                        measurement.get('l_value', 0),
                        measurement.get('a_value', 0),
                        measurement.get('b_value', 0)
                    )
                    
                    # Get RGB values (using correct column names from ColorAnalysisDB)
                    rgb = (
                        measurement.get('rgb_r', 0),
                        measurement.get('rgb_g', 0),
                        measurement.get('rgb_b', 0)
                    )
                    
                    lab_values.append(lab)
                    rgb_values.append(rgb)
                    
                except Exception as e:
                    print(f"Error processing measurement: {e}")
                    continue
            
            if not lab_values:
                messagebox.showerror(
                    "Data Error",
                    "Could not process any of the analysis measurements."
                )
                return
            
            # Calculate average Lab and RGB values
            avg_lab = (
                sum(lab[0] for lab in lab_values) / len(lab_values),
                sum(lab[1] for lab in lab_values) / len(lab_values),
                sum(lab[2] for lab in lab_values) / len(lab_values)
            )
            
            avg_rgb = (
                sum(rgb[0] for rgb in rgb_values) / len(rgb_values),
                sum(rgb[1] for rgb in rgb_values) / len(rgb_values),
                sum(rgb[2] for rgb in rgb_values) / len(rgb_values)
            )
            
            # Show library selection dialog with color preview
            library_name, color_name = self._show_library_selection_dialog(
                len(measurements), avg_lab, avg_rgb
            )
            
            if not library_name or not color_name:
                return
            
            # Create integration instance
            integration = ColorLibraryIntegration()
            
            # Create metadata for the averaged color
            metadata = {
                'image_name': base_image_name,
                'sample_count': len(measurements),
                'averaged_from': f"{len(measurements)} analyzed sample points",
                'analysis_date': datetime.now().isoformat(),
                'source_sample_set': sample_set_name if sample_set_name else 'auto-detected'
            }
            
            # Add the averaged color to library
            success = integration.add_sample_to_library(
                library_name=library_name,
                sample_lab=avg_lab,
                user_name=color_name,
                category="Averaged Colors",
                description=f"Averaged color from {len(measurements)} analyzed sample points",
                source="StampZ Analysis",
                notes=f"RGB: ({avg_rgb[0]:.0f}, {avg_rgb[1]:.0f}, {avg_rgb[2]:.0f}), Lab: ({avg_lab[0]:.1f}, {avg_lab[1]:.1f}, {avg_lab[2]:.1f})",
                sample_metadata=metadata
            )
            
            if success:
                messagebox.showinfo(
                    "Success",
                    f"Successfully added averaged color '{color_name}' to library '{library_name}'.\n\n"
                    f"Color was averaged from {len(measurements)} analyzed sample points for image '{base_image_name}'.\n\n"
                    f"You can view and manage this color using the Color Library Manager."
                )
            else:
                messagebox.showerror(
                    "Failed",
                    f"Failed to add color '{color_name}' to library '{library_name}'.\n\n"
                    f"Please check the color name follows the naming rules."
                )
                
        except ImportError as e:
            messagebox.showerror(
                "Missing Component",
                f"Color library integration not available:\n\n{str(e)}"
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to add analysis to library:\n\n{str(e)}"
            )

    def _apply_fine_square(self):
        """Apply fine square adjustment to make a 4-sided polygon perfectly square/rectangular."""
        if not self.canvas.original_image:
            messagebox.showwarning("No Image", "Please open an image before using Fine Square.")
            return
        
        vertices = self.canvas.get_vertices()
        
        if len(vertices) != 4:
            messagebox.showwarning(
                "Invalid Selection", 
                "Fine Square adjustment requires exactly 4 vertices.\n\n"
                "Current selection has {} vertices. Please select a 4-sided polygon.".format(len(vertices))
            )
            return
        
        try:
            from utils.auto_square import fine_square_adjustment
            
            # Show method selection dialog
            method = self._show_fine_square_method_dialog()
            if not method:
                return  # User cancelled
            
            # Apply fine square adjustment
            adjusted_vertices = fine_square_adjustment(vertices, method=method)
            
            # Update the canvas with the new vertices
            self.canvas.set_vertices(adjusted_vertices)
            
        except Exception as e:
            messagebox.showerror("Fine Square Error", f"Failed to apply fine square adjustment: {str(e)}")
    
    def _show_fine_square_method_dialog(self) -> str:
        """Show dialog to select fine square adjustment method."""
        from tkinter import Toplevel, Radiobutton, Button, Label, Frame, StringVar
        
        # Create dialog window
        dialog = Toplevel(self.root)
        dialog.title("Fine Square Method")
        dialog.geometry("400x300")  # Adjusted size for single option
        dialog.resizable(False, False)
        
        # Make dialog modal and ensure it stays with parent
        dialog.transient(self.root)  # Set parent window
        dialog.grab_set()  # Make it modal
        
        # Position dialog relative to main window
        self.root.update_idletasks()  # Ensure main window's geometry is up to date
        dialog.update_idletasks()  # Ensure dialog's geometry is up to date
        
        # Calculate position relative to main window
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")  # Position relative to main window
        
        # Variables
        selected_method = StringVar(value='preserve_center_level')
        result = None
        
        # Create widgets
        Label(
            dialog, 
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Method options frame
        options_frame = Frame(dialog)
        options_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Method 1: Preserve Center
        method1_frame = Frame(options_frame)
        method1_frame.pack(fill="x", pady=5)
        
        
        # Method 2: Preserve Center + Level
        method2_frame = Frame(options_frame)
        method2_frame.pack(fill="x", pady=5)
        
        Radiobutton(
            method2_frame,
            text="Preserve Center + Level",
            variable=selected_method,
            value='preserve_center_level',
            font=("Arial", 11, "bold"),
            foreground="#0066CC"
        ).pack(anchor="w")
        
        Label(
            method2_frame,
            text="• Keeps the center point of your selection\n"
                 "• Preserves rectangular proportions (width ≠ height)\n"
                 "• Forces sides to be perfectly horizontal/vertical\n"
                 "• Makes all corners exactly 90° AND levels the image\n"
                 "• Perfect for rectangular stamps that need to be leveled",
            font=("Arial", 9),
            justify="left",
            foreground="#0066CC"
        ).pack(anchor="w", padx=20)
        
        
        # Buttons
        button_frame = Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_apply():
            nonlocal result
            result = selected_method.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        Button(button_frame, text="Apply", command=on_apply, width=10).pack(side="left", padx=5)
        Button(button_frame, text="Cancel", command=on_cancel, width=10).pack(side="left", padx=5)
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result

    def _apply_global_offset(self):
        """Apply global position offset to all sample markers."""
        # Check if we have sample markers to adjust
        if not hasattr(self.canvas, '_coord_markers') or not self.canvas._coord_markers:
            messagebox.showwarning(
                "No Samples", 
                "No sample markers found. Please load or place some sample markers first."
            )
            return

        # Get offset values from control panel
        x_offset = self.control_panel.global_x_offset.get()
        y_offset = self.control_panel.global_y_offset.get()

        if x_offset == 0 and y_offset == 0:
            messagebox.showinfo("No Offset", "Global offset values are both 0. No changes will be made.")
            return

        try:
            # Apply offset to all markers
            for i, marker in enumerate(self.canvas._coord_markers):
                if marker.get('is_preview', False):
                    continue  # Skip preview markers

                # Update image position (Y is already in Cartesian coordinates)
                old_x, old_y = marker['image_pos']
                new_x = old_x + x_offset
                new_y = old_y + y_offset  # Direct addition for Cartesian system
                marker['image_pos'] = (new_x, new_y)

                # Update canvas position
                canvas_x, canvas_y = self.canvas._image_to_screen_coords(new_x, new_y)
                marker['canvas_pos'] = (canvas_x, canvas_y)

                # Remove old visual marker
                old_tag = marker.get('tag')
                if old_tag:
                    self.canvas.delete(old_tag)

                # Create new visual marker at updated position
                new_tag = f"coord_marker_{i}_offset"
                marker['tag'] = new_tag

                # Draw the marker using current line color
                line_color = self.control_panel.get_line_color()
                sample_type = marker['sample_type']

                if sample_type == 'circle':
                    radius = marker['sample_width'] / 2
                    self.canvas.create_oval(
                        canvas_x - radius, canvas_y - radius,
                        canvas_x + radius, canvas_y + radius,
                        outline=line_color, width=2, tags=new_tag
                    )
                else:
                    # Rectangle
                    half_w = marker['sample_width'] / 2
                    half_h = marker['sample_height'] / 2
                    self.canvas.create_rectangle(
                        canvas_x - half_w, canvas_y - half_h,
                        canvas_x + half_w, canvas_y + half_h,
                        outline=line_color, width=2, tags=new_tag
                    )

                # Draw cross marker
                cross_size = 8
                self.canvas.create_line(
                    canvas_x - cross_size, canvas_y,
                    canvas_x + cross_size, canvas_y,
                    fill=line_color, width=2, tags=new_tag
                )
                self.canvas.create_line(
                    canvas_x, canvas_y - cross_size,
                    canvas_x, canvas_y + cross_size,
                    fill=line_color, width=2, tags=new_tag
                )

                # Draw sample number
                self.canvas.create_text(
                    canvas_x + 12, canvas_y - 12,
                    text=str(i + 1),  # Sample number (1-based)
                    fill=line_color, font=("Arial", 10, "bold"),
                    tags=new_tag
                )

            # Update status
            self.control_panel.offset_status.set(f"Global offset applied: X={x_offset}, Y={y_offset}")

            # Reset offset values
            self.control_panel.global_x_offset.set(0)
            self.control_panel.global_y_offset.set(0)

            # Force canvas update
            self.canvas.update_idletasks()
            self.canvas.update()

            messagebox.showinfo(
                "Offset Applied", 
                f"Global offset applied to {len([m for m in self.canvas._coord_markers if not m.get('is_preview', False)])} sample markers.\n\n"
                f"Offset: X={x_offset}, Y={y_offset} pixels"
            )

        except Exception as e:
            messagebox.showerror(
                "Offset Error", 
                f"Failed to apply global offset:\n\n{str(e)}"
            )

    def _apply_individual_offset(self):
        """Apply individual position offset to selected sample marker."""
        # Check if we have sample markers to adjust
        if not hasattr(self.canvas, '_coord_markers') or not self.canvas._coord_markers:
            messagebox.showwarning(
                "No Samples", 
                "No sample markers found. Please load or place some sample markers first."
            )
            return

        # Get selected sample and offset values from control panel
        selected_sample = self.control_panel.selected_sample.get()
        x_offset = self.control_panel.individual_x_offset.get()
        y_offset = self.control_panel.individual_y_offset.get()

        if x_offset == 0 and y_offset == 0:
            messagebox.showinfo("No Offset", "Individual offset values are both 0. No changes will be made.")
            return

        # Find the selected sample (1-based to 0-based index)
        marker_index = selected_sample - 1
        non_preview_markers = [m for m in self.canvas._coord_markers if not m.get('is_preview', False)]

        if marker_index < 0 or marker_index >= len(non_preview_markers):
            messagebox.showwarning(
                "Invalid Sample", 
                f"Sample {selected_sample} not found. Available samples: 1-{len(non_preview_markers)}"
            )
            return

        try:
            # Find the actual marker in the original list
            target_marker = None
            actual_index = -1
            non_preview_count = 0

            for i, marker in enumerate(self.canvas._coord_markers):
                if not marker.get('is_preview', False):
                    if non_preview_count == marker_index:
                        target_marker = marker
                        actual_index = i
                        break
                    non_preview_count += 1

            if not target_marker:
                messagebox.showerror("Error", f"Could not find sample {selected_sample}")
                return

            # Update marker position (Y coordinates already in Cartesian system)
            old_x, old_y = target_marker['image_pos']
            new_x = old_x + x_offset
            new_y = old_y + y_offset  # Don't invert Y, already in Cartesian

            # Update marker position
            target_marker['image_pos'] = (new_x, new_y)

            # Update canvas position
            canvas_x, canvas_y = self.canvas._image_to_screen_coords(new_x, new_y)
            target_marker['canvas_pos'] = (canvas_x, canvas_y)

            # Remove old visual marker
            old_tag = target_marker.get('tag')
            if old_tag:
                self.canvas.delete(old_tag)

            # Create new visual marker with preserved dimensions
            new_tag = f"coord_marker_{actual_index}_offset"
            target_marker['tag'] = new_tag

            # Get the marker's original dimensions and properties
            line_color = self.control_panel.get_line_color()
            sample_type = target_marker['sample_type']
            width = target_marker.get('sample_width')
            height = target_marker.get('sample_height')

            if sample_type == 'circle':
                radius = width / 2
                self.canvas.create_oval(
                    canvas_x - radius, canvas_y - radius,
                    canvas_x + radius, canvas_y + radius,
                    outline=line_color, width=2, tags=new_tag
                )
            else:  # rectangle
                half_w = width / 2
                half_h = height / 2
                self.canvas.create_rectangle(
                    canvas_x - half_w, canvas_y - half_h,
                    canvas_x + half_w, canvas_y + half_h,
                    outline=line_color, width=2, tags=new_tag
                )

            # Draw cross marker
            cross_size = 8
            self.canvas.create_line(
                canvas_x - cross_size, canvas_y,
                canvas_x + cross_size, canvas_y,
                fill=line_color, width=2, tags=new_tag
            )
            self.canvas.create_line(
                canvas_x, canvas_y - cross_size,
                canvas_x, canvas_y + cross_size,
                fill=line_color, width=2, tags=new_tag
            )

            # Draw sample number
            self.canvas.create_text(
                canvas_x + 12, canvas_y - 12,
                text=str(selected_sample),
                fill=line_color, font=("Arial", 10, "bold"),
                tags=new_tag
            )

            # Update status
            current_status = self.control_panel.offset_status.get()
            if "No offsets applied" in current_status:
                self.control_panel.offset_status.set(f"Sample {selected_sample}: X={x_offset}, Y={y_offset}")
            else:
                self.control_panel.offset_status.set(f"{current_status}; Sample {selected_sample}: X={x_offset}, Y={y_offset}")

            # Reset offset values
            self.control_panel.individual_x_offset.set(0)
            self.control_panel.individual_y_offset.set(0)

            # Force canvas update
            self.canvas.update_idletasks()
            self.canvas.update()

            messagebox.showinfo(
                "Offset Applied", 
                f"Individual offset applied to sample {selected_sample}.\n\n"
                f"Moved from ({old_x:.1f}, {old_y:.1f}) to ({new_x:.1f}, {new_y:.1f})\n"
                f"Offset: X={x_offset}, Y={y_offset} pixels"
            )

        except Exception as e:
            messagebox.showerror(
                "Offset Error", 
                f"Failed to apply individual offset:\n\n{str(e)}"
            )

    def _reset_all_offsets(self):
        """Reset all position offset controls and status."""
        # Reset all offset values
        self.control_panel.global_x_offset.set(0)
        self.control_panel.global_y_offset.set(0)
        self.control_panel.individual_x_offset.set(0)
        self.control_panel.individual_y_offset.set(0)

        # Reset status
        self.control_panel.offset_status.set("No offsets applied")

        messagebox.showinfo("Reset Complete", "All offset values have been reset to 0.")

    def _refresh_sample_markers_display(self, coordinates):
        """Refresh the visual sample markers to reflect updated parameters."""
        print(f"DEBUG: _refresh_sample_markers_display called with {len(coordinates)} coordinates")
        
        if not hasattr(self.canvas, '_coord_markers') or not coordinates:
            return
        
        try:
            # Clear existing visual markers
            for marker in self.canvas._coord_markers:
                tag = marker.get('tag')
                if tag:
                    self.canvas.delete(tag)
            
            # Update markers with new parameters and redraw them
            non_preview_markers = [m for m in self.canvas._coord_markers if not m.get('is_preview', False)]
            line_color = self.control_panel.get_line_color()
            
            for i, (marker, coord) in enumerate(zip(non_preview_markers, coordinates)):
                # Update marker parameters from coordinate data
                marker['sample_type'] = 'circle' if coord.sample_type.value == 'circle' else 'rectangle'
                marker['sample_width'] = coord.sample_size[0]
                marker['sample_height'] = coord.sample_size[1]
                marker['anchor'] = coord.anchor_position
                
                # Keep the existing position (already updated from fine-tuning if any)
                canvas_x, canvas_y = self.canvas._image_to_screen_coords(*marker['image_pos'])
                marker['canvas_pos'] = (canvas_x, canvas_y)
                
                # Create new visual marker
                new_tag = f"coord_marker_{i}_updated"
                marker['tag'] = new_tag
                
                sample_type = marker['sample_type']
                width = marker['sample_width']
                height = marker['sample_height']
                
                if sample_type == 'circle':
                    radius = width / 2
                    self.canvas.create_oval(
                        canvas_x - radius, canvas_y - radius,
                        canvas_x + radius, canvas_y + radius,
                        outline=line_color, width=2, tags=new_tag
                    )
                else:  # rectangle
                    half_w = width / 2
                    half_h = height / 2
                    self.canvas.create_rectangle(
                        canvas_x - half_w, canvas_y - half_h,
                        canvas_x + half_w, canvas_y + half_h,
                        outline=line_color, width=2, tags=new_tag
                    )
                
                # Draw cross marker
                cross_size = 8
                self.canvas.create_line(
                    canvas_x - cross_size, canvas_y,
                    canvas_x + cross_size, canvas_y,
                    fill=line_color, width=2, tags=new_tag
                )
                self.canvas.create_line(
                    canvas_x, canvas_y - cross_size,
                    canvas_x, canvas_y + cross_size,
                    fill=line_color, width=2, tags=new_tag
                )
                
                # Draw sample number
                self.canvas.create_text(
                    canvas_x + 12, canvas_y - 12,
                    text=str(i + 1),
                    fill=line_color, font=("Arial", 10, "bold"),
                    tags=new_tag
                )
                
                print(f"DEBUG: Refreshed marker {i+1}: {sample_type} {width}x{height} {coord.anchor_position} at ({marker['image_pos']})")
            
            # Force canvas update
            self.canvas.update_idletasks()
            self.canvas.update_display()
            print(f"DEBUG: Display refresh complete")
            
        except Exception as e:
            print(f"DEBUG: Error refreshing display: {e}")
            import traceback
            traceback.print_exc()

    def open_3d_analysis(self):
        """Open 3D color space analysis tool."""
        try:
            # Import Plot_3D module
            from plot3d.Plot_3D import Plot3DApp
            
            # Get current sample set name
            current_sample_set = None
            if (hasattr(self, 'control_panel') and 
                hasattr(self.control_panel, 'sample_set_name') and 
                self.control_panel.sample_set_name.get().strip()):
                current_sample_set = self.control_panel.sample_set_name.get().strip()
            
            # Check if we have data to analyze
            if current_sample_set:
                # Try to get color data from StampZ database
                try:
                    from utils.color_analysis_db import ColorAnalysisDB
                    db = ColorAnalysisDB(current_sample_set)
                    measurements = db.get_all_measurements()
                    
                    if measurements:
                        # Export StampZ data to temporary CSV file for Plot_3D
                        temp_csv_path = self._export_data_for_plot3d(current_sample_set, measurements)
                        
                        if temp_csv_path and os.path.exists(temp_csv_path):
                            # Launch Plot_3D with exported data
                            messagebox.showinfo(
                                "3D Analysis",
                                f"Launching 3D color analysis with {len(measurements)} measurements from '{current_sample_set}'.\n\n"
                                "The 3D analysis window will open shortly."
                            )
                            
                            # Create Plot_3D app instance with exported data
                            plot_app = Plot3DApp(parent=self.root, data_path=temp_csv_path)
                        else:
                            messagebox.showerror(
                                "Export Error",
                                "Failed to export data for 3D analysis. Please try again."
                            )
                    else:
                        messagebox.showinfo(
                            "No Analysis Data",
                            f"No color analysis data found for sample set '{current_sample_set}'.\n\n"
                            "Please run color analysis first using the Sample tool."
                        )
                except Exception as e:
                    print(f"Error accessing analysis data: {e}")
                    messagebox.showerror(
                        "Data Error",
                        f"Could not access analysis data for '{current_sample_set}'.\n\n"
                        f"Error: {str(e)}"
                    )
            else:
                # No current sample set - launch Plot_3D in standalone mode (with file dialog)
                messagebox.showinfo(
                    "3D Analysis",
                    "Launching 3D color analysis tool.\n\n"
                    "You can load existing data files or import from spreadsheets."
                )
                
                # Create Plot_3D app instance without data_path to trigger file dialog
                plot_app = Plot3DApp(parent=self.root)
                
        except ImportError as e:
            messagebox.showerror(
                "Import Error",
                f"Could not load 3D analysis module:\n\n{str(e)}\n\n"
                "Please ensure all Plot_3D components are properly installed."
            )
        except Exception as e:
            messagebox.showerror(
                "Launch Error",
                f"Failed to launch 3D analysis:\n\n{str(e)}"
            )
    
    def _export_data_for_plot3d(self, sample_set_name, measurements):
        """Export StampZ color analysis data to CSV format compatible with Plot_3D.
        
        Plot_3D Format Requirements:
        - Row 1: Headers (X_norm, Y_norm, Z_norm, DataID as first 4 columns)
        - Rows 2-7: Empty dummy rows for K-means processing
        - Row 8+: Actual data starts here
        - Column G: Marker type validation table
        - Column H: Color markers validation table  
        - Column L: Color spheres validation table
        
        Args:
            sample_set_name (str): Name of the sample set
            measurements (list): List of color measurement dictionaries
            
        Returns:
            str: Path to exported CSV file, or None if export failed
        """
        try:
            import csv
            import tempfile
            from datetime import datetime
            from utils.color_analysis_db import ColorAnalysisDB
            
            # Create temporary CSV file
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f"stampz_{sample_set_name}_{timestamp}.csv"
            csv_path = os.path.join(temp_dir, csv_filename)
            
            # Get fresh data from database
            db = ColorAnalysisDB(sample_set_name)
            all_measurements = db.get_all_measurements()
            
            # Use individual measurements only (no averaged data for 3D plotting)
            individual_measurements = [m for m in all_measurements if not m.get('is_averaged', False)]
            
            print(f"DEBUG: Found {len(individual_measurements)} individual measurements for Plot_3D export")
            
            # Sort measurements by image name and coordinate point for consistent ordering
            sorted_measurements = sorted(individual_measurements, 
                                       key=lambda x: (x['image_name'], x['coordinate_point']))
            
            # Define Plot_3D format headers - first 4 columns are the data columns
            headers = [
                'X_norm',          # Column A - Normalized X coordinate (L* or R)
                'Y_norm',          # Column B - Normalized Y coordinate (a* or G)
                'Z_norm',          # Column C - Normalized Z coordinate (b* or B)
                'DataID',          # Column D - Sample identifier
                'E',               # Column E - (empty for now)
                'F',               # Column F - (empty for now)
                'G',               # Column G - Marker type validation table
                'H',               # Column H - Color markers validation table
                'I',               # Column I - (empty for now)
                'J',               # Column J - (empty for now)
                'K',               # Column K - (empty for now)
                'L'                # Column L - Color spheres validation table
            ]
            
            # Define marker type validation data for column G (from your existing Plot_3D format)
            marker_types = ['^', '<', '>', 'v', 'o', 's', 'p', 'h', 'x', '*', 'D', '+']
            
            # Define color validation data for columns H and L (from your existing Plot_3D format)
            color_names_h = ['red', 'green', 'blue', 'lime', 'blueviolet', 'purple', 'darkorange', 'black', 'orchid', 'deeppink']
            color_names_l = ['red', 'green', 'blue', 'yellow', 'blueviolet', 'cyan', 'magenta', 'orange', 'purple', 'brown', 'pink', 'lime', 'navy', 'teal']
            
            # Write CSV data in Plot_3D compatible format
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                
                # Row 1: Write headers
                writer.writeheader()
                
                # Rows 2-7: Write empty dummy rows for K-means (6 empty rows)
                for dummy_row in range(6):
                    empty_row = {header: '' for header in headers}
                    # Add validation data to appropriate columns in dummy rows
                    if dummy_row < len(marker_types):
                        empty_row['G'] = marker_types[dummy_row]
                    if dummy_row < len(color_names_h):
                        empty_row['H'] = color_names_h[dummy_row]
                    if dummy_row < len(color_names_l):
                        empty_row['L'] = color_names_l[dummy_row]
                    writer.writerow(empty_row)
                
                # Row 8+: Write actual measurement data
                for i, measurement in enumerate(sorted_measurements, 1):
                    try:
                        # Get Lab values
                        l_val = measurement.get('l_value', 0.0)
                        a_val = measurement.get('a_value', 0.0)
                        b_val = measurement.get('b_value', 0.0)
                        
                        # Normalize L*a*b* values for Plot_3D
                        # L* is 0-100, normalize to 0-1
                        x_norm = l_val / 100.0
                        # a* and b* are typically -128 to +127, normalize to 0-1
                        y_norm = (a_val + 128) / 256.0
                        z_norm = (b_val + 128) / 256.0
                        
                        # Create data row - only populate the first 4 columns with data
                        row_data = {
                            'X_norm': round(x_norm, 6),  # Normalized L*
                            'Y_norm': round(y_norm, 6),  # Normalized a*
                            'Z_norm': round(z_norm, 6),  # Normalized b*
                            'DataID': f"{sample_set_name}_Sample_{i:03d}",
                            'E': '',               # Empty
                            'F': '',               # Empty
                            'G': '',               # Empty (validation data only in rows 2-7)
                            'H': '',               # Empty (validation data only in rows 2-7)
                            'I': '',               # Empty
                            'J': '',               # Empty
                            'K': '',               # Empty
                            'L': ''                # Empty (validation data only in rows 2-7)
                        }
                        
                        writer.writerow(row_data)
                        
                    except Exception as e:
                        print(f"Warning: Could not process measurement {i}: {e}")
                        continue
            
            print(f"Successfully exported {len(sorted_measurements)} measurements to Plot_3D format: {csv_path}")
            print(f"Format: Row 1=Headers, Rows 2-7=K-means dummy rows, Row 8+=Data")
            return csv_path
            
        except Exception as e:
            print(f"Error exporting data for Plot_3D: {e}")
            import traceback
            traceback.print_exc()
            return None

    def open_database_viewer(self):
        from gui.database_viewer import DatabaseViewer
        DatabaseViewer(self.root)

def main():
    # Set up logging
    import logging
    import tempfile
    import os
    from datetime import datetime
    
    # Create logs directory in user's home
    log_dir = os.path.expanduser('~/Library/Logs/StampZ')
    os.makedirs(log_dir, exist_ok=True)
    
    # Set up logging to file
    log_file = os.path.join(log_dir, f'stampz_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Also log to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    
    logging.info('Starting StampZ application')
    
    try:
        logging.debug('Initializing Tk')
        root = tk.Tk()
        root.withdraw()  # Hide window during initialization
        logging.debug('Tk initialized successfully')
        
        logging.debug('Initializing StampZApp')
        app = StampZApp(root)
        logging.debug('StampZApp initialized successfully')
        
        logging.debug('Showing main window')
        root.deiconify()
        logging.info('Application ready')
        root.mainloop()
    except Exception as e:
        import traceback
        error_msg = f"Failed to initialize application:\n\n{str(e)}\n\n{traceback.format_exc()}"
        try:
            # Try to show error in GUI
            import tkinter.messagebox as messagebox
            messagebox.showerror("Initialization Error", error_msg)
        except:
            # Fallback to console if GUI fails
            print(error_msg)
        raise  # Re-raise the exception for the crash report

if __name__ == "__main__":
    main()
