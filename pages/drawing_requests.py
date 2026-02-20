#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import datetime
import threading
from pages.table_component import CanvasDataTable
import styles

class DrawingRequestsPage(ttk.Frame):
    def __init__(self, parent, username="User"):
        ttk.Frame.__init__(self, parent)
        self.username = username
        
        # Initialize the reusable table component
        self.table = CanvasDataTable(
            self,
            title="Drawing Requisitions",
            headers=["Drawing ID", "Revision", "Status", "Requested By", "Action"],
            initial_widths=[200, 100, 140, 300, 140],
            fetch_data_func=self._fetch_drawings,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search drawings...",
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
        fg = "#4f46e5" if val else "#1f2937"
        return val, fg, ("Segoe UI", 9, "italic"), "w"

    def _fetch_drawings(self):
        try:
            import sys, os
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from db_handler import db

            query = """
                SELECT drawing_no as no,
                       latest_revision as rev,
                       current_status as status
                FROM drawings_master_bal
                WHERE current_status = 'Approved'
                LIMIT 200
            """
            rows = db.fetch_all(query) or []
            for row in rows:
                row['requested_by'] = ""
            return rows
        except Exception as e:
            print("Error fetching drawings: {}".format(e))
            return []

    def _get_actions(self, drawing):
        buttons = []
        if not drawing.get("requested_by"):
            buttons.append(("Request", styles.PRIMARY, "white", self._request_drawing))
        else:
            buttons.append(("Requested", "#e2e8f0", "#6b7280", None))
        return buttons

    def _request_drawing(self, drawing):
        drawing_no = drawing.get("no")
        confirm = messagebox.askyesno("Confirm Request",
                                      "Request drawing no %s?" % drawing_no)
        if not confirm: return
        
        now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        requested_text = "%s at %s" % (self.username, now)
        
        # Update local data
        for d in self.table.data:
            if d.get("no") == drawing_no:
                d["requested_by"] = requested_text
                break
        
        self.table._apply_search()
        messagebox.showinfo("Success", "Request submitted for %s" % drawing_no)

    def refresh(self):
        self.table.refresh()