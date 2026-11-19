import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import os
import uuid
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ====================== CONFIG ======================
CLASS_LEVELS = ("P1A", "P1B", "P2A", "P2B", "P3A", "P3B", "P4A", "P4B", "P5", "P6")
SUBJECT_LIST = ("English", "Kinyarwanda", "Mathematics", "SET", "SST", "French", "Kiswahili")
ASSESSMENT_TYPES = ("Homework", "Exercise", "Quiz", "Exam", "Midterm")

PAYMENT_MONTHS = []
for year in (2026, 2027, 2028, 2029, 2030):
    start = 11 if year == 2026 else 1
    for m in range(start, 13):
        PAYMENT_MONTHS.append(f"{year}-{m:02d}")

PAYMENT_STATUS = (
    "Paid",
    "Not paid",
    "Late 5 days",
    "Late 5-10 days",
    "Late 15 days",
    "Bonus",
    "Drop out"
)
MONTHLY_FEE = 5000
DB_FILE = "igisubizo_academy.db"

# ====================== SECURITY & DB HELPERS ======================
def hash_pwd(pwd: str) -> str:
    return hashlib.sha256(pwd.strip().encode("utf-8")).hexdigest()

def verify_pwd(raw_pwd: str, stored_pwd: str) -> bool:
    if not stored_pwd:
        return False
    return raw_pwd.strip() == stored_pwd or hash_pwd(raw_pwd) == stored_pwd

def get_conn():
    conn = sqlite3.connect(DB_FILE, timeout=20, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def ensure_column(cursor, table_name, column_name, column_def):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing = [row[1] for row in cursor.fetchall()]
    if column_name not in existing:
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        except sqlite3.OperationalError:
            pass

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            gender TEXT DEFAULT 'Male',
            parent_name TEXT,
            parent_phone TEXT,
            parent_email TEXT,
            status TEXT DEFAULT 'Active',
            is_deleted INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    for col, cdef in (
        ("gender", "TEXT DEFAULT 'Male'"),
        ("parent_name", "TEXT"),
        ("parent_phone", "TEXT"),
        ("parent_email", "TEXT"),
        ("status", "TEXT DEFAULT 'Active'"),
        ("is_deleted", "INTEGER DEFAULT 0"),
        ("created_at", "TEXT")
    ):
        ensure_column(c, "students", col, cdef)

    c.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject TEXT,
            assessment_type TEXT DEFAULT 'Exam',
            score REAL,
            max_score REAL DEFAULT 100,
            term TEXT,
            date TEXT,
            teacher TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    for col, cdef in (
        ("assessment_type", "TEXT DEFAULT 'Exam'"),
        ("max_score", "REAL DEFAULT 100"),
        ("term", "TEXT"),
        ("date", "TEXT"),
        ("teacher", "TEXT"),
        ("is_deleted", "INTEGER DEFAULT 0")
    ):
        ensure_column(c, "grades", col, cdef)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT,
            teacher TEXT,
            notes TEXT
        )
    """)
    ensure_column(c, "attendance", "notes", "TEXT")

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            month_year TEXT,
            amount REAL DEFAULT 5000,
            status TEXT DEFAULT 'Not paid',
            paid_date TEXT,
            recorded_by TEXT,
            notes TEXT,
            UNIQUE(student_id, month_year)
        )
    """)
    for col, cdef in (
        ("amount", "REAL DEFAULT 5000"),
        ("status", "TEXT DEFAULT 'Not paid'"),
        ("paid_date", "TEXT"),
        ("recorded_by", "TEXT"),
        ("notes", "TEXT")
    ):
        ensure_column(c, "payments", col, cdef)

    c.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            role TEXT,
            username TEXT UNIQUE,
            password TEXT,
            phone TEXT,
            assigned_classes TEXT DEFAULT 'ALL',
            assigned_subjects TEXT DEFAULT 'ALL',
            status TEXT DEFAULT 'Active'
        )
    """)
    for col, cdef in (
        ("full_name", "TEXT"),
        ("role", "TEXT"),
        ("username", "TEXT"),
        ("password", "TEXT"),
        ("phone", "TEXT"),
        ("assigned_classes", "TEXT DEFAULT 'ALL'"),
        ("assigned_subjects", "TEXT DEFAULT 'ALL'"),
        ("status", "TEXT DEFAULT 'Active'")
    ):
        ensure_column(c, "staff", col, cdef)

    c.execute("""
        CREATE TABLE IF NOT EXISTS staff_invites (
            invite_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invite_code TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'Teacher',
            phone TEXT,
            assigned_classes TEXT DEFAULT 'NONE',
            assigned_subjects TEXT DEFAULT 'NONE',
            status TEXT DEFAULT 'Pending',
            created_by TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS student_advisories (
            advisory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_username TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            assigned_date TEXT,
            status TEXT DEFAULT 'Active',
            UNIQUE(teacher_username, student_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS advisory_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_username TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            week_ending TEXT NOT NULL,
            wellbeing_status TEXT DEFAULT 'Thriving',
            discussion_notes TEXT,
            action_plan TEXT,
            submitted_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conduct (
            conduct_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_type TEXT,
            person_name TEXT,
            grade_or_role TEXT,
            incident_type TEXT,
            points_change INTEGER DEFAULT 0,
            notes TEXT,
            date TEXT,
            recorded_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            perm_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT,
            category TEXT,
            grade_or_role TEXT,
            reason TEXT,
            emergency_level TEXT,
            status TEXT DEFAULT 'Approved',
            date TEXT,
            recorded_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_name TEXT,
            sender_role TEXT,
            recipient TEXT,
            subject TEXT,
            message TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            created_by TEXT,
            created_at TEXT
        )
    """)

    c.execute("SELECT COUNT(*) FROM staff WHERE LOWER(username)='admin'")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status)
            VALUES ('Head Administrator', 'Administration', 'admin', ?, '0780000000', 'ALL', 'ALL', 'Active')
        """, (hash_pwd("admin123"),))

    conn.commit()
    conn.close()

def generate_report_card_pdf(student_row, grades_df, term):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("<b>IGISUBIZO ACADEMY</b>", styles["Title"]),
        Paragraph(f"Official Student Report Card - {term}", styles["Heading2"]),
        Spacer(1, 12),
        Paragraph(
            f"<b>Student Name:</b> {student_row['student_name']}<br/>"
            f"<b>Class Level:</b> {student_row['grade']}<br/>"
            f"<b>Gender:</b> {student_row.get('gender', '-')}<br/>"
            f"<b>Parent / Guardian:</b> {student_row.get('parent_name', '-')} ({student_row.get('parent_phone', '-')})<br/>"
            f"<b>Date Issued:</b> {datetime.date.today()}",
            styles["Normal"]
        ),
        Spacer(1, 16)
    ]

    data = [["Subject", "Assessment", "Score", "Max Score", "Percentage"]]
    total_score, total_max = 0.0, 0.0
    for _, row in grades_df.iterrows():
        m_sc = float(row["max_score"]) if row["max_score"] else 100.0
        sc = float(row["score"]) if row["score"] else 0.0
        pct = (sc / m_sc * 100.0) if m_sc > 0 else 0.0
        data.append([str(row["subject"]), str(row["assessment_type"]), f"{sc:.1f}", f"{m_sc:.1f}", f"{pct:.1f}%"])
        total_score += sc
        total_max += m_sc

    overall_pct = (total_score / total_max * 100.0) if total_max > 0 else 0.0
    data.append(["TOTAL / AVERAGE", "-", f"{total_score:.1f}", f"{total_max:.1f}", f"{overall_pct:.1f}%"])

    table = Table(data, colWidths=(130, 100, 70, 70, 80))
    table.setStyle(TableStyle([
import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import os
import uuid
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ====================== CONFIG ======================
CLASS_LEVELS = ["P1A", "P1B", "P2A", "P2B", "P3A", "P3B", "P4A", "P4B", "P5", "P6"]
SUBJECT_LIST = ["English", "Kinyarwanda", "Mathematics", "SET", "SST", "French", "Kiswahili"]
ASSESSMENT_TYPES = ["Homework", "Exercise", "Quiz", "Exam", "Midterm"]

PAYMENT_MONTHS = []
for year in:
    start = 11 if year == 2026 else 1
    for m in range(start, 13):
        PAYMENT_MONTHS.append(f"{year}-{m:02d}")

PAYMENT_STATUS = [
    "Paid",
    "Not paid",
    "Late 5 days",
    "Late 5-10 days",
    "Late 15 days",
    "Bonus",
    "Drop out"
]
MONTHLY_FEE = 5000
DB_FILE = "igisubizo_academy.db"

# ====================== SECURITY & DB HELPERS ======================
def hash_pwd(pwd: str) -> str:
    return hashlib.sha256(pwd.strip().encode("utf-8")).hexdigest()

def verify_pwd(raw_pwd: str, stored_pwd: str) -> bool:
    if not stored_pwd:
        return False
    return raw_pwd.strip() == stored_pwd or hash_pwd(raw_pwd) == stored_pwd

def get_conn():
    conn = sqlite3.connect(DB_FILE, timeout=20, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def ensure_column(cursor, table_name, column_name, column_def):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing = [row[1] for row in cursor.fetchall()]
    if column_name not in existing:
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        except sqlite3.OperationalError:
            pass

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            gender TEXT DEFAULT 'Male',
            parent_name TEXT,
            parent_phone TEXT,
            parent_email TEXT,
            status TEXT DEFAULT 'Active',
            is_deleted INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    for col, cdef in [
        ("gender", "TEXT DEFAULT 'Male'"),
        ("parent_name", "TEXT"),
        ("parent_phone", "TEXT"),
        ("parent_email", "TEXT"),
        ("status", "TEXT DEFAULT 'Active'"),
        ("is_deleted", "INTEGER DEFAULT 0"),
        ("created_at", "TEXT")
    ]:
        ensure_column(c, "students", col, cdef)

    c.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject TEXT,
            assessment_type TEXT DEFAULT 'Exam',
            score REAL,
            max_score REAL DEFAULT 100,
            term TEXT,
            date TEXT,
            teacher TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    for col, cdef in [
        ("assessment_type", "TEXT DEFAULT 'Exam'"),
        ("max_score", "REAL DEFAULT 100"),
        ("term", "TEXT"),
        ("date", "TEXT"),
        ("teacher", "TEXT"),
        ("is_deleted", "INTEGER DEFAULT 0")
    ]:
        ensure_column(c, "grades", col, cdef)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT,
            teacher TEXT,
            notes TEXT
        )
    """)
    ensure_column(c, "attendance", "notes", "TEXT")

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            month_year TEXT,
            amount REAL DEFAULT 5000,
            status TEXT DEFAULT 'Not paid',
            paid_date TEXT,
            recorded_by TEXT,
            notes TEXT,
            UNIQUE(student_id, month_year)
        )
    """)
    for col, cdef in [
        ("amount", "REAL DEFAULT 5000"),
        ("status", "TEXT DEFAULT 'Not paid'"),
        ("paid_date", "TEXT"),
        ("recorded_by", "TEXT"),
        ("notes", "TEXT")
    ]:
        ensure_column(c, "payments", col, cdef)

    c.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            role TEXT,
            username TEXT UNIQUE,
            password TEXT,
            phone TEXT,
            assigned_classes TEXT DEFAULT 'ALL',
            assigned_subjects TEXT DEFAULT 'ALL',
            status TEXT DEFAULT 'Active'
        )
    """)
    for col, cdef in [
        ("full_name", "TEXT"),
        ("role", "TEXT"),
        ("username", "TEXT"),
        ("password", "TEXT"),
        ("phone", "TEXT"),
        ("assigned_classes", "TEXT DEFAULT 'ALL'"),
        ("assigned_subjects", "TEXT DEFAULT 'ALL'"),
        ("status", "TEXT DEFAULT 'Active'")
    ]:
        ensure_column(c, "staff", col, cdef)

    c.execute("""
        CREATE TABLE IF NOT EXISTS staff_invites (
            invite_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invite_code TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'Teacher',
            phone TEXT,
            assigned_classes TEXT DEFAULT 'NONE',
            assigned_subjects TEXT DEFAULT 'NONE',
            status TEXT DEFAULT 'Pending',
            created_by TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS student_advisories (
            advisory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_username TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            assigned_date TEXT,
            status TEXT DEFAULT 'Active',
            UNIQUE(teacher_username, student_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS advisory_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_username TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            week_ending TEXT NOT NULL,
            wellbeing_status TEXT DEFAULT 'Thriving',
            discussion_notes TEXT,
            action_plan TEXT,
            submitted_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conduct (
            conduct_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_type TEXT,
            person_name TEXT,
            grade_or_role TEXT,
            incident_type TEXT,
            points_change INTEGER DEFAULT 0,
            notes TEXT,
            date TEXT,
            recorded_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            perm_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT,
            category TEXT,
            grade_or_role TEXT,
            reason TEXT,
            emergency_level TEXT,
            status TEXT DEFAULT 'Approved',
            date TEXT,
            recorded_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_name TEXT,
            sender_role TEXT,
            recipient TEXT,
            subject TEXT,
            message TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            created_by TEXT,
            created_at TEXT
        )
    """)

    c.execute("SELECT COUNT(*) FROM staff WHERE LOWER(username)='admin'")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status)
            VALUES ('Head Administrator', 'Administration', 'admin', ?, '0780000000', 'ALL', 'ALL', 'Active')
        """, (hash_pwd("admin123"),))

    conn.commit()
    conn.close()

def generate_report_card_pdf(student_row, grades_df, term):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("<b>IGISUBIZO ACADEMY</b>", styles["Title"]),
        Paragraph(f"Official Student Report Card - {term}", styles["Heading2"]),
        Spacer(1, 12),
        Paragraph(
            f"<b>Student Name:</b> {student_row['student_name']}<br/>"
            f"<b>Class Level:</b> {student_row['grade']}<br/>"
            f"<b>Gender:</b> {student_row.get('gender', '-')}<br/>"
            f"<b>Parent / Guardian:</b> {student_row.get('parent_name', '-')} ({student_row.get('parent_phone', '-')})<br/>"
            f"<b>Date Issued:</b> {datetime.date.today()}",
            styles["Normal"]
        ),
        Spacer(1, 16)
    ]

    data = [["Subject", "Assessment", "Score", "Max Score", "Percentage"]]
    total_score, total_max = 0.0, 0.0
    for _, row in grades_df.iterrows():
        m_sc = float(row["max_score"]) if row["max_score"] else 100.0
        sc = float(row["score"]) if row["score"] else 0.0
        pct = (sc / m_sc * 100.0) if m_sc > 0 else 0.0
        data.append([str(row["subject"]), str(row["assessment_type"]), f"{sc:.1f}", f"{m_sc:.1f}", f"{pct:.1f}%"])
        total_score += sc
        total_max += m_sc

    overall_pct = (total_score / total_max * 100.0) if total_max > 0 else 0.0
    data.append(["TOTAL / AVERAGE", "-", f"{total_score:.1f}", f"{total_max:.1f}", f"{overall_pct:.1f}%"])

    table = Table(data, colWidths=[130, 100, 70, 70, 80])
    table.setStyle(TableStyle([
