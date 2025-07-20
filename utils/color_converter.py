"""
Color space conversion utilities for StampZ.
"""

import math

def lab_to_xyz(l: float, a: float, b: float) -> tuple:
    """Convert CIE L*a*b* to CIE XYZ color space."""
    # L*a*b* D65/2° constants
    X_n = 95.047
    Y_n = 100.0
    Z_n = 108.883

    # L* = 116(Y/Yn)^1/3 - 16
    # a* = 500[(X/Xn)^1/3 - (Y/Yn)^1/3]
    # b* = 200[(Y/Yn)^1/3 - (Z/Zn)^1/3]

    y = (l + 16) / 116
    x = y + (a / 500)
    z = y - (b / 200)

    if x**3 > 0.008856:
        x = x**3
    else:
        x = (x - 16/116) / 7.787

    if y**3 > 0.008856:
        y = y**3
    else:
        y = (y - 16/116) / 7.787

    if z**3 > 0.008856:
        z = z**3
    else:
        z = (z - 16/116) / 7.787

    x *= X_n
    y *= Y_n
    z *= Z_n

    return (x, y, z)

def xyz_to_rgb(x: float, y: float, z: float) -> tuple:
    """Convert CIE XYZ to sRGB color space."""
    # XYZ to RGB matrix transformation
    r = x * 3.2406 + y * -1.5372 + z * -0.4986
    g = x * -0.9689 + y * 1.8758 + z * 0.0415
    b = x * 0.0557 + y * -0.2040 + z * 1.0570

    # Convert to 0-1 range and apply gamma correction
    r = math.pow(r/100, 1/2.4) if r > 0 else 0
    g = math.pow(g/100, 1/2.4) if g > 0 else 0
    b = math.pow(b/100, 1/2.4) if b > 0 else 0

    # Convert to 0-255 range and clamp
    r = min(max(round(r * 255), 0), 255)
    g = min(max(round(g * 255), 0), 255)
    b = min(max(round(b * 255), 0), 255)

    return (r, g, b)

def lab_to_rgb(l: float, a: float, b: float) -> tuple:
    """Convert CIE L*a*b* to sRGB color space."""
    xyz = lab_to_xyz(l, a, b)
    rgb = xyz_to_rgb(*xyz)
    return rgb
