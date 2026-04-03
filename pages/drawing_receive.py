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

            # Prepare API request
            data = urllib.parse.urlencode({
                'action': 'get_returned_drawings',
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
            print("Network error fetching returned drawings: {}".format(e))
            return []
        except json.JSONDecodeError as e:
            print("JSON parse error: {}".format(e))
            print("Raw response: {}".format(raw_response if 'raw_response' in locals() else 'N/A'))
            return []
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

        # Confirm receive
        if not messagebox.askyesno(
            "Confirm Receive",
            "Are you sure you want to receive Drawing %s (Rev: %s)?"
            % (drawing_no, record.get("rev")),
        ):
            return

        try:
            # Prepare API request
            data = urllib.parse.urlencode({
                'action': 'receive_drawing_request',
                'request_id': request_id,
                'user_id': self.user_id
            }).encode('utf-8')

            req = urllib.request.Request(API_BASE_URL, data=data)
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                raw_response = response.read().decode('utf-8')
                result = json.loads(raw_response)

            if result.get('response') == 'true':
                messagebox.showinfo(
                    "Success", "Drawing %s has been received successfully." % drawing_no
                )
                self.refresh(reset_pagination=False)
            else:
                messagebox.showerror("Error", result.get('message', 'Failed to receive drawing.'))

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
