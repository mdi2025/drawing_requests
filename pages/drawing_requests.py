#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import datetime
import threading

# Assuming you have a styles module - if not, you can replace with plain values
# For compatibility we're using more basic colors where possible
try:
    import styles
except ImportError:
    class DummyStyles:
        LIGHT = "#f8fafc"
        DARK = "#1e293b"
        PRIMARY = "#3b82f6"
    styles = DummyStyles()

class DrawingRequestsPage(ttk.Frame):
    def __init__(self, parent, username="User"):
        ttk.Frame.__init__(self, parent, style="Card.TFrame", padding=25)
        self.pack(expand=True, fill="both", padx=20, pady=20)
        
        self.username = username
        self.drawings = []
        self.page_size = 10
        self.current_page = 0
        self.filtered = []
        
        # Column configuration: [Drawing ID, Revision, Status, Requested By, Action]
        self.col_widths = [150, 80, 100, 200, 120]
        self.row_widgets = []  # Cache for row widgets
        
        self._build_ui()
        
        # Start loading data after UI is built
        self.after(100, self._start_loading)

    def _start_loading(self):
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self.table_container.pack_forget() # Hide table while loading (optional, but cleaner)
        
        thread = threading.Thread(target=self._fetch_data_thread)
        thread.daemon = True
        thread.start()

    def _fetch_data_thread(self):
        data = self._generate_data()
        self.after(0, lambda: self._on_data_ready(data))

    def _on_data_ready(self, data):
        self.drawings = data
        self.filtered = list(self.drawings)
        self.current_page = 0
        
        self.loading_label.place_forget()
        self.table_container.pack(expand=True, fill="both")
        self._load_table()

    def _generate_data(self):
        try:
            import sys
            import os
            # Ensure we can import db_handler from parent
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from db_handler import db
            
            query = """
                SELECT drawing_no as no, 
                       latest_revision as rev, 
                       current_status as status 
                FROM drawings_master_bal 
                WHERE current_status = 'Approved' 
                LIMIT 11
            """
            data = db.fetch_all(query)
            
            if not data:
                print("No data found or connection failed.")
                return []
            
            for item in data:
                item['requested_by'] = ""
                
            return data
        except Exception as e:
            print("Error fetching data: {}".format(e))
            return []

    def _build_ui(self):
        # ── Header ───────────────────────────────────────────────
        header = tk.Frame(self, bg=styles.LIGHT)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(header, text="Drawing Requisitions", style="Title.TLabel").pack(side="left")

        ttk.Button(header, text="Refresh", style="Flat.TButton", 
                   command=self.refresh).pack(side="left", padx=20)

        # Search (right aligned)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(header, textvariable=self.search_var,
                                     font=("Segoe UI", 10), bd=0, relief="flat",
                                     width=25,
                                     highlightthickness=1, highlightbackground="#cbd5e1",
                                     highlightcolor=styles.PRIMARY,
                                     fg="#94a3b8")
        self.search_entry.pack(side="right", ipady=8)
        self.search_entry.insert(0, "Search drawings...")
        
        self.search_entry.bind("<FocusIn>", self._clear_placeholder)
        self.search_entry.bind("<FocusOut>", self._restore_placeholder)
        self.search_var.trace("w", self._search_data)

        # ── Loading Indicator ───────────────────────────────────
        self.loading_label = ttk.Label(self, text="Loading data...", 
                                      font=("Segoe UI", 12), foreground="#64748b")

        # ── Table Area ───────────────────────────────────────────
        self.table_container = tk.Frame(self, bg="white", 
                                       highlightthickness=1, highlightbackground="#cbd5e1")
        self.table_container.pack(expand=True, fill="both")

        # Header (resizable columns)
        self.header_paned = tk.PanedWindow(self.table_container, orient="horizontal",
                                          bg="#e2e8f0", bd=0, sashwidth=2, sashpad=0)
        self.header_paned.pack(fill="x")
        
        headers = ["Drawing ID", "Revision", "Status", "Requested By", "Action"]
        min_widths = [110, 70, 80, 150, 80]
        self.header_frames = []
        
        for i, h in enumerate(headers):
            f = tk.Frame(self.header_paned, bg="#f1f5f9", width=self.col_widths[i], height=40)
            f.pack_propagate(False)
            lbl = tk.Label(f, text=h, font=("Segoe UI", 10, "bold"),
                           bg="#f1f5f9", fg=styles.DARK)
            lbl.pack(expand=True, fill="both")
            self.header_paned.add(f, minsize=min_widths[i])
            self.header_frames.append(f)
            f.bind("<Configure>", lambda e: self._sync_columns())

        # Body
        self.body_frame = tk.Frame(self.table_container, bg="white")
        self.body_frame.pack(expand=True, fill="both")

        # ── FIXED Pagination (always at bottom) ──────────────────
        pager = tk.Frame(self, bg=styles.LIGHT, height=50)
        pager.pack(side="bottom", fill="x", pady=10, padx=10)
        pager.pack_propagate(False)   # ← important: prevents height collapse

        # Navigation buttons + labels centered
        nav_frame = tk.Frame(pager, bg=styles.LIGHT)
        nav_frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Button(nav_frame, text="◀ Previous", style="Flat.TButton",
                   command=self._prev_page).pack(side="left", padx=8)

        self.page_label = ttk.Label(nav_frame, text="Page 1 of 1", 
                                   font=("Segoe UI", 10, "bold"))
        self.page_label.pack(side="left", padx=20)

        ttk.Button(nav_frame, text="Next ▶", style="Flat.TButton",
                   command=self._next_page).pack(side="left", padx=8)

        self.records_label = tk.Label(pager, text="", 
                                     font=("Segoe UI", 9), fg="#64748b", bg=styles.LIGHT)
        self.records_label.place(relx=1.0, rely=0.5, anchor="e", x=-10)

        # Load initial data
        # self._load_table() # Called after data loads now

    def _sync_columns(self):
        for i, f in enumerate(self.header_frames):
            try:
                self.col_widths[i] = f.winfo_width()
            except:
                pass
        
        for row_dict in self.row_widgets:
            for i, cell in enumerate(row_dict['cells']):
                try:
                    cell.config(width=self.col_widths[i])
                except:
                    pass

    def _clear_placeholder(self, e):
        if self.search_entry.get() == "Search drawings...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg="#334155")

    def _restore_placeholder(self, e):
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search drawings...")
            self.search_entry.config(fg="#94a3b8")

    def _load_table(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_data = self.filtered[start:end]
        
        for i in range(self.page_size):
            if i < len(page_data):
                d = page_data[i]
                bg = "white" if i % 2 == 0 else "#fbfcfd"
                
                if i >= len(self.row_widgets):
                    row_frame = tk.Frame(self.body_frame, bg="white")
                    row_frame.pack(fill="x")
                    
                    cells = []
                    labels = []
                    
                    for j in range(4):
                        cell = tk.Frame(row_frame, bg="white", width=self.col_widths[j], height=45)
                        cell.pack_propagate(False)
                        cell.pack(side="left")
                        
                        lbl = tk.Label(cell, font=("Segoe UI", 10), fg="#334155", bg="white")
                        lbl.pack(expand=True, fill="both", padx=5)
                        
                        cells.append(cell)
                        labels.append(lbl)
                    
                    action_cell = tk.Frame(row_frame, bg="white", width=self.col_widths[4], height=45)
                    action_cell.pack_propagate(False)
                    action_cell.pack(side="left")
                    
                    btn = ttk.Button(action_cell, text="Request", style="Action.TButton")
                    btn.pack(expand=True)
                    
                    cells.append(action_cell)
                    
                    row_dict = {
                        'frame': row_frame,
                        'cells': cells,
                        'labels': labels,
                        'action_cell': action_cell,
                        'button': btn
                    }
                    self.row_widgets.append(row_dict)
                    
                    row_frame.bind("<Enter>", lambda e, r=row_frame: self._on_row_enter(r))

                else:
                    row_dict = self.row_widgets[i]
                    if not row_dict['frame'].winfo_viewable():
                        row_dict['frame'].pack(fill="x")
                
                row_dict['frame'].configure(bg=bg)
                row_dict['frame'].bind("<Leave>", lambda e, r=row_dict['frame'], b=bg: self._on_row_leave(r, b))
                
                status_val = str(d.get("status") or "N/A").upper()
                vals = [d.get("no", "N/A"), d.get("rev", "N/A"), status_val, d.get("requested_by", "")]
                
                for j, (lbl, cell, val) in enumerate(zip(row_dict['labels'], row_dict['cells'][:4], vals)):
                    lbl.configure(text=val, bg=bg)
                    cell.configure(bg=bg)
                    if j == 3:
                        lbl.configure(fg="#4f46e5", font=("Segoe UI", 9, "italic"))
                
                row_dict['action_cell'].configure(width=self.col_widths[4], bg=bg)
                row_dict['button'].configure(command=lambda dn=d.get("no"), idx=i: self._handle_request(dn, idx))
            
            elif i < len(self.row_widgets):
                self.row_widgets[i]['frame'].pack_forget()

        # Update pagination info
        total_records = len(self.filtered)
        total_pages = max(1, (total_records + self.page_size - 1) // self.page_size)
        current = self.current_page + 1
        
        start_record = start + 1 if total_records > 0 else 0
        end_record = min(end, total_records)
        
        self.page_label.config(text="Page {} of {}".format(current, total_pages))
        self.records_label.config(text="Showing {}–{} of {} records".format(
            start_record, end_record, total_records))

    def _handle_request(self, drawing_no, row_idx=None):
        confirm = messagebox.askyesno("Confirm Request", 
                                     "Request drawing no {}?".format(drawing_no))
        if not confirm:
            return

        now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        status_text = "{} at {}".format(self.username, now)
        
        for d in self.drawings:
            if d.get("no") == drawing_no:
                d['requested_by'] = status_text
                break
        
        if row_idx is not None and row_idx < len(self.row_widgets):
            self.row_widgets[row_idx]['labels'][3].configure(text=status_text)
            
        messagebox.showinfo("Request", "Request submitted for {}".format(drawing_no))

    def refresh(self):
        self._start_loading()

    def _on_row_enter(self, row):
        highlight_bg = "#f1f5f9"
        row.configure(bg=highlight_bg)
        for child in row.winfo_children():
            child.configure(bg=highlight_bg)
            if isinstance(child, tk.Frame):
                for gc in child.winfo_children():
                    try:
                        gc.configure(bg=highlight_bg)
                    except:
                        pass

    def _on_row_leave(self, row, original_bg):
        row.configure(bg=original_bg)
        for child in row.winfo_children():
            child.configure(bg=original_bg)
            if isinstance(child, tk.Frame):
                for gc in child.winfo_children():
                    try:
                        gc.configure(bg=original_bg)
                    except:
                        pass

    def _search_data(self, *args):
        q = self.search_var.get().lower().strip()
        if q in ("", "search drawings..."):
            self.filtered = list(self.drawings)
        else:
            self.filtered = [
                d for d in self.drawings
                if q in str(d.get("no", "")).lower()
                or q in str(d.get("rev", "")).lower()
                or q in str(d.get("status", "")).lower()
                or q in str(d.get("requested_by", "")).lower()
            ]
        self.current_page = 0
        self._load_table()

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._load_table()

    def _next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered):
            self.current_page += 1
            self._load_table()
