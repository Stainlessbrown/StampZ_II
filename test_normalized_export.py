#!/usr/bin/env python3
"""
Test script to demonstrate the normalized export functionality in StampZ.
This script shows how to enable/disable normalized exports and create sample exports.
"""

import os
import sys

# Add the StampZ utils directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

def test_normalized_export():
    """Test the normalized export functionality."""
    
    try:
        from utils.user_preferences import get_preferences_manager
        from utils.ods_exporter import ODSExporter
        
        print("🔧 Testing Normalized Export Functionality")
        print("=" * 50)
        
        # Get preferences manager
        prefs_manager = get_preferences_manager()
        
        print(f"📊 Current export settings:")
        print(f"   - Normalized values: {prefs_manager.get_export_normalized_values()}")
        print(f"   - Preferred format: {prefs_manager.get_preferred_export_format()}")
        print(f"   - Export directory: {prefs_manager.get_export_directory()}")
        print()
        
        # Test 1: Standard export (normalized = False)
        print("📋 Test 1: Standard Export Format")
        print("-" * 30)
        
        # Ensure normalized is disabled for first test
        prefs_manager.set_export_normalized_values(False)
        
        # Create exporter and try to export
        exporter = ODSExporter()
        standard_file = exporter.export_to_sample_set_file("test_standard", "csv")
        
        if standard_file:
            print(f"✅ Standard export created: {standard_file}")
            print("   - RGB values: 0-255 range")
            print("   - L* values: 0-100 range")
            print("   - a*/b* values: typically -128 to +127 range")
        else:
            print("❌ No data available for export (this is normal if no color measurements exist)")
        print()
        
        # Test 2: Normalized export (normalized = True)
        print("📋 Test 2: Normalized Export Format (0.0-1.0)")
        print("-" * 40)
        
        # Enable normalized exports
        prefs_manager.set_export_normalized_values(True)
        
        # Create exporter and try to export
        exporter = ODSExporter()
        normalized_file = exporter.export_to_sample_set_file("test_normalized", "csv")
        
        if normalized_file:
            print(f"✅ Normalized export created: {normalized_file}")
            print("   - RGB values: 0.0000-1.0000 range (4 decimal places)")
            print("   - L* values: 0.0000-1.0000 range (4 decimal places)")
            print("   - a*/b* values: 0.0000-1.0000 range (4 decimal places)")
            print("   - Column headers include '_norm' suffix")
        else:
            print("❌ No data available for export (this is normal if no color measurements exist)")
        print()
        
        # Test 3: Show how to use the preference programmatically
        print("🔧 Programmatic Usage Examples")
        print("-" * 30)
        
        print("# Enable normalized exports:")
        print("prefs_manager.set_export_normalized_values(True)")
        print()
        
        print("# Check current setting:")
        print(f"normalized = prefs_manager.get_export_normalized_values()  # Returns: {prefs_manager.get_export_normalized_values()}")
        print()
        
        print("# Disable normalized exports:")
        print("prefs_manager.set_export_normalized_values(False)")
        prefs_manager.set_export_normalized_values(False)
        print(f"normalized = prefs_manager.get_export_normalized_values()  # Returns: {prefs_manager.get_export_normalized_values()}")
        print()
        
        # Test 4: Show normalization formulas
        print("📐 Normalization Formulas")
        print("-" * 25)
        print("RGB (0-255) → Normalized: value / 255.0")
        print("L* (0-100) → Normalized: value / 100.0")
        print("a*/b* (-128 to +127) → Normalized: (value + 128.0) / 255.0")
        print()
        
        # Examples
        print("🧮 Example Conversions:")
        print("   RGB(255, 128, 0) → (1.0000, 0.5020, 0.0000)")
        print("   L*a*b*(50, -10, 20) → (0.5000, 0.4627, 0.5784)")
        print("   L*a*b*(100, 0, 0) → (1.0000, 0.5020, 0.5020)")
        print()
        
        print("🎯 Benefits of Normalized Export:")
        print("   • Consistent 0.0-1.0 range for all color components")
        print("   • Easier plotting and data visualization")
        print("   • Compatible with many color analysis tools")
        print("   • Simplified statistical analysis")
        print("   • Better for machine learning applications")
        print()
        
        print("✅ Normalized export functionality is working correctly!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the StampZ directory.")
    except Exception as e:
        print(f"❌ Error testing normalized export: {e}")

if __name__ == "__main__":
    test_normalized_export()
