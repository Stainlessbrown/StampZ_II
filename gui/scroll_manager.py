#!/usr/bin/env python3
"""
ScrollManager for Color Library
Handles scrolling functionality for large color lists
"""

import tkinter as tk
from tkinter import ttk

class ScrollManager:
    """Manages scrollable content display for the color library."""
    
    def __init__(self, parent_frame: ttk.Frame):
        """Initialize the scroll manager.
        
        Args:
            parent_frame: Parent frame to contain the scrollable content
        """
        self.parent = parent_frame
        
        # Create scrollbar first
        self.scrollbar = ttk.Scrollbar(self.parent, orient='vertical')
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure scrollbar
        self.scrollbar.lift()
        
        # Create canvas with initial height
        self.canvas = tk.Canvas(self.parent, bg='white', height=400)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure parent frame
        self.parent.rowconfigure(0, weight=1)
        self.parent.columnconfigure(0, weight=1)
        
        # Create the frame that will hold the content
        self.scroll_frame = ttk.Frame(self.canvas)
        
        # Create the window that will hold the frame
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scroll_frame,
            anchor='nw'
        )
        
        # Configure frame to expand horizontally
        self.scroll_frame.columnconfigure(0, weight=1)
        
        # Configure scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.canvas.yview)
        
        # Make sure scrollbar is active and visible
        self.scrollbar.lift()
        
        # Configure frame expansion
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        
        # Bind events
        self._bind_events()
    
    def _bind_events(self):
        """Set up all necessary event bindings."""
        # Update scroll region when frame changes
        self.scroll_frame.bind('<Configure>', self._on_frame_configure)
        
        # Update frame width when canvas changes
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel scrolling for all platforms
        self.canvas.bind('<Enter>', lambda e: self.canvas.focus_set())
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)        # Windows
        self.canvas.bind('<Button-4>', self._on_mousewheel)         # Linux up
        self.canvas.bind('<Button-5>', self._on_mousewheel)         # Linux down
        self.canvas.bind('<Button-2>', self._on_mousewheel)         # Mac
        self.canvas.bind('<Motion>', lambda e: self.canvas.focus_set())  # Focus on mouse move
        
        # Bind to parent and all child widgets
        def bind_recursive(widget):
            widget.bind('<MouseWheel>', self._on_mousewheel)
            widget.bind('<Button-4>', self._on_mousewheel)
            widget.bind('<Button-5>', self._on_mousewheel)
            widget.bind('<Button-2>', self._on_mousewheel)
            for child in widget.winfo_children():
                bind_recursive(child)
        
        bind_recursive(self.scroll_frame)
        
        # Keyboard navigation
        self.canvas.bind('<Prior>', lambda e: self._on_page_navigation(-1))  # Page Up
        self.canvas.bind('<Next>', lambda e: self._on_page_navigation(1))    # Page Down
        self.canvas.bind('<Home>', lambda e: self.canvas.yview_moveto(0))
        self.canvas.bind('<End>', lambda e: self.canvas.yview_moveto(1))
    
    def _on_frame_configure(self, event=None):
        """Update scroll region when the frame size changes."""
        # Update the scroll region to encompass all content
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.update_idletasks()  # Force update
    
    def _on_canvas_configure(self, event):
        """Update frame width when canvas size changes."""
        if event.width > 1:  # Ensure valid width
            # Update the frame's width to match canvas
            self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling for all platforms."""
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self.canvas.yview_scroll(-3, "units")  # Scroll up faster
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            self.canvas.yview_scroll(3, "units")   # Scroll down faster
        
        # Ensure scroll region is up to date
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        return "break"  # Prevent event propagation
    
    def _on_page_navigation(self, direction):
        """Handle page up/down navigation."""
        self.canvas.yview_scroll(direction, "pages")
    
    def clear_content(self):
        """Clear all content from the scroll frame."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
    
    def reset_scroll(self):
        """Reset scroll position to top."""
        self.canvas.yview_moveto(0)
    
    def update_scroll_region(self):
        """Update the scroll region to match content."""
        # Force update to get accurate sizes
        self.scroll_frame.update_idletasks()
        
        # Calculate total size needed for all content
        bbox = self.canvas.bbox("all")
        if bbox:
            total_height = bbox[3] - bbox[1]  # height from bbox
            max_width = bbox[2] - bbox[0]    # width from bbox
        else:
            total_height = self.scroll_frame.winfo_reqheight()
            max_width = self.scroll_frame.winfo_reqwidth()
        
        # Add padding for bottom margin
        total_height += 50
        
        # Get current canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Ensure minimum dimensions
        scroll_width = max(max_width + 20, canvas_width)  # Add padding
        scroll_height = max(total_height, canvas_height)  # Ensure enough scroll space
        
        # Update scroll region
        self.canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))
        
        # Update canvas window width
        self.canvas.itemconfig(self.canvas_window, width=scroll_width)
        
        # Force update
        self.canvas.update_idletasks()
        
        # Make sure scrollbar is visible if needed
        if total_height > canvas_height:
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Print debug info
        print(f"DEBUG: Scroll region updated - Width: {scroll_width}, Height: {scroll_height}")
        print(f"DEBUG: Total content height: {total_height}")
        print(f"DEBUG: Canvas height: {canvas_height}")
        print(f"DEBUG: Number of items: {len(self.scroll_frame.winfo_children())}")
    
    @property
    def content_frame(self) -> ttk.Frame:
        """Get the frame where content should be added."""
        return self.scroll_frame
