#!/usr/bin/env python3
"""
Batch Export Script: StampZ Analysis → Plot_3D Format

This script automatically finds all your existing StampZ color analysis databases
and exports them to Plot_3D compatible format for further analysis.

Features:
- Finds all existing analysis databases (both individual and averaged)
- Creates clean Plot_3D files using template names
- Generates both individual and averaged data exports
- Non-destructive: preserves all original analysis data
- User can edit/delete generated files as needed

Usage:
    python export_all_for_plot3d.py
"""

import os
import sys
from typing import List, Dict, Set
from datetime import datetime

def main():
    """Main export function that processes all existing analysis data."""
    
    print("=" * 60)
    print("StampZ Analysis → Plot_3D Batch Export")
    print("=" * 60)
    print()
    
    try:
        # Import the new direct exporter (bypasses problematic ODS exporter)
        from utils.direct_plot3d_exporter import DirectPlot3DExporter
        from utils.color_analysis_db import ColorAnalysisDB
        
        # Initialize the direct exporter
        exporter = DirectPlot3DExporter()
        
        # Find all existing analysis databases
        sample_sets = find_all_sample_sets()
        
        if not sample_sets:
            print("❌ No existing analysis databases found.")
            print("\nSearched in:")
            print("  • data/color_analysis/")
            print("  • Check that you have completed some color analysis first.")
            return
        
        print(f"📊 Found {len(sample_sets)} analysis database(s):")
        for sample_set in sorted(sample_sets):
            print(f"  • {sample_set}")
        print()
        
        # Track results
        success_count = 0
        error_count = 0
        results = []
        
        # Process each sample set
        for sample_set in sorted(sample_sets):
            print(f"🔄 Processing: {sample_set}")
            
            try:
                # Try to export this sample set using direct exporter
                result = export_sample_set_to_plot3d_direct(sample_set, exporter)
                results.append(result)
                
                if result['success']:
                    success_count += 1
                    print(f"  ✅ {result['message']}")
                    if result.get('files_created'):
                        for file_path in result['files_created']:
                            print(f"     📁 {os.path.basename(file_path)}")
                else:
                    error_count += 1
                    print(f"  ❌ {result['message']}")
                    
            except Exception as e:
                error_count += 1
                error_result = {
                    'sample_set': sample_set,
                    'success': False,
                    'message': f"Unexpected error: {str(e)}",
                    'files_created': []
                }
                results.append(error_result)
                print(f"  ❌ Unexpected error: {str(e)}")
            
            print()
        
        # Print summary
        print("=" * 60)
        print("📊 EXPORT SUMMARY")
        print("=" * 60)
        print(f"✅ Successful exports: {success_count}")
        print(f"❌ Failed exports: {error_count}")
        print(f"📁 Total databases processed: {len(sample_sets)}")
        print()
        
        # List all created files
        all_created_files = []
        for result in results:
            if result['success'] and result.get('files_created'):
                all_created_files.extend(result['files_created'])
        
        if all_created_files:
            print("📁 Files created for Plot_3D:")
            exports_dir = os.path.join(os.getcwd(), "exports")
            for file_path in sorted(all_created_files):
                # Show relative path for cleaner output
                rel_path = os.path.relpath(file_path, os.getcwd())
                file_size = get_file_size_mb(file_path)
                print(f"  • {rel_path} ({file_size})")
            print()
            print(f"📂 Location: {exports_dir}")
            print()
            
        # Usage instructions
        print("🚀 NEXT STEPS:")
        print("1. Launch Plot_3D from your StampZ app")
        print("2. File → Open → Select any of the generated .ods files")
        print("3. Your data will be loaded starting at row 8")
        print("4. Begin analysis: K-means clustering, ΔE calculations, etc.")
        print()
        print("💡 TIP: Files are named using template names (e.g., '137_Plot3D.ods')")
        print("    You can edit, rename, or delete these files as needed.")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure all required modules are available.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1)


def find_all_sample_sets() -> Set[str]:
    """Find all existing sample set databases.
    
    Returns:
        Set of sample set names (without _averages suffix)
    """
    try:
        from utils.color_analysis_db import ColorAnalysisDB
        
        # Get all sample set databases
        all_databases = ColorAnalysisDB.get_all_sample_set_databases()
        
        # Extract base sample set names (remove _averages suffix)
        sample_sets = set()
        for db_name in all_databases:
            if db_name.endswith('_averages'):
                base_name = db_name[:-9]  # Remove '_averages'
                sample_sets.add(base_name)
            else:
                sample_sets.add(db_name)
        
        return sample_sets
        
    except Exception as e:
        print(f"Error finding sample sets: {e}")
        return set()


def export_sample_set_to_plot3d_direct(sample_set: str, exporter) -> Dict:
    """Export a single sample set to Plot_3D format using direct exporter.
    
    Args:
        sample_set: Name of the sample set to export
        exporter: DirectPlot3DExporter instance
        
    Returns:
        Dict with success status, message, and created files
    """
    result = {
        'sample_set': sample_set,
        'success': False,
        'message': '',
        'files_created': []
    }
    
    try:
        # Use the direct exporter to create Plot_3D files
        # This bypasses the problematic ODS intermediate step
        created_files = exporter.export_to_plot3d(
            sample_set_name=sample_set,
            export_individual=True,
            export_averages=True
        )
        
        if created_files:
            result['success'] = True
            result['files_created'] = created_files
            result['message'] = f"Successfully exported {len(created_files)} file(s)"
        else:
            result['message'] = f"No data found for sample set '{sample_set}'"
            
        return result
        
    except Exception as e:
        result['message'] = f"Export failed: {str(e)}"
        return result


def get_file_size_mb(file_path: str) -> str:
    """Get human-readable file size."""
    try:
        size_bytes = os.path.getsize(file_path)
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    except Exception:
        return "unknown size"


if __name__ == "__main__":
    main()
