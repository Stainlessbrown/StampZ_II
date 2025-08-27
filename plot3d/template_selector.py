import tkinter as tk
from tkinter import filedialog
import os
import logging

class TemplateSelector:
    def __init__(self, parent=None):
        self.file_path = None
        self.root = None
        self.parent = parent
        self.create_and_run_dialog()
        
    def create_and_run_dialog(self):
        """Create and run the file selection dialog with proper error handling."""
        try:
            # Create the main window - check if we have a parent (embedded mode)
            if self.parent:
                # Embedded mode - create as Toplevel window
                self.root = tk.Toplevel(self.parent)
                self.root.transient(self.parent)
                self.root.grab_set()  # Modal to parent only, not entire app
            else:
                # Standalone mode - create root window
                self.root = tk.Tk()
                
            self.root.title("Select Worksheet")
            self.root.geometry("300x100")
            self.root.lift()
            self.root.attributes("-topmost", True)
            
            # Add heading
            heading = tk.Label(self.root, text=".ods", font=("Arial", 14, "bold"))
            heading.pack(pady=10)
            
            custom_button = tk.Button(
                self.root, 
                text="Select File",
                command=self.select_custom_file,
                width=20,
                height=2
            )
            custom_button.pack(pady=5)
            
            # Center dialog if we have a parent
            if self.parent:
                self.root.update_idletasks()
                x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.root.winfo_width() // 2)
                y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.root.winfo_height() // 2)
                self.root.geometry(f"+{x}+{y}")
                
                # Wait for window instead of starting mainloop in embedded mode
                self.parent.wait_window(self.root)
            else:
                # Start the main loop only in standalone mode
                self.root.mainloop()
        except Exception as e:
            logging.error(f"Error creating template selector window: {str(e)}")
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass
            raise
    
    def select_custom_file(self):
        logging.debug("Select File")
        # Create a new temporary tkinter root for the file dialog
        file_root = tk.Tk()
        file_root.withdraw()
        
        file_types = [
            ('OpenDocument Spreadsheet', '*.ods'),
            ('All files', '*.*')
        ]
        
        selected_file = filedialog.askopenfilename(filetypes=file_types)
        file_root.destroy()
        
        if selected_file:
            # Convert to absolute path
            self.file_path = os.path.abspath(selected_file)
            logging.info(f"Selected file (absolute path): {self.file_path}")
            self.root.destroy()
        else:
            logging.warning("No file selected")

