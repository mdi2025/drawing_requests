#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import datetime
import threading

try:
    import styles
except ImportError:
    class DummyStyles:
        LIGHT = "#f8fafc"
        DARK = "#1e293b"
        PRIMARY = "#3b82f6"
        SECONDARY = "#64748b"
    styles = DummyStyles()

class DrawingRequestsPage(ttk.Frame):
    def __init__(self, parent, username="User"):
        ttk.Frame.__init__(self, parent, style="Card.TFrame", padding=25)
        self.username = username
        self.drawings = []
        self.filtered = []
        self.page_size = 12
        self.current_page = 0
        self.is_loading = False
        self.row_height = 42
        self.col_widths = [200, 100, 140, 300, 140]  # last one will stretch
        self.headers = ["Drawing ID", "Revision", "Status", "Requested By", "Action"]
        self.hover_row = -1
        self.hover_button = -1
        self.dragging_col = -1
        self._build_ui()
        self.update_idletasks()
        self._stretch_last_column()
        self.after(100, self._start_loading)

    def _stretch_last_column(self):
        fixed = sum(self.col_widths[:-1])
        canvas_w = self.canvas.winfo_width()
        if canvas_w > fixed + 40:
            self.col_widths[-1] = max(140, canvas_w - fixed)
        else:
            self.col_widths[-1] = 140  # minimum

    def _build_ui(self):
        header = tk.Frame(self, bg=styles.LIGHT)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="Drawing Requisitions", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Refresh", style="Flat.TButton",
                   command=self.refresh).pack(side="left", padx=20)

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(header, textvariable=self.search_var,
                                     font=("Segoe UI", 10), width=28,
                                     relief="solid", bd=1,
                                     highlightthickness=1, highlightbackground="#cbd5e1",
                                     highlightcolor=styles.PRIMARY,
                                     fg=styles.SECONDARY)
        self.search_entry.pack(side="right", ipady=6)
        self.search_entry.insert(0, "Search drawings...")
        self.search_entry.bind("<FocusIn>", self._clear_placeholder)
        self.search_entry.bind("<FocusOut>", self._restore_placeholder)
        self.search_var.trace("w", self._search_data)

        self.loading_label = ttk.Label(self, text="Loading data...",
                                       font=("Segoe UI", 12), foreground=styles.SECONDARY)

        table_frame = tk.Frame(self, bg="white", relief="solid", bd=1)
        table_frame.pack(expand=True, fill="both", pady=(0, 8))

        self.canvas = tk.Canvas(table_frame, bg="white", highlightthickness=0)
        self.vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        self.inner_frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Bindings
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_resize_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_resize_release)
        self.canvas.bind("<Leave>", self._on_canvas_leave)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        pager = tk.Frame(self, bg=styles.LIGHT, height=48)
        pager.pack(side="bottom", fill="x", pady=(8, 0))
        pager.pack_propagate(False)
        nav_frame = tk.Frame(pager, bg=styles.LIGHT)
        nav_frame.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Button(nav_frame, text="◀ Previous", style="Flat.TButton",
                   command=self._prev_page).pack(side="left", padx=10)
        self.page_label = ttk.Label(nav_frame, text="Page 1 of 1",
                                    font=("Segoe UI", 10, "bold"))
        self.page_label.pack(side="left", padx=24)
        ttk.Button(nav_frame, text="Next ▶", style="Flat.TButton",
                   command=self._next_page).pack(side="left", padx=10)

        self.records_label = tk.Label(pager, text="",
                                      font=("Segoe UI", 9), fg=styles.SECONDARY,
                                      bg=styles.LIGHT)
        self.records_label.place(relx=1.0, rely=0.5, anchor="e", x=-16)

        self.copy_feedback = tk.Label(self.canvas, text="Copied!", bg="#4ade80", fg="white",
                                      font=("Segoe UI", 9, "bold"), padx=8, pady=4)
        self.copy_feedback_id = None

    def _on_canvas_configure(self, event):
        self._stretch_last_column()
        self._redraw_table()

    def _clear_placeholder(self, event):
        if self.search_entry.get() == "Search drawings...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg="#0f172a")

    def _restore_placeholder(self, event):
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search drawings...")
            self.search_entry.config(fg=styles.SECONDARY)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _start_loading(self):
        if self.is_loading: return
        self.is_loading = True
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        thread = threading.Thread(target=self._fetch_data_thread, daemon=True)
        thread.start()

    def _fetch_data_thread(self):
        data = self._generate_data()
        self.after(0, lambda: self._on_data_ready(data))

    def _on_data_ready(self, data):
        self.drawings = data
        self.filtered = list(self.drawings)
        self.current_page = 0
        self.is_loading = False
        self.loading_label.place_forget()
        self._redraw_table()

    def _generate_data(self):
        try:
            import sys, os
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from db_handler import db

            query = """
                SELECT drawing_no as no,
                       latest_revision as rev,
                       current_status as status
                FROM drawings_master_bal
                WHERE current_status = 'Approved'
                LIMIT 200
            """
            rows = db.fetch_all(query) or []

            for row in rows:
                row['requested_by'] = ""

            return rows

        except Exception as e:
            print("Error fetching drawings: {}".format(e))
            return []

    def _truncate_text(self, text, max_width):
        if not text: return ""
        est = len(text) * 7.5
        if est <= max_width - 30: return text
        max_chars = int((max_width - 30) / 7.5)
        if len(text) > max_chars:
            return text[:max_chars-3] + "..."
        return text

    def _get_action_buttons(self, drawing):
        buttons = []
        if not drawing.get("requested_by"):
            buttons.append(("Request", styles.PRIMARY, "white", self._request_drawing))
        else:
            buttons.append(("Requested", "#e2e8f0", "#6b7280", None))
        return buttons

    def _redraw_table(self):
        self.canvas.delete("all")
        self.hover_row = -1
        self.hover_button = -1

        header_height = 38
        row_start = self.current_page * self.page_size
        page_data = self.filtered[row_start : row_start + self.page_size]

        # Header
        x = 0
        for i, head in enumerate(self.headers):
            w = self.col_widths[i]
            self.canvas.create_rectangle(x, 0, x + w, header_height,
                                        fill="#e5e7eb", outline="#d1d5db")
            self.canvas.create_text(x + w//2, header_height//2,
                                   text=head, fill="#374151",
                                   font=("Segoe UI", 10, "bold"), anchor="center")

            if i < len(self.headers) - 1:
                sep_x = x + w - 1
                # Visible thick line
                self.canvas.create_line(sep_x, 4, sep_x, header_height-4,
                                       fill="#9ca3af", width=4,
                                       tags=("separator", "sep%d" % i))
                # Wider invisible hit area (~36 px total)
                self.canvas.create_rectangle(sep_x - 18, 0, sep_x + 18, header_height,
                                            fill="", outline="",
                                            tags=("separator", "sep%d" % i, "sep_hit"))

            x += w

        # Rows
        y = header_height
        for local_idx, d in enumerate(page_data):
            global_idx = row_start + local_idx
            is_even = local_idx % 2 == 0
            row_bg = "#ffffff" if is_even else "#f8fafc"
            if global_idx == self.hover_row:
                row_bg = "#e0f2fe"

            x = 0
            values = [
                self._truncate_text(d.get("no", "—"), self.col_widths[0]),
                self._truncate_text(d.get("rev", "—"), self.col_widths[1]),
                self._truncate_text(str(d.get("status", "N/A")).upper(), self.col_widths[2]),
                self._truncate_text(d.get("requested_by", ""), self.col_widths[3]),
            ]

            for col_idx, val in enumerate(values):
                w = self.col_widths[col_idx]
                self.canvas.create_rectangle(x, y, x + w, y + self.row_height,
                                            fill=row_bg, outline="#e2e8f0", width=1,
                                            tags=("row%d" % global_idx, "cell"))
                padx = 12
                text_x = x + padx if col_idx in (0,3) else x + w//2
                anchor = "w" if col_idx in (0,3) else "center"
                fg = "#1f2937"
                if col_idx == 3 and d.get("requested_by"):
                    fg = "#4f46e5"
                font = ("Segoe UI", 10) if col_idx != 3 else ("Segoe UI", 9, "italic")
                self.canvas.create_text(text_x, y + self.row_height//2,
                                       text=val, fill=fg, font=font,
                                       anchor=anchor, tags=("row%d" % global_idx,))
                x += w

            # Action column
            w = self.col_widths[-1]
            self.canvas.create_rectangle(x, y, x + w, y + self.row_height,
                                        fill="#f9fafb", outline="#e2e8f0", width=1,
                                        tags=("row%d" % global_idx,))
            buttons = self._get_action_buttons(d)
            btn_count = len(buttons)
            btn_width = 100
            total_btns_w = btn_count * btn_width + (btn_count - 1) * 8
            btn_x = x + (w - total_btns_w) // 2
            btn_y = y + 8
            for btn_idx, (text, bg, fg_color, cb) in enumerate(buttons):
                hovered = (global_idx == self.hover_row and btn_idx == self.hover_button)
                bg_real = "#2563eb" if hovered and bg == styles.PRIMARY else bg
                outline = "#1d4ed8" if hovered else "#d1d5db"
                tags = ("action-btn-%d-%d" % (global_idx, btn_idx), "row%d" % global_idx)
                self.canvas.create_rectangle(btn_x, btn_y, btn_x + btn_width, btn_y + self.row_height - 16,
                                            fill=bg_real, outline=outline,
                                            width=2 if hovered else 1, tags=tags)
                self.canvas.create_text(btn_x + btn_width//2, btn_y + (self.row_height-16)//2,
                                       text=text, fill=fg_color,
                                       font=("Segoe UI", 9, "bold"), anchor="center", tags=tags)
                btn_x += btn_width + 8

            y += self.row_height

        total_height = header_height + len(page_data) * self.row_height
        self.canvas.config(scrollregion=(0, 0, sum(self.col_widths), total_height))

        total = len(self.filtered)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        curr = self.current_page + 1
        start = row_start + 1 if total > 0 else 0
        end = min(row_start + self.page_size, total)
        self.page_label.config(text="Page %d of %d" % (curr, total_pages))
        self.records_label.config(text="Showing %d–%d of %d records" % (start, end, total))

    def _on_canvas_motion(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        # Larger search area for better hit detection
        items = self.canvas.find_overlapping(cx-20, cy-20, cx+20, cy+20)

        new_row = -1
        new_btn = -1
        over_separator = False

        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("row"):
                    new_row = int(tag[3:])
                if tag.startswith("action-btn-"):
                    parts = tag.split("-")
                    new_row = int(parts[2])
                    new_btn = int(parts[3])
                if tag.startswith("sep"):
                    over_separator = True

        redraw_needed = (new_row != self.hover_row or new_btn != self.hover_button)
        self.hover_row = new_row
        self.hover_button = new_btn

        if redraw_needed:
            self._redraw_table()

        # Cursor priority
        if new_btn != -1:
            self.canvas.config(cursor="hand2")
        elif over_separator or self.dragging_col != -1:
            self.canvas.config(cursor="sb_h_double_arrow")
        else:
            self.canvas.config(cursor="")

    def _on_canvas_leave(self, event):
        if self.dragging_col == -1:
            self.hover_row = -1
            self.hover_button = -1
            self.canvas.config(cursor="")
            self._redraw_table()

    def _on_canvas_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        items = self.canvas.find_overlapping(cx-20, cy-20, cx+20, cy+20)

        # Separator check FIRST - highest priority
        for item in items:
            tags = self.canvas.gettags(item)
            if any(t.startswith("sep") for t in tags):
                for tag in tags:
                    if tag.startswith("sep") and tag[3:].isdigit():
                        col = int(tag[3:])
                        self.dragging_col = col
                        self.canvas.config(cursor="sb_h_double_arrow")
                        return

        # Action buttons
        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("action-btn-"):
                    parts = tag.split("-")
                    row_idx = int(parts[2])
                    btn_idx = int(parts[3])
                    if row_idx >= len(self.filtered): return
                    d = self.filtered[row_idx]
                    drawing_no = d.get("no", "")
                    buttons = self._get_action_buttons(d)
                    if btn_idx < len(buttons) and buttons[btn_idx][3]:
                        buttons[btn_idx][3](drawing_no)
                    return

        # Cell copy
        if cy >= 38:
            rel_y = cy - 38
            row_idx = int(rel_y // self.row_height) + self.current_page * self.page_size
            if row_idx >= len(self.filtered): return

            x_pos = 0
            col_idx = -1
            for i, w in enumerate(self.col_widths):
                if cx < x_pos + w:
                    col_idx = i
                    break
                x_pos += w

            keys = ["no", "rev", "status", "requested_by", None]
            key = keys[col_idx] if 0 <= col_idx < len(keys) else None
            if key:
                value = self.filtered[row_idx].get(key, "")
                if value and value != "—":
                    self.clipboard_clear()
                    self.clipboard_append(str(value))
                    self._show_copy_feedback(event.x, event.y)

    def _on_resize_drag(self, event):
        if self.dragging_col == -1:
            return
        cx = self.canvas.canvasx(event.x)
        prev = sum(self.col_widths[:self.dragging_col])
        new_w = max(60, cx - prev)
        self.col_widths[self.dragging_col] = new_w
        self._redraw_table()

    def _on_resize_release(self, event):
        self.dragging_col = -1
        self.canvas.config(cursor="")

    def _show_copy_feedback(self, sx, sy):
        if self.copy_feedback_id:
            self.canvas.after_cancel(self.copy_feedback_id)
            self.canvas.delete("copy_feedback")
        self.canvas.create_window(sx + 20, sy - 10,
                                 window=self.copy_feedback, anchor="nw",
                                 tags="copy_feedback")
        self.copy_feedback_id = self.canvas.after(1500, lambda: self.canvas.delete("copy_feedback"))

    def _search_data(self, *args):
        query = self.search_var.get().lower().strip()
        if query in ("", "search drawings..."):
            self.filtered = list(self.drawings)
        else:
            self.filtered = []
            for d in self.drawings:
                match = False
                for k in ("no", "rev", "status", "requested_by"):
                    if query in str(d.get(k, "")).lower():
                        match = True
                        break
                if match:
                    self.filtered.append(d)
        self.current_page = 0
        self._redraw_table()

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._redraw_table()

    def _next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered):
            self.current_page += 1
            self._redraw_table()

    def refresh(self):
        self._start_loading()

    def _request_drawing(self, drawing_no):
        confirm = messagebox.askyesno("Confirm Request",
                                      "Request drawing no %s?" % drawing_no)
        if not confirm:
            return
        now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        requested_text = "%s at %s" % (self.username, now)
        for d in self.drawings:
            if d.get("no") == drawing_no:
                d["requested_by"] = requested_text
                break
        self._redraw_table()
        messagebox.showinfo("Success", "Request submitted for %s" % drawing_no)