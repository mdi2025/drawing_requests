#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tkinter import ttk

class PlaceholderPage(ttk.Frame):
    def __init__(self, parent, title):
        ttk.Frame.__init__(self, parent, style="Card.TFrame", padding=25)
        
        ttk.Label(self, text=title, style="Title.TLabel").pack(pady=30)

class IssuancePage(PlaceholderPage):
    def __init__(self, parent):
        PlaceholderPage.__init__(self, parent, "Drawing Issuance Page")

class ReturnPage(PlaceholderPage):
    def __init__(self, parent):
        PlaceholderPage.__init__(self, parent, "Return Page")

class ReportsPage(PlaceholderPage):
    def __init__(self, parent):
        PlaceholderPage.__init__(self, parent, "Reports Page")
