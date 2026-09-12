import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime
import threading
import time

# PySerial is used later for ESP32 communication
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


# ============================================================
# DATABASE
# ============================================================

DATABASE_NAME = "attendance.db"

conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
cursor = conn.cursor()

# Student table
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    roll_no TEXT NOT NULL,
    class_name TEXT DEFAULT 'Class 12',
    division TEXT DEFAULT 'B'
)
""")

# Attendance table
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    name TEXT NOT NULL,
    roll_no TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    status TEXT DEFAULT 'PRESENT'
)
""")

conn.commit()


# ============================================================
# GLOBAL VARIABLES
# ============================================================

serial_connection = None
serial_running = False


# ============================================================
# ATTENDANCE FUNCTIONS
# ============================================================

def mark_attendance(uid):

    uid = uid.strip().upper()

    if not uid:
        return

    # Find student
    cursor.execute(
        "SELECT name, roll_no, class_name, division FROM students WHERE uid = ?",
        (uid,)
    )

    student = cursor.fetchone()

    if student is None:

        messagebox.showwarning(
            "Unknown Card",
            f"This NFC card is not registered.\n\nUID:\n{uid}\n\n"
            "Register this card in the Students section."
        )

        status_label.config(
            text=f"UNKNOWN CARD: {uid}"
        )

        return

    name, roll_no, class_name, division = student

    now = datetime.now()

    date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    # Check if already marked today
    cursor.execute("""
        SELECT id FROM attendance
        WHERE uid = ? AND date = ?
    """, (uid, date))

    already_present = cursor.fetchone()

    if already_present:

        status_label.config(
            text=f"{name} is already marked PRESENT today."
        )

        messagebox.showinfo(
            "Already Present",
            f"{name} (Roll {roll_no})\n\n"
            "Attendance has already been marked today."
        )

        return

    # Insert attendance
    cursor.execute("""
        INSERT INTO attendance
        (uid, name, roll_no, date, time, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        uid,
        name,
        roll_no,
        date,
        current_time,
        "PRESENT"
    ))

    conn.commit()

    # Update display
    update_attendance_table()
    update_statistics()

    status_label.config(
        text=f"✓ PRESENT — {name} | Roll {roll_no} | {current_time}"
    )

    # Clear manual UID box
    uid_entry.delete(0, tk.END)


# ============================================================
# STUDENT FUNCTIONS
# ============================================================

def add_student():

    uid = student_uid_entry.get().strip().upper()
    name = student_name_entry.get().strip()
    roll = student_roll_entry.get().strip()
    class_name = student_class_entry.get().strip()
    division = student_division_entry.get().strip()

    if not uid or not name or not roll:
        messagebox.showerror(
            "Missing Information",
            "Please enter UID, student name and roll number."
        )
        return

    if not class_name:
        class_name = "Class 12"

    if not division:
        division = "B"

    try:

        cursor.execute("""
            INSERT INTO students
            (uid, name, roll_no, class_name, division)
            VALUES (?, ?, ?, ?, ?)
        """, (
            uid,
            name,
            roll,
            class_name,
            division
        ))

        conn.commit()

        messagebox.showinfo(
            "Student Added",
            f"{name} has been successfully registered."
        )

        clear_student_fields()
        update_student_table()
        update_statistics()

    except sqlite3.IntegrityError:

        messagebox.showerror(
            "Error",
            "This NFC UID is already registered."
        )


def delete_student():

    selected = student_tree.selection()

    if not selected:
        messagebox.showwarning(
            "Select Student",
            "Please select a student first."
        )
        return

    item = student_tree.item(selected[0])

    uid = item["values"][0]
    name = item["values"][1]

    confirm = messagebox.askyesno(
        "Delete Student",
        f"Are you sure you want to delete {name}?"
    )

    if confirm:

        cursor.execute(
            "DELETE FROM students WHERE uid = ?",
            (uid,)
        )

        conn.commit()

        update_student_table()
        update_statistics()


def clear_student_fields():

    student_uid_entry.delete(0, tk.END)
    student_name_entry.delete(0, tk.END)
    student_roll_entry.delete(0, tk.END)


# ============================================================
# TABLE UPDATES
# ============================================================

def update_student_table():

    for row in student_tree.get_children():
        student_tree.delete(row)

    cursor.execute("""
        SELECT uid, name, roll_no, class_name, division
        FROM students
        ORDER BY CAST(roll_no AS INTEGER)
    """)

    students = cursor.fetchall()

    for student in students:

        student_tree.insert(
            "",
            tk.END,
            values=student
        )


def update_attendance_table():

    for row in attendance_tree.get_children():
        attendance_tree.delete(row)

    cursor.execute("""
        SELECT roll_no, name, date, time, status
        FROM attendance
        ORDER BY date DESC, time DESC
    """)

    records = cursor.fetchall()

    for record in records:

        attendance_tree.insert(
            "",
            tk.END,
            values=record
        )


def update_statistics():

    # Number of students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    # Today's attendance
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE date = ?",
        (today,)
    )

    present_today = cursor.fetchone()[0]

    total_label.config(
        text=f"Total Students\n{total_students}"
    )

    present_label.config(
        text=f"Present Today\n{present_today}"
    )

    absent_label.config(
        text=f"Absent Today\n{max(0, total_students - present_today)}"
    )


# ============================================================
# SEARCH ATTENDANCE
# ============================================================

def search_attendance():

    search = search_entry.get().strip()

    for row in attendance_tree.get_children():
        attendance_tree.delete(row)

    if search == "":

        update_attendance_table()
        return

    cursor.execute("""
        SELECT roll_no, name, date, time, status
        FROM attendance
        WHERE name LIKE ?
        OR roll_no LIKE ?
        OR date LIKE ?
        ORDER BY date DESC, time DESC
    """, (
        f"%{search}%",
        f"%{search}%",
        f"%{search}%"
    ))

    records = cursor.fetchall()

    for record in records:

        attendance_tree.insert(
            "",
            tk.END,
            values=record
        )


# ============================================================
# EXPORT CSV
# ============================================================

def export_csv():

    cursor.execute("""
        SELECT roll_no, name, date, time, status
        FROM attendance
        ORDER BY date DESC, time DESC
    """)

    records = cursor.fetchall()

    if not records:

        messagebox.showinfo(
            "No Data",
            "There are no attendance records to export."
        )

        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[
            ("CSV Files", "*.csv"),
            ("All Files", "*.*")
        ],
        title="Save Attendance CSV"
    )

    if not file_path:
        return

    with open(
        file_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Roll Number",
            "Name",
            "Date",
            "Time",
            "Status"
        ])

        writer.writerows(records)

    messagebox.showinfo(
        "Export Complete",
        "Attendance has been exported successfully."
    )


# ============================================================
# SERIAL / ESP32 FUNCTIONS
# ============================================================

def get_serial_ports():

    if not SERIAL_AVAILABLE:
        return []

    ports = serial.tools.list_ports.comports()

    return [port.device for port in ports]


def refresh_ports():

    ports = get_serial_ports()

    port_combo["values"] = ports

    if ports:
        port_combo.current(0)


def connect_esp32():

    global serial_connection
    global serial_running

    if not SERIAL_AVAILABLE:

        messagebox.showerror(
            "PySerial Missing",
            "Install PySerial using:\n\npip install pyserial"
        )

        return

    selected_port = port_combo.get()

    if not selected_port:

        messagebox.showwarning(
            "No Port",
            "Select an ESP32 COM port first."
        )

        return

    try:

        serial_connection = serial.Serial(
            selected_port,
            115200,
            timeout=1
        )

        serial_running = True

        connection_label.config(
            text=f"ESP32 Connected: {selected_port}"
        )

        connect_button.config(
            text="Disconnect",
            command=disconnect_esp32
        )

        # Start serial listening thread
        thread = threading.Thread(
            target=serial_listener,
            daemon=True
        )

        thread.start()

    except Exception as error:

        messagebox.showerror(
            "Connection Error",
            str(error)
        )


def disconnect_esp32():

    global serial_connection
    global serial_running

    serial_running = False

    if serial_connection:

        try:
            serial_connection.close()
        except:
            pass

    serial_connection = None

    connection_label.config(
        text="ESP32 Disconnected"
    )

    connect_button.config(
        text="Connect ESP32",
        command=connect_esp32
    )


def serial_listener():

    global serial_connection
    global serial_running

    while serial_running:

        try:

            if (
                serial_connection
                and serial_connection.is_open
                and serial_connection.in_waiting
            ):

                data = serial_connection.readline().decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if data:

                    # ESP32 will eventually send NFC UID here
                    root.after(
                        0,
                        lambda uid=data: mark_attendance(uid)
                    )

            else:

                time.sleep(0.1)

        except:

            time.sleep(0.5)


# ============================================================
# GUI
# ============================================================

root = tk.Tk()

root.title("Smart NFC Attendance System")
root.geometry("1100x700")
root.minsize(900, 600)

root.configure(bg="#f2f2f2")


# ------------------------------------------------------------
# TITLE
# ------------------------------------------------------------

title_frame = tk.Frame(
    root,
    bg="#1f2937",
    height=80
)

title_frame.pack(
    fill="x"
)

title_label = tk.Label(
    title_frame,
    text="SMART NFC ATTENDANCE SYSTEM",
    font=("Arial", 24, "bold"),
    fg="white",
    bg="#1f2937"
)

title_label.pack(
    pady=22
)


# ------------------------------------------------------------
# STATISTICS
# ------------------------------------------------------------

stats_frame = tk.Frame(
    root,
    bg="#f2f2f2"
)

stats_frame.pack(
    fill="x",
    padx=20,
    pady=15
)


total_label = tk.Label(
    stats_frame,
    text="Total Students\n0",
    font=("Arial", 15, "bold"),
    bg="white",
    width=20,
    height=3,
    relief="groove"
)

total_label.pack(
    side="left",
    padx=10
)


present_label = tk.Label(
    stats_frame,
    text="Present Today\n0",
    font=("Arial", 15, "bold"),
    bg="white",
    width=20,
    height=3,
    relief="groove"
)

present_label.pack(
    side="left",
    padx=10
)


absent_label = tk.Label(
    stats_frame,
    text="Absent Today\n0",
    font=("Arial", 15, "bold"),
    bg="white",
    width=20,
    height=3,
    relief="groove"
)

absent_label.pack(
    side="left",
    padx=10
)


# ------------------------------------------------------------
# NOTEBOOK / TABS
# ------------------------------------------------------------

notebook = ttk.Notebook(root)

notebook.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10
)


# ============================================================
# SCANNER TAB
# ============================================================

scanner_tab = tk.Frame(
    notebook,
    bg="white"
)

notebook.add(
    scanner_tab,
    text="  Scanner  "
)


scanner_title = tk.Label(
    scanner_tab,
    text="NFC Scanner",
    font=("Arial", 20, "bold"),
    bg="white"
)

scanner_title.pack(
    pady=(30, 10)
)


instructions = tk.Label(
    scanner_tab,
    text=(
        "For now, enter an NFC UID manually.\n"
        "Later the ESP32 + NFC reader will send the UID automatically."
    ),
    font=("Arial", 12),
    bg="white"
)

instructions.pack(
    pady=10
)


uid_entry = tk.Entry(
    scanner_tab,
    font=("Arial", 16),
    width=35,
    justify="center"
)

uid_entry.pack(
    pady=15
)


scan_button = tk.Button(
    scanner_tab,
    text="MARK ATTENDANCE",
    font=("Arial", 14, "bold"),
    width=25,
    height=2,
    command=lambda: mark_attendance(uid_entry.get())
)

scan_button.pack(
    pady=10
)


status_label = tk.Label(
    scanner_tab,
    text="Waiting for NFC card...",
    font=("Arial", 13, "bold"),
    bg="white"
)

status_label.pack(
    pady=20
)


# ============================================================
# STUDENTS TAB
# ============================================================

students_tab = tk.Frame(
    notebook,
    bg="white"
)

notebook.add(
    students_tab,
    text="  Students  "
)


form_frame = tk.Frame(
    students_tab,
    bg="white"
)

form_frame.pack(
    pady=20
)


tk.Label(
    form_frame,
    text="NFC UID",
    font=("Arial", 11),
    bg="white"
).grid(row=0, column=0, padx=5, pady=5)

student_uid_entry = tk.Entry(
    form_frame,
    width=25
)

student_uid_entry.grid(
    row=0,
    column=1,
    padx=5,
    pady=5
)


tk.Label(
    form_frame,
    text="Name",
    font=("Arial", 11),
    bg="white"
).grid(row=0, column=2, padx=5, pady=5)

student_name_entry = tk.Entry(
    form_frame,
    width=25
)

student_name_entry.grid(
    row=0,
    column=3,
    padx=5,
    pady=5
)


tk.Label(
    form_frame,
    text="Roll No.",
    font=("Arial", 11),
    bg="white"
).grid(row=1, column=0, padx=5, pady=5)

student_roll_entry = tk.Entry(
    form_frame,
    width=25
)

student_roll_entry.grid(
    row=1,
    column=1,
    padx=5,
    pady=5
)


tk.Label(
    form_frame,
    text="Class",
    font=("Arial", 11),
    bg="white"
).grid(row=1, column=2, padx=5, pady=5)

student_class_entry = tk.Entry(
    form_frame,
    width=25
)

student_class_entry.insert(
    0,
    "Class 12"
)

student_class_entry.grid(
    row=1,
    column=3,
    padx=5,
    pady=5
)


tk.Label(
    form_frame,
    text="Division",
    font=("Arial", 11),
    bg="white"
).grid(row=2, column=0, padx=5, pady=5)

student_division_entry = tk.Entry(
    form_frame,
    width=25
)

student_division_entry.insert(
    0,
    "B"
)

student_division_entry.grid(
    row=2,
    column=1,
    padx=5,
    pady=5
)


add_button = tk.Button(
    form_frame,
    text="ADD STUDENT",
    width=18,
    command=add_student
)

add_button.grid(
    row=2,
    column=3,
    pady=10
)


# Student table

student_columns = (
    "UID",
    "Name",
    "Roll No",
    "Class",
    "Division"
)

student_tree = ttk.Treeview(
    students_tab,
    columns=student_columns,
    show="headings"
)

for column in student_columns:

    student_tree.heading(
        column,
        text=column
    )

    student_tree.column(
        column,
        width=150
    )


student_tree.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10
)


delete_button = tk.Button(
    students_tab,
    text="DELETE SELECTED STUDENT",
    command=delete_student
)

delete_button.pack(
    pady=10
)


# ============================================================
# ATTENDANCE TAB
# ============================================================

attendance_tab = tk.Frame(
    notebook,
    bg="white"
)

notebook.add(
    attendance_tab,
    text="  Attendance  "
)


search_frame = tk.Frame(
    attendance_tab,
    bg="white"
)

search_frame.pack(
    pady=15
)


tk.Label(
    search_frame,
    text="Search:",
    font=("Arial", 11),
    bg="white"
).pack(
    side="left",
    padx=5
)


search_entry = tk.Entry(
    search_frame,
    width=30
)

search_entry.pack(
    side="left",
    padx=5
)


search_button = tk.Button(
    search_frame,
    text="SEARCH",
    command=search_attendance
)

search_button.pack(
    side="left",
    padx=5
)


clear_search_button = tk.Button(
    search_frame,
    text="CLEAR",
    command=lambda: [
        search_entry.delete(0, tk.END),
        update_attendance_table()
    ]
)

clear_search_button.pack(
    side="left",
    padx=5
)


export_button = tk.Button(
    search_frame,
    text="EXPORT CSV",
    command=export_csv
)

export_button.pack(
    side="left",
    padx=20
)


# Attendance table

attendance_columns = (
    "Roll No",
    "Name",
    "Date",
    "Time",
    "Status"
)

attendance_tree = ttk.Treeview(
    attendance_tab,
    columns=attendance_columns,
    show="headings"
)

for column in attendance_columns:

    attendance_tree.heading(
        column,
        text=column
    )

    attendance_tree.column(
        column,
        width=170
    )


attendance_tree.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10
)


# ============================================================
# ESP32 TAB
# ============================================================

esp32_tab = tk.Frame(
    notebook,
    bg="white"
)

notebook.add(
    esp32_tab,
    text="  ESP32  "
)


tk.Label(
    esp32_tab,
    text="ESP32 Connection",
    font=("Arial", 20, "bold"),
    bg="white"
).pack(
    pady=30
)


tk.Label(
    esp32_tab,
    text="Connect your ESP32 using USB.",
    font=("Arial", 12),
    bg="white"
).pack(
    pady=10
)


port_combo = ttk.Combobox(
    esp32_tab,
    width=25,
    state="readonly"
)

port_combo.pack(
    pady=10
)


refresh_button = tk.Button(
    esp32_tab,
    text="REFRESH PORTS",
    command=refresh_ports
)

refresh_button.pack(
    pady=5
)


connect_button = tk.Button(
    esp32_tab,
    text="Connect ESP32",
    width=20,
    command=connect_esp32
)

connect_button.pack(
    pady=10
)


connection_label = tk.Label(
    esp32_tab,
    text="ESP32 Disconnected",
    font=("Arial", 12, "bold"),
    bg="white"
)

connection_label.pack(
    pady=20
)


tk.Label(
    esp32_tab,
    text=(
        "ESP32 should eventually send one NFC UID per line.\n\n"
        "Example:\n"
        "A3 7F 21 9C\n"
        "B8 42 19 6D"
    ),
    font=("Courier", 11),
    bg="white"
).pack(
    pady=20
)


# ============================================================
# STARTUP
# ============================================================

update_student_table()
update_attendance_table()
update_statistics()
refresh_ports()


# ============================================================
# CLOSE PROGRAM
# ============================================================

def close_program():

    global serial_running

    serial_running = False

    if serial_connection:

        try:
            serial_connection.close()
        except:
            pass

    conn.close()

    root.destroy()


root.protocol(
    "WM_DELETE_WINDOW",
    close_program
)


# ============================================================
# RUN APPLICATION
# ============================================================

root.mainloop()