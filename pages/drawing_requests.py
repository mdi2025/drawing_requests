#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import datetime
import threading
from pages.table_component import CanvasDataTable
import styles
from db_handler import db


class DrawingRequestsPage(ttk.Frame):

    def __init__(self, parent, username="User", user_id=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id

        # Initialize the reusable table component
        self.table = CanvasDataTable(
            self,
            title="Drawing Requisitions",
            headers=["Auto ID", "Drawing ID", "Revision", "Status", "Requested By", "Action"],
            initial_widths=[100, 200, 100, 140, 300, 140],
            fetch_data_func=self._fetch_drawings,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search drawings...",
            search_keys=["id", "no", "rev", "status", "requested_by"],
            cell_formatters={
                3: self._format_status,
                4: self._format_requested_by
            }
        )

        self.table.data_keys = ["id", "no", "rev", "status", "requested_by"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    # ------------------------------
    # Formatters
    # ------------------------------

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _format_requested_by(self, val, record):
        fg = "#4f46e5" if val else "#1f2937"
        return val, fg, ("Segoe UI", 9, "italic"), "w"

    # ------------------------------
    # Fetch Data
    # ------------------------------

    def _fetch_drawings(self):
        try:

            query = """
                SELECT 
                    m.auto_id AS id,
                    m.catalog AS no,
                    m.revision AS rev,
                    m.approved_status AS status,
                    (SELECT CONCAT(u.admin_name, ' at ', DATE_FORMAT(r.request_timestamp, '%d-%m-%Y %H:%i'))
                     FROM drawing_requests r
                     JOIN drawing_users u ON r.user_id = u.id
                     WHERE r.drawing_ref_id = m.auto_id 
                     LIMIT 1) AS requested_by
                FROM master_data_new m
                WHERE m.approved_status = 'Approved'
            """

            rows = db.fetch_all(query)
            return rows

        except Exception as e:
            print("Error fetching drawings: {}".format(e))
            return []

    # ------------------------------
    # Action Buttons
    # ------------------------------

    def _get_actions(self, drawing):
        buttons = []

        if not drawing.get("requested_by"):
            buttons.append(
                ("Request", styles.PRIMARY, "white", self._request_drawing)
            )
        else:
            buttons.append(
                ("Requested", "#e2e8f0", "#6b7280", None)
            )

        return buttons

    # ------------------------------
    # Request Drawing
    # ------------------------------

    def _request_drawing(self, drawing):

        drawing_id = drawing.get("id")
        drawing_no = drawing.get("no")

        confirm = messagebox.askyesno(
            "Confirm Request",
            "Request drawing Auto ID %s (Drawing No: %s)?" % (drawing_id, drawing_no)
        )

        if not confirm:
            return

        if not self.user_id:
            messagebox.showerror("Error", "User session not found. Please log in again.")
            return

        # Double check if already requested in DB to avoid race conditions
        # Enhanced check query to see WHO requested it
        check_query = """
            SELECT u.admin_name, DATE_FORMAT(r.request_timestamp, '%%d-%%m-%%Y %%H:%%i') as ts
            FROM drawing_requests r
            JOIN drawing_users u ON r.user_id = u.id
            WHERE r.drawing_ref_id = %s
        """
        existing = db.fetch_all(check_query, (drawing_id,))
        if existing:
            # Refresh first so UI is correct behind the dialog
            self.refresh(reset_pagination=False)
            
            info = existing[0]
            messagebox.showwarning("Already Requested", 
                "This drawing has already been requested by %s at %s." % (info['admin_name'], info['ts']))
            return

        # Save to database
        insert_query = "INSERT INTO drawing_requests (drawing_ref_id, user_id) VALUES (%s, %s)"
        if db.execute_query(insert_query, (drawing_id, self.user_id)):
            # Update local state for instant feedback
            now_str = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
            drawing["requested_by"] = "%s at %s" % (self.username, now_str)
            self.table._redraw_table()
            
            messagebox.showinfo(
                "Success",
                "Request submitted for Auto ID %s" % drawing_id
            )
        else:
            messagebox.showerror("Error", "Failed to submit request to database.")

    # ------------------------------
    # Refresh Table
    # ------------------------------

    def refresh(self, reset_pagination=True, silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent)