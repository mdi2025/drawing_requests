#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
import auth
import threading
from app import MainApp

class LoginFrame(tk.Frame):
    def __init__(self, parent, on_login_success):
        tk.Frame.__init__(self, parent)
        self.on_login_success = on_login_success
        self._build_ui()

    def _build_ui(self):
        self.configure(bg=styles.LIGHT)
        
        # Outer container for centering
        self.outer = tk.Frame(self, bg=styles.LIGHT)
        self.outer.place(relx=0.5, rely=0.5, anchor="center")

        # Shadow-like border container
        self.shadow = tk.Frame(self.outer, bg="#e2e8f0", padx=1, pady=1)
        self.shadow.pack()

        # Login Card
        self.card = tk.Frame(self.shadow, bg="white", padx=50, pady=50)
        self.card.pack()

        # Header
        ttk.Label(
            self.card,
            text="Welcome",
            style="LoginTitle.TLabel"
        ).pack(pady=(0, 10))
        
        ttk.Label(
            self.card,
            text="Drawing Management System",
            style="LoginSubtitle.TLabel"
        ).pack(pady=(0, 40))

        # Form fields
        form_frame = tk.Frame(self.card, bg="white")
        form_frame.pack(fill="both")

        ttk.Label(form_frame, text="Username", foreground=styles.SECONDARY, background="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.username_entry = tk.Entry(form_frame, font=("Segoe UI", 11), bd=1, relief="solid", highlightthickness=1, highlightbackground="#e2e8f0", highlightcolor=styles.PRIMARY)
        self.username_entry.pack(fill="x", pady=(0, 20), ipady=8)

        ttk.Label(form_frame, text="Password", foreground=styles.SECONDARY, background="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.password_entry = tk.Entry(form_frame, show="*", font=("Segoe UI", 11), bd=1, relief="solid", highlightthickness=1, highlightbackground="#e2e8f0", highlightcolor=styles.PRIMARY)
        self.password_entry.pack(fill="x", pady=(0, 30), ipady=8)
        self.password_entry.bind("<Return>", lambda e: self._handle_login())

        self.login_btn = ttk.Button(form_frame, text="Sign In", style="Primary.TButton", command=self._handle_login)
        self.login_btn.pack(fill="x")
        
    def _handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        # UI Feedback
        self.login_btn.config(text="Signing in...", state="disabled")
        self.username_entry.config(state="disabled")
        self.password_entry.config(state="disabled")
        self.root = self.winfo_toplevel()
        self.root.config(cursor="watch")
        
        # Start background thread
        thread = threading.Thread(target=self._auth_thread, args=(username, password))
        thread.daemon = True
        thread.start()

    def _auth_thread(self, username, password):
        success, permissions = auth.authenticate(username, password)
        # Schedule update on main thread
        self.after(0, lambda: self._on_auth_complete(success, permissions, username))

    def _on_auth_complete(self, success, permissions, username):
        # Reset UI state
        self.login_btn.config(text="Sign In", state="normal")
        self.username_entry.config(state="normal")
        self.password_entry.config(state="normal")
        self.root.config(cursor="")

        if success:
            self.on_login_success(username, permissions)
        else:
            messagebox.showerror("Login Failed", "Invalid credentials")
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus()

    def reset(self):
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)

class DrawingSystemApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Drawing Management System")
        self.root.geometry("900x650")
        self.root.configure(bg=styles.LIGHT)
        
        styles.apply_styles()
        
        self.login_frame = LoginFrame(self.root, self.show_main_app)
        self.login_frame.pack(expand=True, fill="both")
        
        self.main_app = None

    def show_main_app(self, username, permissions):
        self.login_frame.pack_forget()
        if self.main_app:
            self.main_app.destroy()
        
        self.main_app = MainApp(self.root, username, permissions, self.logout)
        self.main_app.pack(expand=True, fill="both")

    def logout(self):
        if self.main_app:
            self.main_app.pack_forget()
        self.login_frame.reset()
        self.login_frame.pack(expand=True, fill="both")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DrawingSystemApp()
    app.run()
