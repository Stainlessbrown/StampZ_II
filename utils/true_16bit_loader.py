#!/usr/bin/env python3
"""
True 16-bit TIFF loader for accurate color analysis.
Prevents PIL from auto-downsampling 16-bit data to 8-bit.
"""

import numpy as np
from PIL import Image
from typing import Tuple, Optional
import tifffile

def load_16bit_tiff(filepath: str, preserve_16bit: bool = True) -> Tuple[np.ndarray, dict]:
    """
    Load a TIFF file while preserving true 16-bit data.
    
    Args:
        filepath: Path to TIFF file
        preserve_16bit: If True, maintains 16-bit precision; if False, uses PIL default
        
    Returns:
        Tuple of (numpy array, metadata dict)
    """
    metadata = {}
    
    try:
        # First, get TIFF metadata using PIL
        with Image.open(filepath) as img:
            metadata = {
                'size': img.size,
                'mode': img.mode,
                'format': img.format,
            }
            
            # Get TIFF tags if available
            if hasattr(img, 'tag_v2') and img.tag_v2:
                bits_per_sample = img.tag_v2.get(258)  # BitsPerSample tag
                metadata['bits_per_sample'] = bits_per_sample
                metadata['compression'] = img.tag_v2.get(259)
                metadata['samples_per_pixel'] = img.tag_v2.get(277)
        
        if preserve_16bit and metadata.get('bits_per_sample') == (16, 16, 16):
            # Use tifffile to load true 16-bit data
            try:
                import tifffile
                print(f"Loading {filepath} with tifffile (preserving 16-bit)")
                img_array = tifffile.imread(filepath)
                
                # Ensure correct shape (height, width, channels)
                if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                    metadata['true_16bit'] = True
                    metadata['data_type'] = str(img_array.dtype)
                    metadata['value_range'] = (img_array.min(), img_array.max())
                    return img_array, metadata
                else:
                    print(f"Unexpected shape from tifffile: {img_array.shape}")
                    
            except ImportError:
                print("tifffile not available, falling back to PIL")
            except Exception as e:
                print(f"Error with tifffile: {e}, falling back to PIL")
        
        # Fallback to PIL (will be 8-bit)
        print(f"Loading {filepath} with PIL (may be downsampled to 8-bit)")
        with Image.open(filepath) as img:
            img_array = np.array(img)
            metadata['true_16bit'] = False
            metadata['data_type'] = str(img_array.dtype)
            metadata['value_range'] = (img_array.min(), img_array.max())
            return img_array, metadata
            
    except Exception as e:
        raise ValueError(f"Failed to load image {filepath}: {e}")

def test_both_methods(filepath: str):
    """
    Test both loading methods to show the difference.
    """
    print(f"\n=== Testing {filepath} ===")
    
    # Method 1: PIL (current method - problematic)
    print("\n1. PIL Method (current):")
    with Image.open(filepath) as img:
        pil_array = np.array(img)
        print(f"   Shape: {pil_array.shape}")
        print(f"   Dtype: {pil_array.dtype}")
        print(f"   Range: {pil_array.min()} - {pil_array.max()}")
        
        # Check TIFF tags
        if hasattr(img, 'tag_v2') and 258 in img.tag_v2:
            print(f"   TIFF BitsPerSample: {img.tag_v2[258]}")
    
    # Method 2: True 16-bit (corrected)
    print("\n2. True 16-bit Method (corrected):")
    try:
        img_array, metadata = load_16bit_tiff(filepath, preserve_16bit=True)
        print(f"   Shape: {img_array.shape}")
        print(f"   Dtype: {img_array.dtype}")
        print(f"   Range: {img_array.min()} - {img_array.max()}")
        print(f"   True 16-bit: {metadata.get('true_16bit', False)}")
        
        # Show the difference in precision
        if metadata.get('true_16bit') and pil_array.dtype != img_array.dtype:
            print(f"\n   ⚠️  PRECISION LOSS DETECTED:")
            print(f"   PIL gives {pil_array.max() - pil_array.min()} unique value range")
            print(f"   16-bit gives {img_array.max() - img_array.min()} unique value range")
            print(f"   Ratio: {(img_array.max() - img_array.min()) / (pil_array.max() - pil_array.min()):.1f}x more precision")
            
    except Exception as e:
        print(f"   Error: {e}")

def main():
    """Test the corrected loader on VueScan TIFF files"""
    import os
    
    test_dir = "/Users/stanbrown/Desktop/color test"
    
    # Test a few representative files
    test_files = [
        "F-199-1.tif",
        "F-278B-1.tif", 
        "F-160-1.tif"
    ]
    
    print("=== 16-bit TIFF Loading Comparison ===")
    print("Testing corrected loader vs current PIL method...")
    
    for filename in test_files:
        filepath = os.path.join(test_dir, filename)
        if os.path.exists(filepath):
            test_both_methods(filepath)
        else:
            print(f"\nFile not found: {filename}")
    
    print("\n=== Recommendations ===")
    print("1. Install tifffile: pip install tifffile")
    print("2. Use load_16bit_tiff() instead of PIL Image.open() for color analysis")
    print("3. This will preserve the full 16-bit precision from VueScan")

if __name__ == "__main__":
    main()
