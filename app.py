#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from pages.drawing_requests import DrawingRequestsPage
from pages.drawing_issuance import DrawingIssuancePage
from pages.placeholders import ReturnPage, ReportsPage
from pages.users_page import UsersPage
import styles

# Page permission mapping: ID -> Page Key
# These IDs should be stored in access_tokens JSON field in drawing_users table
PAGE_PERMISSIONS = {
    1: "Drawing Requests",
    2: "Drawing Issuance",
    3: "Return",
    4: "Reports",
    5: "User Management"
}

class MainApp(ttk.Frame):
    def __init__(self, parent, username, permissions, logout_callback):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.username = username
        self.permissions = permissions  # List of page IDs user has access to
        self.logout_callback = logout_callback
        self.pages = {}
        self.current_page = None
        
        self.sidebar_visible = True
        self._build_ui()
        
        # Show first available page based on permissions immediately
        self._show_first_available_page()

    def _get_allowed_pages(self):
        """Returns list of page keys the user has access to."""
        allowed = []
        for page_id in self.permissions:
            if page_id in PAGE_PERMISSIONS:
                allowed.append(PAGE_PERMISSIONS[page_id])
        return allowed

    def _show_first_available_page(self):
        """Show the first page the user has permission to access."""
        allowed = self._get_allowed_pages()
        if allowed:
            self.show_page(allowed[0])
        else:
            # No pages allowed - show a message
            no_access_label = tk.Label(
                self.content_frame,
                text="You don't have access to any pages.\nPlease contact administrator.",
                font=("Segoe UI", 14),
                fg=styles.SECONDARY
            )
            no_access_label.pack(expand=True)

    def _build_ui(self):
        # Top Bar
        top_bar = tk.Frame(self, bg=styles.DARK, height=45)
        top_bar.pack(fill="x")

        # Toggle Button
        tk.Button(top_bar, text="☰", bg=styles.DARK, fg="white", 
                  font=("Segoe UI", 12), bd=0, activebackground=styles.SECONDARY,
                  command=self._toggle_sidebar).pack(side="left", padx=(15, 5))

        user_label = tk.Label(top_bar, bg=styles.DARK, fg="white",
                              text="Logged in as: {}".format(self.username),
                              font=("Segoe UI", 10))
        user_label.pack(side="left", padx=15)

        tk.Button(top_bar, text="Logout", bg="#dc2626", fg="white",
                  relief="flat", padx=12, pady=5,
                  command=self.logout_callback).pack(side="right", padx=15)

        # Sidebar Menu
        self.menu_frame = tk.Frame(self, bg=styles.DARK, width=180)
        self.menu_frame.pack(side="left", fill="y")

        # Only show menu items for pages the user has permission to access
        allowed_pages = self._get_allowed_pages()
        
        if "Drawing Requests" in allowed_pages:
            self._menu_btn("Drawing Requests", "Drawing Requests").pack(fill="x")
        if "Drawing Issuance" in allowed_pages:
            self._menu_btn("Drawing Issuance", "Drawing Issuance").pack(fill="x")
        if "Return" in allowed_pages:
            self._menu_btn("Return", "Return").pack(fill="x")
        if "Reports" in allowed_pages:
            self._menu_btn("Reports", "Reports").pack(fill="x")
        if "User Management" in allowed_pages:
            self._menu_btn("User Management", "User Management").pack(fill="x")

        # Content Area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(expand=True, fill="both")

    def _toggle_sidebar(self):
        if self.sidebar_visible:
            self.menu_frame.pack_forget()
            self.sidebar_visible = False
        else:
            self.menu_frame.pack(side="left", fill="y", before=self.content_frame)
            self.sidebar_visible = True

    def _menu_btn(self, txt, page_key):
        return tk.Button(self.menu_frame, text=txt,
            bg=styles.DARK, fg="white", relief="flat",
            anchor="w", padx=15, pady=8,
            command=lambda: self.show_page(page_key))

    def show_page(self, page_key):
        # Check if user has permission to access this page
        allowed_pages = self._get_allowed_pages()
        if page_key not in allowed_pages:
            messagebox.showwarning("Access Denied", "You don't have permission to access this page.")
            return
            
        # Hide current page if exists
        if self.current_page:
            self.current_page.pack_forget()

        # Get or create page
        if page_key not in self.pages:
            if page_key == "Drawing Requests":
                self.pages[page_key] = DrawingRequestsPage(self.content_frame, self.username)
            elif page_key == "Drawing Issuance":
                self.pages[page_key] = DrawingIssuancePage(self.content_frame, self.username)
            elif page_key == "Return":
                self.pages[page_key] = ReturnPage(self.content_frame)
            elif page_key == "Reports":
                self.pages[page_key] = ReportsPage(self.content_frame)
            elif page_key == "User Management":
                self.pages[page_key] = UsersPage(self.content_frame)
        
        # Show page first so user sees the layout
        self.current_page = self.pages.get(page_key)
        if self.current_page:
            self.current_page.pack(fill="both", expand=True, padx=20, pady=20)
            # Refresh data in background if the page supports it
            if hasattr(self.current_page, 'refresh'):
                self.current_page.refresh()

