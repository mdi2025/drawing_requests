#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable
from db_handler import db

class DrawingReceivePage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Receive",
            headers=["Auto ID", "Drawing ID", "Revision", "Status", "Returned By", "Return Date", "Actions"],
            initial_widths=[100, 180, 90, 130, 200, 250, 150],
            fetch_data_func=self._fetch_returned_drawings,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search receipts...",
            search_keys=["id", "no", "rev", "status", "returned_by"],
            cell_formatters={
                3: self._format_status,
                4: self._format_returned_by
            }
        )
        self.table.data_keys = ["id", "no", "rev", "status", "returned_by", "return_date"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _format_returned_by(self, val, record):
        return val, "#4f46e5", ("Segoe UI", 9, "italic"), "w"

    def _fetch_returned_drawings(self):
        try:
            query = """
                SELECT 
                    r.id,
                    m.catalog AS no,
                    m.revision AS rev,
                    r.status,
                    u.admin_name AS returned_by,
                    DATE_FORMAT(r.requested_at, '%d-%m-%Y %H:%i') AS return_date
                FROM drawing_requests r
                JOIN master_data_new m ON r.auto_id = m.auto_id
                JOIN drawing_users u ON r.requested_by = u.id
                WHERE r.status = 'Returned'
                ORDER BY r.requested_at DESC
            """
            rows = db.fetch_all(query)
            return rows
        except Exception as e:
            print("Error fetching returned drawings: {}".format(e))
            return []

    def _get_actions(self, record):
        buttons = []
        buttons.append(("Receive", "#10b981", "white", self._handle_receive))
        return buttons

    def _handle_receive(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")
        
        if not messagebox.askyesno("Confirm Receive", "Are you sure you want to receive Drawing %s?" % drawing_no):
            return

        # Log to history BEFORE deleting the request
        insert_history = """
            INSERT INTO drawing_request_history 
            (request_id, event_type, performed_by, remarks) 
            VALUES (%s, 'received', %s, 'Drawing received')
        """
        db.execute_query(insert_history, (request_id, self.user_id or 1))

        # Complete the lifecycle by removing the request record
        query = "DELETE FROM drawing_requests WHERE id = %s"
        if db.execute_query(query, (request_id,)):
            # Instant UI feedback
            self.table.data = [d for d in self.table.data if d["id"] != request_id]
            self.table._apply_search(reset_pagination=False)
            
            messagebox.showinfo("Success", "Drawing %s has been received successfully." % drawing_no)
        else:
            messagebox.showerror("Error", "Failed to receive drawing from database.")

    def refresh(self, reset_pagination=True, silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent)
