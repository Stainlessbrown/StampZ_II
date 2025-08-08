#!/usr/bin/env python3
"""
Color Comparison Manager for StampZ
Provides interface for comparing sample colors with library colors.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Tuple, Dict, Any
import os
from PIL import Image, ImageTk

# Add project root to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.color_library import ColorLibrary, LibraryColor
from .color_display import ColorDisplay

class ColorComparisonManager(tk.Frame):
    """Manages color comparison interface and functionality."""
    
    # Minimum dimensions and proportions
    MIN_WIDTH = 1200        # Minimum window width
    MIN_HEIGHT = 600        # Minimum window height
    IDEAL_WIDTH = 2000      # Ideal window width for scaling calculations
    
    # Proportions (as percentages of window size)
    TOP_HEIGHT_RATIO = 0.35       # Reduced top section height
    BOTTOM_HEIGHT_RATIO = 0.65    # Increased bottom section height
    SWATCH_WIDTH_RATIO = 0.225    # 450/2000
    HEADER_HEIGHT_RATIO = 0.0625   # 50/800
    
    # Fixed aspect ratios
    SWATCH_ASPECT_RATIO = 450/60    # Width to height ratio for normal swatches (adjusted to 60px height)
    AVG_SWATCH_ASPECT_RATIO = 450/375  # Width to height ratio for average swatch
    
    # Minimum padding (will scale up with window size)
    MIN_PADDING = 10
    
    def __init__(self, parent: tk.Widget):
        """Initialize the color comparison manager.
        
        Args:
            parent: Parent widget (typically a notebook tab)
        """
        super().__init__(parent)
        
        # Initialize instance variables
        self.parent = parent
        self.library = None
        self.current_image = None
        self.sample_points = []
        self.delta_e_threshold = 15.0  # Increased threshold for testing
        
        # Initialize current sizes dictionary
        self.current_sizes = {
            'padding': self.MIN_PADDING  # Start with minimum padding
        }
        
        # Set minimum window size
        if isinstance(parent.winfo_toplevel(), tk.Tk):
            parent.winfo_toplevel().minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        
        # Configure for expansion
        self.configure(width=self.IDEAL_WIDTH)
        self.pack(fill=tk.BOTH, expand=True)
        
        # Create the layout
        self._create_layout()
        
        # Bind resize event
        self.bind('<Configure>', self._on_resize)
        
        # Initial size calculation
        self._update_sizes()
        
        # Load available libraries after UI is created
        self._load_available_libraries()
    
    def _create_layout(self):
        """Create the main layout with proportional dimensions."""
        # Configure main grid with weights for proper scaling
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, minsize=50)     # Header - fixed height
        self.grid_rowconfigure(1, minsize=375)    # Top section - height of average swatch
        self.grid_rowconfigure(2, weight=1)       # Bottom section - takes remaining space
        
        # Create header frame (filename display)
        self._create_header()
        
        # Create top frame (samples and average)
        self._create_top_section()
        
        # Create bottom frame (library selection and matches)
        self._create_bottom_section()
    
    def _create_header(self):
        """Create the header section with filename display."""
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky='ew', padx=self.current_sizes['padding'])
        
        self.filename_label = ttk.Label(header_frame, text="No file loaded", 
                                       font=("Arial", 12))
        self.filename_label.pack(side=tk.LEFT, padx=self.current_sizes['padding'])
    
    def _create_top_section(self):
        """Create the top section with samples and average display."""
        top_frame = ttk.Frame(self)
        top_frame.grid(row=1, column=0, sticky='nsew')
        
        # Configure columns for 50/50 split
        top_frame.grid_columnconfigure(0, weight=1)  # Left side
        top_frame.grid_columnconfigure(1, weight=1)  # Right side
        
        # Left frame - Sample data and swatches
        self.samples_frame = ttk.LabelFrame(top_frame, text="Sample Data")
        self.samples_frame.grid(row=0, column=0, sticky='nsew', padx=self.current_sizes['padding'])
        self.samples_frame.grid_propagate(False)
        
        # Right frame - Average display
        self.average_frame = ttk.LabelFrame(top_frame, text="Average Color")
        self.average_frame.grid(row=0, column=1, sticky='nsew', padx=self.current_sizes['padding'])
        self.average_frame.grid_propagate(False)
    
    def _create_bottom_section(self):
        """Create the bottom section with library selection and matches."""
        bottom_frame = ttk.Frame(self)
        bottom_frame.grid(row=2, column=0, sticky='nsew')
        
        # Use grid for precise positioning in bottom frame
        bottom_frame.grid_columnconfigure(0, weight=1)  # Center horizontally
        bottom_frame.grid_columnconfigure(1, weight=1)  # Center horizontally
        bottom_frame.grid_columnconfigure(2, weight=1)  # Center horizontally
        bottom_frame.grid_rowconfigure(1, weight=1)  # Give weight to matches frame
        
        # Library selection bar - at top with minimal padding
        selection_frame = ttk.Frame(bottom_frame)
        selection_frame.grid(row=0, column=1, sticky='ew', padx=self.current_sizes['padding'], pady=5)
        
        # Library dropdown
        ttk.Label(selection_frame, text="Compare with:").pack(side=tk.LEFT)
        self.library_var = tk.StringVar(value="Select Library")
        self.library_combo = ttk.Combobox(selection_frame, textvariable=self.library_var, width=30)
        self.library_combo.pack(side=tk.LEFT, padx=self.current_sizes['padding'])
        self.library_combo.bind('<<ComboboxSelected>>', self._on_library_selected)
        
        # Compare button
        self.compare_button = ttk.Button(selection_frame, text="Compare", command=self._compare_color)
        self.compare_button.pack(side=tk.LEFT, padx=self.current_sizes['padding'])
        
        # Delta E threshold display
        ttk.Label(selection_frame, 
                 text=f"ΔE ≤ {self.delta_e_threshold}",
                 font=("Arial", 12)).pack(side=tk.RIGHT)
        
        # Matches frame
        self.matches_frame = ttk.LabelFrame(bottom_frame, text="Closest Matches")
        self.matches_frame.grid(row=1, column=0, columnspan=3, sticky='nsew', padx=self.current_sizes['padding'], pady=5)
        self.matches_frame.grid_propagate(False)  # Maintain fixed size
    
    def _on_resize(self, event=None):
        """Handle window resize events to maintain proportions."""
        if event and event.widget == self:
            self._update_sizes()
    
    def _update_sizes(self):
        """Update all component sizes based on current window dimensions."""
        # Get current window size
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Calculate new dimensions maintaining proportions
        scale_factor = min(width / self.IDEAL_WIDTH, height / (self.MIN_HEIGHT * 1.5))
        
        # Calculate new sizes
        new_swatch_width = int(self.IDEAL_WIDTH * self.SWATCH_WIDTH_RATIO * scale_factor)
        new_swatch_height = int(new_swatch_width / self.SWATCH_ASPECT_RATIO)
        new_avg_swatch_height = int(new_swatch_width / self.AVG_SWATCH_ASPECT_RATIO)
        new_padding = int(self.MIN_PADDING * scale_factor)
        
        # Store current sizes for use in other methods
        self.current_sizes = {
            'swatch_width': new_swatch_width,
            'swatch_height': new_swatch_height,
            'avg_swatch_height': new_avg_swatch_height,
            'padding': new_padding
        }
        
        # Update frame sizes
        if hasattr(self, 'samples_frame'):
            self.samples_frame.configure(width=new_swatch_width + 2 * new_padding)
        if hasattr(self, 'average_frame'):
            self.average_frame.configure(width=new_swatch_width + 2 * new_padding)
        if hasattr(self, 'matches_frame'):
            self.matches_frame.configure(width=width - 2 * new_padding)
    
    def set_analyzed_data(self, image_path: str, sample_data: List[Dict]):
        """Set the analyzed image path and sample data.
        
        Args:
            image_path: Path to the image file
            sample_data: List of dictionaries containing sample information
                Each dict should have:
                - position: (x, y) tuple
                - type: 'circle' or 'rectangle'
                - size: (width, height) tuple
                - anchor: anchor position string
        """
        try:
            print(f"DEBUG: Setting analyzed data with {len(sample_data)} samples")
            
            # Update filename display
            filename = os.path.basename(image_path)
            self.filename_label.config(text=filename)
            print(f"DEBUG: Updated filename display: {filename}")
            
            # Load the image (needed for color sampling)
            self.current_image = Image.open(image_path)
            
            # Create color analyzer
            from utils.color_analyzer import ColorAnalyzer
            analyzer = ColorAnalyzer()
            
            # Process each sample
            self.sample_points = []
            
            for i, sample in enumerate(sample_data, 1):
                try:
                    print(f"DEBUG: Processing sample {i}")
                    # Create a temporary coordinate point for sampling
                    from utils.coordinate_db import SampleAreaType
                    
                    class TempCoord:
                        def __init__(self, x, y, sample_type, size, anchor):
                            self.x = x
                            self.y = y
                            self.sample_type = SampleAreaType.CIRCLE if sample_type == 'circle' else SampleAreaType.RECTANGLE
                            self.sample_size = size
                            self.anchor_position = anchor
                    
                    # Extract position and parameters
                    x, y = sample['position']
                    temp_coord = TempCoord(
                        x=x,
                        y=y,
                        sample_type=sample['type'],
                        size=sample['size'],
                        anchor=sample['anchor']
                    )
                    
                    # Sample the color
                    rgb_values = analyzer._sample_area_color(self.current_image, temp_coord)
                    if rgb_values:
                        avg_rgb = analyzer._calculate_average_color(rgb_values)
                        
                        # Store the sample point data
                        sample_point = {
                            'rgb': avg_rgb,
                            'position': (x, y),
                            'enabled': tk.BooleanVar(value=True),
                            'index': i,
                            'type': sample['type'],
                            'size': sample['size'],
                            'anchor': sample['anchor']
                        }
                        self.sample_points.append(sample_point)
                        print(f"DEBUG: Added sample {i} with RGB: {avg_rgb}, enabled: {sample_point['enabled'].get()}")
                except Exception as e:
                    print(f"DEBUG: Error processing sample {i}: {str(e)}")
                    continue
            
            print(f"DEBUG: Processed {len(self.sample_points)} sample points")
            
            # Update the display
            self._display_sample_points()
            self._update_average_display()
            
        except Exception as e:
            print(f"DEBUG: Error in set_analyzed_data: {str(e)}")
            messagebox.showerror(
                "Analysis Error",
                f"Failed to analyze sample points:\n\n{str(e)}"
            )
    
    def _display_sample_points(self):
        """Display sample points with their color values and swatches."""
        # Clear existing samples
        for widget in self.samples_frame.winfo_children():
            widget.destroy()
        
        # Display each sample point
        for sample in self.sample_points:
            frame = ttk.Frame(self.samples_frame)
            frame.pack(fill=tk.X, pady=5)
            
            # Sample toggle
            ttk.Checkbutton(frame, 
                          text=f"Sample {sample['index']}",
                          variable=sample['enabled'],
                          command=self._on_sample_toggle).pack(side=tk.LEFT)
            
            # Color values
            rgb = sample['rgb']
            lab = self.library.rgb_to_lab(rgb) if self.library else None
            
            if lab:
                value_text = (f"L*: {lab[0]:>6.1f}  a*: {lab[1]:>6.1f}  b*: {lab[2]:>6.1f}\n" +
                             f"R: {int(rgb[0]):>3}  G: {int(rgb[1]):>3}  B: {int(rgb[2]):>3}")
            else:
                value_text = f"R: {int(rgb[0]):>3}  G: {int(rgb[1]):>3}  B: {int(rgb[2]):>3}"
            
            ttk.Label(frame, text=value_text, font=("Arial", 12)).pack(side=tk.LEFT, padx=20)
            
            # Color swatch using canvas
            canvas = tk.Canvas(
                frame,
                width=450,
                height=60,
                highlightthickness=1,
                highlightbackground='gray'
            )
            canvas.pack(side=tk.RIGHT, padx=5, pady=2)
            
            # Create rectangle for color display
            canvas.create_rectangle(
                0, 0, 450, 60,
                fill=f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}",
                outline=''
            )
    
    def _update_average_display(self):
        """Update the average color display."""
        # Clear existing display
        for widget in self.average_frame.winfo_children():
            widget.destroy()
        
        # Get enabled samples
        enabled_samples = [s for s in self.sample_points if s['enabled'].get()]
        
        if not enabled_samples:
            ttk.Label(self.average_frame, text="No samples enabled").pack(pady=20)
            return
        
        # Calculate average RGB
        total_r = sum(s['rgb'][0] for s in enabled_samples)
        total_g = sum(s['rgb'][1] for s in enabled_samples)
        total_b = sum(s['rgb'][2] for s in enabled_samples)
        count = len(enabled_samples)
        
        avg_rgb = (total_r/count, total_g/count, total_b/count)
        avg_lab = self.library.rgb_to_lab(avg_rgb) if self.library else None
        
        # Create display frame
        frame = ttk.Frame(self.average_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=5)  # Remove left padding
        
        # Average color swatch using canvas
        canvas = tk.Canvas(
            frame,
            width=450,
            height=360,
            highlightthickness=1,
            highlightbackground='gray'
        )
        canvas.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Create rectangle for color display
        canvas.create_rectangle(
            0, 0, 450, 360,
            fill=f"#{int(avg_rgb[0]):02x}{int(avg_rgb[1]):02x}{int(avg_rgb[2]):02x}",
            outline=''
        )
        
        # Color values
        if avg_lab:
            value_text = (f"L*: {avg_lab[0]:>6.1f}  a*: {avg_lab[1]:>6.1f}  b*: {avg_lab[2]:>6.1f}\n" +
                         f"R: {int(avg_rgb[0]):>3}  G: {int(avg_rgb[1]):>3}  B: {int(avg_rgb[2]):>3}")
        else:
            value_text = f"R: {int(avg_rgb[0]):>3}  G: {int(avg_rgb[1]):>3}  B: {int(avg_rgb[2]):>3}"
        
        # Create a frame for values and button
        values_frame = ttk.Frame(frame)
        values_frame.pack(side=tk.LEFT, padx=20, fill=tk.Y)
        
        # Add color values
        ttk.Label(values_frame, text=value_text, font=("Arial", 12)).pack(anchor='w')
        
        # Add some vertical space
        ttk.Frame(values_frame, height=20).pack()
        
        # Add the button at the bottom right of values_frame
        add_button = ttk.Button(values_frame, text="Add color to library", 
                              command=lambda: self._add_color_to_library(avg_rgb, avg_lab))
        add_button.pack(anchor='se')
    
    def _add_color_to_library(self, rgb_values, lab_values):
        """Handle adding the current average color to a library."""
        if not rgb_values or not lab_values:
            messagebox.showerror("Error", "No color data available to add")
            return
            
        # Create a dialog for color name and library selection
        dialog = tk.Toplevel(self)
        dialog.title("Add Color to Library")
        dialog.transient(self)  # Make dialog modal
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("400x200")
        
        # Color name entry
        name_frame = ttk.Frame(dialog, padding="10")
        name_frame.pack(fill=tk.X)
        ttk.Label(name_frame, text="Color name:").pack(side=tk.LEFT)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=30)
        name_entry.pack(side=tk.LEFT, padx=5)
        
        # Library selection
        lib_frame = ttk.Frame(dialog, padding="10")
        lib_frame.pack(fill=tk.X)
        ttk.Label(lib_frame, text="Select library:").pack(side=tk.LEFT)
        
        # Load available libraries similar to Sample mode
        self._load_available_libraries()
        library_list = self.library_combo['values'][1:]  # Exclude 'All Libraries' option
        
        lib_var = tk.StringVar()
        lib_combo = ttk.Combobox(lib_frame, textvariable=lib_var, values=library_list, width=27)
        lib_combo.pack(side=tk.LEFT, padx=5)
        
        # Preview frame showing the color
        preview_frame = ttk.Frame(dialog, padding="10")
        preview_frame.pack(fill=tk.X)
        ttk.Label(preview_frame, text="Color preview:").pack(side=tk.LEFT)
        
        # Color preview swatch
        preview_canvas = tk.Canvas(preview_frame, width=100, height=30,
                                highlightthickness=1, highlightbackground='gray')
        preview_canvas.pack(side=tk.LEFT, padx=5)
        preview_canvas.create_rectangle(
            0, 0, 100, 30,
            fill=f"#{int(rgb_values[0]):02x}{int(rgb_values[1]):02x}{int(rgb_values[2]):02x}",
            outline=''
        )
        
        def save_color():
            name = name_var.get().strip()
            library = lib_var.get()
            
            print(f"DEBUG: Compare Add Color - name='{name}', library='{library}'")
            print(f"DEBUG: Compare Add Color - rgb_values={rgb_values}, lab_values={lab_values}")
            
            if not name:
                messagebox.showerror("Error", "Please enter a color name")
                return
            if not library:
                messagebox.showerror("Error", "Please select a library")
                return
                
            try:
                # Load the selected library
                print(f"DEBUG: Creating ColorLibrary instance with name: {library}")
                color_lib = ColorLibrary(library)
                
                print(f"DEBUG: ColorLibrary created with db_path: {color_lib.db_path}")
                
                # Add the new color with keyword arguments
                print(f"DEBUG: Calling add_color with name={name}, rgb={rgb_values}, lab={lab_values}")
                success = color_lib.add_color(name=name, rgb=rgb_values, lab=lab_values)
                
                print(f"DEBUG: add_color returned: {success}")
                
                if success:
                    # Verify the color was actually added
                    added_color = color_lib.get_color_by_name(name)
                    print(f"DEBUG: Verification - color retrieved: {added_color is not None}")
                    if added_color:
                        print(f"DEBUG: Retrieved color: {added_color.name}, {added_color.lab}")
                    
                    messagebox.showinfo("Success", f"Color '{name}' added to library '{library}'")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", f"Failed to add color '{name}' to library '{library}'")
                
            except Exception as e:
                print(f"DEBUG: Exception in save_color: {str(e)}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Error", f"Failed to add color: {str(e)}")
        
        # Buttons frame
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="Save", command=save_color).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Focus the name entry
        name_entry.focus_set()
    
    def _on_sample_toggle(self):
        """Handle sample toggle event."""
        self._update_average_display()
    
    def _load_available_libraries(self):
        """Load available color libraries and populate dropdown."""
        try:
            # Use the same logic as main.py to find libraries
            library_files = set()  # Use set to avoid duplicates
            
            # Get directories to check
            library_dirs = self._get_library_directories()
            
            for library_dir in library_dirs:
                print(f"DEBUG: Looking for libraries in: {library_dir}")
                
                if not os.path.exists(library_dir):
                    print(f"DEBUG: Library directory does not exist: {library_dir}")
                    continue
                
                # Get list of all files in directory for debugging
                all_files = os.listdir(library_dir)
                print(f"DEBUG: All files in library directory: {all_files}")
                
                # Get list of library files
                for f in all_files:
                    if f.endswith("_library.db") and not f.lower().startswith("all_libraries"):
                        library_name = f[:-11]  # Remove '_library.db' suffix
                        library_files.add(library_name)
                        print(f"DEBUG: Found library: {library_name} in {library_dir}")
            
            # Convert to sorted list
            library_list = sorted(list(library_files))
            print(f"DEBUG: Found {len(library_list)} total libraries: {library_list}")
            
            # Add 'All Libraries' option at the top
            self.library_combo['values'] = ['All Libraries'] + library_list
            print(f"DEBUG: Set combo values to: {self.library_combo['values']}")
            
        except Exception as e:
            print(f"Error loading libraries: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                "Library Error",
                f"Failed to load color libraries:\n\n{str(e)}"
            )
    
    def _get_library_directories(self):
        """Get list of directories to check for color libraries.
        
        Returns:
            List of directory paths to search for libraries
        """
        directories = []
        
        # Check if running as PyInstaller bundle
        if hasattr(sys, '_MEIPASS'):
            # Running in PyInstaller bundle - use user data directory
            if sys.platform.startswith('linux'):
                user_data_dir = os.path.expanduser('~/.local/share/StampZ')
            elif sys.platform == 'darwin':
                user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ')
            else:
                user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ')
            directories.append(os.path.join(user_data_dir, "data", "color_libraries"))
            
            # Also check bundled libraries
            bundled_dir = os.path.join(sys._MEIPASS, "data", "color_libraries")
            directories.append(bundled_dir)
        else:
            # Running from source - use relative path
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            directories.append(os.path.join(current_dir, "data", "color_libraries"))
            
            # Also check user data directory in case libraries were added while running from source
            if sys.platform.startswith('linux'):
                user_data_dir = os.path.expanduser('~/.local/share/StampZ')
            elif sys.platform == 'darwin':
                user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ')
            else:
                user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ')
            directories.append(os.path.join(user_data_dir, "data", "color_libraries"))
        
        return directories
    
    def _on_library_selected(self, event=None):
        """Handle library selection change."""
        library_name = self.library_var.get()
        if not library_name or library_name == "Select Library":
            return
        
        try:
            print(f"Loading library: {library_name}")
            
            if library_name == "All Libraries":
                # Get list of all library files from all directories
                library_files = set()
                library_dirs = self._get_library_directories()
                
                for library_dir in library_dirs:
                    if os.path.exists(library_dir):
                        for f in os.listdir(library_dir):
                            if f.endswith("_library.db") and not f.lower().startswith("all_libraries"):
                                library_name_clean = f[:-11]
                                library_files.add(library_name_clean)
                
                library_list = sorted(list(library_files))
                print(f"Found libraries for 'All Libraries': {library_list}")
                
                if library_list:
                    # Load the first library as primary
                    self.library = ColorLibrary(library_list[0])
                    
                    # Load all libraries for comparison
                    self.all_libraries = [ColorLibrary(lib) for lib in library_list]
                    print(f"Loaded {len(self.all_libraries)} libraries for comparison")
                else:
                    print("No libraries found for 'All Libraries' option")
                    self.library = None
                    self.all_libraries = []
            else:
                self.library = ColorLibrary(library_name)
                self.all_libraries = None
            
            # Update display if we have samples
            if self.sample_points:
                self._display_sample_points()
                self._update_average_display()
            
        except Exception as e:
            print(f"Error selecting library: {str(e)}")
            messagebox.showerror(
                "Library Error",
                f"Failed to load library '{library_name}':\n\n{str(e)}"
            )
    
    def _compare_color(self):
        """Compare the average color to the selected library."""
        if not self.library:
            messagebox.showerror("Error", "Please select a library first")
            return
        
        # Get average color
        enabled_samples = [s for s in self.sample_points if s['enabled'].get()]
        if not enabled_samples:
            messagebox.showinfo("No Data", "Please enable at least one sample point for comparison.")
            return
        
        # Calculate average RGB
        total_r = sum(s['rgb'][0] for s in enabled_samples)
        total_g = sum(s['rgb'][1] for s in enabled_samples)
        total_b = sum(s['rgb'][2] for s in enabled_samples)
        count = len(enabled_samples)
        
        avg_rgb = (total_r/count, total_g/count, total_b/count)
        avg_lab = self.library.rgb_to_lab(avg_rgb)
        
        # Compare with library
        library_name = self.library_var.get()
        print(f"Comparing with {library_name}")
        
        # Clear previous matches
        for widget in self.matches_frame.winfo_children():
            widget.destroy()
        
        try:
            if library_name == "All Libraries" and hasattr(self, 'all_libraries'):
                # Combine results from all libraries
                all_matches = []
                for lib in self.all_libraries:
                    result = lib.compare_sample_to_library(
                        sample_lab=avg_lab,
                        threshold=self.delta_e_threshold
                    )
                    if result and 'matches' in result:
                        all_matches.extend(result['matches'])
                
                # Sort combined matches by delta_e
                all_matches.sort(key=lambda x: x.delta_e_2000)
                matches = all_matches[:5]  # Take top 5
            else:
                # Compare with single library
                result = self.library.compare_sample_to_library(
                    sample_lab=avg_lab,
                    threshold=self.delta_e_threshold
                )
                matches = result.get('matches', [])[:5] if result else []
            
            if not matches:
                ttk.Label(self.matches_frame,
                         text=f"No matches found within ΔE threshold of {self.delta_e_threshold}",
                         font=("Arial", 12)).pack(pady=20)
                return
            
            # Display matches
            for match in matches:
                # Container frame for centering
                container = ttk.Frame(self.matches_frame)
                container.pack(fill=tk.X, pady=2)
                container.grid_columnconfigure(0, weight=1)  # Center content
                
                # Inner frame for match content
                frame = ttk.Frame(container)
                frame.grid(row=0, column=0)  # Will be centered due to container's weight
                
                # Color values with ΔE
                lab = match.library_color.lab
                rgb = match.library_color.rgb
                value_text = (f"L*: {lab[0]:>6.1f}  a*: {lab[1]:>6.1f}  b*: {lab[2]:>6.1f}    ΔE: {match.delta_e_2000:>6.2f}\n" +
                             f"R: {int(rgb[0]):>3}  G: {int(rgb[1]):>3}  B: {int(rgb[2]):>3}    {match.library_color.name}")
                
                ttk.Label(frame, text=value_text, font=("Arial", 12)).pack(side=tk.LEFT, padx=20)
                
                # Color swatch
                canvas = tk.Canvas(
                    frame,
                    width=450,
                    height=60,
                    highlightthickness=1,
                    highlightbackground='gray'
                )
                canvas.pack(side=tk.RIGHT, padx=(5, 10), pady=2)  # Added right padding for centering
                
                # Create rectangle for color display
                canvas.create_rectangle(
                    0, 0, 450, 60,
                    fill=f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}",
                    outline=''
                )
                
        except Exception as e:
            print(f"Error in color comparison: {str(e)}")
            messagebox.showerror(
                "Comparison Error",
                f"Failed to compare colors:\n\n{str(e)}"
            )
