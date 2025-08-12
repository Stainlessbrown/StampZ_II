#!/usr/bin/env python3
"""
Color calibration wizard for StampZ GUI.
Helps users calibrate their display/screenshot color accuracy.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
from datetime import datetime
from PIL import Image, ImageTk
from typing import Dict, Tuple, Optional
import tempfile

from utils.color_calibration import ColorCalibrator
from utils.color_analyzer import ColorAnalyzer
from utils.dynamic_color_calibration import DynamicColorCalibrator

class CalibrationWizard:
    """GUI wizard for color calibration."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.window = None
        self.calibrator = ColorCalibrator()
        self.analyzer = ColorAnalyzer()
        
        # Calibration state
        self.reference_image_path = None
        self.measured_colors = {}
        self.correction_matrix = None
        
        # GUI elements
        self.step_frame = None
        self.current_step = 1
        self.max_steps = 4
        
    def show(self):
        """Show the calibration wizard."""
        self.create_window()
        self.show_step_1()
        
    def create_window(self):
        """Create the main wizard window."""
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("StampZ Color Calibration Wizard")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        
        # Create main frame
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Color Calibration Wizard", 
                               style="Heading.TLabel", font=('Helvetica', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20), sticky=tk.W)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, length=400, mode='determinate')
        self.progress.grid(row=0, column=1, pady=(0, 20), sticky=tk.E)
        self.progress['maximum'] = self.max_steps
        self.progress['value'] = self.current_step
        
        # Step frame (will be populated by step functions)
        self.step_frame = ttk.Frame(main_frame)
        self.step_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.step_frame.grid_columnconfigure(0, weight=1)
        
        # Navigation buttons
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 0))
        
        self.back_btn = ttk.Button(nav_frame, text="← Back", command=self.go_back)
        self.back_btn.pack(side=tk.LEFT)
        
        self.next_btn = ttk.Button(nav_frame, text="Next →", command=self.go_next)
        self.next_btn.pack(side=tk.RIGHT)
        
        self.cancel_btn = ttk.Button(nav_frame, text="Cancel", command=self.cancel)
        self.cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
    def clear_step_frame(self):
        """Clear the current step frame."""
        for widget in self.step_frame.winfo_children():
            widget.destroy()
    
    def show_step_1(self):
        """Step 1: Introduction and explanation."""
        self.current_step = 1
        self.progress['value'] = self.current_step
        self.clear_step_frame()
        
        # Introduction text
        intro_text = """
Welcome to the StampZ Color Calibration Wizard!

This wizard will help improve the color accuracy of your StampZ measurements by:

• Detecting display and screenshot color issues
• Creating correction factors specific to your system
• Improving accuracy for future color analysis

The process takes about 2-3 minutes and involves:

1. Creating a reference color chart
2. Taking a screenshot or importing your measurement
3. Analyzing color deviations
4. Applying corrections to StampZ

Why calibrate?
Screenshots and different displays can introduce color shifts that affect 
measurement accuracy. This calibration will help correct these issues.
        """.strip()
        
        intro_label = ttk.Label(self.step_frame, text=intro_text, 
                               wraplength=600, justify=tk.LEFT)
        intro_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=20)
        
        # System info
        system_frame = ttk.LabelFrame(self.step_frame, text="System Information", padding="10")
        system_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=20)
        
        import platform
        system_info = f"""
Platform: {platform.system()} {platform.release()}
Python: {platform.python_version()}
Current StampZ color mode: {'Calibrated' if self.analyzer.color_correction else 'Standard'}
        """.strip()
        
        ttk.Label(system_frame, text=system_info).pack(anchor=tk.W)
        
        # Update navigation
        self.back_btn.configure(state='disabled')
        self.next_btn.configure(text="Start Calibration →", state='normal')
    
    def show_step_2(self):
        """Step 2: Generate reference colors."""
        self.current_step = 2
        self.progress['value'] = self.current_step
        self.clear_step_frame()
        
        ttk.Label(self.step_frame, text="Step 2: Generate Reference Color Chart", 
                 font=('Helvetica', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 20))
        
        instructions = """
For accurate calibration, you need reference colors from OUTSIDE StampZ.
This ensures we capture real display and screenshot color shifts that affect your measurements.

Choose the method that works best for you:
        """.strip()
        
        ttk.Label(self.step_frame, text=instructions, wraplength=600).grid(row=1, column=0, sticky=tk.W, pady=(0, 20))
        
        # Warning about proper calibration
        warning_frame = ttk.LabelFrame(self.step_frame, text="⚠️ Important: Why External Colors Matter", padding="10")
        warning_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        warning_text = """
Using colors generated within StampZ will NOT detect real color problems!

Real calibration requires colors that go through your entire workflow:
• Display rendering • Screenshot capture • Color profile conversion

External colors capture the real color shifts that affect your measurements.
        """.strip()
        
        ttk.Label(warning_frame, text=warning_text, wraplength=550, 
                 foreground='#D2691E', font=('Helvetica', 10)).pack(anchor=tk.W)
        
        # Option buttons
        option_frame = ttk.Frame(self.step_frame)
        option_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Option 1: Create calibration grid (RECOMMENDED)
        option1_btn = ttk.Button(option_frame, text="🎯 Create Calibration Grid (RECOMMENDED)",
                                command=self.show_calibration_grid_workflow)
        option1_btn.pack(fill=tk.X, pady=5)
        
        ttk.Label(option_frame, text="Guided workflow: Screenshot 6 colors → Auto-arrange into calibration grid",
                 foreground='green', font=('Helvetica', 9, 'bold')).pack(anchor=tk.W, padx=20)
        
        # Option 2: Use existing image
        option2_btn = ttk.Button(option_frame, text="📁 Use Existing Screenshot",
                                command=self.use_existing_image)
        option2_btn.pack(fill=tk.X, pady=5)
        
        ttk.Label(option_frame, text="If you already have a screenshot of pure RGB colors from an external source",
                 foreground='gray', font=('Helvetica', 9)).pack(anchor=tk.W, padx=20)
        
        # Status display
        self.status_label = ttk.Label(self.step_frame, text="", foreground='blue')
        self.status_label.grid(row=3, column=0, sticky=tk.W, pady=20)
        
        # Update navigation
        self.back_btn.configure(state='normal')
        self.next_btn.configure(text="Next →", state='disabled')
    
    def generate_color_chart(self):
        """Generate and display a color calibration chart."""
        try:
            # Create calibration target
            target_image = self.calibrator.create_calibration_target(size=(600, 400))
            
            # Save to temporary file
            temp_dir = tempfile.gettempdir()
            self.reference_image_path = os.path.join(temp_dir, "stampz_calibration_chart.png")
            target_image.save(self.reference_image_path)
            
            # Display the image in a new window
            self.display_reference_image(target_image)
            
            self.status_label.configure(text="✓ Color chart generated and displayed. Take a screenshot when ready.")
            self.next_btn.configure(state='normal')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate color chart: {e}")
    
    def display_reference_image(self, pil_image):
        """Display the reference image in a separate window."""
        display_window = tk.Toplevel(self.window)
        display_window.title("StampZ Calibration Chart - Screenshot This!")
        display_window.geometry("700x500")
        
        # Instructions
        inst_frame = ttk.Frame(display_window, padding="10")
        inst_frame.pack(fill=tk.X)
        
        instructions = """
📸 SCREENSHOT INSTRUCTIONS:

1. Take a screenshot of this color chart (the colored rectangles below)
2. Make sure the colors are clearly visible and not cut off
3. Save the screenshot somewhere you can find it
4. Return to the calibration wizard and click "Next"

The chart shows: Red, Green, Blue (top row) and White, Gray, Black (bottom row)
        """.strip()
        
        ttk.Label(inst_frame, text=instructions, wraplength=650, 
                 background='lightyellow', relief='solid', padding="10").pack()
        
        # Display the image
        img_frame = ttk.Frame(display_window, padding="10")
        img_frame.pack(expand=True, fill='both')
        
        # Convert PIL image to PhotoImage
        photo = ImageTk.PhotoImage(pil_image)
        img_label = ttk.Label(img_frame, image=photo)
        img_label.image = photo  # Keep a reference
        img_label.pack(expand=True)
        
        # Close button
        ttk.Button(display_window, text="Done - Return to Wizard", 
                  command=display_window.destroy).pack(pady=10)
    
    def show_web_instructions(self):
        """Show instructions for using web-based color generators."""
        # Create instruction window
        inst_window = tk.Toplevel(self.window)
        inst_window.title("Web-Based Color Calibration Instructions")
        inst_window.geometry("700x600")
        inst_window.resizable(True, True)
        
        # Main frame with scrollbar
        main_frame = ttk.Frame(inst_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="🌐 Web-Based Color Calibration (RECOMMENDED)", 
                               font=('Helvetica', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Instructions text
        instructions_text = tk.Text(main_frame, wrap=tk.WORD, width=70, height=25, 
                                   font=('Arial', 11))
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=instructions_text.yview)
        instructions_text.configure(yscrollcommand=scrollbar.set)
        
        instructions_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add detailed instructions
        instructions_content = """
🎯 WHY THIS METHOD IS BEST:
Using external websites ensures we capture REAL color shifts from your:
• Display color profile and calibration
• Screenshot method and compression
• Operating system color management
• Browser rendering differences

📋 STEP-BY-STEP INSTRUCTIONS:

1. OPEN A COLOR GENERATOR WEBSITE:
   Recommended sites:
   • htmlcolorcodes.com/colors/
   • colorhexa.com
   • color.adobe.com
   • Or search "HTML color picker" in your browser

2. GENERATE PURE COLORS:
   You need these exact RGB values:
   
   🔴 PURE RED:   RGB(255, 0, 0)   or   #FF0000
   🟢 PURE GREEN: RGB(0, 255, 0)   or   #00FF00
   🔵 PURE BLUE:  RGB(0, 0, 255)   or   #0000FF
   ⚪ PURE WHITE: RGB(255, 255, 255) or   #FFFFFF
   ⚫ PURE BLACK: RGB(0, 0, 0)      or   #000000
   🔘 50% GRAY:   RGB(128, 128, 128) or   #808080

3. DISPLAY EACH COLOR FULLSCREEN:
   • Set each color to fill most of your browser window
   • Make sure the color patch is large and clearly visible
   • Avoid any text or UI elements in the color area

4. TAKE SCREENSHOTS:
   • Screenshot each pure color individually
   • Or create one image with all colors arranged in a grid
   • Save screenshots in PNG format for best quality
   • Make sure colors are not cut off or distorted

5. RETURN TO CALIBRATION WIZARD:
   • Click "Done" below to return to the wizard
   • Click "Next" in the wizard
   • Select "Use Existing Screenshot" and choose your image

💡 PRO TIPS:
• Use your normal screenshot method (what you'd use for stamp analysis)
• Keep lighting consistent with your usual workspace
• Don't adjust monitor settings during calibration
• If possible, use the same browser you use for research

⚠️ AVOID THESE MISTAKES:
• Don't use StampZ's generated chart (defeats the purpose!)
• Don't use colors from within StampZ itself
• Don't use printed color charts (unless that's your workflow)
• Don't change display settings between calibration and normal use

🎯 WHAT WE'RE MEASURING:
Your "Pure Green (0,255,0)" might actually appear as (0,241,0) due to:
• Display color temperature being too warm
• sRGB vs wide color gamut differences  
• Screenshot compression artifacts
• macOS/Windows color management differences

This calibration will detect and correct these systematic shifts!
"""
        
        instructions_text.insert(tk.END, instructions_content.strip())
        instructions_text.config(state=tk.DISABLED)
        
        # Button frame
        button_frame = ttk.Frame(inst_window)
        button_frame.pack(fill=tk.X, pady=(10, 20), padx=20)
        
        # Done button
        done_btn = ttk.Button(button_frame, text="Done - I'll Use Web Colors", 
                             command=lambda: self._web_instructions_done(inst_window))
        done_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # URL buttons for quick access
        url_frame = ttk.Frame(button_frame)
        url_frame.pack(side=tk.LEFT)
        
        ttk.Label(url_frame, text="Quick access:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        urls = [
            ("Nix Sensor", "https://nixsensor.com/free-color-converter/")
        ]
        
        for name, url in urls:
            btn = ttk.Button(url_frame, text=name, 
                           command=lambda u=url: self._open_url(u))
            btn.pack(side=tk.LEFT, padx=5)
    
    def show_calibration_grid_workflow(self):
        """Show instructions for the guided calibration grid workflow using basic_colors."""
        # Create instruction window
        grid_window = tk.Toplevel(self.window)
        grid_window.title("Calibration Grid Workflow")
        grid_window.geometry("700x600")
        grid_window.resizable(True, True)
        
        # Main frame with scrollbar
        main_frame = ttk.Frame(grid_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎯 Guided Calibration Grid Workflow", 
                               font=('Helvetica', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Instructions text
        instructions_text = tk.Text(main_frame, wrap=tk.WORD, width=70, height=25, 
                                   font=('Arial', 11))
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=instructions_text.yview)
        instructions_text.configure(yscrollcommand=scrollbar.set)
        
        instructions_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add detailed instructions
        instructions_content = """
This is the most reliable way to calibrate StampZ.
It guides you through capturing 6 screenshots from StampZ's basic_colors library and automatically arranges them into a perfect calibration grid.

📋 STEP-BY-STEP INSTRUCTIONS:

1. OPEN STAMPZ BASIC COLORS:
   Click the "Open Basic Colors" button below to open StampZ's color library.
   This displays pure reference colors for calibration screenshots.

2. SCREENSHOT EACH REFERENCE COLOR:
   For each color below, you will:
   a. Click on the color in the basic_colors window
   b. Take a screenshot of the displayed color
   c. Save each screenshot with a clear name (e.g., "red.png", "green.png")

   Reference Colors to Capture:
   - 🔴 PURE RED:   RGB(255, 0, 0)
   - 🟢 PURE GREEN: RGB(0, 255, 0)
   - 🔵 PURE BLUE:  RGB(0, 0, 255)
   - ⚪ PURE WHITE: RGB(255, 255, 255)
   - ⚫ PURE BLACK: RGB(0, 0, 0)
   - 🔘 50% GRAY:   RGB(128, 128, 128)

3. CREATE THE CALIBRATION GRID:
   • Click "Create Grid from Screenshots" below
   • Select your 6 screenshots (red, green, blue, white, black, gray)
   • StampZ will automatically create a perfect calibration grid from them

4. RETURN TO THE WIZARD:
   • The wizard will automatically use the newly created grid
   • Click "Next" to analyze the grid and complete the calibration

💡 PRO TIPS:
• Use the same screenshot method for each color (the same you'd use for stamps)
• Use PNG format for best quality
• Screenshot the entire color display area
• This captures the real color drift from your display + screenshot process

🎯 WHY THIS WORKS:
Even though the colors come from StampZ, the screenshot process introduces the same
color shifts that affect your stamp measurements. We're calibrating the screenshot 
workflow, not the display of colors within StampZ.
"""
        
        instructions_text.insert(tk.END, instructions_content.strip())
        instructions_text.config(state=tk.DISABLED)
        
        # Button frame
        button_frame = ttk.Frame(grid_window)
        button_frame.pack(fill=tk.X, pady=(10, 20), padx=20)
        
        # Action buttons
        colors_btn = ttk.Button(button_frame, text="Open Basic Colors",
                               command=self._open_basic_colors)
        colors_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        create_grid_btn = ttk.Button(button_frame, text="Create Grid from Screenshots",
                                   command=lambda: self._create_grid_from_screenshots(grid_window))
        create_grid_btn.pack(side=tk.LEFT)
        
        done_btn = ttk.Button(button_frame, text="Done - Close",
                              command=grid_window.destroy)
        done_btn.pack(side=tk.RIGHT)
    
    def _create_grid_from_screenshots(self, parent_window):
        """Create a calibration grid image from multiple screenshots."""
        # Show detailed instructions before file selection
        instruction_msg = """🎯 IMPORTANT: File Selection Order Matters!

You must select your screenshot files in this EXACT order:
1. Red screenshot (first click)
2. Green screenshot (second click) 
3. Blue screenshot (third click)
4. White screenshot (fourth click)
5. Gray screenshot (fifth click)
6. Black screenshot (sixth click)

Tip: Hold Cmd/Ctrl and click each file in sequence.
The order you click determines the grid layout!"""
        
        messagebox.showinfo("File Selection Order", instruction_msg, parent=parent_window)
        
        # Ask user to select 6 image files
        file_paths = filedialog.askopenfilenames(
            title="Select 6 Screenshots IN ORDER: Red→Green→Blue→White→Gray→Black",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"),
                ("All files", "*.*")
            ],
            parent=parent_window
        )
        
        if len(file_paths) != 6:
            messagebox.showwarning("Incorrect File Count", "Please select exactly 6 image files.", parent=parent_window)
            return
        
        try:
            from PIL import Image
            
            # Open images
            images = [Image.open(fp) for fp in file_paths]
            
            # Determine size of each patch (use the smallest dimensions)
            min_width = min(img.width for img in images)
            min_height = min(img.height for img in images)
            
            # Create a new image to hold the grid
            grid_image = Image.new('RGB', (min_width * 3, min_height * 2))
            
            # Arrange images in a 3x2 grid
            positions = [
                (0, 0), (min_width, 0), (2 * min_width, 0),  # Top row
                (0, min_height), (min_width, min_height), (2 * min_width, min_height)  # Bottom row
            ]
            
            # Paste images into the grid
            for i, img in enumerate(images):
                # Resize image to the smallest dimensions
                resized_img = img.resize((min_width, min_height), Image.Resampling.LANCZOS)
                grid_image.paste(resized_img, positions[i])
            
            # Save the final grid image
            save_path = filedialog.asksaveasfilename(
                title="Save Combined Calibration Grid",
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("All files", "*.*")
                ],
                initialfile="stampz_calibration_grid.png",
                parent=parent_window
            )
            
            if save_path:
                grid_image.save(save_path)
                
                # Use this new grid for calibration
                self.reference_image_path = save_path
                self.status_label.configure(text=f"✓ Calibration grid created: {os.path.basename(save_path)}")
                self.next_btn.configure(state='normal')
                
                messagebox.showinfo("Grid Created", 
                                  "Calibration grid created successfully!\n\n"
                                  "You can now click 'Next' to analyze the grid.",
                                  parent=self.window)
                parent_window.destroy()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create calibration grid: {e}", parent=parent_window)
    
    def _web_instructions_done(self, window):
        """Handle completion of web instructions."""
        window.destroy()
        self.status_label.configure(text="✓ Ready to use web-based colors. Take screenshots and continue to Next step.")
        self.next_btn.configure(state='normal')
    
    def _open_url(self, url):
        """Open URL in default browser."""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open browser: {e}")
    
    def _open_basic_colors(self):
        """Open the StampZ basic colors library for reference color screenshots."""
        try:
            # Import the basic colors module
            from utils.basic_colors import show_basic_colors
            
            # Show the basic colors window
            show_basic_colors()
            
        except ImportError as e:
            messagebox.showerror("Error", f"Could not import basic_colors module: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open basic colors: {e}")
    
    def use_existing_image(self):
        """Allow user to select an existing calibration image."""
        file_path = filedialog.askopenfilename(
            title="Select Calibration Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.reference_image_path = file_path
            self.status_label.configure(text=f"✓ Using image: {os.path.basename(file_path)}")
            self.next_btn.configure(state='normal')
    
    def show_step_3(self):
        """Step 3: Analyze the screenshot."""
        self.current_step = 3
        self.progress['value'] = self.current_step
        self.clear_step_frame()
        
        ttk.Label(self.step_frame, text="Step 3: Analyze Your Screenshot", 
                 font=('Helvetica', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 20))
        
        if not self.reference_image_path:
            ttk.Label(self.step_frame, text="No reference image selected. Please go back and create one.",
                     foreground='red').grid(row=1, column=0, sticky=tk.W)
            self.next_btn.configure(state='disabled')
            return
        
        instructions = """
Now we'll analyze your screenshot to detect real color deviations.

Select your screenshot of external reference colors (from web color generators or other external sources).
        """.strip()
        
        ttk.Label(self.step_frame, text=instructions, wraplength=600).grid(row=1, column=0, sticky=tk.W, pady=(0, 20))
        
        # Analysis options
        analysis_frame = ttk.Frame(self.step_frame)
        analysis_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(analysis_frame, text="📸 Select Screenshot to Analyze",
                  command=self.select_screenshot).pack(fill=tk.X, pady=8)
        
        ttk.Label(analysis_frame, text="Choose your screenshot of external reference colors",
                 foreground='blue', font=('Helvetica', 9)).pack(anchor=tk.W, padx=20)
        
        # Results display
        self.results_text = tk.Text(self.step_frame, height=15, width=80, wrap=tk.WORD)
        self.results_text.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=20)
        self.step_frame.grid_rowconfigure(3, weight=1)
        
        # Scrollbar for results
        scrollbar = ttk.Scrollbar(self.step_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        scrollbar.grid(row=3, column=1, sticky=(tk.N, tk.S))
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        # Update navigation
        self.next_btn.configure(state='disabled')
    
    def select_screenshot(self):
        """Let user select their screenshot for analysis."""
        screenshot_path = filedialog.askopenfilename(
            title="Select Your Screenshot",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if screenshot_path:
            self.analyze_image(screenshot_path)
    
    def analyze_reference_direct(self):
        """Analyze the generated reference image directly."""
        if self.reference_image_path:
            self.analyze_image(self.reference_image_path)
        else:
            messagebox.showwarning("Warning", "No reference image found. Please generate one first.")
    
    def analyze_image(self, image_path):
        """Analyze the selected image for color deviations."""
        try:
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Analyzing image: {os.path.basename(image_path)}\n\n")
            self.results_text.update()
            
            # Actually sample colors from the image
            measured_colors = self._sample_colors_from_calibration_image(image_path)
            
            if not measured_colors:
                self.results_text.insert(tk.END, "ERROR: Could not sample colors from image.\n")
                self.results_text.insert(tk.END, "Make sure the image contains clear red, green, and blue color patches.\n")
                return
            
            # Analyze deviations
            analysis = self.calibrator.analyze_color_deviation(measured_colors)
            
            # Display results in text widget
            self.results_text.insert(tk.END, "=== COLOR ANALYSIS RESULTS ===\n\n")
            
            for color_name, deviation in analysis['deviations'].items():
                self.results_text.insert(tk.END, f"{color_name.upper()} Analysis:\n")
                self.results_text.insert(tk.END, f"  Red deviation: {deviation['red_deviation']:+d}\n")
                self.results_text.insert(tk.END, f"  Green deviation: {deviation['green_deviation']:+d}\n") 
                self.results_text.insert(tk.END, f"  Blue deviation: {deviation['blue_deviation']:+d}\n")
                self.results_text.insert(tk.END, f"  Total deviation: {deviation['total_deviation']}\n\n")
            
            if analysis['avg_deviation']:
                avg = analysis['avg_deviation']
                self.results_text.insert(tk.END, f"Average Channel Deviations:\n")
                self.results_text.insert(tk.END, f"  Red: {avg['red']:+.1f}\n")
                self.results_text.insert(tk.END, f"  Green: {avg['green']:+.1f}\n")
                self.results_text.insert(tk.END, f"  Blue: {avg['blue']:+.1f}\n\n")
            
            if analysis['recommendations']:
                self.results_text.insert(tk.END, "RECOMMENDATIONS:\n")
                for rec in analysis['recommendations']:
                    self.results_text.insert(tk.END, f"• {rec}\n")
                self.results_text.insert(tk.END, "\n")
            
            # Store results
            self.measured_colors = measured_colors
            self.correction_matrix = analysis['correction_matrix']
            
            if self.correction_matrix:
                self.results_text.insert(tk.END, "✓ Correction matrix generated successfully!\n")
                self.results_text.insert(tk.END, "Click 'Next' to apply these corrections to StampZ.\n")
                self.next_btn.configure(state='normal')
            else:
                self.results_text.insert(tk.END, "⚠ Could not generate correction matrix.\n")
                
        except Exception as e:
            self.results_text.insert(tk.END, f"ERROR: {e}\n")
            messagebox.showerror("Analysis Error", f"Failed to analyze image: {e}")
    
    def show_step_4(self):
        """Step 4: Apply corrections and finish."""
        self.current_step = 4
        self.progress['value'] = self.current_step
        self.clear_step_frame()
        
        ttk.Label(self.step_frame, text="Step 4: Apply Color Corrections", 
                 font=('Helvetica', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 20))
        
        if not self.correction_matrix:
            ttk.Label(self.step_frame, text="No correction matrix available. Please complete the analysis first.",
                     foreground='red').grid(row=1, column=0, sticky=tk.W)
            self.next_btn.configure(text="Finish", state='disabled')
            return
        
        # Show correction summary
        summary_frame = ttk.LabelFrame(self.step_frame, text="Correction Summary", padding="10")
        summary_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        
        corrections_text = f"""
Color corrections to be applied:
  Red: {self.correction_matrix['red_correction']:+.1f}
  Green: {self.correction_matrix['green_correction']:+.1f}
  Blue: {self.correction_matrix['blue_correction']:+.1f}

Example corrections:
        """.strip()
        
        ttk.Label(summary_frame, text=corrections_text, font=('Consolas', 10)).pack(anchor=tk.W)
        
        # Show before/after examples
        example_frame = ttk.Frame(summary_frame)
        example_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(example_frame, text="Color", width=8).grid(row=0, column=0, padx=5)
        ttk.Label(example_frame, text="Before", width=12).grid(row=0, column=1, padx=5)
        ttk.Label(example_frame, text="After", width=12).grid(row=0, column=2, padx=5)
        
        for i, (color_name, original) in enumerate(self.measured_colors.items(), 1):
            corrected = self.calibrator.apply_correction(original, self.correction_matrix)
            ttk.Label(example_frame, text=color_name.title()).grid(row=i, column=0, padx=5, sticky=tk.W)
            ttk.Label(example_frame, text=f"{original}", font=('Consolas', 9)).grid(row=i, column=1, padx=5)
            ttk.Label(example_frame, text=f"{corrected}", font=('Consolas', 9)).grid(row=i, column=2, padx=5)
        
        # Application options
        apply_frame = ttk.LabelFrame(self.step_frame, text="Apply Corrections", padding="10")
        apply_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=20)
        
        self.apply_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(apply_frame, text="Apply these corrections to StampZ color analysis",
                       variable=self.apply_var).pack(anchor=tk.W)
        
        ttk.Label(apply_frame, text="When enabled, all future StampZ color measurements will use these corrections.",
                 foreground='gray', font=('Helvetica', 9)).pack(anchor=tk.W, padx=20)
        
        # Save settings option
        self.save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(apply_frame, text="Save calibration settings for future sessions",
                       variable=self.save_var).pack(anchor=tk.W, pady=(10, 0))
        
        ttk.Label(apply_frame, text="Saves the calibration to your StampZ preferences file.",
                 foreground='gray', font=('Helvetica', 9)).pack(anchor=tk.W, padx=20)
        
        # Update navigation
        self.next_btn.configure(text="Apply & Finish", state='normal')
    
    def go_back(self):
        """Go to previous step."""
        if self.current_step > 1:
            if self.current_step == 2:
                self.show_step_1()
            elif self.current_step == 3:
                self.show_step_2()
            elif self.current_step == 4:
                self.show_step_3()
    
    def go_next(self):
        """Go to next step."""
        if self.current_step < self.max_steps:
            if self.current_step == 1:
                self.show_step_2()
            elif self.current_step == 2:
                self.show_step_3()
            elif self.current_step == 3:
                self.show_step_4()
        else:
            # Final step - apply and finish
            self.apply_and_finish()
    
    def apply_and_finish(self):
        """Apply the calibration and close the wizard."""
        try:
            if self.apply_var.get() and self.correction_matrix:
                # Apply to the analyzer
                self.analyzer.color_correction = self.correction_matrix
                
                # Save to preferences if requested
                if self.save_var.get():
                    self.save_calibration_preferences()
                
                messagebox.showinfo("Calibration Complete", 
                                  "Color calibration has been applied successfully!\n\n"
                                  "StampZ will now use these corrections for improved color accuracy.")
            else:
                messagebox.showinfo("Calibration Cancelled", 
                                  "No corrections were applied.")
            
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply calibration: {e}")
    
    def save_calibration_preferences(self):
        """Save calibration settings to preferences file."""
        try:
            # Determine appropriate preferences location based on platform and bundling
            prefs_file = self._get_preferences_file_path()
            
            # Ensure preferences directory exists
            os.makedirs(os.path.dirname(prefs_file), exist_ok=True)
            
            # Load existing preferences
            prefs = {}
            if os.path.exists(prefs_file):
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
            
            # Add calibration data
            prefs['color_calibration'] = {
                'enabled': True,
                'correction_matrix': self.correction_matrix,
                'calibration_date': str(datetime.now()),
                'measured_colors': self.measured_colors
            }
            
            # Save preferences
            with open(prefs_file, 'w') as f:
                json.dump(prefs, f, indent=2)
            
            # Also save as standalone calibration file for the color correction calculator
            self._save_calibration_file()
            
            print(f"Calibration settings saved to {prefs_file}")
            
        except Exception as e:
            print(f"Warning: Could not save calibration preferences: {e}")
    
    def _get_preferences_file_path(self):
        """Get the appropriate preferences file path based on platform and bundling."""
        import sys
        import platform
        
        if hasattr(sys, '_MEIPASS'):
            # Running as bundled executable - use user data directory
            if platform.system() == 'Darwin':  # macOS
                user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ')
            elif platform.system() == 'Windows':
                user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ')
            else:  # Linux
                user_data_dir = os.path.expanduser('~/.local/share/StampZ')
        else:
            # Running from source - use traditional location or create in project directory
            if platform.system() == 'Darwin':  # macOS
                user_data_dir = os.path.expanduser('~/Library/Application Support/StampZ')
            elif platform.system() == 'Windows':
                user_data_dir = os.path.expanduser('~/AppData/Roaming/StampZ')
            else:  # Linux
                user_data_dir = os.path.expanduser('~/.local/share/StampZ')
        
        return os.path.join(user_data_dir, 'preferences.json')
    
    def _save_calibration_file(self):
        """Save calibration as a standalone file for the color correction calculator."""
        try:
            import sys
            
            # Determine where to save the calibration file
            if hasattr(sys, '_MEIPASS'):
                # Running as bundled executable - save next to the executable
                app_dir = os.path.dirname(sys.executable)
            else:
                # Running from source - save in the project root
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            calibration_file = os.path.join(app_dir, 'stampz_calibration.json')
            
            # Create calibration data compatible with the enhanced color_correction_calculator
            calibration_data = {
                'calibration_matrix': {
                    'method': 'wizard_calibration',
                    'created_date': datetime.now().isoformat(),
                    'corrections': self.correction_matrix
                },
                'application': 'StampZ',
                'version': '1.0',
                'wizard_data': {
                    'measured_colors': self.measured_colors,
                    'reference_image': self.reference_image_path
                }
            }
            
            with open(calibration_file, 'w') as f:
                json.dump(calibration_data, f, indent=2)
            
            print(f"Standalone calibration file saved to: {calibration_file}")
            
        except Exception as e:
            print(f"Warning: Could not save standalone calibration file: {e}")
    
    def _sample_colors_from_calibration_image(self, image_path):
        """Sample RGB colors from the calibration target image."""
        try:
            # Use the StampZ image loader which handles color profiles properly
            from utils.image_processor import load_image
            
            # Load the image with proper color profile conversion
            img = load_image(image_path)
            
            width, height = img.size
            
            # Define sampling areas for a 3x2 grid (the calibration target layout)
            # Top row: Red, Green, Blue
            # Bottom row: White, Gray, Black
            
            patch_width = width // 3
            patch_height = height // 2
            
            # Sample from center of each color patch
            samples = {}
            
            # TOP ROW
            # Red patch (top-left)
            red_x = patch_width // 2
            red_y = patch_height // 2
            samples['red'] = img.getpixel((red_x, red_y))
            
            # Green patch (top-center)
            green_x = patch_width + patch_width // 2
            green_y = patch_height // 2
            samples['green'] = img.getpixel((green_x, green_y))
            
            # Blue patch (top-right)
            blue_x = 2 * patch_width + patch_width // 2
            blue_y = patch_height // 2
            samples['blue'] = img.getpixel((blue_x, blue_y))
            
            # BOTTOM ROW  
            # White patch (bottom-left)
            white_x = patch_width // 2
            white_y = patch_height + patch_height // 2
            samples['white'] = img.getpixel((white_x, white_y))
            
            # Gray patch (bottom-center) - using 'gray_50' to match reference_colors key
            gray_x = patch_width + patch_width // 2
            gray_y = patch_height + patch_height // 2
            samples['gray_50'] = img.getpixel((gray_x, gray_y))
            
            # Black patch (bottom-right)
            black_x = 2 * patch_width + patch_width // 2
            black_y = patch_height + patch_height // 2
            samples['black'] = img.getpixel((black_x, black_y))
            
            # Print debug info
            print(f"Sampled colors from {image_path}:")
            print(f"  Red: {samples['red']}")
            print(f"  Green: {samples['green']}")
            print(f"  Blue: {samples['blue']}")
            print(f"  White: {samples['white']}")
            print(f"  Gray: {samples['gray_50']}")
            print(f"  Black: {samples['black']}")
            
            return samples
            
        except Exception as e:
            print(f"Error sampling colors from image: {e}")
            return None
    
    def cancel(self):
        """Cancel the calibration wizard."""
        if messagebox.askquestion("Cancel Calibration", 
                                 "Are you sure you want to cancel the calibration?") == 'yes':
            self.window.destroy()

def show_calibration_wizard(parent=None):
    """Show the calibration wizard."""
    wizard = CalibrationWizard(parent)
    wizard.show()
    return wizard

if __name__ == "__main__":
    # Test the wizard standalone
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    wizard = show_calibration_wizard()
    root.mainloop()
