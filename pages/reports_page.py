#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import zipfile
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils

import styles
from pages.table_component import CanvasDataTable
from db_handler import db


class ReportsPage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None, on_data_ready=None):
        ttk.Frame.__init__(self, parent)

        self._cal_canvas = None

        # ================= DATE FILTER & EXPORT =================
        filter_frame = tk.Frame(self, bg="white")
        filter_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(filter_frame, text="From:", bg="white").pack(side="left", padx=5)
        self.from_date_var = tk.StringVar()
        self.from_entry = tk.Entry(
            filter_frame, textvariable=self.from_date_var, width=12
        )
        self.from_entry.pack(side="left")
        self.from_entry.bind(
            "<Button-1>",
            lambda e: self._show_calendar(self.from_entry, self.from_date_var),
        )

        tk.Label(filter_frame, text="To:", bg="white").pack(side="left", padx=5)
        self.to_date_var = tk.StringVar()
        self.to_entry = tk.Entry(filter_frame, textvariable=self.to_date_var, width=12)
        self.to_entry.pack(side="left")
        self.to_entry.bind(
            "<Button-1>", lambda e: self._show_calendar(self.to_entry, self.to_date_var)
        )

        # Apply Filter Button (Blue)
        apply_btn = tk.Button(
            filter_frame,
            text="Apply Filter",
            command=self.refresh,
            bg="#3b82f6",  # Blue background
            fg="white",  # White text
            activebackground="#2563eb",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=3,
        )
        apply_btn.pack(side="left", padx=10)

        # Export Button (Blue, aligned with filter)
        export_btn = tk.Button(
            filter_frame,
            text="Export Excel (.xlsx)",
            command=self._export_xlsx,
            bg="#3b82f6",
            fg="white",
            activebackground="#2563eb",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=3,
        )
        export_btn.pack(side="right")

        # ================= TABLE =================
        self.table = CanvasDataTable(
            self,
            title="Drawing Lifecycle Report",
            headers=["SNo", "Drawing ID", "Rev", "Status", "Issue Info", "Action"],
            initial_widths=[60, 180, 80, 140, 250, 150],
            fetch_data_func=self._fetch_report_data,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search records / history...",
            search_keys=[
                "no",
                "rev",
                "status",
                "req_info",
                "iss_info",
                "ret_info",
                "rec_info",
                "rej_info",
            ],
            cell_formatters={3: self._format_status, 4: self._format_info},
            on_data_ready_callback=on_data_ready,
        )

        self.table.data_keys = ["id", "no", "rev", "status", "iss_info"]
        self.table.pack(expand=True, fill="both")

    # ================= FAST CANVAS CALENDAR =================
    def _show_calendar(self, widget, target_var):
        import calendar

        if self._cal_canvas:
            self._cal_canvas.destroy()

        self._cal_canvas = tk.Canvas(
            self, width=220, height=220, bg="white", highlightthickness=1
        )

        x = widget.winfo_rootx() - self.winfo_rootx()
        y = widget.winfo_rooty() - self.winfo_rooty() + widget.winfo_height()
        self._cal_canvas.place(x=x, y=y)

        now = datetime.now()
        self.cal_year = now.year
        self.cal_month = now.month

        self.cell_map = {}

        def draw():
            self._cal_canvas.delete("all")
            self.cell_map.clear()

            title = "%s %d" % (calendar.month_name[self.cal_month], self.cal_year)
            self._cal_canvas.create_text(
                110, 15, text=title, font=("Segoe UI", 10, "bold")
            )

            # arrows
            self._cal_canvas.create_text(
                20, 15, text="<", font=("Segoe UI", 10, "bold")
            )
            self._cal_canvas.create_text(
                200, 15, text=">", font=("Segoe UI", 10, "bold")
            )

            days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
            for i, d in enumerate(days):
                self._cal_canvas.create_text(20 + i * 30, 40, text=d)

            cal = calendar.monthcalendar(self.cal_year, self.cal_month)

            y = 60
            for week in cal:
                x = 10
                for d in week:
                    if d != 0:
                        rect = self._cal_canvas.create_rectangle(
                            x, y, x + 25, y + 25, fill="#f1f5f9"
                        )
                        txt = self._cal_canvas.create_text(x + 12, y + 12, text=str(d))
                        self.cell_map[(rect, txt)] = d
                    x += 30
                y += 30

        def click(event):
            x, y = event.x, event.y

            # prev
            if 10 < x < 30 and 5 < y < 25:
                self.cal_month -= 1
                if self.cal_month == 0:
                    self.cal_month = 12
                    self.cal_year -= 1
                draw()
                return

            # next
            if 190 < x < 210 and 5 < y < 25:
                self.cal_month += 1
                if self.cal_month == 13:
                    self.cal_month = 1
                    self.cal_year += 1
                draw()
                return

            items = self._cal_canvas.find_overlapping(x, y, x, y)
            for item in items:
                for (rect, txt), day in self.cell_map.items():
                    if item == rect or item == txt:
                        target_var.set(
                            "%04d-%02d-%02d" % (self.cal_year, self.cal_month, day)
                        )
                        self._cal_canvas.destroy()
                        self._cal_canvas = None
                        return

        self._cal_canvas.bind("<Button-1>", click)
        draw()

    # ================= EXPORT =================
    def _export_xlsx(self):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".xlsx")
            if not path:
                return

            data = self._fetch_report_data()

            def create_cell(val, r, c):
                el = ET.Element("c", {"r": "%s%d" % (c, r), "t": "inlineStr"})
                is_el = ET.SubElement(el, "is")
                t = ET.SubElement(is_el, "t")
                t.text = saxutils.escape(str(val) if val is not None else "")
                return el

            worksheet = ET.Element(
                "worksheet",
                {"xmlns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"},
            )
            sheetData = ET.SubElement(worksheet, "sheetData")

            headers = [
                "SNo",
                "Drawing ID",
                "Rev",
                "Status",
                "Requested",
                "Issued",
                "Returned",
                "Received",
                "Rejected",
            ]

            row = ET.SubElement(sheetData, "row", {"r": "1"})
            for i, h in enumerate(headers):
                row.append(create_cell(h, 1, chr(65 + i)))

            for idx, rdata in enumerate(data, 2):
                row = ET.SubElement(sheetData, "row", {"r": str(idx)})
                vals = [
                    idx - 1,
                    rdata.get("no"),
                    rdata.get("rev"),
                    rdata.get("status"),
                    rdata.get("req_info"),
                    rdata.get("iss_info"),
                    rdata.get("ret_info"),
                    rdata.get("rec_info"),
                    rdata.get("rej_info"),
                ]
                for i, v in enumerate(vals):
                    row.append(create_cell(v, idx, chr(65 + i)))

            sheet_xml = b'<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(
                worksheet
            )

            workbook = ET.Element(
                "workbook",
                {
                    "xmlns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                    "xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
                },
            )
            sheets = ET.SubElement(workbook, "sheets")
            ET.SubElement(
                sheets, "sheet", {"name": "Sheet1", "sheetId": "1", "r:id": "rId1"}
            )
            workbook_xml = b'<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(
                workbook
            )

            content_types = ET.Element(
                "Types",
                {
                    "xmlns": "http://schemas.openxmlformats.org/package/2006/content-types"
                },
            )
            ET.SubElement(
                content_types,
                "Default",
                {
                    "Extension": "rels",
                    "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
                },
            )
            ET.SubElement(
                content_types,
                "Default",
                {"Extension": "xml", "ContentType": "application/xml"},
            )
            ET.SubElement(
                content_types,
                "Override",
                {
                    "PartName": "/xl/workbook.xml",
                    "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
                },
            )
            ET.SubElement(
                content_types,
                "Override",
                {
                    "PartName": "/xl/worksheets/sheet1.xml",
                    "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
                },
            )
            content_types_xml = b'<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(
                content_types
            )

            rels = ET.Element(
                "Relationships",
                {
                    "xmlns": "http://schemas.openxmlformats.org/package/2006/relationships"
                },
            )
            ET.SubElement(
                rels,
                "Relationship",
                {
                    "Id": "rId1",
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
                    "Target": "xl/workbook.xml",
                },
            )
            rels_xml = b'<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(rels)

            workbook_rels = ET.Element(
                "Relationships",
                {
                    "xmlns": "http://schemas.openxmlformats.org/package/2006/relationships"
                },
            )
            ET.SubElement(
                workbook_rels,
                "Relationship",
                {
                    "Id": "rId1",
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                    "Target": "worksheets/sheet1.xml",
                },
            )
            workbook_rels_xml = b'<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(
                workbook_rels
            )

            z = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED)
            z.writestr("[Content_Types].xml", content_types_xml)
            z.writestr("_rels/.rels", rels_xml)
            z.writestr("xl/workbook.xml", workbook_xml)
            z.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
            z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
            z.close()

            messagebox.showinfo("Success", "Excel exported successfully!")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ================= DATA =================
    def _fetch_report_data(self):
        try:
            f = self.from_date_var.get()
            t = self.to_date_var.get()

            date_filter = ""
            if f and t:
                date_filter = "WHERE DATE(h_req.performed_at) BETWEEN '%s' AND '%s'" % (
                    f,
                    t,
                )

            query = """
                SELECT 
                    r.id,
                    r.drawing_id AS no,
                    r.revision AS rev,
                    r.status,
                    h_req.performed_at AS req_time,
                    u_req.admin_name AS req_name,
                    h_iss.performed_at AS iss_time,
                    u_iss.admin_name AS iss_name,
                    h_ret.performed_at AS ret_time,
                    u_ret.admin_name AS ret_name,
                    h_rec.performed_at AS rec_time,
                    u_rec.admin_name AS rec_name,
                    h_rej.performed_at AS rej_time,
                    u_rej.admin_name AS rej_name
                FROM drawing_requests r
                LEFT JOIN drawing_request_history h_req 
                    ON r.id = h_req.request_id AND h_req.event_type = 'requested'
                LEFT JOIN drawing_users u_req 
                    ON h_req.performed_by = u_req.id

                LEFT JOIN drawing_request_history h_iss 
                    ON r.id = h_iss.request_id AND h_iss.event_type = 'issued'
                LEFT JOIN drawing_users u_iss 
                    ON h_iss.performed_by = u_iss.id

                LEFT JOIN drawing_request_history h_ret 
                    ON r.id = h_ret.request_id AND h_ret.event_type = 'returned'
                LEFT JOIN drawing_users u_ret 
                    ON h_ret.performed_by = u_ret.id

                LEFT JOIN drawing_request_history h_rec 
                    ON r.id = h_rec.request_id AND h_rec.event_type = 'received'
                LEFT JOIN drawing_users u_rec 
                    ON h_rec.performed_by = u_rec.id

                LEFT JOIN drawing_request_history h_rej 
                    ON r.id = h_rej.request_id AND h_rej.event_type = 'rejected'
                LEFT JOIN drawing_users u_rej 
                    ON h_rej.performed_by = u_rej.id
            """

            if date_filter:
                query += " " + date_filter

            query += " ORDER BY r.id DESC LIMIT 1000"

            rows = db.fetch_all(query)

            formatted_rows = []
            for row in rows:

                def format_time(name, time):
                    if time:
                        return "%s at %s" % (name, time.strftime("%d-%m-%Y %H:%M"))
                    return "—"

                formatted_rows.append(
                    {
                        "id": row["id"],
                        "no": row["no"],
                        "rev": row["rev"],
                        "status": row["status"],
                        "req_info": format_time(row["req_name"], row["req_time"]),
                        "iss_info": format_time(row["iss_name"], row["iss_time"]),
                        "ret_info": format_time(row["ret_name"], row["ret_time"]),
                        "rec_info": format_time(row["rec_name"], row["rec_time"]),
                        "rej_info": format_time(row["rej_name"], row["rej_time"]),
                    }
                )

                if row["status"].upper() == "REJECTED" and row["rej_time"]:
                    formatted_rows[-1]["iss_info"] = "REJECTED"

            return formatted_rows

        except Exception as e:
            print("Error:", str(e))
            return []

    # ================= FORMATTERS =================
    def _format_status(self, val, record):
        val_upper = str(val).upper()
        color = (
            "#28a745"
            if val_upper == "ISSUED"
            else "#dc3545" if val_upper == "REJECTED" else "#000"
        )
        return val_upper, color, ("Segoe UI", 9, "bold"), "center"

    def _format_info(self, val, record):
        color = "#dc3545" if record["status"].upper() == "REJECTED" else "#000"
        return val or "—", color, ("Segoe UI", 9), "w"

    # ================= ACTIONS =================
    def _get_actions(self, record):
        return [("Details", styles.PRIMARY, "white", self._show_details)]

    # ================= DETAILS MODAL =================
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
    # ================= REFRESH =================
    def refresh(self, *args, **kwargs):
        self.table.refresh()
