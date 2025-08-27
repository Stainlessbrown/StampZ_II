import pandas as pd
import numpy as np
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Set pandas display options for floating-point precision
pd.set_option('display.float_format', lambda x: '{:.4f}'.format(x))
pd.set_option('display.precision', 4)
def load_data(file_path, use_rgb=False, handle_blank_rows=True):
    """Load data from various file formats and process it"""
    logging.debug(f"Loading data from file: {file_path}")
    
    try:
        # Get file extension
        file_extension = file_path.lower().split('.')[-1]
        
        # Load the raw data
        if file_extension == 'ods':
            df = pd.read_excel(file_path, engine='odf')
        else:
            raise ValueError(f"Unsupported file format: {file_extension}. Only .ods files are supported.")
        
        # Add original row numbers for proper tracking before any processing
        df['original_row'] = df.index
        logger.info("Added original_row column to track row numbers")
        print("Debug: Added original_row column to track row numbers")
        
        # Handle blank rows
        total_rows_before = len(df)
        blank_mask = df.isna().all(axis=1)
        blank_rows_count = blank_mask.sum()
        
        logger.info(f"Found {blank_rows_count} completely blank rows in the data")
        print(f"Debug: Found {blank_rows_count} completely blank rows in the data")
        
        # Keep track of blank row positions for logging
        if blank_rows_count > 0:
            blank_row_indices = df.index[blank_mask].tolist()
            logger.info(f"Blank rows found at indices: {blank_row_indices}")
            print(f"Debug: Blank rows found at indices: {blank_row_indices}")
            
            # Remove blank rows if configured to do so
            if handle_blank_rows:
                # Store original row numbers before dropping rows
                original_rows = df['original_row'].copy()
                
                # Drop blank rows
                df = df.dropna(how='all').reset_index(drop=True)
                
                # Ensure original_row values are preserved as integers
                df['original_row'] = df['original_row'].astype(int)
                
                logger.info(f"Removed {blank_rows_count} blank rows. Rows reduced from {total_rows_before} to {len(df)}")
                print(f"Debug: Removed {blank_rows_count} blank rows")
                print(f"Debug: Preserved original row mapping in 'original_row' column")
            else:
                logger.info("Keeping blank rows in the data as requested")
                print("Debug: Keeping blank rows in the data as requested")

        print("Debug: Raw DataFrame columns:", df.columns.tolist())
        logger.info(f"Loaded raw DataFrame with columns: {df.columns.tolist()}")
        
        # Process the DataFrame
        df = process_dataframe(df)
        
        return df
        
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def process_dataframe(df):
    """Process and clean the DataFrame"""
    try:
        # Define required columns and their default values
        defaults = {
            'Xnorm': float('nan'),    # Use NaN instead of 0.0 to better identify empty cells
            'Ynorm': float('nan'),
            'Znorm': float('nan'),
            'Centroid_X': float('nan'),  # Centroid position columns
            'Centroid_Y': float('nan'),  # Centroid position columns
            'Centroid_Z': float('nan'),  # Centroid position columns
            'DataID': lambda i: f"Point_{i+1}",
            'Cluster': None,
            'Marker': '.',  # Changed from 'M' to 'Marker'
            'Color': None,  # We'll set this after DataID is established
            'Sphere': None,  # We'll set this after DataID is established
            'valid_data': False   # Added flag to identify valid data points vs empty rows
        }
        def get_initial_color(data_id):
            """Determine initial color based on DataID"""
            color_map = {
            }
            for prefix, color in color_map.items():
                if str(data_id).startswith(prefix):
                    return color
            return 'black'  # Only used if no color is specified
        # Create missing columns with default values
        for col, default in defaults.items():
            if col not in df.columns:
                if callable(default):
                    df[col] = [default(i) for i in range(len(df))]
                else:
                    df[col] = default
        
        # We'll set colors after coordinate processing to preserve original values
        
        # Process coordinates for spheres
        print("\nDebug: Processing coordinates...")

        # Convert numeric columns to float before any operations
        numeric_cols = ['Xnorm', 'Ynorm', 'Znorm', 'Centroid_X', 'Centroid_Y', 'Centroid_Z']
        for col in numeric_cols:
            if col in df.columns:
                try:
                    # Convert to numeric, only coercing truly invalid values to NaN
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # Count NaN values for logging purposes
                    nan_count = df[col].isna().sum()
                    if nan_count > 0:
                        logger.debug(f"Found {nan_count} NaN values in {col} column")
                    
                    # Important: Empty strings and None values become NaN,
                    # but valid zeros remain as zero
                    logger.debug(f"Converted column {col} to numeric values")
                except Exception as e:
                    logger.warning(f"Error converting column {col} to numeric: {str(e)}")
                    df[col] = 0.0

        # Create a valid_data flag based on coordinate values
        # Note: The two coordinate systems (norm and centroid) have specific relationships:
        # - K-means reads from X/Y/Z_norm, writes to Cluster and Centroid_X/Y/Z
        # - K-means reads from X/Y/Z_norm, writes to Cluster and Centroid_X/Y/Z
        # - ∆E function uses Centroid_X/Y/Z as reference against X/Y/Z_norm
        # - Trendlines ONLY use X/Y/Z_norm coordinates and NEVER use Centroid_X/Y/Z
        # - For trendlines, all three norm coordinates (X, Y, and Z) must be present
        # Each coordinate system is kept completely separate with no fallback between them
        # Check if X/Y/Z norm coordinates are present (not NaN)
        norm_valid = ~(
            df['Xnorm'].isna() & 
            df['Ynorm'].isna() & 
            df['Znorm'].isna()
        )
        
        # Check if Centroid coordinates are present (not NaN)
        centroid_valid = ~(
            df['Centroid_X'].isna() & 
            df['Centroid_Y'].isna() & 
            df['Centroid_Z'].isna()
        )
        
        # Create separate flags for different purposes:
        # 1. valid_data: General data validity (either coordinate system has data)
        # 2. trendline_valid: Only considers X/Y/Z_norm coordinates for trendlines
        df['valid_data'] = norm_valid | centroid_valid
        
        # IMPORTANT: Create a separate flag specifically for trendline calculations
        # IMPORTANT: Create a separate flag specifically for trendline calculations
        # This ONLY considers norm coordinates, never centroid coordinates
        # For trendlines, we need ALL THREE norm coordinates to be present
        trendline_valid = (
            df['Xnorm'].notna() & 
            df['Ynorm'].notna() & 
            df['Znorm'].notna()
        )
        
        # Set the trendline_valid flag directly on the dataframe
        df['trendline_valid'] = trendline_valid
        
        # Calculate valid data count after setting the flag
        # Count valid data points
        valid_data_count = df['valid_data'].sum()
        trendline_valid_count = df['trendline_valid'].sum() 
        
        logger.info(f"Identified {valid_data_count} rows with valid coordinate data")
        logger.info(f"Of these, {trendline_valid_count} rows are valid for trendline calculations (have norm coordinates)")
        print(f"Debug: Found {valid_data_count} rows with valid coordinate data")
        print(f"Debug: Found {trendline_valid_count} rows valid for trendlines (norm coordinates only)")

        # Handle the Centroid_X, Centroid_Y, Centroid_Z columns
        # Keep centroid values as they are - no fallback to normalized coordinates
        logger.info("Processing centroid coordinates")
        # No fallback logic - if Centroid values are empty, they stay empty
        logger.debug("Successfully processed centroid coordinates")
        # Create mask for valid data points (non-NaN values)
        try:
            # Ensure values are valid numbers before calculation
            # Process norm coordinates
            x_norm = pd.to_numeric(df['Xnorm'], errors='coerce')
            y_norm = pd.to_numeric(df['Ynorm'], errors='coerce')
            z_norm = pd.to_numeric(df['Znorm'], errors='coerce')
            
            # Process centroid coordinates
            centroid_x = pd.to_numeric(df['Centroid_X'], errors='coerce')
            centroid_y = pd.to_numeric(df['Centroid_Y'], errors='coerce')
            centroid_z = pd.to_numeric(df['Centroid_Z'], errors='coerce')
            
            # Create separate masks for norm and centroid data
            # A point is valid if at least one coordinate axis has data (not NaN)
            # For general data validity, a point is valid if at least one coordinate has data
            norm_mask = (
                x_norm.notna() | 
                y_norm.notna() | 
                z_norm.notna()
            )
            
            # For trendline calculation, ALL THREE norm coordinates must be present
            # We need complete 3D coordinates (X, Y, and Z) for proper trendline plotting
            trendline_mask = (
                x_norm.notna() & 
                y_norm.notna() & 
                z_norm.notna()
            )
            
            # For centroid data, same approach for general validity
            centroid_mask = (
                centroid_x.notna() | 
                centroid_y.notna() | 
                centroid_z.notna()
            )
            # Extra check: ensure points with zero coordinates (0,0,0) are included
            # They are valid data points, not missing data
            zero_norm_mask = (
                (x_norm == 0) & 
                (y_norm == 0) & 
                (z_norm == 0) & 
                x_norm.notna() & 
                y_norm.notna() & 
                z_norm.notna()
            )
            
            zero_centroid_mask = (
                (centroid_x == 0) & 
                (centroid_y == 0) & 
                (centroid_z == 0) & 
                centroid_x.notna() & 
                centroid_y.notna() & 
                centroid_z.notna()
            )
            
            # Explicitly include zero coordinate points in our masks
            norm_mask = norm_mask | zero_norm_mask
            centroid_mask = centroid_mask | zero_centroid_mask
            
            # Combined mask for all valid data
            # Only filter points that are completely missing from both coordinate systems
            data_mask = norm_mask | centroid_mask
            
            # Update the valid_data flag for general data validity
            df['valid_data'] = data_mask
            
            # Set trendline_valid flag based ONLY on norm coordinates
            # This ensures trendline calculations NEVER use centroid coordinates
            # Update the trendline_valid flag based on the detailed mask
            # This overwrites the initial simple definition with a more comprehensive one 
            # that includes specific handling for zero values, etc.
            df['trendline_valid'] = trendline_mask
            # Log information about valid data points in each coordinate system
            norm_points = norm_mask.sum()
            trendline_points = trendline_mask.sum()
            centroid_points = centroid_mask.sum()
            total_valid = data_mask.sum()
            
            logger.info(f"Created data mask with {total_valid} valid points:")
            logger.info(f"  - Norm coordinate system: {norm_points} non-NaN points")
            logger.info(f"  - Centroid coordinate system: {centroid_points} non-NaN points")
            logger.info(f"  - Trendline-valid points: {trendline_points} (using ONLY norm coordinates, requiring ALL THREE coordinates)")
            print(f"Debug: Created data mask with {total_valid} valid points")
            print(f"Debug:   - Norm coordinates: {norm_points} non-NaN points")
            print(f"Debug:   - Centroid coordinates: {centroid_points} non-NaN points")
            print(f"Debug:   - Trendline-valid points: {trendline_points} (requiring complete X, Y, Z norm coordinates)")
        except Exception as e:
            logger.warning(f"Error creating data mask: {str(e)}")
            logger.warning(f"Error creating data mask: {str(e)}")
            # Fallback to valid_data flag if coordinate processing fails
            data_mask = df['valid_data']
            logger.info(f"Using valid_data flag as fallback with {data_mask.sum()} points")
            
            # For trendlines, create a fallback that requires ALL THREE norm coordinates
            # We need complete X, Y, Z coordinates for 3D trendline plotting
            trendline_fallback = (
                df['Xnorm'].notna() & 
                df['Ynorm'].notna() & 
                df['Znorm'].notna()
            )
            df['trendline_valid'] = trendline_fallback
            logger.info(f"Using trendline_fallback as fallback for trendlines with {trendline_fallback.sum()} points")
        # Do not modify Sphere values - they should be preserved from the input file
        # Only set Sphere to None for points with invalid coordinates
        # Make sure data_mask exists even in the exception case
        if not 'data_mask' in locals():
            data_mask = df['valid_data']
            
        df.loc[~data_mask, 'Sphere'] = None
        # Log information about Sphere values to help with debugging
        sphere_values_count = df['Sphere'].notna().sum()
        logger.info(f"Found {sphere_values_count} rows with Sphere values")
        print(f"Debug: Found {sphere_values_count} rows with Sphere values")
        
        # Set colors - preserve any existing colors from input file
        if 'Color' in df.columns:
            existing_colors = df['Color'].copy()
            # Only set default colors for rows without a color
            df.loc[df['Color'].isna(), 'Color'] = df.loc[df['Color'].isna(), 'DataID'].apply(get_initial_color)
        else:
            df['Color'] = df['DataID'].apply(get_initial_color)
        
        # Log Sphere values to verify they're retained from input file
        
        logger.info(f"Processed DataFrame with {len(df)} rows and {len(df.columns)} columns")
        logger.info(f"Coordinate columns present: Xnorm/Ynorm/Znorm and Centroid_X/Y/Z")
        logger.info(f"Using NaN values consistently for missing coordinates in all coordinate systems")
        
        # Log information about Sphere and highlight functionality preservation
        valid_points = df[df['valid_data']]
        logger.info(f"Final DataFrame has {len(valid_points)} valid points with coordinates")
        print(f"Debug: Final DataFrame has {len(valid_points)} valid data points")
        
        spheres = df[df['Sphere'].notna()]
        logger.info(f"Final DataFrame has {len(spheres)} points with Sphere values")
        print(f"Debug: Final DataFrame has {len(spheres)} points with Sphere values")
        
        # Log information about row tracking
        if 'original_row' in df.columns:
            logger.info("Row tracking is active with 'original_row' column")
            min_row = df['original_row'].min()
            max_row = df['original_row'].max()
            logger.info(f"Original row range: {min_row} to {max_row}")
            print(f"Debug: Original row range: {min_row} to {max_row}")
            
            # Check for gaps in row numbers (indicating blank rows were removed)
            unique_rows = sorted(df['original_row'].unique())
            if len(unique_rows) > 1:
                gaps = []
                for i in range(len(unique_rows) - 1):
                    if unique_rows[i+1] - unique_rows[i] > 1:
                        gaps.append((unique_rows[i], unique_rows[i+1]))
                
                if gaps:
                    logger.info(f"Found {len(gaps)} gaps in row numbers: {gaps}")
                    print(f"Debug: Found {len(gaps)} gaps in row numbers: {gaps}")
        else:
            logger.warning("Row tracking 'original_row' column is missing")
        for col in numeric_cols:
            if col in df.columns:
                try:
                    df[col] = df[col].round(4)
                except Exception as e:
                    logger.warning(f"Error rounding column {col}: {str(e)}")
        
        print("\nDebug: Processed DataFrame:")
        print("Final columns:", sorted(df.columns.tolist()))
        print("\nFirst few rows:")
        # Include centroid columns in the display output
        display_cols = ['Xnorm', 'Ynorm', 'Znorm', 'DataID', 'Cluster', 'Centroid_X', 'Centroid_Y', 'Centroid_Z', 'Marker', 'Color']
        print(df[display_cols].head())
        
        # Final log summary
        logger.info(f"Processed DataFrame with {len(df)} rows and {len(df.columns)} columns")
        logger.info(f"Coordinate columns present: Xnorm/Ynorm/Znorm and Centroid_X/Y/Z")
        logger.info(f"Using NaN values consistently for missing coordinates in both coordinate systems")
        
        valid_points = df[df['valid_data']]
        logger.info(f"Final DataFrame has {len(valid_points)} valid points with coordinates")
        print(f"Debug: Final DataFrame has {len(valid_points)} valid data points")
        
        # Log additional helpful debugging information
        # Log additional helpful debugging information
        empty_rows = len(df) - len(valid_points)
        logger.info(f"DataFrame has {empty_rows} rows with empty (NaN) coordinates (valid_data=False)")
        print(f"Debug: DataFrame has {empty_rows} rows with empty (NaN) coordinates")
        
        # Report on zero coordinates which are valid data points for trendlines
        zero_norm = df[
            (df['Xnorm'] == 0) & (df['Ynorm'] == 0) & (df['Znorm'] == 0) & 
            df['Xnorm'].notna() & df['Ynorm'].notna() & df['Znorm'].notna()
        ]
        zero_centroid = df[
            (df['Centroid_X'] == 0) & (df['Centroid_Y'] == 0) & (df['Centroid_Z'] == 0) &
            df['Centroid_X'].notna() & df['Centroid_Y'].notna() & df['Centroid_Z'].notna()
        ]
        
        if len(zero_norm) > 0:
            logger.info(f"Found {len(zero_norm)} rows with (0,0,0) normalized coordinates - TREATED AS VALID DATA")
            print(f"Debug: Found {len(zero_norm)} rows with (0,0,0) normalized coordinates - these are VALID points")
        
        if len(zero_centroid) > 0:
            logger.info(f"Found {len(zero_centroid)} rows with (0,0,0) centroid coordinates - TREATED AS VALID DATA")
            print(f"Debug: Found {len(zero_centroid)} rows with (0,0,0) centroid coordinates - these are VALID points")
        
        # Double-check that we have enough valid points for trendlines
        # IMPORTANT: Trendlines ONLY use norm coordinates, NEVER centroid coordinates
        # A point is valid for trendlines if it has ANY non-NaN norm coordinate
        trendline_valid_points = df[df['trendline_valid']]
        logger.info(f"Trendline-capable points: {len(trendline_valid_points)} (using ONLY norm coordinates, requiring complete X, Y, Z set)")
        print(f"Debug: Found {len(trendline_valid_points)} points that can be used for trendlines (requiring ALL THREE X, Y, Z norm coordinates)")
        
        # Report on points with partial norm coordinates (some X/Y/Z missing but not all)
        partial_norm = df[
            df['Xnorm'].notna() | df['Ynorm'].notna() | df['Znorm'].notna()
        ].shape[0]
        complete_norm = df[
            df['Xnorm'].notna() & df['Ynorm'].notna() & df['Znorm'].notna()
        ].shape[0]
        
        # Count points with exactly two valid coordinates (minimum for trendlines)
        two_coord_points = df[
            ((df['Xnorm'].notna() & df['Ynorm'].notna() & df['Znorm'].isna()) |
             (df['Xnorm'].notna() & df['Ynorm'].isna() & df['Znorm'].notna()) |
             (df['Xnorm'].isna() & df['Ynorm'].notna() & df['Znorm'].notna()))
        ].shape[0]
        
        logger.info(f"Points by coordinate completeness:")
        logger.info(f"  - With all 3 norm coordinates: {complete_norm}")
        logger.info(f"  - With exactly 2 norm coordinates: {two_coord_points}")
        logger.info(f"  - With at least 1 norm coordinate: {partial_norm}")
        print(f"Debug: Points with all 3 norm coordinates: {complete_norm}")
        print(f"Debug: Points with exactly 2 norm coordinates: {two_coord_points}")
        
        if partial_norm > complete_norm:
            logger.info(f"Found {partial_norm - complete_norm} rows with partial norm coordinates (some X/Y/Z values missing)")
            print(f"Debug: Found {partial_norm - complete_norm} rows with partial norm coordinates")
        spheres = df[df['Sphere'].notna()]
        logger.info(f"Final DataFrame has {len(spheres)} points with Sphere values")
        print(f"Debug: Final DataFrame has {len(spheres)} points with Sphere values")
        
        # Return the processed DataFrame
        return df
        
    except Exception as e:
        print(f"Error processing DataFrame: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

