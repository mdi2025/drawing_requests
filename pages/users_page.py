#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import hashlib
import json
import threading
import datetime

try:
    import styles
except ImportError:
    # Fallback styles
    class DummyStyles:
        LIGHT = "#f8fafc"
        DARK = "#1e293b"
        PRIMARY = "#3b82f6"
        SECONDARY = "#64748b"
        DANGER = "#ef4444"
        SUCCESS = "#22c55e"
    styles = DummyStyles()

class UsersPage(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent, style="Card.TFrame", padding=25)
        
        self.users = []
        self.filtered = []
        self.page_size = 12
        self.current_page = 0
        self.is_loading = False
        self.row_height = 42
        
        # [ID, Username, Department, Permissions, Actions]
        self.col_widths = [60, 180, 180, 280, 180]  # last one will stretch
        self.headers = ["ID", "Username", "Department", "Permissions", "Actions"]
        self.hover_row = -1
        self.hover_button = -1
        self.dragging_col = -1
        
        self._build_ui()
        self.update_idletasks()
        self._stretch_last_column()
        self.after(100, self.refresh)

    def _stretch_last_column(self):
        fixed = sum(self.col_widths[:-1])
        canvas_w = self.canvas.winfo_width()
        if canvas_w > fixed + 40:
            self.col_widths[-1] = max(180, canvas_w - fixed)
        else:
            self.col_widths[-1] = 180  # minimum

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=styles.LIGHT)
        header.pack(fill="x", pady=(0, 16))
        
        ttk.Label(header, text="User Management", style="Title.TLabel").pack(side="left")
        
        ttk.Button(header, text="+ Add User", style="Primary.TButton", 
                   command=self._show_add_user_dialog).pack(side="left", padx=20)
        
        ttk.Button(header, text="Refresh", style="Flat.TButton",
                   command=self.refresh).pack(side="left", padx=10)
        
        # Search
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(header, textvariable=self.search_var,
                                     font=("Segoe UI", 10), width=28,
                                     relief="solid", bd=1,
                                     highlightthickness=1, highlightbackground="#cbd5e1",
                                     highlightcolor=styles.PRIMARY,
                                     fg=styles.SECONDARY)
        self.search_entry.pack(side="right", ipady=6)
        self.search_entry.insert(0, "Search users...")
        self.search_entry.bind("<FocusIn>", self._clear_placeholder)
        self.search_entry.bind("<FocusOut>", self._restore_placeholder)
        self.search_var.trace("w", self._search_data)

        self.loading_label = ttk.Label(self, text="Loading data...",
                                       font=("Segoe UI", 12), foreground=styles.SECONDARY)

        # Table Area
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

        # Pager
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
        if self.search_entry.get() == "Search users...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg="#0f172a")

    def _restore_placeholder(self, event):
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search users...")
            self.search_entry.config(fg=styles.SECONDARY)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh(self):
        if self.is_loading: return
        self.is_loading = True
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        thread = threading.Thread(target=self._fetch_data_thread, daemon=True)
        thread.start()

    def _fetch_data_thread(self):
        try:
            import sys
            import os
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from db_handler import db
            
            query = "SELECT id, admin_name, department, access_tokens FROM drawing_users ORDER BY id"
            data = db.fetch_all(query) or []
            
            for user in data:
                tokens = user.get('access_tokens', [])
                if isinstance(tokens, (str, bytes)):
                    try:
                        tokens = json.loads(tokens)
                    except:
                        tokens = []
                user['access_tokens'] = tokens
                
            self.after(0, lambda: self._on_data_ready(data))
        except Exception as e:
            print("Error fetching users: {}".format(e))
            self.after(0, lambda: self._on_data_ready([]))

    def _on_data_ready(self, data):
        self.users = data
        self.is_loading = False
        self.loading_label.place_forget()
        self._apply_search()

    def _apply_search(self):
        q = self.search_var.get().lower().strip()
        if q in ("", "search users..."):
            self.filtered = list(self.users)
        else:
            self.filtered = [
                u for u in self.users
                if q in str(u.get("id", "")).lower() or \
                   q in str(u.get("admin_name", "")).lower() or \
                   q in str(u.get("department", "")).lower()
            ]
        self.current_page = 0
        self._redraw_table()

    def _search_data(self, *args):
        self._apply_search()

    def _truncate_text(self, text, max_width):
        if not text: return ""
        est = len(text) * 7.5
        if est <= max_width - 30: return text
        max_chars = int((max_width - 30) / 7.5)
        if len(text) > max_chars:
            return text[:max_chars-3] + "..."
        return text

    def _format_permissions(self, tokens):
        perm_map = {1: "Req", 2: "Issue", 3: "Ret", 4: "Rpt", 5: "Users"}
        names = []
        if not isinstance(tokens, list): return ""
        for t in sorted(tokens):
            if t in perm_map:
                names.append(perm_map[t])
        return ", ".join(names)

    def _get_action_buttons(self, user):
        buttons = []
        buttons.append(("Edit", styles.PRIMARY, "white", lambda u=user: self._show_edit_user_dialog(u)))
        buttons.append(("Delete", "#ef4444", "white", lambda u=user: self._delete_user(u)))
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
                self.canvas.create_line(sep_x, 4, sep_x, header_height-4,
                                       fill="#9ca3af", width=4,
                                       tags=("separator", "sep%d" % i))
                self.canvas.create_rectangle(sep_x - 18, 0, sep_x + 18, header_height,
                                            fill="", outline="",
                                            tags=("separator", "sep%d" % i, "sep_hit"))
            x += w

        # Rows
        y = header_height
        for local_idx, u in enumerate(page_data):
            global_idx = row_start + local_idx
            is_even = local_idx % 2 == 0
            row_bg = "#ffffff" if is_even else "#f8fafc"
            if global_idx == self.hover_row:
                row_bg = "#e0f2fe"

            x = 0
            perms_text = self._format_permissions(u.get("access_tokens", []))
            values = [
                str(u.get("id", "")),
                u.get("admin_name", ""),
                u.get("department", "") or "",
                perms_text,
            ]

            for col_idx, val in enumerate(values):
                w = self.col_widths[col_idx]
                self.canvas.create_rectangle(x, y, x + w, y + self.row_height,
                                            fill=row_bg, outline="#e2e8f0", width=1,
                                            tags=("row%d" % global_idx, "cell"))
                padx = 12
                # Left align for most, ID is centered
                anchor = "center" if col_idx == 0 else "w"
                text_x = x + w//2 if col_idx == 0 else x + padx
                
                fg = "#1f2937"
                font = ("Segoe UI", 10)
                if col_idx == 3: # Permissions column
                    fg = styles.PRIMARY
                    font = ("Segoe UI", 9, "italic")
                
                self.canvas.create_text(text_x, y + self.row_height//2,
                                       text=self._truncate_text(val, w), fill=fg, font=font,
                                       anchor=anchor, tags=("row%d" % global_idx,))
                x += w

            # Action column
            w = self.col_widths[-1]
            self.canvas.create_rectangle(x, y, x + w, y + self.row_height,
                                        fill="#f9fafb", outline="#e2e8f0", width=1,
                                        tags=("row%d" % global_idx,))
            buttons = self._get_action_buttons(u)
            btn_count = len(buttons)
            btn_width = 75
            total_btn_width = (btn_width * btn_count) + (10 * (btn_count - 1))
            start_x = x + (w - total_btn_width) // 2
            
            btn_x = start_x
            btn_y = y + 8
            for btn_idx, (text, bg, fg_color, cb) in enumerate(buttons):
                hovered = (global_idx == self.hover_row and btn_idx == self.hover_button)
                tags = ("action-btn-%d-%d" % (global_idx, btn_idx), "row%d" % global_idx)
                self.canvas.create_rectangle(btn_x, btn_y, btn_x + btn_width, btn_y + self.row_height - 16,
                                            fill=bg, outline="#1d4ed8" if hovered else "#d1d5db",
                                            width=2 if hovered else 1, tags=tags)
                self.canvas.create_text(btn_x + btn_width//2, btn_y + (self.row_height-16)//2,
                                       text=text, fill=fg_color,
                                       font=("Segoe UI", 9, "bold"), anchor="center", tags=tags)
                btn_x += btn_width + 10
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
        items = self.canvas.find_overlapping(cx-10, cy-10, cx+10, cy+10)

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
        items = self.canvas.find_overlapping(cx-10, cy-10, cx+10, cy+10)

        for item in items:
            tags = self.canvas.gettags(item)
            if any(t.startswith("sep") for t in tags):
                for tag in tags:
                    if tag.startswith("sep") and tag[3:].isdigit():
                        self.dragging_col = int(tag[3:])
                        self.canvas.config(cursor="sb_h_double_arrow")
                        return

        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("action-btn-"):
                    parts = tag.split("-")
                    row_idx = int(parts[2])
                    btn_idx = int(parts[3])
                    if row_idx >= len(self.filtered): return
                    user = self.filtered[row_idx]
                    buttons = self._get_action_buttons(user)
                    if btn_idx < len(buttons):
                        buttons[btn_idx][3]()
                    return

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
            keys = ["id", "admin_name", "department", "access_tokens", None]
            key = keys[col_idx] if 0 <= col_idx < len(keys) else None
            if key:
                val = self.filtered[row_idx].get(key, "")
                if key == "access_tokens": val = self._format_permissions(val)
                if val:
                    self.clipboard_clear()
                    self.clipboard_append(str(val))
                    self._show_copy_feedback(event.x, event.y)

    def _on_resize_drag(self, event):
        if self.dragging_col == -1: return
        cx = self.canvas.canvasx(event.x)
        prev = sum(self.col_widths[:self.dragging_col])
        new_w = max(40, cx - prev)
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

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._redraw_table()

    def _next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered):
            self.current_page += 1
            self._redraw_table()

    # Dialogs - Keeping original logic
    def _show_add_user_dialog(self): self._user_dialog("Add New User")
    def _show_edit_user_dialog(self, user): self._user_dialog("Edit User", user)

    def _user_dialog(self, title, user=None):
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry("500x550")
        dlg.resizable(False, False)
        dlg.configure(bg="white")
        dlg.transient(self)
        
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 250
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 275
        dlg.geometry("+{}+{}".format(x, y))

        ttk.Label(dlg, text=title, font=("Segoe UI", 14, "bold"), background="white").pack(pady=20)
        frm = tk.Frame(dlg, bg="white", padx=40)
        frm.pack(fill="both", expand=True)
        
        ttk.Label(frm, text="Username", background="white").pack(anchor="w")
        username_var = tk.StringVar(value=user['admin_name'] if user else "")
        tk.Entry(frm, textvariable=username_var, font=("Segoe UI", 10)).pack(fill="x", pady=(0, 15))
        
        ttk.Label(frm, text="Password " + ("(Leave blank to keep current)" if user else ""), background="white").pack(anchor="w")
        password_var = tk.StringVar()
        tk.Entry(frm, textvariable=password_var, show="*", font=("Segoe UI", 10)).pack(fill="x", pady=(0, 15))

        ttk.Label(frm, text="Department", background="white").pack(anchor="w")
        dept_var = tk.StringVar(value=user.get('department', '') if user else "")
        tk.Entry(frm, textvariable=dept_var, font=("Segoe UI", 10)).pack(fill="x", pady=(0, 15))
        
        ttk.Label(frm, text="Permissions", background="white", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(5,5))
        
        perm_container = tk.Frame(frm, bg="white", highlightthickness=1, highlightbackground="#e2e8f0")
        perm_container.pack(fill="x", pady=(0, 15), ipady=5)
        
        p_canvas = tk.Canvas(perm_container, bg="white", height=150, highlightthickness=0)
        p_scrollbar = ttk.Scrollbar(perm_container, orient="vertical", command=p_canvas.yview)
        p_frame = tk.Frame(p_canvas, bg="white")
        p_frame.bind("<Configure>", lambda e: p_canvas.configure(scrollregion=p_canvas.bbox("all")))
        p_canvas.create_window((0, 0), window=p_frame, anchor="nw")
        p_canvas.configure(yscrollcommand=p_scrollbar.set)
        p_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        p_scrollbar.pack(side="right", fill="y")
        
        def _on_p_mw(event):
            if event.num == 4: p_canvas.yview_scroll(-1, "units")
            elif event.num == 5: p_canvas.yview_scroll(1, "units")
        p_canvas.bind("<Button-4>", _on_p_mw); p_canvas.bind("<Button-5>", _on_p_mw)
        
        perms_map = {1: "Drawing Requests", 2: "Drawing Issuance", 3: "Return", 4: "Reports", 5: "User Management"}
        perm_vars = {}
        current_perms = user['access_tokens'] if user else []
        for i, (pid, pname) in enumerate(sorted(perms_map.items())):
            var = tk.BooleanVar(value=pid in current_perms)
            perm_vars[pid] = var
            row, col = i // 2, i % 2
            tk.Checkbutton(p_frame, text=pname, variable=var, bg="white", activebackground="white").grid(row=row, column=col, sticky="w", padx=10, pady=2)
        
        def save():
            uname, pwd, dept = username_var.get().strip(), password_var.get().strip(), dept_var.get().strip()
            sel_perms = [pid for pid, var in perm_vars.items() if var.get()]
            if not uname: messagebox.showerror("Error", "Username is required", parent=dlg); return
            if not user and not pwd: messagebox.showerror("Error", "Password is required", parent=dlg); return
            if user: self._update_user_db(user['id'], uname, pwd, dept, sel_perms, dlg)
            else: self._create_user_db(uname, pwd, dept, sel_perms, dlg)
        ttk.Button(dlg, text="Save User", style="Primary.TButton", command=save).pack(pady=20)
        
        dlg.update_idletasks()
        try:
            dlg.grab_set()
        except:
            pass # Fallback if still not viewable locally

    def _create_user_db(self, username, password, department, perms, dlg):
        try:
            from db_handler import db
            if db.fetch_all("SELECT id FROM drawing_users WHERE admin_name=%s", (username,)):
                messagebox.showerror("Error", "Username exists", parent=dlg); return
            pwd_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
            if db.execute_query("INSERT INTO drawing_users (admin_name, admin_pass, department, access_tokens) VALUES (%s, %s, %s, %s)",
                               (username, pwd_hash, department, json.dumps(perms))):
                messagebox.showinfo("Success", "User created", parent=dlg); dlg.destroy(); self.refresh()
            else: messagebox.showerror("Error", "Failed", parent=dlg)
        except Exception as e: messagebox.showerror("Error", str(e), parent=dlg)

    def _update_user_db(self, uid, username, password, department, perms, dlg):
        try:
            from db_handler import db
            if password:
                pwd_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
                q = "UPDATE drawing_users SET admin_name=%s, admin_pass=%s, department=%s, access_tokens=%s WHERE id=%s"
                p = (username, pwd_hash, department, json.dumps(perms), uid)
            else:
                q = "UPDATE drawing_users SET admin_name=%s, department=%s, access_tokens=%s WHERE id=%s"
                p = (username, department, json.dumps(perms), uid)
            if db.execute_query(q, p):
                messagebox.showinfo("Success", "User updated", parent=dlg); dlg.destroy(); self.refresh()
            else: messagebox.showerror("Error", "Failed", parent=dlg)
        except Exception as e: messagebox.showerror("Error", str(e), parent=dlg)

    def _delete_user(self, user):
        if not messagebox.askyesno("Confirm", "Delete user '%s'?" % user['admin_name']): return
        try:
            from db_handler import db
            if db.execute_query("DELETE FROM drawing_users WHERE id=%s", (user['id'],)):
                messagebox.showinfo("Success", "Deleted"); self.refresh()
            else: messagebox.showerror("Error", "Failed")
        except Exception as e: messagebox.showerror("Error", str(e))
