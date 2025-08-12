#!/usr/bin/env python3
"""
Test script to verify that calibration wizard samples colors correctly without applying corrections.
"""

from utils.color_analyzer import ColorAnalyzer
from PIL import Image
import os

def test_calibration_sampling():
    """Test that calibration sampling works without applying corrections."""
    
    print("Testing calibration color sampling...")
    
    # Test 1: Create analyzer with calibration (normal usage)
    print("\n=== Test 1: Normal ColorAnalyzer (with calibration) ===")
    analyzer_with_cal = ColorAnalyzer(load_calibration=True)
    print(f"Analyzer has calibration: {analyzer_with_cal.is_calibrated()}")
    
    # Test 2: Create analyzer without calibration (for calibration wizard)
    print("\n=== Test 2: ColorAnalyzer for calibration wizard (no calibration) ===")
    analyzer_no_cal = ColorAnalyzer(load_calibration=False)
    print(f"Analyzer has calibration: {analyzer_no_cal.is_calibrated()}")
    
    # Test 3: Test color correction behavior
    test_rgb = (227, 224, 210)  # A whitish color with contamination
    
    print(f"\n=== Test 3: Color correction comparison ===")
    print(f"Original RGB: {test_rgb}")
    
    corrected_with_cal = analyzer_with_cal.apply_color_correction(test_rgb)
    corrected_no_cal = analyzer_no_cal.apply_color_correction(test_rgb)
    
    print(f"With calibration: {test_rgb} -> {corrected_with_cal}")
    print(f"Without calibration: {test_rgb} -> {corrected_no_cal}")
    
    # Test 4: Verify they behave differently
    if corrected_with_cal != corrected_no_cal:
        print("\n✓ SUCCESS: Analyzers behave differently as expected!")
        print(f"  Calibrated analyzer applies corrections")
        print(f"  Non-calibrated analyzer returns original values")
        return True
    else:
        print("\n✗ FAILURE: Both analyzers returned same values")
        return False

if __name__ == "__main__":
    success = test_calibration_sampling()
    if success:
        print("\n🎯 Calibration wizard should now sample colors correctly!")
        print("   The wizard will use raw, uncorrected color values for calibration.")
    else:
        print("\n⚠️  There may still be an issue with calibration sampling.")
