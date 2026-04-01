#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable
from db_handler import db


class DrawingReturnPage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None, on_data_ready=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id

        self.table = CanvasDataTable(
            self,
            title="Drawing Return",
            headers=[
                "SNo",
                "Drawing ID",
                "Revision",
                "Bag Name",
                "IPD Catalog",
                "Status",
                "Remarks",
                "Issue/Reject Date",
                "Action",
            ],
            initial_widths=[60, 140, 70, 120, 120, 110, 100, 180, 140],
            fetch_data_func=self._fetch_issued_drawings,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search issued drawings...",
            search_keys=[
                "no",
                "rev",
                "bag_name",
                "ipd_catalog",
                "status",
                "remarks",
                "rejected_info",
            ],
            cell_formatters={5: self._format_status, 6: self._format_remarks},
            on_data_ready_callback=on_data_ready,
            on_cell_click=self._handle_cell_click,
            non_copyable_cols=[6],
        )
        self.table.data_keys = [
            "id",
            "no",
            "rev",
            "bag_name",
            "ipd_catalog",
            "status",
            "remarks",
            "issue_reject_date",
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
            values=["All", "Pending", "Issued", "Returned", "Received", "Rejected"],
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

    def _fetch_issued_drawings(self):
        try:
            if not self.user_id:
                return []

            status_filter = getattr(self, "status_var", None)
            selected_status = status_filter.get() if status_filter else "All"

            if selected_status == "All":
                status_condition = "r.status IN ('Pending', 'Issued', 'Returned', 'Received', 'Rejected')"
                params = (self.user_id,)
            else:
                status_condition = "r.status = %s"
                params = (selected_status, self.user_id)

            query = (
                """
                SELECT 
                    r.id,
                    r.drawing_id AS no,
                    r.revision AS rev,
                    r.bag_name,
                    r.ipd_catalog,
                    r.status,
                    CASE 
                        WHEN r.status = 'Rejected' THEN (SELECT DATE_FORMAT(h_rej.performed_at, '%%d-%%m-%%Y %%H:%%i:%%s') 
                                                         FROM drawing_request_history h_rej 
                                                         WHERE h_rej.request_id = r.id AND h_rej.event_type = 'rejected' 
                                                         LIMIT 1)
                        WHEN r.status = 'Pending' THEN NULL
                        ELSE DATE_FORMAT(h_iss.performed_at, '%%d-%%m-%%Y %%H:%%i:%%s')
                    END AS issue_reject_date,
                    (SELECT CONCAT(u_ret.admin_name, ' at ', DATE_FORMAT(h_ret.performed_at, '%%d-%%m-%%Y %%H:%%i:%%s'))
                     FROM drawing_request_history h_ret
                     JOIN drawing_users u_ret ON h_ret.performed_by = u_ret.id
                     WHERE h_ret.request_id = r.id AND h_ret.event_type = 'returned'
                     LIMIT 1) AS returned_info,
                    (SELECT CONCAT(u_rec.admin_name, ' at ', DATE_FORMAT(h_rec.performed_at, '%%d-%%m-%%Y %%H:%%i:%%s'))
                     FROM drawing_request_history h_rec
                     JOIN drawing_users u_rec ON h_rec.performed_by = u_rec.id
                     WHERE h_rec.request_id = r.id AND h_rec.event_type = 'received'
                     LIMIT 1) AS received_info,
                    (SELECT CONCAT(u_rej.admin_name, ' at ', DATE_FORMAT(h_rej.performed_at, '%%d-%%m-%%Y %%H:%%i:%%s'))
                     FROM drawing_request_history h_rej
                     JOIN drawing_users u_rej ON h_rej.performed_by = u_rej.id
                     WHERE h_rej.request_id = r.id AND h_rej.event_type = 'rejected'
                     LIMIT 1) AS rejected_info,
                    (SELECT remarks FROM drawing_request_history 
                     WHERE request_id = r.id AND event_type = 'rejected' 
                     LIMIT 1) AS remarks
                FROM drawing_requests r
                LEFT JOIN drawing_request_history h_iss ON r.id = h_iss.request_id AND h_iss.event_type = 'issued'
                WHERE """
                + status_condition
                + """ AND r.requested_by = %s
                ORDER BY r.id DESC
                LIMIT 500;
            """
            )
            rows = db.fetch_all(query, params)
            return rows
        except Exception as e:
            print("Error fetching issued drawings: {}".format(e))
            return []

    def _format_remarks(self, val, record):
        if val:
            return (
                "VIEW",
                styles.PRIMARY,
                ("Segoe UI", 10, "bold", "underline"),
                "center",
            )
        return "—", "#94a3b8", ("Segoe UI", 10), "center"

    def _handle_cell_click(self, record, col_idx):
        if col_idx == 6:  # Remarks column index updated to 6
            remarks = record.get("remarks")
            if remarks:
                self._show_remarks_modal(record.get("no"), remarks)

    def _show_remarks_modal(self, drawing_no, remarks):
        dialog = tk.Toplevel(self)
        dialog.title("Rejection Remarks")
        dialog.geometry("400x300")
        dialog.configure(bg="white")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())

        # Header
        header = tk.Frame(dialog, bg=styles.PRIMARY, height=50)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Remarks for " + drawing_no,
            font=("Segoe UI", 12, "bold"),
            fg="white",
            bg=styles.PRIMARY,
        ).pack(pady=10)

        # Body
        body = tk.Frame(dialog, bg="white", padx=20, pady=20)
        body.pack(fill="both", expand=True)

        txt = tk.Text(
            body,
            font=("Segoe UI", 10),
            wrap="word",
            bg="#f8fafc",
            relief="flat",
            padx=10,
            pady=10,
        )
        txt.insert("1.0", remarks)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True)

        btn = ttk.Button(body, text="Close", command=dialog.destroy)
        btn.pack(pady=(15, 0))

        # Center
        dialog.update_idletasks()
        rw, rh = 400, 300
        sw = self.winfo_toplevel().winfo_width()
        sh = self.winfo_toplevel().winfo_height()
        sx = self.winfo_toplevel().winfo_rootx() + (sw - rw) // 2
        sy = self.winfo_toplevel().winfo_rooty() + (sh - rh) // 2
        dialog.geometry("+%d+%d" % (sx, sy))
        dialog.grab_set()

    def _get_actions(self, record):
        status = record.get("status")
        if status == "Issued":
            buttons = []
            buttons.append(("Return", styles.PRIMARY, "white", self._handle_return))
            return buttons
        elif status == "Returned":
            info = record.get("returned_info", "Returned")
            if info and info != "Returned":
                info = "Returned by " + info
            return (info, "#4f46e5", ("Segoe UI", 9, "italic"), "center")
        elif status == "Received":
            info = record.get("received_info", "Received")
            if info and info != "Received":
                info = "Received by " + info
            return (info, "#10b981", ("Segoe UI", 9, "italic"), "center")
        elif status == "Rejected":
            info = record.get("rejected_info", "Rejected")
            if info and info != "Rejected":
                info = "Rejected by " + info
            return (info, "#ef4444", ("Segoe UI", 9, "italic"), "center")
        elif status == "Pending":
            return ("Request Pending", "#f59e0b", ("Segoe UI", 9, "italic"), "center")
        return []

    def _handle_return(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")

        # ✅ Live DB check — catch if someone else already returned it
        current = db.fetch_all(
            "SELECT status FROM drawing_requests WHERE id = %s", (request_id,)
        )
        if not current:
            messagebox.showerror("Error", "Drawing record not found.")
            self.refresh(reset_pagination=False)
            return

        if current[0].get("status") != "Issued":
            messagebox.showwarning(
                "Already Returned",
                "Drawing %s has already been returned by someone else.\n\nThe list will now refresh."
                % drawing_no,
            )
            self.refresh(reset_pagination=False)
            return

        # Only ask confirmation if it's still genuinely "Issued"
        if not messagebox.askyesno(
            "Confirm Return",
            "Are you sure you want to return Drawing %s (Rev: %s)?"
            % (drawing_no, record.get("rev")),
        ):
            return

        query = "UPDATE drawing_requests SET status = 'Returned' WHERE id = %s"
        if db.execute_query(query, (request_id,)):
            insert_history = """
                INSERT INTO drawing_request_history 
                (request_id, event_type, performed_by, revision) 
                VALUES (%s, 'returned', %s, (SELECT revision FROM drawing_requests WHERE id = %s))
            """
            db.execute_query(
                insert_history, (request_id, self.user_id or 1, request_id)
            )
            messagebox.showinfo(
                "Success", "Drawing %s has been returned successfully." % drawing_no
            )
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to update return status in database.")

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(
            reset_pagination=reset_pagination,
            silent=silent,
            button_silent=button_silent,
        )
