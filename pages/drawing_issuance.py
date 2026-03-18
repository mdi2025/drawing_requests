#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable
from db_handler import db

class DrawingIssuancePage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Issuance",
            headers=["Auto ID", "Drawing ID", "Revision", "Requested By", "Status", "Actions"],
            initial_widths=[100, 150, 80, 250, 120, 300],
            fetch_data_func=self._fetch_requests,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search requests...",
            search_keys=["auto_id", "no", "rev", "status", "requested_by", "issued_info", "rejected_info"],
            cell_formatters={
                3: self._format_requested_by,
                4: self._format_status
            }
        )
        self.table.data_keys = ["auto_id", "no", "rev", "requested_by", "status", "id"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _format_requested_by(self, val, record):
        return val, "#4f46e5", ("Segoe UI", 9, "italic"), "w"

    def _fetch_requests(self):
        try:

            query = """
                SELECT 
                    r.id,
                    r.auto_id,
                    m.catalog AS no,
                    m.revision AS rev,
                    r.status,
                    CONCAT(u_req.admin_name, ' at ', DATE_FORMAT(h_req.performed_at, '%d-%m-%Y %H:%i')) AS requested_by,
                    (SELECT CONCAT(u_iss.admin_name, ' at ', DATE_FORMAT(h_iss.performed_at, '%d-%m-%Y %H:%i'))
                     FROM drawing_request_history h_iss
                     JOIN drawing_users u_iss ON h_iss.performed_by = u_iss.id
                     WHERE h_iss.request_id = r.id AND h_iss.event_type = 'issued'
                     LIMIT 1) AS issued_info,
                    (SELECT CONCAT(u_rej.admin_name, ' at ', DATE_FORMAT(h_rej.performed_at, '%d-%m-%Y %H:%i'))
                     FROM drawing_request_history h_rej
                     JOIN drawing_users u_rej ON h_rej.performed_by = u_rej.id
                     WHERE h_rej.request_id = r.id AND h_rej.event_type = 'rejected'
                     LIMIT 1) AS rejected_info
                FROM drawing_requests r
                JOIN master_data_new m ON r.auto_id = m.auto_id
                JOIN drawing_request_history h_req ON r.id = h_req.request_id AND h_req.event_type = 'requested'
                JOIN drawing_users u_req ON h_req.performed_by = u_req.id
                WHERE r.status IN ('Pending', 'open', 'Issued', 'Rejected')
                ORDER BY r.id DESC
                LIMIT 500
            """
            rows = db.fetch_all(query)
            return rows
        except Exception as e:
            print("Error fetching requests: {}".format(e))
            return []

    def _get_actions(self, record):
        status = record.get("status")
        if status in ('Pending', 'open'):
            buttons = []
            buttons.append(("Issue", "#10b981", "white", self._handle_issue))
            buttons.append(("Reject", "#ef4444", "white", self._handle_reject))
            return buttons
        elif status == 'Issued':
            info = record.get("issued_info", "Issued")
            return (info, "#4f46e5", ("Segoe UI", 9, "italic"), "w")
        elif status == 'Rejected':
            info = record.get("rejected_info", "Rejected")
            return (info, "#4f46e5", ("Segoe UI", 9, "italic"), "w")
        return []

    def _handle_issue(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")
        
        if not messagebox.askyesno("Confirm Issue", "Are you sure you want to issue drawing %s?" % drawing_no):
            return

        query = "UPDATE drawing_requests SET status = 'Issued' WHERE id = %s"
        if db.execute_query(query, (request_id,)):
            # Log to history
            insert_history = """
                INSERT INTO drawing_request_history 
                (request_id, event_type, performed_by, remarks) 
                VALUES (%s, 'issued', %s, 'Drawing issued')
            """
            db.execute_query(insert_history, (request_id, self.user_id or 1))

            messagebox.showinfo("Issuance", "Drawing %s has been issued successfully." % drawing_no)
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to update status in database.")

    def _handle_reject(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")
        
        if not messagebox.askyesno("Reject", "Are you sure you want to reject the request for %s?" % drawing_no):
            return

        query = "UPDATE drawing_requests SET status = 'Rejected' WHERE id = %s"
        if db.execute_query(query, (request_id,)):
            # Log to history
            insert_history = """
                INSERT INTO drawing_request_history 
                (request_id, event_type, performed_by, remarks) 
                VALUES (%s, 'rejected', %s, 'Request rejected')
            """
            db.execute_query(insert_history, (request_id, self.user_id or 1))

            messagebox.showinfo("Rejected", "Request for %s has been rejected." % drawing_no)
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to update status in database.")

    def refresh(self, reset_pagination=True, silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent)