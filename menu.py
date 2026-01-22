#!/usr/bin/env python2.7
import Tkinter as tk
import tkMessageBox
import ttk

# -------------------
# Login Credentials
# -------------------
USERS = {
    "admin": "admin123",
    "user1": "password"
}

# -------------------
# Functions
# -------------------
def login():
    username = username_entry.get()
    password = password_entry.get()
    if username in USERS and USERS[username] == password:
        show_main_app(username)
    else:
        tkMessageBox.showerror("Login Failed", "Invalid username or password!")

def logout():
    main_frame.pack_forget()
    login_frame.pack(expand=True, fill="both")
    username_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)

def show_page(page_name):
    for widget in content_frame.winfo_children():
        widget.destroy()

    if page_name == "Drawing Requests Page":
        # Search bar
        search_frame = ttk.Frame(content_frame)
        search_frame.pack(fill="x", pady=(10, 5), padx=10)
        ttk.Label(search_frame, text="Search Drawing:", font=("Arial", 12)).pack(side="left", padx=(0,5))
        search_entry = ttk.Entry(search_frame, font=("Arial", 12))
        search_entry.pack(side="left", fill="x", expand=True, padx=(0,5))

        # Table
        columns = ("Drawing No", "Revision", "Status", "Action")
        tree = ttk.Treeview(content_frame, columns=columns, show="headings", height=10)
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        # Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        style.configure("Treeview", rowheight=25, font=("Arial", 11))
        style.map('Treeview', background=[('selected', '#2980b9')], foreground=[('selected', 'white')])

        # Columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")

        # Example data
        drawings = [
            ("DR-001", "A", "Pending"),
            ("DR-002", "B", "Approved"),
            ("DR-003", "C", "Pending"),
            ("DR-004", "A", "Rejected"),
            ("DR-005", "B", "Pending"),
        ]

        # Insert data with alternating colors
        for i, (dr_no, rev, status) in enumerate(drawings):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            tree.insert("", "end", values=(dr_no, rev, status, "Request"), tags=(tag,))

        tree.tag_configure("evenrow", background="#ecf0f1")
        tree.tag_configure("oddrow", background="#ffffff")

        # Handle click on "Request"
        def on_click(event):
            region = tree.identify("region", event.x, event.y)
            if region == "cell":
                col = tree.identify_column(event.x)
                item = tree.identify_row(event.y)
                if col == "#4":  # 4th column = Action
                    values = tree.item(item, "values")
                    tkMessageBox.showinfo("Request", "Request submitted for Drawing No: {}".format(values[0]))

        tree.bind("<Button-1>", on_click)

        # Search functionality
        def filter_drawings(*args):
            query = search_entry.get().lower()
            for item in tree.get_children():
                vals = tree.item(item, "values")
                if query in vals[0].lower() or query in vals[1].lower() or query in vals[2].lower():
                    tree.reattach(item, '', 'end')
                else:
                    tree.detach(item)

        search_entry.bind("<KeyRelease>", filter_drawings)

    else:
        label = ttk.Label(content_frame, text=page_name, font=("Arial", 14))
        label.pack(pady=20)

def show_main_app(username):
    login_frame.pack_forget()
    main_frame.pack(expand=True, fill="both")
    user_label.config(text="Logged in as: {}".format(username))
    show_page("Welcome, {}!".format(username))

# -------------------
# Root Window
# -------------------
root = tk.Tk()
root.title("Drawing Management System")
root.geometry("800x500")
root.resizable(True, True)  # allow resizing horizontally and vertically

# -------------------
# Login Frame
# -------------------
login_frame = tk.Frame(root, bg="#ecf0f1")
login_frame.pack(expand=True, fill="both")

tk.Label(login_frame, text="Username:", font=("Arial", 12), bg="#ecf0f1").pack(pady=10)
username_entry = tk.Entry(login_frame, font=("Arial", 12))
username_entry.pack()

tk.Label(login_frame, text="Password:", font=("Arial", 12), bg="#ecf0f1").pack(pady=10)
password_entry = tk.Entry(login_frame, font=("Arial", 12), show="*")
password_entry.pack()

tk.Button(login_frame, text="Login", font=("Arial", 12), bg="#2980b9", fg="white",
          command=login).pack(pady=20)

# -------------------
# Main Application Frame
# -------------------
main_frame = tk.Frame(root)

# Top bar with username and logout
top_bar = tk.Frame(main_frame, height=30, bg="#34495e")
top_bar.pack(side="top", fill="x")
user_label = tk.Label(top_bar, text="", fg="white", bg="#34495e", font=("Arial", 10))
user_label.pack(side="left", padx=10)
logout_button = tk.Button(top_bar, text="Logout", command=logout, bg="#c0392b", fg="white", relief="flat")
logout_button.pack(side="right", padx=10)

# Left menu
menu_frame = tk.Frame(main_frame, width=150, bg="#2c3e50")
menu_frame.pack(side="left", fill="y")

buttons = [
    ("Drawing Requests", "Drawing Requests Page"),
    ("Drawing Issuance", "Drawing Issuance Page"),
    ("Return", "Return Page"),
    ("Reports", "Reports Page")
]

for text, page in buttons:
    btn = tk.Button(menu_frame, text=text, fg="white", bg="#34495e",
                    relief="flat", command=lambda p=page: show_page(p))
    btn.pack(fill="x", pady=5, padx=5)

# Main content area
content_frame = tk.Frame(main_frame, bg="white")
content_frame.pack(side="right", expand=True, fill="both")

# -------------------
# Start the app
# -------------------
root.mainloop()
