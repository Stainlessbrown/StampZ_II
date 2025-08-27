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
        
        # Calculate new sizes - increase base swatch width for comparison view
        base_swatch_width = max(500, int(self.IDEAL_WIDTH * self.SWATCH_WIDTH_RATIO * scale_factor))
        new_swatch_width = base_swatch_width
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
            # Make matches frame use more of the available width
            self.matches_frame.configure(width=max(width - 2 * new_padding, 1200))
    
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
        
        # Calculate average color for ΔE comparisons
        enabled_samples = [s for s in self.sample_points if s['enabled'].get()]
        average_lab = None
        
        if enabled_samples and self.library:
            from utils.color_analyzer import ColorAnalyzer
            analyzer = ColorAnalyzer()
            
            lab_values = []
            rgb_values = []
            for sample in enabled_samples:
                rgb = sample['rgb']
                lab = self.library.rgb_to_lab(rgb) if self.library else analyzer.rgb_to_lab(rgb)
                lab_values.append(lab)
                rgb_values.append(rgb)
            
            if lab_values:
                # Calculate quality-controlled average for ΔE comparison
                averaging_result = analyzer._calculate_quality_controlled_average(lab_values, rgb_values)
                average_lab = averaging_result['avg_lab']
        
        # Display each sample point
        for sample in self.sample_points:
            frame = ttk.Frame(self.samples_frame)
            frame.pack(fill=tk.X, pady=5)
            
            # Sample toggle
            ttk.Checkbutton(frame, 
                          text=f"Sample {sample['index']}",
                          variable=sample['enabled'],
                          command=self._on_sample_toggle).pack(side=tk.LEFT)
            
            # Color values with ΔE from average
            rgb = sample['rgb']
            lab = self.library.rgb_to_lab(rgb) if self.library else None
            
            # Use conditional color display based on user preferences
            from utils.color_display_utils import get_conditional_color_values_text
            value_text = get_conditional_color_values_text(rgb, lab, compact=True)
            
            # Add ΔE from average if we have both values
            if lab and average_lab and sample['enabled'].get():
                from utils.color_analyzer import ColorAnalyzer
                analyzer = ColorAnalyzer()
                delta_e = analyzer.calculate_delta_e(lab, average_lab)
                value_text += f"\nΔE from avg: {delta_e:.2f}"
            
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
        
        # Use ColorAnalyzer for quality-controlled averaging with ΔE outlier detection
        from utils.color_analyzer import ColorAnalyzer
        analyzer = ColorAnalyzer()
        
        # Convert samples to Lab and RGB lists for quality averaging
        lab_values = []
        rgb_values = []
        for sample in enabled_samples:
            rgb = sample['rgb']
            lab = self.library.rgb_to_lab(rgb) if self.library else analyzer.rgb_to_lab(rgb)
            lab_values.append(lab)
            rgb_values.append(rgb)
        
        # Calculate quality-controlled average with ΔE outlier detection
        averaging_result = analyzer._calculate_quality_controlled_average(lab_values, rgb_values)
        
        avg_rgb = averaging_result['avg_rgb']
        avg_lab = averaging_result['avg_lab']
        max_delta_e = averaging_result['max_delta_e']
        samples_used = averaging_result['samples_used']
        outliers_excluded = averaging_result['outliers_excluded']
        
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
        
        # Color values based on user preferences
        from utils.color_display_utils import get_conditional_color_values_text
        value_text = get_conditional_color_values_text(avg_rgb, avg_lab, compact=True)
        
        # Create a frame for values and button
        values_frame = ttk.Frame(frame)
        values_frame.pack(side=tk.LEFT, padx=20, fill=tk.Y)
        
        # Add color values
        ttk.Label(values_frame, text=value_text, font=("Arial", 12)).pack(anchor='w')
        
        # Add quality metrics with ΔE information
        quality_text = f"Quality: ΔE max {max_delta_e:.2f}, {samples_used}/{len(enabled_samples)} samples used"
        if outliers_excluded > 0:
            quality_text += f", {outliers_excluded} outliers excluded"
        
        ttk.Label(values_frame, text=quality_text, font=("Arial", 10), foreground="#666666").pack(anchor='w', pady=(5, 0))
        
        # Add some vertical space
        ttk.Frame(values_frame, height=15).pack()
        
        # Add the button at the bottom right of values_frame
        add_button = ttk.Button(values_frame, text="Add color to library", 
                              command=lambda: self._add_color_to_library(avg_rgb, avg_lab))
        add_button.pack(anchor='se', pady=(0, 5))
        
        # Add Save Average to Database button
        save_button = ttk.Button(values_frame, text="Save Average to Database", 
                               command=lambda: self._save_average_to_database(avg_rgb, avg_lab, enabled_samples))
        save_button.pack(anchor='se')
    
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
                    
                    # Refresh the library display if the main library window is open
                    self._refresh_library_manager(library)
                    
                    messagebox.showinfo("Success", f"Color '{name}' added to library '{library}'\n\nNote: If the Library window is open, you may need to\nclose and reopen it to see the new color.")
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
    
    def _save_average_to_database(self, avg_rgb, avg_lab, enabled_samples):
        """Save the averaged color data to the database for export.
        
        Args:
            avg_rgb: Averaged RGB values
            avg_lab: Averaged Lab values
            enabled_samples: List of enabled sample points used for averaging
        """
        print(f"DEBUG: _save_average_to_database called")
        print(f"DEBUG: avg_rgb={avg_rgb}, avg_lab={avg_lab}")
        print(f"DEBUG: enabled_samples count={len(enabled_samples)}")
        
        try:
            if not enabled_samples:
                messagebox.showerror("Error", "No samples enabled for averaging")
                return
            
            # Check if we have a current image loaded
            if not self.current_image or not hasattr(self, 'filename_label'):
                messagebox.showerror("Error", "No image data available")
                return
            
            # Get image name from the filename label
            filename = self.filename_label.cget("text")
            if filename == "No file loaded":
                messagebox.showerror("Error", "No file loaded")
                return
            
            image_name = os.path.splitext(filename)[0]
            print(f"DEBUG: Extracted image_name: '{image_name}'")
            
            # Find which database contains individual measurements for this image
            sample_set_name = self._find_database_for_image(image_name)
            if not sample_set_name:
                # Fall back to Compare_* naming if no existing database found
                sample_set_name = f"Compare_{image_name}"
                print(f"DEBUG: No existing database found, using fallback: '{sample_set_name}'")
            else:
                print(f"DEBUG: Found existing database: '{sample_set_name}' for image '{image_name}'")
            
            # Convert enabled samples to the format expected by ColorAnalyzer
            sample_measurements = []
            for i, sample in enumerate(enabled_samples, 1):
                measurement = {
                    'id': f"compare_{i}",
                    'l_value': self.library.rgb_to_lab(sample['rgb'])[0] if self.library else 0,
                    'a_value': self.library.rgb_to_lab(sample['rgb'])[1] if self.library else 0,
                    'b_value': self.library.rgb_to_lab(sample['rgb'])[2] if self.library else 0,
                    'rgb_r': sample['rgb'][0],
                    'rgb_g': sample['rgb'][1],
                    'rgb_b': sample['rgb'][2],
                    'x_position': sample['position'][0],
                    'y_position': sample['position'][1],
                    'sample_type': sample['type'],
                    'sample_width': sample['size'][0],
                    'sample_height': sample['size'][1],
                    'anchor': sample['anchor']
                }
                sample_measurements.append(measurement)
            
            # Use ColorAnalyzer to save the averaged measurement
            from utils.color_analyzer import ColorAnalyzer
            analyzer = ColorAnalyzer()
            
            notes = f"Compare mode average from {len(enabled_samples)} enabled samples"
            success = analyzer.save_averaged_measurement_from_samples(
                sample_measurements=sample_measurements,
                sample_set_name=sample_set_name,
                image_name=image_name,
                notes=notes
            )
            
            if success:
                messagebox.showinfo(
                    "Success",
                    f"Successfully saved averaged color data to database!\n\n"
                    f"Sample Set: {sample_set_name}\n"
                    f"Image: {image_name}\n"
                    f"Averaged from {len(enabled_samples)} samples\n\n"
                    f"This data will now be included in exports."
                )
            else:
                messagebox.showerror(
                    "Error",
                    "Failed to save averaged color data to database."
                )
                
        except Exception as e:
            print(f"Error saving averaged measurement: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                "Error",
                f"Failed to save averaged color data:\n\n{str(e)}"
            )
    
    def _find_database_for_image(self, image_name: str) -> str:
        """Find which database contains individual measurements for the given image name.
        
        Args:
            image_name: The image name to search for (e.g., 'F137-S35')
            
        Returns:
            Sample set name (database name) that contains individual measurements for this image,
            or None if not found
        """
        # Create debug log file in user's home directory
        import os
        from datetime import datetime
        debug_log = os.path.expanduser('~/StampZ_Compare_Debug.log')
        
        def log_debug(message):
            try:
                with open(debug_log, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] {message}\n")
            except:
                pass
        
        log_debug(f"=== _find_database_for_image called for '{image_name}' ===")
        
        try:
            import os
            from utils.color_analysis_db import ColorAnalysisDB
            
            # Try multiple possible database directories
            possible_dirs = [
                'data/color_analysis',  # Development relative path
                os.path.join(os.path.expanduser('~/Library/Application Support/StampZ_II'), 'data', 'color_analysis'),  # macOS app support
                os.path.join(os.getenv('STAMPZ_DATA_DIR', ''), 'data', 'color_analysis') if os.getenv('STAMPZ_DATA_DIR') else None
            ]
            
            # Filter out None values
            possible_dirs = [d for d in possible_dirs if d]
            
            log_debug(f"Checking directories: {possible_dirs}")
            
            db_dir = None
            for test_dir in possible_dirs:
                if os.path.exists(test_dir):
                    db_dir = test_dir
                    log_debug(f"Found existing directory: {db_dir}")
                    break
                else:
                    log_debug(f"Directory not found: {test_dir}")
            
            if not db_dir:
                log_debug("No database directory found")
                return None
                
            db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
            log_debug(f"Database files found: {db_files}")
            
            # Check each database for individual measurements with this image name
            for db_file in db_files:
                try:
                    sample_set_name = os.path.splitext(db_file)[0]
                    log_debug(f"Checking database: {sample_set_name}")
                    
                    db = ColorAnalysisDB(sample_set_name)
                    all_measurements = db.get_all_measurements()
                    log_debug(f"  Total measurements: {len(all_measurements)}")
                    
                    # Look for individual measurements (not averaged) with this image name
                    # Try both exact match and partial match (database might store base name like 'S1' while we search for '138-S1-crp_1')
                    individual_measurements = []
                    for m in all_measurements:
                        if m.get('is_averaged', False):  # Skip averaged measurements
                            continue
                        
                        stored_name = m.get('image_name', '')
                        # Try exact match first
                        if stored_name == image_name:
                            individual_measurements.append(m)
                        # Try partial match (stored name is contained in search name)
                        elif stored_name and stored_name in image_name:
                            individual_measurements.append(m)
                        # Try reverse partial match (search name is contained in stored name)
                        elif image_name and image_name in stored_name:
                            individual_measurements.append(m)
                    
                    log_debug(f"  Individual measurements for '{image_name}': {len(individual_measurements)}")
                    
                    if individual_measurements:
                        log_debug(f"SUCCESS: Found {len(individual_measurements)} individual measurements for image '{image_name}' in database '{sample_set_name}'")
                        print(f"DEBUG: Found {len(individual_measurements)} individual measurements for image '{image_name}' in database '{sample_set_name}'")
                        return sample_set_name
                        
                except Exception as e:
                    log_debug(f"  Error checking database {db_file}: {e}")
                    print(f"DEBUG: Error checking database {db_file}: {e}")
                    continue
            
            log_debug(f"FAILURE: No database found containing individual measurements for image '{image_name}'")
            print(f"DEBUG: No database found containing individual measurements for image '{image_name}'")
            return None
            
        except Exception as e:
            log_debug(f"ERROR in _find_database_for_image: {e}")
            print(f"DEBUG: Error in _find_database_for_image: {e}")
            return None
    
    def _refresh_library_manager(self, library_name: str):
        """Refresh the library manager display if it's open.
        
        Args:
            library_name: Name of the library that was updated
        """
        try:
            # Try to find the main app through the widget hierarchy
            widget = self
            main_app = None
            
            # Navigate up the widget hierarchy to find main app
            while widget:
                if hasattr(widget, 'main_app'):
                    main_app = widget.main_app
                    break
                elif hasattr(widget, 'master'):
                    widget = widget.master
                    if hasattr(widget, 'main_app'):
                        main_app = widget.main_app
                        break
                else:
                    break
            
            # If we found the main app, check if it has an active library manager
            if main_app and hasattr(main_app, '_active_library_manager'):
                lib_manager = main_app._active_library_manager
                if lib_manager and hasattr(lib_manager, 'current_library_name'):
                    # Check if the updated library matches the currently displayed one
                    if lib_manager.current_library_name == library_name:
                        print(f"DEBUG: Refreshing library manager display for {library_name}")
                        
                        # Refresh the display
                        if hasattr(lib_manager, '_update_colors_display'):
                            lib_manager._update_colors_display()
                        
                        # Also update stats
                        if hasattr(lib_manager, '_update_stats'):
                            lib_manager._update_stats()
                        
                        print(f"DEBUG: Successfully refreshed library display")
            
        except Exception as e:
            print(f"DEBUG: Error refreshing library manager: {str(e)}")
            # Don't show error to user as this is just a convenience feature
    
    def _on_sample_toggle(self):
        """Handle sample toggle event."""
        # Update both the average display and the individual sample displays
        # so that ΔE values reflect the new average after sample selection changes
        self._display_sample_points()
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
            
            # Set default library from preferences
            try:
                from utils.user_preferences import get_preferences_manager
                prefs_manager = get_preferences_manager()
                default_library = prefs_manager.get_default_color_library()
                
                # Check if default library exists in our list
                if default_library in library_list:
                    self.library_var.set(default_library)
                    # Automatically load the default library
                    self._on_library_selected()
                    print(f"DEBUG: Set default library to: {default_library}")
                elif library_list:  # Fallback to first library if default not found
                    self.library_var.set(library_list[0])
                    self._on_library_selected()
                    print(f"DEBUG: Default library not found, using: {library_list[0]}")
                else:
                    self.library_var.set("Select Library")
                    print("DEBUG: No libraries available")
            except Exception as e:
                print(f"DEBUG: Error setting default library: {e}")
                # Fallback behavior
                if library_list:
                    self.library_var.set(library_list[0])
                    self._on_library_selected()
                else:
                    self.library_var.set("Select Library")
            
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
        
        # Use the unified path utility for consistency
        from utils.path_utils import get_color_libraries_dir
        
        directories = []
        
        # Check if running as PyInstaller bundle
        if hasattr(sys, '_MEIPASS'):
            # Running in PyInstaller bundle - use user data directory
            if sys.platform.startswith('linux'):
                user_data_dir = os.path.expanduser('~/.local/share/StampZ_II')
            elif sys.platform == 'darwin':
                user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ_II')
            else:
                user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ_II')
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
                user_data_dir = os.path.expanduser('~/.local/share/StampZ_II')
            elif sys.platform == 'darwin':
                user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ_II')
            else:
                user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ_II')
            directories.append(os.path.join(user_data_dir, "data", "color_libraries"))
        
        # Note: Backward compatibility with old StampZ directory has been removed.
        # Users should use the migration feature in Preferences to migrate old data.
        
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
                    # Get matches from this library with library name included
                    lib_matches = lib.find_closest_matches(
                        sample_lab=avg_lab,
                        max_delta_e=self.delta_e_threshold,
                        max_results=5,  # Get more from each library
                        include_library_name=True
                    )
                    # Set the library name for each match
                    for match in lib_matches:
                        match.library_name = lib.library_name
                    all_matches.extend(lib_matches)
                
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
                # Container frame using grid for better structure
                container = ttk.Frame(self.matches_frame)
                container.pack(fill=tk.X, pady=2)
                
                # Configure grid layout - use 3 columns
                container.grid_columnconfigure(0, weight=1)  # Color values - takes available space
                container.grid_columnconfigure(1, weight=0)  # Color name - fixed width
                container.grid_columnconfigure(2, weight=0)  # Color swatch - fixed width
                
                # Color values with ΔE (left-aligned) - split for bold ΔE
                lab = match.library_color.lab
                rgb = match.library_color.rgb
                
                # Create a sub-frame for the values column to hold multiple labels
                values_frame = ttk.Frame(container)
                values_frame.grid(row=0, column=0, padx=(20, 5), pady=2, sticky="w")
                
                # Top row: L*, a*, b* values (normal font)
                lab_text = f"L*: {lab[0]:.1f}  a*: {lab[1]:.1f}  b*: {lab[2]:.1f}    "
                lab_label = ttk.Label(values_frame, text=lab_text, font=("Arial", 12), anchor="w")
                lab_label.grid(row=0, column=0, sticky="w")
                
                # ΔE value (bold font) - placed next to lab values
                delta_e_text = f"ΔE: {match.delta_e_2000:.2f}"
                delta_e_label = ttk.Label(values_frame, text=delta_e_text, font=("Arial", 12, "bold"), anchor="w")
                delta_e_label.grid(row=0, column=1, sticky="w")
                
                # Bottom row: RGB values (normal font)
                rgb_text = f"R: {int(rgb[0])}  G: {int(rgb[1])}  B: {int(rgb[2])}"
                rgb_label = ttk.Label(values_frame, text=rgb_text, font=("Arial", 12), anchor="w")
                rgb_label.grid(row=1, column=0, columnspan=2, sticky="w")
                
                # Create separate color name label - left aligned
                name_text = match.library_color.name
                # Add library name if available (for "All Libraries" searches)
                if hasattr(match, 'library_name') and match.library_name:
                    name_text += f"\nLibrary: {match.library_name}"
                
                name_label = ttk.Label(container, text=name_text, font=("Arial", 12), anchor="w")
                name_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")
                
                # Color swatch - increase width to 500
                swatch_width = min(500, self.current_sizes.get('swatch_width', 500))  # Use dynamic width with min of 500
                canvas = tk.Canvas(
                    container,
                    width=swatch_width,
                    height=60,
                    highlightthickness=1,
                    highlightbackground='gray'
                )
                canvas.grid(row=0, column=2, padx=(5, 20), pady=2, sticky="e")
                
                # Create rectangle for color display
                canvas.create_rectangle(
                    0, 0, swatch_width, 60,
                    fill=f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}",
                    outline=''
                )
                
        except Exception as e:
            print(f"Error in color comparison: {str(e)}")
            messagebox.showerror(
                "Comparison Error",
                f"Failed to compare colors:\n\n{str(e)}"
            )
