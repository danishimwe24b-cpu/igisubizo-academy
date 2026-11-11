import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

# ==================== TRANSLATIONS (4 LANGUAGES) ====================
TRANSLATIONS = {
    "English": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "School Management, Finance & Communication System",
        "login_header": "System Login Portal",
        "select_role": "Select Portal Role",
        "username": "Username / Parent Phone",
        "password": "Password / PIN",
        "login_btn": "Login",
        "logout_btn": "Logout",
        "menu": "Navigation Menu",
        "dashboard": "Dashboard",
        "students": "Students (By Grade)",
        "grades": "Grades & Progress",
        "attendance": "Attendance",
        "payments": "Payments (Dec 2026 - Dec 2027)",
        "finance": "Monthly Budget & Expenses",
        "reports": "Teacher Weekly Reports",
        "staff": "Staff & Workers",
        "chat": "Communication & Parent Requests",
        "active_students": "Active Students",
        "total_collected": "Total Fees Collected (RWF)",
        "select_grade": "Select Grade Level First",
        "status": "Status",
        "save": "Save",
    },
    "Kinyarwanda": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Sisitemu y'Ishuri, Imari n'Itumanaho",
        "login_header": "Kwinjira muri Sisitemu",
        "select_role": "Hitamo Urwego",
        "username": "Izina / Telefoni y'Umubyeyi",
        "password": "Ijambo ry'ibanga",
        "login_btn": "Injira",
        "logout_btn": "Sohoka",
        "menu": "Ibice bya Sisitemu",
        "dashboard": "Incamake (Dashboard)",
        "students": "Abanyeshuri (Ku Ishuri)",
        "grades": "Amanota n'Iterambere",
        "attendance": "Kwitabira Ishuri",
        "payments": "Ubwishyu (Ukuboza 2026 - Ukuboza 2027)",
        "finance": "Ingengo y'Imari n'Ibyakoreshejwe",
        "reports": "Raporo y'Icyumweru y'Umwarimu",
        "staff": "Abakozi Bose b'Ikigo",
        "chat": "Itumanaho n'Impushya z'Ababyeyi",
        "active_students": "Abanyeshuri Biga (Active)",
        "total_collected": "Amafaranga Yose Yishyuwe (RWF)",
        "select_grade": "Banza Uhitemo Ishuri (Grade)",
        "status": "Imimerere",
        "save": "Bika Amakuru",
    },
    "French": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Système de Gestion Scolaire, Finance et Communication",
        "login_header": "Portail de Connexion",
        "select_role": "Choisir le Rôle",
        "username": "Nom d'utilisateur / Téléphone Parent",
        "password": "Mot de passe",
        "login_btn": "Se connecter",
        "logout_btn": "Déconnexion",
        "menu": "Menu Principal",
        "dashboard": "Tableau de Bord",
        "students": "Élèves (Par Classe)",
        "grades": "Notes et Progrès",
        "attendance": "Présences",
        "payments": "Paiements (Déc 2026 - Déc 2027)",
        "finance": "Budget Mensuel et Dépenses",
        "reports": "Rapport Hebdomadaire Enseignant",
        "staff": "Personnel et Employés",
        "chat": "Communication et Demandes Parents",
        "active_students": "Élèves Actifs",
        "total_collected": "Total Frais Perçus (RWF)",
        "select_grade": "Choisissez d'abord la Classe",
        "status": "Statut",
        "save": "Enregistrer",
    },
    "Kiswahili": {
        "title": "IGISUBIZO ACADEMY",
        "subtitle": "Mfumo wa Usimamizi wa Shule, Fedha na Mawasiliano",
        "login_header": "Sehemu ya Kuingia",
        "select_role": "Chagua Nafasi Yako",
        "username": "Jina la Mtumiaji / Simu ya Mzazi",
        "password": "Nenosiri",
        "login_btn": "Ingia",
        "logout_btn": "Toka",
        "menu": "Menyu Kuu",
        "dashboard": "Dashibodi",
        "students": "Wanafunzi (Kwa Darasa)",
        "grades": "Alama na Maendeleo",
        "attendance": "Mahudhurio",
        "payments": "Malipo (Des 2026 - Des 2027)",
        "finance": "Bajeti ya Mwezi na Matumizi",
        "reports": "Ripoti ya Wiki ya Mwalimu",
        "staff": "Wafanyakazi Wote",
        "chat": "Mawasiliano na Maombi ya Wazazi",
        "active_students": "Wanafunzi Wanaosoma (Active)",
        "total_collected": "Jumla ya Ada Zilizokusanywa (RWF)",
        "select_grade": "Chagua Darasa Kwanza",
        "status": "Hali",
        "save": "Hifadhi",
    }
}

# Payment months required: Dec 2026 through Dec 2027 (5,000 RWF each)
PAYMENT_MONTHS = [
    "2026-12", "2027-01", "2027-02", "2027-03", "2027-04", "2027-05",
    "2027-06", "2027-07", "2027-08", "2027-09", "2027-10", "2027-11", "2027-12"
]
MONTHLY_FEE = 5000

# ==================== DATABASE SETUP & MIGRATION ====================
def get_conn():
    return sqlite3.connect('igisubizo_academy.db')

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Students table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            parent_name TEXT,
            parent_phone TEXT,
            parent_email TEXT,
            status TEXT DEFAULT 'Active',
            created_at TEXT
        )
    ''')

    # Grades table (with assessment_type for Homework, Exercise, Quiz, Exam)
    c.execute('''
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
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')
    # Safely add assessment_type if upgrading from older DB
    try:
        c.execute("ALTER TABLE grades ADD COLUMN assessment_type TEXT DEFAULT 'Exam'")
    except sqlite3.OperationalError:
        pass

    # Attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT,
            teacher TEXT,
            notes TEXT,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')

    # Payments table (5000 RWF/month, Dec 2026 - Dec 2027)
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            month_year TEXT,
            amount REAL DEFAULT 5000,
            paid_date TEXT,
            recorded_by TEXT,
            UNIQUE(student_id, month_year),
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')

    # Monthly Budget table (manual entry)
    c.execute('''
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT UNIQUE,
            allocated_amount REAL,
            notes TEXT,
            updated_by TEXT
        )
    ''')

    # Monthly Expenses table
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT,
            category TEXT,
            description TEXT,
            amount REAL,
            date TEXT,
            recorded_by TEXT
        )
    ''')

    # Weekly Teacher Reports
    c.execute('''
        CREATE TABLE IF NOT EXISTS weekly_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_name TEXT,
            grade TEXT,
            week_ending TEXT,
            topics_covered TEXT,
            challenges TEXT,
            next_week_plan TEXT,
            submitted_at TEXT
        )
    ''')

    # Staff & Workers (Teachers, Cleaners, Safe Walkers, Security Guards)
    c.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            assigned_grade TEXT,
            monthly_salary REAL,
            status TEXT DEFAULT 'Active',
            hired_date TEXT
        )
    ''')

    # Communication & Parent Requests/Feedback
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_role TEXT,
            sender_name TEXT,
            parent_phone TEXT,
            student_name TEXT,
            msg_type TEXT,
            content TEXT,
            reply TEXT,
            created_at TEXT
        )
    ''')

    # System Users for Login Portals
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            full_name TEXT
        )
    ''')

    # Seed default staff logins if empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        default_users = [
            ("admin", "admin123", "Administration", "Head Administrator"),
            ("register", "reg123", "Register Officer", "School Registrar"),
            ("teacher", "teach123", "Teacher", "Class Teacher")
        ]
        c.executemany("INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)", default_users)

    conn.commit()
    conn.close()

init_db()

# ==================== SESSION STATE & LANGUAGE ====================
if "lang" not in st.session_state:
    st.session_state.lang = "English"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_name = None
    st.session_state.parent_phone = None
