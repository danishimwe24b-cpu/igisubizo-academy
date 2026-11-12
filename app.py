import os
import io
import sqlite3
import datetime
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

LOGO_PATH = "logo.png"
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
    return sqlite3.connect('igisubizo_academy.db')

def init_db():
    conn = get_conn()
    c = conn.cursor()

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
    try:
        c.execute("ALTER TABLE grades ADD COLUMN assessment_type TEXT DEFAULT 'Exam'")
    except sqlite3.OperationalError:
        pass

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

    c.execute('''
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT UNIQUE,
            allocated_amount REAL,
            notes TEXT,
            updated_by TEXT
        )
    ''')

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

    c.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            assigned_grade TEXT,
            assigned_subject TEXT,
            monthly_salary REAL,
            status TEXT DEFAULT 'Active',
            hired_date TEXT
        )
    ''')
    try:
        c.execute("ALTER TABLE staff ADD COLUMN assigned_subject TEXT")
    except sqlite3.OperationalError:
        pass

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

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            full_name TEXT,
            assigned_class TEXT,
            assigned_subject TEXT
        )
    ''')
    for col_name in ["assigned_class", "assigned_subject"]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} TEXT")
        except sqlite3.OperationalError:
            pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS password_requests (
            req_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            full_name TEXT,
            role TEXT,
            new_password TEXT,
            status TEXT DEFAULT 'Pending',
            requested_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS conduct_records (
            conduct_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_type TEXT,
            person_name TEXT,
            role_or_class TEXT,
            incident_type TEXT,
            points_change INTEGER,
            description TEXT,
            date TEXT,
            recorded_by TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            assigned_to TEXT,
            staff_role TEXT,
            task_title TEXT,
            task_details TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'Pending',
            assigned_by TEXT
        )
    ''')

    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone() == 0:
        default_users = [
            ("admin", "admin123", "Administration", "Head Administrator", "ALL", "ALL"),
            ("register", "reg123", "Register Officer", "School Registrar", "ALL", "ALL"),
            ("teacher", "teach123", "Teacher", "Default Teacher", "P1A", "Mathematics")
        ]
        c.executemany(
            "INSERT INTO users (username, password, role, full_name, assigned_class, assigned_subject) VALUES (?, ?, ?, ?, ?, ?)",
            default_users
        )

    conn.commit()
    conn.close()

init_db()

# ==================== PDF REPORT CARD GENERATOR WITH SCHOOL LOGO ====================
def generate_report_card_pdf(student_row, grades_df, conduct_score, term_label):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    if os.path.exists(LOGO_PATH):
        logo_img = RLImage(LOGO_PATH, width=95, height=85)
        header_tbl = Table([
            [logo_img, Paragraph("<b>IGISUBIZO ACADEMY</b><br/><font size=11>Excellence, Discipline &amp; Knowledge</font><br/><font size=10>Official Academic &amp; Conduct Report Card — " + term_label + "</font>", styles["Title"])]
        ], colWidths=[110, 380])
        header_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ]))
        elements.append(header_tbl)
    else:
        elements.append(Paragraph("<b>IGISUBIZO ACADEMY</b>", styles["Title"]))
        elements.append(Paragraph(f"Official Student Academic &amp; Conduct Report Card — {term_label}", styles["Heading3"]))

    elements.append(Spacer(1, 14))

    info_data = [
        ["Student Name:", student_row["student_name"], "Class Level:", student_row["grade"]],
        ["Parent / Guardian:", student_row["parent_name"] or "N/A", "Parent Phone:", student_row["parent_phone"] or "N/A"],
        ["Conduct Score:", f"{conduct_score} / 100", "Date Issued:", datetime.date.today().isoformat()]
    ]
    info_table = Table(info_data, colWidths=[115, 145, 110, 120])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    table_data = [["Subject", "Homework", "Exercise", "Quiz", "Exam", "Average (%)"]]
    total_avgs = []
    if not grades_df.empty:
        piv = grades_df.pivot_table(index="subject", columns="assessment_type", values="score", aggfunc="mean")
        for subj in piv.index:
            hw = piv.loc[subj, "Homework"] if "Homework" in piv.columns and pd.notna(piv.loc[subj, "Homework"]) else "-"
            ex = piv.loc[subj, "Exercise"] if "Exercise" in piv.columns and pd.notna(piv.loc[subj, "Exercise"]) else "-"
            qz = piv.loc[subj, "Quiz"] if "Quiz" in piv.columns and pd.notna(piv.loc[subj, "Quiz"]) else "-"
            xm = piv.loc[subj, "Exam"] if "Exam" in piv.columns and pd.notna(piv.loc[subj, "Exam"]) else "-"
            numeric_vals = [v for v in [hw, ex, qz, xm] if isinstance(v, (int, float))]
            avg_val = round(sum(numeric_vals) / len(numeric_vals), 1) if numeric_vals else 0.0
            total_avgs.append(avg_val)
            table_data.append([
                subj,
                f"{hw:.1f}" if isinstance(hw, float) else hw,
                f"{ex:.1f}" if isinstance(ex, float) else ex,
                f"{qz:.1f}" if isinstance(qz, float) else qz,
                f"{xm:.1f}" if isinstance(xm, float) else xm,
                f"{avg_val:.1f}%"
            ])

    overall_pct = round(sum(total_avgs) / len(total_avgs), 1) if total_avgs else 0.0
    table_data.append(["OVERALL AVERAGE", "", "", "", "", f"{overall_pct:.1f}%"])

    grade_table = Table(table_data, colWidths=[130, 70, 70, 70, 70, 80])
    grade_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B6E4F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(grade_table)
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Class Teacher Signature: ______________________    Head Administrator Stamp &amp; Signature: ______________________", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================== SESSION STATE & LANGUAGE ====================
for key, val in {
    "lang": "English",
    "logged_in": False,
    "role": None,
    "username": None,
    "user_name": None,
    "parent_phone": None,
    "assigned_class": "ALL",
    "assigned_subject": "ALL"
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

lang_col1, lang_col2 = st.columns([3, 1])
with lang_col2:
    selected_lang = st.selectbox(
        "🌐 Language / Ururimi",
        ["English", "Kinyarwanda", "French", "Kiswahili"],
        index=["English", "Kinyarwanda", "French", "Kiswahili"].index(st.session_state.lang)
    )
    st.session_state.lang = selected_lang

T = TRANSLATIONS[st.session_state.lang]

head_c1, head_c2 = st.columns([1, 5])
with head_c1:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=110)
with head_c2:
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #0B6E4F 0%, #0A3D62 100%); padding: 1.2rem; border-radius: 10px; color: white;">
        <h1 style="margin:0;">{T['title']}</h1>
        <p style="margin:0;">{T['subtitle']}</p>
    </div>
    """, unsafe_allow_html=True)

# ==================== LOGIN PORTAL ====================
if not st.session_state.logged_in:
    st.subheader(f"🔐 {T['login_header']}")
    col1, col2 = st.columns(2)
    with col1:
        portal_role = st.selectbox(
            T["select_role"],
            ["Administration", "Register Officer", "Teacher", "Parents"]
        )
        username_input = st.text_input(T["username"])
        password_input = st.text_input(T["password"], type="password")

        if st.button(T["login_btn"], type="primary"):
            conn = get_conn()
            if portal_role == "Parents":
                df_p = pd.read_sql_query(
                    "SELECT DISTINCT parent_name, parent_phone FROM students WHERE parent_phone = ? AND status = 'Active'",
                    conn, params=(username_input.strip(),)
                )
                if not df_p.empty and password_input in ["1234", username_input.strip()]:
                    st.session_state.logged_in = True
                    st.session_state.role = "Parents"
                    st.session_state.username = username_input.strip()
                    st.session_state.user_name = df_p.iloc[0]["parent_name"] or "Parent"
                    st.session_state.parent_phone = username_input.strip()
                    st.rerun()
                else:
                    st.error("Invalid Parent Phone or PIN (Default PIN is 1234).")
            else:
                df_u = pd.read_sql_query(
                    "SELECT * FROM users WHERE username = ? AND password = ? AND role = ?",
                    conn, params=(username_input.strip(), password_input.strip(), portal_role)
                )
                if not df_u.empty:
                    st.session_state.logged_in = True
                    st.session_state.role = portal_role
                    st.session_state.username = df_u.iloc[0]["username"]
                    st.session_state.user_name = df_u.iloc[0]["full_name"]
                    st.session_state.assigned_class = df_u.iloc[0]["assigned_class"] or "ALL"
                    st.session_state.assigned_subject = df_u.iloc[0]["assigned_subject"] or "ALL"
                    st.rerun()
                else:
                    st.error("Invalid credentials for selected role.")
            conn.close()

    with col2:
        st.info("""
        **Default Demo Logins:**
        * **Administration:** `admin` / `admin123`
        * **Register Officer:** `register` / `reg123`
        * **Teacher:** `teacher` / `teach123` *(or individual teacher login created by Admin)*
        * **Parents:** Registered *Parent Phone* & PIN `1234`
        """)
    st.stop()

# ==================== SIDEBAR NAVIGATION ====================
role = st.session_state.role
st.sidebar.success(f"👤 {st.session_state.user_name}\n\n**Role:** {role}")
if role == "Teacher":
    st.sidebar.info(f"🏫 Class: **{st.session_state.assigned_class}**\n\n📚 Subject: **{st.session_state.assigned_subject}**")

if st.sidebar.button(T["logout_btn"]):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()

if role == "Administration":
    menu_options = [
        T["dashboard"], T["students"], T["grades"], T["report_card"], T["attendance"],
        T["conduct"], T["payments"], T["finance"], T["reports"], T["staff"],
        T["tasks"], T["chat"], T["change_pwd"]
    ]
elif role == "Register Officer":
    menu_options = [
        T["dashboard"], T["students"], T["payments"], T["conduct"],
        T["tasks"], T["chat"], T["change_pwd"]
    ]
elif role == "Teacher":
    menu_options = [
        T["grades"], T["attendance"], T["conduct"], T["reports"],
        T["tasks"], T["chat"], T["change_pwd"]
    ]
else:
    menu_options = [
        T["chat"], T["grades"], T["report_card"], T["payments"]
    ]

menu = st.sidebar.radio(T["menu"], menu_options)

# ==================== 1. EXECUTIVE DASHBOARD (ALL DEPARTMENTS & PORTALS) ====================
if menu == T["dashboard"]:
    st.subheader(f"📊 {T['dashboard']}")
    conn = get_conn()
    active_students = pd.read_sql_query("SELECT * FROM students WHERE status='Active'", conn)
    payments_df = pd.read_sql_query(
        "SELECT p.*, s.student_name, s.grade FROM payments p JOIN students s ON p.student_id = s.student_id WHERE s.status = 'Active'",
        conn
    )
    expenses_df = pd.read_sql_query("SELECT * FROM expenses", conn)
    budgets_df = pd.read_sql_query("SELECT * FROM monthly_budgets", conn)
    staff_df = pd.read_sql_query("SELECT * FROM staff WHERE status='Active'", conn)
    tasks_df = pd.read_sql_query("SELECT * FROM tasks", conn)
    msgs_df = pd.read_sql_query("SELECT * FROM messages WHERE sender_role='Parent'", conn)
    att_today = pd.read_sql_query("SELECT * FROM attendance WHERE date = ?", conn, params=(datetime.date.today().isoformat(),))
    pwd_reqs = pd.read_sql_query("SELECT * FROM password_requests WHERE status='Pending'", conn)

    total_collected = payments_df["amount"].sum() if not payments_df.empty else 0
    total_expenses = expenses_df["amount"].sum() if not expenses_df.empty else 0
    total_budget = budgets_df["allocated_amount"].sum() if not budgets_df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T["active_students"], len(active_students))
    c2.metric(T["total_collected"], f"{total_collected:,.0f} RWF")
    c3.metric("Total Expenses / Budget", f"{total_expenses:,.0f} / {total_budget:,.0f} RWF")
    c4.metric("Active Staff & Workers", len(staff_df))

    if role == "Administration":
        st.divider()
        st.write("### 🏛️ All School Departments & Portals Overview")
        dept_c1, dept_c2, dept_c3, dept_c4 = st.columns(4)

        with dept_c1:
            st.info(f"""
            **🎓 Academics & Teacher Portal**
            * Active Classes: **{active_students['grade'].nunique() if not active_students.empty else 0}**
            * Today's Attendance Logs: **{len(att_today)}**
            * Pending Password Approvals: **{len(pwd_reqs)}**
            """)
        with dept_c2:
            st.success(f"""
            **💳 Register & Finance Portal**
            * Total Fees Paid: **{total_collected:,.0f} RWF**
            * Total Expenses: **{total_expenses:,.0f} RWF**
            * Net Balance: **{total_collected - total_expenses:,.0f} RWF**
            """)
        with dept_c3:
            cleaners = len(staff_df[staff_df["role"] == "Cleaner"]) if not staff_df.empty else 0
            walkers = len(staff_df[staff_df["role"] == "Safe Walker"]) if not staff_df.empty else 0
            guards = len(staff_df[staff_df["role"] == "Security Guard"]) if not staff_df.empty else 0
            teachers_cnt = len(staff_df[staff_df["role"] == "Teacher"]) if not staff_df.empty else 0
            st.warning(f"""
            **👷 Operations & Support Staff**
            * Teachers: **{teachers_cnt}** | Cleaners: **{cleaners}**
            * Safe Walkers: **{walkers}** | Security: **{guards}**
            * Monthly Payroll: **{staff_df['monthly_salary'].sum() if not staff_df.empty else 0:,.0f} RWF**
            """)
        with dept_c4:
            pending_tasks = len(tasks_df[tasks_df["status"] == "Pending"]) if not tasks_df.empty else 0
            unanswered_parents = len(msgs_df[msgs_df["reply"].isna() | (msgs_df["reply"] == "")]) if not msgs_df.empty else 0
            st.error(f"""
            **📩 Parent & Task Portal**
            * Parent Requests: **{len(msgs_df)}** ({unanswered_parents} unreplied)
            * Pending Staff Tasks: **{pending_tasks}**
            """)

    if not active_students.empty:
        st.write("### Active Students per Class Level")
        st.bar_chart(active_students["grade"].value_counts().reindex(CLASS_LEVELS).dropna())

        st.divider()
    conn = get_conn()

                 if role == "Parents":
        students_df = pd.read_sql_query(
            "SELECT student_id, student_name, grade FROM students WHERE parent_phone = ? AND status = 'Active'",
            conn, params=(st.session_state.parent_phone,)
        )
    elif role == "Teacher" and st.session_state.assigned_class not in [None, "", "ALL"]:
        selected_grade = st.session_state.assigned_class
        st.info(f"🔒 Confidential Teacher View — Assigned Class: **{selected_grade}** | Assigned Subject: **{st.session_state.assigned_subject}**")
        students_df = pd.read_sql_query(
            "SELECT student_id, student_name, grade FROM students WHERE grade = ? AND status = 'Active' ORDER BY student_name",
            conn, params=(selected_grade,)
        )
    else:
        selected_grade = st.selectbox(f"📌 {T['select_grade']}", CLASS_LEVELS)
        students_df = pd.read_sql_query(
            "SELECT student_id, student_name, grade FROM students WHERE grade = ? AND status = 'Active' ORDER BY student_name",
            conn, params=(selected_grade,)
        )

        )
