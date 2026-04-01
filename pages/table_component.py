#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
import threading
import datetime
import tkinter.font as tkfont

try:
    import styles
except ImportError:

    class DummyStyles:
        LIGHT = "#f8fafc"
        DARK = "#1e293b"
        PRIMARY = "#3b82f6"
        SECONDARY = "#64748b"

    styles = DummyStyles()


class CanvasDataTable(ttk.Frame):
    """
    A reusable, highly performant table component using tk.Canvas.
    Supports:
    - Custom columns and headers
    - Column resizing
    - Hover effects
    - Smooth scrolling
    - Cell copying to clipboard
    - Integrated Search & Pagination
    - Custom Action Buttons
    """

    def __init__(
        self,
        parent,
        title="Data Table",
        headers=None,
        initial_widths=None,
        page_size=12,
        fetch_data_func=None,
        get_action_buttons_func=None,
        search_placeholder="Search records...",
        search_keys=None,
        cell_formatters=None,
        data_keys=None,
        on_data_ready_callback=None,
        on_cell_click=None,
        non_copyable_cols=None,
    ):

        ttk.Frame.__init__(self, parent, style="Card.TFrame", padding=25)

        self.title = title

        # Identify ID/Auto ID columns to replace with S.No
        provided_headers = headers or ["ID", "Name", "Action"]
        self.headers = []
        self.id_col_index = -1
        for i, h in enumerate(provided_headers):
            if (
                h.lower() in ("id", "auto id", "sno", "s.no")
                and self.id_col_index == -1
            ):
                self.id_col_index = i
                self.headers.append("S.No")
            else:
                self.headers.append(h)

        self.col_widths = initial_widths or [100, 200, 150]
        self.page_size = page_size
        self.fetch_data_func = fetch_data_func
        self.get_action_buttons_func = get_action_buttons_func
        self.search_placeholder = search_placeholder
        self.search_keys = search_keys or []
        self.cell_formatters = cell_formatters or {}  # col_idx -> func
        self.on_data_ready_callback = on_data_ready_callback
        self.on_cell_click = on_cell_click
        self.non_copyable_cols = non_copyable_cols or []

        self.data = []
        self.filtered = []
        self.current_page = 0
        self.is_loading = False
        self.row_height = 42

        self.hover_row = -1
        self.hover_button = -1
        self.dragging_col = -1
        self.data_keys = data_keys or []

        # Sorting State
        self.sort_col_index = -1
        self.sort_ascending = True

        self._build_ui()
        # Remove update_idletasks() as it blocks the main thread during instantiation.
        # Defer stretching to when the widget is actually mapped and has a width.
        self.after(10, self._stretch_after_map)

    def _stretch_after_map(self):
        """Helper to stretch columns after the widget has been mapped/sized."""
        if self.winfo_width() > 1:
            self._stretch_last_column()
            self._redraw_table()
        else:
            # Re-schedule if still not mapped
            self.after(100, self._stretch_after_map)

    def _stretch_last_column(self):
        self.update_idletasks()  # Ensure dimensions are current
        fixed = sum(self.col_widths[:-1])
        canvas_w = self.canvas.winfo_width()

        # Fallback if canvas_w is still not yet determined
        if canvas_w <= 1:
            canvas_w = self.winfo_width() - 50

        min_last = 160  # slightly more space for action buttons
        if canvas_w > fixed + 10:
            self.col_widths[-1] = max(min_last, canvas_w - fixed)
        else:
            self.col_widths[-1] = min_last

    def _build_ui(self):
        # Header Area
        self.header_frame = tk.Frame(self, bg=styles.LIGHT)
        self.header_frame.pack(fill="x", pady=(0, 16))

        ttk.Label(self.header_frame, text=self.title, style="Title.TLabel").pack(side="left")

        # Action Buttons for Header (optional, usually Refresh)
        self.refresh_btn = ttk.Button(
            self.header_frame, text="Refresh", style="Flat.TButton", command=self.refresh
        )
        self.refresh_btn.pack(side="left", padx=20)

        # Search
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            self.header_frame,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
            width=28,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
            highlightcolor=styles.PRIMARY,
            fg=styles.SECONDARY,
        )
        self.search_entry.pack(side="right", ipady=6)
        self.search_entry.insert(0, self.search_placeholder)
        self.search_entry.bind("<FocusIn>", self._clear_placeholder)
        self.search_entry.bind("<FocusOut>", self._restore_placeholder)
        self.search_var.trace("w", self._search_data)

        self.loading_label = ttk.Label(
            self,
            text="Loading ....",
            font=("Segoe UI", 12),
            foreground=styles.SECONDARY,
        )

        table_frame = tk.Frame(self, bg="white", relief="solid", bd=1)
        table_frame.pack(expand=True, fill="both", pady=(0, 8))

        # Use grid for table_frame to accommodate both scrollbars
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(table_frame, bg="white", highlightthickness=0)
        self.vsb = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.canvas.yview
        )
        self.hsb = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.canvas.xview
        )

        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        # Bindings
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_resize_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_resize_release)
        self.canvas.bind("<Leave>", self._on_canvas_leave)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.canvas.bind(
            "<Button-4>", lambda e: self._handle_scroll(-1)
        )  # Linux Scroll Up
        self.canvas.bind(
            "<Button-5>", lambda e: self._handle_scroll(1)
        )  # Linux Scroll Down

        # Pager Area
        pager = tk.Frame(self, bg=styles.LIGHT, height=48)
        pager.pack(side="bottom", fill="x", pady=(8, 0))
        pager.pack_propagate(False)

        nav_frame = tk.Frame(pager, bg=styles.LIGHT)
        nav_frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Button(
            nav_frame, text="◀ Previous", style="Flat.TButton", command=self._prev_page
        ).pack(side="left", padx=10)
        self.page_label = ttk.Label(
            nav_frame, text="Page 1 of 1", font=("Segoe UI", 10, "bold")
        )
        self.page_label.pack(side="left", padx=24)
        ttk.Button(
            nav_frame, text="Next ▶", style="Flat.TButton", command=self._next_page
        ).pack(side="left", padx=10)

        self.records_label = tk.Label(
            pager, text="", font=("Segoe UI", 9), fg=styles.SECONDARY, bg=styles.LIGHT
        )
        self.records_label.place(relx=1.0, rely=0.5, anchor="e", x=-16)

        # Copy Feedback Overlay
        self.copy_feedback = tk.Label(
            self.canvas,
            text="Copied!",
            bg="#4ade80",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
        )
        self.copy_feedback_id = None

    def _on_canvas_configure(self, event):
        # Use event dimensions if possible for immediate measurement
        # Debounce the resize event to prevent rapid redraws
        if hasattr(self, "_resize_timer") and self._resize_timer:
            self.after_cancel(self._resize_timer)
        # Reduced debounce to 50ms for snappier response
        self._resize_timer = self.after(50, self._do_resize)

    def _do_resize(self):
        self._resize_timer = None
        self._stretch_last_column()
        self._redraw_table()

    def _clear_placeholder(self, event):
        if self.search_entry.get() == self.search_placeholder:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg="#0f172a")

    def _restore_placeholder(self, event):
        if not self.search_entry.get():
            self.search_entry.insert(0, self.search_placeholder)
            self.search_entry.config(fg=styles.SECONDARY)

    def _on_mousewheel(self, event):
        self._handle_scroll(int(-1 * (event.delta / 120)))

    def _on_shift_mousewheel(self, event):
        self._handle_hscroll(int(-1 * (event.delta / 120)))

    def _handle_scroll(self, amount):
        sr = self.canvas.cget("scrollregion")
        if not sr:
            return
        try:
            _, _, _, sr_h = [float(x) for x in sr.split()]
            canvas_h = self.canvas.winfo_height()
            if sr_h <= canvas_h + 1:  # Plus 1 for rounding
                return
            self.canvas.yview_scroll(amount, "units")
        except:
            pass

    def _handle_hscroll(self, amount):
        sr = self.canvas.cget("scrollregion")
        if not sr:
            return
        try:
            _, _, sr_w, _ = [float(x) for x in sr.split()]
            canvas_w = self.canvas.winfo_width()
            if sr_w <= canvas_w + 1:
                return
            self.canvas.xview_scroll(amount, "units")
        except:
            pass

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        if self.is_loading:
            return
        self.is_loading = True

        # Subtle loading state only if not silent
        if not silent:
            if not button_silent:
                self.refresh_btn.config(state="disabled", text="Refreshing...")

            # Show prominent loading label
            self.loading_label.place(relx=0.5, rely=0.5, anchor="center")

        thread = threading.Thread(
            target=self._load_data_thread,
            args=(reset_pagination, silent, button_silent),
            daemon=True,
        )
        if reset_pagination:
            self.canvas.yview_moveto(0)
        thread.start()

    def _load_data_thread(
        self, reset_pagination=True, silent=False, button_silent=False
    ):
        try:
            if self.fetch_data_func:
                data = self.fetch_data_func()
                self.after(
                    0,
                    lambda: self._on_data_ready(
                        data, reset_pagination, silent, button_silent
                    ),
                )
            else:
                self.after(
                    0,
                    lambda: self._on_data_ready(
                        [], reset_pagination, silent, button_silent
                    ),
                )
        except Exception as e:
            print("Error in fetch thread: {}".format(e))
            self.after(
                0, lambda: self.refresh_btn.config(state="normal", text="Refresh")
            )
            self.is_loading = False

    def _on_data_ready(
        self, data, reset_pagination=True, silent=False, button_silent=False
    ):
        self.data = data
        self.is_loading = False
        if not silent and not button_silent:
            self.refresh_btn.config(state="normal", text="Refresh")
        self.loading_label.place_forget()
        self._apply_search(reset_pagination)

        # Notify callback if this is the first time we got data
        if self.on_data_ready_callback:
            self.on_data_ready_callback()
            self.on_data_ready_callback = None  # Only once

    def _apply_search(self, reset_pagination=True):
        query = self.search_var.get().lower().strip()
        if query in ("", self.search_placeholder.lower()):
            self.filtered = list(self.data)
        else:
            self.filtered = []
            for d in self.data:
                match = False
                # If search_keys is provided, search specifically, otherwise all keys
                keys = self.search_keys if self.search_keys else d.keys()
                for k in keys:
                    if query in str(d.get(k, "")).lower():
                        match = True
                        break
                if match:
                    self.filtered.append(d)

        if reset_pagination:
            self.current_page = 0
            self.canvas.yview_moveto(0)
        else:
            # Clamp current_page to valid range for new data size
            total = len(self.filtered)
            max_p = max(0, (total - 1) // self.page_size)
            if self.current_page > max_p:
                self.current_page = max_p
                self.canvas.yview_moveto(0)

        self._redraw_table()

    def _search_data(self, *args):
        self._apply_search()

    def _truncate_text(self, text, max_width):
        if not text:
            return ""
        est = len(str(text)) * 7.5
        if est <= max_width - 30:
            return str(text)
        max_chars = int((max_width - 30) / 7.5)
        if len(str(text)) > max_chars:
            return str(text)[: max_chars - 3] + "..."
        return str(text)

    def _redraw_table(self):
        # Instead of delete("all"), we use tags to redraw and then delete old items
        # This prevents the "white flash" (flicker) during redraw.
        self.canvas.addtag_all("old_content")

        # Don't reset hover_row/button here if we want to preserve state during scroll
        # but for redraw (re-pagination), it's safer to reset or re-check.

        header_height = 38
        row_start = self.current_page * self.page_size
        page_data = self.filtered[row_start : row_start + self.page_size]

        # Draw Headers
        x = 0
        for i, head in enumerate(self.headers):
            w = self.col_widths[i]
            is_action = i == len(self.headers) - 1

            # Header background
            self.canvas.create_rectangle(
                x,
                0,
                x + w,
                header_height,
                fill="#e5e7eb",
                outline="#d1d5db",
                tags=("header", "head%d" % i),
            )

            # Text
            text_x = x + w // 2
            header_fg = "#1e293b"  # active header color
            header_font = ("Segoe UI", 10, "bold")

            if i == self.sort_col_index:
                header_fg = styles.PRIMARY
                # Draw sort indicator (arrow)
                arrow = " ▲" if self.sort_ascending else " ▼"
                display_head = head + arrow
            else:
                display_head = head

            self.canvas.create_text(
                text_x,
                header_height // 2,
                text=display_head,
                fill=header_fg,
                font=header_font,
                anchor="center",
                tags=("header", "head%d" % i),
            )

            if i < len(self.headers) - 1:
                sep_x = x + w - 1
                # Separator Line
                self.canvas.create_line(
                    sep_x,
                    4,
                    sep_x,
                    header_height - 4,
                    fill="#9ca3af",
                    width=4,
                    tags=("separator", "sep%d" % i),
                )
            x += w

        # Draw Rows
        y = header_height
        for local_idx, d in enumerate(page_data):
            global_idx = row_start + local_idx
            is_even = local_idx % 2 == 0
            row_bg = "#ffffff" if is_even else "#f8fafc"
            if global_idx == self.hover_row:
                row_bg = "#e0f2fe"

            x = 0
            # Rows are rendered based on data keys provided or inferred
            # For simplicity, we assume we have a way to map headers to data or vice versa
            # Better approach: pass a list of keys corresponding to headers (excluding Action)
            # For now, we'll use keys from data if not specified, but this is risky.
            # Let's assume the user passes a list of data_keys.

            # For this component, let's assume 'data_keys' is also an init param.
            # I'll add that to the class.

            x = 0
            for col_idx in range(len(self.headers) - 1):  # All except Action
                w = self.col_widths[col_idx]
                self.canvas.create_rectangle(
                    x,
                    y,
                    x + w,
                    y + self.row_height,
                    fill=row_bg,
                    outline="#e2e8f0",
                    width=1,
                    tags=("row%d" % global_idx, "row-bg-%d" % global_idx, "cell"),
                )

                # Get value - use serial number if this is the S.No column
                raw_val = ""
                if col_idx == self.id_col_index:
                    raw_val = str(global_idx + 1)
                    display_val = (raw_val, "#1f2937", ("Segoe UI", 10), "center")
                else:
                    if hasattr(self, "data_keys") and col_idx < len(self.data_keys):
                        key = self.data_keys[col_idx]
                        raw_val = d.get(key, "")

                    # Apply custom formatting if any
                    if col_idx in self.cell_formatters:
                        display_val = self.cell_formatters[col_idx](raw_val, d)
                    else:
                        display_val = raw_val

                padx = 12
                # Defaults
                anchor = "w"
                text_x = x + padx
                fg = "#1f2937"
                font = ("Segoe UI", 10)

                # Specific styling if provided by formatter? or just hardcoded for now?
                # Let's allow formatters to return (text, fg, font, anchor)
                if isinstance(display_val, tuple):
                    val_text, fg, font, anchor = display_val
                    if anchor == "center":
                        text_x = x + w // 2
                else:
                    val_text = display_val

                self.canvas.create_text(
                    text_x,
                    y + self.row_height // 2,
                    text=self._truncate_text(val_text, w),
                    fill=fg,
                    font=font,
                    anchor=anchor,
                    tags=("row%d" % global_idx,),
                )
                x += w

            # Action Column
            w = self.col_widths[-1]
            # Draw a slightly wider background to prevent white gaps during resize
            bg_w = max(w, self.canvas.winfo_width() - x)
            # Use 'action-bg' tag for full row hover effect
            action_row_bg = "#f9fafb" if global_idx != self.hover_row else "#e0f2fe"
            self.canvas.create_rectangle(
                x,
                y,
                x + bg_w,
                y + self.row_height,
                fill=action_row_bg,
                outline="#e2e8f0",
                width=1,
                tags=("row%d" % global_idx, "action-bg-%d" % global_idx),
            )

            if self.get_action_buttons_func:
                buttons = self.get_action_buttons_func(d)
                if isinstance(buttons, list) and buttons:
                    btn_count = len(buttons)
                    gap = 8
                    # Standardized button width
                    btn_width = 85 if btn_count > 1 else 115

                    # Available width for buttons (leave some padding)
                    available_w = w - 12
                    total_required = (btn_width * btn_count) + (gap * (btn_count - 1))

                    # Scale down btn_width if it exceeds available space
                    if total_required > available_w:
                        btn_width = (available_w - (gap * (btn_count - 1))) // btn_count
                        btn_width = max(btn_width, 35)
                        total_required = (btn_width * btn_count) + (
                            gap * (btn_count - 1)
                        )

                    # Center the button group in the column width 'w'
                    start_x = x + (w - total_required) // 2
                    # Ensure it doesn't peek into the previous column
                    start_x = max(x + 4, start_x)

                    btn_x = start_x
                    btn_y = y + 7
                    for btn_idx, (text, bg, fg_color, cb) in enumerate(buttons):
                        # Cap at column end
                        if btn_x >= x + w - 4:
                            break

                        draw_w = btn_width
                        if btn_x + draw_w > x + w - 4:
                            draw_w = (x + w - 4) - btn_x

                        if draw_w < 10:
                            break

                        hovered = (
                            global_idx == self.hover_row
                            and btn_idx == self.hover_button
                        )
                        btn_tags = (
                            "action-btn-%d-%d" % (global_idx, btn_idx),
                            "row%d" % global_idx,
                        )
                        r_tag = "btn-rect-%d-%d" % (global_idx, btn_idx)

                        # Use slightly rounded corners or just ensure sharp placement
                        self.canvas.create_rectangle(
                            btn_x,
                            btn_y,
                            btn_x + draw_w,
                            btn_y + self.row_height - 14,
                            fill=bg,
                            outline="#2563eb" if hovered else "#d1d5db",
                            width=2 if hovered else 1,
                            tags=btn_tags + (r_tag,),
                        )

                        if draw_w > 20:
                            # Truncate text for the button width
                            btn_text = self._truncate_text(text, draw_w + 12)
                            self.canvas.create_text(
                                btn_x + draw_w // 2,
                                btn_y + (self.row_height - 14) // 2,
                                text=btn_text,
                                fill=fg_color,
                                font=("Segoe UI", 8, "bold"),
                                anchor="center",
                                tags=btn_tags
                                + ("btn-text-%d-%d" % (global_idx, btn_idx),),
                            )

                        btn_x += draw_w + gap
                elif isinstance(buttons, tuple) or isinstance(buttons, str):
                    # Show as label
                    display_val = buttons
                    if isinstance(display_val, tuple):
                        val_text, fg, font, anchor = display_val
                    else:
                        val_text = display_val
                        fg = "#1f2937"
                        font = ("Segoe UI", 10)
                        anchor = "center"

                    text_x = x + w // 2 if anchor == "center" else x + 12
                    self.canvas.create_text(
                        text_x,
                        y + self.row_height // 2,
                        text=self._truncate_text(val_text, w),
                        fill=fg,
                        font=font,
                        anchor=anchor,
                        tags=("row%d" % global_idx,),
                    )

            y += self.row_height

        total_height = header_height + len(page_data) * self.row_height
        # Ensure scrollregion is at least the size of the canvas to avoid jumping
        canvas_h = self.canvas.winfo_height()
        scroll_h = max(total_height, canvas_h)
        self.canvas.config(scrollregion=(0, 0, sum(self.col_widths), scroll_h))

        total = len(self.filtered)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        curr = self.current_page + 1
        start = row_start + 1 if total > 0 else 0
        end = min(row_start + self.page_size, total)
        self.page_label.config(text="Page %d of %d" % (curr, total_pages))
        self.records_label.config(
            text="Showing %d–%d of %d records" % (start, end, total)
        )

        # Finally delete old items after drawing new ones - this is the flicker patch
        self.canvas.delete("old_content")

    def _on_canvas_motion(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        # Check if we are over a column boundary for resizing
        over_separator = False
        if cy < 38:  # Only headers
            sep_idx = self._get_column_boundary(cx)
            if sep_idx != -1:
                over_separator = True

        items = self.canvas.find_overlapping(cx - 5, cy - 5, cx + 5, cy + 5)

        new_row = -1
        new_btn = -1

        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("row") and not tag.startswith("row-bg"):
                    try:
                        new_row = int(tag[3:])
                    except:
                        pass
                if tag.startswith("action-btn-"):
                    parts = tag.split("-")
                    new_row = int(parts[2])
                    new_btn = int(parts[3])

        if new_row != self.hover_row or new_btn != self.hover_button:
            old_row = self.hover_row
            old_btn = self.hover_button

            self.hover_row = new_row
            self.hover_button = new_btn

            # Fast update: only change colors of affected tags
            if old_row != -1:
                self._update_row_highlight(old_row, False)
            if new_row != -1:
                self._update_row_highlight(new_row, True)

            if old_btn != -1:
                self._update_btn_highlight(old_row, old_btn, False)
            if new_btn != -1:
                self._update_btn_highlight(new_row, new_btn, True)

        if new_btn != -1:
            self.canvas.config(cursor="hand2")
        elif over_separator or self.dragging_col != -1:
            self.canvas.config(cursor="sb_h_double_arrow")
        else:
            self.canvas.config(cursor="")

    def _update_row_highlight(self, row_idx, is_hovered):
        # Calculate original background for normal cells
        local_idx = row_idx % self.page_size
        is_even = local_idx % 2 == 0
        bg = "#e0f2fe" if is_hovered else ("#ffffff" if is_even else "#f8fafc")
        self.canvas.itemconfigure("row-bg-%d" % row_idx, fill=bg)

        # Also highlight action column background
        action_bg = "#e0f2fe" if is_hovered else "#f9fafb"
        self.canvas.itemconfigure("action-bg-%d" % row_idx, fill=action_bg)

    def _update_btn_highlight(self, row_idx, btn_idx, is_hovered):
        # Target only the rectangle tag, not the text item
        outline = "#2563eb" if is_hovered else "#d1d5db"
        width = 2 if is_hovered else 1
        try:
            self.canvas.itemconfigure(
                "btn-rect-%d-%d" % (row_idx, btn_idx), outline=outline, width=width
            )
        except tk.TclError:
            # Fallback in case of tag mismatch during redraw
            pass

    def _get_column_boundary(self, cx):
        x = 0
        threshold = 12
        for i in range(len(self.col_widths) - 1):  # All except after the last one
            x += self.col_widths[i]
            if x - threshold <= cx <= x + threshold:
                return i
        return -1

    def _on_canvas_leave(self, event):
        if self.dragging_col == -1:
            # Targeted clear of highlights instead of full redraw
            if self.hover_row != -1:
                self._update_row_highlight(self.hover_row, False)
            if self.hover_button != -1:
                self._update_btn_highlight(self.hover_row, self.hover_button, False)
            self.hover_row = -1
            self.hover_button = -1
            self.canvas.config(cursor="")

    def _on_canvas_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        items = self.canvas.find_overlapping(cx - 10, cy - 10, cx + 10, cy + 10)
        tags = []
        for item in items:
            tags.extend(self.canvas.gettags(item))

        # Header Area Interaction
        if cy < 38:
            boundary_col = self._get_column_boundary(cx)
            if boundary_col != -1:
                self.dragging_col = boundary_col
                self.canvas.config(cursor="sb_h_double_arrow")
                return

            # Header Area Click (Sorting)
            if any(t == "header" for t in tags):
                # Calculate which column was clicked
                curr_x = 0
                for i, w in enumerate(self.col_widths):
                    if cx < curr_x + w:
                        if i < len(self.headers) - 1:  # Don't sort Action column
                            self._sort_by_column(i)
                        break
                    curr_x += w
                return

        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("action-btn-"):
                    parts = tag.split("-")
                    row_idx = int(parts[2])
                    btn_idx = int(parts[3])
                    if row_idx >= len(self.filtered):
                        return
                    record = self.filtered[row_idx]
                    buttons = self.get_action_buttons_func(record)
                    if btn_idx < len(buttons) and buttons[btn_idx][3]:
                        buttons[btn_idx][3](record)
                    return

        # Cell copy logic
        if cy >= 38:
            rel_y = cy - 38
            row_idx = int(rel_y // self.row_height) + self.current_page * self.page_size
            if row_idx >= len(self.filtered):
                return
            x_pos = 0
            col_idx = -1
            for i, w in enumerate(self.col_widths):
                if cx < x_pos + w:
                    col_idx = i
                    break
                x_pos += w

            if col_idx < len(self.headers) - 1:
                record = self.filtered[row_idx]
                key = (
                    self.data_keys[col_idx]
                    if hasattr(self, "data_keys") and col_idx < len(self.data_keys)
                    else None
                )
                if key and col_idx not in self.non_copyable_cols:
                    val = record.get(key, "")
                    # Apply formatter if exists for copying formatted value
                    if col_idx in self.cell_formatters:
                        fmt_val = self.cell_formatters[col_idx](val, record)
                        if isinstance(fmt_val, tuple):
                            val = fmt_val[0]
                        else:
                            val = fmt_val

                    if val and val != "—":
                        self.clipboard_clear()
                        self.clipboard_append(str(val))
                        self._show_copy_feedback(event.x, event.y)

                if self.on_cell_click:
                    self.on_cell_click(record, col_idx)

    def _on_resize_drag(self, event):
        if self.dragging_col == -1:
            return
        cx = self.canvas.canvasx(event.x)
        prev = sum(self.col_widths[: self.dragging_col])

        # Calculate minimum width based on header text
        header_text = self.headers[self.dragging_col]
        # Using a default font measurement as backup
        try:
            f = tkfont.Font(family="Segoe UI", size=10, weight="bold")
            text_w = f.measure(header_text)
        except:
            text_w = len(header_text) * 9

        min_w = text_w + 40  # text width + padding for separators and icons

        new_w = max(min_w, cx - prev)
        self.col_widths[self.dragging_col] = new_w
        self._redraw_table()
        self._stretch_last_column()  # Ensure last column reacts to change

    def _on_resize_release(self, event):
        self.dragging_col = -1
        self.canvas.config(cursor="")

    def _show_copy_feedback(self, sx, sy):
        if self.copy_feedback_id:
            self.canvas.after_cancel(self.copy_feedback_id)
            self.canvas.delete("copy_feedback")
        self.canvas.create_window(
            sx + 20,
            sy - 10,
            window=self.copy_feedback,
            anchor="nw",
            tags="copy_feedback",
        )
        self.copy_feedback_id = self.canvas.after(
            1500, lambda: self.canvas.delete("copy_feedback")
        )

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.canvas.yview_moveto(0)
            self._redraw_table()

    def _next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered):
            self.current_page += 1
            self.canvas.yview_moveto(0)
            self._redraw_table()

    def _sort_by_column(self, col_idx):
        if not self.data:
            return

        if col_idx == self.sort_col_index:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_col_index = col_idx
            self.sort_ascending = True

        # Determine the key to sort by
        if hasattr(self, "data_keys") and col_idx < len(self.data_keys):
            key = self.data_keys[col_idx]
        else:
            return

        def sort_key(item):
            val = item.get(key, "")
            if val is None:
                val = ""
            
            # If it's already a number, group it in category 0
            if isinstance(val, (int, float)):
                return (0, float(val))
            
            s_val = str(val).strip()
            # If it's a string that represents a number, also group in category 0
            if s_val.isdigit():
                try:
                    return (0, float(s_val))
                except:
                    pass
            
            # Otherwise, group in category 1 as a lowercase string
            return (1, s_val.lower())

        self.data.sort(key=sort_key, reverse=not self.sort_ascending)
        self._apply_search(reset_pagination=True)
