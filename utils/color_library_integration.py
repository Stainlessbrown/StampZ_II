#!/usr/bin/env python3
"""
Color Library Integration for StampZ
Connects color analysis, library matching, and user workflow for philatelic color research.
"""

import os
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .color_library import ColorLibrary, ColorMatch, LibraryColor
from .color_analysis_db import ColorAnalysisDB
from .ods_exporter import ODSExporter

@dataclass
class SampleAnalysisResult:
    """Result of analyzing a color sample against libraries."""
    sample_info: Dict[str, Any]  # Lab, RGB, position, etc.
    library_matches: Dict[str, List[ColorMatch]]  # Library name -> matches
    best_matches: List[Tuple[str, ColorMatch]]  # (library_name, match) sorted by Delta E
    user_action_needed: bool  # Whether user needs to decide what to do

class ColorLibraryIntegration:
    """Integration layer for complete color analysis and library workflow."""
    
    def __init__(self, default_libraries: List[str] = None):
        """Initialize with optional default libraries.
        
        Args:
            default_libraries: List of library names to load by default
        """
        self.loaded_libraries = {}  # library_name -> ColorLibrary instance
        
        # Load default libraries if specified
        if default_libraries:
            for lib_name in default_libraries:
                self.load_library(lib_name)
    
    def load_library(self, library_name: str) -> bool:
        """Load a color library for matching.
        
        Args:
            library_name: Name of the library to load
            
        Returns:
            True if loaded successfully
        """
        try:
            library = ColorLibrary(library_name)
            self.loaded_libraries[library_name] = library
            return True
        except Exception as e:
            print(f"Error loading library '{library_name}': {e}")
            return False
    
    def unload_library(self, library_name: str):
        """Unload a library from active matching."""
        if library_name in self.loaded_libraries:
            del self.loaded_libraries[library_name]
    
    def get_loaded_libraries(self) -> List[str]:
        """Get list of currently loaded library names."""
        return list(self.loaded_libraries.keys())
    
    def analyze_sample_against_libraries(
        self,
        sample_lab: Tuple[float, float, float],
        sample_rgb: Tuple[float, float, float] = None,
        threshold: float = 5.0,
        max_matches_per_library: int = 3
    ) -> SampleAnalysisResult:
        """Analyze a color sample against all loaded libraries.
        
        Args:
            sample_lab: Lab values of the sample
            sample_rgb: RGB values (will be calculated if not provided)
            threshold: Delta E threshold for matches
            max_matches_per_library: Max matches to find per library
            
        Returns:
            Complete analysis result with matches from all libraries
        """
        # Calculate RGB if not provided
        if sample_rgb is None and self.loaded_libraries:
            # Use any library for conversion (they all use the same method)
            first_lib = next(iter(self.loaded_libraries.values()))
            sample_rgb = first_lib.lab_to_rgb(sample_lab)
        
        # Search each loaded library
        library_matches = {}
        all_matches = []
        
        for lib_name, library in self.loaded_libraries.items():
            matches = library.find_closest_matches(
                sample_lab=sample_lab,
                max_delta_e=threshold,
                max_results=max_matches_per_library
            )
            library_matches[lib_name] = matches
            
            # Add to global list with library info
            for match in matches:
                all_matches.append((lib_name, match))
        
        # Sort all matches by Delta E (best first)
        all_matches.sort(key=lambda x: x[1].delta_e_2000)
        
        # Determine if user action is needed
        has_excellent_match = any(match.delta_e_2000 <= 1.0 for _, match in all_matches)
        user_action_needed = not has_excellent_match
        
        return SampleAnalysisResult(
            sample_info={
                'lab': sample_lab,
                'rgb': sample_rgb,
                'analysis_date': datetime.now().isoformat()
            },
            library_matches=library_matches,
            best_matches=all_matches[:5],  # Top 5 overall
            user_action_needed=user_action_needed
        )
    
    def add_sample_to_library(
        self,
        library_name: str,
        sample_lab: Tuple[float, float, float],
        user_name: str,
        category: str = "User Samples",
        description: str = "",
        source: str = "StampZ Analysis",
        notes: str = None,
        sample_metadata: Dict[str, Any] = None
    ) -> bool:
        """Add a new sample to a specific library with user-provided name.
        
        Args:
            library_name: Name of the library to add to
            sample_lab: Lab values of the sample
            user_name: User-provided name for the color
            category: Category within the library
            description: Description of the color
            source: Source of the sample
            notes: Optional notes
            sample_metadata: Additional metadata (image name, coordinates, etc.)
            
        Returns:
            True if added successfully
        """
        # Load library if not already loaded
        if library_name not in self.loaded_libraries:
            if not self.load_library(library_name):
                return False
        
        library = self.loaded_libraries[library_name]
        
        # Enhance description with metadata if provided
        full_description = description
        if sample_metadata:
            metadata_parts = []
            if 'image_name' in sample_metadata:
                metadata_parts.append(f"Image: {sample_metadata['image_name']}")
            if 'coordinate_point' in sample_metadata:
                metadata_parts.append(f"Point: {sample_metadata['coordinate_point']}")
            if 'position' in sample_metadata:
                x, y = sample_metadata['position']
                metadata_parts.append(f"Position: ({x:.0f},{y:.0f})")
            
            if metadata_parts:
                metadata_str = " | ".join(metadata_parts)
                full_description = f"{description} | {metadata_str}" if description else metadata_str
        
        # Enhanced notes with analysis info
        full_notes = notes or ""
        if sample_metadata and 'analysis_date' in sample_metadata:
            analysis_note = f"Analyzed: {sample_metadata['analysis_date']}"
            full_notes = f"{full_notes} | {analysis_note}" if full_notes else analysis_note
        
        return library.add_color(
            name=user_name,
            lab=sample_lab,
            description=full_description,
            category=category,
            source=source,
            notes=full_notes
        )
    
    def get_analysis_workflow_summary(
        self,
        sample_set_name: str,
        threshold: float = 5.0
    ) -> Dict[str, Any]:
        """Get a summary of analysis workflow for a complete sample set.
        
        Args:
            sample_set_name: Name of the sample set to analyze
            threshold: Delta E threshold for library matching
            
        Returns:
            Dictionary with workflow summary and recommendations
        """
        try:
            # Get color analysis data
            color_db = ColorAnalysisDB(sample_set_name)
            measurements = color_db.get_all_measurements()
            
            if not measurements:
                return {
                    'sample_set': sample_set_name,
                    'status': 'no_data',
                    'message': 'No color measurements found for this sample set'
                }
            
            # Analyze each measurement against libraries
            sample_analyses = []
            unmatched_samples = []
            
            for measurement in measurements:
                sample_lab = (
                    measurement['l_value'],
                    measurement['a_value'], 
                    measurement['b_value']
                )
                
                analysis = self.analyze_sample_against_libraries(
                    sample_lab=sample_lab,
                    threshold=threshold
                )
                
                sample_data = {
                    'measurement': measurement,
                    'analysis': analysis,
                    'has_good_matches': len(analysis.best_matches) > 0
                }
                
                sample_analyses.append(sample_data)
                
                if not sample_data['has_good_matches']:
                    unmatched_samples.append(sample_data)
            
            # Generate workflow summary
            total_samples = len(measurements)
            matched_samples = total_samples - len(unmatched_samples)
            match_percentage = (matched_samples / total_samples * 100) if total_samples > 0 else 0
            
            return {
                'sample_set': sample_set_name,
                'status': 'analyzed',
                'summary': {
                    'total_samples': total_samples,
                    'matched_samples': matched_samples,
                    'unmatched_samples': len(unmatched_samples),
                    'match_percentage': match_percentage,
                    'loaded_libraries': list(self.loaded_libraries.keys()),
                    'threshold_used': threshold
                },
                'sample_analyses': sample_analyses,
                'unmatched_samples': unmatched_samples,
                'recommendations': self._generate_recommendations(sample_analyses, unmatched_samples)
            }
            
        except Exception as e:
            return {
                'sample_set': sample_set_name,
                'status': 'error',
                'error': str(e)
            }
    
    def _generate_recommendations(
        self,
        sample_analyses: List[Dict],
        unmatched_samples: List[Dict]
    ) -> List[str]:
        """Generate workflow recommendations based on analysis results."""
        recommendations = []
        
        if unmatched_samples:
            recommendations.append(
                f"Consider adding {len(unmatched_samples)} unmatched samples to your libraries "
                "to improve future matching"
            )
        
        if sample_analyses:
            # Find most common categories in matches
            category_counts = {}
            for analysis in sample_analyses:
                for _, match in analysis['analysis'].best_matches:
                    cat = match.library_color.category
                    category_counts[cat] = category_counts.get(cat, 0) + 1
            
            if category_counts:
                top_category = max(category_counts.items(), key=lambda x: x[1])
                recommendations.append(
                    f"Most matches found in '{top_category[0]}' category "
                    f"({top_category[1]} matches)"
                )
        
        return recommendations
    
    def export_analysis_with_library_matches(
        self,
        sample_set_name: str,
        output_dir: str = None,
        include_library_matches: bool = True,
        threshold: float = 5.0
    ) -> str:
        """Export analysis results with library matches to ODS file.
        
        Args:
            sample_set_name: Sample set to export
            output_dir: Directory for output file (default: data/exports)
            include_library_matches: Whether to include library match columns
            threshold: Delta E threshold for matches
            
        Returns:
            Path to created ODS file
        """
        # Get workflow summary
        workflow = self.get_analysis_workflow_summary(sample_set_name, threshold)
        
        if workflow['status'] != 'analyzed':
            raise ValueError(f"Cannot export: {workflow.get('message', workflow.get('error', 'Unknown error'))}")
        
        # Standard ODS export
        exporter = ODSExporter(sample_set_name)
        
        # Determine output path
        if output_dir is None:
            # Use STAMPZ_DATA_DIR environment variable if available (for packaged apps)
            stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
            if stampz_data_dir:
                output_dir = os.path.join(stampz_data_dir, "data", "exports")
            else:
                # Fallback to relative path for development
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                output_dir = os.path.join(current_dir, "data", "exports")
            os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if include_library_matches:
            filename = f"{sample_set_name}_with_library_matches_{timestamp}.ods"
        else:
            filename = f"{sample_set_name}_analysis_{timestamp}.ods"
        
        output_path = os.path.join(output_dir, filename)
        
        # Export with enhanced data
        success = exporter.export_to_ods(
            output_path=output_path,
            include_library_data=include_library_matches,
            library_integration=self if include_library_matches else None,
            threshold=threshold
        )
        
        if success:
            return output_path
        else:
            raise RuntimeError("Failed to export ODS file")

# Convenience functions for common workflows
def quick_philatelic_analysis(
    sample_lab: Tuple[float, float, float],
    libraries: List[str] = None
) -> SampleAnalysisResult:
    """Quick analysis against philatelic libraries.
    
    Args:
        sample_lab: Lab values to analyze
        libraries: Library names (default: ['philatelic_colors', 'basic_colors'])
        
    Returns:
        Analysis result
    """
    if libraries is None:
        libraries = ['philatelic_colors', 'basic_colors']
    
    integration = ColorLibraryIntegration(libraries)
    return integration.analyze_sample_against_libraries(sample_lab)

def create_standard_philatelic_libraries():
    """Create standard philatelic libraries if they don't exist."""
    from .color_library import ColorLibrary
    
    print("Creating standard color libraries...")
    
    # No longer automatically creates libraries
    print("Library creation is now handled through the Color Library Manager interface")
    return []
