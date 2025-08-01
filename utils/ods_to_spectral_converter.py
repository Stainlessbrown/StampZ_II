#!/usr/bin/env python3
"""
ODS to Spectral Analysis Converter for StampZ
Converts existing ODS color analysis files to ColorMeasurement format for spectral analysis.
"""

import pandas as pd
import os
import sys
from datetime import datetime
from typing import List, Tuple, Optional

# Add the parent directory to path so we can import StampZ modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.color_analyzer import ColorMeasurement
from utils.spectral_analyzer import SpectralAnalyzer, analyze_spectral_deviation_from_measurements

def load_ods_data(file_path: str) -> pd.DataFrame:
    """Load ODS file and return DataFrame."""
    try:
        df = pd.read_excel(file_path, engine='odf')
        print(f"Loaded ODS file: {os.path.basename(file_path)}")
        print(f"Shape: {df.shape}")
        return df
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def identify_columns(df: pd.DataFrame) -> dict:
    """
    Identify which columns contain L*a*b* and RGB data based on data analysis.
    """
    print("\nAnalyzing columns to identify L*a*b* and RGB data...")
    
    # Look for numeric columns
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    
    # Analyze data ranges to identify likely L*a*b* and RGB columns
    column_analysis = {}
    for col in numeric_cols:
        non_null_data = df[col].dropna()
        if len(non_null_data) > 0:
            min_val = non_null_data.min()
            max_val = non_null_data.max()
            mean_val = non_null_data.mean()
            column_analysis[col] = {
                'min': min_val,
                'max': max_val, 
                'mean': mean_val,
                'count': len(non_null_data)
            }
            print(f"Column {col}: min={min_val:.2f}, max={max_val:.2f}, mean={mean_val:.2f}, count={len(non_null_data)}")
    
    # Heuristic identification
    # L* typically ranges 0-100
    # a* and b* typically range -128 to +127 but commonly -50 to +50
    # RGB typically ranges 0-255
    
    lab_candidates = []
    rgb_candidates = []
    
    for col, stats in column_analysis.items():
        if stats['count'] < 10:  # Skip columns with too little data
            continue
            
        # L* channel: 0-100 range, positive values
        if 0 <= stats['min'] and stats['max'] <= 100 and stats['mean'] > 10:
            lab_candidates.append((col, 'L', stats))
        
        # a* and b* channels: can be negative, typically smaller range
        elif -60 <= stats['min'] <= 20 and -20 <= stats['max'] <= 60:
            lab_candidates.append((col, 'ab', stats))
        
        # RGB channels: 0-255 range, typically higher values
        elif 0 <= stats['min'] and 200 <= stats['max'] <= 255:
            rgb_candidates.append((col, 'RGB', stats))
        elif 0 <= stats['min'] and 100 <= stats['max'] <= 200 and stats['mean'] > 50:
            rgb_candidates.append((col, 'RGB', stats))
    
    print(f"\nL*a*b* candidates: {[c[0] for c in lab_candidates]}")
    print(f"RGB candidates: {[c[0] for c in rgb_candidates]}")
    
    # Based on the sample data, make educated guesses
    # From the sample: columns 0,1,2 look like L*a*b* and columns 9,10,11 look like RGB
    result = {
        'L_star': df.columns[0] if len(df.columns) > 0 else None,
        'a_star': df.columns[1] if len(df.columns) > 1 else None, 
        'b_star': df.columns[2] if len(df.columns) > 2 else None,
        'R': df.columns[9] if len(df.columns) > 9 else None,
        'G': df.columns[10] if len(df.columns) > 10 else None,
        'B': df.columns[11] if len(df.columns) > 11 else None
    }
    
    print(f"\nColumn mapping:")
    for key, col in result.items():
        if col is not None:
            print(f"  {key}: {col}")
    
    return result

def convert_to_color_measurements(df: pd.DataFrame, column_mapping: dict, dataset_name: str) -> List[ColorMeasurement]:
    """Convert DataFrame to ColorMeasurement objects."""
    measurements = []
    
    # Get column names
    l_col = column_mapping['L_star']
    a_col = column_mapping['a_star'] 
    b_col = column_mapping['b_star']
    r_col = column_mapping['R']
    g_col = column_mapping['G']
    b_rgb_col = column_mapping['B']
    
    print(f"\nConverting {len(df)} rows to ColorMeasurement objects...")
    
    for i, row in df.iterrows():
        try:
            # Extract L*a*b* values
            L = row[l_col] if pd.notna(row[l_col]) else 50.0
            a = row[a_col] if pd.notna(row[a_col]) else 0.0
            b = row[b_col] if pd.notna(row[b_col]) else 0.0
            
            # Extract RGB values
            R = int(row[r_col]) if pd.notna(row[r_col]) else 128
            G = int(row[g_col]) if pd.notna(row[g_col]) else 128
            B = int(row[b_rgb_col]) if pd.notna(row[b_rgb_col]) else 128
            
            # Create ColorMeasurement object
            measurement = ColorMeasurement(
                coordinate_id=i,
                coordinate_point=i + 1,  # 1-based
                position=(0.0, 0.0),  # No position data in ODS
                rgb=(float(R), float(G), float(B)),
                lab=(L, a, b),
                sample_area={'type': 'unknown', 'size': (10, 10), 'anchor': 'center'},
                measurement_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                notes=f"{dataset_name} measurement {i+1}"
            )
            
            measurements.append(measurement)
            
        except Exception as e:
            print(f"Warning: Failed to process row {i}: {e}")
            continue
    
    print(f"Successfully converted {len(measurements)} measurements")
    return measurements

def run_spectral_analysis(measurements: List[ColorMeasurement], dataset_name: str, output_dir: str = None):
    """Run spectral analysis on the converted measurements."""
    if not measurements:
        print("No measurements to analyze")
        return
    
    print(f"\n{'='*60}")
    print(f"SPECTRAL ANALYSIS FOR {dataset_name.upper()}")
    print(f"{'='*60}")
    print(f"Analyzing {len(measurements)} color measurements...")
    
    # Initialize spectral analyzer
    spectral_analyzer = SpectralAnalyzer()
    
    # 1. Wavelength deviation analysis
    print(f"\n1. WAVELENGTH DEVIATION ANALYSIS")
    print(f"{'-'*40}")
    analyze_spectral_deviation_from_measurements(measurements)
    
    # 2. Spectral response analysis for different illuminants
    print(f"\n2. SPECTRAL RESPONSE ANALYSIS")
    print(f"{'-'*40}")
    
    illuminants = ['D65', 'A', 'F2']  # Daylight, Incandescent, Fluorescent
    spectral_results = {}
    
    for illuminant in illuminants:
        print(f"\n--- Analysis under {illuminant} illuminant ---")
        spectral_data = spectral_analyzer.analyze_spectral_response(measurements, illuminant)
        spectral_results[illuminant] = spectral_data
        
        sample_count = len(set(m.sample_id for m in spectral_data))
        wavelength_count = len(set(m.wavelength for m in spectral_data))
        
        print(f"Generated {len(spectral_data)} spectral measurements")
        print(f"Covers {sample_count} samples across {wavelength_count} wavelength points")
        
        if spectral_data:
            sample_1_data = [m for m in spectral_data if m.sample_id == 'sample_1']
            if sample_1_data:
                print(f"Spectral range: {min(m.wavelength for m in sample_1_data):.0f}-{max(m.wavelength for m in sample_1_data):.0f}nm")
                
                max_r = max(sample_1_data, key=lambda m: m.rgb_response[0])
                max_g = max(sample_1_data, key=lambda m: m.rgb_response[1]) 
                max_b = max(sample_1_data, key=lambda m: m.rgb_response[2])
                
                print(f"Peak responses - R: {max_r.wavelength:.0f}nm, G: {max_g.wavelength:.0f}nm, B: {max_b.wavelength:.0f}nm")
    
    # 3. Metamerism analysis
    print(f"\n3. METAMERISM ANALYSIS")
    print(f"{'-'*40}")
    print("Analyzing how colors appear under different lighting conditions...")
    
    # Sample first 10 measurements for metamerism comparison
    sample_limit = min(10, len(measurements))
    for i in range(min(5, sample_limit)):
        for j in range(i+1, min(5, sample_limit)):
            metamerism_index = spectral_analyzer.calculate_metamerism_index(measurements[i], measurements[j])
            
            print(f"Sample {i+1} vs Sample {j+1}: Metamerism Index = {metamerism_index:.3f}")
            if metamerism_index > 2.0:
                print("  → High metamerism - colors may appear different under various lights")
            elif metamerism_index > 1.0:
                print("  → Moderate metamerism - some color shift possible")
            else:
                print("  → Low metamerism - colors should appear consistent")
    
    # 4. Export results if output directory specified
    if output_dir:
        print(f"\n4. EXPORTING RESULTS")
        print(f"{'-'*40}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Export spectral data for each illuminant
        for illuminant, spectral_data in spectral_results.items():
            export_filename = os.path.join(output_dir, f"{dataset_name}_spectral_{illuminant}_{datetime.now().strftime('%Y%m%d')}.csv")
            success = spectral_analyzer.export_spectral_analysis(spectral_data, export_filename)
            if success:
                print(f"Exported {illuminant} analysis to {os.path.basename(export_filename)}")
        
        # Generate plots if matplotlib is available
        try:
            print("\nGenerating spectral response plots...")
            d65_data = spectral_results.get('D65', [])
            if d65_data:
                # Set up plot saving
                plot_filename = os.path.join(output_dir, f"{dataset_name}_spectral_plot_{datetime.now().strftime('%Y%m%d')}.png")
                spectral_analyzer._save_plot_path = plot_filename
                
                # Limit plotting to reasonable number of samples for readability
                plot_samples = min(20, len(measurements))
                spectral_analyzer.plot_spectral_response(d65_data, max_samples=plot_samples)
                print(f"Spectral response plots generated and saved to {os.path.basename(plot_filename)}!")
                print(f"(showing {plot_samples} of {len(measurements)} samples)")
                
                # Clean up the save path attribute
                del spectral_analyzer._save_plot_path
        except ImportError:
            print("Install matplotlib to generate plots: pip install matplotlib")
        except Exception as e:
            print(f"Could not generate plots: {e}")
    
    print(f"\n{'='*60}")
    print("PRACTICAL APPLICATIONS FOR PHILATELIC ANALYSIS")
    print(f"{'='*60}")
    print("This spectral analysis can help you:")
    print("• Identify pigments with unique spectral signatures")
    print("• Detect printing method differences (line-engraved vs lithographic)")
    print("• Analyze paper aging effects on color reproduction")
    print("• Compare stamps printed in different eras with different inks")
    print("• Identify potential forgeries through spectral inconsistencies")
    print("• Optimize photography lighting for accurate color capture")

def main():
    """Main function to process ODS files."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert ODS color data to spectral analysis')
    parser.add_argument('ods_file', help='Path to ODS file')
    parser.add_argument('--output-dir', '-o', help='Output directory for results')
    parser.add_argument('--dataset-name', '-n', help='Name for the dataset')
    args = parser.parse_args()
    
    if not os.path.exists(args.ods_file):
        print(f"Error: File {args.ods_file} not found")
        return
    
    # Load ODS data
    df = load_ods_data(args.ods_file)
    if df is None:
        return
    
    # Identify columns
    column_mapping = identify_columns(df)
    
    # Determine dataset name
    dataset_name = args.dataset_name or os.path.splitext(os.path.basename(args.ods_file))[0]
    
    # Convert to ColorMeasurement objects
    measurements = convert_to_color_measurements(df, column_mapping, dataset_name)
    
    # Run spectral analysis
    run_spectral_analysis(measurements, dataset_name, args.output_dir)

if __name__ == "__main__":
    main()
