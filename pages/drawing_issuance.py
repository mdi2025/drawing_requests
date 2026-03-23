#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable
from db_handler import db

class DrawingIssuancePage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None, on_data_ready=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Issuance",
            headers=["SNo", "Drawing ID", "Revision", "Requested By", "Status", "Actions"],
            initial_widths=[80, 150, 80, 250, 120, 300],
            fetch_data_func=self._fetch_requests,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search requests...",
            search_keys=["no", "rev", "status", "requested_by", "issued_info", "rejected_info"],
            cell_formatters={
                3: self._format_requested_by,
                4: self._format_status
            },
            on_data_ready_callback=on_data_ready
        )
        self.table.data_keys = ["id", "no", "rev", "requested_by", "status"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        s = str(val).lower()
        if s == "rejected": color = "#ef4444"
        elif s == "issued": color = "#008000"
        else: color = "#1f2937"
        return str(val).upper(), color, ("Segoe UI", 10), "center"

    def _format_requested_by(self, val, record):
        return val, "#1f2937", ("Segoe UI", 10), "w"

    def _fetch_requests(self):
        try:

            query = """
                SELECT 
                    r.id,
                    r.drawing_id AS no,
                    r.revision AS rev,
                    r.status,
                    CONCAT(u_req.admin_name, ' at ', DATE_FORMAT(h_req.performed_at, '%d-%m-%Y %H:%i:%s')) AS requested_by,
                    CONCAT(u_iss.admin_name, ' at ', DATE_FORMAT(h_iss.performed_at, '%d-%m-%Y %H:%i:%s')) AS issued_info,
                    CONCAT(u_rej.admin_name, ' at ', DATE_FORMAT(h_rej.performed_at, '%d-%m-%Y %H:%i:%s')) AS rejected_info
                FROM drawing_requests r
                JOIN drawing_request_history h_req ON r.id = h_req.request_id AND h_req.event_type = 'requested'
                JOIN drawing_users u_req ON h_req.performed_by = u_req.id
                LEFT JOIN drawing_request_history h_iss ON r.id = h_iss.request_id AND h_iss.event_type = 'issued'
                LEFT JOIN drawing_users u_iss ON h_iss.performed_by = u_iss.id
                LEFT JOIN drawing_request_history h_rej ON r.id = h_rej.request_id AND h_rej.event_type = 'rejected'
                LEFT JOIN drawing_users u_rej ON h_rej.performed_by = u_rej.id
                WHERE r.status IN ('Pending', 'open', 'Issued', 'Rejected', 'Returned')
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
  
        elif status == 'Rejected':
            info = record.get("rejected_info", "Rejected")
            if info and info != "Rejected": info = "Rejected by " + info
            return (info, "#ef4444", ("Segoe UI", 9, "italic"), "center")
        else :
            info = record.get("issued_info", "Issued")
            if info and info != "Issued": info = "Issued by " + info
            return (info, "#008000", ("Segoe UI", 9, "italic"), "center")
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
                (request_id, event_type, performed_by) 
                VALUES (%s, 'issued', %s)
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
                (request_id, event_type, performed_by) 
                VALUES (%s, 'rejected', %s)
            """
            db.execute_query(insert_history, (request_id, self.user_id or 1))

            messagebox.showinfo("Rejected", "Request for %s has been rejected." % drawing_no)
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to update status in database.")

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent, button_silent=button_silent)