#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable
from db_handler import db

class DrawingReturnPage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Return",
            headers=["Auto ID", "Drawing ID", "Revision", "Status", "Issue Date", "Action"],
            initial_widths=[100, 200, 100, 140, 250, 140],
            fetch_data_func=self._fetch_issued_drawings,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search issued drawings...",
            search_keys=["id", "no", "rev", "status"],
            cell_formatters={
                3: self._format_status
            }
        )
        self.table.data_keys = ["id", "no", "rev", "status", "issue_date"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _fetch_issued_drawings(self):
        try:
            if not self.user_id:
                return []

            query = """
                SELECT 
                    r.id,
                    m.catalog AS no,
                    m.revision AS rev,
                    r.status,
                    DATE_FORMAT(h.performed_at, '%%d-%%m-%%Y %%H:%%i') AS issue_date
                FROM drawing_requests r
                JOIN master_data_new m ON r.auto_id = m.auto_id
                LEFT JOIN drawing_request_history h ON r.id = h.request_id AND h.event_type = 'issued'
                WHERE r.status = 'Issued' AND r.requested_by = %s
                ORDER BY h.performed_at DESC
            """
            rows = db.fetch_all(query, (self.user_id,))
            return rows
        except Exception as e:
            print("Error fetching issued drawings: {}".format(e))
            return []

    def _get_actions(self, record):
        buttons = []
        buttons.append(("Return", styles.PRIMARY, "white", self._handle_return))
        return buttons

    def _handle_return(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")
        
        if not messagebox.askyesno("Confirm Return", "Are you sure you want to return Drawing %s?" % drawing_no):
            return

        query = "UPDATE drawing_requests SET status = 'Returned' WHERE id = %s"
        if db.execute_query(query, (request_id,)):
            # Log to history
            insert_history = """
                INSERT INTO drawing_request_history 
                (request_id, event_type, performed_by, remarks) 
                VALUES (%s, 'returned', %s, 'Drawing returned')
            """
            db.execute_query(insert_history, (request_id, self.user_id or 1))

            # Instant UI feedback: remove from current list
            self.table.data = [d for d in self.table.data if d["id"] != request_id]
            self.table._apply_search(reset_pagination=False)
            
            messagebox.showinfo("Success", "Drawing %s has been returned successfully." % drawing_no)
        else:
            messagebox.showerror("Error", "Failed to update return status in database.")

    def refresh(self, reset_pagination=True, silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent)
