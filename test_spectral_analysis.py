import numpy as np
from datetime import datetime
from utils.spectral_analyzer import SpectralAnalyzer
from utils.color_analyzer import ColorMeasurement

# Generate synthetic measurements for testing
measurements = []
for i in range(50):
    rgb = (np.random.randint(50, 206), np.random.randint(50, 206), np.random.randint(50, 206))
    # Create a basic L*a*b* approximation from RGB
    lab = (50 + np.random.rand() * 50, np.random.rand() * 100 - 50, np.random.rand() * 100 - 50)
    
    measurement = ColorMeasurement(
        coordinate_id=i,
        coordinate_point=i + 1,
        position=(np.random.rand() * 1000, np.random.rand() * 1000),
        rgb=rgb,
        lab=lab,
        sample_area={'type': 'rectangle', 'size': (20, 20), 'anchor': 'center'},
        measurement_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        notes=f"Test sample {i+1}"
    )
    measurements.append(measurement)

print(f"Generated {len(measurements)} synthetic color measurements")

# Initialize the spectral analyzer
analyzer = SpectralAnalyzer()

# Analyze spectral responses
print("Analyzing spectral responses...")
spectral_data = analyzer.analyze_spectral_response(measurements)

print(f"Generated {len(spectral_data)} spectral data points")
print("Opening interactive plot...")

# Plot results in interactive mode
analyzer.plot_spectral_response(spectral_data, interactive=True, max_samples=50)
