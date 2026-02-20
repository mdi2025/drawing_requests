#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable

class DrawingIssuancePage(ttk.Frame):
    def __init__(self, parent, username="User"):
        ttk.Frame.__init__(self, parent)
        self.username = username
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Issuance",
            headers=["Drawing ID", "Revision", "Status", "Requested By", "Actions"],
            initial_widths=[180, 90, 130, 280, 200],
            fetch_data_func=self._generate_static_data,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search requests...",
            search_keys=["no", "rev", "status", "requested_by"],
            cell_formatters={
                2: self._format_status,
                3: self._format_requested_by
            }
        )
        self.table.data_keys = ["no", "rev", "status", "requested_by"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _format_requested_by(self, val, record):
        return val, "#4f46e5", ("Segoe UI", 9, "italic"), "w"

    def _generate_static_data(self):
        base = [
            {"no": "MDI-DRW-101", "rev": "A.0", "status": "REQUESTED", "requested_by": "John Doe"},
            {"no": "MDI-DRW-105", "rev": "1.2", "status": "REQUESTED", "requested_by": "Jane Smith"},
            {"no": "ENG-2024-001", "rev": "0",   "status": "REQUESTED", "requested_by": "Robert Brown"},
            {"no": "ENG-2024-002", "rev": "0",   "status": "REQUESTED", "requested_by": "Sarah Wilson"},
            {"no": "ST-9982-X",    "rev": "B",   "status": "REQUESTED", "requested_by": "Michael Scott"},
        ]
        return base * 8

    def _get_actions(self, record):
        buttons = []
        buttons.append(("Issue", "#10b981", "white", self._handle_issue))
        buttons.append(("Reject", "#ef4444", "white", self._handle_reject))
        return buttons

    def _handle_issue(self, record):
        drawing_no = record.get("no")
        messagebox.showinfo("Issuance", "Drawing %s has been issued successfully." % drawing_no)
        self.table.data = [d for d in self.table.data if d["no"] != drawing_no]
        self.table._apply_search()

    def _handle_reject(self, record):
        drawing_no = record.get("no")
        if messagebox.askyesno("Reject", "Are you sure you want to reject the request for %s?" % drawing_no):
            messagebox.showwarning("Rejected", "Request for %s rejected." % drawing_no)
            self.table.data = [d for d in self.table.data if d["no"] != drawing_no]
            self.table._apply_search()

    def refresh(self):
        self.table.refresh()