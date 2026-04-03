#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import os
import stat
import zipfile
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
import urllib.request
import urllib.parse
import json

import styles
from pages.table_component import CanvasDataTable
from config import app_url as API_BASE_URL, api_timeout as API_TIMEOUT


class ReportsPage(ttk.Frame):
    def __init__(self, parent, username="User", user_id=None, on_data_ready=None):
        ttk.Frame.__init__(self, parent)

        self._cal_canvas = None

        # ================= DATE FILTER & EXPORT =================
        filter_frame = tk.Frame(self, bg="white")
        filter_frame.pack(fill="x", padx=10, pady=5)

        # ── Default date range: 1st of current month → today ──
        _today = datetime.now()
        _default_from = "%04d-%02d-01" % (_today.year, _today.month)
        _default_to = "%04d-%02d-%02d" % (_today.year, _today.month, _today.day)

        tk.Label(filter_frame, text="From:", bg="white").pack(side="left", padx=5)
        self.from_date_var = tk.StringVar(value=_default_from)
        self.from_entry = tk.Entry(
            filter_frame, textvariable=self.from_date_var, width=12
        )
        self.from_entry.pack(side="left")
        self.from_entry.bind(
            "<Button-1>",
            lambda e: self._show_calendar(self.from_entry, self.from_date_var),
        )

        tk.Label(filter_frame, text="To:", bg="white").pack(side="left", padx=5)
        self.to_date_var = tk.StringVar(value=_default_to)
        self.to_entry = tk.Entry(filter_frame, textvariable=self.to_date_var, width=12)
        self.to_entry.pack(side="left")
        self.to_entry.bind(
            "<Button-1>", lambda e: self._show_calendar(self.to_entry, self.to_date_var)
        )

        # ====== Status Filter ======
        tk.Label(filter_frame, text="Status:", bg="white").pack(side="left", padx=(15, 5))
        self.status_var = tk.StringVar(value="All")
        self.status_cb = ttk.Combobox(
            filter_frame, 
            textvariable=self.status_var,
            values=["All", "Pending", "Issued", "Rejected", "Received", "Returned"],
            state="readonly",
            width=10
        )
        self.status_cb.pack(side="left")

        # Apply Filter Button (Blue)
        apply_btn = tk.Button(
            filter_frame,
            text="Apply Filter",
            command=self.refresh,
            bg="#3b82f6",
            fg="white",
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
            text="Export Excel (.xls)",
            command=self._export_xls,
            bg="#16a34a",
            fg="white",
            activebackground="#15803d",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=3,
        )
        export_btn.pack(side="left", padx=5)

        # ================= TABLE =================
        self.table = CanvasDataTable(
            self,
            title="Drawing Lifecycle Report",
            headers=[
                "SNo",
                "Drawing ID",
                "Rev",
                "Bag Name",
                "Catalog",
                "Status",
                "Remarks",
                "Issue Info",
                "Action",
            ],
            initial_widths=[60, 140, 60, 120, 120, 100, 180, 220, 120],
            fetch_data_func=self._fetch_report_data,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search records / history...",
            search_keys=[
                "no",
                "rev",
                "status",
                "bag_name",
                "ipd_catalog",
                "remarks",
                "req_info",
                "iss_info",
                "ret_info",
                "rec_info",
                "rej_info",
            ],
            cell_formatters={5: self._format_status, 6: self._format_remarks, 7: self._format_info},
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
            "iss_info",
        ]
        self.table.pack(expand=True, fill="both")
        # ================= FAST CANVAS CALENDAR =================

    def _show_calendar(self, widget, target_var):
        import calendar

        if self._cal_canvas:
            self._cal_canvas.destroy()

        self._cal_canvas = tk.Canvas(
            self, width=220, height=260, bg="white", highlightthickness=1
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
                        selected = "%04d-%02d-%02d" % (
                            self.cal_year,
                            self.cal_month,
                            day,
                        )

                        # ── Validate: from < to ──
                        if target_var is self.from_date_var:
                            to_val = self.to_date_var.get()
                            if to_val and selected > to_val:
                                messagebox.showwarning(
                                    "Invalid Date",
                                    "Start date cannot be greater than end date.\nPlease select a smaller date.",
                                )
                                return  # keep calendar open for re-selection

                        elif target_var is self.to_date_var:
                            from_val = self.from_date_var.get()
                            if from_val and selected < from_val:
                                messagebox.showwarning(
                                    "Invalid Date",
                                    "End date cannot be smaller than start date.\nPlease select a larger date.",
                                )
                                return  # keep calendar open for re-selection

                        target_var.set(selected)
                        self._cal_canvas.destroy()
                        self._cal_canvas = None
                        return

        self._cal_canvas.bind("<Button-1>", click)
        draw()

    # ================= EXPORT (XLS - Excel 97-2003, no packages needed) =================
    def _export_xls(self):
        """
        Exports as HTML table saved as .xls
        """
        try:
            f = self.from_date_var.get() or "start"
            t = self.to_date_var.get() or "end"
            default_name = "drawing_request_report_%s_to_%s.xls" % (f, t)

            path = filedialog.asksaveasfilename(
                defaultextension=".xls",
                initialfile=default_name,
                filetypes=[("Excel 97-2003 files", "*.xls")],
            )
            if not path:
                return

            data = self._fetch_report_data()

            headers = [
                "SNo",
                "Drawing ID",
                "Rev",
                "Bag Name",
                "Catalog",
                "Status",
                "Remarks",
                "Requested",
                "Issued",
                "Returned",
                "Received",
            ]

            def esc(val):
                if val is None:
                    return ""
                s = str(val)
                s = s.replace("&", "&amp;")
                s = s.replace("<", "&lt;")
                s = s.replace(">", "&gt;")
                s = s.replace('"', "&quot;")
                return s

            lines = []
            lines.append('<html xmlns:o="urn:schemas-microsoft-com:office:office"')
            lines.append('      xmlns:x="urn:schemas-microsoft-com:office:excel"')
            lines.append('      xmlns="http://www.w3.org/TR/REC-html40">')
            lines.append("<head>")
            lines.append(
                '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>'
            )
            lines.append("<!--[if gte mso 9]>")
            lines.append("<xml>")
            lines.append(" <o:DocumentProperties>")
            lines.append("  <o:ReadOnlyRecommended/>")
            lines.append(" </o:DocumentProperties>")
            lines.append(" <x:ExcelWorkbook>")
            lines.append("  <x:ProtectStructure>True</x:ProtectStructure>")
            lines.append("  <x:ExcelWorksheets>")
            lines.append("   <x:ExcelWorksheet>")
            lines.append("    <x:Name>Report</x:Name>")
            lines.append("    <x:WorksheetOptions>")
            lines.append("     <x:DisplayGridlines/>")
            lines.append("     <x:ProtectContents>True</x:ProtectContents>")
            lines.append("    </x:WorksheetOptions>")
            lines.append("   </x:ExcelWorksheet>")
            lines.append("  </x:ExcelWorksheets>")
            lines.append(" </x:ExcelWorkbook>")
            lines.append("</xml>")
            lines.append("<![endif]-->")
            lines.append("<style>")
            lines.append(
                "  table { border-collapse: collapse; font-family: Arial; font-size: 10pt; }"
            )
            lines.append("  th {")
            lines.append("    background-color: #4472C4;")
            lines.append("    color: #FFFFFF;")
            lines.append("    font-weight: bold;")
            lines.append("    border: 1px solid #000000;")
            lines.append("    padding: 4px 8px;")
            lines.append("    text-align: center;")
            lines.append("  }")
            lines.append("  td {")
            lines.append("    border: 1px solid #000000;")
            lines.append("    padding: 3px 6px;")
            lines.append("    vertical-align: middle;")
            lines.append("  }")
            lines.append("  tr:nth-child(even) td { background-color: #F2F2F2; }")
            lines.append("  tr:nth-child(odd)  td { background-color: #FFFFFF; }")
            lines.append("</style>")
            lines.append("</head>")
            lines.append("<body>")
            lines.append("<table>")

            # Header row
            lines.append(" <thead><tr>")
            for h in headers:
                lines.append("  <th>%s</th>" % esc(h))
            lines.append(" </tr></thead>")

            # Data rows
            lines.append(" <tbody>")
            for idx, rdata in enumerate(data, 1):
                vals = [
                    str(idx),
                    rdata.get("no") or "",
                    rdata.get("rev") or "",
                    rdata.get("bag_name") or "",
                    rdata.get("ipd_catalog") or "",
                    rdata.get("status") or "",
                    rdata.get("remarks") or "",
                    rdata.get("req_info") or "",
                    rdata.get("iss_info") or "",
                    rdata.get("ret_info") or "",
                    rdata.get("rec_info") or "",
                ]
                lines.append("  <tr>")
                for v in vals:
                    lines.append("   <td>%s</td>" % esc(v))
                lines.append("  </tr>")
            lines.append(" </tbody>")

            lines.append("</table>")
            lines.append("</body>")
            lines.append("</html>")

            content = "\n".join(lines)

            # ── Force Overwrite if exists (restore write permission) ──
            if os.path.exists(path):
                try:
                    os.chmod(
                        path, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH
                    )
                except:
                    pass

            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)

            # ── Strictly Read-Only ──
            try:
                os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            except:
                pass

            messagebox.showinfo(
                "Success",
                "Excel Exported successfully"
            )

        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ================= DATA =================
    def _fetch_report_data(self):
        try:
            f = self.from_date_var.get()
            t = self.to_date_var.get()

            status_filter = getattr(self, "status_var", None)
            selected_status = status_filter.get() if status_filter else "All"

            # Prepare API request
            data = urllib.parse.urlencode({
                'action': 'get_report_data',
                'from_date': f,
                'to_date': t,
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
            print("Network error fetching report data: {}".format(e))
            return []
        except json.JSONDecodeError as e:
            print("JSON parse error: {}".format(e))
            print("Raw response: {}".format(raw_response if 'raw_response' in locals() else 'N/A'))
            return []
        except Exception as e:
            print("Error fetching report data: {}".format(e))
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
        if col_idx == 6:  # Remarks column
            remarks = record.get("remarks")
            if remarks:
                self._show_remarks_modal(record.get("no"), remarks)

    def _format_info(self, val, record):
        color = "#dc3545" if record["status"].upper() == "REJECTED" else "#000"
        return val or "—", color, ("Segoe UI", 9), "w"

    # ================= ACTIONS =================
    def _get_actions(self, record):
        return [("Details", styles.PRIMARY, "white", self._show_details)]

    def _show_remarks_modal(self, drawing_no, remarks):
        dialog = tk.Toplevel(self)
        dialog.title("Remarks")
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

    # ================= DETAILS MODAL =================
    def _show_details(self, record):
        """Show a premium modal with full lifecycle history."""
        dialog = tk.Toplevel(self)
        dialog.title("Drawing Request Details")
        dialog.geometry("500x600")
        dialog.configure(bg="white")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())

        dialog.transient(self.winfo_toplevel())

        # Robust fix for "grab failed": delay grab until window is definitely mapped
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
            x = self.winfo_toplevel().winfo_rootx() + (main_w - 500) // 2
            y = self.winfo_toplevel().winfo_rooty() + (main_h - 600) // 2
            dialog.geometry("+%d+%d" % (x, y))
        except:
            pass

        # Header Area
        header = tk.Frame(dialog, bg=styles.DARK, height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Drawing Lifecycle History",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg=styles.DARK,
        ).pack(anchor="w", padx=25, pady=(15, 0))
        tk.Label(
            header,
            text="Drawing No: %s (Rev: %s)" % (record.get("no"), record.get("rev")),
            font=("Segoe UI", 10, "bold"),
            fg="#94a3b8",
            bg=styles.DARK,
        ).pack(anchor="w", padx=25, pady=(2, 0))

        # Content Container - Scrollable Area
        container = tk.Frame(dialog, bg="white")
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white", padx=30, pady=25)

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", _on_frame_configure)

        # Create window inside canvas
        # Width is dialog width (500) minus scrollbar width (approx 20)
        canvas_window = canvas.create_window(
            (0, 0), window=scrollable_frame, anchor="nw", width=480
        )

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel support
        def _on_mousewheel(event):
            if canvas.winfo_exists():
                if event.num == 4:  # Linux scroll up
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:  # Linux scroll down
                    canvas.yview_scroll(1, "units")
                else:  # Windows/macOS
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        dialog.bind_all("<MouseWheel>", _on_mousewheel)
        dialog.bind_all("<Button-4>", _on_mousewheel)
        dialog.bind_all("<Button-5>", _on_mousewheel)

        def _on_destroy(event):
            # Only unbind if it's the dialog itself being destroyed
            if str(event.widget) == str(dialog):
                dialog.unbind_all("<MouseWheel>")
                dialog.unbind_all("<Button-4>")
                dialog.unbind_all("<Button-5>")

        dialog.bind("<Destroy>", _on_destroy)

        # Re-assign 'content' to 'scrollable_frame' for compatibility
        content = scrollable_frame

        # ── Request Info Section (PREMIUM LOOK) ──
        info_section = tk.Frame(
            content,
            bg="#f8fafc",
            padx=15,
            pady=15,
            highlightthickness=1,
            highlightbackground="#e2e8f0",
        )
        info_section.pack(fill="x", pady=(0, 15))

        # Helper to add rows
        def add_info_row(parent, row, label, value, val_color="#1e293b"):
            tk.Label(
                parent,
                text=label,
                font=("Segoe UI", 9, "bold"),
                fg="#64748b",
                bg="#f8fafc",
            ).grid(row=row, column=0, sticky="w", pady=2)
            tk.Label(
                parent,
                text=value or "N/A",
                font=("Segoe UI", 10, "bold"),
                fg=val_color,
                bg="#f8fafc",
            ).grid(row=row, column=1, sticky="w", padx=(15, 0), pady=2)

        add_info_row(info_section, 0, "Bag Name:", record.get("bag_name"))
        add_info_row(info_section, 1, "Catalog:", record.get("ipd_catalog"))

        if record.get("remarks"):
            tk.Label(
                info_section,
                text="Remarks:",
                font=("Segoe UI", 9, "bold"),
                fg="#64748b",
                bg="#f8fafc",
            ).grid(row=2, column=0, sticky="nw", pady=(10, 0))
            tk.Label(
                info_section,
                text=record.get("remarks"),
                font=("Segoe UI", 9),
                fg="#ef4444",
                bg="#f8fafc",
                wraplength=300,
                justify="left",
            ).grid(row=2, column=1, sticky="w", padx=(15, 0), pady=(10, 0))

        # Lifecycle Title
        tk.Label(
            content,
            text="LIFECYCLE HISTORY",
            font=("Segoe UI", 8, "bold"),
            fg="#94a3b8",
            bg="white",
        ).pack(anchor="w", pady=(10, 5))

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
            (
                second_label,
                second_info,
                "#ef4444" if status == "rejected" else "#10b981",
            ),
            ("Returned", record.get("ret_info"), "#6366f1"),
            ("Received", record.get("rec_info"), "#10b981"),
        ]

        for i, (label, info, color) in enumerate(events):
            frame = tk.Frame(content, bg="white")
            frame.pack(fill="x", pady=12)

            # Indicator Icon / Dot
            dot_canvas = tk.Canvas(
                frame, width=24, height=24, bg="white", highlightthickness=0
            )
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

            tk.Label(
                text_frame,
                text=label,
                font=("Segoe UI", 10, "bold"),
                fg=styles.DARK if is_done else "#94a3b8",
                bg="white",
            ).pack(anchor="w")

            if is_done:
                # If it's the rejected info, clean it up
                clean_info = info
                if label == "Issued/Rejected" and record.get("status") == "Rejected":
                    clean_info = record.get("rej_info")

                tk.Label(
                    text_frame,
                    text=clean_info,
                    font=("Segoe UI", 9),
                    fg=styles.GRAY_TEXT,
                    bg="white",
                ).pack(anchor="w")
            else:
                tk.Label(
                    text_frame,
                    text="Not reached yet",
                    font=("Segoe UI", 9, "italic"),
                    fg="#cbd5e1",
                    bg="white",
                ).pack(anchor="w")

        # Footer
        footer = tk.Frame(dialog, bg="white", pady=20)
        footer.pack(fill="x")

        ttk.Button(
            footer, text="Close", command=dialog.destroy, style="Flat.TButton"
        ).pack(side="bottom")

    # ================= REFRESH =================
    def refresh(self, *args, **kwargs):
        self.table.refresh()
