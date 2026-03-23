#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
import styles
from pages.table_component import CanvasDataTable
from db_handler import db

class ReportsPage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None, on_data_ready=None):
        ttk.Frame.__init__(self, parent)
        self.username = username
        self.user_id = user_id
        
        self.table = CanvasDataTable(
            self,
            title="Drawing Lifecycle Report",
            headers=["SNo", "Drawing ID", "Rev", "Status", "Issue Info", "Action"],
            initial_widths=[60, 180, 80, 140, 250, 150],
            fetch_data_func=self._fetch_report_data,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search records / history...",
            search_keys=["no", "rev", "status", "req_info", "iss_info", "ret_info", "rec_info", "rej_info"],
            cell_formatters={
                3: self._format_status,
                4: self._format_info
            },
            on_data_ready_callback=on_data_ready
        )
        self.table.data_keys = ["id", "no", "rev", "status", "iss_info"]
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_status(self, val, record):
        s = str(val).lower()
        color = "#1f2937"
        if s == "rejected": color = "#ef4444"
        elif s == "issued": color = "#008000"
        elif s == "returned": color = "#4f46e5"
        elif s == "received": color = "#10b981"
        return str(val).upper(), color, ("Segoe UI", 9, "bold"), "center"

    def _format_info(self, val, record):
        if not val or val == "—":
            return "—", "#94a3b8", ("Segoe UI", 9), "w"
        return val, "#1f2937", ("Segoe UI", 9), "w"

    def _fetch_report_data(self):
        try:
            # Comprehensive query to get all stages of the lifecycle
            query = """
                SELECT 
                    r.id,
                    r.drawing_id AS no,
                    r.revision AS rev,
                    r.status,
                    CONCAT(u_req.admin_name, ' at ', DATE_FORMAT(h_req.performed_at, '%d-%m-%Y %H:%i')) AS req_info,
                    COALESCE(CONCAT(u_iss.admin_name, ' at ', DATE_FORMAT(h_iss.performed_at, '%d-%m-%Y %H:%i')), '—') AS iss_info,
                    COALESCE(CONCAT(u_ret.admin_name, ' at ', DATE_FORMAT(h_ret.performed_at, '%d-%m-%Y %H:%i')), '—') AS ret_info,
                    COALESCE(CONCAT(u_rec.admin_name, ' at ', DATE_FORMAT(h_rec.performed_at, '%d-%m-%Y %H:%i')), '—') AS rec_info,
                    COALESCE(CONCAT(u_rej.admin_name, ' at ', DATE_FORMAT(h_rej.performed_at, '%d-%m-%Y %H:%i')), '—') AS rej_info
                FROM drawing_requests r
                LEFT JOIN drawing_request_history h_req ON r.id = h_req.request_id AND h_req.event_type = 'requested'
                LEFT JOIN drawing_users u_req ON h_req.performed_by = u_req.id
                
                LEFT JOIN drawing_request_history h_iss ON r.id = h_iss.request_id AND h_iss.event_type = 'issued'
                LEFT JOIN drawing_users u_iss ON h_iss.performed_by = u_iss.id
                
                LEFT JOIN drawing_request_history h_ret ON r.id = h_ret.request_id AND h_ret.event_type = 'returned'
                LEFT JOIN drawing_users u_ret ON h_ret.performed_by = u_ret.id
                
                LEFT JOIN drawing_request_history h_rec ON r.id = h_rec.request_id AND h_rec.event_type = 'received'
                LEFT JOIN drawing_users u_rec ON h_rec.performed_by = u_rec.id
                
                LEFT JOIN drawing_request_history h_rej ON r.id = h_rej.request_id AND h_rej.event_type = 'rejected'
                LEFT JOIN drawing_users u_rej ON h_rej.performed_by = u_rej.id
                
                ORDER BY r.id DESC
                LIMIT 1000
            """
            rows = db.fetch_all(query)
            
            # If a drawing was rejected, we might want to show that in the status or merge it with issuance
            for row in rows:
                if row['status'] == 'Rejected' and row['rej_info'] != '—':
                    row['iss_info'] = "REJECTED"
            
            return rows
        except Exception as e:
            print("Error fetching report data: {}".format(e))
            return []

    def _get_actions(self, record):
        # Add a "Details" button to every row
        return [("Details", styles.PRIMARY, "white", self._show_details)]

    def _show_details(self, record):
        """Show a premium modal with full lifecycle history."""
        dialog = tk.Toplevel(self)
        dialog.title("Drawing Request Details")
        dialog.geometry("500x520")
        dialog.configure(bg="white")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        
        dialog.transient(self.winfo_toplevel())
        
        # Robust fix for "grab failed": delay grab until window is definitely mapped
        def _apply_grab():
            try:
                if dialog.winfo_exists():
                    dialog.grab_set()
            except: pass
        dialog.after(100, _apply_grab)

        # Center dialog
        dialog.update_idletasks()
        try:
            main_w = self.winfo_toplevel().winfo_width()
            main_h = self.winfo_toplevel().winfo_height()
            x = self.winfo_toplevel().winfo_rootx() + (main_w - 500) // 2
            y = self.winfo_toplevel().winfo_rooty() + (main_h - 520) // 2
            dialog.geometry("+%d+%d" % (x, y))
        except:
            pass

        # Header Area
        header = tk.Frame(dialog, bg=styles.DARK, height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="Drawing Lifecycle History", font=("Segoe UI", 16, "bold"),
                 fg="white", bg=styles.DARK).pack(anchor="w", padx=25, pady=(15, 0))
        tk.Label(header, text="Drawing No: %s (Rev: %s)" % (record.get('no'), record.get('rev')),
                 font=("Segoe UI", 10, "bold"), fg="#94a3b8", bg=styles.DARK).pack(anchor="w", padx=25, pady=(2, 0))

        # Content Container
        content = tk.Frame(dialog, bg="white", padx=30, pady=30)
        content.pack(fill="both", expand=True)

        # Determine second event label based on status
        status = record.get("status", "").lower()
        if status == "rejected":
            second_label = "Rejected"
            second_info = record.get("rej_info")
        else:
            second_label = "Issued"
            second_info = record.get("iss_info")

        events = [
            ("Requested", record.get("req_info"), "#3b82f6"),
            (second_label, second_info, "#ef4444" if status == "rejected" else "#10b981"),
            ("Returned", record.get("ret_info"), "#6366f1"),
            ("Received", record.get("rec_info"), "#10b981")
        ]

        for i, (label, info, color) in enumerate(events):
            frame = tk.Frame(content, bg="white")
            frame.pack(fill="x", pady=12)

            # Indicator Icon / Dot
            dot_canvas = tk.Canvas(frame, width=24, height=24, bg="white", highlightthickness=0)
            dot_canvas.pack(side="left", padx=(0, 15))
            
            # Draw vertical line if not last
            if i < len(events) - 1:
                dot_canvas.create_line(12, 12, 12, 24, fill="#e2e8f0", width=2)
            # Draw vertical line from top if not first
            if i > 0:
                dot_canvas.create_line(12, 0, 12, 12, fill="#e2e8f0", width=2)

            is_done = info and info != "—"
            dot_color = color if is_done else "#e2e8f0"
            dot_canvas.create_oval(6, 6, 18, 18, fill=dot_color, outline=dot_color)

            # Text Info
            text_frame = tk.Frame(frame, bg="white")
            text_frame.pack(side="left", fill="both")

            tk.Label(text_frame, text=label, font=("Segoe UI", 10, "bold"),
                     fg=styles.DARK if is_done else "#94a3b8", bg="white").pack(anchor="w")
            
            if is_done:
                # If it's the rejected info, clean it up
                clean_info = info
                if label == "Issued/Rejected" and record.get("status") == 'Rejected':
                    clean_info = record.get("rej_info")

                tk.Label(text_frame, text=clean_info, font=("Segoe UI", 9),
                         fg=styles.GRAY_TEXT, bg="white").pack(anchor="w")
            else:
                tk.Label(text_frame, text="Not reached yet", font=("Segoe UI", 9, "italic"),
                         fg="#cbd5e1", bg="white").pack(anchor="w")

        # Footer
        footer = tk.Frame(dialog, bg="white", pady=20)
        footer.pack(fill="x")

        ttk.Button(footer, text="Close", command=dialog.destroy, style="Flat.TButton").pack(side="bottom")

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent, button_silent=button_silent)
