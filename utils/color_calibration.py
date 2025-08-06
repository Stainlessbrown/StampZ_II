#!/usr/bin/env python3
"""
Color calibration utilities for StampZ.
Addresses color accuracy issues when analyzing screenshots or display captures.
"""

import numpy as np
from PIL import Image
from typing import Tuple, Dict, Optional, List
import json
import os

class ColorCalibrator:
    """Handles color calibration and correction for improved accuracy."""
    
    def __init__(self):
        """Initialize color calibrator with common display/screenshot corrections."""
        
        # Common display color temperature adjustments
        self.display_corrections = {
            'generic_srgb': {
                'gamma': 2.2,
                'white_point': (0.3127, 0.3290),  # D65
                'description': 'Standard sRGB display'
            },
            'warm_display': {
                'gamma': 2.2,
                'white_point': (0.3367, 0.3421),  # Warmer white point
                'rgb_matrix': [
                    [0.98, 0.02, 0.00],  # Reduce slight red boost
                    [0.00, 1.00, 0.00],  # Keep green
                    [0.05, 0.00, 0.95]   # Boost blue slightly
                ],
                'description': 'Warm-tinted display correction'
            },
            'screenshot_generic': {
                'gamma': 2.2,
                'rgb_adjustments': {
                    'red': {'gain': 0.98, 'offset': 0},
                    'green': {'gain': 1.00, 'offset': -2},  # Green often too high in screenshots
                    'blue': {'gain': 1.04, 'offset': 8}     # Blue often too low in screenshots
                },
                'description': 'Generic screenshot color correction'
            }
        }
        
        # Known reference colors for calibration
        self.reference_colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'gray_50': (128, 128, 128)
        }
    
    def analyze_color_deviation(self, measured_colors: Dict[str, Tuple[int, int, int]], 
                              reference_colors: Optional[Dict[str, Tuple[int, int, int]]] = None) -> Dict:
        """
        Analyze deviation between measured and reference colors.
        
        Args:
            measured_colors: Dict mapping color names to measured RGB tuples
            reference_colors: Dict of reference RGB values (uses defaults if None)
            
        Returns:
            Analysis dict with deviations and suggested corrections
        """
        if reference_colors is None:
            reference_colors = self.reference_colors
        
        analysis = {
            'deviations': {},
            'avg_deviation': {},
            'correction_matrix': None,
            'recommendations': []
        }
        
        total_r_dev = 0
        total_g_dev = 0  
        total_b_dev = 0
        count = 0
        
        print("=== COLOR DEVIATION ANALYSIS ===")
        print(f"{'Color':<10} {'Expected':<15} {'Measured':<15} {'Deviation':<15}")
        print("-" * 60)
        
        for color_name in reference_colors:
            if color_name in measured_colors:
                ref_r, ref_g, ref_b = reference_colors[color_name]
                meas_r, meas_g, meas_b = measured_colors[color_name]
                
                dev_r = meas_r - ref_r
                dev_g = meas_g - ref_g
                dev_b = meas_b - ref_b
                
                analysis['deviations'][color_name] = {
                    'red_deviation': dev_r,
                    'green_deviation': dev_g,
                    'blue_deviation': dev_b,
                    'total_deviation': abs(dev_r) + abs(dev_g) + abs(dev_b)
                }
                
                print(f"{color_name:<10} ({ref_r:>3},{ref_g:>3},{ref_b:>3}) ({meas_r:>3},{meas_g:>3},{meas_b:>3}) ({dev_r:>+3},{dev_g:>+3},{dev_b:>+3})")
                
                total_r_dev += dev_r
                total_g_dev += dev_g
                total_b_dev += dev_b
                count += 1
        
        if count > 0:
            avg_r_dev = total_r_dev / count
            avg_g_dev = total_g_dev / count
            avg_b_dev = total_b_dev / count
            
            analysis['avg_deviation'] = {
                'red': avg_r_dev,
                'green': avg_g_dev,
                'blue': avg_b_dev
            }
            
            print(f"\nAverage Channel Deviations:")
            print(f"  Red: {avg_r_dev:+.2f}")
            print(f"  Green: {avg_g_dev:+.2f}")
            print(f"  Blue: {avg_b_dev:+.2f}")
            
            # Generate recommendations
            if abs(avg_g_dev) > 5:
                if avg_g_dev > 0:
                    analysis['recommendations'].append("Green channel is consistently high - possible display/screenshot issue")
                else:
                    analysis['recommendations'].append("Green channel is consistently low")
            
            if abs(avg_b_dev) > 5:
                if avg_b_dev < 0:
                    analysis['recommendations'].append("Blue channel is consistently low - common in screenshots")
                else:
                    analysis['recommendations'].append("Blue channel is consistently high")
            
            if abs(avg_r_dev) > 3:
                if avg_r_dev > 0:
                    analysis['recommendations'].append("Red channel is slightly high")
                else:
                    analysis['recommendations'].append("Red channel is slightly low")
            
            # Create correction matrix
            analysis['correction_matrix'] = self._create_correction_matrix(
                avg_r_dev, avg_g_dev, avg_b_dev
            )
        
        return analysis
    
    def _create_correction_matrix(self, r_dev: float, g_dev: float, b_dev: float) -> Dict:
        """Create a correction matrix based on average deviations."""
        return {
            'red_correction': -r_dev,
            'green_correction': -g_dev,
            'blue_correction': -b_dev,
            'multiplicative_factors': {
                'red': 1.0 if abs(r_dev) < 3 else (255 - abs(r_dev)) / 255,
                'green': 1.0 if abs(g_dev) < 5 else (255 - abs(g_dev)) / 255,
                'blue': 1.0 if abs(b_dev) < 5 else (255 + abs(b_dev) if b_dev < 0 else 255 - abs(b_dev)) / 255
            }
        }
    
    def apply_correction(self, rgb: Tuple[int, int, int], 
                        correction_matrix: Dict) -> Tuple[int, int, int]:
        """
        Apply color correction to RGB values.
        
        Args:
            rgb: Original RGB tuple
            correction_matrix: Correction matrix from analyze_color_deviation
            
        Returns:
            Corrected RGB tuple
        """
        r, g, b = rgb
        
        # Apply additive corrections
        r_corr = r + correction_matrix.get('red_correction', 0)
        g_corr = g + correction_matrix.get('green_correction', 0)
        b_corr = b + correction_matrix.get('blue_correction', 0)
        
        # Apply multiplicative corrections if available
        mult_factors = correction_matrix.get('multiplicative_factors', {})
        if mult_factors:
            r_corr *= mult_factors.get('red', 1.0)
            g_corr *= mult_factors.get('green', 1.0) 
            b_corr *= mult_factors.get('blue', 1.0)
        
        # Clamp to valid range
        r_final = max(0, min(255, int(round(r_corr))))
        g_final = max(0, min(255, int(round(g_corr))))
        b_final = max(0, min(255, int(round(b_corr))))
        
        return (r_final, g_final, b_final)
    
    def create_calibration_target(self, size: Tuple[int, int] = (400, 300)) -> Image.Image:
        """
        Create a calibration target image with known colors.
        
        Args:
            size: Image size as (width, height)
            
        Returns:
            PIL Image with calibration colors
        """
        width, height = size
        target = Image.new('RGB', size, (255, 255, 255))
        
        # Create color patches
        patch_width = width // 3
        patch_height = height // 2
        
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green  
            (0, 0, 255),    # Blue
            (255, 255, 255), # White
            (128, 128, 128), # Gray
            (0, 0, 0)       # Black
        ]
        
        positions = [
            (0, 0), (patch_width, 0), (2*patch_width, 0),
            (0, patch_height), (patch_width, patch_height), (2*patch_width, patch_height)
        ]
        
        pixels = target.load()
        
        for i, (color, (start_x, start_y)) in enumerate(zip(colors, positions)):
            for x in range(start_x, min(start_x + patch_width, width)):
                for y in range(start_y, min(start_y + patch_height, height)):
                    pixels[x, y] = color
        
        return target
    
    def diagnose_color_issue(self, your_measurements: Dict[str, Tuple[int, int, int]]) -> str:
        """
        Diagnose the specific color issue you're experiencing.
        
        Args:
            your_measurements: Your measured color values
            
        Returns:
            Diagnostic string with recommendations
        """
        print("=== COLOR ISSUE DIAGNOSIS ===")
        
        # Check your specific measurements
        if 'red' in your_measurements:
            red_measured = your_measurements['red']
            print(f"Red analysis: Expected (255,0,0), Got {red_measured}")
            if red_measured[0] < 250:
                print("  → Red channel is low - check display brightness/contrast")
            if red_measured[1] > 5 or red_measured[2] > 5:
                print("  → Green/Blue contamination in red - check color purity settings")
        
        if 'green' in your_measurements:
            green_measured = your_measurements['green']
            print(f"Green analysis: Expected (0,255,0), Got {green_measured}")
            if green_measured[1] < 250:
                print("  → Green channel is low")
            if green_measured[2] > 10:
                print("  → Significant blue contamination - common screenshot issue")
                print("  → This explains your (0,255,57) reading!")
        
        if 'blue' in your_measurements:
            blue_measured = your_measurements['blue']
            print(f"Blue analysis: Expected (0,0,255), Got {blue_measured}")
            if blue_measured[2] < 200:
                print("  → Blue channel severely low - major screenshot color shift")
                print("  → This explains your (24,17,247) reading!")
            if blue_measured[0] > 15 or blue_measured[1] > 15:
                print("  → Red/Green contamination in blue")
        
        # Generate specific recommendations
        recommendations = [
            "\n=== RECOMMENDATIONS ===",
            "1. SCREENSHOT ISSUES:",
            "   - Screenshots often have poor color accuracy",
            "   - Try using a different screenshot method",
            "   - Consider using a colorimeter for accurate readings",
            "",
            "2. DISPLAY CALIBRATION:",
            "   - Your display may need calibration",
            "   - Check display color temperature settings",
            "   - Ensure sRGB/standard color mode is enabled",
            "",
            "3. BROWSER/SOFTWARE ISSUES:",
            "   - Different browsers render colors differently", 
            "   - Online color generators may not be accurate",
            "   - Try a dedicated color reference application",
            "",
            "4. IMMEDIATE FIX:",
            "   - Use the correction matrix this tool generates",
            "   - Apply corrections in your StampZ color analysis",
            "   - Test with known color references"
        ]
        
        return "\n".join(recommendations)

def analyze_your_color_issue():
    """Analyze the specific color issue described in your question."""
    
    calibrator = ColorCalibrator()
    
    # Your reported measurements
    your_measurements = {
        'red': (254, 0, 0),      # Almost spot on
        'green': (0, 255, 57),   # Green contaminated with blue
        'blue': (24, 17, 247)    # Blue contaminated with red/green
    }
    
    print("ANALYZING YOUR SPECIFIC COLOR ISSUE")
    print("="*50)
    print("You reported these measurements from online color generator screenshots:")
    
    # Analyze the deviations
    analysis = calibrator.analyze_color_deviation(your_measurements)
    
    print("\n" + "="*50)
    print("ISSUE IDENTIFICATION:")
    
    # Green issue analysis
    green_blue_contamination = your_measurements['green'][2]  # Blue value in green
    print(f"Green shows {green_blue_contamination} units of blue contamination")
    print("This is typical of:")
    print("  - Screenshot color space issues")
    print("  - Display with poor color gamut")
    print("  - Browser color management problems")
    
    # Blue issue analysis  
    blue_red_contamination = your_measurements['blue'][0]
    blue_green_contamination = your_measurements['blue'][1]
    blue_deficit = 255 - your_measurements['blue'][2]
    
    print(f"\nBlue shows significant issues:")
    print(f"  - {blue_red_contamination} units red contamination")
    print(f"  - {blue_green_contamination} units green contamination")
    print(f"  - {blue_deficit} units blue deficit")
    print("This suggests a systematic color space conversion error")
    
    # Generate correction
    if analysis['correction_matrix']:
        print(f"\n" + "="*50)
        print("SUGGESTED CORRECTIONS:")
        matrix = analysis['correction_matrix']
        
        print("Apply these corrections to future measurements:")
        print(f"  Red: {matrix['red_correction']:+.1f}")
        print(f"  Green: {matrix['green_correction']:+.1f}")  
        print(f"  Blue: {matrix['blue_correction']:+.1f}")
        
        print("\nCorrected values would be:")
        for color_name, original in your_measurements.items():
            corrected = calibrator.apply_correction(original, matrix)
            print(f"  {color_name}: {original} → {corrected}")
    
    # Generate diagnostic recommendations
    diagnosis = calibrator.diagnose_color_issue(your_measurements)
    print(diagnosis)
    
    return analysis

if __name__ == "__main__":
    # Run the analysis for your specific issue
    analyze_your_color_issue()
