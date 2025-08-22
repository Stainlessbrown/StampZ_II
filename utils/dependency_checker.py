#!/usr/bin/env python3
"""
Dependency checker for StampZ optional dependencies.
Checks for optional libraries and provides installation guidance.
"""

import importlib
import sys
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class DependencyInfo:
    """Information about an optional dependency."""
    name: str
    import_name: str
    pip_install_name: str
    description: str
    features_enabled: List[str]
    installation_command: str
    is_available: bool = False
    version: Optional[str] = None

class DependencyChecker:
    """Check for optional dependencies and provide user guidance."""
    
    def __init__(self):
        self.dependencies = [
            DependencyInfo(
                name="TiffFile",
                import_name="tifffile",
                pip_install_name="tifffile",
                description="16-bit TIFF support for maximum color precision",
                features_enabled=[
                    "Load 16-bit TIFF files with full precision",
                    "Prevent automatic 8-bit downsampling",
                    "Preserve maximum color information for analysis"
                ],
                installation_command="pip install tifffile"
            ),
            DependencyInfo(
                name="Colorspacious",
                import_name="colorspacious", 
                pip_install_name="colorspacious",
                description="Precise CIE L*a*b* color space conversions",
                features_enabled=[
                    "Accurate RGB to L*a*b* conversions",
                    "Professional color science calculations", 
                    "Better color difference measurements (ΔE)"
                ],
                installation_command="pip install colorspacious"
            ),
            DependencyInfo(
                name="Matplotlib",
                import_name="matplotlib",
                pip_install_name="matplotlib", 
                description="Spectral analysis plotting and visualization",
                features_enabled=[
                    "Generate spectral response plots",
                    "Visualize color analysis data",
                    "Export analysis charts as images"
                ],
                installation_command="pip install matplotlib"
            ),
            DependencyInfo(
                name="OdfPy",
                import_name="odf",
                pip_install_name="odfpy",
                description="OpenDocument Spreadsheet export support",
                features_enabled=[
                    "Export analysis data to ODS format",
                    "Compatible with LibreOffice Calc",
                    "Professional data sharing"
                ],
                installation_command="pip install odfpy==1.4.1"
            )
        ]
        
        self._check_all_dependencies()
    
    def _check_all_dependencies(self):
        """Check availability of all optional dependencies."""
        for dep in self.dependencies:
            try:
                # Use safer import that won't break in CI/CD environments
                module = importlib.import_module(dep.import_name)
                dep.is_available = True
                
                # Try to get version if available
                try:
                    if hasattr(module, '__version__'):
                        dep.version = module.__version__
                    elif hasattr(module, 'version'):
                        dep.version = module.version
                    elif hasattr(module, 'VERSION'):
                        dep.version = str(module.VERSION)
                except (AttributeError, TypeError):
                    dep.version = "unknown"
                    
            except (ImportError, ModuleNotFoundError, OSError) as e:
                # More comprehensive error handling for CI/CD environments
                dep.is_available = False
                dep.version = None
            except Exception as e:
                # Catch any other unexpected errors during import
                dep.is_available = False
                dep.version = None
    
    def get_missing_dependencies(self) -> List[DependencyInfo]:
        """Get list of missing optional dependencies."""
        return [dep for dep in self.dependencies if not dep.is_available]
    
    def get_available_dependencies(self) -> List[DependencyInfo]:
        """Get list of available optional dependencies."""
        return [dep for dep in self.dependencies if dep.is_available]
    
    def get_dependency_status_summary(self) -> Dict[str, any]:
        """Get summary of dependency status."""
        available = self.get_available_dependencies()
        missing = self.get_missing_dependencies()
        
        return {
            'total_dependencies': len(self.dependencies),
            'available_count': len(available),
            'missing_count': len(missing),
            'available': available,
            'missing': missing,
            'completion_percentage': int((len(available) / len(self.dependencies)) * 100)
        }
    
    def should_show_dependency_dialog(self) -> bool:
        """Determine if dependency dialog should be shown to user."""
        missing = self.get_missing_dependencies()
        # Show dialog if any important dependencies are missing
        important_deps = ['tifffile', 'colorspacious']
        missing_important = [dep for dep in missing if dep.import_name in important_deps]
        return len(missing_important) > 0
    
    def get_installation_script(self, missing_only: bool = True) -> str:
        """Generate installation script for dependencies."""
        deps_to_install = self.get_missing_dependencies() if missing_only else self.dependencies
        
        if not deps_to_install:
            return "# All optional dependencies are already installed!"
        
        script_lines = [
            "#!/bin/bash",
            "# StampZ Optional Dependencies Installation Script",
            "# Run this script to install missing optional dependencies",
            "",
            "echo 'Installing StampZ optional dependencies...'",
            ""
        ]
        
        for dep in deps_to_install:
            script_lines.extend([
                f"echo 'Installing {dep.name}...'",
                dep.installation_command,
                f"echo '{dep.name} installation complete.'",
                ""
            ])
        
        script_lines.extend([
            "echo 'All optional dependencies installed!'",
            "echo 'Please restart StampZ to use the new features.'"
        ])
        
        return "\n".join(script_lines)
    
    def format_dependency_report(self) -> str:
        """Format a human-readable dependency report."""
        status = self.get_dependency_status_summary()
        
        report_lines = [
            "StampZ Dependency Status Report",
            "=" * 40,
            f"Optional Dependencies: {status['available_count']}/{status['total_dependencies']} available ({status['completion_percentage']}%)",
            ""
        ]
        
        if status['available']:
            report_lines.extend([
                "✅ AVAILABLE DEPENDENCIES:",
                "-" * 30
            ])
            for dep in status['available']:
                version_str = f" (v{dep.version})" if dep.version else ""
                report_lines.append(f"✓ {dep.name}{version_str}")
                report_lines.append(f"  {dep.description}")
                report_lines.append("")
        
        if status['missing']:
            report_lines.extend([
                "❌ MISSING DEPENDENCIES:",
                "-" * 30
            ])
            for dep in status['missing']:
                report_lines.append(f"✗ {dep.name}")
                report_lines.append(f"  {dep.description}")
                report_lines.append(f"  Install: {dep.installation_command}")
                report_lines.append(f"  Features: {', '.join(dep.features_enabled)}")
                report_lines.append("")
        
        if status['missing']:
            report_lines.extend([
                "QUICK INSTALLATION:",
                "-" * 20,
                "Install all missing dependencies with:",
                ""
            ])
            for dep in status['missing']:
                report_lines.append(dep.installation_command)
        
        return "\n".join(report_lines)

def check_dependencies() -> DependencyChecker:
    """Convenience function to check dependencies."""
    return DependencyChecker()

def main():
    """CLI interface for dependency checking."""
    checker = DependencyChecker()
    print(checker.format_dependency_report())
    
    # Generate installation script
    missing = checker.get_missing_dependencies()
    if missing:
        script_path = "install_optional_deps.sh"
        with open(script_path, 'w') as f:
            f.write(checker.get_installation_script())
        print(f"\nInstallation script saved to: {script_path}")
        print("Make it executable with: chmod +x install_optional_deps.sh")

if __name__ == "__main__":
    main()
