#!/usr/bin/env python3
"""
Example: Spectral Analysis with StampZ
Demonstrate how to analyze spectral response characteristics
of stamp color measurements.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.color_analyzer import ColorAnalyzer, ColorMeasurement, PrintType
from utils.spectral_analyzer import SpectralAnalyzer, analyze_spectral_deviation_from_measurements
from PIL import Image

def run_spectral_analysis_example():
    """
    Example of performing spectral analysis on stamp color measurements.
    """
    print("=== StampZ Spectral Analysis Example ===")
    print("This example demonstrates how to analyze RGB channel")
    print("behavior across the visible light spectrum.")
    print()
    
    # Create some example color measurements (would normally come from your analysis)
    example_measurements = [
        # Simulate measurements across different color regions
        ColorMeasurement(
            coordinate_id=0,
            coordinate_point=1,
            position=(100, 100),
            rgb=(220, 85, 45),      # Red-orange (simulates 620-650nm dominant)
            lab=(55.2, 45.8, 38.9),
            sample_area={'type': 'rectangle', 'size': (20, 20), 'anchor': 'center'},
            measurement_date="2024-01-01 10:00:00",
            notes="Red stamp color"
        ),
        ColorMeasurement(
            coordinate_id=1,
            coordinate_point=2,
            position=(150, 150),
            rgb=(45, 180, 75),      # Green (simulates 520-550nm dominant)
            lab=(65.8, -42.3, 35.1),
            sample_area={'type': 'rectangle', 'size': (20, 20), 'anchor': 'center'},
            measurement_date="2024-01-01 10:01:00",
            notes="Green stamp color"
        ),
        ColorMeasurement(
            coordinate_id=2,
            coordinate_point=3,
            position=(200, 200),
            rgb=(55, 95, 185),      # Blue (simulates 450-480nm dominant)
            lab=(42.1, 18.5, -48.2),
            sample_area={'type': 'rectangle', 'size': (20, 20), 'anchor': 'center'},
            measurement_date="2024-01-01 10:02:00",
            notes="Blue stamp color"
        ),
        ColorMeasurement(
            coordinate_id=3,
            coordinate_point=4,
            position=(250, 250),
            rgb=(180, 160, 45),     # Yellow (simulates 570-590nm dominant)
            lab=(68.4, -8.2, 58.7),
            sample_area={'type': 'rectangle', 'size': (20, 20), 'anchor': 'center'},
            measurement_date="2024-01-01 10:03:00",
            notes="Yellow stamp color"
        ),
        ColorMeasurement(
            coordinate_id=4,
            coordinate_point=5,
            position=(300, 300),
            rgb=(140, 85, 180),     # Purple/Violet (simulates 380-420nm + 650nm)
            lab=(48.3, 35.2, -38.9),
            sample_area={'type': 'rectangle', 'size': (20, 20), 'anchor': 'center'},
            measurement_date="2024-01-01 10:04:00",
            notes="Purple stamp color"
        ),
        ColorMeasurement(
            coordinate_id=5,
            coordinate_point=6,
            position=(350, 350),
            rgb=(195, 145, 95),     # Brown/Orange (broad spectrum, paper-influenced)
            lab=(62.8, 15.4, 28.3),
            sample_area={'type': 'rectangle', 'size': (20, 20), 'anchor': 'center'},
            measurement_date="2024-01-01 10:05:00",
            notes="Brown ink on paper"
        )
    ]
    
    print(f"Analyzing {len(example_measurements)} color measurements...")
    print()
    
    # Initialize spectral analyzer
    spectral_analyzer = SpectralAnalyzer()
    
    # 1. Analyze wavelength deviation patterns
    print("1. WAVELENGTH DEVIATION ANALYSIS")
    print("This shows how RGB channels deviate across spectral regions:")
    print()
    analyze_spectral_deviation_from_measurements(example_measurements)
    print()
    
    # 2. Generate spectral response data
    print("2. SPECTRAL RESPONSE ANALYSIS")
    print("Generating spectral response curves for different illuminants...")
    print()
    
    illuminants = ['D65', 'A', 'F2']  # Daylight, Incandescent, Fluorescent
    
    for illuminant in illuminants:
        print(f"--- Analysis under {illuminant} illuminant ---")
        spectral_data = spectral_analyzer.analyze_spectral_response(example_measurements, illuminant)
        
        # Calculate some basic statistics
        sample_count = len(set(m.sample_id for m in spectral_data))
        wavelength_count = len(set(m.wavelength for m in spectral_data))
        
        print(f"Generated {len(spectral_data)} spectral measurements")
        print(f"Covers {sample_count} samples across {wavelength_count} wavelength points")
        
        # Show sample spectral characteristics
        if spectral_data:
            sample_1_data = [m for m in spectral_data if m.sample_id == 'sample_1']
            print(f"Sample 1 spectral range: {min(m.wavelength for m in sample_1_data):.0f}-{max(m.wavelength for m in sample_1_data):.0f}nm")
            
            # Find peak response wavelengths for each channel
            max_r_response = max(sample_1_data, key=lambda m: m.rgb_response[0])
            max_g_response = max(sample_1_data, key=lambda m: m.rgb_response[1])
            max_b_response = max(sample_1_data, key=lambda m: m.rgb_response[2])
            
            print(f"Peak responses - R: {max_r_response.wavelength:.0f}nm, G: {max_g_response.wavelength:.0f}nm, B: {max_b_response.wavelength:.0f}nm")
        print()
    
    # 3. Metamerism analysis
    print("3. METAMERISM ANALYSIS")
    print("Analyzing how colors appear under different lighting conditions...")
    print()
    
    for i, measurement1 in enumerate(example_measurements[:3]):  # Compare first 3 samples
        for j, measurement2 in enumerate(example_measurements[i+1:4], i+1):
            metamerism_index = spectral_analyzer.calculate_metamerism_index(measurement1, measurement2)
            color1_note = measurement1.notes.split()[0] if measurement1.notes else f"Sample {i+1}"
            color2_note = measurement2.notes.split()[0] if measurement2.notes else f"Sample {j+1}"
            
            print(f"{color1_note} vs {color2_note}: Metamerism Index = {metamerism_index:.3f}")
            if metamerism_index > 2.0:
                print("  ^ High metamerism - colors may appear different under various lights")
            elif metamerism_index > 1.0:
                print("  ^ Moderate metamerism - some color shift possible")
            else:
                print("  ^ Low metamerism - colors should appear consistent")
    
    print()
    
    # 4. Export results
    print("4. EXPORT CAPABILITIES")
    print("You can export spectral analysis data for further analysis...")
    
    # Generate spectral data for export
    export_data = spectral_analyzer.analyze_spectral_response(example_measurements, 'D65')
    
    # Example export (commented out to avoid creating files in this demo)
    # export_filename = "spectral_analysis_results.csv"
    # success = spectral_analyzer.export_spectral_analysis(export_data, export_filename)
    # if success:
    #     print(f"Data exported to {export_filename}")
    
    print(f"Generated {len(export_data)} data points for export")
    print("Includes wavelength, RGB responses, relative responses, and illuminant data")
    print()
    
    print("=== PRACTICAL APPLICATIONS ===")
    print()
    print("This spectral analysis can help you:")
    print("• Identify pigments with unique spectral signatures")
    print("• Detect printing method differences (line-engraved vs lithographic)")
    print("• Analyze paper aging effects on color reproduction")
    print("• Compare stamps printed in different eras with different inks")
    print("• Identify potential forgeries through spectral inconsistencies")
    print("• Optimize photography lighting for accurate color capture")
    print()
    
    print("=== INTEGRATION WITH STAMPZ ===")
    print()
    print("To use with your existing StampZ workflow:")
    print("1. Perform normal color analysis on your stamp")
    print("2. Extract ColorMeasurement objects from your analysis")
    print("3. Feed them into SpectralAnalyzer for advanced analysis")
    print("4. Use the results to understand spectral characteristics")
    print("5. Export data for scientific analysis or documentation")

def analyze_real_stampz_data(coordinate_set_name: str, image_path: str = None):
    """
    Example of how to perform spectral analysis on real StampZ data.
    
    Args:
        coordinate_set_name: Name of existing coordinate set in StampZ
        image_path: Optional path to image file for fresh analysis
    """
    print(f"=== REAL STAMPZ SPECTRAL ANALYSIS ===")
    print(f"Analyzing coordinate set: {coordinate_set_name}")
    print()
    
    # Initialize analyzers
    color_analyzer = ColorAnalyzer(print_type=PrintType.SOLID_PRINTED)
    spectral_analyzer = SpectralAnalyzer()
    
    try:
        if image_path and os.path.exists(image_path):
            # Perform fresh analysis
            measurements = color_analyzer.analyze_image_colors(image_path, coordinate_set_name)
        else:
            # Load existing measurements from database
            measurements = color_analyzer.get_color_measurements(coordinate_set_name)
        
        if not measurements:
            print(f"No measurements found for coordinate set '{coordinate_set_name}'")
            print("Please ensure the coordinate set exists and has been analyzed.")
            return
        
        print(f"Found {len(measurements)} color measurements")
        print()
        
        # Perform spectral deviation analysis
        analyze_spectral_deviation_from_measurements(measurements)
        print()
        
        # Generate spectral response analysis
        print("Generating full spectral response analysis...")
        spectral_data = spectral_analyzer.analyze_spectral_response(measurements, 'D65')
        
        # Optional: Create plots if matplotlib is available
        try:
            spectral_analyzer.plot_spectral_response(spectral_data)
            print("Spectral response plots generated!")
        except ImportError:
            print("Install matplotlib to generate spectral response plots:")
            print("pip install matplotlib")
        except Exception as e:
            print(f"Could not generate plots: {e}")
        
        # Export results
        export_filename = f"spectral_analysis_{coordinate_set_name}.csv"
        if spectral_analyzer.export_spectral_analysis(spectral_data, export_filename):
            print(f"Results exported to {export_filename}")
        
    except Exception as e:
        print(f"Error analyzing StampZ data: {e}")
        print("Make sure the coordinate set exists and has been analyzed.")

if __name__ == "__main__":
    # Run the example with synthetic data
    run_spectral_analysis_example()
    
    print("\n" + "="*60)
    print("To analyze your real StampZ data, uncomment and modify:")
    print("# analyze_real_stampz_data('your_coordinate_set_name', 'path/to/your/image.jpg')")
    print("="*60)
    
    # Example of analyzing real data (commented out)
    # analyze_real_stampz_data('my_stamp_analysis', '/path/to/stamp_image.jpg')
