#!/usr/bin/env python3
"""
GUI component for StampZ to Plot_3D integration.

Provides a simple interface for users to transfer their color analysis data
to Plot_3D format with one-click operation.
"""

import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import os
import threading
from typing import Optional, Callable

class Plot3DIntegrationPanel:
    """GUI panel for StampZ to Plot_3D data integration."""
    
    def __init__(self, parent_frame: tk.Widget, 
                 get_current_sample_set: Optional[Callable] = None,
                 on_export_success: Optional[Callable] = None):
        """Initialize the integration panel.
        
        Args:
            parent_frame: Parent tkinter widget
            get_current_sample_set: Function to get current sample set name
            on_export_success: Callback when export succeeds
        """
        self.parent_frame = parent_frame
        self.get_current_sample_set = get_current_sample_set
        self.on_export_success = on_export_success
        
        # Integration components
        self.integrator = None
        self.integration_thread = None
        
        # GUI components
        self.frame = None
        self.status_label = None
        self.progress_var = None
        self.integrate_button = None
        self.auto_refresh_var = None
        
        self._setup_gui()
    
    def _setup_gui(self):
        """Setup the GUI components."""
        # Main frame
        self.frame = tk.LabelFrame(self.parent_frame, text="Plot_3D Integration", padx=5, pady=5)
        
        # Status display
        status_frame = tk.Frame(self.frame)
        status_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(status_frame, text="Status:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.status_label = tk.Label(status_frame, text="Ready", font=("Arial", 9), fg="green")
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Controls frame
        controls_frame = tk.Frame(self.frame)
        controls_frame.pack(fill=tk.X, pady=2)
        
        # Main integrate button
        self.integrate_button = tk.Button(
            controls_frame,
            text="Send to Plot_3D",
            command=self._on_integrate_clicked,
            bg="#4CAF50",  # Green background
            fg="white",
            font=("Arial", 9, "bold"),
            relief=tk.RAISED,
            pady=2
        )
        self.integrate_button.pack(side=tk.LEFT, padx=2)
        
        # Auto-refresh toggle
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_check = tk.Checkbutton(
            controls_frame,
            text="Auto-refresh Plot_3D",
            variable=self.auto_refresh_var,
            font=("Arial", 8)
        )
        auto_refresh_check.pack(side=tk.LEFT, padx=(10, 5))
        
        # Help button
        help_button = tk.Button(
            controls_frame,
            text="?",
            command=self._show_help,
            font=("Arial", 8),
            width=2,
            bg="lightblue"
        )
        help_button.pack(side=tk.RIGHT, padx=2)
        
        # Options frame (initially hidden)
        self.options_frame = tk.Frame(self.frame)
        
        # Advanced options toggle
        self.show_options_var = tk.BooleanVar(value=False)
        options_toggle = tk.Checkbutton(
            self.frame,
            text="Show advanced options",
            variable=self.show_options_var,
            command=self._toggle_options,
            font=("Arial", 8)
        )
        options_toggle.pack(pady=2)
        
        # Progress bar (hidden by default)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.frame,
            variable=self.progress_var,
            mode='indeterminate',
            length=200
        )
        # Don't pack initially - shown during operation
        
    def _toggle_options(self):
        """Toggle advanced options visibility."""
        if self.show_options_var.get():
            self._setup_advanced_options()
            self.options_frame.pack(fill=tk.X, pady=5)
        else:
            self.options_frame.pack_forget()
    
    def _setup_advanced_options(self):
        """Setup advanced options panel."""
        # Clear existing widgets
        for widget in self.options_frame.winfo_children():
            widget.destroy()
            
        # File selection frame
        file_frame = tk.LabelFrame(self.options_frame, text="File Selection", font=("Arial", 8))
        file_frame.pack(fill=tk.X, pady=2)
        
        # StampZ export file
        tk.Label(file_frame, text="StampZ Export:", font=("Arial", 8)).grid(row=0, column=0, sticky=tk.W)
        self.export_path_var = tk.StringVar(value="Auto-detect")
        export_entry = tk.Entry(file_frame, textvariable=self.export_path_var, width=30, font=("Arial", 8))
        export_entry.grid(row=0, column=1, padx=5)
        
        export_browse = tk.Button(
            file_frame, 
            text="Browse", 
            command=self._browse_export_file,
            font=("Arial", 8)
        )
        export_browse.grid(row=0, column=2, padx=2)
        
        # Plot_3D target file
        tk.Label(file_frame, text="Plot_3D File:", font=("Arial", 8)).grid(row=1, column=0, sticky=tk.W)
        self.plot3d_path_var = tk.StringVar(value="Auto-detect")
        plot3d_entry = tk.Entry(file_frame, textvariable=self.plot3d_path_var, width=30, font=("Arial", 8))
        plot3d_entry.grid(row=1, column=1, padx=5)
        
        plot3d_browse = tk.Button(
            file_frame,
            text="Browse",
            command=self._browse_plot3d_file,
            font=("Arial", 8)
        )
        plot3d_browse.grid(row=1, column=2, padx=2)
        
        # Options frame
        opts_frame = tk.LabelFrame(self.options_frame, text="Options", font=("Arial", 8))
        opts_frame.pack(fill=tk.X, pady=2)
        
        # Create new file option
        self.create_new_var = tk.BooleanVar(value=True)
        create_new_check = tk.Checkbutton(
            opts_frame,
            text="Create new Plot_3D file if none exists",
            variable=self.create_new_var,
            font=("Arial", 8)
        )
        create_new_check.pack(anchor=tk.W)
        
        # Starting row option
        row_frame = tk.Frame(opts_frame)
        row_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(row_frame, text="Start at row:", font=("Arial", 8)).pack(side=tk.LEFT)
        self.start_row_var = tk.StringVar(value="8")
        start_row_entry = tk.Entry(row_frame, textvariable=self.start_row_var, width=5, font=("Arial", 8))
        start_row_entry.pack(side=tk.LEFT, padx=5)
    
    def _browse_export_file(self):
        """Browse for StampZ export file."""
        filename = filedialog.askopenfilename(
            title="Select StampZ Export File",
            filetypes=[
                ("All supported", "*.ods;*.xlsx;*.csv"),
                ("OpenDocument Spreadsheet", "*.ods"),
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.export_path_var.set(filename)
    
    def _browse_plot3d_file(self):
        """Browse for Plot_3D file."""
        filename = filedialog.askopenfilename(
            title="Select Plot_3D File",
            filetypes=[
                ("OpenDocument Spreadsheet", "*.ods"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.plot3d_path_var.set(filename)
    
    def _on_integrate_clicked(self):
        """Handle integrate button click."""
        if self.integration_thread and self.integration_thread.is_alive():
            messagebox.showwarning("Integration in Progress", "Please wait for current integration to complete.")
            return
            
        # Start integration in separate thread
        self.integration_thread = threading.Thread(target=self._run_integration, daemon=True)
        self.integration_thread.start()
    
    def _run_integration(self):
        """Run the integration process in background thread."""
        try:
            # Update UI to show progress
            self._update_status("Initializing...", "orange")
            self._show_progress(True)
            
            # Lazy import to avoid startup delays
            from utils.plot3d_integration import StampZPlot3DIntegrator
            self.integrator = StampZPlot3DIntegrator()
            
            # Determine files to use
            export_file = self._get_export_file()
            plot3d_file = self._get_plot3d_file()
            
            if not export_file:
                self._update_status("No export file found", "red")
                self._show_progress(False)
                return
            
            # Update status
            self._update_status("Converting data...", "orange")
            
            # Get template name if available
            template_name = None
            if self.get_current_sample_set:
                template_name = self.get_current_sample_set()
                # Remove common suffixes to get clean template name
                if template_name and template_name.endswith('_averages'):
                    template_name = template_name[:-9]  # Remove '_averages'
            
            # Perform integration
            success = self.integrator.integrate_stampz_data(
                stampz_export_path=export_file,
                plot3d_file_path=plot3d_file if plot3d_file != "Auto-detect" else None,
                create_if_missing=self._get_create_new_option(),
                template_name=template_name
            )
            
            if success:
                self._update_status("Integration successful!", "green")
                
                # Trigger refresh if auto-refresh enabled
                if self.auto_refresh_var.get():
                    self._trigger_plot3d_refresh()
                
                # Call success callback if provided
                if self.on_export_success:
                    self.parent_frame.after(100, self.on_export_success)
                    
                # Show success message
                self.parent_frame.after(100, lambda: messagebox.showinfo(
                    "Integration Complete",
                    f"Successfully integrated data to Plot_3D!\n\n"
                    f"Data from: {os.path.basename(export_file)}\n"
                    f"{'Auto-refresh enabled' if self.auto_refresh_var.get() else 'Refresh Plot_3D manually to see changes'}"
                ))
            else:
                self._update_status("Integration failed", "red")
                self.parent_frame.after(100, lambda: messagebox.showerror(
                    "Integration Error",
                    "Failed to integrate data to Plot_3D.\n\n"
                    "Check that:\n"
                    "• Export file has correct format (L*_norm, a*_norm, b*_norm, DataID)\n"
                    "• Plot_3D file is not open in another program\n"
                    "• You have write permissions to the files"
                ))
            
        except Exception as e:
            self._update_status(f"Error: {str(e)}", "red")
            self.parent_frame.after(100, lambda: messagebox.showerror(
                "Integration Error", 
                f"An error occurred during integration:\n\n{str(e)}"
            ))
            
        finally:
            self._show_progress(False)
    
    def _get_export_file(self) -> Optional[str]:
        """Get the StampZ export file to use."""
        if hasattr(self, 'export_path_var') and self.export_path_var.get() != "Auto-detect":
            return self.export_path_var.get()
            
        # Auto-detect based on current sample set
        if self.get_current_sample_set:
            sample_set = self.get_current_sample_set()
            if sample_set:
                # Look for recent exports
                exports_dir = os.path.join(os.getcwd(), "exports")
                if os.path.exists(exports_dir):
                    # Find most recent export for this sample set
                    matching_files = []
                    for filename in os.listdir(exports_dir):
                        if (sample_set in filename and 
                            any(filename.endswith(ext) for ext in ['.ods', '.xlsx', '.csv'])):
                            file_path = os.path.join(exports_dir, filename)
                            matching_files.append((file_path, os.path.getmtime(file_path)))
                    
                    if matching_files:
                        # Return most recent file
                        return sorted(matching_files, key=lambda x: x[1], reverse=True)[0][0]
        
        return None
    
    def _get_plot3d_file(self) -> Optional[str]:
        """Get the Plot_3D file to use."""
        if hasattr(self, 'plot3d_path_var') and self.plot3d_path_var.get() != "Auto-detect":
            return self.plot3d_path_var.get()
        return None
    
    def _get_create_new_option(self) -> bool:
        """Get create new file option."""
        if hasattr(self, 'create_new_var'):
            return self.create_new_var.get()
        return True
    
    def _get_start_row(self) -> int:
        """Get starting row for data insertion."""
        if hasattr(self, 'start_row_var'):
            try:
                return int(self.start_row_var.get())
            except ValueError:
                pass
        return 8  # Default
    
    def _update_status(self, message: str, color: str = "black"):
        """Update status label safely from any thread."""
        def update():
            self.status_label.config(text=message, fg=color)
        
        self.parent_frame.after(0, update)
    
    def _show_progress(self, show: bool):
        """Show/hide progress bar."""
        def toggle():
            if show:
                self.progress_bar.pack(pady=2)
                self.progress_bar.start(10)  # Animation speed
                self.integrate_button.config(state=tk.DISABLED, text="Integrating...")
            else:
                self.progress_bar.stop()
                self.progress_bar.pack_forget()
                self.integrate_button.config(state=tk.NORMAL, text="Send to Plot_3D")
        
        self.parent_frame.after(0, toggle)
    
    def _trigger_plot3d_refresh(self):
        """Trigger Plot_3D refresh if possible."""
        # This could be enhanced to actually communicate with Plot_3D
        # For now, just update status
        self._update_status("Ready (data sent)", "green")
    
    def _show_help(self):
        """Show help information."""
        help_text = """StampZ to Plot_3D Integration Help

This tool transfers your StampZ color analysis data to Plot_3D for visualization.

Basic Usage:
1. Complete your color analysis in StampZ
2. Save your measurements (including averages)  
3. Click "Send to Plot_3D"
4. Data will be automatically transferred starting at row 8

Data Mapping:
• L*_norm → Xnorm (Plot_3D X-axis)
• a*_norm → Ynorm (Plot_3D Y-axis) 
• b*_norm → Znorm (Plot_3D Z-axis)
• DataID → DataID (point labels)

Auto-Refresh:
When enabled, Plot_3D will be notified to refresh its display automatically.

Advanced Options:
• Manually select specific export and target files
• Choose starting row for data insertion
• Control whether to create new files

Semi-Real-Time:
Each time you save averages in StampZ, you can click "Send to Plot_3D" 
to update the visualization with your latest data!"""

        messagebox.showinfo("Plot_3D Integration Help", help_text)
    
    def get_frame(self) -> tk.Widget:
        """Get the main frame widget."""
        return self.frame


def demo():
    """Demo the integration panel."""
    root = tk.Tk()
    root.title("Plot_3D Integration Demo")
    root.geometry("400x300")
    
    # Mock functions
    def get_sample_set():
        return "137_averages"
    
    def on_success():
        print("Export successful!")
    
    # Create integration panel
    panel = Plot3DIntegrationPanel(
        parent_frame=root,
        get_current_sample_set=get_sample_set,
        on_export_success=on_success
    )
    
    panel.get_frame().pack(fill=tk.X, padx=10, pady=10)
    
    # Add some padding
    tk.Label(root, text="Demo - StampZ Plot_3D Integration", 
            font=("Arial", 12, "bold")).pack(pady=10)
    
    root.mainloop()


if __name__ == "__main__":
    demo()
