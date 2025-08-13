# Normalized Export Feature

## Overview

StampZ now supports exporting color analysis data with values normalized to a 0.0-1.0 range with 4 decimal places. This feature makes the data much more manageable for plotting, analysis, and integration with other color analysis tools.

## What's Normalized

When normalized export is enabled, the following transformations are applied:

### RGB Values (0-255 → 0.0000-1.0000)
- **Formula**: `normalized_value = original_value / 255.0`
- **Example**: RGB(255, 128, 0) → (1.0000, 0.5020, 0.0000)

### L* Values (0-100 → 0.0000-1.0000)
- **Formula**: `normalized_value = original_value / 100.0`
- **Example**: L* = 50.0 → 0.5000

### a*/b* Values (-128 to +127 → 0.0000-1.0000)
- **Formula**: `normalized_value = (original_value + 128.0) / 255.0`
- **Example**: a* = -10, b* = 20 → (0.4627, 0.5784)

## Column Headers

When normalized export is enabled, column headers are updated to indicate the normalized format:
- `L*` → `L*_norm`
- `a*` → `a*_norm`
- `b*` → `b*_norm`
- `R` → `R_norm`
- `G` → `G_norm`
- `B` → `B_norm`

## How to Enable/Disable

### Method 1: Programmatically (Python)

```python
from utils.user_preferences import get_preferences_manager

# Get preferences manager
prefs_manager = get_preferences_manager()

# Enable normalized exports
prefs_manager.set_export_normalized_values(True)

# Check current setting
is_normalized = prefs_manager.get_export_normalized_values()
print(f"Normalized export: {is_normalized}")

# Disable normalized exports
prefs_manager.set_export_normalized_values(False)
```

### Method 2: Via Export Functions

Once the preference is set, all export functions (ODS, Excel, CSV) will automatically use the normalized format:

```python
from utils.ods_exporter import ODSExporter

# Create exporter
exporter = ODSExporter()

# Export using current preference setting
output_file = exporter.export_to_sample_set_file("my_data", "csv")
```

## Supported Export Formats

The normalized export feature works with all supported formats:
- **ODS** (.ods) - LibreOffice Calc format
- **Excel** (.xlsx) - Microsoft Excel format
- **CSV** (.csv) - Comma-separated values

## Benefits

### For Data Analysis
- **Consistent Range**: All color components use the same 0.0-1.0 scale
- **Easier Plotting**: No need to handle different scales for different components
- **Statistical Analysis**: Simplified calculations without range conversions

### For Visualization
- **Plotting Libraries**: Direct compatibility with matplotlib, seaborn, etc.
- **Color Mapping**: Easy to map values to visual elements
- **Machine Learning**: Ready for ML algorithms that expect normalized inputs

### Example Comparison

**Standard Export:**
```csv
L*,a*,b*,R,G,B
50.25,-10.5,20.3,255,128,64
```

**Normalized Export:**
```csv
L*_norm,a*_norm,b*_norm,R_norm,G_norm,B_norm
0.5025,0.4627,0.5784,1.0000,0.5020,0.2510
```

## Precision

All normalized values are formatted to 4 decimal places, providing sufficient precision for most color analysis applications while keeping file sizes manageable.

## Backward Compatibility

- The standard export format remains the default
- Existing workflows are unaffected unless explicitly enabled
- The preference setting is persistent across sessions
- Both formats can be used simultaneously by changing the preference

## Testing

Run the test script to verify the functionality:

```bash
cd /path/to/StampZ
python3 test_normalized_export.py
```

This will create sample exports in both standard and normalized formats for comparison.

## Integration with Existing Tools

The normalized format is particularly useful for:
- **Python data analysis** (pandas, numpy)
- **R statistical analysis**
- **MATLAB/Octave** processing
- **Color science applications**
- **Machine learning pipelines**

## Notes

- Position coordinates (X, Y) are not normalized as they represent pixel positions
- Date and text fields remain unchanged
- The DataID and other metadata columns are not affected
- Empty calculation columns are still included for user convenience
