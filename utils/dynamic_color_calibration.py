#!/usr/bin/env python3
"""
Dynamic Color Calibration System for StampZ
Uses database reference colors to create adaptive correction matrices.
"""

import numpy as np
import sqlite3
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from PIL import Image
import colorspacious

@dataclass
class ReferenceColor:
    """Reference color with expected values."""
    name: str
    expected_rgb: Tuple[int, int, int]
    expected_lab: Tuple[float, float, float]
    category: str  # Primary, Secondary, Neutral

@dataclass
class CalibrationMeasurement:
    """Measured color for calibration."""
    name: str
    measured_rgb: Tuple[int, int, int]
    reference: ReferenceColor
    deviation_rgb: Tuple[int, int, int]
    deviation_magnitude: float

class DynamicColorCalibrator:
    """Dynamic color calibration using database reference colors."""
    
    def __init__(self, library_path: Optional[str] = None):
        """Initialize calibrator with reference colors from database."""
        self.reference_colors = {}
        self.calibration_matrix = None
        self.correction_stats = {}
        
        if library_path is None:
            # Use default basic colors library
            library_path = self._find_basic_colors_db()
        
        self.library_path = library_path
        self._load_reference_colors()
    
    def _find_basic_colors_db(self) -> str:
        """Find the basic colors database."""
        # Check multiple possible locations
        possible_paths = [
            "/Users/stanbrown/Desktop/StampZ/data/color_libraries/basic_colors_library.db",
            "data/color_libraries/basic_colors_library.db",
            "../data/color_libraries/basic_colors_library.db"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("Could not find basic_colors_library.db")
    
    def _load_reference_colors(self):
        """Load reference colors from the database."""
        print(f"Loading reference colors from: {self.library_path}")
        
        try:
            conn = sqlite3.connect(self.library_path)
            cursor = conn.cursor()
            
            # Query all colors from the library
            cursor.execute("""
                SELECT name, description, lab_l, lab_a, lab_b, 
                       rgb_r, rgb_g, rgb_b, category
                FROM library_colors
                ORDER BY name
            """)
            
            rows = cursor.fetchall()
            print(f"Found {len(rows)} reference colors in database")
            
            for row in rows:
                name, desc, l_star, a_star, b_star, red, green, blue, category = row
                
                # Create reference color object
                ref_color = ReferenceColor(
                    name=name,
                    expected_rgb=(int(round(red)), int(round(green)), int(round(blue))),
                    expected_lab=(l_star, a_star, b_star),
                    category=category
                )
                
                self.reference_colors[name.lower()] = ref_color
                print(f"  Loaded: {name} - RGB({int(red)}, {int(green)}, {int(blue)}) LAB({l_star:.1f}, {a_star:.1f}, {b_star:.1f})")
            
            conn.close()
            
        except Exception as e:
            print(f"Error loading reference colors: {e}")
            # Fallback to hardcoded references
            self._load_fallback_references()
    
    def _load_fallback_references(self):
        """Load fallback reference colors if database fails."""
        print("Using fallback reference colors")
        fallback_colors = {
            'pure red': ReferenceColor('Pure Red', (255, 0, 0), (53.0, 80.0, 67.0), 'Primary'),
            'pure green': ReferenceColor('Pure Green', (0, 255, 0), (87.0, -86.0, 83.0), 'Primary'),
            'pure blue': ReferenceColor('Pure Blue', (0, 0, 255), (32.0, 79.0, -108.0), 'Primary'),
            'white': ReferenceColor('White', (255, 255, 255), (100.0, 0.0, 0.0), 'Neutral'),
            'black': ReferenceColor('Black', (0, 0, 0), (0.0, 0.0, 0.0), 'Neutral'),
            'gray 50%': ReferenceColor('Gray 50%', (128, 128, 128), (54.0, 0.0, 0.0), 'Neutral')
        }
        self.reference_colors = fallback_colors
    
    def measure_reference_colors(self, measurements: Dict[str, Tuple[int, int, int]]) -> List[CalibrationMeasurement]:
        """
        Process measured reference colors for calibration.
        
        Args:
            measurements: Dict mapping color names to measured RGB tuples
            
        Returns:
            List of CalibrationMeasurement objects
        """
        calibration_measurements = []
        
        print("\n=== CALIBRATION MEASUREMENT ANALYSIS ===")
        print(f"{'Color':<15} {'Expected':<15} {'Measured':<15} {'Deviation':<15} {'Magnitude'}")
        print("-" * 80)
        
        for color_name, measured_rgb in measurements.items():
            # Find matching reference color (case insensitive)
            ref_key = None
            for key in self.reference_colors.keys():
                if key.lower() in color_name.lower() or color_name.lower() in key.lower():
                    ref_key = key
                    break
            
            if not ref_key:
                print(f"Warning: No reference found for '{color_name}'")
                continue
            
            reference = self.reference_colors[ref_key]
            expected_rgb = reference.expected_rgb
            
            # Calculate deviations
            dev_r = measured_rgb[0] - expected_rgb[0]
            dev_g = measured_rgb[1] - expected_rgb[1]
            dev_b = measured_rgb[2] - expected_rgb[2]
            deviation_rgb = (dev_r, dev_g, dev_b)
            
            # Calculate magnitude of deviation
            magnitude = np.sqrt(dev_r**2 + dev_g**2 + dev_b**2)
            
            measurement = CalibrationMeasurement(
                name=color_name,
                measured_rgb=measured_rgb,
                reference=reference,
                deviation_rgb=deviation_rgb,
                deviation_magnitude=magnitude
            )
            
            calibration_measurements.append(measurement)
            
            print(f"{color_name:<15} {expected_rgb!s:<15} {measured_rgb!s:<15} {deviation_rgb!s:<15} {magnitude:.2f}")
        
        return calibration_measurements
    
    def calculate_calibration_matrix(self, measurements: List[CalibrationMeasurement]) -> Dict:
        """
        Calculate calibration matrix from measurement deviations.
        
        Args:
            measurements: List of calibration measurements
            
        Returns:
            Calibration matrix dictionary
        """
        if not measurements:
            print("No measurements provided for calibration")
            return {}
        
        # Collect channel deviations
        r_deviations = []
        g_deviations = []
        b_deviations = []
        
        # Separate by color category for weighted analysis
        primary_measurements = []
        neutral_measurements = []
        secondary_measurements = []
        
        for measurement in measurements:
            r_dev, g_dev, b_dev = measurement.deviation_rgb
            r_deviations.append(r_dev)
            g_deviations.append(g_dev)
            b_deviations.append(b_dev)
            
            if measurement.reference.category == 'Primary':
                primary_measurements.append(measurement)
            elif measurement.reference.category == 'Neutral':
                neutral_measurements.append(measurement)
            elif measurement.reference.category == 'Secondary':
                secondary_measurements.append(measurement)
        
        # Calculate statistics
        stats = {
            'total_samples': len(measurements),
            'primary_samples': len(primary_measurements),
            'neutral_samples': len(neutral_measurements),
            'secondary_samples': len(secondary_measurements),
            'avg_deviations': {
                'red': np.mean(r_deviations),
                'green': np.mean(g_deviations),
                'blue': np.mean(b_deviations)
            },
            'std_deviations': {
                'red': np.std(r_deviations),
                'green': np.std(g_deviations),
                'blue': np.std(b_deviations)
            },
            'max_deviations': {
                'red': max(r_deviations, key=abs),
                'green': max(g_deviations, key=abs),
                'blue': max(b_deviations, key=abs)
            }
        }
        
        # Calculate weighted corrections
        # Give more weight to primary colors and neutrals
        primary_weight = 0.4
        neutral_weight = 0.4
        secondary_weight = 0.2
        
        # Weighted channel corrections
        weighted_r_correction = 0
        weighted_g_correction = 0
        weighted_b_correction = 0
        total_weight = 0
        
        for measurement in measurements:
            weight = primary_weight if measurement.reference.category == 'Primary' else \
                    neutral_weight if measurement.reference.category == 'Neutral' else \
                    secondary_weight
            
            r_dev, g_dev, b_dev = measurement.deviation_rgb
            weighted_r_correction += r_dev * weight
            weighted_g_correction += g_dev * weight
            weighted_b_correction += b_dev * weight
            total_weight += weight
        
        if total_weight > 0:
            weighted_r_correction /= total_weight
            weighted_g_correction /= total_weight
            weighted_b_correction /= total_weight
        
        # Create calibration matrix
        calibration_matrix = {
            'method': 'weighted_reference_calibration',
            'corrections': {
                'red_correction': -weighted_r_correction,  # Subtract to correct
                'green_correction': -weighted_g_correction,
                'blue_correction': -weighted_b_correction
            },
            'confidence_metrics': {
                'sample_count': len(measurements),
                'primary_colors_used': len(primary_measurements),
                'avg_magnitude': np.mean([m.deviation_magnitude for m in measurements]),
                'max_magnitude': max([m.deviation_magnitude for m in measurements]),
                'channel_consistency': {
                    'red_std': stats['std_deviations']['red'],
                    'green_std': stats['std_deviations']['green'],
                    'blue_std': stats['std_deviations']['blue']
                }
            },
            'detailed_stats': stats
        }
        
        self.calibration_matrix = calibration_matrix
        self.correction_stats = stats
        
        return calibration_matrix
    
    def apply_calibration(self, rgb: Tuple[int, int, int], 
                         calibration_matrix: Optional[Dict] = None) -> Tuple[int, int, int]:
        """
        Apply calibration correction to RGB values.
        
        Args:
            rgb: Original RGB tuple
            calibration_matrix: Optional calibration matrix (uses stored one if None)
            
        Returns:
            Corrected RGB tuple
        """
        if calibration_matrix is None:
            calibration_matrix = self.calibration_matrix
        
        if not calibration_matrix or 'corrections' not in calibration_matrix:
            print("Warning: No calibration matrix available")
            return rgb
        
        corrections = calibration_matrix['corrections']
        r, g, b = rgb
        
        # Apply corrections
        r_corrected = r + corrections.get('red_correction', 0)
        g_corrected = g + corrections.get('green_correction', 0)
        b_corrected = b + corrections.get('blue_correction', 0)
        
        # Clamp to valid range
        r_final = max(0, min(255, int(round(r_corrected))))
        g_final = max(0, min(255, int(round(g_corrected))))
        b_final = max(0, min(255, int(round(b_corrected))))
        
        return (r_final, g_final, b_final)
    
    def validate_calibration(self, validation_measurements: Dict[str, Tuple[int, int, int]]) -> Dict:
        """
        Validate calibration accuracy using test measurements.
        
        Args:
            validation_measurements: Dict of test measurements
            
        Returns:
            Validation results
        """
        if not self.calibration_matrix:
            return {"error": "No calibration matrix available"}
        
        validation_results = {
            'original_errors': [],
            'corrected_errors': [],
            'improvement': {},
            'per_color_results': {}
        }
        
        print("\n=== CALIBRATION VALIDATION ===")
        print(f"{'Color':<15} {'Original Error':<15} {'Corrected Error':<15} {'Improvement'}")
        print("-" * 70)
        
        for color_name, measured_rgb in validation_measurements.items():
            # Find reference
            ref_key = None
            for key in self.reference_colors.keys():
                if key.lower() in color_name.lower() or color_name.lower() in key.lower():
                    ref_key = key
                    break
            
            if not ref_key:
                continue
            
            reference = self.reference_colors[ref_key]
            expected_rgb = reference.expected_rgb
            
            # Calculate original error
            original_error = np.sqrt(sum((m - e)**2 for m, e in zip(measured_rgb, expected_rgb)))
            
            # Apply calibration
            corrected_rgb = self.apply_calibration(measured_rgb)
            
            # Calculate corrected error
            corrected_error = np.sqrt(sum((c - e)**2 for c, e in zip(corrected_rgb, expected_rgb)))
            
            # Calculate improvement
            improvement = original_error - corrected_error
            improvement_pct = (improvement / original_error * 100) if original_error > 0 else 0
            
            validation_results['original_errors'].append(original_error)
            validation_results['corrected_errors'].append(corrected_error)
            validation_results['per_color_results'][color_name] = {
                'original_rgb': measured_rgb,
                'corrected_rgb': corrected_rgb,
                'expected_rgb': expected_rgb,
                'original_error': original_error,
                'corrected_error': corrected_error,
                'improvement': improvement,
                'improvement_pct': improvement_pct
            }
            
            print(f"{color_name:<15} {original_error:<15.2f} {corrected_error:<15.2f} {improvement:+.2f} ({improvement_pct:+.1f}%)")
        
        # Overall statistics
        if validation_results['original_errors']:
            avg_original = np.mean(validation_results['original_errors'])
            avg_corrected = np.mean(validation_results['corrected_errors'])
            overall_improvement = avg_original - avg_corrected
            overall_improvement_pct = (overall_improvement / avg_original * 100) if avg_original > 0 else 0
            
            validation_results['improvement'] = {
                'avg_original_error': avg_original,
                'avg_corrected_error': avg_corrected,
                'avg_improvement': overall_improvement,
                'improvement_percentage': overall_improvement_pct
            }
            
            print(f"\nOverall: {overall_improvement:+.2f} error reduction ({overall_improvement_pct:+.1f}% improvement)")
        
        return validation_results
    
    def save_calibration(self, filename: str):
        """Save calibration matrix to file."""
        if not self.calibration_matrix:
            print("No calibration matrix to save")
            return False
        
        try:
            calibration_data = {
                'calibration_matrix': self.calibration_matrix,
                'reference_colors': {name: {
                    'expected_rgb': ref.expected_rgb,
                    'expected_lab': ref.expected_lab,
                    'category': ref.category
                } for name, ref in self.reference_colors.items()}
            }
            
            with open(filename, 'w') as f:
                json.dump(calibration_data, f, indent=2)
            
            print(f"Calibration saved to: {filename}")
            return True
            
        except Exception as e:
            print(f"Error saving calibration: {e}")
            return False
    
    def load_calibration(self, filename: str) -> bool:
        """Load calibration matrix from file."""
        try:
            with open(filename, 'r') as f:
                calibration_data = json.load(f)
            
            self.calibration_matrix = calibration_data['calibration_matrix']
            print(f"Calibration loaded from: {filename}")
            return True
            
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return False
    
    def generate_calibration_report(self) -> str:
        """Generate a comprehensive calibration report."""
        if not self.calibration_matrix:
            return "No calibration data available"
        
        matrix = self.calibration_matrix
        corrections = matrix['corrections']
        confidence = matrix['confidence_metrics']
        
        report = [
            "=== STAMPZ COLOR CALIBRATION REPORT ===",
            "",
            f"Calibration Method: {matrix.get('method', 'Unknown')}",
            f"Reference Colors Used: {confidence['sample_count']}",
            f"Primary Colors: {confidence['primary_colors_used']}",
            "",
            "CHANNEL CORRECTIONS:",
            f"  Red:   {corrections['red_correction']:+6.2f}",
            f"  Green: {corrections['green_correction']:+6.2f}",
            f"  Blue:  {corrections['blue_correction']:+6.2f}",
            "",
            "CONFIDENCE METRICS:",
            f"  Average Error Magnitude: {confidence['avg_magnitude']:.2f}",
            f"  Maximum Error Magnitude: {confidence['max_magnitude']:.2f}",
            f"  Red Channel Consistency: {confidence['channel_consistency']['red_std']:.2f}",
            f"  Green Channel Consistency: {confidence['channel_consistency']['green_std']:.2f}",
            f"  Blue Channel Consistency: {confidence['channel_consistency']['blue_std']:.2f}",
            "",
            "USAGE:",
            "  Apply these corrections to any color measurements:",
            f"  corrected_r = measured_r + ({corrections['red_correction']:+.1f})",
            f"  corrected_g = measured_g + ({corrections['green_correction']:+.1f})",
            f"  corrected_b = measured_b + ({corrections['blue_correction']:+.1f})",
            "",
            "QUALITY ASSESSMENT:",
        ]
        
        # Quality assessment
        avg_magnitude = confidence['avg_magnitude']
        if avg_magnitude < 5:
            report.append("  ✓ EXCELLENT: Very low deviation from references")
        elif avg_magnitude < 10:
            report.append("  ✓ GOOD: Acceptable deviation from references")
        elif avg_magnitude < 20:
            report.append("  ⚠ FAIR: Moderate deviation - consider display calibration")
        else:
            report.append("  ⚠ POOR: High deviation - check display settings or screenshot method")
        
        max_std = max(confidence['channel_consistency'].values())
        if max_std < 5:
            report.append("  ✓ CONSISTENT: Low channel variation")
        elif max_std < 10:
            report.append("  ⚠ MODERATE: Some channel inconsistency")
        else:
            report.append("  ⚠ INCONSISTENT: High channel variation - may need per-color corrections")
        
        return "\n".join(report)

def create_calibration_workflow():
    """Create an interactive calibration workflow."""
    print("=== STAMPZ DYNAMIC COLOR CALIBRATION ===")
    print()
    print("This tool will help you calibrate StampZ using your reference colors.")
    print("You'll need to measure the reference colors using screenshots or your display.")
    print()
    
    # Initialize calibrator
    try:
        calibrator = DynamicColorCalibrator()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    # Show available reference colors
    print("Available reference colors:")
    for name, ref in calibrator.reference_colors.items():
        print(f"  - {ref.name}: Expected RGB{ref.expected_rgb}")
    print()
    
    # Guide user through measurement
    print("STEP 1: Measure Reference Colors")
    print("Take screenshots of known reference colors and measure them using StampZ.")
    print("Enter the measured values below:")
    print()
    
    measurements = {}
    
    # Ask for key color measurements
    key_colors = ['Pure Red', 'Pure Green', 'Pure Blue', 'White', 'Gray 50%']
    
    for color_name in key_colors:
        while True:
            try:
                user_input = input(f"Enter measured RGB for {color_name} (e.g., '255,0,0' or 'skip'): ").strip()
                
                if user_input.lower() == 'skip':
                    print(f"Skipped {color_name}")
                    break
                
                # Parse RGB values
                rgb_str = user_input.replace('(', '').replace(')', '').replace(' ', '')
                rgb_values = [int(x.strip()) for x in rgb_str.split(',')]
                
                if len(rgb_values) != 3:
                    print("Please enter 3 numbers separated by commas")
                    continue
                
                if not all(0 <= val <= 255 for val in rgb_values):
                    print("RGB values must be between 0 and 255")
                    continue
                
                measurements[color_name] = tuple(rgb_values)
                print(f"✓ Recorded {color_name}: {measurements[color_name]}")
                break
                
            except ValueError:
                print("Please enter valid numbers")
            except KeyboardInterrupt:
                print("\nCalibration cancelled")
                return
    
    if not measurements:
        print("No measurements provided. Cannot create calibration.")
        return
    
    print(f"\nSTEP 2: Analyze {len(measurements)} Measurements")
    
    # Process measurements
    calibration_measurements = calibrator.measure_reference_colors(measurements)
    
    # Calculate calibration matrix
    print("\nSTEP 3: Calculate Calibration Matrix")
    matrix = calibrator.calculate_calibration_matrix(calibration_measurements)
    
    if matrix:
        # Show report
        print("\nSTEP 4: Calibration Results")
        report = calibrator.generate_calibration_report()
        print(report)
        
        # Test calibration
        print("\nSTEP 5: Test Calibration")
        print("Testing corrections on your measurements:")
        
        for color_name, measured_rgb in measurements.items():
            corrected_rgb = calibrator.apply_calibration(measured_rgb)
            print(f"{color_name}: {measured_rgb} → {corrected_rgb}")
        
        # Save option
        save_choice = input("\nWould you like to save this calibration? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes']:
            filename = input("Enter filename (default: 'stampz_calibration.json'): ").strip()
            if not filename:
                filename = 'stampz_calibration.json'
            
            if calibrator.save_calibration(filename):
                print(f"\n✓ Calibration saved! You can now use these corrections in StampZ.")
                print(f"Manual corrections to apply:")
                corrections = matrix['corrections']
                print(f"  Red: {corrections['red_correction']:+.1f}")
                print(f"  Green: {corrections['green_correction']:+.1f}")
                print(f"  Blue: {corrections['blue_correction']:+.1f}")
    else:
        print("Failed to create calibration matrix")

if __name__ == "__main__":
    create_calibration_workflow()
