#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable

class DrawingReturnPage(ttk.Frame):
    def __init__(self, parent, username="User"):
        ttk.Frame.__init__(self, parent)
        self.username = username
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Returns",
            headers=["Drawing ID", "Revision", "Status", "Returned By", "Return Date", "Actions"],
            initial_widths=[180, 90, 130, 200, 180, 150],
            fetch_data_func=self._generate_dummy_data,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search returns...",
            search_keys=["no", "rev", "status", "returned_by"],
            cell_formatters={
                2: self._format_status,
                3: self._format_returned_by
            }
        )
        self.table.data_keys = ["no", "rev", "status", "returned_by", "date"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _format_returned_by(self, val, record):
        return val, "#4f46e5", ("Segoe UI", 9, "italic"), "w"

    def _generate_dummy_data(self):
        base = [
            {"no": "MDI-DRW-101", "rev": "A.0", "status": "RETURNED", "returned_by": "John Doe", "date": "2024-03-01"},
            {"no": "MDI-DRW-105", "rev": "1.2", "status": "RETURNED", "returned_by": "Jane Smith", "date": "2024-03-02"},
            {"no": "ENG-2024-001", "rev": "0",   "status": "RETURNED", "returned_by": "Robert Brown", "date": "2024-03-03"},
        ]
        return base * 5

    def _get_actions(self, record):
        buttons = []
        buttons.append(("Process", "#3b82f6", "white", self._handle_process))
        return buttons

    def _handle_process(self, record):
        drawing_no = record.get("no")
        messagebox.showinfo("Success", "Drawing %s return processed." % drawing_no)
        self.table.data = [d for d in self.table.data if d["no"] != drawing_no]
        self.table._apply_search()

    def refresh(self):
        self.table.refresh()
