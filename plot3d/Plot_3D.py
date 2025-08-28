#!/usr/bin/env python3
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Helvetica", "Calibri"]
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 14
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk, FigureCanvasTkAgg
from matplotlib import ticker
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import pandas as pd
import platform
import threading
import os
# Optional seaborn import for styling
try:
    import seaborn as sns
    sns.set_style("whitegrid", {'axes.grid': False})
    HAS_SEABORN = True
except ImportError:
    print("Warning: seaborn not available. Using default matplotlib styling.")
    HAS_SEABORN = False

from .logging_setup import setup_logging
from .template_selector import TemplateSelector
from .data_processor import load_data
from .plot_utils import (calculate_aspect_ratios, calculate_default_ranges, set_axis_labels)
from .axis_controls import AxisControls, create_button_frame
from .rotation_controls import RotationControls
from .highlight_manager import HighlightManager
from .k_means_manager import KmeansManager
from .trendline_manager import TrendlineManager
from .delta_e_manager import DeltaEManager
from .sphere_manager import SphereManager
from .reference_point_calculator import ReferencePointCalculator
from .group_display_manager import GroupDisplayManager
from .zoom_controls import ZoomControls
from logging import getLogger
# Initialize logging
setup_logging()

class Plot3DApp:
    # Dictionary of marker sizes for different marker types
    MARKER_SIZES = {
        '.': 25,  # Dot
        'o': 25,  # Circle
        '*': 60,  # Star
        '^': 40,  # Triangle up
        '<': 40,  # Triangle left
        '>': 40,  # Triangle right
        'v': 40,  # Triangle down
        's': 40,  # Square
        'D': 40,  # Diamond
        '+': 50,  # Plus (increased for better visibility)
        'x': 40,  # Cross (increased for better visibility)
    }
    
    def __init__(self, parent=None, data_path=None):
        """Initialize the Plot3DApp
        
        Args:
            parent: Parent tkinter window (if integrating with another app)
            data_path: Optional path to data file (skip file dialog)
        """
        self._refresh_in_progress = False
        self.axis_range_changed = False  # Flag to track when axis ranges change
        self.use_rgb = False
        self.highlight_manager = None
        self.group_display_manager = None  # Will be initialized in _init_ui
        self.file_opener_state = {"attempted": False, "completed": False, "error": None}
        self.file_opener_state = {"attempted": False, "completed": False, "error": None}
        self.trendline_manager = TrendlineManager()
        self.show_trendline = None  # Will be initialized in _init_ui
        self.current_ax = None  # Store reference to current axes for direct rotation
        self.show_trendline = None  # Will
        
        # Handle data source - either from parameter or file dialog
        if data_path:
            # Use provided data path (integrated mode)
            self.file_path = data_path
            print(f"Using provided data path: {self.file_path}")
        else:
            # Get file path from template selector (standalone mode)
            try:
                print("Opening template selector dialog...")
                
                # Check if we're in embedded mode (has parent) - if so, show warning
                if parent is not None:
                    messagebox.showinfo(
                        "File Selection Required",
                        "Please select a data file to analyze in 3D.\n\n"
                        "Supported formats: .ods (OpenDocument Spreadsheet)"
                    )
                
                template_selector = TemplateSelector(parent=parent)
                
                # Check if template_selector has the file_path attribute
                if template_selector is None or not hasattr(template_selector, 'file_path'):
                    print("No file selected or invalid template selector")
                    if parent is None:  # Only exit in standalone mode
                        sys.exit(0)
                    else:
                        return  # Just return in embedded mode
                    
                # Get the file path with proper null checking
                self.file_path = template_selector.file_path if template_selector.file_path else None
                
                # Check if file path is valid
                if self.file_path is None or not self.file_path:
                    print("No file path obtained from template selector")
                    if parent is None:  # Only exit in standalone mode
                        sys.exit(0)
                    else:
                        return  # Just return in embedded mode
                    
                print(f"Template selector provided file path: {self.file_path}")
                    
            except Exception as e:
                print(f"Error initializing template selector: {str(e)}")
                messagebox.showerror("Error", f"Failed to initialize template selector: {str(e)}")
                if parent is None:  # Only exit in standalone mode
                    sys.exit(1)
                else:
                    return  # Just return in embedded mode
        
        # Verify file exists before proceeding
        if not os.path.exists(self.file_path):
            print(f"Error: File does not exist: {self.file_path}")
            messagebox.showerror("File Not Found", f"The file {self.file_path} does not exist.")
            if parent is None:  # Only exit in standalone mode
                sys.exit(1)
            else:
                return  # Just return in embedded mode
            
        print(f"Selected file: {self.file_path}")

        # Single attempt to open file
        try:
            print(f"Opening selected file: {self.file_path}")
            if not self._open_file_immediate(self.file_path):
                print("Warning: Could not open file immediately")
        except Exception as e:
            print(f"Warning: Failed to open file: {str(e)}")
    
        # Create main window - either standalone or as child window
        if parent is None:
            # Standalone mode - create root window
            self.root = tk.Tk()
            self.root.title("Plot 3D App")
            self.is_embedded = False
        else:
            # Embedded mode - create child window
            self.root = tk.Toplevel(parent)
            self.root.title("3D Color Space Analysis")
            # NOTE: On macOS, transient() can cause window disappearing issues when moved
            # Use a more stable approach for window management
            if platform.system() == 'Darwin':
                # On macOS, don't use transient - just ensure proper window attributes
                self.root.attributes('-topmost', False)  # Don't force always on top
                # Store parent reference for cleanup but don't make transient
                self._parent_window = parent
            else:
                # On other platforms, transient works better
                self.root.transient(parent)
            # NOTE: Removed grab_set() to allow non-modal operation so StampZ remains interactive
            self.is_embedded = True
            
        # Common window configuration
        self.root.resizable(True, True)
        
        # Calculate appropriate window size based on screen dimensions
        self._configure_window_geometry()
        
        # Configure main window grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Load initial data
        self.df = load_data(self.file_path)
        if self.df is None:
            messagebox.showerror("Error", "Failed to load data")
            sys.exit(1)
            
        # Initialize variables first
        self._init_variables()
        
        # Define callback for K-means manager to update main DataFrame
        def on_kmeans_update(updated_df):
            self.df = updated_df
            self.refresh_plot()
        
        # Initialize K-means manager with data and file path
        self.kmeans_manager = KmeansManager(on_data_update=on_kmeans_update)
        self.kmeans_manager.set_file_path(self.file_path)
        self.kmeans_manager.load_data(self.df)
        
        # Initialize Delta E manager with the same callback
        self.delta_e_manager = DeltaEManager(on_data_update=on_kmeans_update)
        self.delta_e_manager.set_file_path(self.file_path)
        self.delta_e_manager.load_data(self.df)
        
        # Initialize logger for custom delta E calculator
        logger = getLogger(__name__)
        
        # Initialize Custom Delta E calculator
        self.custom_delta_e_calculator = ReferencePointCalculator(logger=logger)
        self.custom_delta_e_calculator.set_file_path(self.file_path)
        self.custom_delta_e_calculator.load_data(self.df)
        
        # Create figure AFTER data is loaded and BEFORE UI creation
        print("Creating initial figure...")
        self.fig = plt.figure(figsize=(8, 6))
        if not self.fig:
            messagebox.showerror("Error", "Failed to create figure")
            sys.exit(1)
        
        # Create UI components (which will use the figure)
        print("Initializing UI components...")
        self._init_ui()
        
        # Window size already set in _configure_window_geometry()
        
        # Create initial plot
        self.refresh_plot()
        
        # Configure window protocol first
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup_and_exit)
        
        # Schedule delayed file opening only as a backup
        # in case the immediate opening failed
        # Focus on the main window
        self.root.focus_force()
        
        # Start main loop only in standalone mode
        if not self.is_embedded:
            print("Starting standalone mainloop...")
            self.root.mainloop()
        else:
            print("Embedded mode - not starting mainloop (parent app handles this)")
    
    def refresh_plot(self):
        """Refresh the plot with current data"""
        try:
            # Prevent multiple refresh operations
            if hasattr(self, '_refresh_in_progress') and self._refresh_in_progress:
                print("Refresh already in progress, skipping...")
                return
            self._refresh_in_progress = True
            
            # Load and process data
            self.df = load_data(self.file_path)
            if self.df is None:
                self._refresh_in_progress = False
                return
            
            # Store current view angles and zoom level before clearing
            current_elev = None
            current_azim = None
            current_roll = None
            current_xlim = None
            current_ylim = None
            current_zlim = None
            
            # Store zoom controls state if available
            zoom_state = None
            if hasattr(self, 'zoom_controls') and self.zoom_controls:
                zoom_state = self.zoom_controls.get_current_limits()
                print(f"Stored zoom state from zoom controls: {zoom_state}")
            
            if hasattr(self, 'fig') and hasattr(self.fig, 'axes') and len(self.fig.axes) > 0:
                try:
                    current_ax = self.fig.axes[0]  # Get the first (and likely only) axes
                    # Store rotation angles
                    if hasattr(current_ax, 'elev'):
                        current_elev = current_ax.elev
                    if hasattr(current_ax, 'azim'):
                        current_azim = current_ax.azim
                    if hasattr(current_ax, 'roll'):  # Only in newer matplotlib versions
                        current_roll = current_ax.roll
                        
                    # Store zoom level (axis limits)
                    current_xlim = current_ax.get_xlim()
                    current_ylim = current_ax.get_ylim()
                    current_zlim = current_ax.get_zlim()
                    print(f"Stored current zoom levels: X={current_xlim}, Y={current_ylim}, Z={current_zlim}")
                except Exception as e:
                    print(f"Warning: Could not retrieve current view state: {e}")
            
            # Properly clean up existing artists to prevent "cannot remove artist" errors
            try:
                for ax in self.fig.axes:
                    try:
                        # Clear existing collections (scatter plots, etc.)
                        for collection in ax.collections[:]:
                            try:
                                collection.remove()
                            except Exception as e:
                                print(f"Warning: Could not remove collection: {e}")
                        
                        # Clear existing lines
                        for line in ax.lines[:]:
                            try:
                                line.remove()
                            except Exception as e:
                                print(f"Warning: Could not remove line: {e}")
                                
                        # Clear text objects
                        for text in ax.texts[:]:
                            try:
                                text.remove()
                            except Exception as e:
                                print(f"Warning: Could not remove text: {e}")
                    except Exception as inner_e:
                        print(f"Warning: Error cleaning up axis artists: {inner_e}")
            except Exception as outer_e:
                print(f"Warning: Error in axes cleanup: {outer_e}")
            
            # Clear the current figure with proper error handling
            try:
                plt.clf()  # Clear current figure
                self.fig.clear()
            except Exception as e:
                print(f"Warning: Error clearing figure: {e}")
                # If clearing fails, create a new figure
                self.fig = plt.figure(figsize=(8, 6))
                self.canvas.figure = self.fig
            
            # Create 3D subplot with equal aspect ratio
            ax = self.fig.add_subplot(111, projection='3d')
            # Store reference to current axes for direct rotation
            self.current_ax = ax
            
            # Update zoom controls with new axes reference if available
            if hasattr(self, 'zoom_controls') and self.zoom_controls:
                self.zoom_controls.update_axes_reference(ax)
            
            # Get the ranges from axis controls (using x values as they should all be the same)
            try:
                min_val = float(self.axis_vars['x_min'].get())
                max_val = float(self.axis_vars['x_max'].get())
                if min_val >= max_val:
                    messagebox.showerror("Invalid Range", "Min value must be less than max value")
                    min_val = 0.0
                    max_val = 1.0
            except (ValueError, tk.TclError) as e:
                print(f"Error getting axis ranges: {e}")
                min_val = 0.0
                max_val = 1.0
            # If axis range was changed via controls or we don't have stored limits,
            # apply the range from axis controls
            if self.axis_range_changed or current_xlim is None or current_ylim is None or current_zlim is None:
                # Apply the same range to all axes to maintain aspect ratio
                ax.set_xlim([min_val, max_val])
                ax.set_ylim([min_val, max_val])
                ax.set_zlim([min_val, max_val])
                print(f"Using axis control limits: [{min_val}, {max_val}]")
                # Reset the flag after applying
                self.axis_range_changed = False
            else:
                # Check if we have a stored zoom state from the zoom controls
                if zoom_state and all(zoom_state.values()):
                    # Use the zoom controls state
                    ax.set_xlim(zoom_state['xlim'])
                    ax.set_ylim(zoom_state['ylim'])
                    ax.set_zlim(zoom_state['zlim'])
                    print(f"Restored zoom from zoom controls: X={zoom_state['xlim']}, Y={zoom_state['ylim']}, Z={zoom_state['zlim']}")
                else:
                    # Otherwise, restore previously stored limits (preserves zoom level)
                    ax.set_xlim(current_xlim)
                    ax.set_ylim(current_ylim)
                    ax.set_zlim(current_zlim)
                    print(f"Restored zoom levels: X={current_xlim}, Y={current_ylim}, Z={current_zlim}")
            
            # Ensure equal aspect ratio for proper 3D rendering
            ax.set_box_aspect([1, 1, 1])
            print("Applying rotation values to plot")
            # First priority: Use rotation controls values
            if hasattr(self, 'rotation_controls'):
                try:
                    elev = self.rotation_controls.elevation
                    azim = self.rotation_controls.azimuth
                    roll = self.rotation_controls.roll
                    print(f"Using rotation control values: elev={elev}, azim={azim}, roll={roll}")
                    
                    # Handle roll parameter depending on matplotlib version
                    try:
                        ax.view_init(elev=elev, azim=azim, roll=roll)
                    except TypeError:
                        # Older matplotlib versions don't support roll
                        ax.view_init(elev=elev, azim=azim)
                        print("Note: Roll parameter not supported in this matplotlib version")
                except Exception as e:
                    print(f"Error applying rotation from controls: {e}")
                    # Use cached values as fallback
                    if current_elev is not None and current_azim is not None:
                        try:
                            if current_roll is not None:
                                ax.view_init(elev=current_elev, azim=current_azim, roll=current_roll)
                            else:
                                ax.view_init(elev=current_elev, azim=current_azim)
                            print(f"Using cached rotation values: elev={current_elev}, azim={current_azim}, roll={current_roll}")
                        except Exception as e2:
                            print(f"Error applying cached rotation: {e2}")
                            # Last resort: Set default rotation
                            ax.view_init(elev=30, azim=-60)
                            print("Falling back to default rotation")
            # Second priority: Use cached values from the previous view
            elif current_elev is not None and current_azim is not None:
                try:
                    if current_roll is not None:
                        ax.view_init(elev=current_elev, azim=current_azim, roll=current_roll)
                    else:
                        ax.view_init(elev=current_elev, azim=current_azim)
                    print(f"Using cached rotation values: elev={current_elev}, azim={current_azim}, roll={current_roll}")
                except Exception as e:
                    print(f"Error applying cached rotation: {e}")
                    # Last resort: Set default rotation
                    ax.view_init(elev=30, azim=-60)
                    print("Falling back to default rotation")
            else:
                # Last resort: Set default rotation
                ax.view_init(elev=30, azim=-60)
                print("Using default rotation")
            # Draw data points with appropriate markers
                
            # Get visibility mask first
            visible_mask = pd.Series(True, index=self.df.index)  # Default to all visible
            if hasattr(self, 'group_display_manager') and self.group_display_manager:
                visible_mask = self.group_display_manager.get_visible_mask()

            # Only plot points that should be visible
            visible_df = self.df[visible_mask]
            print("Plotting points with specific markers...")
            for idx, row in visible_df.iterrows():
                data_id = row.get('DataID', f'Row {idx}')
                
                # Log centroid identification (for debugging only)
                if 'Cluster' in row and pd.notna(row.get('Cluster')):
                    if pd.notna(row.get('Centroid_X')) and pd.notna(row.get('Centroid_Y')) and pd.notna(row.get('Centroid_Z')):
                        print(f"Point {data_id}: Identified as centroid for cluster {row.get('Cluster')}")
                
                # Validate marker to prevent 'nan' errors
                marker = row['Marker'] if pd.notna(row['Marker']) else 'o'
                color = row['Color'] if pd.notna(row['Color']) else 'blue'
                
                # Check if this point has ∆E value - log but don't let it affect marker
                delta_e = row.get('∆E', 'N/A')
                print(f"Point {data_id}: Plotting with marker '{marker}', color '{color}', ΔE: {delta_e}")
                
                # Get marker-specific size from dictionary
                marker_size = self.MARKER_SIZES.get(marker, 25)

                # Special handling for line-type markers (x and +)
                if marker in ['x', '+']:
                    # Use plot for line markers instead of scatter
                    ax.plot(
                        [row['Xnorm']], 
                        [row['Ynorm']], 
                        [row['Znorm']],
                        color=color,
                        marker=marker,
                        markersize=np.sqrt(marker_size),  # Convert scatter size to markersize
                        linestyle='none',  # Only show markers, no connecting lines
                        label=data_id,
                        zorder=20,  # Higher zorder to ensure visibility
                        clip_on=False  # Prevent clipping
                    )
                else:
                    # Original scatter plot for other markers
                    ax.scatter(
                        row['Xnorm'], 
                        row['Ynorm'], 
                        row['Znorm'],
                        c=color,
                        marker=marker,  # Use original marker value
                        s=marker_size,  # Use marker-specific size
                        label=data_id,
                        zorder=10,  # Ensure points are always on top
                        edgecolors='none',  # No edges for filled markers
                        linewidths=0  # No line width
                    )
            # Group visibility is now handled at the beginning of plotting
            # No need for duplicate code here
            
            set_axis_labels(ax, using_rgb=self.use_rgb)
            
            # Apply tick label visibility settings from axis controls
            if hasattr(self, 'axis_controls'):
                try:
                    # Get visibility settings from axis controls
                    x_tick_visible = self.axis_controls.x_tick_visible.get()
                    y_tick_visible = self.axis_controls.y_tick_visible.get()
                    z_tick_visible = self.axis_controls.z_tick_visible.get()
                    
                    # Apply visibility settings to tick labels while preserving axis labels
                    if not x_tick_visible:
                        ax.xaxis.set_ticklabels([])
                    if not y_tick_visible:
                        ax.yaxis.set_ticklabels([])
                    if not z_tick_visible:
                        ax.zaxis.set_ticklabels([])
                        
                    print(f"Applied tick label visibility: X={x_tick_visible}, Y={y_tick_visible}, Z={z_tick_visible}")
                except Exception as e:
                    print(f"Error applying tick label visibility: {e}")
            
            # Update sphere manager references and render spheres
            # Update sphere manager references and render spheres
            self.sphere_manager.update_references(ax, self.canvas, self.df)
            self._update_sphere_toggles()  # Update sphere visibility toggles
            self.sphere_manager.render_spheres()
            # Adjust layout and refresh
            self.fig.tight_layout()
            
            # Update highlight manager references
            if self.highlight_manager:
                self.highlight_manager.update_references(ax, self.df, self.use_rgb)
            
            # Update group display manager references
            if hasattr(self, 'group_display_manager') and self.group_display_manager:
                self.group_display_manager.update_references(self.df)
            
            # Handle trendline drawing if checkbox is checked
            # Handle trendline drawing if checkbox is checked
            if self.show_trendline.get():
                try:
                    print("Starting linear trendline calculation...")
                    # Only use valid data points for trendline calculation
                    # Specifically use trendline_valid flag to ensure only points with all three coordinates are used
                    valid_df = self.df[self.df['trendline_valid']].copy()
                    print(f"Found {len(valid_df)} valid points for trendline calculation")
                    
                    if len(valid_df) > 2:  # Need at least 3 points for a 3D trendline
                        self.trendline_manager.calculate_linear_regression(valid_df)
                        
                        # Get the fitted plane parameters
                        a, b, c = self.trendline_manager.get_line_equation()
                        print(f"Linear regression parameters: a={a}, b={b}, c={c}")
                        
                        # Calculate the centroid of the data
                        x_mean = valid_df['Xnorm'].mean()
                        y_mean = valid_df['Ynorm'].mean() 
                        z_mean = valid_df['Znorm'].mean()
                        print(f"Data centroid: ({x_mean}, {y_mean}, {z_mean})")
                        
                        # Get min/max values for plotting extent
                        x_values = valid_df['Xnorm'].values
                        y_values = valid_df['Ynorm'].values
                        
                        # Calculate the ranges
                        x_min, x_max = min(x_values), max(x_values)
                        y_min, y_max = min(y_values), max(y_values)
                        x_range = x_max - x_min
                        y_range = y_max - y_min
                        
                        # Find principal direction of data variance for line direction
                        # For a more representative line through the data
                        try:
                            from sklearn.decomposition import PCA
                            HAS_SKLEARN = True
                        except ImportError:
                            print("Warning: scikit-learn not available. Using fallback method for trendline direction.")
                            HAS_SKLEARN = False
                        
                        try:
                            # Try PCA approach first for better directional visualization
                            xy_data = np.vstack([x_values, y_values]).T
                            pca = PCA(n_components=1)
                            pca.fit(xy_data)
                            
                            # Get principal direction
                            direction = pca.components_[0]
                            print(f"Principal direction: {direction}")
                            
                            # Scale to create a line that spans the data extent
                            # Calculate appropriate scale based on data range
                            scale = max(x_range, y_range) * 1.5
                            
                            # Create points along this principal direction
                            t = np.linspace(-scale, scale, 100)
                            line_x = x_mean + direction[0] * t
                            line_y = y_mean + direction[1] * t
                            
                            # Calculate z from the plane equation z = ax + by + c
                            line_z = a * line_x + b * line_y + c
                            
                            print(f"Generated {len(line_x)} points for trendline visualization")
                        except Exception as pca_error:
                            print(f"PCA approach failed: {pca_error}. Using fallback method.")
                            # Fallback to simpler approach if PCA fails
                            # Extend ranges by 20% on each end
                            extended_x_min = x_min - 0.2 * x_range
                            extended_x_max = x_max + 0.2 * x_range
                            extended_y_min = y_min - 0.2 * y_range
                            extended_y_max = y_max + 0.2 * y_range
                            
                            # Create line passing through data centroid along both x and y directions
                            num_points = 100
                            t = np.linspace(-1, 1, num_points)
                            line_x = x_mean + t * x_range
                            line_y = y_mean + t * y_range
                            line_z = a * line_x + b * line_y + c
                        
                        # Plot the trendline as a continuous line
                        print("Plotting trendline...")
                        ax.plot3D(
                            line_x,
                            line_y,
                            line_z,
                            color=self.trendline_manager.get_color(),
                            linewidth=0.8,  # Thinner to avoid obscuring data points
                            label='Linear Trendline',
                            zorder=30  # Higher zorder to ensure it's visible above other elements
                        )
                    else:
                        # Not enough valid data points for trendline
                        print(f"Warning: Not enough valid data points for trendline calculation. Need at least 3, got {len(valid_df)}")
                    
                    # Get line equation parameters for display
                    eq_text = f"z = {a:.4f}x + {b:.4f}y + {c:.4f}"
                    ax.text2D(0.05, 0.95, eq_text, transform=ax.transAxes, 
                             fontsize=10, color='black', bbox=dict(facecolor='white', alpha=0.7))
                except Exception as e:
                    print(f"Error plotting trendline: {str(e)}")
            
            # Handle color-filtered trend lines
            colors = ['red', 'green', 'blue']
            color_vars = [self.show_red_trendline, self.show_green_trendline, self.show_blue_trendline]
            line_styles = ['--', '-.', ':']
            equation_y_positions = [0.85, 0.80, 0.75]  # Y positions for equations display
            
            for color, show_var, line_style, eq_y_pos in zip(colors, color_vars, line_styles, equation_y_positions):
                if show_var.get():
                    try:
                        print(f"Starting {color} trendline calculation...")
                        valid_df = self.df[self.df['trendline_valid']].copy()
                        
                        # Get color-filtered trend line points
                        points = self.trendline_manager.get_color_trendline_points(valid_df, color)
                        
                        if points is not None:
                            # Get equation parameters for display
                            equation = self.trendline_manager.get_color_line_equation(color)
                            
                            if equation is not None:
                                a, b, c = equation
                                print(f"{color.capitalize()} regression parameters: a={a}, b={b}, c={c}")
                                
                                # Use PCA approach for better line visualization (similar to main trendline)
                                color_df = valid_df[valid_df['Color'].str.lower() == color.lower()].copy()
                                color_clean = color_df.dropna(subset=['Xnorm', 'Ynorm', 'Znorm'])
                                
                                if len(color_clean) > 2:
                                    x_values = color_clean['Xnorm'].values
                                    y_values = color_clean['Ynorm'].values
                                    
                                    # Calculate centroid
                                    x_mean = color_clean['Xnorm'].mean()
                                    y_mean = color_clean['Ynorm'].mean()
                                    
                                    # Calculate ranges using ALL data points (like main trendline)
                                    all_data_df = valid_df  # This contains all points
                                    all_x_values = all_data_df['Xnorm'].values  
                                    all_y_values = all_data_df['Ynorm'].values
                                    all_x_min, all_x_max = min(all_x_values), max(all_x_values)
                                    all_y_min, all_y_max = min(all_y_values), max(all_y_values) 
                                    x_range = all_x_max - all_x_min  # Use ALL data range
                                    y_range = all_y_max - all_y_min  # Use ALL data range
                                    
                                    try:
                                        # Use PCA for better directional visualization
                                        try:
                                            from sklearn.decomposition import PCA
                                        except ImportError:
                                            print(f"Warning: scikit-learn not available for {color} trendline PCA. Using fallback.")
                                            raise Exception("sklearn not available")
                                        
                                        xy_data = np.vstack([x_values, y_values]).T
                                        pca = PCA(n_components=1)
                                        pca.fit(xy_data)
                                        
                                        direction = pca.components_[0]
                                        scale = max(x_range, y_range) * 1.5
                                        
                                        t = np.linspace(-scale, scale, 100)
                                        line_x = x_mean + direction[0] * t
                                        line_y = y_mean + direction[1] * t
                                        line_z = a * line_x + b * line_y + c
                                        
                                    except Exception as pca_error:
                                        print(f"PCA failed for {color}: {pca_error}. Using fallback.")
                                        # Fallback method
                                        num_points = 100
                                        t = np.linspace(-1, 1, num_points)
                                        line_x = x_mean + t * x_range
                                        line_y = y_mean + t * y_range
                                        line_z = a * line_x + b * line_y + c
                                    
                                    # Plot the color-filtered trendline
                                    ax.plot3D(
                                        line_x,
                                        line_y,
                                        line_z,
                                        color=color,
                                        linestyle=line_style,
                                        linewidth=1.0,
                                        alpha=0.8,
                                        label=f'{color.capitalize()} Trendline',
                                        zorder=25
                                    )
                                    
                                    # Display equation
                                    eq_text = f"{color[0].upper()}: z = {a:.4f}x + {b:.4f}y + {c:.4f}"
                                    ax.text2D(0.05, eq_y_pos, eq_text, transform=ax.transAxes,
                                             fontsize=9, color=color, 
                                             bbox=dict(facecolor='white', alpha=0.7))
                                else:
                                    print(f"Not enough {color} data points for trendline")
                            else:
                                print(f"No valid equation for {color} trendline")
                        else:
                            print(f"No valid points for {color} trendline")
                            
                    except Exception as e:
                        print(f"Error plotting {color} trendline: {str(e)}")
                
            # Handle polynomial surface drawing if checkbox is checked
            if self.show_polynomial.get():
                try:
                    print("Starting polynomial surface calculation...")
                    # Use trendline_valid flag to ensure only points with all three coordinates are used
                    valid_df = self.df[self.df['trendline_valid']].copy()
                    print(f"Found {len(valid_df)} valid points for polynomial calculation")
                    
                    # Need at least 6 points for a proper polynomial surface (one for each coefficient)
                    if len(valid_df) > 5:  
                        self.trendline_manager.calculate_polynomial_regression(valid_df)
                        
                        # Get the polynomial equation parameters for validation
                        a, b, c, d, e, f = self.trendline_manager.get_polynomial_equation()
                        print(f"Polynomial regression parameters: a={a}, b={b}, c={c}, d={d}, e={e}, f={f}")
                        
                        # Calculate adaptive grid size based on dataset size
                        # More points for smaller datasets, fewer for larger ones to maintain performance
                        num_data_points = len(valid_df)
                        if num_data_points < 20:
                            grid_size = 15  # Smaller grid for very small datasets
                        elif num_data_points < 50:
                            grid_size = 20  # Medium resolution for small datasets
                        elif num_data_points < 200:
                            grid_size = 15  # Lower resolution for medium datasets
                        else:
                            grid_size = 10  # Lowest resolution for large datasets
                        
                        print(f"Using grid size {grid_size} for polynomial surface")
                        
                        # Calculate the range of data for better surface boundaries
                        x_values = valid_df['Xnorm'].values
                        y_values = valid_df['Ynorm'].values
                        
                        x_min, x_max = min(x_values), max(x_values)
                        y_min, y_max = min(y_values), max(y_values)
                        
                        # Extend the range slightly to show a little beyond the data points
                        # but not too much to avoid extrapolation issues
                        x_range = x_max - x_min
                        y_range = y_max - y_min
                        
                        x_min -= 0.05 * x_range
                        x_max += 0.05 * x_range
                        y_min -= 0.05 * y_range
                        y_max += 0.05 * y_range
                        
                        # Get polynomial points for visualization with adaptive grid size
                        # Create custom grid ranges to avoid extrapolation issues
                        x = np.linspace(x_min, x_max, grid_size)
                        y = np.linspace(y_min, y_max, grid_size)
                        X, Y = np.meshgrid(x, y)
                        
                        # Calculate Z values using the polynomial equation
                        Z = (
                            a * X**2 +     # ax²
                            b * Y**2 +     # by²
                            c * X * Y +    # cxy
                            d * X +        # dx
                            e * Y +        # ey
                            f              # f
                        )
                        
                        points = {'x': X, 'y': Y, 'z': Z}
                        print(f"Generated polynomial surface with dimensions: {Z.shape}")
                        
                        try:
                            print("Plotting polynomial surface as wireframe...")
                            # Plot the polynomial surface as a wireframe
                            ax.plot_wireframe(
                                points['x'],
                                points['y'],
                                points['z'],
                                color=self.trendline_manager.get_polynomial_color(),
                                linewidth=0.5,  # Thinner lines to avoid obscuring data points
                                alpha=0.7,      # Slight transparency
                                label='Polynomial Surface',
                                rstride=1,      # Row stride for wireframe
                                cstride=1,      # Column stride for wireframe
                                zorder=20       # Ensure visibility above points
                            )
                            print("Successfully plotted polynomial surface wireframe")
                        except ValueError as wireframe_error:
                            print(f"Error plotting wireframe: {wireframe_error}")
                            # Fallback to scatter plot if wireframe fails
                            print("Falling back to scatter plot visualization for polynomial surface")
                            try:
                                # Flatten arrays for scatter plot
                                x_flat = points['x'].flatten()
                                y_flat = points['y'].flatten()
                                z_flat = points['z'].flatten()
                                print(f"Created {len(x_flat)} flattened points for scatter visualization")
                                
                                ax.scatter(
                                    x_flat, 
                                    y_flat, 
                                    z_flat,
                                    color=self.trendline_manager.get_polynomial_color(),
                                    s=2,  # Small point size
                                    alpha=0.7,
                                    label='Polynomial Surface (scatter fallback)',
                                    zorder=19  # Just below the primary trendline but above data points
                                )
                                print("Successfully plotted polynomial surface as scatter points")
                            except Exception as scatter_error:
                                print(f"Error in scatter fallback: {scatter_error}")
                                # Last resort - try another wireframe with different settings
                                try:
                                    ax.plot_wireframe(
                                        points['x'],
                                        points['y'],
                                        points['z'],
                                        color=self.trendline_manager.get_polynomial_color(),
                                        linewidth=0.5,     # Thinner lines to avoid obscuring data points
                                        alpha=0.8,         # Slightly reduced opacity but still clearly visible
                                        label='Polynomial Surface',
                                        rstride=1,         # Include all rows for complete visualization
                                        cstride=1,         # Include all columns
                                        zorder=25          # Ensure visibility above points
                                    )
                                    print("Successfully plotted fallback wireframe")
                                except Exception as last_error:
                                    print(f"All surface plotting methods failed: {last_error}")
                        except Exception as general_error:
                            print(f"Unexpected error in polynomial plotting: {general_error}")
                        
                        # Display the polynomial equation below the trendline equation
                        # Linear trendline is at 0.95, so position this at 0.90 (5% lower)
                        y_pos = 0.90  # Position below the linear trendline equation
                        eq_text = f"z = {a:.4f}x² + {b:.4f}y² + {c:.4f}xy + {d:.4f}x + {e:.4f}y + {f:.4f}"
                        ax.text2D(0.05, y_pos, eq_text, transform=ax.transAxes, 
                                 fontsize=10, color=self.trendline_manager.get_polynomial_color(), 
                                 bbox=dict(facecolor='white', alpha=0.7))
                except Exception as e:
                    print(f"Error plotting polynomial surface: {str(e)}")
            
            # Update the rotation controls with current view angles
            if hasattr(self, 'rotation_controls'):
                try:
                    self.rotation_controls.update_values(
                        ax.elev,
                        ax.azim,
                        ax.roll if hasattr(ax, 'roll') else 0
                    )
                except Exception as e:
                    print(f"Warning: Could not update rotation controls: {e}")
            
            # Redraw the canvas with proper error handling
            try:
                self.canvas.draw()
            except Exception as e:
                print(f"Error drawing canvas: {str(e)}")
                try:
                    # Fall back to draw_idle if draw fails
                    self.canvas.draw_idle()
                except Exception as e2:
                    print(f"Error in draw_idle fallback: {str(e2)}")
        except Exception as e:
            print(f"Error in refresh_plot: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Always ensure the refresh lock is released
            self._refresh_in_progress = False
    
    def _apply_rotation(self, elev=None, azim=None, roll=None):
        """Apply rotation directly to the current plot without full refresh"""
        if not hasattr(self, 'current_ax') or self.current_ax is None:
            print("No axes available for rotation")
            return False
            
        try:
            # Get current values if not specified
            if elev is None and hasattr(self, 'rotation_controls'):
                elev = self.rotation_controls.elevation
            if azim is None and hasattr(self, 'rotation_controls'):
                azim = self.rotation_controls.azimuth
            if roll is None and hasattr(self, 'rotation_controls'):
                roll = self.rotation_controls.roll
                
            print(f"Directly applying rotation: elev={elev}, azim={azim}, roll={roll}")
            
            # Apply rotation
            try:
                self.current_ax.view_init(elev=elev, azim=azim, roll=roll)
            except TypeError:
                # Older matplotlib versions don't support roll
                self.current_ax.view_init(elev=elev, azim=azim)
                
            # Redraw the canvas - use draw_idle for better performance
            try:
                self.canvas.draw_idle()
            except Exception as e:
                print(f"Error in draw_idle: {e}")
                # Fall back to regular draw
                self.canvas.draw()
                
            return True
        except Exception as e:
            print(f"Error applying direct rotation: {e}")
        
    def _init_variables(self):
        """Initialize tkinter variables with shared axis ranges.
        
        Sets up the axis range variables with default values and prepares for UI initialization.
        """
        default_min = 0.0
        default_max = 1.0
        
        self.axis_vars = {
            'x_min': tk.DoubleVar(master=self.root, value=default_min),
            'x_max': tk.DoubleVar(master=self.root, value=default_max),
            'y_min': tk.DoubleVar(master=self.root, value=default_min),
            'y_max': tk.DoubleVar(master=self.root, value=default_max),
            'z_min': tk.DoubleVar(master=self.root, value=default_min),
            'z_max': tk.DoubleVar(master=self.root, value=default_max)
        }
        
        # Initialize show_trendline and show_polynomial variables here instead of in _init_ui
        self.show_trendline = tk.BooleanVar(value=False)
        self.show_polynomial = tk.BooleanVar(value=False)
        
        # Initialize color-filtered trend line variables
        self.show_red_trendline = tk.BooleanVar(value=False)
        self.show_green_trendline = tk.BooleanVar(value=False)
        self.show_blue_trendline = tk.BooleanVar(value=False)
        
    def _create_sphere_visibility_frame(self):
        """Create frame for sphere visibility toggles."""
        try:
            # Create a labeled frame for sphere visibility controls
            sphere_frame = ttk.LabelFrame(self.control_frame, text="Sphere Visibility")
            sphere_frame.grid(row=10, column=0, sticky='nsew', padx=5, pady=5)
            
            # Force minimum size and prevent frame from shrinking
            sphere_frame.grid_propagate(False)
            sphere_frame.configure(height=120)  # Minimum height to show toggles
            
            # Initialize sphere toggle variables dictionary if not exists
            if not hasattr(self, 'sphere_toggle_vars'):
                self.sphere_toggle_vars = {}
            
            # Create frame for toggles
            self.toggle_frame = ttk.Frame(sphere_frame)
            self.toggle_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
            
            # Configure grid weights for proper expansion
            sphere_frame.grid_columnconfigure(0, weight=1)
            self.toggle_frame.grid_columnconfigure(0, weight=1)
            
            # Create initial toggles
            self._update_sphere_toggles()
            
            return sphere_frame
            
        except Exception as e:
            print(f"Error creating sphere visibility frame: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Methods removed since we're now using the main scrollbar
    
    def _update_sphere_toggles(self):
        """Update sphere visibility toggles based on current data."""
        try:
            # Clear existing toggles
            for widget in self.toggle_frame.winfo_children():
                widget.destroy()
            
            # Get active colors from sphere manager
            active_colors = self.sphere_manager.get_active_colors()
            
            if not active_colors:
                # Show message if no spheres are available
                msg_label = ttk.Label(
                    self.toggle_frame, 
                    text="No spheres available",
                    foreground='gray'
                )
                msg_label.grid(row=0, column=0, padx=5, pady=5)
                return
            
            # Create toggle for each active color with proper styling
            for i, color in enumerate(active_colors):
                if color not in self.sphere_toggle_vars:
                    self.sphere_toggle_vars[color] = tk.BooleanVar(value=True)
                
                # Create container frame for better visibility
                toggle_container = ttk.Frame(self.toggle_frame)
                toggle_container.grid(row=i, column=0, sticky='ew', padx=5, pady=2)
                toggle_container.grid_columnconfigure(0, weight=1)
                
                # Create checkbutton with explicit width and padding
                cb = ttk.Checkbutton(
                    toggle_container,
                    text=color.capitalize(),
                    variable=self.sphere_toggle_vars[color],
                    command=lambda c=color: self._on_sphere_toggle(c),
                    padding=5
                )
                cb.grid(row=0, column=0, sticky='w')
            
            # Force toggle frame update
            self.toggle_frame.update_idletasks()
            
        except Exception as e:
            print(f"Error updating sphere toggles: {str(e)}")
    
    def _on_sphere_toggle(self, color: str):
        """Handle sphere visibility toggle."""
        if hasattr(self, 'sphere_manager'):
            self.sphere_manager.toggle_visibility(color)
            
    def _init_ui(self):
        """
        Creates and arranges all UI elements including the plot canvas, 
        controls, toolbars, and visualization options.
        """
        # Variables should already be initialized in _init_variables
        
        # Create main container frame
        main_container = ttk.Frame(self.root)
        main_container.grid(row=0, column=0, sticky='nsew')
        
        # Configure main container grid
        main_container.grid_columnconfigure(0, weight=1)  # Canvas area
        main_container.grid_columnconfigure(1, weight=0)  # Controls area
        main_container.grid_rowconfigure(0, weight=1)
        
        # Create canvas frame FIRST before any controls
        canvas_frame = ttk.Frame(main_container)
        canvas_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)
        
        # Use the figure created before _init_ui and create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
        
        # Create toolbar frame and toolbar
        toolbar_frame = ttk.Frame(canvas_frame)
        toolbar_frame.grid(row=1, column=0, sticky='ew')
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        # Initialize sphere manager now that figure exists
        self.sphere_manager = SphereManager(self.fig.gca(), self.canvas, self.df)
        
        # NOW create controls container
        controls_container = ttk.Frame(main_container)
        controls_container.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        controls_container.grid_rowconfigure(0, weight=1)
        controls_container.grid_columnconfigure(0, weight=1)
        
        # Create scrollable canvas for controls
        # Increased width from 300 to 400 to accommodate all rotation controls
        control_canvas = tk.Canvas(controls_container, width=400)  
        control_scrollbar = ttk.Scrollbar(controls_container, orient="vertical", command=control_canvas.yview)
        control_canvas.configure(yscrollcommand=control_scrollbar.set)
        
        # Create control frame inside canvas
        self.control_frame = ttk.Frame(control_canvas)
        
        # Add control frame to canvas with proper width (370px to match the increased canvas width)
        canvas_frame_window = control_canvas.create_window((0, 0), window=self.control_frame, anchor='nw', width=370)  # Slightly less than canvas width
        
        # Configure grid weights and sticky settings
        control_canvas.grid(row=0, column=0, sticky='nsew', padx=(5,0))  # Add padding on left
        control_scrollbar.grid(row=0, column=1, sticky='ns', padx=(0,5))  # Add padding on right
        
        # Configure column weights
        controls_container.grid_columnconfigure(0, weight=1)
        controls_container.grid_columnconfigure(1, weight=0)  # Scrollbar column should not expand
        
        # Initialize axis controls first
        self.axis_controls = AxisControls(
            self.control_frame,
            self.axis_vars,
            on_update=self._on_axis_range_changed
        )
        self.axis_controls.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        # Create label toggle button
        self.label_toggle_button = ttk.Button(
            self.control_frame,
            text="Labels: L*a*b*",
            command=self._toggle_labels
        )
        self.label_toggle_button.grid(row=1, column=0, sticky='ew', padx=5, pady=5)
        
        # Initialize rotation controls early to ensure they're available for plot creation
        self.rotation_controls = RotationControls(
            self.control_frame,
            on_rotation_change=self._rotation_changed_callback
        )
        self.rotation_controls.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
        
        # Initialize zoom controls immediately after rotation controls for better workflow
        try:
            # Ensure figure exists
            if not hasattr(self, 'fig') or self.fig is None:
                print("Warning: Figure doesn't exist yet, creating a new one")
                self.fig = plt.figure(figsize=(8, 6))
                
            # Ensure canvas exists
            if not hasattr(self, 'canvas') or self.canvas is None:
                print("Warning: Canvas doesn't exist yet, skipping zoom controls initialization")
                return
                
            # Update canvas figure reference if needed
            if self.canvas.figure is not self.fig:
                self.canvas.figure = self.fig
            
            # Get axes for zoom controls - create if needed
            ax = None
            if hasattr(self.fig, 'axes') and len(self.fig.axes) > 0:
                ax = self.fig.axes[0]
            else:
                # Create a 3D axes if none exists
                ax = self.fig.add_subplot(111, projection='3d')
                
            # Initialize the zoom controls with all required components
            self.zoom_controls = ZoomControls(
                self.control_frame,
                self.fig,
                self.canvas, 
                ax,
                on_zoom_change=self._on_zoom_change
            )
            self.zoom_controls.grid(row=3, column=0, sticky='nsew', padx=5, pady=5)
            print("Successfully initialized zoom controls")
        except Exception as e:
            print(f"Error initializing zoom controls: {e}")
            import traceback
            traceback.print_exc()
        
        # Note: Canvas frame, figure, and toolbar are now created BEFORE controls
        
        # Configure column weights
        controls_container.grid_columnconfigure(0, weight=1)
        controls_container.grid_columnconfigure(1, weight=0)  # Scrollbar column should not expand
        
        # Bind frame configuration to update scroll region
        def _on_control_frame_configure(event):
            # Update scrollregion to include all of the control frame
            control_canvas.configure(scrollregion=control_canvas.bbox("all"))
            # Update the width of the canvas window to fit the control frame
            control_canvas.itemconfig(canvas_frame_window, width=control_canvas.winfo_width())
        
        # Bind events for scrolling
        self.control_frame.bind('<Configure>', _on_control_frame_configure)
        
        # Add mouse wheel scrolling with platform-specific handling
        def _on_control_mousewheel(event):
            if platform.system() == 'Windows':
                control_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif platform.system() == 'Darwin':  # macOS
                control_canvas.yview_scroll(int(-1*event.delta), "units")
            else:  # Linux
                if hasattr(event, 'num'):
                    if event.num == 4:
                        control_canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        control_canvas.yview_scroll(1, "units")
        
        # Bind mouse wheel events
        control_canvas.bind_all('<MouseWheel>', _on_control_mousewheel)  # Windows and macOS
        control_canvas.bind_all('<Button-4>', _on_control_mousewheel)    # Linux scroll up
        control_canvas.bind_all('<Button-5>', _on_control_mousewheel)    # Linux scroll down
        
        # Note: Axis controls, label toggle, and rotation controls are now initialized earlier
        
        # Ensure the control frame can expand properly
        self.control_frame.grid_columnconfigure(0, weight=1)
        
        button_frame = create_button_frame(self.control_frame, on_refresh=self.refresh_plot)
        button_frame.grid(row=6, column=0, sticky='ew', padx=5, pady=5)

        # Create highlight frame and manager
        self.highlight_frame = ttk.Frame(self.control_frame)
        self.highlight_frame.grid(row=7, column=0, sticky='ew', padx=5, pady=5)
        # Initialize highlight manager
        self.highlight_manager = HighlightManager(
            self.root,
            self.highlight_frame,
            self.fig.gca(),
            self.canvas,
            self.df,
            self.use_rgb,
        )

        # Create visualization options frame
        
        # Create group display frame with explicit LabelFrame and styling
        group_display_frame = ttk.LabelFrame(self.control_frame, text="Group Display")
        group_display_frame.grid(row=8, column=0, sticky='nsew', padx=5, pady=5)

        # Force minimum size and prevent frame from shrinking
        group_display_frame.grid_propagate(False)
        group_display_frame.configure(height=180, width=350)  # Adjusted height
        group_display_frame.grid_columnconfigure(0, weight=1)

        # Add style for better visibility
        style = ttk.Style()
        style.configure('GroupDisplay.TLabelframe', borderwidth=2, relief='solid')
        style.configure('GroupDisplay.TLabelframe.Label', font=('Arial', 10, 'bold'))
        group_display_frame.configure(style='GroupDisplay.TLabelframe')

        # Initialize group display manager
        self.group_display_manager = GroupDisplayManager(
            self.root,
            group_display_frame,
            self.df,
            on_visibility_change=self.refresh_plot
        )

        # Force frame update and ensure proper layout
        group_display_frame.update()
        group_display_frame.update_idletasks()
        
        # Create trendline frame after group display
        self.trendline_frame = ttk.LabelFrame(self.control_frame, text="Trend Lines")
        self.trendline_frame.grid(row=9, column=0, sticky='ew', padx=5, pady=5)

        # Add linear trendline toggle
        ttk.Checkbutton(
            self.trendline_frame,
            text="Linear Equation",
            variable=self.show_trendline,
            command=self.refresh_plot
        ).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        # Add color-filtered trendline toggles (R, G, B) on the same row
        ttk.Checkbutton(
            self.trendline_frame,
            text="R",
            variable=self.show_red_trendline,
            command=self.refresh_plot,
            width=3
        ).grid(row=0, column=1, sticky='w', padx=2, pady=5)
        
        ttk.Checkbutton(
            self.trendline_frame,
            text="G",
            variable=self.show_green_trendline,
            command=self.refresh_plot,
            width=3
        ).grid(row=0, column=2, sticky='w', padx=2, pady=5)
        
        ttk.Checkbutton(
            self.trendline_frame,
            text="B",
            variable=self.show_blue_trendline,
            command=self.refresh_plot,
            width=3
        ).grid(row=0, column=3, sticky='w', padx=2, pady=5)
        
        # Add polynomial toggle
        ttk.Checkbutton(
            self.trendline_frame,
            text="Polynomial",
            variable=self.show_polynomial,
            command=self.refresh_plot
        ).grid(row=1, column=0, sticky='w', padx=5, pady=5)

        # Create sphere visibility frame with scrollable content
        sphere_frame = ttk.LabelFrame(self.control_frame, text="Sphere Visibility")
        sphere_frame.grid(row=10, column=0, sticky='nsew', padx=5, pady=5)

        # Force minimum size and prevent frame from shrinking
        sphere_frame.grid_propagate(False)
        sphere_frame.configure(height=350, width=350)  # Further increased height
        sphere_frame.grid_columnconfigure(0, weight=1)

        # Create scrollable canvas with explicit size
        canvas = tk.Canvas(sphere_frame, height=320, width=330)  # Explicit dimensions
        canvas.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(sphere_frame, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scrollbar.set)

        # Create frame for toggles inside canvas
        self.toggle_frame = ttk.Frame(canvas)
        self.toggle_frame.grid_columnconfigure(0, weight=1)

        # Create window for toggle frame in canvas
        canvas_window = canvas.create_window((0, 0), window=self.toggle_frame, anchor='nw')

        # Configure canvas and scrolling
        def _configure_toggle_frame(event):
            # Update scroll region to include all toggle buttons
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Set window width to match canvas
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())

        self.toggle_frame.bind('<Configure>', _configure_toggle_frame)

        # Initialize sphere toggle variables
        if not hasattr(self, 'sphere_toggle_vars'):
            self.sphere_toggle_vars = {}

        # Create initial toggles
        self._update_sphere_toggles()

        # Force frame updates
        sphere_frame.update()
        sphere_frame.update_idletasks()
        
        # No duplicate zoom controls needed - already initialized after rotation controls
        
        # Configure control frame grid
        self.control_frame.grid_columnconfigure(0, weight=1)
                    
    def _configure_window_geometry(self):
        """Calculate and set optimal window size and position based on screen dimensions."""
        try:
            # Get available screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Default to larger size for multi-monitor setups (1600x1000)
            # but scale down for smaller screens
            if screen_width >= 3000:  # Likely multi-monitor setup
                window_width = 1600
                window_height = 1000
            elif screen_width >= 1920:  # Standard desktop/larger laptop
                window_width = 1400
                window_height = 900
            else:  # Smaller screens
                window_width = min(1200, int(screen_width * 0.8))
                window_height = min(800, int(screen_height * 0.8))
            
            # Try to detect multiple monitors and position on second monitor if available
            # This is approximate since Tkinter doesn't have direct multi-monitor API
            if screen_width > 2000:  # Likely multiple monitors
                # Position on second monitor - assume first monitor ends around screen_width/2
                # This is a simplification but works for common side-by-side monitor setups
                x_position = max(screen_width // 2, screen_width - window_width - 50)
                y_position = (screen_height - window_height) // 2
            else:
                # Center on primary monitor
                x_position = (screen_width - window_width) // 2
                y_position = (screen_height - window_height) // 2
            
            # Set the geometry
            self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
            
            # Set minimum size to ensure controls remain usable
            self.root.minsize(900, 700)
        except Exception as e:
            # Fall back to default size if anything goes wrong
            print(f"Warning: Could not calculate optimal window size: {e}")
            self.root.geometry("1200x800")
    
    def cleanup_and_exit(self):
        # App cleanup and shutdown handler
        print("Application is closing, performing cleanup...")
        
        # Clean up parent window reference if stored (macOS fix)
        if hasattr(self, '_parent_window'):
            self._parent_window = None
        
        try:
            if hasattr(self, 'custom_delta_e_calculator'):
                self.custom_delta_e_calculator.save_to_file()
                
            if hasattr(self, 'kmeans_manager'):
                self.kmeans_manager.save_to_file()
                
            if hasattr(self, 'delta_e_manager'):
                self.delta_e_manager.save_to_file()
                
            # Save zoom presets before exit
            if hasattr(self, 'zoom_controls'):
                try:
                    self.zoom_controls.save_presets_to_file()
                    print("Saved zoom presets")
                except Exception as e:
                    print(f"Warning: Error saving zoom presets: {str(e)}")
                
        except Exception as e:
            print(f"Warning: Error during manager cleanup: {str(e)}")
        
        try:
            if platform.system() == 'Darwin':
                pass
        except Exception as e:
            print(f"Warning: Error during process cleanup: {str(e)}")
        
        if hasattr(self, 'file_opener_state'):
            print("File opener status - Attempted: {}, Completed: {}, Error: {}".format(
                self.file_opener_state.get('attempted', False),
                self.file_opener_state.get('completed', False),
                self.file_opener_state.get('error', None)
            ))
        
        try:
            plt.close('all')
        except Exception as e:
            print(f"Warning: Error closing plots: {str(e)}")
            
        try:
            self.root.destroy()
        except Exception as e:
            print(f"Warning: Error destroying root window: {str(e)}")
        
        print("Cleanup complete, exiting application")
        sys.exit(0)

    def _toggle_labels(self):
        """Toggle between L*a*b* and RGB axis labels"""
        self.use_rgb = not self.use_rgb
        self.label_toggle_button.config(text="Labels: " + ("RGB" if self.use_rgb else "L*a*b*"))
        
        # Update checkbox labels in axis controls to match current axis system
        if hasattr(self, 'axis_controls'):
            self.axis_controls.update_checkbox_labels(self.use_rgb)
            
        self.refresh_plot()
        
    def _rotation_changed_callback(self):
        """Handle rotation changes from rotation controls"""
        try:
            # Special handling for rotation controls to avoid full refresh
            if not hasattr(self, 'rotation_controls') or self.rotation_controls is None:
                print("Rotation controls not yet initialized, skipping callback")
                return
                
            # Get rotation values directly from controls
            elev = self.rotation_controls.elevation
            azim = self.rotation_controls.azimuth
            roll = self.rotation_controls.roll
                
            # Try direct rotation first for better performance
            if self._apply_rotation(elev, azim, roll):
                print(f"Applied rotation directly (fast path): elev={elev}, azim={azim}, roll={roll}")
            else:
                # Fall back to full refresh if direct rotation fails
                self.refresh_plot()
        except Exception as e:
            print(f"Error during rotation control callback: {e}")
            
    def _on_axis_range_changed(self):
        """Handle axis range changes from controls."""
        # Set flag to indicate axis ranges were manually changed
        self.axis_range_changed = True
        # Refresh the plot with the new ranges
        self.refresh_plot()
    
    def _on_zoom_change(self, axis_ranges=None):
        """Handle zoom changes from the zoom controls.
        
        Args:
            axis_ranges: Optional dictionary containing axis min/max values
                         when loading a complete view preset
        """
        try:
            # This is called when zoom is changed through the zoom controls
            # We don't need to do a full refresh because the zoom controls
            # already update the plot. We just need to update any related UI
            
            # If axis ranges were provided (from a preset load)
            if axis_ranges:
                print(f"Updating axis ranges from preset: {axis_ranges}")
                # Update the axis control variables
                for axis in ['x', 'y', 'z']:
                    min_key = f'{axis}_min'
                    max_key = f'{axis}_max'
                    if min_key in axis_ranges and max_key in axis_ranges:
                        self.axis_vars[min_key].set(axis_ranges[min_key])
                        self.axis_vars[max_key].set(axis_ranges[max_key])
                
                # Update rotation controls with new view if available
                if hasattr(self, 'rotation_controls') and hasattr(self, 'current_ax'):
                    self.rotation_controls.update_values(
                        self.current_ax.elev,
                        self.current_ax.azim,
                        self.current_ax.roll if hasattr(self.current_ax, 'roll') else 0
                    )
        except Exception as e:
            print(f"Error in zoom change handler: {e}")
    
    def _get_platform_open_command(self):
        """
        Get the platform-specific command to open a file with its default application.
        
        Returns:
            tuple: (command, extra_args) where command is the platform-specific command,
                  and extra_args is a list of additional arguments to pass before the filename.
        """
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            # On macOS, the 'open' command is used to open files with default applications
            # The -g flag prevents the opener from taking focus (more stable)
            return 'open', ['-g']
            
        elif system == 'Windows':
            # On Windows, 'start' is a shell command, not an executable
            # The empty string as the first argument prevents the command window from opening
            return 'start', ['""']
            
        elif system == 'Linux':
            # Try different commands that might be available on Linux
            for cmd in ['xdg-open', 'gnome-open', 'kde-open']:
                try:
                    if subprocess.run(['which', cmd], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL).returncode == 0:
                        return cmd, []
                except:
                    pass
                    
        # Return None, [] if we can't determine the command
        print(f"Warning: Could not determine file open command for {system} platform")
        return None, []
    
    def _open_file_immediate(self, file_path):
        """
        Open .ods file immediately using LibreOffice.
        
        Args:
            file_path: Path to the file to open
            
        Returns:
            bool: True if file was opened successfully, False otherwise
        """
        try:
            print(f"Opening file immediately with LibreOffice: {file_path}")
            if platform.system() == 'Darwin':
                # Use LibreOffice on macOS
                try:
                    # First try with soffice command (LibreOffice binary)
                    process = subprocess.Popen(
                        ['soffice', file_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    print("Successfully launched LibreOffice using soffice command")
                    self.file_opened = True
                    return True
                except Exception as e:
                    print(f"soffice command failed: {e}, trying direct LibreOffice path")
                    try:
                        # Try direct path to LibreOffice
                        process = subprocess.Popen(
                            ['/Applications/LibreOffice.app/Contents/MacOS/soffice', file_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        print("Successfully launched LibreOffice using direct path")
                        self.file_opened = True
                        return True
                    except Exception as e:
                        print(f"Failed to open with LibreOffice: {e}, trying default handler")
                        # Fall back to default handler as last resort
                        try:
                            subprocess.Popen(
                                ['open', file_path],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                start_new_session=True
                            )
                            print("Successfully launched with default handler")
                            self.file_opened = True
                            return True
                        except Exception as e:
                            print(f"Default open failed: {e}")
                            return False
            elif platform.system() == 'Windows':
                try:
                    # Try LibreOffice on Windows
                    subprocess.Popen(
                        ['soffice', file_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    print("Successfully launched LibreOffice on Windows")
                    self.file_opened = True
                    return True
                except:
                    # Fallback to default Windows handler
                    os.startfile(file_path)
                    print("Launched with default Windows handler")
                    self.file_opened = True
                    return True
            else:
                # Linux handlers with LibreOffice first
                commands = ['soffice', 'libreoffice', 'xdg-open', 'gnome-open', 'kde-open']
                for cmd in commands:
                    try:
                        subprocess.Popen(
                            [cmd, file_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        print(f"Successfully launched with {cmd}")
                        self.file_opened = True
                        return True
                    except:
                        continue
                        
            # If we get here, all immediate methods failed
            print("All file opening methods failed")
            return False
        except Exception as e:
            print(f"Error in immediate file opening: {str(e)}")
            return False


if __name__ == '__main__':
    Plot3DApp()
