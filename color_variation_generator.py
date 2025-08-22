#!/usr/bin/env python3
"""
Color Variation Generator for RGBCMY
Generates color variations in L*a*b* space with configurable increments
Exports to CSV for spreadsheet use
"""

import pandas as pd
import numpy as np
import colorsys
from typing import List, Tuple, Dict

def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Convert RGB (0-255) to L*a*b* color space
    Using simplified conversion via XYZ
    """
    # Normalize RGB to 0-1
    r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
    
    # Convert to XYZ (using sRGB matrix)
    # Simplified conversion - for more accurate results, use colorspacious library
    r_linear = r_norm**2.2 if r_norm > 0.04045 else r_norm/12.92
    g_linear = g_norm**2.2 if g_norm > 0.04045 else g_norm/12.92  
    b_linear = b_norm**2.2 if b_norm > 0.04045 else b_norm/12.92
    
    # sRGB to XYZ matrix (D65 illuminant)
    x = r_linear * 0.4124 + g_linear * 0.3576 + b_linear * 0.1805
    y = r_linear * 0.2126 + g_linear * 0.7152 + b_linear * 0.0722
    z = r_linear * 0.0193 + g_linear * 0.1192 + b_linear * 0.9505
    
    # XYZ to L*a*b* (D65 white point: Xn=0.9505, Yn=1.0000, Zn=1.0890)
    xn, yn, zn = 0.9505, 1.0000, 1.0890
    fx = ((x/xn)**(1/3)) if (x/xn) > 0.008856 else (7.787*(x/xn) + 16/116)
    fy = ((y/yn)**(1/3)) if (y/yn) > 0.008856 else (7.787*(y/yn) + 16/116)
    fz = ((z/zn)**(1/3)) if (z/zn) > 0.008856 else (7.787*(z/zn) + 16/116)
    
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b_lab = 200 * (fy - fz)
    
    return round(L, 2), round(a, 2), round(b_lab, 2)

def generate_color_variations(base_colors: Dict[str, Tuple[int, int, int]], 
                            increment_percent: float = 10) -> List[Dict]:
    """
    Generate color variations for RGBCMY with specified increment
    """
    variations = []
    
    for color_name, (r, g, b) in base_colors.items():
        # Base color
        l_base, a_base, b_base = rgb_to_lab(r, g, b)
        variations.append({
            'Color_Family': color_name,
            'Variation': 'Base',
            'RGB_Hex': f'#{r:02X}{g:02X}{b:02X}',
            'RGB_R': r, 'RGB_G': g, 'RGB_B': b,
            'LAB_L': l_base, 'LAB_a': a_base, 'LAB_b': b_base,
            'Brightness_Change': 0
        })
        
        # Generate darker variations (negative increments)
        for i in range(1, 6):  # -10%, -20%, -30%, -40%, -50%
            factor = 1 - (increment_percent * i / 100)
            new_r = max(0, int(r * factor))
            new_g = max(0, int(g * factor))
            new_b = max(0, int(b * factor))
            
            l_var, a_var, b_var = rgb_to_lab(new_r, new_g, new_b)
            variations.append({
                'Color_Family': color_name,
                'Variation': f'-{increment_percent * i:.0f}%',
                'RGB_Hex': f'#{new_r:02X}{new_g:02X}{new_b:02X}',
                'RGB_R': new_r, 'RGB_G': new_g, 'RGB_B': new_b,
                'LAB_L': l_var, 'LAB_a': a_var, 'LAB_b': b_var,
                'Brightness_Change': -(increment_percent * i)
            })
        
        # Generate lighter variations (positive increments)
        for i in range(1, 6):  # +10%, +20%, +30%, +40%, +50%
            factor = 1 + (increment_percent * i / 100)
            new_r = min(255, int(r * factor))
            new_g = min(255, int(g * factor))
            new_b = min(255, int(b * factor))
            
            l_var, a_var, b_var = rgb_to_lab(new_r, new_g, new_b)
            variations.append({
                'Color_Family': color_name,
                'Variation': f'+{increment_percent * i:.0f}%',
                'RGB_Hex': f'#{new_r:02X}{new_g:02X}{new_b:02X}',
                'RGB_R': new_r, 'RGB_G': new_g, 'RGB_B': new_b,
                'LAB_L': l_var, 'LAB_a': a_var, 'LAB_b': b_var,
                'Brightness_Change': increment_percent * i
            })
    
    return variations

def main():
    # Define RGBCMY base colors (standard printing colors)
    base_colors = {
        'Red': (255, 0, 0),
        'Green': (0, 255, 0),
        'Blue': (0, 0, 255),
        'Cyan': (0, 255, 255),
        'Magenta': (255, 0, 255),
        'Yellow': (255, 255, 0)
    }
    
    print("Generating color variations...")
    print("Base colors: Red, Green, Blue, Cyan, Magenta, Yellow")
    
    # Generate variations with 10% increments (recommended)
    variations_10 = generate_color_variations(base_colors, 10)
    df_10 = pd.DataFrame(variations_10)
    
    # Generate variations with 5% increments (for comparison)
    variations_5 = generate_color_variations(base_colors, 5)
    df_5 = pd.DataFrame(variations_5)
    
    # Export to CSV files
    df_10.to_csv('color_variations_10_percent.csv', index=False)
    df_5.to_csv('color_variations_5_percent.csv', index=False)
    
    print(f"\nGenerated {len(variations_10)} variations with 10% increments")
    print(f"Generated {len(variations_5)} variations with 5% increments")
    print("\nFiles created:")
    print("- color_variations_10_percent.csv (recommended for human perception)")
    print("- color_variations_5_percent.csv (finer gradations)")
    
    # Display sample of 10% variations
    print("\nSample of 10% variations:")
    print(df_10[df_10['Color_Family'] == 'Red'].head(10).to_string(index=False))
    
    # Calculate some Delta E values for comparison
    print("\n=== Human Perception Analysis ===")
    red_base = df_10[(df_10['Color_Family'] == 'Red') & (df_10['Variation'] == 'Base')].iloc[0]
    red_10 = df_10[(df_10['Color_Family'] == 'Red') & (df_10['Variation'] == '-10%')].iloc[0]
    red_5 = df_5[(df_5['Color_Family'] == 'Red') & (df_5['Variation'] == '-5%')].iloc[0]
    
    # Simple Delta E calculation (Euclidean distance in L*a*b*)
    delta_e_10 = ((red_base['LAB_L'] - red_10['LAB_L'])**2 + 
                  (red_base['LAB_a'] - red_10['LAB_a'])**2 + 
                  (red_base['LAB_b'] - red_10['LAB_b'])**2)**0.5
    
    delta_e_5 = ((red_base['LAB_L'] - red_5['LAB_L'])**2 + 
                 (red_base['LAB_a'] - red_5['LAB_a'])**2 + 
                 (red_base['LAB_b'] - red_5['LAB_b'])**2)**0.5
    
    print(f"Delta E (10% change): {delta_e_10:.2f}")
    print(f"Delta E (5% change): {delta_e_5:.2f}")
    print("\nDelta E interpretation:")
    print("- < 1.0: Not perceptible by human eyes")
    print("- 1-2: Perceptible through close observation")  
    print("- 2-10: Perceptible at a glance")
    print("- 11-49: Colors are more similar than opposite")
    print("- > 50: Colors are exact opposite")

if __name__ == "__main__":
    main()
