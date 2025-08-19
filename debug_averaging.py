#!/usr/bin/env python3
"""
Diagnostic script to help debug averaging and export issues in StampZ.
Run this script after performing an analysis to check what data exists.
"""

import sys
import os
import datetime
from pathlib import Path

# Add the StampZ directory to Python path
stampz_dir = Path(__file__).parent
sys.path.insert(0, str(stampz_dir))

def check_recent_databases():
    """Check for recently modified databases."""
    print("=== Recent Database Activity ===")
    
    color_data_dir = stampz_dir / "data" / "color_analysis"
    if not color_data_dir.exists():
        print("❌ Color analysis directory not found")
        return []
    
    # Find all databases and their modification times
    db_files = list(color_data_dir.glob("*.db"))
    if not db_files:
        print("❌ No databases found")
        return []
    
    # Sort by modification time (newest first)
    now = datetime.datetime.now().timestamp()
    db_info = []
    
    for db_file in db_files:
        mtime = db_file.stat().st_mtime
        age_minutes = (now - mtime) / 60
        
        sample_set_name = db_file.stem
        mod_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        db_info.append((sample_set_name, age_minutes, mod_time, db_file))
    
    db_info.sort(key=lambda x: x[1])  # Sort by age (newest first)
    
    print(f"Found {len(db_info)} databases:")
    recent_dbs = []
    
    for name, age, mod_time, db_file in db_info:
        if age < 60:  # Less than 1 hour old
            print(f"  🔥 {name} (modified: {mod_time}, {age:.1f} min ago) - RECENT")
            recent_dbs.append((name, db_file))
        elif age < 1440:  # Less than 1 day old
            print(f"  📝 {name} (modified: {mod_time}, {age/60:.1f} hours ago)")
        else:
            print(f"  📁 {name} (modified: {mod_time}, {age/1440:.1f} days ago)")
    
    return recent_dbs

def check_database_content(sample_set_name):
    """Check the content of a specific database."""
    print(f"\n=== Database Content: {sample_set_name} ===")
    
    try:
        from utils.color_analysis_db import ColorAnalysisDB
        
        db = ColorAnalysisDB(sample_set_name)
        measurements = db.get_all_measurements()
        
        individual_measurements = [m for m in measurements if not m.get('is_averaged', False)]
        averaged_measurements = [m for m in measurements if m.get('is_averaged', False)]
        
        print(f"Total measurements: {len(measurements)}")
        print(f"Individual measurements: {len(individual_measurements)}")
        print(f"Averaged measurements: {len(averaged_measurements)}")
        
        if individual_measurements:
            print(f"\nIndividual measurements (first 3):")
            for i, m in enumerate(individual_measurements[:3]):
                print(f"  {i+1}. Point {m['coordinate_point']}: L*={m['l_value']:.2f}, a*={m['a_value']:.2f}, b*={m['b_value']:.2f}")
        
        if averaged_measurements:
            print(f"\n✅ Averaged measurements found:")
            for i, m in enumerate(averaged_measurements):
                print(f"  {i+1}. Point {m['coordinate_point']}: L*={m['l_value']:.2f}, a*={m['a_value']:.2f}, b*={m['b_value']:.2f}")
                print(f"      Source samples: {m['source_samples_count']}")
                print(f"      Notes: {m['notes']}")
        else:
            print("❌ No averaged measurements found")
            print("   This means 'Save average to database' either:")
            print("   - Was not clicked")
            print("   - Failed to save (check for error messages)")
            print("   - Saved to a different database")
        
        return len(averaged_measurements) > 0
        
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        return False

def check_export_directory():
    """Check recent export files."""
    print(f"\n=== Recent Export Files ===")
    
    export_dir = stampz_dir / "exports"
    if not export_dir.exists():
        print("❌ Export directory not found")
        return []
    
    # Find all export files
    export_files = []
    for pattern in ["*.ods", "*.csv", "*.xlsx"]:
        export_files.extend(export_dir.glob(pattern))
    
    if not export_files:
        print("❌ No export files found")
        return []
    
    # Sort by modification time (newest first)
    now = datetime.datetime.now().timestamp()
    export_info = []
    
    for export_file in export_files:
        mtime = export_file.stat().st_mtime
        age_minutes = (now - mtime) / 60
        mod_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        export_info.append((export_file.name, age_minutes, mod_time, export_file))
    
    export_info.sort(key=lambda x: x[1])  # Sort by age (newest first)
    
    print(f"Found {len(export_info)} export files:")
    recent_exports = []
    
    for name, age, mod_time, export_file in export_info:
        if age < 60:  # Less than 1 hour old
            print(f"  🔥 {name} (created: {mod_time}, {age:.1f} min ago) - VERY RECENT")
            recent_exports.append((name, export_file))
        elif age < 1440:  # Less than 1 day old
            print(f"  📝 {name} (created: {mod_time}, {age/60:.1f} hours ago)")
        else:
            print(f"  📁 {name} (created: {mod_time}, {age/1440:.1f} days ago)")
    
    return recent_exports

def check_export_preferences():
    """Check export preferences."""
    print(f"\n=== Export Preferences ===")
    
    try:
        from utils.user_preferences import get_preferences_manager
        
        prefs = get_preferences_manager()
        normalized_export = prefs.get_export_normalized_values()
        
        print(f"Export normalized values: {normalized_export}")
        
        if normalized_export:
            print("⚠️  Normalized export is ENABLED")
            print("   This will show *_norm columns instead of full values")
        else:
            print("✅ Normalized export is DISABLED")
            print("   This should show full L*, a*, b*, R, G, B values")
        
        return normalized_export
        
    except Exception as e:
        print(f"❌ Error reading preferences: {e}")
        return None

def test_export_for_recent_db(sample_set_name):
    """Test export functionality for a recent database."""
    print(f"\n=== Testing Export for: {sample_set_name} ===")
    
    try:
        from utils.ods_exporter import ODSExporter
        
        exporter = ODSExporter(sample_set_name)
        measurements = exporter.get_color_measurements(deduplicate=False)
        
        print(f"Measurements found for export: {len(measurements)}")
        
        if measurements:
            individual_count = len([m for m in measurements if not m.is_averaged])
            averaged_count = len([m for m in measurements if m.is_averaged])
            print(f"Individual: {individual_count}, Averaged: {averaged_count}")
            
            # Test export
            test_export_path = stampz_dir / "exports" / f"diagnostic_test_{sample_set_name}.csv"
            success = exporter.export_to_csv(str(test_export_path))
            
            if success and test_export_path.exists():
                print(f"✅ Test export successful: {test_export_path.name}")
                
                # Check content
                with open(test_export_path, 'r') as f:
                    lines = f.readlines()
                    header_line = lines[0].strip()
                    
                print(f"Export format: {'Normalized' if '_norm' in header_line else 'Standard'}")
                
                # Check for averaged data
                for i, line in enumerate(lines[1:], 1):
                    if 'AVERAGE' in line:
                        print(f"✅ Found averaged data in row {i+1}")
                        break
                else:
                    if averaged_count > 0:
                        print("⚠️  Averaged measurements exist but not found in export")
                    else:
                        print("ℹ️  No averaged measurements to export")
                
                # Clean up test file
                test_export_path.unlink()
                
            else:
                print("❌ Test export failed")
        else:
            print("❌ No measurements available for export")
            
    except Exception as e:
        print(f"❌ Error testing export: {e}")

def main():
    """Main diagnostic function."""
    print("🔍 StampZ Averaging & Export Diagnostic Tool")
    print("=" * 50)
    
    # Check recent database activity
    recent_dbs = check_recent_databases()
    
    # Check export directory
    recent_exports = check_export_directory()
    
    # Check preferences
    check_export_preferences()
    
    # Check content of most recent database
    if recent_dbs:
        most_recent_db = recent_dbs[0][0]
        has_averaged_data = check_database_content(most_recent_db)
        
        # Test export for the most recent database
        test_export_for_recent_db(most_recent_db)
        
        # Summary
        print(f"\n=== Summary ===")
        print(f"Most recent database: {most_recent_db}")
        print(f"Has averaged data: {'✅ Yes' if has_averaged_data else '❌ No'}")
        print(f"Recent exports: {len(recent_exports)}")
        
        if not has_averaged_data:
            print(f"\n💡 Next Steps:")
            print(f"1. Run a new analysis with 3-5 samples")
            print(f"2. Open Compare and click 'Save average to database'")
            print(f"3. Watch for any error messages")
            print(f"4. Run this diagnostic script again")
            
    else:
        print(f"\n💡 No recent databases found. Run an analysis first.")
    
    print(f"\n🔍 Diagnostic complete!")

if __name__ == "__main__":
    main()
