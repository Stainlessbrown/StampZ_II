#!/usr/bin/env python3
"""
Manual Color Correction Calculator for StampZ
Based on your system's known color shifts determined through calibration testing.

Usage: python3 color_correction_calculator.py
"""

def correct_color(r, g, b, method='universal', calibration_file=None):
    """
    Apply manual corrections based on your system's known shifts.
    
    Your system's channel biases (from calibration analysis):
    - Red channel: +8.3 average bias (reads too high)
    - Green channel: +5.7 average bias (reads too high)  
    - Blue channel: +9.7 average bias (reads too high)
    
    Args:
        r, g, b: Measured RGB values from StampZ
        method: 'universal' (recommended), 'color_specific', or 'dynamic'
        calibration_file: Path to calibration JSON file (for dynamic method)
        
    Returns:
        Corrected RGB tuple and method used
    """
    
    # Try dynamic calibration first if available
    if method == 'dynamic' or calibration_file:
        try:
            import json
            import os
            
            # Default calibration file location
            if not calibration_file:
                calibration_file = 'stampz_calibration.json'
            
            if os.path.exists(calibration_file):
                with open(calibration_file, 'r') as f:
                    calibration_data = json.load(f)
                
                if 'calibration_matrix' in calibration_data:
                    corrections = calibration_data['calibration_matrix']['corrections']
                    
                    # Apply dynamic corrections
                    corrected_r = max(0, min(255, r + corrections.get('red_correction', 0)))
                    corrected_g = max(0, min(255, g + corrections.get('green_correction', 0)))
                    corrected_b = max(0, min(255, b + corrections.get('blue_correction', 0)))
                    
                    corrected = (int(round(corrected_r)), int(round(corrected_g)), int(round(corrected_b)))
                    method_used = 'Dynamic (from calibration file)'
                    
                    return corrected, method_used
        except Exception as e:
            print(f"Warning: Could not load dynamic calibration: {e}")
            # Fall back to universal method
    
    if method == 'universal':
        # Universal channel corrections - works for ANY color
        corrected_r = max(0, min(255, r - 8))  # Subtract red bias
        corrected_g = max(0, min(255, g - 6))  # Subtract green bias
        corrected_b = max(0, min(255, b - 10)) # Subtract blue bias
        
        corrected = (corrected_r, corrected_g, corrected_b)
        method_used = 'Universal (recommended)'
        
    else:
        # Legacy color-specific method (less reliable for mixed colors)
        max_val = max(r, g, b)
        if r == max_val and r > g + 50 and r > b + 50:
            # Primarily red - minimal correction
            corrected = (max(0, r - 1), g, b)
            method_used = 'Red-dominant'
        elif g == max_val and g > r + 50 and g > b + 50:
            # Primarily green - reduce blue contamination
            corrected = (r, g, max(0, b - 37))
            method_used = 'Green-dominant'
        elif b == max_val and b > r + 50 and b > g + 50:
            # Primarily blue - reduce red/green contamination
            corrected = (max(0, r - 26), max(0, g - 17), b)
            method_used = 'Blue-dominant'
        else:
            # Mixed color - use universal method
            corrected_r = max(0, min(255, r - 8))
            corrected_g = max(0, min(255, g - 6)) 
            corrected_b = max(0, min(255, b - 10))
            corrected = (corrected_r, corrected_g, corrected_b)
            method_used = 'Mixed (universal fallback)'
    
    return corrected, method_used

def main():
    """Interactive color correction calculator."""
    print("StampZ Universal Color Correction Calculator")
    print("=" * 48)
    print()
    print("Based on your system's channel biases:")
    print("• Red channel:   Subtract 8 from measurement")
    print("• Green channel: Subtract 6 from measurement") 
    print("• Blue channel:  Subtract 10 from measurement")
    print()
    print("✨ Works for ANY color: red, green, blue, purple, teal, etc!")
    print()
    
    while True:
        try:
            print("Enter RGB values from StampZ (or 'q' to quit):")
            user_input = input("RGB: ").strip()
            
            if user_input.lower() == 'q':
                break
                
            # Parse input - accept various formats
            rgb_str = user_input.replace('(', '').replace(')', '').replace(',', ' ')
            rgb_values = [int(x) for x in rgb_str.split()]
            
            if len(rgb_values) != 3:
                print("Please enter 3 numbers for R, G, B")
                continue
                
            r, g, b = rgb_values
            
            # Validate ranges
            if not all(0 <= val <= 255 for val in [r, g, b]):
                print("RGB values must be between 0 and 255")
                continue
                
            # Calculate correction
            corrected, detected_type = correct_color(r, g, b)
            
            # Display results
            print(f"Original:    ({r}, {g}, {b})")
            print(f"Corrected:   {corrected}")
            print(f"Detected as: {detected_type} color")
            
            # Show the change
            dr = corrected[0] - r
            dg = corrected[1] - g  
            db = corrected[2] - b
            print(f"Change:      ({dr:+d}, {dg:+d}, {db:+d})")
            print()
            
        except ValueError:
            print("Please enter valid numbers")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
