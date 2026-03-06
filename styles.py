#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tkinter import ttk

PRIMARY = "#3b82f6"  # Standard Blue
SECONDARY = "#64748b" # Slate
DARK = "#334155"     # Slate Dark
LIGHT = "#f1f5f9"    # Light Grey-Blue
GRAY_TEXT = "#64748b"

def apply_styles():
    style = ttk.Style()
    style.theme_use("clam")

    # Frame styles
    style.configure("TFrame", background=LIGHT)
    style.configure("Card.TFrame", background="white", borderwidth=0, relief="flat")
    style.configure("Sidebar.TFrame", background=DARK)
    
    # Label styles
    style.configure("TLabel", background=LIGHT, foreground=DARK, font=("Segoe UI", 10))
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground=DARK)
    style.configure("LoginTitle.TLabel", font=("Segoe UI", 24, "bold"), foreground=DARK, background="white")
    style.configure("LoginSubtitle.TLabel", font=("Segoe UI", 11), foreground=GRAY_TEXT, background="white")

    # Button styles
    style.configure("Primary.TButton",
        font=("Segoe UI", 10, "bold"),
        background=PRIMARY,
        foreground="white",
        relief="flat",
        padding=(20, 10)
    )
    style.map("Primary.TButton", background=[("active", "#2563eb")])

    style.configure("Success.TButton",
        font=("Segoe UI", 9, "bold"),
        background="#10b981",
        foreground="white",
        padding=(12, 6)
    )
    style.map("Success.TButton", background=[("active", "#059669")])

    # Premium Action Button (Indigo/Royal)
    style.configure("Action.TButton",
        font=("Segoe UI", 9, "bold"),
        background="#4f46e5",
        foreground="white",
        padding=(15, 8),
        relief="flat"
    )
    style.map("Action.TButton", background=[("active", "#4338ca")])

    style.configure("Flat.TButton",
        font=("Segoe UI", 10),
        background=PRIMARY,
        foreground="white",
        relief="flat",
        borderwidth=0,
        padding=(10, 6)
    )
    style.map("Flat.TButton", background=[("active", "#2563eb")])

    # Danger Button (Red)
    style.configure("Danger.TButton",
        font=("Segoe UI", 9, "bold"),
        background="#dc2626",
        foreground="white",
        padding=(10, 6),
        relief="flat"
    )
    style.map("Danger.TButton", background=[("active", "#b91c1c")])

    # Treeview styles (Traditional Heading)
    style.configure("Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        background="#e5e7eb",
        foreground=DARK
    )

import tkinter as tk

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=200, height=40, radius=20, 
                 bg="white", fg="white", btn_bg="#3b82f6", hover_bg="#2563eb"):
        tk.Canvas.__init__(self, parent, borderwidth=0, relief="flat", 
                           highlightthickness=0, bg=bg, width=width, height=height)
        self.command = command
        self.text = text
        self.radius = radius
        self.btn_bg = btn_bg
        self.hover_bg = hover_bg
        self.fg = fg
        self.width = width
        self.height = height

        # Draw initial state
        self._draw(self.btn_bg)
        
        # Bind events
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _draw(self, color):
        self.delete("all")
        r = self.radius
        w = self.width
        h = self.height
        
        # Corners
        self.create_arc((0, 0, 2*r, 2*r), start=90, extent=90, fill=color, outline=color)
        self.create_arc((w-2*r, 0, w, 2*r), start=0, extent=90, fill=color, outline=color)
        self.create_arc((w-2*r, h-2*r, w, h), start=270, extent=90, fill=color, outline=color)
        self.create_arc((0, h-2*r, 2*r, h), start=180, extent=90, fill=color, outline=color)
        
        # Rectangles
        self.create_rectangle((r, 0, w-r, h), fill=color, outline=color)
        self.create_rectangle((0, r, w, h-r), fill=color, outline=color)
        
        # Text
        self.create_text(w/2, h/2, text=self.text, fill=self.fg, 
                         font=("Segoe UI", 10, "bold"))

    def _on_enter(self, e):
        self._draw(self.hover_bg)
        self.config(cursor="hand2")

    def _on_leave(self, e):
        self._draw(self.btn_bg)

    def _on_click(self, e):
        if self.command:
            self.command()
