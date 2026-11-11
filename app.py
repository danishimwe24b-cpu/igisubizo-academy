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
            monthly_salary REAL,
            status TEXT DEFAULT 'Active',
            hired_date TEXT
        )
    ''')

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
            full_name TEXT
        )
    ''')

    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone() == 0:
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

lang_col1, lang_col2 = st.columns()
with lang_col2:
    selected_lang = st.selectbox(
        "🌐 Language / Ururimi",
        ["English", "Kinyarwanda", "French", "Kiswahili"],
        index=["English", "Kinyarwanda", "French", "Kiswahili"].index(st.session_state.lang)
    )
    st.session_state.lang = selected_lang

T = TRANSLATIONS[st.session_state.lang]

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0B6E4F 0%, #0A3D62 100%);
        padding: 1.2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(f"<div class='main-header'><h1>🎓 {T['title']}</h1><p>{T['subtitle']}</p></div>", unsafe_allow_html=True)

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
                    st.session_state.user_name = df_p.iloc["parent_name"] or "Parent"
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
                    st.session_state.user_name = df_u.iloc["full_name"]
                    st.rerun()
                else:
                    st.error("Invalid credentials for selected role.")
            conn.close()

    with col2:
        st.info("""
        **Demo Portal Logins:**
        * **Administration:** `admin` / `admin123`
        * **Register Officer:** `register` / `reg123`
        * **Teacher:** `teacher` / `teach123`
        * **Parents:** Enter registered *Parent Phone* & PIN `1234`
        """)
    st.stop()

# ==================== SIDEBAR NAVIGATION (ROLE-BASED) ====================
st.sidebar.success(f"👤 {st.session_state.user_name}\n\n**Role:** {st.session_state.role}")
if st.sidebar.button(T["logout_btn"]):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()

role = st.session_state.role

if role == "Administration":
    menu_options = [
        T["dashboard"], T["students"], T["grades"], T["attendance"],
        T["payments"], T["finance"], T["reports"], T["staff"], T["chat"]
    ]
elif role == "Register Officer":
    menu_options = [
        T["dashboard"], T["students"], T["payments"], T["chat"]
    ]
elif role == "Teacher":
    menu_options = [
        T["grades"], T["attendance"], T["reports"], T["chat"]
    ]
else:
    menu_options = [
        T["chat"], T["grades"], T["payments"]
    ]

menu = st.sidebar.radio(T["menu"], menu_options)

# ==================== 1. DASHBOARD ====================
if menu == T["dashboard"]:
    st.subheader(f"📊 {T['dashboard']}")
    conn = get_conn()
    active_students = pd.read_sql_query("SELECT * FROM students WHERE status='Active'", conn)
    payments_df = pd.read_sql_query("""
        SELECT p.*, s.status FROM payments p
        JOIN students s ON p.student_id = s.student_id
        WHERE s.status = 'Active'
    """, conn)
    expenses_df = pd.read_sql_query("SELECT * FROM expenses", conn)
    conn.close()

    total_collected = payments_df["amount"].sum() if not payments_df.empty else 0
    total_expenses = expenses_df["amount"].sum() if not expenses_df.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric(T["active_students"], len(active_students))
    c2.metric(T["total_collected"], f"{total_collected:,.0f} RWF")
    c3.metric("Total Recorded Expenses", f"{total_expenses:,.0f} RWF")

    if not active_students.empty:
        st.write("### Active Students per Grade")
        st.bar_chart(active_students["grade"].value_counts().sort_index())

# ==================== 2. STUDENTS ====================
elif menu == T["students"]:
    st.subheader(f"👥 {T['students']}")

    with st.expander("➕ Register New Student", expanded=False):
        with st.form("add_student", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Student Full Name *")
            grade = col2.selectbox("Grade *", ["P1", "P2", "P3", "P4", "P5", "P6"])
            parent_name = col1.text_input("Parent / Guardian Full Name *")
            parent_phone = col2.text_input("Parent Phone Number * (Used to link siblings & Parent Login)")
            parent_email = col1.text_input("Parent Email")
            status = col2.selectbox("Status", ["Active", "Inactive"])
            if st.form_submit_button(T["save"]):
                if name and grade and parent_phone:
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO students (student_name, grade, parent_name, parent_phone, parent_email, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (name.strip(), grade, parent_name.strip(), parent_phone.strip(), parent_email.strip(), status, datetime.date.today().isoformat()))
                    conn.commit()
                    conn.close()
                    st.success(f"Student {name} registered in {grade}!")
                else:
                    st.error("Student Name, Grade, and Parent Phone are required.")

    st.divider()
    selected_grade = st.selectbox(f"📌 {T['select_grade']}", ["P1", "P2", "P3", "P4", "P5", "P6"])
    show_inactive = st.checkbox("Include Inactive Students in View", value=False)

    conn = get_conn()
    if show_inactive:
        query = "SELECT * FROM students WHERE grade = ? ORDER BY student_name"
    else:
        query = "SELECT * FROM students WHERE grade = ? AND status = 'Active' ORDER BY student_name"
    grade_df = pd.read_sql_query(query, conn, params=(selected_grade,))
    conn.close()

    st.write(f"### Students in {selected_grade} ({len(grade_df)})")
    if not grade_df.empty:
        st.dataframe(grade_df[['student_id', 'student_name', 'grade', 'parent_name', 'parent_phone', 'status']], use_container_width=True)

        st.write("#### Update Student Status (Active / Inactive)")
        col_s1, col_s2, col_s3 = st.columns(3)
        target_student = col_s1.selectbox(
            "Select Student",
            grade_df['student_id'].astype(str) + " - " + grade_df['student_name'] + " (" + grade_df['status'] + ")"
        )
        new_status = col_s2.selectbox("New Status", ["Active", "Inactive"])
        if col_s3.button("Update Status"):
            sid = int(target_student.split(" - "))
            conn = get_conn()
            conn.execute("UPDATE students SET status = ? WHERE student_id = ?", (new_status, sid))
            conn.commit()
            conn.close()
            st.success("Status updated! Inactive students are excluded from counts and payments.")
            st.rerun()
    else:
        st.info(f"No students found in {selected_grade}.")
# ==================== 3. GRADES & INDIVIDUAL PROGRESS ====================
elif menu == T["grades"]:
    st.subheader(f"📝 {T['grades']}")
    conn = get_conn()

    if role == "Parents":
        students_df = pd.read_sql_query(
            "SELECT student_id, student_name, grade FROM students WHERE parent_phone = ? AND status = 'Active'",
            conn, params=(st.session_state.parent_phone,)
        )
    else:
        selected_grade = st.selectbox(f"📌 {T['select_grade']}", ["P1", "P2", "P3", "P4", "P5", "P6"])
        students_df = pd.read_sql_query(
            "SELECT student_id, student_name, grade FROM students WHERE grade = ? AND status = 'Active' ORDER BY student_name",
            conn, params=(selected_grade,)
        )

    if students_df.empty:
        st.warning("No active students found for this selection.")
        conn.close()
    else:
        tab1, tab2 = st.tabs(["📈 Individual Student Progress", "➕ Record Marks (Homework, Exercise, Quiz, Exam)"])

        with tab1:
            student_map = dict(zip(students_df['student_name'] + " (" + students_df['grade'] + ")", students_df['student_id']))
            chosen_label = st.selectbox("Select Student to View Progress", list(student_map.keys()))
            chosen_sid = student_map[chosen_label]

            prog_df = pd.read_sql_query("""
                SELECT subject, assessment_type, score, max_score, term, date, teacher
                FROM grades WHERE student_id = ? ORDER BY date ASC
            """, conn, params=(chosen_sid,))

            if prog_df.empty:
                st.info("No grades recorded yet for this student.")
            else:
                st.write(f"#### Subject Performance Breakdown: {chosen_label}")
                pivot_df = prog_df.pivot_table(
                    index="subject", columns="assessment_type", values="score", aggfunc="mean"
                ).round(1)
                st.dataframe(pivot_df, use_container_width=True)
                st.write("#### Progress Trend Chart")
                st.bar_chart(pivot_df)
                with st.expander("View Full Assessment History"):
                    st.dataframe(prog_df, use_container_width=True)

        with tab2:
            if role == "Parents":
                st.info("Parents have view-only access to grades.")
            else:
                student_map = dict(zip(students_df['student_name'] + " (" + students_df['grade'] + ")", students_df['student_id']))
                with st.form("enter_grade_form", clear_on_submit=True):
                    selected_st = st.selectbox("Student", list(student_map.keys()))
                    c1, c2, c3 = st.columns(3)
                    subject = c1.selectbox("Subject", ["English", "Kinyarwanda", "Mathematics", "SET", "SST", "French", "Kiswahili"])
                    assess_type = c2.selectbox("Assessment Type", ["Homework", "Exercise", "Quiz", "Exam"])
                    score = c3.number_input("Score (out of 100)", min_value=0.0, max_value=100.0, step=0.5)
                    c4, c5 = st.columns(2)
                    term = c4.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
                    date_val = c5.date_input("Date", datetime.date.today())

                    if st.form_submit_button(T["save"]):
                        c = conn.cursor()
                        c.execute('''
                            INSERT INTO grades (student_id, subject, assessment_type, score, max_score, term, date, teacher)
                            VALUES (?, ?, ?, ?, 100, ?, ?, ?)
                        ''', (student_map[selected_st], subject, assess_type, score, term, date_val.isoformat(), st.session_state.user_name))
                        conn.commit()
                        st.success(f"Saved {assess_type} score ({score}) for {selected_st} in {subject}.")
        conn.close()

# ==================== 4. ATTENDANCE ====================
elif menu == T["attendance"]:
    st.subheader(f"📅 {T['attendance']}")
    selected_grade = st.selectbox(f"📌 {T['select_grade']}", ["P1", "P2", "P3", "P4", "P5", "P6"])
    att_date = st.date_input("Date", datetime.date.today())

    conn = get_conn()
    grade_students = pd.read_sql_query(
        "SELECT student_id, student_name FROM students WHERE grade = ? AND status = 'Active' ORDER BY student_name",
        conn, params=(selected_grade,)
    )

    if grade_students.empty:
        st.warning(f"No active students in {selected_grade}.")
    else:
        with st.form("attendance_form"):
            records = []
            for _, row in grade_students.iterrows():
                c1, c2, c3 = st.columns(3)
                c1.write(f"**{row['student_name']}**")
                st_status = c2.selectbox("Status", ["Present", "Absent", "Late", "Excused"], key=f"att_{row['student_id']}")
                notes = c3.text_input("Notes", key=f"note_{row['student_id']}")
                records.append((row['student_id'], att_date.isoformat(), st_status, st.session_state.user_name, notes))

            if st.form_submit_button(T["save"]):
                c = conn.cursor()
                c.executemany('''
                    INSERT INTO attendance (student_id, date, status, teacher, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', records)
                conn.commit()
                st.success(f"Attendance saved for {selected_grade} on {att_date}!")
    conn.close()

# ==================== 5. PAYMENTS (5,000 RWF/MO DEC 2026 - DEC 2027) ====================
elif menu == T["payments"]:
    st.subheader(f"💳 {T['payments']}")
    st.caption("Monthly Tuition: **5,000 RWF** per Active student (December 2026 – December 2027). Inactive students are excluded.")
    conn = get_conn()

    if role == "Parents":
        matched_students = pd.read_sql_query(
            "SELECT * FROM students WHERE parent_phone = ? AND status = 'Active'",
            conn, params=(st.session_state.parent_phone,)
        )
    else:
        search_name = st.text_input("🔍 Type Student Name to Find Student & All Siblings with Same Parent:")
        if search_name.strip():
            parent_matches = pd.read_sql_query(
                "SELECT DISTINCT parent_phone, parent_name FROM students WHERE student_name LIKE ? AND status = 'Active'",
                conn, params=(f"%{search_name.strip()}%",)
            )
            if not parent_matches.empty:
                phones = tuple(parent_matches["parent_phone"].dropna().unique())
                if len(phones) == 1:
                    matched_students = pd.read_sql_query(
                        "SELECT * FROM students WHERE parent_phone = ? AND status = 'Active' ORDER BY grade, student_name",
                        conn, params=(phones,)
                    )
                else:
                    placeholders = ",".join("?" * len(phones))
                    matched_students = pd.read_sql_query(
                        f"SELECT * FROM students WHERE parent_phone IN ({placeholders}) AND status = 'Active' ORDER BY parent_phone, grade",
                        conn, params=phones
                    )
            else:
                matched_students = pd.DataFrame()
        else:
            matched_students = pd.DataFrame()

    if not matched_students.empty:
        parent_label = matched_students.iloc["parent_name"]
        parent_ph = matched_students.iloc["parent_phone"]
        st.success(f"👨‍👩‍👧‍👦 Family Group Found — Parent: **{parent_label}** ({parent_ph}) | Active Children: **{len(matched_students)}**")

        sids = tuple(matched_students["student_id"].tolist())
        placeholders = ",".join("?" * len(sids))
        existing_payments = pd.read_sql_query(
            f"SELECT student_id, month_year, amount FROM payments WHERE student_id IN ({placeholders})",
            conn, params=sids
        )

        matrix_rows = []
        for _, st_row in matched_students.iterrows():
            row_dict = {"Student": f"{st_row['student_name']} ({st_row['grade']})"}
            st_pays = existing_payments[existing_payments["student_id"] == st_row["student_id"]]["month_year"].tolist()
            for m in PAYMENT_MONTHS:
                row_dict[m] = "✅ 5,000" if m in st_pays else "❌ Unpaid"
            matrix_rows.append(row_dict)

        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True)

        if role in ["Administration", "Register Officer"]:
            st.write("#### Record Monthly Payment (5,000 RWF)")
            with st.form("record_payment_form"):
                c1, c2, c3 = st.columns(3)
                sib_map = dict(zip(matched_students["student_name"] + " (" + matched_students["grade"] + ")", matched_students["student_id"]))
                pay_student = c1.selectbox("Select Child", list(sib_map.keys()))
                pay_month = c2.selectbox("Select Month", PAYMENT_MONTHS)
                pay_date = c3.date_input("Payment Date", datetime.date.today())

                if st.form_submit_button("Confirm 5,000 RWF Payment"):
                    try:
                        c = conn.cursor()
                        c.execute('''
                            INSERT INTO payments (student_id, month_year, amount, paid_date, recorded_by)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (sib_map[pay_student], pay_month, MONTHLY_FEE, pay_date.isoformat(), st.session_state.user_name))
                        conn.commit()
                        st.success(f"Recorded 5,000 RWF for {pay_student} ({pay_month}).")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.warning("This month is already marked as paid for this student.")

    if role in ["Administration", "Register Officer"]:
        st.divider()
        st.write("### 📊 Payment Revenue Reports (Active Students Only)")
        all_active_pays = pd.read_sql_query("""
