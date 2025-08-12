#!/usr/bin/env python3
"""
Debug script to analyze why calibration corrections aren't bridging the color gap.
This will help identify what's causing the persistent variance between expected and measured values.
"""

import os
import json
from PIL import Image
import numpy as np
from utils.image_processor import load_image
from utils.color_calibration import ColorCalibrator
from color_correction_calculator import correct_color

def test_color_pipeline(image_path=None):
    """Test the complete color analysis pipeline to find where the gap occurs."""
    
    print("=== STAMPZ CALIBRATION GAP DIAGNOSTIC ===")
    print()
    
    # Test 1: Basic color reference values
    print("TEST 1: Reference Color Values")
    reference_colors = {
        'Pure Red': (255, 0, 0),
        'Pure Green': (0, 255, 0), 
        'Pure Blue': (0, 0, 255),
        'White': (255, 255, 255),
        'Gray 50%': (128, 128, 128),
        'Black': (0, 0, 0)
    }
    
    for name, rgb in reference_colors.items():
        print(f"  {name}: {rgb}")
    print()
    
    # Test 2: Image loading and color profile handling
    if image_path and os.path.exists(image_path):
        print(f"TEST 2: Image Loading Analysis - {os.path.basename(image_path)}")
        
        # Load with basic PIL
        basic_img = Image.open(image_path)
        print(f"  Basic PIL load: Mode={basic_img.mode}, Size={basic_img.size}")
        if hasattr(basic_img, 'info') and 'icc_profile' in basic_img.info:
            print(f"  ICC Profile present: {len(basic_img.info['icc_profile'])} bytes")
        else:
            print("  No ICC Profile found")
        
        # Load with StampZ image processor
        stampz_img = load_image(image_path)
        print(f"  StampZ load: Mode={stampz_img.mode}, Size={stampz_img.size}")
        
        # Compare pixel sampling at same location
        test_x, test_y = stampz_img.width // 4, stampz_img.height // 4  # Top-left red area
        basic_pixel = basic_img.getpixel((test_x, test_y))
        stampz_pixel = stampz_img.getpixel((test_x, test_y))
        
        print(f"  Sample pixel ({test_x}, {test_y}):")
        print(f"    Basic PIL: {basic_pixel}")
        print(f"    StampZ:    {stampz_pixel}")
        
        pixel_diff = tuple(s - b for s, b in zip(stampz_pixel, basic_pixel))
        print(f"    Difference: {pixel_diff}")
        print()
    
    # Test 3: Current calibration methods
    print("TEST 3: Current Calibration Methods")
    
    # Test the universal correction from color_correction_calculator
    test_rgb = (255, 234, 57)  # Example problematic green reading
    universal_corrected, method = correct_color(*test_rgb, method='universal')
    print(f"  Universal method:")
    print(f"    Input:  {test_rgb}")
    print(f"    Output: {universal_corrected}")
    print(f"    Method: {method}")
    
    # Test dynamic calibration if available
    try:
        dynamic_corrected, method = correct_color(*test_rgb, method='dynamic')
        print(f"  Dynamic method:")
        print(f"    Input:  {test_rgb}")  
        print(f"    Output: {dynamic_corrected}")
        print(f"    Method: {method}")
    except:
        print("  Dynamic method: Not available (no calibration file)")
    
    print()
    
    # Test 4: Analyze calibration file if it exists
    calibration_files = ['stampz_calibration.json', 'calibration_data.json']
    for cal_file in calibration_files:
        if os.path.exists(cal_file):
            print(f"TEST 4: Calibration File Analysis - {cal_file}")
            try:
                with open(cal_file, 'r') as f:
                    cal_data = json.load(f)
                
                print(f"  File structure:")
                for key in cal_data.keys():
                    print(f"    {key}: {type(cal_data[key])}")
                
                if 'calibration_matrix' in cal_data:
                    matrix = cal_data['calibration_matrix']
                    if 'corrections' in matrix:
                        corrections = matrix['corrections']
                        print(f"  Correction values:")
                        print(f"    Red:   {corrections.get('red_correction', 'N/A')}")
                        print(f"    Green: {corrections.get('green_correction', 'N/A')}")
                        print(f"    Blue:  {corrections.get('blue_correction', 'N/A')}")
                
                if 'wizard_data' in cal_data and 'measured_colors' in cal_data['wizard_data']:
                    measured = cal_data['wizard_data']['measured_colors']
                    print(f"  Measured colors from wizard:")
                    for color, rgb in measured.items():
                        expected = reference_colors.get(f"Pure {color.title()}", reference_colors.get(color.title(), "Unknown"))
                        deviation = tuple(m - e for m, e in zip(rgb, expected)) if expected != "Unknown" else "N/A"
                        print(f"    {color}: {rgb} (deviation: {deviation})")
                
            except Exception as e:
                print(f"    Error reading calibration file: {e}")
            print()
            break
    else:
        print("TEST 4: No calibration files found")
        print()
    
    # Test 5: Color space analysis
    print("TEST 5: Color Space Analysis")
    
    # Check if the issue is with color space assumptions
    sample_colors = [
        ("Pure Red", (255, 0, 0)),
        ("Pure Green", (0, 255, 0)),
        ("Pure Blue", (0, 0, 255)),
        ("Your reported Green", (0, 255, 57)),  # Your problematic reading
        ("Your reported Blue", (24, 17, 247))   # Your problematic reading
    ]
    
    print("  Converting to different color spaces:")
    for name, rgb in sample_colors:
        try:
            # Convert to LAB color space for perceptual analysis
            from colorspacious import cspace_convert
            lab = cspace_convert(rgb, "sRGB1", "CIELab")
            print(f"    {name:20} RGB{rgb} -> LAB({lab[0]:.1f}, {lab[1]:.1f}, {lab[2]:.1f})")
        except ImportError:
            print(f"    {name:20} RGB{rgb} -> LAB conversion not available (need colorspacious)")
    print()
    
    # Test 6: Gap calculation
    print("TEST 6: Gap Analysis")
    
    # Simulate your reported measurements vs expectations
    your_measurements = {
        'red': (255, 0, 0),      # Close to perfect
        'green': (0, 255, 57),   # 57-point blue contamination  
        'blue': (24, 17, 247)    # 24 red, 17 green contamination, 8 blue deficit
    }
    
    expected = {
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255)
    }
    
    print("  Raw deviations:")
    total_error_before = 0
    for color in ['red', 'green', 'blue']:
        meas = your_measurements[color]
        exp = expected[color]
        dev = tuple(m - e for m, e in zip(meas, exp))
        magnitude = np.sqrt(sum(d**2 for d in dev))
        total_error_before += magnitude
        print(f"    {color:6}: measured {meas} vs expected {exp} = deviation {dev} (magnitude: {magnitude:.1f})")
    
    print(f"  Total error before correction: {total_error_before:.1f}")
    
    # Apply current calibration
    print("  After universal correction (-8, -6, -10):")
    total_error_after = 0
    for color in ['red', 'green', 'blue']:
        meas = your_measurements[color]
        corrected = (max(0, meas[0] - 8), max(0, meas[1] - 6), max(0, meas[2] - 10))
        exp = expected[color]
        dev = tuple(c - e for c, e in zip(corrected, exp))
        magnitude = np.sqrt(sum(d**2 for d in dev))
        total_error_after += magnitude
        improvement = np.sqrt(sum((m - e)**2 for m, e in zip(meas, exp))) - magnitude
        print(f"    {color:6}: {meas} -> {corrected} vs {exp} = deviation {dev} (magnitude: {magnitude:.1f}, improvement: {improvement:+.1f})")
    
    print(f"  Total error after correction: {total_error_after:.1f}")
    print(f"  Overall improvement: {total_error_before - total_error_after:+.1f} ({((total_error_before - total_error_after)/total_error_before)*100:+.1f}%)")
    print()
    
    # Test 7: Recommendations
    print("TEST 7: Diagnostic Recommendations")
    
    if total_error_after > 30:  # Still significant error
        print("  ❌ SIGNIFICANT REMAINING ERROR DETECTED")
        print("     Current calibration is insufficient for your system.")
        print()
        print("  Possible causes:")
        print("  1. Color profile conversion issues not fully resolved")
        print("  2. Display has non-linear color response") 
        print("  3. Screenshot method introduces additional color shifts")
        print("  4. Calibration samples don't match actual usage conditions")
        print()
        print("  Recommended solutions:")
        print("  A. ENHANCED CALIBRATION:")
        print("     - Take new screenshots using basic_colors with latest build")
        print("     - Use per-color corrections instead of universal")
        print("     - Include white/gray/black in calibration matrix")
        print()
        print("  B. BYPASS SCREENSHOTS:")
        print("     - Use Digital Color Meter directly on stamp images") 
        print("     - Load stamp images directly into StampZ for analysis")
        print("     - Avoid screenshot workflow entirely")
        print()
        print("  C. CUSTOM CORRECTION MATRIX:")
        print("     - Create per-color corrections based on your specific measurements")
        print("     - Use multiplicative corrections for non-linear responses")
    else:
        print("  ✓ Current calibration shows good improvement")
        print("  ✓ Remaining error is within acceptable range")
    
    return {
        'total_error_before': total_error_before,
        'total_error_after': total_error_after,
        'improvement_pct': ((total_error_before - total_error_after)/total_error_before)*100,
        'your_measurements': your_measurements,
        'needs_enhanced_calibration': total_error_after > 30
    }

def create_enhanced_correction_matrix():
    """Create an enhanced correction matrix based on your specific measurements."""
    
    print("\n=== CREATING ENHANCED CORRECTION MATRIX ===")
    
    # Your actual measurements vs expectations
    measurements = {
        'red': {'measured': (255, 0, 0), 'expected': (255, 0, 0)},
        'green': {'measured': (0, 255, 57), 'expected': (0, 255, 0)},
        'blue': {'measured': (24, 17, 247), 'expected': (0, 0, 255)}
    }
    
    # Calculate per-color corrections
    corrections = {}
    
    print("Per-color correction analysis:")
    for color, data in measurements.items():
        measured = data['measured']
        expected = data['expected']
        
        # Calculate both additive and multiplicative corrections
        additive = tuple(e - m for e, m in zip(expected, measured))
        
        # Multiplicative correction (avoid division by zero)
        multiplicative = tuple(
            e / m if m != 0 else 1.0 
            for e, m in zip(expected, measured)
        )
        
        corrections[color] = {
            'additive': additive,
            'multiplicative': multiplicative,
            'hybrid_correction': {
                'red': additive[0] if abs(additive[0]) > 5 else 0,
                'green': additive[1] if abs(additive[1]) > 5 else 0, 
                'blue': additive[2] if abs(additive[2]) > 5 else 0
            }
        }
        
        print(f"  {color}:")
        print(f"    Measured:   {measured}")
        print(f"    Expected:   {expected}")
        print(f"    Additive:   {additive}")
        print(f"    Multiplicative: {multiplicative}")
    
    # Generate specific corrections for your problematic colors
    enhanced_matrix = {
        'method': 'enhanced_per_color_correction',
        'corrections': {
            # Red is already accurate
            'red_correction': 0,
            'green_correction': -57,  # Remove blue contamination
            'blue_correction': +8,    # Boost blue, remove red/green contamination
            
            # Per-color specific corrections
            'per_color_corrections': {
                'green_dominant': {
                    'red_correction': 0,
                    'green_correction': 0, 
                    'blue_correction': -57  # Specifically address blue contamination in green
                },
                'blue_dominant': {
                    'red_correction': -24,   # Remove red contamination
                    'green_correction': -17, # Remove green contamination
                    'blue_correction': +8    # Boost blue
                },
                'red_dominant': {
                    'red_correction': 0,
                    'green_correction': 0,
                    'blue_correction': 0
                }
            }
        },
        'confidence': 'custom_tuned_for_user_system'
    }
    
    print("\nEnhanced correction matrix:")
    print(json.dumps(enhanced_matrix, indent=2))
    
    # Save enhanced calibration
    with open('stampz_calibration_enhanced.json', 'w') as f:
        json.dump({
            'calibration_matrix': enhanced_matrix,
            'application': 'StampZ',
            'version': '1.1_enhanced',
            'notes': 'Custom calibration matrix for significant color contamination issues',
            'test_data': measurements
        }, f, indent=2)
    
    print("\nEnhanced calibration saved to: stampz_calibration_enhanced.json")
    
    # Test the enhanced corrections
    print("\nTesting enhanced corrections:")
    for color, data in measurements.items():
        measured = data['measured']
        expected = data['expected']
        
        if color == 'green':
            corrected = (measured[0], measured[1], max(0, measured[2] - 57))
        elif color == 'blue':  
            corrected = (max(0, measured[0] - 24), max(0, measured[1] - 17), min(255, measured[2] + 8))
        else:  # red
            corrected = measured
        
        error_before = np.sqrt(sum((m - e)**2 for m, e in zip(measured, expected)))
        error_after = np.sqrt(sum((c - e)**2 for c, e in zip(corrected, expected)))
        improvement = error_before - error_after
        
        print(f"  {color}: {measured} -> {corrected} (error: {error_before:.1f} -> {error_after:.1f}, improvement: {improvement:+.1f})")

if __name__ == "__main__":
    # Run diagnostic
    print("Starting calibration gap diagnostic...")
    print("=" * 60)
    
    # Look for calibration grid images
    grid_files = []
    for file in os.listdir('.'):
        if 'calibration' in file.lower() and file.lower().endswith(('.png', '.jpg', '.jpeg')):
            grid_files.append(file)
    
    if grid_files:
        print(f"Found calibration images: {grid_files}")
        test_image = grid_files[0]
    else:
        print("No calibration images found. Testing without image analysis.")
        test_image = None
    
    # Run the diagnostic
    results = test_color_pipeline(test_image)
    
    # Create enhanced correction if needed
    if results['needs_enhanced_calibration']:
        create_enhanced_correction_matrix()
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("1. Use the enhanced calibration file: stampz_calibration_enhanced.json")
        print("2. Replace your current calibration with this enhanced version")
        print("3. Test color measurements with the new corrections")
        print("4. If still not sufficient, consider avoiding screenshots entirely")
    
    print("\nDiagnostic complete!")
