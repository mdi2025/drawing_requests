#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable
from db_handler import db


class DrawingReceivePage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None, on_data_ready=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id

        self.table = CanvasDataTable(
            self,
            title="Drawing Receive",
            headers=[
                "SNo",
                "Drawing ID",
                "Revision",
                "Bag Name",
                "Catalog",
                "Status",
                "Returned By",
                "Return Date",
                "Actions",
            ],
            initial_widths=[60, 140, 70, 120, 120, 110, 180, 200, 150],
            fetch_data_func=self._fetch_returned_drawings,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search receipts...",
            search_keys=[
                "no",
                "rev",
                "status",
                "bag_name",
                "ipd_catalog",
                "returned_by",
            ],
            cell_formatters={5: self._format_status, 6: self._format_returned_by},
            on_data_ready_callback=on_data_ready,
        )
        self.table.data_keys = [
            "id",
            "no",
            "rev",
            "bag_name",
            "ipd_catalog",
            "status",
            "returned_by",
            "return_date",
        ]

        # Add Status Filter Dropdown
        filter_frame = tk.Frame(self.table.header_frame, bg=styles.LIGHT)
        filter_frame.pack(side="left", padx=(20, 0))

        tk.Label(
            filter_frame,
            text="Filter:",
            bg=styles.LIGHT,
            fg=styles.SECONDARY,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(0, 5))

        self.status_var = tk.StringVar(value="All")
        self.status_cb = ttk.Combobox(
            filter_frame,
            textvariable=self.status_var,
            values=["All", "Returned", "Received"],
            state="readonly",
            width=12,
            font=("Segoe UI", 10),
        )
        self.status_cb.pack(side="left")
        self.status_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _format_returned_by(self, val, record):
        return val, "#1f2937", ("Segoe UI", 10), "w"

    def _fetch_returned_drawings(self):
        try:
            status_filter = getattr(self, "status_var", None)
            selected_status = status_filter.get() if status_filter else "All"

            query = """
                SELECT 
                    r.id,
                    r.drawing_id AS no,
                    r.revision AS rev,
                    r.bag_name,
                    r.ipd_catalog,
                    r.status,
                    u.admin_name AS returned_by,
                    DATE_FORMAT(r.requested_at, '%%d-%%m-%%Y %%H:%%i:%%s') AS return_date,
                    (SELECT CONCAT(u_rec.admin_name, ' at ', DATE_FORMAT(h_rec.performed_at, '%%d-%%m-%%Y %%H:%%i:%%s'))
                     FROM drawing_request_history h_rec
                     JOIN drawing_users u_rec ON h_rec.performed_by = u_rec.id
                     WHERE h_rec.request_id = r.id AND h_rec.event_type = 'received'
                     LIMIT 1) AS received_info
                FROM drawing_requests r
                JOIN drawing_users u ON r.requested_by = u.id
                WHERE r.status IN ('Returned', 'Received')
                AND (r.status = %s OR %s = 'All')
                ORDER BY r.requested_at DESC
                LIMIT 500;
            """
            rows = db.fetch_all(query, (selected_status, selected_status))
            return rows
        except Exception as e:
            print("Error fetching returned drawings: {}".format(e))
            return []

    def _get_actions(self, record):
        status = record.get("status")
        if status == "Returned":
            buttons = []
            buttons.append(("Receive", "#10b981", "white", self._handle_receive))
            return buttons
        elif status == "Received":
            info = record.get("received_info", "Received")
            if info and info != "Received":
                info = "Received by " + info
            return (info, "#4f46e5", ("Segoe UI", 9, "italic"), "center")
        return []

    def _handle_receive(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")

        # ✅ Live DB check — catch if someone else already received it
        current = db.fetch_all(
            "SELECT status FROM drawing_requests WHERE id = %s", (request_id,)
        )
        if not current:
            messagebox.showerror("Error", "Drawing record not found.")
            self.refresh(reset_pagination=False)
            return

        if current[0].get("status") != "Returned":
            messagebox.showwarning(
                "Already Received",
                "Drawing %s has already been received by someone else.\n\nThe list will now refresh."
                % drawing_no,
            )
            self.refresh(reset_pagination=False)
            return

        if not messagebox.askyesno(
            "Confirm Receive",
            "Are you sure you want to receive Drawing %s (Rev: %s)?"
            % (drawing_no, record.get("rev")),
        ):
            return

        # Log to history BEFORE updating the request
        insert_history = """
            INSERT INTO drawing_request_history 
            (request_id, event_type, performed_by, revision) 
            VALUES (%s, 'received', %s, (SELECT revision FROM drawing_requests WHERE id = %s))
        """
        db.execute_query(insert_history, (request_id, self.user_id or 1, request_id))

        # Complete the lifecycle by updating the status
        query = "UPDATE drawing_requests SET status = 'Received' WHERE id = %s"
        if db.execute_query(query, (request_id,)):
            messagebox.showinfo(
                "Success", "Drawing %s has been received successfully." % drawing_no
            )
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to receive drawing from database.")

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(
            reset_pagination=reset_pagination,
            silent=silent,
            button_silent=button_silent,
        )
