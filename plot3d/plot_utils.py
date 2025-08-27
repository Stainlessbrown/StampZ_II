import numpy as np

def calculate_aspect_ratios(ax_ranges):
    """Calculate the aspect ratios based on data ranges"""
    x_range = ax_ranges['x_max'] - ax_ranges['x_min']
    y_range = ax_ranges['y_max'] - ax_ranges['y_min']
    z_range = ax_ranges['z_max'] - ax_ranges['z_min']
    max_range = max(x_range, y_range, z_range)
    return [x_range/max_range, y_range/max_range, z_range/max_range]

def calculate_default_ranges(df):
    """Calculate default axis ranges from DataFrame using standardized Xnorm/Ynorm/Znorm columns"""
    if df is not None:
        # Check if we have the standardized normalized columns
        if 'Xnorm' in df.columns and 'Ynorm' in df.columns and 'Znorm' in df.columns:
            # Get data ranges from the standardized columns
            return {
                'x_min': df['Xnorm'].min(),
                'x_max': df['Xnorm'].max(),
                'y_min': df['Ynorm'].min(),
                'y_max': df['Ynorm'].max(),
                'z_min': df['Znorm'].min(),
                'z_max': df['Znorm'].max()
            }
        else:
            # Columns not found, log warning and return default range
            import logging
            logging.warning("Standardized columns (Xnorm, Ynorm, Znorm) not found in DataFrame")
            logging.debug(f"Available columns: {df.columns.tolist()}")
            # Return default 0-1 range
            return {
                'x_min': 0.0, 'x_max': 1.0,
                'y_min': 0.0, 'y_max': 1.0,
                'z_min': 0.0, 'z_max': 1.0
            }
    return {
        'x_min': 0.0, 'x_max': 1.0,
        'y_min': 0.0, 'y_max': 1.0,
        'z_min': 0.0, 'z_max': 1.0
    }

def set_axis_labels(ax, using_rgb=False):
    """Set and format axis labels for the 3D plot
    
    Args:
        ax: The 3D axis object
        using_rgb: Whether to use RGB or L*a*b* labels
        
    Returns:
        tuple: (xlabel, ylabel, zlabel) objects
    """
    if using_rgb:
        # Using RGB color space
        xlabel = ax.xaxis.get_label()
        xlabel.set_text('R')
        xlabel.set_color('red')
        xlabel.set_weight('bold')
        xlabel.set_size(16)
        xlabel.set_visible(True)
        
        ylabel = ax.yaxis.get_label()
        ylabel.set_text('G')
        ylabel.set_color('green')
        ylabel.set_weight('bold')
        ylabel.set_size(16)
        ylabel.set_visible(True)
        
        zlabel = ax.zaxis.get_label()
        zlabel.set_text('B')
        zlabel.set_color('blue')
        zlabel.set_weight('bold')
        zlabel.set_size(16)
        zlabel.set_visible(True)
    else:
        # Using L*a*b* color space
        xlabel = ax.xaxis.get_label()
        xlabel.set_text('L*')
        xlabel.set_color('black')
        xlabel.set_weight('bold')
        xlabel.set_size(16)
        xlabel.set_visible(True)
        
        ylabel = ax.yaxis.get_label()
        ylabel.set_text('a*')
        ylabel.set_color('black')
        ylabel.set_weight('bold')
        ylabel.set_size(16)
        ylabel.set_visible(True)
        
        zlabel = ax.zaxis.get_label()
        zlabel.set_text('b*')
        zlabel.set_color('black')
        zlabel.set_weight('bold')
        zlabel.set_size(16)
        zlabel.set_visible(True)
        
    return xlabel, ylabel, zlabel
