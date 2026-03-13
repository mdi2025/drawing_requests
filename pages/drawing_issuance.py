#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable
from db_handler import db

class DrawingIssuancePage(ttk.Frame):
    def __init__(self, parent, username="User"):
        ttk.Frame.__init__(self, parent)
        self.username = username
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Issuance",
            headers=["Auto ID", "Drawing ID", "Revision", "Status", "Requested By", "Actions"],
            initial_widths=[100, 180, 90, 130, 280, 180],
            fetch_data_func=self._fetch_requests,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search requests...",
            search_keys=["drawing_ref_id", "no", "rev", "status", "requested_by"],
            cell_formatters={
                3: self._format_status,
                4: self._format_requested_by
            }
        )
        self.table.data_keys = ["drawing_ref_id", "no", "rev", "status", "requested_by", "request_id"]
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
                    r.request_id,
                    r.drawing_ref_id,
                    m.catalog AS no,
                    m.revision AS rev,
                    r.status,
                    CONCAT(u.admin_name, ' at ', DATE_FORMAT(r.request_timestamp, '%d-%m-%Y %H:%i')) AS requested_by
                FROM drawing_requests r
                JOIN master_data_new m ON r.drawing_ref_id = m.auto_id
                JOIN drawing_users u ON r.user_id = u.id
                WHERE r.status = 'Pending'
                LIMIT 500
            """
            rows = db.fetch_all(query)
            return rows
        except Exception as e:
            print("Error fetching requests: {}".format(e))
            return []

    def _get_actions(self, record):
        buttons = []
        buttons.append(("Issue", "#10b981", "white", self._handle_issue))
        buttons.append(("Reject", "#ef4444", "white", self._handle_reject))
        return buttons

    def _handle_issue(self, record):
        request_id = record.get("request_id")
        drawing_no = record.get("no")
        
        query = "UPDATE drawing_requests SET status = 'Issued' WHERE request_id = %s"
        if db.execute_query(query, (request_id,)):
            messagebox.showinfo("Issuance", "Drawing %s has been issued successfully." % drawing_no)
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to update status in database.")

    def _handle_reject(self, record):
        request_id = record.get("request_id")
        drawing_no = record.get("no")
        
        if messagebox.askyesno("Reject", "Are you sure you want to reject the request for %s?" % drawing_no):
            # For rejection, we could either delete the record or set a 'Rejected' status.
            # However, the enum only has 'Pending','Issued','Returned'.
            # If we delete it, it can be requested again. If we want to block, we need a Rejected status.
            # Since the user didn't specify, I will delete it so it can be requested again or fix the request.
            query = "DELETE FROM drawing_requests WHERE request_id = %s"
            if db.execute_query(query, (request_id,)):
                messagebox.showinfo("Rejected", "Request for %s has been removed." % drawing_no)
                self.refresh(reset_pagination=False)
            else:
                messagebox.showerror("Error", "Failed to remove request from database.")

    def refresh(self, reset_pagination=True, silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent)