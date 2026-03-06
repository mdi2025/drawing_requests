#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import styles
import auth
import threading
from app import MainApp
import math

class LoaderFrame(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.configure(bg=styles.LIGHT)
        self._build_ui()
        self.animation_running = False
        self.angle = 0
        
    def _build_ui(self):
        # Center container
        container = tk.Frame(self, bg=styles.LIGHT)
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Canvas for circular loader
        self.canvas = tk.Canvas(container, width=80, height=80, bg=styles.LIGHT, highlightthickness=0)
        self.canvas.pack(pady=(0, 20))
        
        # Loading text
        tk.Label(
            container,
            text="Loading...",
            font=("Segoe UI", 14),
            fg=styles.PRIMARY,
            bg=styles.LIGHT
        ).pack()
        
    def start_animation(self):
        """Start the circular loader animation."""
        self.animation_running = True
        self._animate()
        
    def stop_animation(self):
        """Stop the circular loader animation."""
        self.animation_running = False
        
    def _animate(self):
        """Animate the circular loader."""
        if not self.animation_running:
            return
            
        self.canvas.delete("all")
        
        # Draw circular arc
        center_x, center_y = 40, 40
        radius = 30
        
        # Calculate arc parameters
        start_angle = self.angle
        extent = 280  # Arc length in degrees
        
        # Draw the arc
        self.canvas.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=start_angle,
            extent=extent,
            outline=styles.PRIMARY,
            width=4,
            style="arc"
        )
        
        # Update angle for next frame
        self.angle = (self.angle + 10) % 360
        
        # Schedule next frame (60 FPS = ~16ms per frame)
        self.after(16, self._animate)

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
            text="DMS",
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
        
        # Warm up database connection in background
        from db_handler import db
        db.warm_up()
        
        self.login_frame = LoginFrame(self.root, self.show_main_app)
        self.login_frame.pack(expand=True, fill="both")
        
        # Create loader frame but don't pack it yet
        self.loader_frame = LoaderFrame(self.root)
        
        self.main_app = None

    def show_main_app(self, username, permissions):
        # Hide login frame and show loader
        self.login_frame.pack_forget()
        self.loader_frame.pack(expand=True, fill="both")
        self.loader_frame.start_animation()
        
        # Create main app in background thread
        def create_app():
            # Small delay to ensure loader is visible
            import time
            time.sleep(0.1)
            
            # Schedule app creation on main thread
            self.root.after(0, lambda: self._finish_loading(username, permissions))
        
        thread = threading.Thread(target=create_app)
        thread.daemon = True
        thread.start()
    
    def _finish_loading(self, username, permissions):
        """Complete the app loading process on the main thread."""
        if self.main_app:
            self.main_app.destroy()
        
        # Create and show main app immediately
        self.main_app = MainApp(self.root, username, permissions, self.logout)
        
        # Hide loader and show main app
        self.loader_frame.stop_animation()
        self.loader_frame.pack_forget()
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
