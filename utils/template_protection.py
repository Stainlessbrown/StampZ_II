#!/usr/bin/env python3
"""
Template protection manager for sample mode.
Manages template protection state and detects modifications to prevent accidental overwrites.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from copy import deepcopy


@dataclass
class SampleParameters:
    """Represents parameters for a single sample."""
    shape: str
    width: float
    height: float
    anchor: str
    
    def __eq__(self, other):
        if not isinstance(other, SampleParameters):
            return False
        return (
            self.shape == other.shape and
            abs(self.width - other.width) < 0.1 and
            abs(self.height - other.height) < 0.1 and
            self.anchor == other.anchor
        )


class TemplateProtectionManager:
    """Manages template protection state and modification detection."""
    
    def __init__(self, control_panel):
        self.control_panel = control_panel
        self.is_protected = False
        self.original_template_name = ""
        self.original_parameters: List[SampleParameters] = []
        self.current_parameters: List[SampleParameters] = []
        self._modification_handlers = []
        
    def protect_template(self, template_name: str, coordinates) -> None:
        """Mark a template as protected and store original parameters."""
        self.is_protected = True
        self.original_template_name = template_name
        
        # Store original parameters from loaded coordinates
        self.original_parameters = []
        for coord in coordinates[:5]:  # Limit to 5 samples
            params = SampleParameters(
                shape='circle' if coord.sample_type.value == 'circle' else 'rectangle',
                width=float(coord.sample_size[0]),
                height=float(coord.sample_size[1]) if coord.sample_type.value == 'rectangle' else float(coord.sample_size[0]),
                anchor=coord.anchor_position
            )
            self.original_parameters.append(params)
        
        # Initialize current parameters as copy of original
        self.current_parameters = deepcopy(self.original_parameters)
        
        # Set up modification detection
        self._setup_modification_detection()
        
    def unprotect_template(self) -> None:
        """Remove template protection."""
        self.is_protected = False
        self.original_template_name = ""
        self.original_parameters.clear()
        self.current_parameters.clear()
        self._remove_modification_detection()
        
    def _setup_modification_detection(self) -> None:
        """Set up event handlers to detect modifications."""
        self._remove_modification_detection()  # Remove any existing handlers
        
        
        # Add trace callbacks to sample control variables
        for i, control in enumerate(self.control_panel.sample_controls):
            if i >= len(self.original_parameters):
                break
                
            # Create closures with the correct index value
            def make_callback(index):
                return lambda *args: self._on_parameter_change(index)
            
            # Add traces to detect changes
            shape_callback = make_callback(i)
            handler_id = control['shape'].trace('w', shape_callback)
            self._modification_handlers.append((control['shape'], handler_id))
            
            width_callback = make_callback(i)
            handler_id = control['width'].trace('w', width_callback)
            self._modification_handlers.append((control['width'], handler_id))
            
            height_callback = make_callback(i)
            handler_id = control['height'].trace('w', height_callback)
            self._modification_handlers.append((control['height'], handler_id))
            
            anchor_callback = make_callback(i)
            handler_id = control['anchor'].trace('w', anchor_callback)
            self._modification_handlers.append((control['anchor'], handler_id))
            
    
    def _remove_modification_detection(self) -> None:
        """Remove modification detection handlers."""
        for var, handler_id in self._modification_handlers:
            try:
                var.trace_vdelete('w', handler_id)
            except:
                pass  # Handler might already be removed
        self._modification_handlers.clear()
    
    def _on_parameter_change(self, sample_index: int) -> None:
        """Handle parameter change detection."""
        
        if not self.is_protected or sample_index >= len(self.original_parameters):
            return
            
        # Update current parameters
        if sample_index >= len(self.current_parameters):
            self.current_parameters.extend([SampleParameters('circle', 10, 10, 'center')] * 
                                         (sample_index + 1 - len(self.current_parameters)))
        
        try:
            control = self.control_panel.sample_controls[sample_index]
            width_val = float(control['width'].get())
            height_val = float(control['height'].get())
            
            original = self.original_parameters[sample_index]
            new_params = SampleParameters(
                shape=control['shape'].get(),
                width=width_val,
                height=height_val,
                anchor=control['anchor'].get()
            )
            
            
            self.current_parameters[sample_index] = new_params
            
        except (ValueError, IndexError) as e:
            return  # Invalid values, ignore
        
        # Just update the current parameters, don't show warning yet
        # Warning will be shown when user clicks Analyze
        has_mods = self.has_modifications()
    
    def has_modifications(self) -> bool:
        """Check if current parameters differ from original."""
        if not self.is_protected:
            return False
            
        if len(self.current_parameters) != len(self.original_parameters):
            print(f"DEBUG: Parameter count mismatch: {len(self.current_parameters)} vs {len(self.original_parameters)}")
            return True
            
        for i, (current, original) in enumerate(zip(self.current_parameters, self.original_parameters)):
            if current != original:
                print(f"DEBUG: Modification detected in sample {i+1}: {original} -> {current}")
                return True
                
        print("DEBUG: No modifications detected")
        return False
    
    def get_modifications(self) -> List[Tuple[int, str]]:
        """Get list of modifications as (sample_index, description) tuples."""
        modifications = []
        
        if not self.is_protected:
            return modifications
        
        for i, (current, original) in enumerate(zip(self.current_parameters, self.original_parameters)):
            changes = []
            
            if current.shape != original.shape:
                changes.append(f"shape: {original.shape} → {current.shape}")
                
            if abs(current.width - original.width) >= 0.1:
                changes.append(f"width: {original.width} → {current.width}")
                
            if abs(current.height - original.height) >= 0.1:
                changes.append(f"height: {original.height} → {current.height}")
                
            if current.anchor != original.anchor:
                changes.append(f"anchor: {original.anchor} → {current.anchor}")
            
            if changes:
                modifications.append((i + 1, ", ".join(changes)))
        
        return modifications
    
    def _show_protection_warning(self) -> None:
        """Show warning about modifying protected template."""
        if not self.has_modifications():
            return
            
        # Only show warning once per session for efficiency
        if hasattr(self, '_warning_shown'):
            return
        self._warning_shown = True
        
        # Schedule the warning to appear after current event processing
        self.control_panel.after_idle(self._display_warning_dialog)
    
    def _display_warning_dialog(self) -> None:
        """Display the protection warning dialog."""
        modifications = self.get_modifications()
        
        dialog = tk.Toplevel(self.control_panel)
        dialog.title("Protected Template Modified")
        dialog.transient(self.control_panel)
        dialog.grab_set()
        
        # Set dialog size and position
        dialog_width = 500
        dialog_height = 400
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Warning message
        warning_frame = ttk.Frame(dialog)
        warning_frame.pack(fill=tk.X, padx=10, pady=10)
        
        warning_icon = ttk.Label(warning_frame, text="⚠️", font=('Arial', 24))
        warning_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        warning_text = ttk.Label(
            warning_frame,
            text=f"Template '{self.original_template_name}' is protected!",
            font=('Arial', 14, 'bold'),
            foreground='red'
        )
        warning_text.pack(side=tk.LEFT)
        
        # Explanation
        explanation = ttk.Label(
            dialog,
            text="You have modified parameters of a protected template. "
                 "The original template cannot be overwritten directly.",
            wraplength=450,
            justify=tk.LEFT
        )
        explanation.pack(padx=10, pady=(0, 10))
        
        # Modifications list
        if modifications:
            mods_frame = ttk.LabelFrame(dialog, text="Detected Modifications")
            mods_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            mods_text = tk.Text(mods_frame, height=8, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(mods_frame, orient=tk.VERTICAL, command=mods_text.yview)
            mods_text.configure(yscrollcommand=scrollbar.set)
            
            for sample_num, description in modifications:
                mods_text.insert(tk.END, f"Sample {sample_num}: {description}\n")
            
            mods_text.config(state=tk.DISABLED)
            mods_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_as_new():
            dialog.destroy()
            self.show_save_as_dialog()
        
        def revert_changes():
            self._revert_to_original()
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save As New Template", 
                  command=save_as_new).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Revert Changes", 
                  command=revert_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Continue Analysis", 
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def show_save_as_dialog(self, from_warning_dialog=False) -> Optional[str]:
        """Show save as dialog for protected template."""
        dialog = tk.Toplevel(self.control_panel)
        dialog.title("Save As New Template")
        dialog.transient(self.control_panel)
        dialog.grab_set()
        
        # Set dialog size and position
        dialog_width = 500
        dialog_height = 300
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        result = {'name': None, 'saved': False}
        
        # Instructions
        ttk.Label(
            dialog,
            text="Enter a new name for the modified template:",
            font=('Arial', 11)
        ).pack(padx=10, pady=(20, 10))
        
        # Name entry
        name_var = tk.StringVar(value=f"{self.original_template_name}_modified")
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30, font=('Arial', 11))
        name_entry.pack(padx=10, pady=5)
        name_entry.select_range(0, tk.END)
        name_entry.focus_set()
        
        # Validation message
        validation_label = ttk.Label(dialog, text="", foreground='red')
        validation_label.pack(padx=10, pady=5)
        
        # Success message (initially hidden)
        success_label = ttk.Label(dialog, text="", foreground='green')
        success_label.pack(padx=10, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=20)
        
        # Save button and its handler
        save_button = ttk.Button(button_frame, text="Save")
        save_button.pack(side=tk.LEFT, padx=5)
        
        def validate_and_save():
            name = name_var.get().strip()
            if not name:
                validation_label.config(text="Template name cannot be empty")
                success_label.config(text="")
                return
                
            if name == self.original_template_name:
                validation_label.config(text="New name must be different from original")
                success_label.config(text="")
                return
            
            # Check if template already exists in coordinate database
            try:
                from utils.coordinate_db import CoordinateDB
                db = CoordinateDB()
                existing_sets = db.get_all_set_names()
                print(f"DEBUG: Checking if '{name}' exists in coordinate DB: {existing_sets}")
                if name in existing_sets:
                    validation_label.config(text=f"Template '{name}' already exists in coordinate database. Choose a different name.")
                    success_label.config(text="")
                    return
            except Exception as e:
                print(f"DEBUG: Error checking coordinate database: {e}")
            
            # Also check color analysis databases for potential conflicts
            try:
                from utils.color_analysis_db import ColorAnalysisDB
                import os
                
                # Get the color analysis data directory
                stampz_data_dir = os.getenv('STAMPZ_DATA_DIR')
                if stampz_data_dir:
                    color_data_dir = os.path.join(stampz_data_dir, "data", "color_analysis")
                else:
                    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    color_data_dir = os.path.join(current_dir, "data", "color_analysis")
                
                if os.path.exists(color_data_dir):
                    existing_analysis_dbs = ColorAnalysisDB.get_all_sample_set_databases(color_data_dir)
                    print(f"DEBUG: Checking if '{name}' exists in color analysis DBs: {existing_analysis_dbs}")
                    
                    # Standardize the name for comparison
                    from utils.naming_utils import standardize_name
                    standardized_name = standardize_name(name)
                    
                    if name in existing_analysis_dbs or standardized_name in existing_analysis_dbs:
                        validation_label.config(text=f"Template '{name}' conflicts with existing color analysis data. Choose a different name.")
                        success_label.config(text="")
                        return
                        
            except Exception as e:
                print(f"DEBUG: Error checking color analysis databases: {e}")
            
            # Clear validation message and save
            validation_label.config(text="")
            result['name'] = name
            result['saved'] = True
            
            # Save the modified template to the coordinate database
            if self._save_modified_template_to_db(name):
                # Update template name and remove protection
                self.control_panel.sample_set_name.set(name)
                
                # Update the main app coordinates with new parameters before refreshing
                if hasattr(self.control_panel, 'main_app') and self.control_panel.main_app:
                    canvas = self.control_panel.main_app.canvas
                    if hasattr(canvas, '_coord_markers') and canvas._coord_markers:
                        # Update existing markers with new parameters
                        for i, params in enumerate(self.current_parameters):
                            if i < len(canvas._coord_markers):
                                marker = canvas._coord_markers[i]
                                if not marker.get('is_preview', False):
                                    # Update marker parameters
                                    marker['sample_type'] = params.shape
                                    marker['sample_width'] = params.width
                                    marker['sample_height'] = params.height
                                    marker['anchor'] = params.anchor
                                    print(f"DEBUG: Updated marker {i+1}: {params.shape} {params.width}x{params.height} {params.anchor}")
                        
                        print(f"DEBUG: Updated {len(self.current_parameters)} canvas markers with new parameters")
                        
                        # Redraw all markers with updated parameters
                        canvas._redraw_all_coordinate_markers()
                        canvas.update_display()
                        print("DEBUG: Canvas markers redrawn successfully")
                        
                        # Show confirmation dialog after refresh to verify appearance
                        if not self._confirm_template_appearance(name, dialog):
                            # User cancelled - revert the changes
                            validation_label.config(text="Template save cancelled - shapes/positions may need adjustment")
                            success_label.config(text="")
                            return
                    else:
                        print("DEBUG: No canvas markers found to update")
                else:
                    print("DEBUG: No main app or canvas found for marker update")
                
                # Refresh the UI and template selector
                self.control_panel.update()
                if hasattr(self.control_panel, '_refresh_sample_sets'):
                    self.control_panel._refresh_sample_sets(show_feedback=False)
                    print("DEBUG: Refreshed template selector dropdown")
                
                # DON'T remove protection yet - we need it for the new template
                # Instead, update the protection to the new template name and parameters
                self.original_template_name = name
                self.original_parameters = deepcopy(self.current_parameters)
                print(f"DEBUG: Updated template protection to new template '{name}'")
                
                # Show success message
                success_label.config(text=f"✓ Template saved as '{name}' and is now protected")
                
                # Disable save button and entry after successful save
                save_button.config(state='disabled')
                name_entry.config(state='disabled')
                
                # Add close button after successful save
                ttk.Button(
                    button_frame, 
                    text="Close", 
                    command=dialog.destroy
                ).pack(side=tk.RIGHT, padx=5)
            else:
                # Show error if save failed
                validation_label.config(text=f"Failed to save template '{name}'. Please try again.")
                success_label.config(text="")
        
        save_button.config(command=validate_and_save)
        
        def cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.RIGHT, padx=5)
        
        # Bind Enter key to save
        dialog.bind('<Return>', lambda e: validate_and_save())
        
        dialog.wait_window()
        
        return result['name'] if result['saved'] else None
    
    def _confirm_template_appearance(self, template_name: str, parent_dialog) -> bool:
        """Show confirmation dialog after canvas refresh to verify template appearance.
        
        Args:
            template_name: Name of the template being saved
            parent_dialog: The parent save-as dialog
            
        Returns:
            True if user confirms the template looks correct, False if cancelled
        """
        # Temporarily hide parent dialog
        parent_dialog.withdraw()
        
        confirm_dialog = tk.Toplevel(self.control_panel)
        confirm_dialog.title("Verify Template Appearance")
        confirm_dialog.transient(self.control_panel)
        confirm_dialog.grab_set()
        
        # Set dialog size and position
        dialog_width = 450
        dialog_height = 250
        screen_width = confirm_dialog.winfo_screenwidth()
        screen_height = confirm_dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        confirm_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        result = {'confirmed': False}
        
        # Icon and title
        header_frame = ttk.Frame(confirm_dialog)
        header_frame.pack(fill=tk.X, padx=20, pady=20)
        
        icon_label = ttk.Label(header_frame, text="👁️", font=('Arial', 32))
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        title_label = ttk.Label(
            header_frame,
            text="Verify Template Appearance",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(side=tk.LEFT, anchor='w')
        
        # Instructions
        instructions = ttk.Label(
            confirm_dialog,
            text=f"The canvas has been updated with the new template parameters for '{template_name}'.\n\n"
                 "Please check the sample areas on the image to ensure:\n"
                 "• Shapes and sizes look correct\n"
                 "• Sample areas don't overlap unwanted regions\n"
                 "• Sample areas are positioned on printed ink areas\n\n"
                 "Do you want to keep this template?",
            wraplength=400,
            justify=tk.LEFT,
            font=('Arial', 11)
        )
        instructions.pack(padx=20, pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(confirm_dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        def confirm_template():
            result['confirmed'] = True
            confirm_dialog.destroy()
            parent_dialog.deiconify()  # Restore parent dialog
        
        def cancel_template():
            result['confirmed'] = False
            confirm_dialog.destroy()
            parent_dialog.deiconify()  # Restore parent dialog
        
        # Primary action button (left side)
        ttk.Button(
            button_frame, 
            text="✓ Keep Template", 
            command=confirm_template
        ).pack(side=tk.LEFT, padx=5)
        
        # Secondary action buttons (right side)
        ttk.Button(
            button_frame, 
            text="✗ Cancel Save", 
            command=cancel_template
        ).pack(side=tk.RIGHT, padx=5)
        
        # Bind Enter key to confirm
        confirm_dialog.bind('<Return>', lambda e: confirm_template())
        
        # Bind Escape key to cancel
        confirm_dialog.bind('<Escape>', lambda e: cancel_template())
        
        confirm_dialog.wait_window()
        return result['confirmed']
    
    
    
    def _revert_to_original(self) -> None:
        """Revert all parameters to original values."""
        if not self.is_protected:
            return
            
        # Temporarily remove modification detection to avoid recursion
        self._remove_modification_detection()
        
        try:
            # Reset all sample controls to original values
            for i, original in enumerate(self.original_parameters):
                if i < len(self.control_panel.sample_controls):
                    control = self.control_panel.sample_controls[i]
                    control['shape'].set(original.shape)
                    control['width'].set(str(int(original.width)))
                    control['height'].set(str(int(original.height)))
                    control['anchor'].set(original.anchor)
            
            # Reset current parameters
            self.current_parameters = deepcopy(self.original_parameters)
            
            # Clear warning shown flag
            if hasattr(self, '_warning_shown'):
                delattr(self, '_warning_shown')
            
        finally:
            # Restore modification detection
            self._setup_modification_detection()
    
    def _show_protection_warning_modal(self) -> bool:
        """Show modal protection warning and return True if analysis should proceed."""
        print("DEBUG: _show_protection_warning_modal called")
        if not self.has_modifications():
            print("DEBUG: No modifications detected, returning True")
            return True
        
        modifications = self.get_modifications()
        print(f"DEBUG: Found {len(modifications)} modifications, showing dialog")
        
        dialog = tk.Toplevel(self.control_panel)
        dialog.title("Protected Template Modified")
        dialog.transient(self.control_panel)
        dialog.grab_set()
        
        # Set dialog size and position
        dialog_width = 500
        dialog_height = 450
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        result = {'proceed': False}
        
        # Warning message
        warning_frame = ttk.Frame(dialog)
        warning_frame.pack(fill=tk.X, padx=10, pady=10)
        
        warning_icon = ttk.Label(warning_frame, text="⚠️", font=('Arial', 24))
        warning_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        warning_text = ttk.Label(
            warning_frame,
            text=f"Template '{self.original_template_name}' is protected!",
            font=('Arial', 14, 'bold'),
            foreground='red'
        )
        warning_text.pack(side=tk.LEFT)
        
        # Explanation
        explanation = ttk.Label(
            dialog,
            text="You have modified parameters of a protected template. "
                 "What would you like to do?",
            wraplength=450,
            justify=tk.LEFT
        )
        explanation.pack(padx=10, pady=(0, 10))
        
        # Modifications list
        if modifications:
            mods_frame = ttk.LabelFrame(dialog, text="Detected Modifications")
            mods_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            mods_text = tk.Text(mods_frame, height=6, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(mods_frame, orient=tk.VERTICAL, command=mods_text.yview)
            mods_text.configure(yscrollcommand=scrollbar.set)
            
            for sample_num, description in modifications:
                mods_text.insert(tk.END, f"Sample {sample_num}: {description}\n")
            
            mods_text.config(state=tk.DISABLED)
            mods_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_as_new():
            print("DEBUG: save_as_new button clicked")
            result['proceed'] = True
            dialog.destroy()
            self.show_save_as_dialog()
            print("DEBUG: save_as_new completed")
        
        def revert_changes():
            self._revert_to_original()
            result['proceed'] = True  # Proceed with analysis after reverting
            dialog.destroy()
        
        def continue_analysis():
            result['proceed'] = True
            dialog.destroy()
        
        def cancel_analysis():
            result['proceed'] = False
            dialog.destroy()
        
        # Reorganized button layout - single row
        ttk.Button(button_frame, text="Save As New Template", 
                  command=save_as_new).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Revert Changes", 
                  command=revert_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Continue Analysis", 
                  command=continue_analysis).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=cancel_analysis).pack(side=tk.RIGHT, padx=5)
        
        dialog.wait_window()
        return result['proceed']
    
    def check_before_analyze(self) -> bool:
        """Check for modifications before analysis and show warning if needed. Returns True if analysis should proceed."""
        if not self.is_protected or not self.has_modifications():
            return True
            
        # Show protection warning and get user decision
        return self._show_protection_warning_modal()
    
    def _save_modified_template_to_db(self, template_name: str) -> bool:
        """Save the modified template parameters to the coordinate database.
        
        Args:
            template_name: Name for the new template
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            from utils.coordinate_db import CoordinateDB, CoordinatePoint, SampleAreaType
            
            print(f"DEBUG: Saving modified template '{template_name}' to coordinate database")
            
            # Get current coordinate positions from the canvas markers
            current_markers = None
            if hasattr(self.control_panel, 'main_app') and self.control_panel.main_app:
                canvas = self.control_panel.main_app.canvas
                if hasattr(canvas, '_coord_markers') and canvas._coord_markers:
                    current_markers = canvas._coord_markers
            
            # Create coordinate points from current parameters, preserving actual positions
            coordinates = []
            for i, params in enumerate(self.current_parameters):
                # Convert parameters back to CoordinatePoint format
                sample_type = SampleAreaType.CIRCLE if params.shape == 'circle' else SampleAreaType.RECTANGLE
                sample_size = (params.width, params.height)
                
                # Get actual coordinate positions from canvas markers
                if current_markers and i < len(current_markers):
                    marker = current_markers[i]
                    # Use the image position from the marker, not canvas position
                    x_pos, y_pos = marker['image_pos']
                    print(f"DEBUG: Using actual marker position for coordinate {i+1}: ({x_pos}, {y_pos})")
                else:
                    # This should rarely happen - log as a warning
                    print(f"WARNING: No marker found for coordinate {i+1}, using dummy position")
                    x_pos = 100 + i * 50
                    y_pos = 100 + i * 50
                
                coord = CoordinatePoint(
                    x=x_pos,
                    y=y_pos,
                    sample_type=sample_type,
                    sample_size=sample_size,
                    anchor_position=params.anchor
                )
                coordinates.append(coord)
                print(f"DEBUG: Created coordinate {i+1}: {params.shape} {params.width}x{params.height} {params.anchor} at ({x_pos}, {y_pos})")
            
            # Save to coordinate database
            db = CoordinateDB()
            # Use a dummy image path since this is just for template storage
            dummy_image_path = "template_modified.png"
            success, standardized_name = db.save_coordinate_set(
                name=template_name,
                image_path=dummy_image_path,
                coordinates=coordinates
            )
            
            if success:
                print(f"DEBUG: Successfully saved modified template as '{standardized_name}'")
                return True
            else:
                print(f"DEBUG: Failed to save modified template: {standardized_name}")
                return False
                
        except Exception as e:
            print(f"DEBUG: Error saving modified template: {e}")
            return False
    
    
    def handle_protected_save(self) -> bool:
        """Handle save attempt on protected template. Returns True if save should proceed."""
        if not self.is_protected or not self.has_modifications():
            return True
        
        # Show save as dialog
        new_name = self.show_save_as_dialog()
        
        # If user provided a new name, allow save to proceed
        return new_name is not None
