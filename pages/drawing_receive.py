#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable

class DrawingReceivePage(ttk.Frame):
    def __init__(self, parent, username="User"):
        ttk.Frame.__init__(self, parent)
        self.username = username
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Receipts",
            headers=["Drawing ID", "Revision", "Status", "Received From", "Source", "Actions"],
            initial_widths=[180, 90, 130, 200, 180, 150],
            fetch_data_func=self._generate_dummy_data,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search receipts...",
            search_keys=["no", "rev", "status", "received_from"],
            cell_formatters={
                2: self._format_status,
                3: self._format_received_from
            }
        )
        self.table.data_keys = ["no", "rev", "status", "received_from", "source"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _format_received_from(self, val, record):
        return val, "#4f46e5", ("Segoe UI", 9, "italic"), "w"

    def _generate_dummy_data(self):
        base = [
            {"no": "MDI-DRW-201", "rev": "0", "status": "RECEIVED", "received_from": "Vendor A", "source": "Incoming Shipment"},
            {"no": "MDI-DRW-202", "rev": "1", "status": "RECEIVED", "received_from": "Dept X", "source": "Internal Transfer"},
            {"no": "ENG-2024-501", "rev": "A", "status": "RECEIVED", "received_from": "Designer Y", "source": "New Upload"},
        ]
        return base * 5

    def _get_actions(self, record):
        buttons = []
        buttons.append(("Acknowledge", "#10b981", "white", self._handle_acknowledge))
        return buttons

    def _handle_acknowledge(self, record):
        drawing_no = record.get("no")
        messagebox.showinfo("Success", "Drawing %s receipt acknowledged." % drawing_no)
        self.table.data = [d for d in self.table.data if d["no"] != drawing_no]
        self.table._apply_search()

    def refresh(self):
        self.table.refresh()
