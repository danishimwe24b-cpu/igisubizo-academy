import os
import io
import sqlite3
import datetime
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

CLASS_LEVELS = ["P1A", "P1B", "P2A", "P2B", "P3A", "P3B", "P4A", "P4B", "P5", "P6"]
SUBJECT_LIST = ["English", "Kinyarwanda", "Mathematics", "SET", "SST", "French", "Kiswahili"]
PAYMENT_MONTHS = [
    "2026-12", "2027-01", "2027-02", "2027-03", "2027-04", "2027-05",
    "2027-06", "2027-07", "2027-08", "2027-09", "2027-10", "2027-11", "2027-12"
]
MONTHLY_FEE = 5000
SALARY_DEFAULTS = {
    "Teacher": 50000,
    "Cleaner": 25000,
    "Safe Walker": 15000,
    "Security Guard": 30000,
    "Administration": 60000,
    "Register Officer": 50000
}

# ==================== TRANSLATIONS (4 LANGUAGES) ====================
TRANSLATIONS = {
    "English": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "School Management, Finance, Conduct & Report Card System",
        "login_header": "System Login Portal",
        "select_role": "Select Portal Role",
        "username": "Username / Parent Phone",
        "password": "Password / PIN",
        "login_btn": "Login",
        "logout_btn": "Logout",
        "menu": "Navigation Menu",
        "dashboard": "Executive Dashboard (All Departments)",
        "students": "Students (By Class Level)",
        "grades": "Grades & Progress",
        "report_card": "Generate Report Card (PDF)",
        "attendance": "Class Attendance",
        "conduct": "Conduct (Students & Staff)",
        "payments": "Payments (Daily, Weekly, Monthly & Unpaid)",
        "finance": "Monthly Budget & Expenses",
        "reports": "Teacher Weekly Reports",
        "staff": "Staff, Salaries & Accounts",
        "tasks": "Task Assignments",
        "chat": "Communication & Parent Requests",
        "change_pwd": "Change Password",
        "active_students": "Active Students",
        "total_collected": "Total Fees Collected (RWF)",
        "select_grade": "Select Class Level First",
        "save": "Save",
    },
    "Kinyarwanda": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Sisitemu y'Ishuri, Imari, Imyitwarire n'Indangamanota",
        "login_header": "Kwinjira muri Sisitemu",
        "select_role": "Hitamo Urwego",
        "username": "Izina / Telefoni y'Umubyeyi",
        "password": "Ijambo ry'ibanga",
        "login_btn": "Injira",
        "logout_btn": "Sohoka",
        "menu": "Ibice bya Sisitemu",
        "dashboard": "Incamake y'Amashami Yose (Dashboard)",
        "students": "Abanyeshuri (Ku Ishuri)",
        "grades": "Amanota n'Iterambere",
        "report_card": "Indangamanota (PDF Report Card)",
        "attendance": "Kwitabira Ishuri (Attendance)",
        "conduct": "Imyitwarire (Abanyeshuri n'Abakozi)",
        "payments": "Ubwishyu (Buri Munsi, Icyumweru, Ukwezi)",
        "finance": "Ingengo y'Imari n'Ibyakoreshejwe",
        "reports": "Raporo y'Icyumweru y'Umwarimu",
        "staff": "Abakozi, Imishahara & Konti",
        "tasks": "Gutanga Inshingano (Tasks)",
        "chat": "Itumanaho n'Impushya z'Ababyeyi",
        "change_pwd": "Guhindura Ijambo ry'Ibanga",
        "active_students": "Abanyeshuri Biga (Active)",
        "total_collected": "Amafaranga Yose Yishyuwe (RWF)",
        "select_grade": "Banza Uhitemo Ishuri (Class Level)",
        "save": "Bika Amakuru",
    },
    "French": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Système de Gestion Scolaire, Conduite et Bulletins",
        "login_header": "Portail de Connexion",
        "select_role": "Choisir le Rôle",
        "username": "Nom d'utilisateur / Téléphone Parent",
        "password": "Mot de passe",
        "login_btn": "Se connecter",
        "logout_btn": "Déconnexion",
        "menu": "Menu Principal",
        "dashboard": "Tableau de Bord (Tous Départements)",
        "students": "Élèves (Par Classe)",
        "grades": "Notes et Progrès",
        "report_card": "Bulletin Scolaire (PDF)",
        "attendance": "Présences par Classe",
        "conduct": "Conduite (Élèves & Personnel)",
        "payments": "Paiements (Jour, Semaine, Mois & Impayés)",
        "finance": "Budget Mensuel et Dépenses",
        "reports": "Rapport Hebdomadaire Enseignant",
        "staff": "Personnel, Salaires & Comptes",
        "tasks": "Attribution des Tâches",
        "chat": "Communication et Demandes Parents",
        "change_pwd": "Changer le Mot de Passe",
        "active_students": "Élèves Actifs",
        "total_collected": "Total Frais Perçus (RWF)",
        "select_grade": "Choisissez d'abord la Classe",
        "save": "Enregistrer",
    },
    "Kiswahili": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Mfumo wa Usimamizi wa Shule, Nidhamu na Ripoti",
        "login_header": "Sehemu ya Kuingia",
        "select_role": "Chagua Nafasi Yako",
        "username": "Jina la Mtumiaji / Simu ya Mzazi",
        "password": "Nenosiri",
        "login_btn": "Ingia",
        "logout_btn": "Toka",
        "menu": "Menyu Kuu",
        "dashboard": "Dashibodi (Idara Zote)",
        "students": "Wanafunzi (Kwa Darasa)",
        "grades": "Alama na Maendeleo",
        "report_card": "Ripoti ya Mwanafunzi (PDF)",
        "attendance": "Mahudhurio ya Darasa",
        "conduct": "Nidhamu (Wanafunzi na Wafanyakazi)",
        "payments": "Malipo (Kila Siku, Wiki, Mwezi)",
        "finance": "Bajeti ya Mwezi na Matumizi",
        "reports": "Ripoti ya Wiki ya Mwalimu",
        "staff": "Wafanyakazi, Mishahara & Akaunti",
        "tasks": "Ugawaji wa Kazi",
        "chat": "Mawasiliano na Maombi ya Wazazi",
        "change_pwd": "Badilisha Nenosiri",
        "active_students": "Wanafunzi Wanaosoma (Active)",
        "total_collected": "Jumla ya Ada Zilizokusanywa (RWF)",
        "select_grade": "Chagua Darasa Kwanza",
        "save": "Hifadhi",
    }
}

# ==================== DATABASE SETUP & MIGRATION ====================
def get_conn():
    return sqlite3.connect('igisubizo_academy.db', timeout=15, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        grade TEXT NOT NULL,
        parent_name TEXT,
        parent_phone TEXT,
        parent_email TEXT,
        status TEXT DEFAULT 'Active',
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        subject TEXT,
        assessment_type TEXT DEFAULT 'Exam',
        score REAL,
        max_score REAL DEFAULT 100,
        term TEXT,
        date TEXT,
        teacher TEXT,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        teacher TEXT,
        notes TEXT,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        month_year TEXT,
        amount REAL DEFAULT 5000,
        paid_date TEXT,
        recorded_by TEXT,
        UNIQUE(student_id, month_year),
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS monthly_budgets (
        budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_year TEXT,
        category TEXT,
        allocated_amount REAL,
        spent_amount REAL DEFAULT 0,
        description TEXT,
        date TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS conduct (
        conduct_id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_type TEXT,
        person_name TEXT,
        grade_or_role TEXT,
        incident_type TEXT,
        points_change INTEGER,
        notes TEXT,
        date TEXT,
        recorded_by TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS teacher_reports (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_name TEXT,
        grade TEXT,
        week_ending TEXT,
        topics_covered TEXT,
        challenges TEXT,
        submitted_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS staff (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        salary REAL,
        status TEXT DEFAULT 'Active'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        assigned_to TEXT,
        title TEXT,
        description TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'Pending',
        assigned_by TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_name TEXT,
        sender_role TEXT,
        recipient TEXT,
        subject TEXT,
        message TEXT,
        created_at TEXT
    )''')

    # Seed default Admin account if staff table is empty
    c.execute("SELECT COUNT(*) FROM staff")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO staff (full_name, role, username, password, phone, salary) VALUES (?, ?, ?, ?, ?, ?)",
            ("Head Administrator", "Administration", "admin", "admin123", "0780000000", 60000)
        )

    conn.commit()
    conn.close()

init_db()
import os
import io
import sqlite3
import datetime
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

CLASS_LEVELS = ["P1A", "P1B", "P2A", "P2B", "P3A", "P3B", "P4A", "P4B", "P5", "P6"]
SUBJECT_LIST = ["English", "Kinyarwanda", "Mathematics", "SET", "SST", "French", "Kiswahili"]
PAYMENT_MONTHS = [
    "2026-12", "2027-01", "2027-02", "2027-03", "2027-04", "2027-05",
    "2027-06", "2027-07", "2027-08", "2027-09", "2027-10", "2027-11", "2027-12"
]
MONTHLY_FEE = 5000
SALARY_DEFAULTS = {
    "Teacher": 50000,
    "Cleaner": 25000,
    "Safe Walker": 15000,
    "Security Guard": 30000,
    "Administration": 60000,
    "Register Officer": 50000
}

# ==================== TRANSLATIONS (4 LANGUAGES) ====================
TRANSLATIONS = {
    "English": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "School Management, Finance, Conduct & Report Card System",
        "login_header": "System Login Portal",
        "select_role": "Select Portal Role",
        "username": "Username / Parent Phone",
        "password": "Password / PIN",
        "login_btn": "Login",
        "logout_btn": "Logout",
        "menu": "Navigation Menu",
        "dashboard": "Executive Dashboard (All Departments)",
        "students": "Students (By Class Level)",
        "grades": "Grades & Progress",
        "report_card": "Generate Report Card (PDF)",
        "attendance": "Class Attendance",
        "conduct": "Conduct (Students & Staff)",
        "payments": "Payments (Daily, Weekly, Monthly & Unpaid)",
        "finance": "Monthly Budget & Expenses",
        "reports": "Teacher Weekly Reports",
        "staff": "Staff, Salaries & Accounts",
        "tasks": "Task Assignments",
        "chat": "Communication & Parent Requests",
        "change_pwd": "Change Password",
        "active_students": "Active Students",
        "total_collected": "Total Fees Collected (RWF)",
        "select_grade": "Select Class Level First",
        "save": "Save",
    },
    "Kinyarwanda": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Sisitemu y'Ishuri, Imari, Imyitwarire n'Indangamanota",
        "login_header": "Kwinjira muri Sisitemu",
        "select_role": "Hitamo Urwego",
        "username": "Izina / Telefoni y'Umubyeyi",
        "password": "Ijambo ry'ibanga",
        "login_btn": "Injira",
        "logout_btn": "Sohoka",
        "menu": "Ibice bya Sisitemu",
        "dashboard": "Incamake y'Amashami Yose (Dashboard)",
        "students": "Abanyeshuri (Ku Ishuri)",
        "grades": "Amanota n'Iterambere",
        "report_card": "Indangamanota (PDF Report Card)",
        "attendance": "Kwitabira Ishuri (Attendance)",
        "conduct": "Imyitwarire (Abanyeshuri n'Abakozi)",
        "payments": "Ubwishyu (Buri Munsi, Icyumweru, Ukwezi)",
        "finance": "Ingengo y'Imari n'Ibyakoreshejwe",
        "reports": "Raporo y'Icyumweru y'Umwarimu",
        "staff": "Abakozi, Imishahara & Konti",
        "tasks": "Gutanga Inshingano (Tasks)",
        "chat": "Itumanaho n'Impushya z'Ababyeyi",
        "change_pwd": "Guhindura Ijambo ry'Ibanga",
        "active_students": "Abanyeshuri Biga (Active)",
        "total_collected": "Amafaranga Yose Yishyuwe (RWF)",
        "select_grade": "Banza Uhitemo Ishuri (Class Level)",
        "save": "Bika Amakuru",
    },
    "French": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Système de Gestion Scolaire, Conduite et Bulletins",
        "login_header": "Portail de Connexion",
        "select_role": "Choisir le Rôle",
        "username": "Nom d'utilisateur / Téléphone Parent",
        "password": "Mot de passe",
        "login_btn": "Se connecter",
        "logout_btn": "Déconnexion",
        "menu": "Menu Principal",
        "dashboard": "Tableau de Bord (Tous Départements)",
        "students": "Élèves (Par Classe)",
        "grades": "Notes et Progrès",
        "report_card": "Bulletin Scolaire (PDF)",
        "attendance": "Présences par Classe",
        "conduct": "Conduite (Élèves & Personnel)",
        "payments": "Paiements (Jour, Semaine, Mois & Impayés)",
        "finance": "Budget Mensuel et Dépenses",
        "reports": "Rapport Hebdomadaire Enseignant",
        "staff": "Personnel, Salaires & Comptes",
        "tasks": "Attribution des Tâches",
        "chat": "Communication et Demandes Parents",
        "change_pwd": "Changer le Mot de Passe",
        "active_students": "Élèves Actifs",
        "total_collected": "Total Frais Perçus (RWF)",
        "select_grade": "Choisissez d'abord la Classe",
        "save": "Enregistrer",
    },
    "Kiswahili": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Mfumo wa Usimamizi wa Shule, Nidhamu na Ripoti",
        "login_header": "Sehemu ya Kuingia",
        "select_role": "Chagua Nafasi Yako",
        "username": "Jina la Mtumiaji / Simu ya Mzazi",
        "password": "Nenosiri",
        "login_btn": "Ingia",
        "logout_btn": "Toka",
        "menu": "Menyu Kuu",
        "dashboard": "Dashibodi (Idara Zote)",
        "students": "Wanafunzi (Kwa Darasa)",
        "grades": "Alama na Maendeleo",
        "report_card": "Ripoti ya Mwanafunzi (PDF)",
        "attendance": "Mahudhurio ya Darasa",
        "conduct": "Nidhamu (Wanafunzi na Wafanyakazi)",
        "payments": "Malipo (Kila Siku, Wiki, Mwezi)",
        "finance": "Bajeti ya Mwezi na Matumizi",
        "reports": "Ripoti ya Wiki ya Mwalimu",
        "staff": "Wafanyakazi, Mishahara & Akaunti",
        "tasks": "Ugawaji wa Kazi",
        "chat": "Mawasiliano na Maombi ya Wazazi",
        "change_pwd": "Badilisha Nenosiri",
        "active_students": "Wanafunzi Wanaosoma (Active)",
        "total_collected": "Jumla ya Ada Zilizokusanywa (RWF)",
        "select_grade": "Chagua Darasa Kwanza",
        "save": "Hifadhi",
    }
}

# ==================== DATABASE SETUP & AUTO-MIGRATION ====================
def get_conn():
    return sqlite3.connect('igisubizo_academy.db', timeout=15, check_same_thread=False)

def ensure_column(cursor, table_name, column_name, column_def):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if column_name not in existing_cols:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        grade TEXT NOT NULL,
        parent_name TEXT,
        parent_phone TEXT,
        parent_email TEXT,
        status TEXT DEFAULT 'Active',
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        subject TEXT,
        assessment_type TEXT DEFAULT 'Exam',
        score REAL,
        max_score REAL DEFAULT 100,
        term TEXT,
        date TEXT,
        teacher TEXT,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')
    ensure_column(c, "grades", "assessment_type", "TEXT DEFAULT 'Exam'")
    ensure_column(c, "grades", "max_score", "REAL DEFAULT 100")

    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        teacher TEXT,
        notes TEXT,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        month_year TEXT,
        amount REAL DEFAULT 5000,
        paid_date TEXT,
        recorded_by TEXT,
        UNIQUE(student_id, month_year),
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS monthly_budgets (
        budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_year TEXT,
        category TEXT,
        allocated_amount REAL,
        spent_amount REAL DEFAULT 0,
        description TEXT,
        date TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS conduct (
        conduct_id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_type TEXT,
        person_name TEXT,
        grade_or_role TEXT,
        incident_type TEXT,
        points_change INTEGER,
        notes TEXT,
        date TEXT,
        recorded_by TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS teacher_reports (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_name TEXT,
        grade TEXT,
        week_ending TEXT,
        topics_covered TEXT,
        challenges TEXT,
        submitted_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS staff (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        role TEXT,
        username TEXT UNIQUE,
        password TEXT,
        phone TEXT,
        salary REAL,
        status TEXT DEFAULT 'Active'
    )''')
    # Migrate older staff schemas safely
    ensure_column(c, "staff", "full_name", "TEXT")
    ensure_column(c, "staff", "role", "TEXT")
    ensure_column(c, "staff", "username", "TEXT")
    ensure_column(c, "staff", "password", "TEXT")
    ensure_column(c, "staff", "phone", "TEXT")
    ensure_column(c, "staff", "salary", "REAL DEFAULT 50000")
    ensure_column(c, "staff", "status", "TEXT DEFAULT 'Active'")

    # If old schema had 'name' instead of 'full_name', copy it over
    c.execute("PRAGMA table_info(staff)")
    staff_cols = [row[1] for row in c.fetchall()]
    if "name" in staff_cols:

