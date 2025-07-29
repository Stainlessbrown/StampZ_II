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

logger = logging.getLogger(__name__)

class StampZApp:
    """Main application window for StampZ."""
    def __init__(self, root: tk.Tk):
        # Ensure data directories exist first
        ensure_data_directories()
        
        self.root = root
        self.root.title("StampZ")
        self._set_application_name()
        try:
            self.root.tk.call('wm', 'class', self.root, 'StampZ')
        except:
            pass
        # Use the environment variable for recent files directory
        stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
        if stampz_data_dir:
            recent_dir = os.path.join(stampz_data_dir, 'recent')
            self.recent_files = RecentFilesManager(recent_dir=recent_dir)
        else:
            self.recent_files = RecentFilesManager()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.9)
        window_height = int(screen_height * 0.9)
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.root.minsize(800, 600)
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

    def _set_application_name(self):
        try:
            self.root.tk.call('tk', 'appname', 'StampZ')
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
        filetypes = [
            ('Image files', '*.jpg *.jpeg *.tif *.png'),
            ('TIFF files', '*.tif'),
            ('JPEG files', '*.jpg *.jpeg'),
            ('PNG files', '*.png')
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
                image = load_image(filename)
                self.canvas.load_image(image)
                self.current_file = filename
                self.control_panel.enable_controls(True)
                base_filename = os.path.basename(filename)
                self.root.title(f"StampZ - {base_filename}")
                self.control_panel.update_current_filename(filename)
            except ImageLoadError as e:
                messagebox.showerror("Error", str(e))

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
            filetypes = []
            if panel_options.format == SaveFormat.JPEG:
                filetypes = [
                    ('JPEG files', '*.jpg *.jpeg'),
                    ('TIFF files', '*.tif *.tiff'),
                    ('PNG files', '*.png'),
                    ('All Image files', '*.jpg *.jpeg *.tif *.tiff *.png')
                ]
                default_ext = '.jpg'
            elif panel_options.format == SaveFormat.PNG:
                filetypes = [
                    ('PNG files', '*.png'),
                    ('TIFF files', '*.tif *.tiff'),
                    ('JPEG files', '*.jpg *.jpeg'),
                    ('All Image files', '*.jpg *.jpeg *.tif *.tiff *.png')
                ]
                default_ext = '.png'
            else:  # TIFF
                filetypes = [
                    ('TIFF files', '*.tif *.tiff'),
                    ('JPEG files', '*.jpg *.jpeg'),
                    ('PNG files', '*.png'),
                    ('All Image files', '*.jpg *.jpeg *.tif *.tiff *.png')
                ]
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
                    selected_format = SaveFormat.JPEG
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
                        jpeg_quality=panel_options.jpeg_quality if selected_format == SaveFormat.JPEG else 95,
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
                        new_image = load_image(filepath)
                        self.canvas.load_image(new_image)
                        self.current_file = filepath
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
        messagebox.showinfo(
            "About StampZ",
            "StampZ\n\n"
            "An image cropping tool and color analysis tool optimized for philatelic images.\n"
            "Supports polygon selection and high-quality output."
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
            self.root.title("StampZ")
            
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
                messagebox.showinfo(
                    "Success",
                    f"Successfully saved {len(coordinates)} sample points to set '{standardized_name}'."
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
            
            sets_listbox = Listbox(listbox_frame, font=("Arial", 11))
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
            
            def on_cancel():
                nonlocal selected_option
                selected_option = None
                dialog.quit()
                dialog.destroy()
            
            # Buttons frame
            buttons_frame = Frame(dialog)
            buttons_frame.pack(pady=10)
            
            Button(buttons_frame, text="View Selected Set", command=on_view_selected, width=15).pack(side="left", padx=5)
            Button(buttons_frame, text="View All Data", command=on_view_all, width=15).pack(side="left", padx=5)
            Button(buttons_frame, text="Cancel", command=on_cancel, width=10).pack(side="left", padx=5)
            
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

    def _analyze_colors(self, print_type="solid"):
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
            from utils.color_analyzer import ColorAnalyzer, PrintType
            # Create analyzer with appropriate print type
            analyzer = ColorAnalyzer(
                print_type=PrintType.LINE_ENGRAVED if print_type == "line" else PrintType.SOLID_PRINTED
            )
            
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
            
            if hasattr(sys, '_MEIPASS'):
                # Running in PyInstaller bundle - use user data directory
                if sys.platform.startswith('linux'):
                    user_data_dir = os.path.expanduser('~/.local/share/StampZ')
                elif sys.platform == 'darwin':
                    user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ')
                else:
                    user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ')
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
