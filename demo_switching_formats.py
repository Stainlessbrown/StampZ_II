#!/usr/bin/env python3
"""
Demo script showing how to easily switch between normalized and full value exports
by simply changing the user preference.
"""

import os
import sys

# Add the StampZ utils directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

def demo_format_switching():
    """Demonstrate switching between normalized and full value exports."""
    
    try:
        from utils.user_preferences import get_preferences_manager
        from utils.ods_exporter import ODSExporter
        
        print("🔄 Demo: Switching Between Export Formats")
        print("=" * 50)
        
        # Get preferences manager
        prefs_manager = get_preferences_manager()
        
        print("📊 This demo shows how you can instantly switch between:")
        print("   • Full values (standard ranges)")
        print("   • Normalized values (0.0-1.0 range)")
        print("   Just by changing a single preference!\n")
        
        # Create exporter once
        exporter = ODSExporter()
        
        # Demo 1: Export with full values
        print("🔧 Step 1: Set preference to FULL VALUES")
        print("-" * 30)
        prefs_manager.set_export_normalized_values(False)
        print(f"✅ Normalized export: {prefs_manager.get_export_normalized_values()}")
        
        # Export with full values
        print("\n📋 Exporting with full values...")
        full_file = exporter.export_to_sample_set_file("demo_full_values", "csv")
        if full_file:
            print(f"✅ Full values export: {os.path.basename(full_file)}")
        print()
        
        # Demo 2: Switch to normalized values
        print("🔧 Step 2: Set preference to NORMALIZED VALUES")
        print("-" * 35)
        prefs_manager.set_export_normalized_values(True)
        print(f"✅ Normalized export: {prefs_manager.get_export_normalized_values()}")
        
        # Export with normalized values (same data, different format)
        print("\n📋 Exporting with normalized values...")
        norm_file = exporter.export_to_sample_set_file("demo_normalized", "csv")
        if norm_file:
            print(f"✅ Normalized export: {os.path.basename(norm_file)}")
        print()
        
        # Demo 3: Switch back to full values
        print("🔧 Step 3: Switch back to FULL VALUES")
        print("-" * 30)
        prefs_manager.set_export_normalized_values(False)
        print(f"✅ Normalized export: {prefs_manager.get_export_normalized_values()}")
        
        # Export again with full values
        print("\n📋 Exporting with full values again...")
        full_file2 = exporter.export_to_sample_set_file("demo_full_values_2", "csv")
        if full_file2:
            print(f"✅ Full values export: {os.path.basename(full_file2)}")
        print()
        
        # Show the differences if files were created
        if full_file and norm_file:
            print("📈 Comparing the formats:")
            print("-" * 25)
            
            print("🔍 Full values format (first few columns):")
            os.system(f"head -2 '{full_file}' | cut -d',' -f1-6")
            
            print("\n🔍 Normalized format (first few columns):")  
            os.system(f"head -2 '{norm_file}' | cut -d',' -f1-6")
            print()
        
        print("✨ Key Benefits:")
        print("   • Same underlying data - different presentations")
        print("   • Instant switching with one line of code") 
        print("   • No data loss or conversion needed")
        print("   • Perfect for different analysis workflows")
        print("   • All export formats (ODS, Excel, CSV) work the same way")
        print()
        
        print("🎯 Real-world usage scenarios:")
        print("   • Use NORMALIZED for plotting and data science")
        print("   • Use FULL VALUES for traditional color analysis")
        print("   • Switch formats based on your analysis tool")
        print("   • Generate both formats for different audiences")
        print()
        
        print("💡 Pro tip: You can even create both formats in one script:")
        print("   # Export full values")
        print("   prefs_manager.set_export_normalized_values(False)")
        print("   full_data = exporter.export_to_sample_set_file('data_full', 'csv')")
        print("   ")
        print("   # Export normalized values")
        print("   prefs_manager.set_export_normalized_values(True)")
        print("   norm_data = exporter.export_to_sample_set_file('data_norm', 'csv')")
        print()
        
        print("✅ Format switching demo completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the StampZ directory.")
    except Exception as e:
        print(f"❌ Error in demo: {e}")

if __name__ == "__main__":
    demo_format_switching()
