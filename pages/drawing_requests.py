#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import datetime
import threading
import json
import urllib.parse
try:
    import urllib.request as urllib_request
except ImportError:
    import urllib as urllib_request
from pages.table_component import CanvasDataTable
import styles
from db_handler import db
from config import app_url as API_BASE_URL, api_timeout as API_TIMEOUT

# ─────────────────────────────────────────────
# API endpoint
# ─────────────────────────────────────────────


class DrawingRequestsPage(ttk.Frame):

    def __init__(self, parent, username="User", user_id=None, on_data_ready=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id

        # Initialize the reusable table component
        self.table = CanvasDataTable(
            self,
            title="Drawing Requisitions",
            headers=[
                "SNo",
                "Drawing ID",
                "Revision",
                "Status",
                "Requested By",
                "Bag Name",
                "Catalog",
                "Action",
            ],
            initial_widths=[60, 160, 80, 100, 250, 150, 150, 140],
            fetch_data_func=self._fetch_drawings,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search drawings...",
            search_keys=[
                "no",
                "rev",
                "status",
                "requested_by",
                "bag_name",
                "ipd_catalog",
            ],
            cell_formatters={3: self._format_status, 4: self._format_requested_by},
            on_data_ready_callback=on_data_ready,
        )

        self.table.data_keys = [
            "id",
            "no",
            "rev",
            "status",
            "requested_by",
            "bag_name",
            "ipd_catalog",
            "req_status",
        ]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    # ------------------------------
    # Formatters
    # ------------------------------

    def _format_status(self, val, record):
        return str(val).upper(), "#1f2937", ("Segoe UI", 10), "center"

    def _format_requested_by(self, val, record):
        fg = "#4f46e5" if val else "#1f2937"
        return val, fg, ("Segoe UI", 9, "italic"), "w"

    # ------------------------------
    # Fetch Data
    # ------------------------------

    def _fetch_drawings(self):
        try:
            url = API_BASE_URL + "?action=get_drawing_requests"
            response = urllib_request.urlopen(url, timeout=API_TIMEOUT)
            raw     = response.read().decode("utf-8")
            result  = json.loads(raw)

            if result.get("response") == "true":
                return result.get("data", [])
            else:
                print("API error: {}".format(result.get("message", "Unknown")))
                return []

        except Exception as e:
            print("Error fetching drawings from API: {}".format(e))
            return []
 
    # ------------------------------
    # Action Buttons
    # ------------------------------

    def _get_actions(self, drawing):
        status = drawing.get("req_status")
        if status in ("Pending", "Issued", "Returned"):
            return [("Requested", "#f1f5f9", "#64748b", None)]
        
        return [("Request", styles.PRIMARY, "white", self._request_drawing)]

    # ------------------------------
    # IPD Selection Modal
    # ------------------------------

    def _ask_ipd_details(self):
        result = {"ipd": False, "bag_name": "", "catalog_no": "", "cancel": False}

        dialog = tk.Toplevel(self)
        dialog.title("IPD Request Details")
        dialog.geometry("450x400")
        dialog.configure(bg="white")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())

        # Robust grab set
        def _apply_grab():
            try:
                if dialog.winfo_exists():
                    dialog.grab_set()
            except:
                pass

        dialog.after(100, _apply_grab)

        def on_close():
            result["cancel"] = True
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)

        # Header
        header = tk.Frame(dialog, bg=styles.PRIMARY, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="IPD Request Details",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg=styles.PRIMARY,
        ).pack(pady=15)

        # Body
        body = tk.Frame(dialog, bg="white", padx=30, pady=10)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="Is this drawing an IPD request?",
            font=("Segoe UI", 11),
            bg="white",
            fg="#1f2937",
        ).pack(pady=(15, 5), anchor="w")

        ipd_var = tk.StringVar(value="No")

        def on_toggle():
            if ipd_var.get() == "Yes":
                details_frame.pack(fill="x", pady=15)
            else:
                details_frame.pack_forget()

        radio_frame = tk.Frame(body, bg="white")
        radio_frame.pack(fill="x", pady=5)

        tk.Radiobutton(
            radio_frame,
            text="No",
            variable=ipd_var,
            value="No",
            font=("Segoe UI", 10),
            bg="white",
            command=on_toggle,
        ).pack(side="left", padx=(0, 20))
        tk.Radiobutton(
            radio_frame,
            text="Yes",
            variable=ipd_var,
            value="Yes",
            font=("Segoe UI", 10),
            bg="white",
            command=on_toggle,
        ).pack(side="left")

        # Details Frame (initially hidden)
        details_frame = tk.Frame(
            body,
            bg="#f8fafc",
            padx=15,
            pady=15,
            highlightthickness=1,
            highlightbackground="#e2e8f0",
        )

        tk.Label(
            details_frame,
            text="Bag Name:",
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
        ).grid(row=0, column=0, sticky="w", pady=5)
        bag_entry = tk.Entry(details_frame, font=("Segoe UI", 10), width=25)
        bag_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(
            details_frame,
            text="Catalog:",
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
        ).grid(row=1, column=0, sticky="w", pady=5)
        cat_entry = tk.Entry(details_frame, font=("Segoe UI", 10), width=25)
        cat_entry.grid(row=1, column=1, padx=10, pady=5)

        # Buttons
        btn_frame = tk.Frame(body, bg="white", pady=20)
        btn_frame.pack(fill="x", side="bottom")

        def on_submit():
            result["ipd"] = ipd_var.get() == "Yes"
            if result["ipd"]:
                result["bag_name"] = bag_entry.get().strip()
                result["catalog_no"] = cat_entry.get().strip()
                if not result["bag_name"] or not result["catalog_no"]:
                    messagebox.showwarning(
                        "Input Required",
                        "Please fill in both Bag Name and Catalog No for IPD requests.",
                        parent=dialog,
                    )
                    return
            dialog.destroy()

        def on_cancel():
            result["cancel"] = True
            dialog.destroy()

        tk.Button(
            btn_frame,
            text="Submit",
            font=("Segoe UI", 9, "bold"),
            bg=styles.PRIMARY,
            fg="white",
            command=on_submit,
            relief="flat",
            padx=25,
            pady=8,
        ).pack(side="right", padx=5)
        tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#f1f5f9",
            fg="#1f2937",
            command=on_cancel,
            relief="flat",
            padx=20,
            pady=8,
        ).pack(side="right", padx=5)

        # Center dialog
        dialog.update_idletasks()
        try:
            main_w = self.winfo_toplevel().winfo_width()
            main_h = self.winfo_toplevel().winfo_height()
            x = self.winfo_toplevel().winfo_rootx() + (main_w - 450) // 2
            y = self.winfo_toplevel().winfo_rooty() + (main_h - 400) // 2
            dialog.geometry("+%d+%d" % (x, y))
        except:
            pass

        self.wait_window(dialog)
        return result

    # ------------------------------
    # Request Drawing
    # ------------------------------

    def _request_drawing(self, drawing):

        auto_id = drawing.get("id")
        catalog = drawing.get("no")
        revision = drawing.get("rev")

        # Get IPD Details
        ipd_data = self._ask_ipd_details()
        if ipd_data.get("cancel"):
            return

        msg = "Request drawing %s (Revision: %s)?" % (catalog, revision)
        if ipd_data["ipd"]:
            msg += "\n\nIPD REQUEST:\nBag: %s\nCat: %s" % (
                ipd_data["bag_name"],
                ipd_data["catalog_no"],
            )

        confirm = messagebox.askyesno("Confirm Request", msg)

        if not confirm:
            return

        if not self.user_id:
            messagebox.showerror(
                "Error", "User session not found. Please log in again."
            )
            return

        # Call API to insert request
        data = {
            'action': 'insert_drawing_request',
            'drawing_id': catalog,
            'revision': revision,
            'requested_by': self.user_id,
            'bag_name': ipd_data.get("bag_name", ""),
            'ipd_catalog': ipd_data.get("catalog_no", ""),
        }
        encoded_data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib_request.Request(API_BASE_URL, data=encoded_data, method='POST')
        try:
            response = urllib_request.urlopen(req, timeout=API_TIMEOUT)
            raw = response.read().decode("utf-8")
            result = json.loads(raw)
            if result.get("response") == "true":
                request_id = result.get("request_id")
                # Success
            else:
                messagebox.showerror("Error", result.get("message", "Failed to submit request."))
                return
        except ValueError as e:
            print("Raw API response:", repr(raw))
            messagebox.showerror("Error", "API returned invalid JSON: {}".format(e))
            return
        except Exception as e:
            print("API call failed with exception:", e)
            messagebox.showerror("Error", "API call failed: {}".format(e))
            return

        # Update UI immediately
        now_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        placeholder = "%s at %s" % (self.username, now_str)
        for row in self.table.data:
            if row.get("no") == catalog and row.get("rev") == revision:
                row["requested_by"] = placeholder
                row["req_status"] = "Pending"
                break
        self.table._apply_search(reset_pagination=False)

        # Kick off background refresh to sync from DB
        self.refresh(reset_pagination=False, button_silent=True)

        messagebox.showinfo("Success", "Request submitted for drawing %s" % catalog)

    # ------------------------------
    # Refresh Table
    # ------------------------------

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(
            reset_pagination=reset_pagination,
            silent=silent,
            button_silent=button_silent,
        )
