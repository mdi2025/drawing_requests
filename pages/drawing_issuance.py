#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import json
import urllib.parse

try:
    import urllib.request as urllib_request
except ImportError:
    import urllib as urllib_request
import styles
from pages.table_component import CanvasDataTable
from db_handler import db
from config import app_url as API_BASE_URL, api_timeout as API_TIMEOUT


class DrawingIssuancePage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None, on_data_ready=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id


        self.table = CanvasDataTable(
            self,
            title="Drawing Issuance",
            headers=[
                "SNo",
                "Drawing ID",
                "Revision",
                "Bag Name",
                "IPD Catalog",
                "Requested By",
                "Status",
                "Remarks",
                "Actions",
            ],
            initial_widths=[60, 140, 70, 120, 120, 200, 100, 100, 250],
            fetch_data_func=self._fetch_requests,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search requests...",
            search_keys=[
                "no",
                "rev",
                "status",
                "requested_by",
                "bag_name",
                "ipd_catalog",
                "remarks",
                "issued_info",
                "rejected_info",
            ],
            cell_formatters={
                5: self._format_requested_by,
                6: self._format_status,
                7: self._format_remarks,
            },
            on_data_ready_callback=on_data_ready,
            on_cell_click=self._handle_cell_click,
            non_copyable_cols=[7],
        )
        self.table.data_keys = [
            "id",
            "no",
            "rev",
            "bag_name",
            "ipd_catalog",
            "requested_by",
            "status",
            "remarks",
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
            values=["All", "Pending", "Issued", "Rejected", "Received", "Returned"],
            state="readonly",
            width=12,
            font=("Segoe UI", 10),
        )
        self.status_cb.pack(side="left")
        self.status_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        s = str(val).lower()
        if s == "rejected":
            color = "#ef4444"
        elif s == "issued":
            color = "#008000"
        else:
            color = "#1f2937"
        return str(val).upper(), color, ("Segoe UI", 10), "center"

    def _format_requested_by(self, val, record):
        return val, "#1f2937", ("Segoe UI", 10), "w"

    def _fetch_requests(self):
        try:
            status_filter = getattr(self, "status_var", None)
            selected_status = status_filter.get() if status_filter else "All"

            # Call API to get requested drawings
            data = {
                "action": "get_requested_drawings",
                "status_filter": selected_status,
            }
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib_request.Request(API_BASE_URL, data=encoded_data, method="POST")

            response = urllib_request.urlopen(req, timeout=API_TIMEOUT)
            raw = response.read().decode("utf-8")
            result = json.loads(raw)

            if result.get("response") == "true":
                return result.get("data", [])
            else:
                print("API error: {}".format(result.get("message", "Unknown")))
                return []

        except ValueError as e:
            print("Raw API response:", repr(raw))
            messagebox.showerror("Error", "API returned invalid JSON: {}".format(e))
            return []
        except Exception as e:
            print("API call failed: {}".format(e))
            messagebox.showerror("Error", "Failed to fetch requests from server.")
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
        if col_idx == 7:  # Remarks column
            remarks = record.get("remarks")
            if remarks:
                self._show_remarks_modal(record.get("no"), remarks)

    def _show_remarks_modal(self, drawing_no, remarks):
        import tkinter as tk  # Explicit import for use in this method

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

        from tkinter import ttk  # Explicit import for use in this method

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
        if status in ("Pending", "open"):
            return [
                ("Issue", "#10b981", "white", self._handle_issue),
                ("Reject", "#ef4444", "white", self._handle_reject),
            ]
        elif status == "Rejected":
            info = record.get("rejected_info", "Rejected")
            if info and info != "Rejected":
                info = "Rejected by " + info
            return (info, "#ef4444", ("Segoe UI", 9, "italic"), "center")
        else:
            info = record.get("issued_info", "Issued")
            if info and info != "Issued":
                info = "Issued by " + info
            return (info, "#008000", ("Segoe UI", 9, "italic"), "center")

        return []

    # ====================== UPDATED: Issuance logic (Revision selection, No remarks) ======================
    def _handle_issue(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")
        requested_rev = record.get("rev")

        try:
            data = {
                "action": "check_latest_revision",
                "drawing_no": drawing_no,
                "requested_rev": requested_rev,
            }
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib_request.Request(API_BASE_URL, data=encoded_data, method="POST")
            response = urllib_request.urlopen(req, timeout=API_TIMEOUT)
            result = json.loads(response.read().decode("utf-8"))

            if result.get("response") != "true":
                messagebox.showerror("Error", result.get("message", "Failed to check revision."))
                return

            latest_rev = result.get("latest_rev")
            has_newer = result.get("has_newer", False)

            if not has_newer:
                if messagebox.askyesno(
                    "Confirm Issue",
                    "Are you sure you want to issue drawing {} (Rev: {})?".format(drawing_no, requested_rev),
                ):
                    self._finish_issuance(record, requested_rev)
            else:
                self._show_revision_modal(record, requested_rev, latest_rev)

        except Exception as e:
            print("API call failed: {}".format(e))
            messagebox.showerror("Error", "Failed to connect to server.")

    def _show_revision_modal(self, record, req_rev, lat_rev):
        dialog = tk.Toplevel(self)
        dialog.title("Revision Selection")
        dialog.geometry("450x380")
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

        # Header
        header = tk.Frame(dialog, bg=styles.PRIMARY, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Choose Revision to Issue",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg=styles.PRIMARY,
        ).pack(pady=15)

        # Body
        body = tk.Frame(dialog, bg="white", padx=30, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="A newer approved revision exists for this drawing.",
            font=("Segoe UI", 10),
            bg="white",
            fg="#1f2937",
        ).pack(pady=(0, 20))

        # Info Box
        info_frame = tk.Frame(
            body,
            bg="#f8fafc",
            padx=15,
            pady=15,
            highlightthickness=1,
            highlightbackground="#e2e8f0",
        )
        info_frame.pack(fill="x", pady=5)

        tk.Label(
            info_frame,
            text="Drawing No: {}".format(record.get("no")),
            font=("Segoe UI", 11, "bold"),
            bg="#f8fafc",
            fg="#1f2937",
        ).pack(anchor="w")
        tk.Label(
            info_frame,
            text="Requested: Rev {}".format(req_rev),
            font=("Segoe UI", 10),
            bg="#f8fafc",
            fg="#64748b",
        ).pack(anchor="w", pady=(5, 0))
        tk.Label(
            info_frame,
            text="Latest: Rev {}".format(lat_rev),
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
            fg="#10b981",
        ).pack(anchor="w")

        # Selection Buttons
        btn_frame = tk.Frame(body, bg="white", pady=25)
        btn_frame.pack(fill="x")

        def issue_requested():
            dialog.destroy()
            self._finish_issuance(record, req_rev)

        def issue_latest():
            dialog.destroy()
            self._finish_issuance(record, lat_rev)

        # Buttons
        tk.Button(
            btn_frame,
            text="Issue Requested ({})".format(req_rev),
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9",
            fg="#1f2937",
            command=issue_requested,
            relief="flat",
            padx=15,
            pady=8,
        ).pack(side="left", expand=True)

        tk.Button(
            btn_frame,
            text="Issue Latest ({})".format(lat_rev),
            font=("Segoe UI", 9, "bold"),
            bg="#4f46e5",
            fg="white",
            command=issue_latest,
            relief="flat",
            padx=15,
            pady=8,
        ).pack(side="right", expand=True)

        # Center dialog
        dialog.update_idletasks()
        try:
            main_w = self.winfo_toplevel().winfo_width()
            main_h = self.winfo_toplevel().winfo_height()
            x = self.winfo_toplevel().winfo_rootx() + (main_w - 450) // 2
            y = self.winfo_toplevel().winfo_rooty() + (main_h - 380) // 2
            dialog.geometry("+%d+%d" % (x, y))
        except:
            pass

        self.wait_window(dialog)

    def _finish_issuance(self, record, target_rev):
        request_id = record.get("id")
        drawing_no = record.get("no")
        current_rev = record.get("rev")

        # Call API to issue the drawing
        data = {
            "action": "issue_drawing_request",
            "request_id": request_id,
            "user_id": self.user_id or 1,
            "target_revision": target_rev if target_rev != current_rev else "",
        }
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib_request.Request(API_BASE_URL, data=encoded_data, method="POST")

        try:
            response = urllib_request.urlopen(req, timeout=API_TIMEOUT)
            raw = response.read().decode("utf-8")
            result = json.loads(raw)

            if result.get("response") == "true":
                # Success - update UI immediately
                for row in self.table.data:
                    if row.get("id") == request_id:
                        row["status"] = "Issued"
                        row["rev"] = target_rev
                        break
                self.table._apply_search(reset_pagination=False)

                msg = "Drawing {} (Rev {}) has been issued successfully.".format(
                    drawing_no, target_rev
                )
                messagebox.showinfo("Issuance", msg)
                self.refresh(reset_pagination=False, button_silent=True)
            else:
                messagebox.showerror(
                    "Error", result.get("message", "Failed to issue drawing.")
                )

        except ValueError as e:
            print("Raw API response:", repr(raw))
            messagebox.showerror("Error", "API returned invalid JSON: {}".format(e))
        except Exception as e:
            print("API call failed: {}".format(e))
            messagebox.showerror("Error", "Failed to connect to server.")

    # ====================== NEW: Rejection Remarks Modal (Red Theme) ======================
    def _handle_reject(self, record):
        dialog = tk.Toplevel(self)
        dialog.title("Confirm Rejection")
        dialog.geometry("450x420")
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

        # Header (RED THEME)
        header = tk.Frame(dialog, bg="#ef4444", height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Reject Drawing Request",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg="#ef4444",
        ).pack(pady=15)

        # Body
        body = tk.Frame(dialog, bg="white", padx=30, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="Drawing No: {} (Rev: {})".format(record.get("no"), record.get("rev")),
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#1f2937",
        ).pack(anchor="w")

        tk.Label(
            body,
            text="Bag Name: {} | Catalog: {}".format(
                record.get("bag_name") or "—", record.get("ipd_catalog") or "—"
            ),
            font=("Segoe UI", 10),
            bg="white",
            fg="#64748b",
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            body,
            text="Please provide a reason for rejection (Required):",
            font=("Segoe UI", 10),
            bg="white",
            fg="#4b5563",
        ).pack(anchor="w", pady=(15, 5))

        # Remarks Container for Text + Scrollbar
        remarks_frame = tk.Frame(body, bg="white")
        remarks_frame.pack(fill="x", pady=5)

        remarks_entry = tk.Text(
            remarks_frame,
            font=("Segoe UI", 10),
            height=5,
            relief="solid",
            bd=1,
            highlightthickness=1,
            wrap="word",
        )
        remarks_scrollbar = tk.Scrollbar(
            remarks_frame, orient="vertical", command=remarks_entry.yview
        )
        remarks_entry.configure(yscrollcommand=remarks_scrollbar.set)

        remarks_entry.pack(side="left", fill="x", expand=True)
        remarks_scrollbar.pack(side="right", fill="y")
        remarks_entry.focus_set()

        # Buttons
        btn_frame = tk.Frame(body, bg="white", pady=20)
        btn_frame.pack(fill="x", side="bottom")

        def confirm_rejection():
            remarks = remarks_entry.get("1.0", tk.END).strip()
            if not remarks:
                messagebox.showwarning(
                    "Remarks Required",
                    "Please provide a reason for rejection.",
                    parent=dialog,
                )
                return

            dialog.destroy()
            self._execute_rejection(record, remarks)

        tk.Button(
            btn_frame,
            text="Reject Request",
            font=("Segoe UI", 10, "bold"),
            bg="#ef4444",
            fg="white",
            command=confirm_rejection,
            relief="flat",
            padx=25,
            pady=10,
        ).pack(side="right")

        tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 10),
            bg="#f1f5f9",
            fg="#1f2937",
            command=dialog.destroy,
            relief="flat",
            padx=20,
            pady=10,
        ).pack(side="right", padx=10)

        # Center dialog
        dialog.update_idletasks()
        try:
            main_w = self.winfo_toplevel().winfo_width()
            main_h = self.winfo_toplevel().winfo_height()
            x = self.winfo_toplevel().winfo_rootx() + (main_w - 450) // 2
            y = self.winfo_toplevel().winfo_rooty() + (main_h - 420) // 2
            dialog.geometry("+%d+%d" % (x, y))
        except:
            pass

        self.wait_window(dialog)

    def _execute_rejection(self, record, remarks):
        request_id = record.get("id")
        drawing_no = record.get("no")

        # Call API to reject the drawing
        data = {
            "action": "reject_drawing_request",
            "request_id": request_id,
            "user_id": self.user_id or 1,
            "remarks": remarks,
        }
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib_request.Request(API_BASE_URL, data=encoded_data, method="POST")

        try:
            response = urllib_request.urlopen(req, timeout=API_TIMEOUT)
            raw = response.read().decode("utf-8")
            result = json.loads(raw)

            if result.get("response") == "true":
                messagebox.showinfo(
                    "Rejected", "Request for {} has been rejected.".format(drawing_no)
                )
                self.refresh(reset_pagination=False)
            else:
                messagebox.showerror(
                    "Error", result.get("message", "Failed to reject request.")
                )

        except ValueError as e:
            print("Raw API response:", repr(raw))
            messagebox.showerror("Error", "API returned invalid JSON: {}".format(e))
        except Exception as e:
            print("API call failed: {}".format(e))
            messagebox.showerror("Error", "Failed to connect to server.")

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(
            reset_pagination=reset_pagination,
            silent=silent,
            button_silent=button_silent,
        )
