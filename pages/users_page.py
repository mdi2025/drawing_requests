#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import hashlib
import json
import threading
import styles
import urllib.request
import urllib.parse
from pages.table_component import CanvasDataTable
from config import app_url as API_BASE_URL, api_timeout as API_TIMEOUT


class UsersPage(ttk.Frame):
    # API Configuration
    def __init__(self, parent, on_data_ready=None):
        ttk.Frame.__init__(self, parent)

        self.API_BASE_URL = API_BASE_URL
        self.API_TIMEOUT = API_TIMEOUT

        self.table = CanvasDataTable(
            self,
            title="User Management",
            headers=["ID", "Username", "Department", "Permissions", "Role", "Actions"],
            initial_widths=[60, 180, 180, 280, 120, 220],
            fetch_data_func=self._fetch_users,
            get_action_buttons_func=self._get_actions,
            search_placeholder="Search users...",
            search_keys=["id", "admin_name", "department"],
            cell_formatters={
                0: lambda v, r: (str(v), "#1f2937", ("Segoe UI", 10), "center"),
                3: self._format_permissions,
                4: self._format_roles,
            },
            on_data_ready_callback=on_data_ready,
        )
        # Include user_role in the data keys fetched per row
        self.table.data_keys = [
            "id",
            "admin_name",
            "department",
            "access_tokens",
            "user_role",
        ]

        # Add the 'Add User' button to the header
        header_frame = self.table.winfo_children()[0]
        ttk.Button(
            header_frame,
            text="+ Add User",
            style="Primary.TButton",
            command=self._show_add_user_dialog,
        ).pack(side="left", padx=20)

        self.table.pack(expand=True, fill="both")
        self.pack_propagate(False)

    # ── Role display helpers ──────────────────────────────────────────────────

    ROLE_COLORS = {
        "ADMIN": ("#7c3aed", "#ede9fe"),  # purple text, lavender bg
        "ISSUER": ("#0369a1", "#e0f2fe"),  # blue text, sky bg
        "REQUESTER": ("#065f46", "#d1fae5"),  # green text, mint bg
    }

    def _format_roles(self, roles_raw, record):
        """Format user_role JSON list as comma-separated colored badges (text only)."""
        if not roles_raw:
            return ("—", "#9ca3af", ("Segoe UI", 9, "italic"), "center")

        if isinstance(roles_raw, (str, bytes)):
            try:
                roles = json.loads(roles_raw)
            except Exception:
                roles = []
        else:
            roles = roles_raw if isinstance(roles_raw, list) else []

        if not roles:
            return ("—", "#9ca3af", ("Segoe UI", 9, "italic"), "center")

        label = ", ".join(r.capitalize() for r in roles)
        # Pick color of the first (or most privileged) role
        first = roles[0].upper() if roles else ""
        color, _ = self.ROLE_COLORS.get(first, ("#374151", "#f3f4f6"))
        return (label, color, ("Segoe UI", 9, "bold"), "center")

    # ── Permissions display ───────────────────────────────────────────────────

    def _format_permissions(self, tokens, record):
        perm_map = {1: "Req", 2: "Issue", 3: "Ret", 4: "Rec", 5: "Rpt", 6: "Users"}
        names = []
        if not isinstance(tokens, list):
            return ""
        for t in sorted(tokens):
            if t in perm_map:
                names.append(perm_map[t])
        return ", ".join(names), styles.PRIMARY, ("Segoe UI", 9, "italic"), "w"

    # ── Data fetching ─────────────────────────────────────────────────────────

    def _fetch_users(self):
        try:
            # Make API call to get users
            url = "{}?action=get_users".format(self.API_BASE_URL)
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode("utf-8"))

            if data.get("response") == "true":
                return data.get("data", [])
            else:
                print("API Error: {}".format(data.get("message", "Unknown error")))
                return []
        except Exception as e:
            print("Error fetching users: {}".format(e))
            return []

    # ── Action buttons ────────────────────────────────────────────────────────

    def _get_actions(self, user):
        buttons = []
        buttons.append(("Edit", styles.PRIMARY, "white", self._show_edit_user_dialog))
        buttons.append(
            ("Assign Role", "#7c3aed", "white", self._show_assign_role_dialog)
        )
        buttons.append(("Delete", "#ef4444", "white", self._delete_user))
        return buttons

    # ── Add / Edit user dialog ────────────────────────────────────────────────

    def _show_add_user_dialog(self):
        self._user_dialog("Add New User")

    def _show_edit_user_dialog(self, user):
        self._user_dialog("Edit User", user)

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

        ttk.Label(
            dlg, text=title, font=("Segoe UI", 14, "bold"), background="white"
        ).pack(pady=20)
        frm = tk.Frame(dlg, bg="white", padx=40)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Username", background="white").pack(anchor="w")
        username_var = tk.StringVar(value=user["admin_name"] if user else "")
        tk.Entry(frm, textvariable=username_var, font=("Segoe UI", 10)).pack(
            fill="x", pady=(0, 15)
        )

        ttk.Label(
            frm,
            text="Password " + ("(Leave blank to keep current)" if user else ""),
            background="white",
        ).pack(anchor="w")
        password_var = tk.StringVar()
        tk.Entry(frm, textvariable=password_var, show="*", font=("Segoe UI", 10)).pack(
            fill="x", pady=(0, 15)
        )

        ttk.Label(frm, text="Department", background="white").pack(anchor="w")
        dept_var = tk.StringVar(value=user.get("department", "") if user else "")

        try:
            # Fetch departments from API
            dept_url = "{}?action=get_departments".format(self.API_BASE_URL)
            with urllib.request.urlopen(dept_url) as response:
                dept_data = json.loads(response.read().decode("utf-8"))

            if dept_data.get("response") == "true":
                dept_list = dept_data.get("data", [])
            else:
                dept_list = []
        except Exception:
            dept_list = []

        all_depts = ["-- Select Department --"] + dept_list
        dept_combo = ttk.Combobox(
            frm, textvariable=dept_var, values=all_depts, font=("Segoe UI", 10)
        )
        dept_combo.pack(fill="x", pady=(0, 15))

        if user and user.get("department") in dept_list:
            dept_combo.set(user.get("department"))
        else:
            dept_combo.set("-- Select Department --")

        def _filter_depts(event=None):
            if event and event.keysym in ("Down", "Up", "Return", "Escape", "Tab"):
                return
            typed = dept_var.get().strip().lower()
            if typed == "" or typed == "-- select department --":
                dept_combo["values"] = all_depts
            else:
                filtered = [d for d in dept_list if typed in d.lower()]
                dept_combo["values"] = filtered if filtered else ["No match found"]
            dept_combo.after(10, lambda: dept_combo.event_generate("<Down>"))

        dept_combo.bind("<KeyRelease>", _filter_depts)

        ttk.Label(
            frm, text="Permissions", background="white", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(5, 5))

        perm_container = tk.Frame(
            frm, bg="white", highlightthickness=1, highlightbackground="#e2e8f0"
        )
        perm_container.pack(fill="x", pady=(0, 15), ipady=5)

        p_canvas = tk.Canvas(
            perm_container, bg="white", height=150, highlightthickness=0
        )
        p_scrollbar = ttk.Scrollbar(
            perm_container, orient="vertical", command=p_canvas.yview
        )
        p_frame = tk.Frame(p_canvas, bg="white")
        p_frame.bind(
            "<Configure>",
            lambda e: p_canvas.configure(scrollregion=p_canvas.bbox("all")),
        )
        p_canvas.create_window((0, 0), window=p_frame, anchor="nw")
        p_canvas.configure(yscrollcommand=p_scrollbar.set)
        p_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        p_scrollbar.pack(side="right", fill="y")

        perms_map = {
            1: "Drawing Requests",
            2: "Drawing Issuance",
            3: "Drawing Return",
            4: "Drawing Receive",
            5: "Reports",
            6: "User Management",
        }
        perm_vars = {}
        current_perms = user["access_tokens"] if user else []
        for i, (pid, pname) in enumerate(sorted(perms_map.items())):
            var = tk.BooleanVar(value=pid in current_perms)
            perm_vars[pid] = var
            row, col = i // 2, i % 2
            tk.Checkbutton(
                p_frame, text=pname, variable=var, bg="white", activebackground="white"
            ).grid(row=row, column=col, sticky="w", padx=10, pady=2)

        def save():
            uname = username_var.get().strip()
            pwd = password_var.get().strip()
            dept = dept_var.get().strip()

            if not uname:
                messagebox.showerror("Error", "Username is required", parent=dlg)
                return
            if not user and not pwd:
                messagebox.showerror("Error", "Password is required", parent=dlg)
                return
            if dept in ("-- Select Department --", "", "No match found"):
                messagebox.showerror("Error", "Please select a department", parent=dlg)
                return

            sel_perms = [pid for pid, var in perm_vars.items() if var.get()]
            if not sel_perms:
                messagebox.showerror(
                    "Error",
                    "Please select at least one permission.\n\n"
                    "Without permissions the user will not be able to log in.",
                    parent=dlg,
                )
                return
            if user:
                self._update_user_db(user["id"], uname, pwd, dept, sel_perms, dlg)
            else:
                self._create_user_db(uname, pwd, dept, sel_perms, dlg)

        ttk.Button(dlg, text="Save User", style="Primary.TButton", command=save).pack(
            pady=20
        )
        dlg.update_idletasks()
        try:
            dlg.grab_set()
        except Exception:
            pass

    # ── Assign Role dialog ────────────────────────────────────────────────────

    def _show_assign_role_dialog(self, user):
        """Show a dialog to manually assign one or more roles to a user."""
        dlg = tk.Toplevel(self)
        dlg.title("Assign Role — {}".format(user["admin_name"]))
        dlg.geometry("380x320")
        dlg.resizable(False, False)
        dlg.configure(bg="white")
        dlg.transient(self)

        x = self.winfo_rootx() + (self.winfo_width() // 2) - 190
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 160
        dlg.geometry("+{}+{}".format(x, y))

        # ── Title ──
        ttk.Label(
            dlg,
            text="Assign Role",
            font=("Segoe UI", 13, "bold"),
            background="white",
        ).pack(pady=(20, 4))
        ttk.Label(
            dlg,
            text="User: {}".format(user["admin_name"]),
            font=("Segoe UI", 10),
            foreground="#6b7280",
            background="white",
        ).pack(pady=(0, 16))

        frm = tk.Frame(dlg, bg="white", padx=40)
        frm.pack(fill="both", expand=True)

        # ── Roles available ──
        ALL_ROLES = ["ADMIN", "ISSUER", "REQUESTER"]

        current_roles = user.get("user_role", [])
        if isinstance(current_roles, (str, bytes)):
            try:
                current_roles = json.loads(current_roles)
            except Exception:
                current_roles = []

        role_vars = {}
        for role in ALL_ROLES:
            var = tk.BooleanVar(value=role in current_roles)
            role_vars[role] = var

            # Colored row container
            color_text, color_bg = self.ROLE_COLORS.get(role, ("#374151", "#f9fafb"))
            row_frame = tk.Frame(frm, bg=color_bg, pady=4, padx=10)
            row_frame.pack(fill="x", pady=4)

            tk.Checkbutton(
                row_frame,
                text=role,
                variable=var,
                font=("Segoe UI", 10, "bold"),
                fg=color_text,
                bg=color_bg,
                activebackground=color_bg,
                selectcolor=color_bg,
            ).pack(side="left")

            # Short description
            desc = {
                "ADMIN": "Full access — all permissions",
                "ISSUER": "Can issue & receive drawings",
                "REQUESTER": "Can request & return drawings",
            }.get(role, "")
            tk.Label(
                row_frame,
                text=desc,
                font=("Segoe UI", 8),
                fg="#6b7280",
                bg=color_bg,
            ).pack(side="left", padx=(8, 0))

        # ── Save button ──
        def save_role():
            selected = [r for r, v in role_vars.items() if v.get()]
            self._save_user_role(user["id"], selected, dlg)

        ttk.Button(
            dlg, text="Save Role", style="Primary.TButton", command=save_role
        ).pack(pady=20)

        dlg.update_idletasks()
        try:
            dlg.grab_set()
        except Exception:
            pass

    # Maps each role to its access_token set
    ROLE_PERMISSIONS = {
        "ADMIN": [1, 2, 3, 4, 5, 6],
        "ISSUER": [2, 4, 5],
        "REQUESTER": [1, 3, 5],
    }

    def _save_user_role(self, uid, roles, dlg):
        """Persist user_role and auto-update access_tokens based on selected roles."""
        try:
            if not roles:
                messagebox.showerror(
                    "Error",
                    "Please select at least one role.",
                    parent=dlg,
                )
                return

            # ── Merge permissions from all selected roles (union, sorted) ──
            merged_tokens = set()
            for role in roles:
                merged_tokens.update(self.ROLE_PERMISSIONS.get(role, []))
            merged_tokens = sorted(merged_tokens)

            # Make API call to assign user role
            data = {
                "action": "assign_user_role",
                "user_id": uid,
                "user_role": json.dumps(roles),
            }

            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(
                self.API_BASE_URL, data=encoded_data, method="POST"
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))

            if result.get("response") == "true":
                messagebox.showinfo(
                    "Success",
                    "Role updated successfully.\nPermissions set to: {}".format(
                        ", ".join(str(t) for t in merged_tokens)
                    ),
                    parent=dlg,
                )
                dlg.destroy()
                self.refresh(reset_pagination=False)
            else:
                messagebox.showerror(
                    "Error", result.get("message", "Failed to update role"), parent=dlg
                )
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    # ── DB create / update / delete ───────────────────────────────────────────

    def _create_user_db(self, username, password, department, perms, dlg):
        try:
            # Make API call to create user
            data = {
                "action": "create_user",
                "username": username,
                "password": password,
                "department": department,
                "access_tokens": json.dumps(perms),
            }

            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(
                self.API_BASE_URL, data=encoded_data, method="POST"
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))

            if result.get("response") == "true":
                messagebox.showinfo("Success", "User created", parent=dlg)
                dlg.destroy()
                self.refresh(reset_pagination=False)
            else:
                messagebox.showerror(
                    "Error", result.get("message", "Failed"), parent=dlg
                )
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    def _update_user_db(self, uid, username, password, department, perms, dlg):
        try:
            # Make API call to update user
            data = {
                "action": "update_user",
                "user_id": uid,
                "username": username,
                "department": department,
                "access_tokens": json.dumps(perms),
            }

            if password:
                data["password"] = password

            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(
                self.API_BASE_URL, data=encoded_data, method="POST"
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))

            if result.get("response") == "true":
                messagebox.showinfo("Success", "User updated", parent=dlg)
                dlg.destroy()
                self.refresh(reset_pagination=False)
            else:
                messagebox.showerror(
                    "Error", result.get("message", "Failed"), parent=dlg
                )
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=dlg)

    def _delete_user(self, user):
        if not messagebox.askyesno("Confirm", "Delete user '%s'?" % user["admin_name"]):
            return
        try:
            # Make API call to delete user
            data = {"action": "delete_user", "user_id": user["id"]}

            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(
                self.API_BASE_URL, data=encoded_data, method="POST"
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))

            if result.get("response") == "true":
                messagebox.showinfo("Success", "User Deleted")
                self.refresh(reset_pagination=False)
            else:
                messagebox.showerror(
                    "Error", result.get("message", "Failed to delete user")
                )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh(self, reset_pagination=True, silent=False, button_silent=False):
        self.table.refresh(
            reset_pagination=reset_pagination,
            silent=silent,
            button_silent=button_silent,
        )
