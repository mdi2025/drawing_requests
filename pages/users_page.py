#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import hashlib
import json
import threading
import styles
from pages.table_component import CanvasDataTable

class UsersPage(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        
        self.table = CanvasDataTable(
            self,
            title="User Management",
            headers=["ID", "Username", "Department", "Permissions", "Actions"],
            initial_widths=[60, 180, 180, 280, 180],
            fetch_data_func=self._fetch_users,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search users...",
            search_keys=["id", "admin_name", "department"],
            cell_formatters={
                0: lambda v, r: (str(v), "#1f2937", ("Segoe UI", 10), "center"),
                3: self._format_permissions
            }
        )
        self.table.data_keys = ["id", "admin_name", "department", "access_tokens"]
        
        # Add the 'Add User' button to the header
        header_frame = self.table.winfo_children()[0] # Header frame is first child
        ttk.Button(header_frame, text="+ Add User", style="Primary.TButton", 
                   command=self._show_add_user_dialog).pack(side="left", padx=20)
        
        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    def _format_permissions(self, tokens, record):
        perm_map = {1: "Req", 2: "Issue", 3: "Ret", 4: "Rpt", 5: "Users"}
        names = []
        if not isinstance(tokens, list): return ""
        for t in sorted(tokens):
            if t in perm_map:
                names.append(perm_map[t])
        return ", ".join(names), styles.PRIMARY, ("Segoe UI", 9, "italic"), "w"

    def _fetch_users(self):
        try:
            import sys, os
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from db_handler import db
            
            query = "SELECT id, admin_name, department, access_tokens FROM drawing_users ORDER BY id"
            data = db.fetch_all(query) or []
            
            for user in data:
                tokens = user.get('access_tokens', [])
                if isinstance(tokens, (str, bytes)):
                    try: tokens = json.loads(tokens)
                    except: tokens = []
                user['access_tokens'] = tokens
            return data
        except Exception as e:
            print("Error fetching users: {}".format(e))
            return []

    def _get_actions(self, user):
        buttons = []
        buttons.append(("Edit", styles.PRIMARY, "white", self._show_edit_user_dialog))
        buttons.append(("Delete", "#ef4444", "white", self._delete_user))
        return buttons

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
        try: dlg.grab_set()
        except: pass

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

    def refresh(self):
        self.table.refresh()
