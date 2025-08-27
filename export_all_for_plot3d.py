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
        # Import required modules
        from utils.ods_exporter import ODSExporter
        from utils.plot3d_integration import StampZPlot3DIntegrator
        from utils.color_analysis_db import ColorAnalysisDB
        
        # Initialize components
        integrator = StampZPlot3DIntegrator()
        
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
                # Try to export this sample set
                result = export_sample_set_to_plot3d(sample_set, integrator)
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


def export_sample_set_to_plot3d(sample_set: str, integrator) -> Dict:
    """Export a single sample set to Plot_3D format.
    
    Args:
        sample_set: Name of the sample set to export
        integrator: StampZPlot3DIntegrator instance
        
    Returns:
        Dict with success status, message, and created files
    """
    try:
        from utils.ods_exporter import ODSExporter
        
        result = {
            'sample_set': sample_set,
            'success': False,
            'message': '',
            'files_created': []
        }
        
        # Check if this sample set has data
        try:
            # Try to create exporter and check for data
            exporter = ODSExporter(sample_set_name=sample_set)
            measurements = exporter.get_color_measurements(deduplicate=False)
            
            if not measurements:
                result['message'] = f"No measurement data found for '{sample_set}'"
                return result
                
        except Exception as e:
            result['message'] = f"Could not access data for '{sample_set}': {str(e)}"
            return result
        
        files_created = []
        export_errors = []
        
        # Export individual measurements (if available)
        try:
            individual_exporter = ODSExporter(sample_set_name=sample_set)
            individual_measurements = individual_exporter.get_color_measurements(deduplicate=True)
            
            if individual_measurements:
                # Create temporary export
                temp_export = individual_exporter.export_to_sample_set_file(format_type="ods")
                
                if temp_export and os.path.exists(temp_export):
                    # Convert to Plot_3D format
                    plot3d_success = integrator.integrate_stampz_data(
                        stampz_export_path=temp_export,
                        template_name=sample_set,
                        create_if_missing=True
                    )
                    
                    if plot3d_success:
                        # Find the created Plot_3D file
                        plot3d_file = os.path.join(
                            os.path.dirname(temp_export),
                            f"{sample_set}_Plot3D.ods"
                        )
                        if os.path.exists(plot3d_file):
                            files_created.append(plot3d_file)
                    
                    # Clean up temp export
                    try:
                        os.remove(temp_export)
                    except Exception:
                        pass
                        
        except Exception as e:
            export_errors.append(f"Individual data export failed: {str(e)}")
        
        # Export averaged measurements (if available)  
        try:
            averaged_exporter = ODSExporter(sample_set_name=f"{sample_set}_averages")
            averaged_measurements = averaged_exporter.get_color_measurements(deduplicate=False)
            
            if averaged_measurements:
                # Create temporary export for averages
                temp_avg_export = averaged_exporter.export_to_sample_set_file(format_type="ods")
                
                if temp_avg_export and os.path.exists(temp_avg_export):
                    # Convert to Plot_3D format with _Avg suffix
                    plot3d_avg_success = integrator.integrate_stampz_data(
                        stampz_export_path=temp_avg_export,
                        plot3d_file_path=os.path.join(
                            os.path.dirname(temp_avg_export),
                            f"{sample_set}_Averages_Plot3D.ods"
                        ),
                        template_name=f"{sample_set}_Averages",
                        create_if_missing=True
                    )
                    
                    if plot3d_avg_success:
                        avg_plot3d_file = os.path.join(
                            os.path.dirname(temp_avg_export),
                            f"{sample_set}_Averages_Plot3D.ods"
                        )
                        if os.path.exists(avg_plot3d_file):
                            files_created.append(avg_plot3d_file)
                    
                    # Clean up temp export
                    try:
                        os.remove(temp_avg_export)
                    except Exception:
                        pass
                        
        except Exception as e:
            # Don't treat missing averages as an error - it's optional
            if "No sample set databases" not in str(e):
                export_errors.append(f"Averaged data export failed: {str(e)}")
        
        # Determine final result
        if files_created:
            result['success'] = True
            result['files_created'] = files_created
            result['message'] = f"Successfully exported {len(files_created)} file(s)"
            
            if export_errors:
                result['message'] += f" (with {len(export_errors)} warnings)"
        else:
            result['message'] = "No data exported"
            if export_errors:
                result['message'] += f": {'; '.join(export_errors)}"
        
        return result
        
    except Exception as e:
        return {
            'sample_set': sample_set,
            'success': False,
            'message': f"Export failed: {str(e)}",
            'files_created': []
        }


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
