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
            return rows if rows else []
        except Exception as e:
            print("Error fetching requests: {}".format(e))
            return []

    def _get_actions(self, record):
        status = record.get("status")
        if status in ('Pending', 'open'):
            return [
                ("Issue", "#10b981", "white", self._handle_issue),
                ("Reject", "#ef4444", "white", self._handle_reject)
            ]
        elif status == 'Rejected':
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

    # ====================== NEW: Check latest revision on button click ======================
    def _handle_issue(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")
        requested_rev = record.get("rev")

        try:
            # Check latest approved revision from backend
            latest_query = """
                SELECT revision 
                FROM master_data_new 
                WHERE catalog = %s 
                  AND approved_status = 'approved'
                ORDER BY auto_id DESC 
                LIMIT 1
            """
            latest_data = db.fetch_all(latest_query, (drawing_no,))
            latest_rev = latest_data[0]['revision'] if latest_data else None

            # Case 1: No newer revision or same as requested
            if not latest_rev or str(requested_rev) == str(latest_rev):
                if messagebox.askyesno("Confirm Issue", 
                                       "Are you sure you want to issue drawing {}?".format(drawing_no)):
                    self._finish_issuance(record, requested_rev)
                return

            # Case 2: Newer revision available → Show modal
            self._show_revision_modal(record, requested_rev, latest_rev)

        except Exception as e:
            print("Error checking latest revision: {}".format(e))
            # Fallback: Issue the originally requested revision
            if messagebox.askyesno("Confirm Issue", 
                                   "Are you sure you want to issue drawing {}?".format(drawing_no)):
                self._finish_issuance(record, requested_rev)

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

        # Header
        header = tk.Frame(dialog, bg=styles.PRIMARY, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Choose Revision to Issue", 
                 font=("Segoe UI", 16, "bold"), fg="white", bg=styles.PRIMARY).pack(pady=15)

        # Body
        body = tk.Frame(dialog, bg="white", padx=30, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="A newer approved revision exists for this drawing.", 
                 font=("Segoe UI", 10), bg="white", fg=styles.DARK).pack(pady=(0, 20))

        # Info Box
        info_frame = tk.Frame(body, bg="#f8fafc", padx=15, pady=15, 
                              highlightthickness=1, highlightbackground="#e2e8f0")
        info_frame.pack(fill="x", pady=5)
        
        tk.Label(info_frame, text="Drawing No: {}".format(record.get("no")), 
                 font=("Segoe UI", 11, "bold"), bg="#f8fafc", fg=styles.DARK).pack(anchor="w")
        tk.Label(info_frame, text="Requested: Rev {}".format(req_rev), 
                 font=("Segoe UI", 10), bg="#f8fafc", fg=styles.GRAY_TEXT).pack(anchor="w", pady=(5, 0))
        tk.Label(info_frame, text="Latest: Rev {}".format(lat_rev), 
                 font=("Segoe UI", 10, "bold"), bg="#f8fafc", fg="#10b981").pack(anchor="w")

        # Selection Buttons
        btn_frame = tk.Frame(body, bg="white", pady=25)
        btn_frame.pack(fill="x")

        def issue_requested():
            dialog.destroy()
            self._finish_issuance(record, req_rev)

        def issue_latest():
            dialog.destroy()
            self._finish_issuance(record, lat_rev)

        # Buttons (appearance unchanged)
        btn_req = tk.Button(btn_frame, text="Issue Requested ({})".format(req_rev),
                            font=("Segoe UI", 9, "bold"), bg="#f1f5f9", fg=styles.DARK,
                            command=issue_requested, relief="flat", padx=15, pady=8)
        btn_req.pack(side="left", expand=True)

        btn_lat = tk.Button(btn_frame, text="Issue Latest ({})".format(lat_rev),
                            font=("Segoe UI", 9, "bold"), bg="#4f46e5", fg="white",
                            command=issue_latest, relief="flat", padx=15, pady=8)
        btn_lat.pack(side="right", expand=True)

    def _finish_issuance(self, record, target_rev):
        request_id = record.get("id")
        drawing_no = record.get("no")
        current_rev = record.get("rev")

        # Update revision if different
        if target_rev and str(target_rev) != str(current_rev):
            db.execute_query("UPDATE drawing_requests SET revision = %s WHERE id = %s", 
                           (target_rev, request_id))

        query = "UPDATE drawing_requests SET status = 'Issued' WHERE id = %s"
        if db.execute_query(query, (request_id,)):
            # Log history
            insert_history = """
                INSERT INTO drawing_request_history 
                (request_id, event_type, performed_by) 
                VALUES (%s, 'issued', %s)
            """
            db.execute_query(insert_history, (request_id, self.user_id or 1))

            msg = "Drawing {} (Rev {}) has been issued successfully.".format(drawing_no, target_rev)
            messagebox.showinfo("Issuance", msg)
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to update status in database.")

    def _handle_reject(self, record):
        request_id = record.get("id")
        drawing_no = record.get("no")
        
        if not messagebox.askyesno("Reject", 
                                   "Are you sure you want to reject the request for {}?".format(drawing_no)):
            return

        query = "UPDATE drawing_requests SET status = 'Rejected' WHERE id = %s"
        if db.execute_query(query, (request_id,)):
            insert_history = """
                INSERT INTO drawing_request_history 
                (request_id, event_type, performed_by) 
                VALUES (%s, 'rejected', %s)
            """
            db.execute_query(insert_history, (request_id, self.user_id or 1))

            messagebox.showinfo("Rejected", "Request for {} has been rejected.".format(drawing_no))
            self.refresh(reset_pagination=False)
        else:
            messagebox.showerror("Error", "Failed to update status in database.")

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(reset_pagination=reset_pagination, silent=silent, button_silent=button_silent)