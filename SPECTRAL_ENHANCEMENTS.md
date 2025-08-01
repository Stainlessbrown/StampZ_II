# StampZ Spectral Analysis Enhancements

## Overview

The StampZ spectral analysis system has been enhanced with two major improvements:

1. **Plot Saving Functionality** - Save spectral response plots as image files
2. **Detailed CSV Export** - Export numeric spectral data for further analysis

## Enhanced Features

### 1. Plot Saving Functionality

**What it does:**
- Saves spectral response plots as high-quality image files
- Supports multiple formats: PNG, SVG, PDF
- Maintains full plot quality and resolution (300 DPI)

**Where available:**
- **GUI**: Color Analysis → Spectral Analysis... → "Plot Curves" button
- **Command line**: Automatic saving when using `ods_to_spectral_converter.py -o output_dir`
- **API**: Set `spectral_analyzer._save_plot_path` before calling `plot_spectral_response()`

**Example usage in GUI:**
1. Run spectral analysis on your color measurements
2. Click "Plot Curves" 
3. Choose "Yes" when asked to save the plot
4. Select file format and location
5. Plot displays AND saves automatically

### 2. Detailed CSV Export

**What it exports:**
- `sample_id`: Identifier for each color sample
- `wavelength`: Wavelength in nanometers (380-700nm in 5nm steps)
- `r_response`, `g_response`, `b_response`: Raw RGB response values
- `r_relative`, `g_relative`, `b_relative`: Illuminant-normalized responses
- `illuminant`: Lighting condition (D65, A, F2, LED)

**Data structure:**
```csv
sample_id,wavelength,r_response,g_response,b_response,r_relative,g_relative,b_relative,illuminant
sample_1,380,0.0,6.397e-05,0.027619,0.0,0.000213,0.092064,D65
sample_1,385,0.0,0.000102,0.036180,0.0,0.000214,0.076169,D65
...
```

**Where available:**
- **GUI**: Color Analysis → Spectral Analysis... → "Export CSV Data" button
- **Command line**: Automatic export when using `ods_to_spectral_converter.py -o output_dir`
- **API**: Call `spectral_analyzer.export_spectral_analysis(spectral_data, filepath)`

## Updated GUI Integration

The Spectral Analysis dialog now includes:

- **Run Analysis**: Performs the spectral analysis (unchanged)
- **Export Results**: Saves descriptive text summary (unchanged)
- **Export CSV Data**: 🆕 NEW - Exports detailed numeric data
- **Plot Curves**: Enhanced with optional plot saving
- **Close**: Close dialog (unchanged)

## Command Line Integration

The `ods_to_spectral_converter.py` script now automatically:
- Exports detailed CSV data for each illuminant
- Saves high-quality spectral response plots
- Both saved to the specified output directory

Example:
```bash
python3 utils/ods_to_spectral_converter.py data/my_stamps.ods -o results/
```

Creates:
- `results/my_stamps_spectral_D65_20250801.csv`
- `results/my_stamps_spectral_A_20250801.csv` 
- `results/my_stamps_spectral_F2_20250801.csv`
- `results/my_stamps_spectral_plot_20250801.png`

## Benefits for Philatelic Research

### Enhanced Plot Saving
- **Publication ready**: High-resolution plots suitable for papers and presentations
- **Documentation**: Permanent visual record of spectral characteristics
- **Comparison**: Save plots from different stamp series for side-by-side analysis

### Detailed CSV Export
- **Further analysis**: Import data into Excel, R, MATLAB, or other analysis tools
- **Statistical studies**: Perform advanced statistical analysis on spectral data
- **Machine learning**: Use spectral data for automated stamp classification
- **Validation**: Verify and reproduce analysis results independently

## Practical Applications

1. **Pigment Analysis**: Export CSV data to identify specific pigments used in different printing periods
2. **Forgery Detection**: Compare spectral signatures between authentic and suspected forged stamps
3. **Printing Method Study**: Analyze spectral differences between line-engraved vs. lithographic stamps
4. **Paper Aging Research**: Track how paper aging affects spectral response over time
5. **Color Matching**: Use precise spectral data for accurate color reproduction in catalog photography

## Technical Implementation

The enhancements maintain full backward compatibility while adding new functionality:

- **Plot saving**: Uses matplotlib's `savefig()` with configurable DPI and format
- **CSV export**: Structured data format compatible with standard analysis tools
- **Memory efficient**: Processes large datasets without memory issues
- **Error handling**: Robust error handling for file I/O operations

## File Outputs

### Spectral Response Plots
- **Format**: PNG (default), SVG, PDF supported
- **Resolution**: 300 DPI for publication quality
- **Content**: 4-panel plot showing RGB responses, ratios, and deviations
- **Naming**: `{dataset}_spectral_plot_{date}.png`

### CSV Data Files
- **Format**: Standard CSV with headers
- **Size**: ~650 rows per sample (65 wavelengths × 10 samples typical)
- **Precision**: Full floating-point precision maintained
- **Naming**: `{dataset}_spectral_{illuminant}_{date}.csv`

## Integration Status

✅ **GUI Integration**: Complete - Available in Color Analysis menu
✅ **Command Line**: Complete - Enhanced ods_to_spectral_converter.py
✅ **API Integration**: Complete - Enhanced spectral_analyzer.py
✅ **Documentation**: Complete - This file and inline documentation
✅ **Testing**: Complete - Verified with test script

These enhancements provide StampZ users with professional-grade spectral analysis capabilities suitable for both casual exploration and rigorous scientific research.
