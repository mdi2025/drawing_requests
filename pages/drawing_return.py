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
            headers=["SNo", "Drawing ID", "Revision", "Status", "Issue Date", "Action"],
            initial_widths=[80, 200, 100, 140, 250, 140],
            fetch_data_func=self._fetch_issued_drawings,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search issued drawings...",
            search_keys=["no", "rev", "status"],
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
                    r.drawing_id AS no,
                    r.revision AS rev,
                    r.status,
                    DATE_FORMAT(h_iss.performed_at, '%%d-%%m-%%Y %%H:%%i') AS issue_date,
                    (SELECT CONCAT(u_ret.admin_name, ' at ', DATE_FORMAT(h_ret.performed_at, '%%d-%%m-%%Y %%H:%%i'))
                     FROM drawing_request_history h_ret
                     JOIN drawing_users u_ret ON h_ret.performed_by = u_ret.id
                     WHERE h_ret.request_id = r.id AND h_ret.event_type = 'returned'
                     LIMIT 1) AS returned_info
                FROM drawing_requests r
                LEFT JOIN drawing_request_history h_iss ON r.id = h_iss.request_id AND h_iss.event_type = 'issued'
                WHERE r.status IN ('Issued', 'Returned') AND r.requested_by = %s
                ORDER BY r.id DESC
            """
            rows = db.fetch_all(query, (self.user_id,))
            return rows
        except Exception as e:
            print("Error fetching issued drawings: {}".format(e))
            return []

    def _get_actions(self, record):
        status = record.get("status")
        if status == 'Issued':
            buttons = []
            buttons.append(("Return", styles.PRIMARY, "white", self._handle_return))
            return buttons
        elif status == 'Returned':
            info = record.get("returned_info", "Returned")
            if info and info != "Returned": info = "Returned by " + info
            return (info, "#4f46e5", ("Segoe UI", 9, "italic"), "center")
        return []

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

            messagebox.showinfo("Success", "Drawing %s has been returned successfully." % drawing_no)
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to update return status in database.")

    def refresh(self, reset_pagination=True, silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent)
