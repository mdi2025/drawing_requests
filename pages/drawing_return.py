#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
from pages.table_component import CanvasDataTable
import urllib.request
import urllib.parse
import json
from config import app_url as API_BASE_URL, api_timeout as API_TIMEOUT


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

            # Prepare API request
            data = urllib.parse.urlencode({
                'action': 'get_issued_drawings_for_user',
                'user_id': self.user_id,
                'status_filter': selected_status
            }).encode('utf-8')

            req = urllib.request.Request(API_BASE_URL, data=data)
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                raw_response = response.read().decode('utf-8')
                result = json.loads(raw_response)

            if result.get('response') == 'true':
                return result.get('data', [])
            else:
                print("API Error: {}".format(result.get('message', 'Unknown error')))
                return []

        except urllib.error.URLError as e:
            print("Network error fetching issued drawings: {}".format(e))
            return []
        except json.JSONDecodeError as e:
            print("JSON parse error: {}".format(e))
            print("Raw response: {}".format(raw_response if 'raw_response' in locals() else 'N/A'))
            return []
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

        # Confirm return
        if not messagebox.askyesno(
            "Confirm Return",
            "Are you sure you want to return Drawing %s (Rev: %s)?"
            % (drawing_no, record.get("rev")),
        ):
            return

        try:
            # Prepare API request
            data = urllib.parse.urlencode({
                'action': 'return_drawing_request',
                'request_id': request_id,
                'user_id': self.user_id
            }).encode('utf-8')

            req = urllib.request.Request(API_BASE_URL, data=data)
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                raw_response = response.read().decode('utf-8')
                result = json.loads(raw_response)

            if result.get('response') == 'true':
                messagebox.showinfo(
                    "Success", "Drawing %s has been returned successfully." % drawing_no
                )
                self.refresh(reset_pagination=False)
            else:
                messagebox.showerror("Error", result.get('message', 'Failed to return drawing.'))

        except urllib.error.URLError as e:
            messagebox.showerror("Network Error", "Failed to connect to server: {}".format(e))
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", "Invalid response from server.")
            print("JSON parse error: {}".format(e))
            print("Raw response: {}".format(raw_response if 'raw_response' in locals() else 'N/A'))
        except Exception as e:
            messagebox.showerror("Error", "An unexpected error occurred: {}".format(e))

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(
            reset_pagination=reset_pagination,
            silent=silent,
            button_silent=button_silent,
        )
