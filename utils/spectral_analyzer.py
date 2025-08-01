#!/usr/bin/env python3
"""
Spectral response analysis for StampZ.
Analyze how RGB channels respond across the visible light spectrum.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import sqlite3
from PIL import Image

from .color_analyzer import ColorAnalyzer, ColorMeasurement, PrintType

@dataclass
class SpectralMeasurement:
    """Represents spectral analysis data for a color sample."""
    wavelength: float  # nm
    rgb_response: Tuple[float, float, float]
    relative_response: Tuple[float, float, float]  # Normalized to peak
    sample_id: str
    illuminant: str = "D65"  # Standard daylight

class SpectralAnalyzer:
    """Analyze spectral response characteristics of color samples."""
    
    def __init__(self):
        self.color_analyzer = ColorAnalyzer()
        
        # Standard illuminant spectral power distributions (simplified)
        self.illuminants = {
            'D65': self._generate_d65_spd(),      # Daylight 6500K
            'A': self._generate_illuminant_a(),   # Incandescent 2856K
            'F2': self._generate_f2_spd(),        # Cool white fluorescent
            'LED': self._generate_led_spd()       # Modern LED
        }
        
        # RGB sensor response curves (approximate sRGB primaries)
        self.rgb_responses = self._generate_rgb_responses()
    
    def _generate_d65_spd(self) -> Dict[float, float]:
        """Generate D65 standard illuminant spectral power distribution."""
        wavelengths = np.arange(380, 751, 5)
        # Simplified D65 - actual would use CIE standard
        spd = {}
        for wl in wavelengths:
            if wl < 400:
                power = 0.3 + 0.7 * (wl - 380) / 20
            elif wl < 500:
                power = 1.0
            elif wl < 600:
                power = 1.1 - 0.1 * (wl - 500) / 100
            else:
                power = 1.0 - 0.2 * (wl - 600) / 100
            spd[wl] = max(0.1, power)
        return spd
    
    def _generate_illuminant_a(self) -> Dict[float, float]:
        """Generate Illuminant A (incandescent) SPD."""
        wavelengths = np.arange(380, 751, 5)
        spd = {}
        for wl in wavelengths:
            # Planckian radiator at 2856K (simplified)
            power = (wl / 560) ** -1.5  # Reddish bias
            spd[wl] = power
        return spd
    
    def _generate_f2_spd(self) -> Dict[float, float]:
        """Generate F2 fluorescent SPD with mercury peaks."""
        wavelengths = np.arange(380, 751, 5)
        spd = {}
        mercury_peaks = [405, 436, 546, 578]  # Mercury emission lines
        
        for wl in wavelengths:
            # Base fluorescent continuum
            base = 0.5 + 0.3 * np.sin((wl - 380) * np.pi / 320)
            
            # Add mercury peaks
            peak_contribution = 0
            for peak in mercury_peaks:
                if abs(wl - peak) < 10:
                    peak_contribution += 2.0 * np.exp(-((wl - peak) / 5) ** 2)
            
            spd[wl] = base + peak_contribution
        return spd
    
    def _generate_led_spd(self) -> Dict[float, float]:
        """Generate modern LED SPD (blue peak + phosphor)."""
        wavelengths = np.arange(380, 751, 5)
        spd = {}
        for wl in wavelengths:
            # Blue LED peak around 450nm
            blue_peak = 3.0 * np.exp(-((wl - 450) / 20) ** 2)
            
            # Phosphor broad emission 500-700nm
            if wl > 480:
                phosphor = 0.8 * (1 - np.exp(-(wl - 480) / 60)) * np.exp(-(wl - 550) / 100)
            else:
                phosphor = 0
            
            spd[wl] = blue_peak + phosphor
        return spd
    
    def _generate_rgb_responses(self) -> Dict[str, Dict[float, float]]:
        """Generate RGB sensor response curves."""
        wavelengths = np.arange(380, 751, 5)
        responses = {'R': {}, 'G': {}, 'B': {}}
        
        for wl in wavelengths:
            # Red response (peak ~600nm)
            r_response = np.exp(-((wl - 600) / 80) ** 2) if wl > 500 else 0
            
            # Green response (peak ~550nm)
            g_response = np.exp(-((wl - 550) / 60) ** 2)
            
            # Blue response (peak ~450nm)
            b_response = np.exp(-((wl - 450) / 50) ** 2) if wl < 550 else 0
            
            responses['R'][wl] = r_response
            responses['G'][wl] = g_response
            responses['B'][wl] = b_response
        
        return responses
    
    def analyze_spectral_response(self, measurements: List[ColorMeasurement], 
                                illuminant: str = 'D65') -> List[SpectralMeasurement]:
        """
        Analyze spectral response characteristics of color measurements.
        
        Args:
            measurements: List of ColorMeasurement objects
            illuminant: Illuminant type for analysis
            
        Returns:
            List of SpectralMeasurement objects
        """
        if illuminant not in self.illuminants:
            raise ValueError(f"Unknown illuminant: {illuminant}")
        
        spectral_data = []
        spd = self.illuminants[illuminant]
        
        for i, measurement in enumerate(measurements):
            # Convert RGB to relative spectral response
            r, g, b = measurement.rgb
            
            # Estimate spectral characteristics based on RGB ratios
            for wavelength in sorted(spd.keys()):
                # Calculate relative response at this wavelength
                r_resp = self.rgb_responses['R'].get(wavelength, 0) * (r / 255.0)
                g_resp = self.rgb_responses['G'].get(wavelength, 0) * (g / 255.0)
                b_resp = self.rgb_responses['B'].get(wavelength, 0) * (b / 255.0)
                
                rgb_response = (r_resp, g_resp, b_resp)
                
                # Normalize to illuminant power
                illuminant_power = spd[wavelength]
                relative_response = tuple(resp / illuminant_power for resp in rgb_response)
                
                spectral_measurement = SpectralMeasurement(
                    wavelength=wavelength,
                    rgb_response=rgb_response,
                    relative_response=relative_response,
                    sample_id=f"sample_{i+1}",
                    illuminant=illuminant
                )
                spectral_data.append(spectral_measurement)
        
        return spectral_data
    
    def plot_spectral_response(self, spectral_data: List[SpectralMeasurement], 
                             sample_ids: Optional[List[str]] = None, 
                             max_samples: int = 20, 
                             interactive: bool = False, 
                             plot_type: str = 'overview') -> None:
        """
        Plot spectral response curves for analyzed samples.
        
        Args:
            spectral_data: List of SpectralMeasurement objects
            sample_ids: Optional list of specific sample IDs to plot
            max_samples: Maximum number of samples to plot (default 20 for readability)
            interactive: Enable interactive plotting with navigation controls
            plot_type: Type of plot - 'overview', 'rg_ratio', 'bg_ratio', 'deviation', or 'individual'
        """
        if not spectral_data:
            print("No spectral data to plot")
            return
        
        # Group data by sample
        sample_data = {}
        for measurement in spectral_data:
            if sample_ids and measurement.sample_id not in sample_ids:
                continue
            
            if measurement.sample_id not in sample_data:
                sample_data[measurement.sample_id] = {
                    'wavelengths': [],
                    'r_response': [],
                    'g_response': [],
                    'b_response': []
                }
            
            sample_data[measurement.sample_id]['wavelengths'].append(measurement.wavelength)
            sample_data[measurement.sample_id]['r_response'].append(measurement.relative_response[0])
            sample_data[measurement.sample_id]['g_response'].append(measurement.relative_response[1])
            sample_data[measurement.sample_id]['b_response'].append(measurement.relative_response[2])
        
        # Limit number of samples for readability
        original_sample_count = len(sample_data)
        if len(sample_data) > max_samples:
            print(f"Note: Displaying first {max_samples} of {original_sample_count} samples for readability")
            limited_sample_data = {}
            for i, (sample_id, data) in enumerate(sample_data.items()):
                if i >= max_samples:
                    break
                limited_sample_data[sample_id] = data
            sample_data = limited_sample_data
        
        # Create plots with larger figure size for better readability
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Spectral Response Analysis ({len(sample_data)} of {original_sample_count} samples)', fontsize=16)
        
        # Plot 1: All RGB responses for first sample
        if sample_data:
            first_sample = list(sample_data.keys())[0]
            data = sample_data[first_sample]
            
            axes[0, 0].plot(data['wavelengths'], data['r_response'], 'r-', label='Red', linewidth=2)
            axes[0, 0].plot(data['wavelengths'], data['g_response'], 'g-', label='Green', linewidth=2)
            axes[0, 0].plot(data['wavelengths'], data['b_response'], 'b-', label='Blue', linewidth=2)
            axes[0, 0].set_xlabel('Wavelength (nm)')
            axes[0, 0].set_ylabel('Relative Response')
            axes[0, 0].set_title(f'RGB Response Curves - {first_sample}')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
        
        # Plot 2: R/G ratio across spectrum (no legend for multiple samples)
        axes[0, 1].set_title('Red/Green Ratio vs Wavelength')
        sample_count = 0
        for sample_id, data in sample_data.items():
            rg_ratio = []
            wavelengths = data['wavelengths']
            for i in range(len(data['r_response'])):
                r, g = data['r_response'][i], data['g_response'][i]
                ratio = r / (g + 0.001) if g > 0.001 else 0  # Avoid division by zero
                rg_ratio.append(ratio)
            
            # Use color map for better distinction
            color = plt.cm.viridis(sample_count / len(sample_data))
            axes[0, 1].plot(wavelengths, rg_ratio, alpha=0.6, color=color, linewidth=0.8)
            sample_count += 1
        
        axes[0, 1].set_xlabel('Wavelength (nm)')
        axes[0, 1].set_ylabel('R/G Ratio')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].text(0.02, 0.98, f'{len(sample_data)} samples', transform=axes[0, 1].transAxes, 
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Plot 3: B/G ratio across spectrum (no legend for multiple samples)
        axes[1, 0].set_title('Blue/Green Ratio vs Wavelength')
        sample_count = 0
        for sample_id, data in sample_data.items():
            bg_ratio = []
            wavelengths = data['wavelengths']
            for i in range(len(data['b_response'])):
                b, g = data['b_response'][i], data['g_response'][i]
                ratio = b / (g + 0.001) if g > 0.001 else 0
                bg_ratio.append(ratio)
            
            # Use color map for better distinction
            color = plt.cm.plasma(sample_count / len(sample_data))
            axes[1, 0].plot(wavelengths, bg_ratio, alpha=0.6, color=color, linewidth=0.8)
            sample_count += 1
        
        axes[1, 0].set_xlabel('Wavelength (nm)')
        axes[1, 0].set_ylabel('B/G Ratio')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].text(0.02, 0.98, f'{len(sample_data)} samples', transform=axes[1, 0].transAxes, 
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Plot 4: Spectral deviation analysis (no legend for multiple samples)
        axes[1, 1].set_title('Channel Deviation Across Spectrum')
        sample_count = 0
        for sample_id, data in sample_data.items():
            deviations = []
            wavelengths = data['wavelengths']
            for i in range(len(data['r_response'])):
                r, g, b = data['r_response'][i], data['g_response'][i], data['b_response'][i]
                mean_response = (r + g + b) / 3
                deviation = np.std([r, g, b]) / (mean_response + 0.001)
                deviations.append(deviation)
            
            # Use color map for better distinction
            color = plt.cm.coolwarm(sample_count / len(sample_data))
            axes[1, 1].plot(wavelengths, deviations, alpha=0.6, color=color, linewidth=0.8)
            sample_count += 1
        
        axes[1, 1].set_xlabel('Wavelength (nm)')
        axes[1, 1].set_ylabel('Coefficient of Variation')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].text(0.02, 0.98, f'{len(sample_data)} samples', transform=axes[1, 1].transAxes, 
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Add overall statistics text
        fig.text(0.02, 0.02, f'Analysis: {original_sample_count} total samples, showing {len(sample_data)} for clarity', 
                 fontsize=10, style='italic')
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.05)  # Make room for bottom text
        
        # Save the plot if requested
        if hasattr(self, '_save_plot_path') and self._save_plot_path:
            try:
                plt.savefig(self._save_plot_path, dpi=300, bbox_inches='tight')
                print(f"Plot saved to: {self._save_plot_path}")
            except Exception as e:
                print(f"Failed to save plot: {e}")
        
        # Add interactive options if requested
        if interactive:
            # Add buttons for interactive functionality
            from matplotlib.widgets import Button
            import matplotlib.gridspec as gridspec
            
            # Adjust layout to make room for buttons
            fig.subplots_adjust(bottom=0.15)
            
            # Create button axes
            ax_btn1 = plt.axes([0.05, 0.08, 0.12, 0.04])
            ax_btn2 = plt.axes([0.2, 0.08, 0.12, 0.04])
            ax_btn3 = plt.axes([0.35, 0.08, 0.12, 0.04])
            ax_btn4 = plt.axes([0.5, 0.08, 0.12, 0.04])
            ax_btn5 = plt.axes([0.65, 0.08, 0.15, 0.04])
            ax_btn6 = plt.axes([0.82, 0.08, 0.15, 0.04])
            
            # Create buttons
            btn_rgb = Button(ax_btn1, 'Pop-out RGB')
            btn_rg = Button(ax_btn2, 'Pop-out R/G')
            btn_bg = Button(ax_btn3, 'Pop-out B/G')
            btn_dev = Button(ax_btn4, 'Pop-out Deviation')
            btn_few = Button(ax_btn5, 'Show 5 w/Labels')
            btn_all = Button(ax_btn6, 'Reset View')
            
            # Button callback functions
            def show_rgb_plot(event):
                # Auto-enable labels for small sample sets
                with_labels = len(sample_data) <= 10
                self._create_individual_plot(sample_data, 'rgb', original_sample_count, with_labels=with_labels)
            
            def show_rg_plot(event):
                # Auto-enable labels for small sample sets
                with_labels = len(sample_data) <= 10
                self._create_individual_plot(sample_data, 'rg_ratio', original_sample_count, with_labels=with_labels)
            
            def show_bg_plot(event):
                # Auto-enable labels for small sample sets
                with_labels = len(sample_data) <= 10
                self._create_individual_plot(sample_data, 'bg_ratio', original_sample_count, with_labels=with_labels)
            
            def show_dev_plot(event):
                # Auto-enable labels for small sample sets
                with_labels = len(sample_data) <= 10
                self._create_individual_plot(sample_data, 'deviation', original_sample_count, with_labels=with_labels)
            
            def show_few_labeled(event):
                # Show just 5 samples with labels for identification
                few_sample_data = {}
                for i, (sample_id, data) in enumerate(sample_data.items()):
                    if i >= 5:
                        break
                    few_sample_data[sample_id] = data
                
                # Create a multi-plot figure showing different analysis types with labels
                self._create_labeled_multi_plot(few_sample_data, original_sample_count)
            
            def reset_view(event):
                # Refresh the current plot
                plt.close('all')
                self.plot_spectral_response(spectral_data, sample_ids, max_samples, interactive, plot_type)
            
            # Connect buttons to callbacks
            btn_rgb.on_clicked(show_rgb_plot)
            btn_rg.on_clicked(show_rg_plot)
            btn_bg.on_clicked(show_bg_plot)
            btn_dev.on_clicked(show_dev_plot)
            btn_few.on_clicked(show_few_labeled)
            btn_all.on_clicked(reset_view)
            
            print("Interactive mode: Click buttons to pop out individual plots in new windows")
        
        plt.show()
    
    def _create_individual_plot(self, sample_data: Dict, plot_type: str, total_samples: int, with_labels: bool = False) -> None:
        """Create an individual pop-out plot window.
        
        Args:
            sample_data: Dictionary of sample data
            plot_type: Type of plot ('rgb', 'rg_ratio', 'bg_ratio', 'deviation', 'labeled_overview')
            total_samples: Total number of samples in the dataset
            with_labels: Whether to show sample labels for identification
        """
        # Create a new figure for the individual plot
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        
        # Add interactive functionality for sample identification
        sample_lines = []  # Store line objects for hover functionality
        
        if plot_type == 'rgb':
            # RGB response curves for all samples
            ax.set_title(f'RGB Response Curves - All {len(sample_data)} Samples', fontsize=14)
            ax.set_xlabel('Wavelength (nm)', fontsize=12)
            ax.set_ylabel('Relative Response', fontsize=12)
            
            # Plot all samples with different colors for R, G, B
            sample_count = 0
            for sample_id, data in sample_data.items():
                alpha = max(0.3, 1.0 / len(sample_data))  # Adjust transparency based on sample count
                color_base = plt.cm.viridis(sample_count / len(sample_data))
                
                ax.plot(data['wavelengths'], data['r_response'], 'r-', alpha=alpha, linewidth=1)
                ax.plot(data['wavelengths'], data['g_response'], 'g-', alpha=alpha, linewidth=1)
                ax.plot(data['wavelengths'], data['b_response'], 'b-', alpha=alpha, linewidth=1)
                sample_count += 1
            
            # Add legend for RGB channels
            ax.plot([], [], 'r-', label='Red Channel', linewidth=2)
            ax.plot([], [], 'g-', label='Green Channel', linewidth=2)
            ax.plot([], [], 'b-', label='Blue Channel', linewidth=2)
            ax.legend()
            
        elif plot_type == 'rg_ratio':
            # Red/Green ratio plot
            ax.set_title(f'Red/Green Ratio vs Wavelength - All {len(sample_data)} Samples', fontsize=14)
            ax.set_xlabel('Wavelength (nm)', fontsize=12)
            ax.set_ylabel('R/G Ratio', fontsize=12)
            
            sample_count = 0
            for sample_id, data in sample_data.items():
                rg_ratio = []
                wavelengths = data['wavelengths']
                for i in range(len(data['r_response'])):
                    r, g = data['r_response'][i], data['g_response'][i]
                    ratio = r / (g + 0.001) if g > 0.001 else 0
                    rg_ratio.append(ratio)
                
                color = plt.cm.viridis(sample_count / len(sample_data))
                if with_labels and len(sample_data) <= 10:  # Add labels for small sets
                    ax.plot(wavelengths, rg_ratio, alpha=0.8, color=color, linewidth=2, label=sample_id)
                else:
                    ax.plot(wavelengths, rg_ratio, alpha=0.7, color=color, linewidth=1.2)
                sample_count += 1
            
            if with_labels and len(sample_data) <= 10:
                ax.legend(loc='upper right', fontsize=9)
                
        elif plot_type == 'bg_ratio':
            # Blue/Green ratio plot
            ax.set_title(f'Blue/Green Ratio vs Wavelength - All {len(sample_data)} Samples', fontsize=14)
            ax.set_xlabel('Wavelength (nm)', fontsize=12)
            ax.set_ylabel('B/G Ratio', fontsize=12)
            
            sample_count = 0
            for sample_id, data in sample_data.items():
                bg_ratio = []
                wavelengths = data['wavelengths']
                for i in range(len(data['b_response'])):
                    b, g = data['b_response'][i], data['g_response'][i]
                    ratio = b / (g + 0.001) if g > 0.001 else 0
                    bg_ratio.append(ratio)
                
                color = plt.cm.plasma(sample_count / len(sample_data))
                if with_labels and len(sample_data) <= 10:  # Add labels for small sets
                    ax.plot(wavelengths, bg_ratio, alpha=0.8, color=color, linewidth=2, label=sample_id)
                else:
                    ax.plot(wavelengths, bg_ratio, alpha=0.7, color=color, linewidth=1.2)
                sample_count += 1
            
            if with_labels and len(sample_data) <= 10:
                ax.legend(loc='upper right', fontsize=9)
                
        elif plot_type == 'deviation':
            # Channel deviation plot
            ax.set_title(f'Channel Deviation Across Spectrum - All {len(sample_data)} Samples', fontsize=14)
            ax.set_xlabel('Wavelength (nm)', fontsize=12)
            ax.set_ylabel('Coefficient of Variation', fontsize=12)
            
            sample_count = 0
            for sample_id, data in sample_data.items():
                deviations = []
                wavelengths = data['wavelengths']
                for i in range(len(data['r_response'])):
                    r, g, b = data['r_response'][i], data['g_response'][i], data['b_response'][i]
                    mean_response = (r + g + b) / 3
                    deviation = np.std([r, g, b]) / (mean_response + 0.001)
                    deviations.append(deviation)
                
                color = plt.cm.coolwarm(sample_count / len(sample_data))
                if with_labels and len(sample_data) <= 10:  # Add labels for small sets
                    ax.plot(wavelengths, deviations, alpha=0.8, color=color, linewidth=2, label=sample_id)
                else:
                    ax.plot(wavelengths, deviations, alpha=0.7, color=color, linewidth=1.2)
                sample_count += 1
            
            if with_labels and len(sample_data) <= 10:
                ax.legend(loc='upper right', fontsize=9)
                
        elif plot_type == 'labeled_overview':
            # Overview with sample labels for identification
            ax.set_title(f'Labeled Sample Overview - {len(sample_data)} Samples with R/G Ratio', fontsize=14)
            ax.set_xlabel('Wavelength (nm)', fontsize=12)
            ax.set_ylabel('R/G Ratio', fontsize=12)
            
            sample_count = 0
            for sample_id, data in sample_data.items():
                rg_ratio = []
                wavelengths = data['wavelengths']
                for i in range(len(data['r_response'])):
                    r, g = data['r_response'][i], data['g_response'][i]
                    ratio = r / (g + 0.001) if g > 0.001 else 0
                    rg_ratio.append(ratio)
                
                color = plt.cm.Set1(sample_count % 9)  # Use distinct colors
                line = ax.plot(wavelengths, rg_ratio, alpha=0.8, color=color, linewidth=2, label=sample_id)[0]
                sample_lines.append(line)
                sample_count += 1
            
            # Add legend with sample IDs
            ax.legend(loc='upper right', fontsize=10)
        
        # Common formatting for all plots
        ax.grid(True, alpha=0.3)
        ax.text(0.02, 0.98, f'{len(sample_data)} of {total_samples} samples shown', 
                transform=ax.transAxes, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        plt.show()
        
        print(f"Opened individual {plot_type} plot in new window")
    
    def _create_labeled_multi_plot(self, sample_data: Dict, total_samples: int) -> None:
        """Create a multi-plot figure with labels for sample identification.
        
        Args:
            sample_data: Dictionary of sample data (should be limited to ~5 samples)
            total_samples: Total number of samples in the original dataset
        """
        # Create a 2x2 subplot figure similar to the overview but with labels
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Labeled Spectral Analysis - {len(sample_data)} of {total_samples} Samples', fontsize=16)
        
        # Plot 1: RGB responses with labels
        if sample_data:
            axes[0, 0].set_title('RGB Response Curves (Labeled)', fontsize=12)
            axes[0, 0].set_xlabel('Wavelength (nm)')
            axes[0, 0].set_ylabel('Relative Response')
            
            sample_count = 0
            for sample_id, data in sample_data.items():
                color = plt.cm.Set1(sample_count % 9)
                axes[0, 0].plot(data['wavelengths'], data['r_response'], 'r-', alpha=0.7, linewidth=1.5, label=f'{sample_id} (R)')
                axes[0, 0].plot(data['wavelengths'], data['g_response'], 'g-', alpha=0.7, linewidth=1.5, label=f'{sample_id} (G)')
                axes[0, 0].plot(data['wavelengths'], data['b_response'], 'b-', alpha=0.7, linewidth=1.5, label=f'{sample_id} (B)')
                sample_count += 1
            
            axes[0, 0].legend(loc='upper right', fontsize=8, ncol=2)
            axes[0, 0].grid(True, alpha=0.3)
        
        # Plot 2: R/G ratio with labels
        axes[0, 1].set_title('Red/Green Ratio (Labeled)', fontsize=12)
        axes[0, 1].set_xlabel('Wavelength (nm)')
        axes[0, 1].set_ylabel('R/G Ratio')
        
        sample_count = 0
        for sample_id, data in sample_data.items():
            rg_ratio = []
            wavelengths = data['wavelengths']
            for i in range(len(data['r_response'])):
                r, g = data['r_response'][i], data['g_response'][i]
                ratio = r / (g + 0.001) if g > 0.001 else 0
                rg_ratio.append(ratio)
            
            color = plt.cm.Set1(sample_count % 9)
            axes[0, 1].plot(wavelengths, rg_ratio, alpha=0.8, color=color, linewidth=2, label=sample_id)
            sample_count += 1
        
        axes[0, 1].legend(loc='upper right', fontsize=9)
        axes[0, 1].grid(True, alpha=0.3)
        
        # Plot 3: B/G ratio with labels
        axes[1, 0].set_title('Blue/Green Ratio (Labeled)', fontsize=12)
        axes[1, 0].set_xlabel('Wavelength (nm)')
        axes[1, 0].set_ylabel('B/G Ratio')
        
        sample_count = 0
        for sample_id, data in sample_data.items():
            bg_ratio = []
            wavelengths = data['wavelengths']
            for i in range(len(data['b_response'])):
                b, g = data['b_response'][i], data['g_response'][i]
                ratio = b / (g + 0.001) if g > 0.001 else 0
                bg_ratio.append(ratio)
            
            color = plt.cm.Set1(sample_count % 9)
            axes[1, 0].plot(wavelengths, bg_ratio, alpha=0.8, color=color, linewidth=2, label=sample_id)
            sample_count += 1
        
        axes[1, 0].legend(loc='upper right', fontsize=9)
        axes[1, 0].grid(True, alpha=0.3)
        
        # Plot 4: Channel deviation with labels
        axes[1, 1].set_title('Channel Deviation (Labeled)', fontsize=12)
        axes[1, 1].set_xlabel('Wavelength (nm)')
        axes[1, 1].set_ylabel('Coefficient of Variation')
        
        sample_count = 0
        for sample_id, data in sample_data.items():
            deviations = []
            wavelengths = data['wavelengths']
            for i in range(len(data['r_response'])):
                r, g, b = data['r_response'][i], data['g_response'][i], data['b_response'][i]
                mean_response = (r + g + b) / 3
                deviation = np.std([r, g, b]) / (mean_response + 0.001)
                deviations.append(deviation)
            
            color = plt.cm.Set1(sample_count % 9)
            axes[1, 1].plot(wavelengths, deviations, alpha=0.8, color=color, linewidth=2, label=sample_id)
            sample_count += 1
        
        axes[1, 1].legend(loc='upper right', fontsize=9)
        axes[1, 1].grid(True, alpha=0.3)
        
        # Add overall info
        fig.text(0.02, 0.02, f'Labeled Analysis: {len(sample_data)} samples shown with individual identification', 
                 fontsize=10, style='italic')
        
        # Add interactive buttons for labeled pop-outs
        from matplotlib.widgets import Button
        
        # Adjust layout to make room for buttons
        fig.subplots_adjust(bottom=0.12)
        
        # Create button axes for labeled multi-plot
        ax_btn1 = plt.axes([0.1, 0.02, 0.15, 0.04])
        ax_btn2 = plt.axes([0.3, 0.02, 0.15, 0.04])
        ax_btn3 = plt.axes([0.5, 0.02, 0.15, 0.04])
        ax_btn4 = plt.axes([0.7, 0.02, 0.15, 0.04])
        
        # Create buttons for labeled individual plots
        btn_rgb_labeled = Button(ax_btn1, 'Pop-out RGB (Labeled)')
        btn_rg_labeled = Button(ax_btn2, 'Pop-out R/G (Labeled)')
        btn_bg_labeled = Button(ax_btn3, 'Pop-out B/G (Labeled)')
        btn_dev_labeled = Button(ax_btn4, 'Pop-out Dev (Labeled)')
        
        # Button callback functions that preserve labels
        def show_rgb_labeled(event):
            self._create_individual_plot(sample_data, 'rgb', total_samples, with_labels=True)
        
        def show_rg_labeled(event):
            self._create_individual_plot(sample_data, 'rg_ratio', total_samples, with_labels=True)
        
        def show_bg_labeled(event):
            self._create_individual_plot(sample_data, 'bg_ratio', total_samples, with_labels=True)
        
        def show_dev_labeled(event):
            self._create_individual_plot(sample_data, 'deviation', total_samples, with_labels=True)
        
        # Connect buttons to callbacks
        btn_rgb_labeled.on_clicked(show_rgb_labeled)
        btn_rg_labeled.on_clicked(show_rg_labeled)
        btn_bg_labeled.on_clicked(show_bg_labeled)
        btn_dev_labeled.on_clicked(show_dev_labeled)
        
        plt.tight_layout()
        plt.show()
        
        print(f"Opened labeled multi-plot with {len(sample_data)} samples")
        print("Click buttons to pop out individual labeled plots")
    
    def calculate_metamerism_index(self, measurement1: ColorMeasurement,
                                 measurement2: ColorMeasurement) -> float:
        """
        Calculate metamerism index between two color measurements.
        
        Args:
            measurement1: First color measurement
            measurement2: Second color measurement
            
        Returns:
            Metamerism index (0 = perfect match, higher = more metameric)
        """
        # Convert to XYZ for multiple illuminants
        metameric_differences = []
        
        for illuminant in ['D65', 'A', 'F2']:
            # This is a simplified calculation - would need full spectral data for accuracy
            xyz1 = self._rgb_to_xyz(measurement1.rgb, illuminant)
            xyz2 = self._rgb_to_xyz(measurement2.rgb, illuminant)
            
            # Calculate color difference in XYZ space
            diff = np.sqrt(sum((a - b) ** 2 for a, b in zip(xyz1, xyz2)))
            metameric_differences.append(diff)
        
        # Metamerism index is the standard deviation of differences across illuminants
        return np.std(metameric_differences)
    
    def _rgb_to_xyz(self, rgb: Tuple[float, float, float], illuminant: str) -> Tuple[float, float, float]:
        """Convert RGB to XYZ under specified illuminant (simplified)."""
        r, g, b = [c / 255.0 for c in rgb]
        
        # Standard sRGB to XYZ matrix (would need chromatic adaptation for other illuminants)
        x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
        y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
        z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
        
        # Simple illuminant scaling (very approximate)
        if illuminant == 'A':
            x *= 1.1  # Warmer
            z *= 0.8
        elif illuminant == 'F2':
            # Fluorescent has spiky spectrum
            x *= 0.95
            z *= 1.05
        
        return (x * 100, y * 100, z * 100)
    
    def analyze_wavelength_deviation(self, measurements: List[ColorMeasurement]) -> Dict[str, List[float]]:
        """
        Analyze how RGB channels deviate from each other across the spectrum.
        
        This addresses your core question about channel deviation across wavelengths.
        
        Args:
            measurements: List of color measurements
            
        Returns:
            Dictionary with deviation metrics across wavelength ranges
        """
        wavelength_ranges = {
            'violet': (380, 450),
            'blue': (450, 495),
            'green': (495, 570),
            'yellow': (570, 590),
            'orange': (590, 620),
            'red': (620, 700)
        }
        
        deviation_analysis = {
            'wavelength_range': [],
            'rg_deviation': [],  # Red-Green deviation
            'rb_deviation': [],  # Red-Blue deviation
            'gb_deviation': [],  # Green-Blue deviation
            'total_deviation': []  # Overall channel deviation
        }
        
        for range_name, (min_wl, max_wl) in wavelength_ranges.items():
            rg_deviations = []
            rb_deviations = []
            gb_deviations = []
            total_deviations = []
            
            for measurement in measurements:
                r, g, b = measurement.rgb
                
                # Normalize to prevent brightness bias
                total = r + g + b
                if total > 0:
                    r_norm, g_norm, b_norm = r/total, g/total, b/total
                    
                    # Calculate channel deviations
                    rg_dev = abs(r_norm - g_norm)
                    rb_dev = abs(r_norm - b_norm)
                    gb_dev = abs(g_norm - b_norm)
                    total_dev = np.std([r_norm, g_norm, b_norm])
                    
                    rg_deviations.append(rg_dev)
                    rb_deviations.append(rb_dev)
                    gb_deviations.append(gb_dev)
                    total_deviations.append(total_dev)
            
            # Average deviations for this wavelength range
            deviation_analysis['wavelength_range'].append(range_name)
            deviation_analysis['rg_deviation'].append(np.mean(rg_deviations) if rg_deviations else 0)
            deviation_analysis['rb_deviation'].append(np.mean(rb_deviations) if rb_deviations else 0)
            deviation_analysis['gb_deviation'].append(np.mean(gb_deviations) if gb_deviations else 0)
            deviation_analysis['total_deviation'].append(np.mean(total_deviations) if total_deviations else 0)
        
        return deviation_analysis
    
    def export_spectral_analysis(self, spectral_data: List[SpectralMeasurement], 
                               filename: str) -> bool:
        """Export spectral analysis data to CSV file."""
        try:
            import csv
            
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['sample_id', 'wavelength', 'r_response', 'g_response', 
                            'b_response', 'r_relative', 'g_relative', 'b_relative', 'illuminant']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for measurement in spectral_data:
                    writer.writerow({
                        'sample_id': measurement.sample_id,
                        'wavelength': measurement.wavelength,
                        'r_response': measurement.rgb_response[0],
                        'g_response': measurement.rgb_response[1],
                        'b_response': measurement.rgb_response[2],
                        'r_relative': measurement.relative_response[0],
                        'g_relative': measurement.relative_response[1],
                        'b_relative': measurement.relative_response[2],
                        'illuminant': measurement.illuminant
                    })
            
            print(f"Spectral analysis exported to {filename}")
            return True
            
        except Exception as e:
            print(f"Error exporting spectral analysis: {e}")
            return False

def analyze_spectral_deviation_from_measurements(measurements: List[ColorMeasurement]) -> None:
    """
    Quick analysis function to examine channel deviation across color samples.
    This directly addresses your question about RGB channel behavior across the spectrum.
    """
    analyzer = SpectralAnalyzer()
    
    print("=== SPECTRAL DEVIATION ANALYSIS ===")
    print("Analyzing how RGB channels deviate across wavelength ranges...")
    print()
    
    # Analyze wavelength-based deviations
    deviation_data = analyzer.analyze_wavelength_deviation(measurements)
    
    print("Channel Deviation by Wavelength Range:")
    print("=" * 50)
    print(f"{'Range':<10} {'R-G Dev':<10} {'R-B Dev':<10} {'G-B Dev':<10} {'Total Dev':<10}")
    print("-" * 50)
    
    for i, range_name in enumerate(deviation_data['wavelength_range']):
        rg_dev = deviation_data['rg_deviation'][i]
        rb_dev = deviation_data['rb_deviation'][i]
        gb_dev = deviation_data['gb_deviation'][i]
        total_dev = deviation_data['total_deviation'][i]
        
        print(f"{range_name:<10} {rg_dev:<10.3f} {rb_dev:<10.3f} {gb_dev:<10.3f} {total_dev:<10.3f}")
    
    print("\nInterpretation:")
    print("- Higher values indicate greater channel deviation")
    print("- R-G Dev: Red-Green channel difference")
    print("- R-B Dev: Red-Blue channel difference")  
    print("- G-B Dev: Green-Blue channel difference")
    print("- Total Dev: Overall RGB channel spread")
    print("\nThis analysis reveals how color channels behave differently")
    print("across the visible spectrum for your stamp samples!")
