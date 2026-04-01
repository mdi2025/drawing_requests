#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import datetime
import threading
from pages.table_component import CanvasDataTable
import styles
from db_handler import db


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

            query = """
 SELECT 
    m.catalog AS no, 
    m.revision AS rev, 
    m.approved_status AS status, 
    m.auto_id AS id,
    CASE 
        WHEN r.status IN ('Pending', 'Issued', 'Returned') THEN 
            CONCAT(u.admin_name, ' at ', DATE_FORMAT(r.requested_at, '%d-%m-%Y %H:%i:%s'))
        ELSE NULL
    END AS requested_by,
    CASE WHEN r.status IN ('Received', 'Rejected') THEN NULL ELSE r.status END AS req_status,
    CASE WHEN r.status IN ('Received', 'Rejected') THEN NULL ELSE r.bag_name END AS bag_name,
    CASE WHEN r.status IN ('Received', 'Rejected') THEN NULL ELSE r.ipd_catalog END AS ipd_catalog
FROM master_data_new m
JOIN (
    SELECT catalog, MAX(auto_id) AS max_auto_id
    FROM master_data_new
    WHERE approved_status = 'approved'
    GROUP BY catalog
) AS t ON m.catalog = t.catalog AND m.auto_id = t.max_auto_id
LEFT JOIN (
    SELECT r1.drawing_id, r1.revision, r1.requested_by, r1.requested_at, r1.status, r1.bag_name, r1.ipd_catalog
    FROM drawing_requests r1
    JOIN (
        SELECT drawing_id, revision, MAX(requested_at) AS max_ts
        FROM drawing_requests
        GROUP BY drawing_id, revision
    ) r2 ON r1.drawing_id = r2.drawing_id 
          AND r1.revision = r2.revision 
          AND r1.requested_at = r2.max_ts
) r ON r.drawing_id = m.catalog AND r.revision = m.revision
LEFT JOIN drawing_users u ON r.requested_by = u.id
WHERE r.status IS NULL 
   OR r.status = 'Pending'
   OR r.status = 'Issued'
   OR r.status = 'Returned'
   OR r.status = 'Received'
   OR r.status = 'Rejected'
ORDER BY m.catalog;
            """

            rows = db.fetch_all(query)
            return rows

        except Exception as e:
            print("Error fetching drawings: {}".format(e))
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

        # Check for existing requests
        check_query = """
            SELECT r.id, r.status, u.admin_name, DATE_FORMAT(r.requested_at, '%%d-%%m-%%Y %%H:%%i') as ts
            FROM drawing_requests r
            JOIN drawing_users u ON r.requested_by = u.id
            WHERE r.drawing_id = %s AND r.revision = %s
            AND r.status IN ('Pending', 'Issued', 'Returned')
        """
        existing = db.fetch_all(check_query, (catalog, revision))
        if existing:
            info = existing[0]
            self.refresh(reset_pagination=False)
            messagebox.showwarning(
                "Already Requested",
                "This drawing has already been requested by %s at %s."
                % (info["admin_name"], info["ts"]),
            )
            return

        # Always create new request (no update logic for rejected requests)
        insert_request = """
            INSERT INTO drawing_requests 
            (drawing_id, revision, requested_by, status, bag_name, ipd_catalog) 
            VALUES (%s, %s, %s, 'Pending', %s, %s)
        """
        params = (
            catalog,
            revision,
            self.user_id,
            ipd_data.get("bag_name"),
            ipd_data.get("catalog_no"),
        )

        request_id = db.execute_insert(insert_request, params)

        if request_id:
            # Save to drawing_request_history
            insert_history = """
                INSERT INTO drawing_request_history 
                (request_id, event_type, performed_by, revision) 
                VALUES (%s, 'requested', %s, %s)
            """
            db.execute_query(insert_history, (request_id, self.user_id, revision))

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
