# Color Calibration Feature - Release Notes

## Overview
Added experimental color calibration system to improve measurement accuracy for display/screenshot color shifts.

## ✅ What's Safe and Working

### Core Improvements
- **Fixed preferences system** - Now preserves calibration data without overwriting
- **Optional calibration support** - Disabled by default, no impact on existing users
- **Manual correction tools** - For users who want to apply corrections manually

### New Files Added
- `utils/color_calibration.py` - Color calibration utilities and analysis
- `gui/calibration_wizard.py` - GUI wizard for calibration (experimental)
- `color_correction_calculator.py` - Manual correction calculator
- `COLOR_CALIBRATION_SOLUTION.md` - Complete technical documentation

### Modified Files
- `main.py` - Added "Calibrate Color Accuracy..." menu item (optional feature)
- `utils/color_analyzer.py` - Added calibration support (only active if user enables it)
- `utils/user_preferences.py` - Fixed to preserve all preference data

## ⚠️ Known Issues and Limitations

### Calibration Wizard Issues
- **Bug**: Wizard may analyze generated target instead of user screenshot
- **Result**: May create ineffective calibration (no corrections applied)
- **Workaround**: Users can create manual calibrations or wait for fixes

### Important User Guidance
- **System-specific**: Each user needs their own calibration
- **Optional feature**: Calibration is completely optional - StampZ works fine without it
- **Risk of over-correction**: Poorly done calibration can make measurements worse
- **Manual alternative**: Users can apply corrections manually using the calculator

## 🎯 For Users

### Who Should Use This
- Users experiencing consistent color shifts in measurements
- Users who frequently analyze screenshots
- Advanced users comfortable with calibration concepts

### Who Should Wait
- Users satisfied with current measurement accuracy
- Users new to color analysis
- Users wanting a "just works" experience

### How to Use (When It Works)
1. Go to **Color Analysis** menu → **"Calibrate Color Accuracy..."**
2. Follow wizard steps (generate target, screenshot, analyze)
3. Apply calibration if improvements are shown
4. Test with known color samples

### Manual Alternative
If the wizard doesn't work well:
1. Generate reference colors manually
2. Screenshot them on your system
3. Measure colors in StampZ
4. Use `color_correction_calculator.py` for manual corrections

## 🔧 For Developers

### Safe to Use
- Calibration system is opt-in only
- No changes to core measurement algorithms
- Backwards compatible - existing measurements unchanged
- Preferences system improvement benefits all users

### Future Improvements Needed
- Fix wizard to properly analyze user screenshots
- Add validation to ensure calibration quality
- Improve user guidance and error handling
- Add calibration strength adjustment options

## Impact Assessment

### ✅ Zero Risk
- **Existing users**: No change in behavior unless they specifically use calibration
- **Default state**: Calibration disabled, no corrections applied
- **Core functionality**: Unchanged and unaffected

### 📈 Benefits
- **Optional improvement** for users with color accuracy issues
- **Foundation** for future calibration enhancements
- **Manual tools** for advanced users
- **Better preferences management** for all users

## Version Notes
- **Status**: Experimental feature
- **Stability**: Core improvements stable, wizard has known issues
- **Recommendation**: Safe to include, document limitations clearly
