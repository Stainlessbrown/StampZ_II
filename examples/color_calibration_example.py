#!/usr/bin/env python3
"""
StampZ Color Calibration Example
Demonstrates how to calibrate for color drift using reference colors.

This addresses your specific issue where green (0,253,0) reads as (0,241,0).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.dynamic_color_calibration import DynamicColorCalibrator

def demonstrate_your_calibration_issue():
    """Demonstrate calibration using your specific measurements."""
    
    print("=== SOLVING YOUR SPECIFIC COLOR DRIFT ISSUE ===")
    print()
    print("You reported:")
    print("  - Green in library: (0, 253, 0)")
    print("  - Green measured: (0, 241, 0)")
    print("  - Drift: -12 in green channel")
    print()
    
    # Initialize calibrator with your database
    try:
        calibrator = DynamicColorCalibrator()
        print(f"✓ Loaded reference colors from database")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Your measurements (simulate what you might measure)
    your_measurements = {
        'Pure Green': (0, 241, 0),      # Your reported measurement
        'Pure Red': (254, 1, 0),        # Slightly off red
        'Pure Blue': (0, 5, 248),       # Slightly off blue  
        'White': (255, 250, 255),       # White with slight green deficit
        'Gray 50%': (128, 125, 130)     # Gray with channel imbalance
    }
    
    print("Simulated measurements (based on your reported drift):")
    for color, rgb in your_measurements.items():
        print(f"  {color}: {rgb}")
    
    # Process measurements and create calibration
    print("\nProcessing measurements...")
    measurements = calibrator.measure_reference_colors(your_measurements)
    
    print("\nCalculating calibration matrix...")
    matrix = calibrator.calculate_calibration_matrix(measurements)
    
    if matrix:
        # Show calibration report
        print("\n" + "="*60)
        report = calibrator.generate_calibration_report()
        print(report)
        
        # Test the calibration on your specific green measurement
        print("\n" + "="*60)
        print("TESTING ON YOUR SPECIFIC ISSUE:")
        print()
        
        # Your original measurement
        original_green = (0, 241, 0)
        corrected_green = calibrator.apply_calibration(original_green)
        expected_green = (0, 253, 0)  # From your library
        
        print(f"Original measurement:  {original_green}")
        print(f"After calibration:     {corrected_green}")
        print(f"Expected (library):    {expected_green}")
        
        # Calculate improvement
        original_error = abs(original_green[1] - expected_green[1])
        corrected_error = abs(corrected_green[1] - expected_green[1])
        improvement = original_error - corrected_error
        
        print(f"\nGreen channel error:")
        print(f"  Before: {original_error} units off")
        print(f"  After:  {corrected_error} units off")
        print(f"  Improvement: {improvement} units ({improvement/original_error*100:.1f}%)")
        
        # Show the correction formula
        corrections = matrix['corrections']
        print(f"\nYour correction formula:")
        print(f"  corrected_red   = measured_red   + {corrections['red_correction']:+.1f}")
        print(f"  corrected_green = measured_green + {corrections['green_correction']:+.1f}")
        print(f"  corrected_blue  = measured_blue  + {corrections['blue_correction']:+.1f}")
        
        # Apply to other examples
        print(f"\nTesting calibration on other colors:")
        test_colors = {
            'Red': (254, 1, 0),
            'Blue': (0, 5, 248),
            'White': (255, 250, 255)
        }
        
        for color, measured in test_colors.items():
            corrected = calibrator.apply_calibration(measured)
            print(f"  {color}: {measured} → {corrected}")

def create_practical_calibration_guide():
    """Create a practical guide for your specific use case."""
    
    print("\n" + "="*60)
    print("PRACTICAL CALIBRATION GUIDE FOR YOUR SETUP")
    print("="*60)
    
    guide = """
STEP-BY-STEP CALIBRATION FOR YOUR ISSUE:

1. PREPARE REFERENCE COLORS:
   - Open your basic_colors.db in StampZ
   - Display the reference colors on screen
   - Use known pure colors: Red(255,0,0), Green(0,255,0), Blue(0,0,255)

2. CAPTURE AND MEASURE:
   - Take screenshots of each reference color
   - Use StampZ to analyze each screenshot
   - Record the measured RGB values

3. CREATE CALIBRATION:
   - Run: python examples/color_calibration_example.py
   - Enter your measured values when prompted
   - Save the calibration matrix

4. APPLY CORRECTIONS:
   There are several ways to use the calibration:
   
   A) Manual Method (immediate):
      - Note the correction values (e.g., +12 for green)
      - Manually adjust your readings: measured_green + 12
   
   B) Update color_correction_calculator.py:
      - Replace the hardcoded corrections with your calibrated values
      - Use the updated script for all future measurements
   
   C) Integrate into StampZ GUI:
      - Add calibration loading to your analysis workflow
      - Apply corrections automatically during color analysis

5. VALIDATE:
   - Test with known colors not used in calibration
   - Check accuracy across different color ranges
   - Re-calibrate if you change display settings

ADDRESSING YOUR SPECIFIC ISSUE:
Your green drift of -12 units suggests either:
- Display color temperature is too warm
- Screenshot compression artifacts
- sRGB color profile mismatch

The calibration will correct this systematically across all colors.
"""
    
    print(guide)

if __name__ == "__main__":
    # Run the demonstration
    demonstrate_your_calibration_issue()
    
    # Show practical guide
    create_practical_calibration_guide()
    
    print(f"\n{'='*60}")
    print("Next steps:")
    print("1. Run the interactive calibration:")
    print("   python utils/dynamic_color_calibration.py")
    print("2. Measure your reference colors and enter the values")
    print("3. Apply the generated corrections to your workflow")
    print("4. Test with real stamp color analysis")
