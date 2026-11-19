import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import os
import secrets
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ====================== CONFIG ======================
CLASS_LEVELS = ["P1A", "P1B", "P2A", "P2B", "P3A", "P3B", "P4A", "P4B", "P5", "P6"]
SUBJECT_LIST = ["English", "Kinyarwanda", "Mathematics", "SET", "SST", "French", "Kiswahili"]
ASSESSMENT_TYPES = ["Homework", "Exercise", "Quiz", "Exam", "Midterm"]

PAYMENT_MONTHS = []
for year in [2026, 2027, 2028, 2029, 2030]:
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

# ====================== SECURITY HELPERS ======================
def hash_pwd(pwd: str) -> str:
    return hashlib.sha256(pwd.strip().encode("utf-8")).hexdigest()

def verify_pwd(raw_pwd: str, stored_pwd: str) -> bool:
    if not stored_pwd:
        return False
    return stored_pwd == raw_pwd.strip() or stored_pwd == hash_pwd(raw_pwd)

# ====================== DATABASE ======================
DB_PATH = os.environ.get("IGISUBIZO_DB_PATH", "igisubizo_academy.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
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
    for col, col_def in [
        ("gender", "TEXT DEFAULT 'Male'"),
        ("parent_name", "TEXT"),
        ("parent_phone", "TEXT"),
        ("parent_email", "TEXT"),
        ("status", "TEXT DEFAULT 'Active'"),
        ("is_deleted", "INTEGER DEFAULT 0"),
        ("created_at", "TEXT")
    ]:
        ensure_column(c, "students", col, col_def)

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
    for col, col_def in [
        ("assessment_type", "TEXT DEFAULT 'Exam'"),
        ("max_score", "REAL DEFAULT 100"),
        ("term", "TEXT"),
        ("date", "TEXT"),
        ("teacher", "TEXT"),
        ("is_deleted", "INTEGER DEFAULT 0")
    ]:
        ensure_column(c, "grades", col, col_def)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT,
            teacher TEXT,
            notes TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    ensure_column(c, "attendance", "is_deleted", "INTEGER DEFAULT 0")

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
            is_deleted INTEGER DEFAULT 0,
            UNIQUE(student_id, month_year)
        )
    """)
    for col, col_def in [
        ("amount", "REAL DEFAULT 5000"),
        ("status", "TEXT DEFAULT 'Not paid'"),
        ("paid_date", "TEXT"),
        ("recorded_by", "TEXT"),
        ("notes", "TEXT"),
        ("is_deleted", "INTEGER DEFAULT 0")
    ]:
        ensure_column(c, "payments", col, col_def)

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
            status TEXT DEFAULT 'Active',
            is_deleted INTEGER DEFAULT 0
        )
    """)
    for col, col_def in [
        ("full_name", "TEXT"),
        ("role", "TEXT"),
        ("username", "TEXT"),
        ("password", "TEXT"),
        ("phone", "TEXT"),
        ("assigned_classes", "TEXT DEFAULT 'ALL'"),
        ("assigned_subjects", "TEXT DEFAULT 'ALL'"),
        ("status", "TEXT DEFAULT 'Active'"),
        ("is_deleted", "INTEGER DEFAULT 0")
    ]:
        ensure_column(c, "staff", col, col_def)

    c.execute("""
        CREATE TABLE IF NOT EXISTS staff_invites (
            invite_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invite_code TEXT UNIQUE,
            full_name TEXT,
            role TEXT DEFAULT 'Teacher',
            phone TEXT,
            assigned_classes TEXT,
            assigned_subjects TEXT,
            created_by TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS student_advisories (
            advisory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_username TEXT,
            teacher_name TEXT,
            student_id INTEGER,
            assigned_by TEXT,
            assigned_at TEXT,
            status TEXT DEFAULT 'Active',
            UNIQUE(teacher_username, student_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS advisory_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_username TEXT,
            teacher_name TEXT,
            student_id INTEGER,
            week_ending TEXT,
            wellbeing_status TEXT,
            summary TEXT,
            action_plan TEXT,
            submitted_at TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conduct (
            conduct_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_type TEXT,
            person_name TEXT,
            grade_or_role TEXT,
            incident_type TEXT,
            points_change INTEGER,
            notes TEXT,
            date TEXT,
            recorded_by TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    ensure_column(c, "conduct", "is_deleted", "INTEGER DEFAULT 0")

    c.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            perm_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            request_type TEXT,
            reason TEXT,
            start_date TEXT,
            end_date TEXT,
            emergency_contact TEXT,
            status TEXT DEFAULT 'Approved',
            recorded_by TEXT,
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
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
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    ensure_column(c, "messages", "is_deleted", "INTEGER DEFAULT 0")

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            created_by TEXT,
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    ensure_column(c, "notifications", "is_deleted", "INTEGER DEFAULT 0")

    c.execute("""
        CREATE TABLE IF NOT EXISTS removed_records (
            archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_table TEXT,
            record_id INTEGER,
            summary TEXT,
            removed_by TEXT,
            removed_at TEXT
        )
    """)

    c.execute("SELECT COUNT(*) FROM staff WHERE LOWER(username)='admin'")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status, is_deleted)
            VALUES ('Head Administrator', 'Administration', 'admin', ?, '0780000000', 'ALL', 'ALL', 'Active', 0)
        """, (hash_pwd("admin123"),))

    conn.commit()
    conn.close()

init_db()

# ====================== PAGE SETUP ======================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0B6E4F 0%, #0A3D62 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .stButton>button {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ====================== SESSION ======================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.session_state.username = ""
    st.session_state.assigned_classes = "ALL"
    st.session_state.assigned_subjects = "ALL"

# ====================== LOGIN & TEACHER INVITE REGISTRATION ======================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=160)
        st.markdown("<div class='main-header'><h2 style='margin:0;'>IGISUBIZO ACADEMY</h2><p style='margin:4px 0 0 0;'>School Management, Advisory & Finance System</p></div>", unsafe_allow_html=True)

        tab_login, tab_invite = st.tabs(["🔐 Staff Login", "🎟️ Teacher Registration (Invite Code)"])

        with tab_login:
            st.info("Default Admin: username `admin` / password `admin123`")
            with st.form("login_form"):
                role = st.selectbox("Select Role", ["Administration", "Teacher", "Register Officer"])
                uname = st.text_input("Username").strip()
                pwd = st.text_input("Password", type="password").strip()
                if st.form_submit_button("Login", use_container_width=True):
                    conn = get_conn()
                    df = pd.read_sql_query(
                        "SELECT * FROM staff WHERE LOWER(TRIM(username))=? AND TRIM(role)=? AND status='Active' AND COALESCE(is_deleted,0)=0",
                        conn, params=(uname.lower(), role)
                    )
                    conn.close()
                    if not df.empty and verify_pwd(pwd, df.iloc[0]["password"]):
                        rec = df.iloc[0]
                        st.session_state.logged_in = True
                        st.session_state.user_name = rec["full_name"]
                        st.session_state.user_role = rec["role"]
                        st.session_state.username = rec["username"]
                        st.session_state.assigned_classes = rec["assigned_classes"] or "ALL"
                        st.session_state.assigned_subjects = rec["assigned_subjects"] or "ALL"
                        st.rerun()
                    else:
                        st.error("Invalid credentials, inactive account, or wrong role selected.")

        with tab_invite:
            st.caption("Invited teachers: enter the Invitation Code sent by the Administrator to set your own username and password.")
            with st.form("teacher_invite_register"):
                inv_code = st.text_input("Invitation Code *").strip().upper()
                new_uname = st.text_input("Choose Your Username *").strip()
                new_pwd = st.text_input("Create Your Password *", type="password").strip()
                confirm_pwd = st.text_input("Confirm Password *", type="password").strip()
                if st.form_submit_button("Complete Registration", use_container_width=True):
                    if not inv_code or not new_uname or not new_pwd:
                        st.error("Please fill in all required fields.")
                    elif new_pwd != confirm_pwd:
                        st.error("Passwords do not match.")
                    elif len(new_pwd) < 4:
                        st.error("Password must be at least 4 characters.")
                    else:
                        conn = get_conn()
                        cur = conn.cursor()
                        inv_df = pd.read_sql_query(
                            "SELECT * FROM staff_invites WHERE UPPER(TRIM(invite_code))=? AND status='Pending'",
                            conn, params=(inv_code,)
                        )
                        existing_user = pd.read_sql_query(
                            "SELECT staff_id FROM staff WHERE LOWER(TRIM(username))=?",
                            conn, params=(new_uname.lower(),)
                        )
                        if inv_df.empty:
                            st.error("Invalid or already used Invitation Code.")
                        elif not existing_user.empty:
                            st.error("That username is already taken. Please choose another one.")
                        else:
                            inv = inv_df.iloc[0]
                            cur.execute("""
                                INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status, is_deleted)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', 0)
                            """, (
                                inv["full_name"],
                                inv["role"] or "Teacher",
                                new_uname,
                                hash_pwd(new_pwd),
                                inv["phone"] or "",
                                inv["assigned_classes"] or "NONE",
                                inv["assigned_subjects"] or "NONE"
                            ))
                            cur.execute("UPDATE staff_invites SET status='Accepted' WHERE invite_id=?", (int(inv["invite_id"]),))
                            conn.commit()
                            st.success(f"Welcome {inv['full_name']}! Your account is active. You can now log in under the Staff Login tab.")
                        conn.close()
    st.stop()

# ====================== HELPERS ======================
def allowed_classes():
    if st.session_state.user_role != "Teacher" or st.session_state.assigned_classes == "ALL":
        return CLASS_LEVELS
    raw = [c.strip() for c in str(st.session_state.assigned_classes).split(",") if c.strip()]
    return [c for c in CLASS_LEVELS if c in raw]

def allowed_subjects():
    if st.session_state.user_role != "Teacher" or st.session_state.assigned_subjects == "ALL":
        return SUBJECT_LIST
    raw = [s.strip() for s in str(st.session_state.assigned_subjects).split(",") if s.strip()]
    return [s for s in SUBJECT_LIST if s in raw]

def archive_record(conn, table_name, id_col, record_id, summary_text):
    conn.execute(f"UPDATE {table_name} SET is_deleted = 1 WHERE {id_col} = ?", (int(record_id),))
    conn.execute(
        "INSERT INTO removed_records (source_table, record_id, summary, removed_by, removed_at) VALUES (?, ?, ?, ?, ?)",
        (table_name, int(record_id), summary_text, st.session_state.user_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()

def build_report_pdf(student_row, grades_df, term):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("SchoolTitle", parent=styles["Title"], textColor=colors.HexColor("#0B6E4F"), alignment=TA_CENTER)
    sub_style = ParagraphStyle("SubTitle", parent=styles["Heading2"], textColor=colors.HexColor("#0A3D62"), alignment=TA_CENTER)

    elements = [
        Paragraph("<b>IGISUBIZO ACADEMY</b>", title_style),
        Paragraph(f"Official Student Academic Report — {term}", sub_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B6E4F")),
        Spacer(1, 10),
        Paragraph(
            f"<b>Student Name:</b> {student_row['student_name']} &nbsp;&nbsp;&nbsp; "
            f"<b>Class:</b> {student_row['grade']}<br/>"
            f"<b>Parent / Guardian:</b> {student_row.get('parent_name') or '-'} ({student_row.get('parent_phone') or '-'})<br/>"
            f"<b>Status:</b> {student_row.get('status', 'Active')} &nbsp;&nbsp;&nbsp; "
            f"<b>Issued Date:</b> {datetime.date.today()}",
            styles["Normal"]
        ),
        Spacer(1, 14)
    ]

    table_data = [["Subject", "Assessment", "Score", "Max", "Percentage"]]
    tot_s, tot_m = 0.0, 0.0
    for _, r in grades_df.iterrows():
        sc = float(r["score"] or 0)
        mx = float(r["max_score"] or 100)
        pct = (sc / mx * 100) if mx > 0 else 0
        table_data.append([r["subject"], r["assessment_type"], f"{sc:.1f}", f"{mx:.1f}", f"{pct:.1f}%"])
        tot_s += sc
        tot_m += mx

    overall = (tot_s / tot_m * 100) if tot_m > 0 else 0
    table_data.append(["TOTAL / OVERALL", "-", f"{tot_s:.1f}", f"{tot_m:.1f}", f"{overall:.1f}%"])

    tbl = Table(table_data, colWidths=[4.5*cm, 3.8*cm, 2.5*cm, 2.5*cm, 3.2*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B6E4F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.75, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F5E9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Class Teacher Signature: ______________________ &nbsp;&nbsp;&nbsp; Head Administrator Signature: ______________________", styles["Normal"]))
    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()

# ====================== SIDEBAR ======================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=110)
    st.success(f"👤 **{st.session_state.user_name}**

Role: **{st.session_state.user_role}**")
    if st.session_state.user_role == "Teacher":
        st.caption(f"Classes: {st.session_state.assigned_classes}")
        st.caption(f"Subjects: {st.session_state.assigned_subjects}")

    if st.button("Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()

    if st.session_state.user_role == "Administration":
        menu = st.radio("Navigation", [
            "Dashboard", "Students", "Staff & Teachers", "Student Advisory",
            "Grades", "Attendance", "Payments", "Report Cards",
            "Code of Conduct", "Permission & Emergency", "Notifications",
            "Messages", "Removed Records"
        ])
    elif st.session_state.user_role == "Teacher":
        menu = st.radio("Navigation", [
            "Student Advisory", "Grades", "Attendance", "Report Cards",
            "Code of Conduct", "Permission & Emergency", "Notifications", "Messages"
        ])
    else:
        menu = st.radio("Navigation", [
            "Students", "Report Cards", "Code of Conduct",
            "Permission & Emergency", "Notifications", "Messages"
        ])

conn = get_conn()

# ====================== 1. DASHBOARD ======================
if menu == "Dashboard":
    st.markdown("<div class='main-header'><h2 style='margin:0;'>📊 Administration Dashboard</h2></div>", unsafe_allow_html=True)

    active_students = pd.read_sql_query("SELECT * FROM students WHERE status='Active' AND COALESCE(is_deleted,0)=0", conn)
    inactive_students = pd.read_sql_query("SELECT * FROM students WHERE status='Inactive' AND COALESCE(is_deleted,0)=0", conn)
    total_paid_df = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE COALESCE(is_deleted,0)=0 AND status IN ('Paid', 'Late 5 days', 'Late 5-10 days', 'Late 15 days')", conn)
    active_staff = pd.read_sql_query("SELECT * FROM staff WHERE status='Active' AND COALESCE(is_deleted,0)=0", conn)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Students", len(active_students))
    c2.metric("Inactive Students", len(inactive_students))
    c3.metric("Total Fees Collected", f"{float(total_paid_df.iloc[0]['total']):,.0f} RWF")
    c4.metric("Active Staff", len(active_staff))

    st.divider()
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Active Students by Class Level")
        if not active_students.empty:
            counts = active_students["grade"].value_counts().reindex(CLASS_LEVELS, fill_value=0)
            st.bar_chart(counts)
        else:
            st.info("No active students registered yet.")
    with col_right:
        st.subheader("Recent Payment Records")
        recent_pay = pd.read_sql_query("""
            SELECT s.student_name AS Student, s.grade AS Class, p.month_year AS Month,
                   p.status AS Status, p.amount AS Amount, p.paid_date AS Date
            FROM payments p
            JOIN students s ON p.student_id = s.student_id
            WHERE COALESCE(p.is_deleted,0)=0
            ORDER BY p.payment_id DESC LIMIT 10
        """, conn)
        if not recent_pay.empty:
            st.dataframe(recent_pay, use_container_width=True)
        else:
            st.info("No payment records found yet.")

# ====================== 2. STUDENTS ======================
elif menu == "Students":
    st.subheader("👥 Students Management")
    t_active, t_inactive, t_add, t_status = st.tabs([
        "✅ Active Students",
        "⏸️ Inactive Students",
        "➕ Add Student",
        "🔄 Update Student Status"
    ])

    with t_active:
        cls_filter = st.selectbox("Filter by Class Level", ["All"] + CLASS_LEVELS, key="act_cls_filter")
        if cls_filter == "All":
            df_act = pd.read_sql_query("SELECT student_id, student_name, grade, gender, parent_name, parent_phone, status, created_at FROM students WHERE status='Active' AND COALESCE(is_deleted,0)=0 ORDER BY grade, student_name", conn)
        else:
            df_act = pd.read_sql_query("SELECT student_id, student_name, grade, gender, parent_name, parent_phone, status, created_at FROM students WHERE status='Active' AND grade=? AND COALESCE(is_deleted,0)=0 ORDER BY student_name", conn, params=(cls_filter,))
        st.dataframe(df_act, use_container_width=True)

    with t_inactive:
        df_inact = pd.read_sql_query("SELECT student_id, student_name, grade, gender, parent_name, parent_phone, status, created_at FROM students WHERE status='Inactive' AND COALESCE(is_deleted,0)=0 ORDER BY grade, student_name", conn)
        st.dataframe(df_inact, use_container_width=True)

    with t_add:
        with st.form("add_student_form"):
            c1, c2, c3 = st.columns(3)
            s_name = c1.text_input("Student Full Name *").strip()
            s_grade = c2.selectbox("Class Level *", CLASS_LEVELS)
            s_gender = c3.selectbox("Gender", ["Male", "Female"])
            c4, c5, c6 = st.columns(3)
            p_name = c4.text_input("Parent / Guardian Name").strip()
            p_phone = c5.text_input("Parent Phone").strip()
            p_email = c6.text_input("Parent Email (Optional)").strip()
            if st.form_submit_button("Register Student", use_container_width=True):
                if not s_name:
                    st.error("Student Full Name is required.")
                else:
                    conn.execute("""
                        INSERT INTO students (student_name, grade, gender, parent_name, parent_phone, parent_email, status, is_deleted, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'Active', 0, ?)
                    """, (s_name, s_grade, s_gender, p_name, p_phone, p_email, str(datetime.date.today())))
                    conn.commit()
                    st.success(f"Student '{s_name}' registered in {s_grade}!")
                    st.rerun()

    with t_status:
        if st.session_state.user_role != "Administration":
            st.warning("Only the Administrator can update student Active/Inactive status.")
        else:
            all_st = pd.read_sql_query("SELECT student_id, student_name, grade, status FROM students WHERE COALESCE(is_deleted,0)=0 ORDER BY grade, student_name", conn)
            if all_st.empty:
                st.info("No students found.")
            else:
                st_map = {f"{r['student_name']} ({r['grade']}) — Current: {r['status']}": r["student_id"] for _, r in all_st.iterrows()}
                with st.form("update_student_status_form"):
                    sel_st_label = st.selectbox("Select Student", list(st_map.keys()))
                    new_st_status = st.selectbox("New Status", ["Active", "Inactive"])
                    if st.form_submit_button("Save Status Update", use_container_width=True):
                        sid = int(st_map[sel_st_label])
                        conn.execute("UPDATE students SET status=? WHERE student_id=?", (new_st_status, sid))
                        conn.commit()
                        st.success(f"Student status updated to **{new_st_status}**!")
                        st.rerun()

# ====================== 3. STAFF & TEACHERS (ADMIN ONLY) ======================
elif menu == "Staff & Teachers":
    if st.session_state.user_role != "Administration":
        st.error("Access restricted to Administration.")
        st.stop()

    st.subheader("👩‍🏫 Staff & Teacher Invitations")
    t_inv, t_direct, t_perms = st.tabs([
        "🎟️ Send Teacher Invitation",
        "➕ Direct Staff Account",
        "🛠️ Manage Assignments & Status"
    ])

    with t_inv:
        st.info("Generate an Invitation Code for a teacher with their assigned classes and subjects. The teacher will use this code on the login screen to create their own username and password.")
        with st.form("create_invite_form"):
            c1, c2, c3 = st.columns(3)
            t_name = c1.text_input("Teacher Full Name *").strip()
            t_role = c2.selectbox("Role", ["Teacher", "Register Officer"])
            t_phone = c3.text_input("Phone Number").strip()

            c4, c5 = st.columns(2)
            inv_classes = c4.multiselect("Assigned Classes *", CLASS_LEVELS)
            inv_subjects = c5.multiselect("Assigned Subjects *", SUBJECT_LIST)

            if st.form_submit_button("Generate Invitation Code", use_container_width=True):
                if not t_name:
                    st.error("Teacher Full Name is required.")
                elif t_role == "Teacher" and (not inv_classes or not inv_subjects):
                    st.error("Please select at least one Class and one Subject for the teacher.")
                else:
                    code = "IGS-" + secrets.token_hex(3).upper()
                    cls_str = ",".join(inv_classes) if t_role == "Teacher" else "ALL"
                    sub_str = ",".join(inv_subjects) if t_role == "Teacher" else "ALL"
                    conn.execute("""
                        INSERT INTO staff_invites (invite_code, full_name, role, phone, assigned_classes, assigned_subjects, created_by, created_at, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
                    """, (code, t_name, t_role, t_phone, cls_str, sub_str, st.session_state.user_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success(f"Invitation created for **{t_name}**! Share this Invitation Code: **`{code}`**")

        st.markdown("#### Sent Invitations")
        invites_df = pd.read_sql_query("SELECT invite_code, full_name, role, phone, assigned_classes, assigned_subjects, status, created_at FROM staff_invites ORDER BY invite_id DESC", conn)
        st.dataframe(invites_df, use_container_width=True)

    with t_direct:
        with st.form("direct_staff_form"):
            c1, c2, c3 = st.columns(3)
            d_name = c1.text_input("Full Name *").strip()
            d_role = c2.selectbox("Role", ["Administration", "Teacher", "Register Officer"])
            d_phone = c3.text_input("Phone").strip()
            c4, c5 = st.columns(2)
            d_uname = c4.text_input("Username *").strip()
            d_pwd = c5.text_input("Initial Password *", value="123456").strip()
            c6, c7 = st.columns(2)
            d_cls = c6.multiselect("Assigned Classes (Teachers)", CLASS_LEVELS)
            d_sub = c7.multiselect("Assigned Subjects (Teachers)", SUBJECT_LIST)
            if st.form_submit_button("Create Account"):
                if not d_name or not d_uname or not d_pwd:
                    st.error("Name, username, and password are required.")
                else:
                    try:
                        c_str = ",".join(d_cls) if (d_role == "Teacher" and d_cls) else ("NONE" if d_role == "Teacher" else "ALL")
                        s_str = ",".join(d_sub) if (d_role == "Teacher" and d_sub) else ("NONE" if d_role == "Teacher" else "ALL")
                        conn.execute("""
                            INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status, is_deleted)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', 0)
                        """, (d_name, d_role, d_uname, hash_pwd(d_pwd), d_phone, c_str, s_str))
                        conn.commit()
                        st.success(f"Account created for {d_name} (`{d_uname}`).")
                    except sqlite3.IntegrityError:
                        st.error("Username already exists.")

    with t_perms:
        staff_df = pd.read_sql_query("SELECT staff_id, full_name, role, username, phone, assigned_classes, assigned_subjects, status FROM staff WHERE COALESCE(is_deleted,0)=0", conn)
        st.dataframe(staff_df, use_container_width=True)
        if not staff_df.empty:
            with st.form("edit_staff_perms"):
                u_list = staff_df["username"].tolist()
                sel_u = st.selectbox("Select Staff Username", u_list)
                c1, c2 = st.columns(2)
                upd_cls = c1.multiselect("Update Assigned Classes", CLASS_LEVELS)
                upd_sub = c2.multiselect("Update Assigned Subjects", SUBJECT_LIST)
                c3, c4 = st.columns(2)
                upd_status = c3.selectbox("Account Status", ["Active", "Inactive"])
                reset_pwd = c4.text_input("Reset Password (leave blank to keep current)", type="password").strip()
                if st.form_submit_button("Save Changes"):
                    row_role = staff_df[staff_df["username"] == sel_u].iloc[0]["role"]
                    c_str = ",".join(upd_cls) if upd_cls else ("ALL" if row_role != "Teacher" else "NONE")
                    s_str = ",".join(upd_sub) if upd_sub else ("ALL" if row_role != "Teacher" else "NONE")
                    if reset_pwd:
                        conn.execute("UPDATE staff SET assigned_classes=?, assigned_subjects=?, status=?, password=? WHERE username=?", (c_str, s_str, upd_status, hash_pwd(reset_pwd), sel_u))
                    else:
                        conn.execute("UPDATE staff SET assigned_classes=?, assigned_subjects=?, status=? WHERE username=?", (c_str, s_str, upd_status, sel_u))
                    conn.commit()
                    st.success(f"Updated settings for `{sel_u}`!")
                    st.rerun()

# ====================== 4. STUDENT ADVISORY & WEEKLY REPORTS ======================
elif menu == "Student Advisory":
    st.subheader("🧭 Student Advisory & Weekly Reports")

    if st.session_state.user_role == "Administration":
        tab_assign, tab_reports = st.tabs(["📌 Assign Students to Teachers", "📋 All Weekly Advisory Reports"])

        with tab_assign:
            teachers = pd.read_sql_query("SELECT username, full_name FROM staff WHERE role='Teacher' AND status='Active' AND COALESCE(is_deleted,0)=0 ORDER BY full_name", conn)
            students = pd.read_sql_query("SELECT student_id, student_name, grade FROM students WHERE status='Active' AND COALESCE(is_deleted,0)=0 ORDER BY grade, student_name", conn)

            if teachers.empty or students.empty:
                st.info("Ensure there is at least one Active Teacher and one Active Student before assigning advisories.")
            else:
                with st.form("assign_advisory_form"):
                    t_map = {f"{r['full_name']} ({r['username']})": (r["username"], r["full_name"]) for _, r in teachers.iterrows()}
                    s_map = {f"{r['student_name']} — {r['grade']}": int(r["student_id"]) for _, r in students.iterrows()}

                    sel_t = st.selectbox("Select Advisor (Teacher)", list(t_map.keys()))
                    sel_students = st.multiselect("Select Students from Any Class Level", list(s_map.keys()))

                    if st.form_submit_button("Assign Advisory Students", use_container_width=True):
                        if not sel_students:
                            st.error("Select at least one student.")
                        else:
                            t_uname, t_fname = t_map[sel_t]
                            for label in sel_students:
                                sid = s_map[label]
                                conn.execute("""
                                    INSERT INTO student_advisories (teacher_username, teacher_name, student_id, assigned_by, assigned_at, status)
                                    VALUES (?, ?, ?, ?, ?, 'Active')
                                    ON CONFLICT(teacher_username, student_id) DO UPDATE SET status='Active', assigned_at=excluded.assigned_at
                                """, (t_uname, t_fname, sid, st.session_state.user_name, str(datetime.date.today())))
                            conn.commit()
                            st.success(f"Assigned {len(sel_students)} student(s) to {t_fname}!")
                            st.rerun()

            st.markdown("#### Current Advisory Assignments")
            adv_df = pd.read_sql_query("""
                SELECT a.advisory_id, a.teacher_name AS Advisor, s.student_name AS Student, s.grade AS Class, a.assigned_at AS Assigned_Date
                FROM student_advisories a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.status='Active' AND COALESCE(s.is_deleted,0)=0
                ORDER BY a.teacher_name, s.grade, s.student_name
            """, conn)
            st.dataframe(adv_df, use_container_width=True)

        with tab_reports:
            rep_df = pd.read_sql_query("""
                SELECT r.report_id, r.week_ending AS Week_Ending, r.teacher_name AS Advisor,
                       s.student_name AS Student, s.grade AS Class, r.wellbeing_status AS Wellbeing,
                       r.summary AS Weekly_Summary, r.action_plan AS Action_Plan, r.submitted_at AS Submitted
                FROM advisory_reports r
                JOIN students s ON r.student_id = s.student_id
                WHERE COALESCE(r.is_deleted,0)=0
                ORDER BY r.report_id DESC
            """, conn)
            st.dataframe(rep_df, use_container_width=True)

    else:
        my_advisees = pd.read_sql_query("""
            SELECT s.student_id, s.student_name, s.grade, s.parent_name, s.parent_phone
            FROM student_advisories a
            JOIN students s ON a.student_id = s.student_id
            WHERE LOWER(a.teacher_username)=? AND a.status='Active' AND s.status='Active' AND COALESCE(s.is_deleted,0)=0
            ORDER BY s.grade, s.student_name
        """, conn, params=(st.session_state.username.lower(),))

        if my_advisees.empty:
            st.info("You have not been assigned any advisory students yet. Contact the Administrator.")
        else:
            st.markdown("#### My Assigned Advisory Students")
            st.dataframe(my_advisees[["student_name", "grade", "parent_name", "parent_phone"]], use_container_width=True)

            st.markdown("#### Submit Weekly Advisory Report")
            adv_map = {f"{r['student_name']} ({r['grade']})": int(r["student_id"]) for _, r in my_advisees.iterrows()}
            with st.form("teacher_advisory_report_form"):
                c1, c2, c3 = st.columns(3)
                sel_adv = c1.selectbox("Select Advisee", list(adv_map.keys()))
                wk_end = c2.date_input("Week Ending Date", datetime.date.today())
                wb_status = c3.selectbox("Student Well-being", ["Thriving", "Needs Academic Support", "Needs Behavioral Support", "Urgent Follow-up"])
                summary_txt = st.text_area("Weekly Advisory Discussion & Observations *")
                action_txt = st.text_area("Follow-up Action Plan")
                if st.form_submit_button("Submit Weekly Report", use_container_width=True):
                    if not summary_txt.strip():
                        st.error("Please enter your weekly observations.")
                    else:
                        conn.execute("""
                            INSERT INTO advisory_reports (teacher_username, teacher_name, student_id, week_ending, wellbeing_status, summary, action_plan, submitted_at, is_deleted)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                        """, (st.session_state.username, st.session_state.user_name, adv_map[sel_adv], str(wk_end), wb_status, summary_txt.strip(), action_txt.strip(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn.commit()
                        st.success("Weekly Advisory Report submitted!")
                        st.rerun()

            st.markdown("#### My Submitted Weekly Reports")
            my_reps = pd.read_sql_query("""
                SELECT r.week_ending, s.student_name, s.grade, r.wellbeing_status, r.summary, r.action_plan, r.submitted_at
                FROM advisory_reports r
                JOIN students s ON r.student_id = s.student_id
                WHERE LOWER(r.teacher_username)=? AND COALESCE(r.is_deleted,0)=0
                ORDER BY r.report_id DESC
            """, conn, params=(st.session_state.username.lower(),))
            st.dataframe(my_reps, use_container_width=True)

# ====================== 5. GRADES ======================
elif menu == "Grades":
    st.subheader("📝 Grades & Assessments")
    cls_opts = allowed_classes()
    sub_opts = allowed_subjects()

    if not cls_opts or not sub_opts:
        st.warning("You have no assigned classes or subjects. Please ask the Administrator to assign your classes and subjects.")
        st.stop()

    sel_cls = st.selectbox("Select Class Level", cls_opts)
    st_df = pd.read_sql_query("SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' AND COALESCE(is_deleted,0)=0 ORDER BY student_name", conn, params=(sel_cls,))

    if st_df.empty:
        st.warning(f"No active students found in {sel_cls}.")
    else:
        with st.form("grade_entry_form"):
            c1, c2, c3 = st.columns(3)
            s_map = dict(zip(st_df["student_name"], st_df["student_id"]))
            sel_s = c1.selectbox("Student", list(s_map.keys()))
            sel_sub = c2.selectbox("Subject", sub_opts)
            sel_term = c3.selectbox("Term", ["Term 1", "Term 2", "Term 3"])

            c4, c5, c6 = st.columns(3)
            a_type = c4.selectbox("Assessment Type", ASSESSMENT_TYPES)
            score_val = c5.number_input("Score", min_value=0.0, max_value=100.0, value=70.0)
            max_val = c6.number_input("Max Score", min_value=1.0, max_value=100.0, value=100.0)

            if st.form_submit_button("Save Grade", use_container_width=True):
                conn.execute("""
                    INSERT INTO grades (student_id, subject, assessment_type, score, max_score, term, date, teacher, is_deleted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (int(s_map[sel_s]), sel_sub, a_type, score_val, max_val, sel_term, str(datetime.date.today()), st.session_state.user_name))
                conn.commit()
                st.success(f"Saved {sel_sub} ({a_type}) grade for {sel_s}!")

    placeholders = ",".join("?" for _ in sub_opts)
    grades_df = pd.read_sql_query(f"""
        SELECT g.grade_id, s.student_name, s.grade, g.term, g.subject, g.assessment_type, g.score, g.max_score, g.date, g.teacher
        FROM grades g
        JOIN students s ON g.student_id = s.student_id
        WHERE s.grade = ? AND g.subject IN ({placeholders}) AND COALESCE(g.is_deleted,0)=0
        ORDER BY g.grade_id DESC
    """, conn, params=(sel_cls, *sub_opts))
    st.dataframe(grades_df, use_container_width=True)

# ====================== 6. ATTENDANCE ======================
elif menu == "Attendance":
    st.subheader("📅 Class Attendance")
    cls_opts = allowed_classes()
    if not cls_opts:
        st.warning("No classes assigned to your account.")
        st.stop()

    c1, c2 = st.columns(2)
    sel_cls = c1.selectbox("Select Class Level", cls_opts)
    att_date = c2.date_input("Attendance Date", datetime.date.today())

    st_df = pd.read_sql_query("SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' AND COALESCE(is_deleted,0)=0 ORDER BY student_name", conn, params=(sel_cls,))
    if st_df.empty:
        st.warning(f"No active students in {sel_cls}.")
    else:
        with st.form("attendance_entry_form"):
            rows = []
            for _, r in st_df.iterrows():
                col1, col2, col3 = st.columns([2, 2, 3])
                col1.write(f"**{r['student_name']}**")
                st_att = col2.selectbox("Status", ["Present", "Absent", "Late", "Excused"], key=f"att_st_{r['student_id']}")
                nt = col3.text_input("Notes", key=f"att_nt_{r['student_id']}")
                rows.append((int(r["student_id"]), str(att_date), st_att, st.session_state.user_name, nt, 0))
            if st.form_submit_button("Save Class Attendance", use_container_width=True):
                conn.executemany("INSERT INTO attendance (student_id, date, status, teacher, notes, is_deleted) VALUES (?, ?, ?, ?, ?, ?)", rows)
                conn.commit()
                st.success(f"Attendance recorded for {sel_cls} on {att_date}!")

    st.markdown("#### Recent Attendance Logs")
    logs = pd.read_sql_query("""
        SELECT a.date, s.grade, s.student_name, a.status, a.notes, a.teacher
        FROM attendance a JOIN students s ON a.student_id = s.student_id
        WHERE s.grade = ? AND COALESCE(a.is_deleted,0)=0
        ORDER BY a.attendance_id DESC LIMIT 30
    """, conn, params=(sel_cls,))
    st.dataframe(logs, use_container_width=True)

# ====================== 7. PAYMENTS (ADMINISTRATION ONLY) ======================
elif menu == "Payments":
    st.subheader("💳 School Fees & Payments (2026 – 2030)")

    if st.session_state.user_role != "Administration":
        st.error("Only the Administrator is authorized to record or modify payment records.")
        st.stop()

    t_rec, t_all, t_matrix = st.tabs([
        "📝 Record / Update Payment",
        "📋 All Payments by Class",
        "📆 Multi-Year Tracker (2026–2030)"
    ])

    with t_rec:
        sel_cls = st.selectbox("Class Level", CLASS_LEVELS, key="pay_cls_sel")
        st_cls_df = pd.read_sql_query("SELECT student_id, student_name, status FROM students WHERE grade=? AND COALESCE(is_deleted,0)=0 ORDER BY student_name", conn, params=(sel_cls,))

        if st_cls_df.empty:
            st.warning(f"No students registered in {sel_cls}.")
        else:
            with st.form("record_payment_form"):
                c1, c2 = st.columns(2)
                s_map = {f"{r['student_name']} ({r['status']})": int(r["student_id"]) for _, r in st_cls_df.iterrows()}
                sel_student = c1.selectbox("Student", list(s_map.keys()))
                sel_month = c2.selectbox("Billing Month (Nov 2026 – Dec 2030)", PAYMENT_MONTHS)

                c3, c4 = st.columns(2)
                pay_status = c3.selectbox("Payment Status", PAYMENT_STATUS)
                pay_amount = c4.number_input("Amount (RWF)", min_value=0, value=MONTHLY_FEE, step=500)
                pay_note = st.text_input("Notes (Optional)")

                if st.form_submit_button("Save Payment Record", use_container_width=True):
                    sid = s_map[sel_student]
                    final_amt = 0 if pay_status in ("Not paid", "Bonus", "Drop out") and pay_amount == MONTHLY_FEE else pay_amount
                    conn.execute("""
                        INSERT INTO payments (student_id, month_year, amount, status, paid_date, recorded_by, notes, is_deleted)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                        ON CONFLICT(student_id, month_year) DO UPDATE SET
                            amount = excluded.amount,
                            status = excluded.status,
                            paid_date = excluded.paid_date,
                            recorded_by = excluded.recorded_by,
                            notes = excluded.notes,
                            is_deleted = 0
                    """, (sid, sel_month, final_amt, pay_status, str(datetime.date.today()), st.session_state.user_name, pay_note))
                    if pay_status == "Drop out":
                        conn.execute("UPDATE students SET status='Inactive' WHERE student_id=?", (sid,))
                    conn.commit()
                    st.success(f"Saved payment status **{pay_status}** for {sel_month}!")
                    st.rerun()

    with t_all:
        view_cls = st.selectbox("Filter Class Level", ["All Classes"] + CLASS_LEVELS, key="pay_view_cls")
        if view_cls == "All Classes":
            p_df = pd.read_sql_query("""
                SELECT p.payment_id, s.student_name, s.grade, p.month_year, p.status, p.amount, p.paid_date, p.recorded_by, p.notes
                FROM payments p JOIN students s ON p.student_id = s.student_id
                WHERE COALESCE(p.is_deleted,0)=0
                ORDER BY p.payment_id DESC
            """, conn)
        else:
            p_df = pd.read_sql_query("""
                SELECT p.payment_id, s.student_name, s.grade, p.month_year, p.status, p.amount, p.paid_date, p.recorded_by, p.notes
                FROM payments p JOIN students s ON p.student_id = s.student_id
                WHERE s.grade = ? AND COALESCE(p.is_deleted,0)=0
                ORDER BY p.payment_id DESC
            """, conn, params=(view_cls,))
        st.dataframe(p_df, use_container_width=True)

    with t_matrix:
        mc1, mc2 = st.columns(2)
        m_cls = mc1.selectbox("Select Class", CLASS_LEVELS, key="mat_cls")
        m_yr = mc2.selectbox("Select Year", ["2026", "2027", "2028", "2029", "2030"], key="mat_yr")
        yr_months = [m for m in PAYMENT_MONTHS if m.startswith(m_yr)]

        sts = pd.read_sql_query("SELECT student_id, student_name, status FROM students WHERE grade=? AND COALESCE(is_deleted,0)=0 ORDER BY student_name", conn, params=(m_cls,))
        pays = pd.read_sql_query("SELECT p.student_id, p.month_year, p.status FROM payments p JOIN students s ON p.student_id = s.student_id WHERE s.grade=? AND COALESCE(p.is_deleted,0)=0", conn, params=(m_cls,))
        lookup = {(r["student_id"], r["month_year"]): r["status"] for _, r in pays.iterrows()}

        grid = []
        for _, s in sts.iterrows():
            row = {"Student": s["student_name"], "Account": s["status"]}
            for ym in yr_months:
                row[ym] = lookup.get((s["student_id"], ym), "Not paid")
            grid.append(row)
        st.dataframe(pd.DataFrame(grid), use_container_width=True)

# ====================== 8. REPORT CARDS ======================
elif menu == "Report Cards":
    st.subheader("🎓 Student Report Cards (PDF)")
    cls_opts = allowed_classes()
    if not cls_opts:
        st.warning("No classes assigned.")
        st.stop()

    sel_cls = st.selectbox("Select Class Level", cls_opts)
    st_df = pd.read_sql_query("SELECT * FROM students WHERE grade=? AND status='Active' AND COALESCE(is_deleted,0)=0 ORDER BY student_name", conn, params=(sel_cls,))
    if st_df.empty:
        st.info("No active students in this class.")
    else:
        c1, c2 = st.columns(2)
        sel_name = c1.selectbox("Student", st_df["student_name"].tolist())
        sel_term = c2.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
        s_row = st_df[st_df["student_name"] == sel_name].iloc[0].to_dict()

        g_df = pd.read_sql_query("SELECT subject, assessment_type, score, max_score FROM grades WHERE student_id=? AND term=? AND COALESCE(is_deleted,0)=0", conn, params=(int(s_row["student_id"]), sel_term))
        if g_df.empty:
            st.info(f"No grades recorded yet for {sel_name} in {sel_term}.")
        else:
            st.dataframe(g_df, use_container_width=True)
            pdf_bytes = build_report_pdf(s_row, g_df, sel_term)
            st.download_button(
                "📄 Download Official Report Card (PDF)",
                data=pdf_bytes,
                file_name=f"ReportCard_{sel_name.replace(' ', '_')}_{sel_term}.pdf",
                mime="application/pdf"
            )

# ====================== 9. CODE OF CONDUCT ======================
elif menu == "Code of Conduct":
    st.subheader("⚖️ Code of Conduct")
    with st.form("conduct_entry_form"):
        c1, c2, c3 = st.columns(3)
        p_type = c1.selectbox("Person Type", ["Student", "Staff"])
        p_name = c2.text_input("Full Name *").strip()
        g_role = c3.text_input("Class Level or Staff Role").strip()
        c4, c5 = st.columns(2)
        inc = c4.selectbox("Incident Type", ["Commendation (+)", "Warning (-)", "Suspension (-)"])
        pts = c5.number_input("Points Change", value=5 if "+" in inc else -5)
        notes = st.text_area("Details")
        if st.form_submit_button("Save Conduct Record"):
            if p_name:
                conn.execute("""
                    INSERT INTO conduct (person_type, person_name, grade_or_role, incident_type, points_change, notes, date, recorded_by, is_deleted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (p_type, p_name, g_role, inc, pts, notes.strip(), str(datetime.date.today()), st.session_state.user_name))
                conn.commit()
                st.success("Conduct record saved.")
    st.dataframe(pd.read_sql_query("SELECT conduct_id, person_type, person_name, grade_or_role, incident_type, points_change, notes, date, recorded_by FROM conduct WHERE COALESCE(is_deleted,0)=0 ORDER BY conduct_id DESC", conn), use_container_width=True)

# ====================== 10. PERMISSION & EMERGENCY ======================
elif menu == "Permission & Emergency":
    st.subheader("🚑 Permission & Emergency Logs")
    sts = pd.read_sql_query("SELECT student_id, student_name, grade FROM students WHERE status='Active' AND COALESCE(is_deleted,0)=0 ORDER BY grade, student_name", conn)
    if sts.empty:
        st.info("No active students registered.")
    else:
        with st.form("perm_form"):
            s_map = {f"{r['student_name']} ({r['grade']})": int(r["student_id"]) for _, r in sts.iterrows()}
            c1, c2 = st.columns(2)
            sel_s = c1.selectbox("Student", list(s_map.keys()))
            r_type = c2.selectbox("Request Type", ["Medical Leave", "Family Permission", "Emergency Exit", "Other"])
            c3, c4, c5 = st.columns(3)
            s_dt = c3.date_input("Start Date", datetime.date.today())
            e_dt = c4.date_input("Return Date", datetime.date.today())
            e_contact = c5.text_input("Emergency Contact Phone").strip()
            reason = st.text_area("Reason / Notes")
            if st.form_submit_button("Record Permission"):
                conn.execute("""
                    INSERT INTO permissions (student_id, request_type, reason, start_date, end_date, emergency_contact, status, recorded_by, created_at, is_deleted)
                    VALUES (?, ?, ?, ?, ?, ?, 'Approved', ?, ?, 0)
                """, (s_map[sel_s], r_type, reason.strip(), str(s_dt), str(e_dt), e_contact, st.session_state.user_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                st.success("Permission recorded.")
    st.dataframe(pd.read_sql_query("""
        SELECT p.perm_id, s.student_name, s.grade, p.request_type, p.start_date, p.end_date, p.emergency_contact, p.reason, p.recorded_by
        FROM permissions p JOIN students s ON p.student_id = s.student_id
        WHERE COALESCE(p.is_deleted,0)=0 ORDER BY p.perm_id DESC
    """, conn), use_container_width=True)

# ====================== 11. NOTIFICATIONS ======================
elif menu == "Notifications":
    st.subheader("📢 School Announcements & Notifications")
    if st.session_state.user_role == "Administration":
        with st.form("notif_form"):
            title = st.text_input("Announcement Title *").strip()
            msg = st.text_area("Message *").strip()
            if st.form_submit_button("Post Announcement"):
                if title and msg:
                    conn.execute("INSERT INTO notifications (title, message, created_by, created_at, is_deleted) VALUES (?, ?, ?, ?, 0)", (title, msg, st.session_state.user_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Announcement posted!")
    st.dataframe(pd.read_sql_query("SELECT notif_id, title, message, created_by, created_at FROM notifications WHERE COALESCE(is_deleted,0)=0 ORDER BY notif_id DESC", conn), use_container_width=True)

# ====================== 12. MESSAGES ======================
elif menu == "Messages":
    st.subheader("💬 Internal Staff Messages")
    staff_names = pd.read_sql_query("SELECT full_name FROM staff WHERE status='Active' AND COALESCE(is_deleted,0)=0", conn)["full_name"].tolist()
    with st.form("msg_form"):
        c1, c2 = st.columns(2)
        rec = c1.selectbox("Recipient", ["All Staff"] + staff_names)
        subj = c2.text_input("Subject *").strip()
        body = st.text_area("Message *").strip()
        if st.form_submit_button("Send Message"):
            if subj and body:
                conn.execute("""
                    INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at, is_deleted)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (st.session_state.user_name, st.session_state.user_role, rec, subj, body, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                st.success("Message sent!")
    st.dataframe(pd.read_sql_query("SELECT msg_id, sender_name, sender_role, recipient, subject, message, created_at FROM messages WHERE COALESCE(is_deleted,0)=0 ORDER BY msg_id DESC", conn), use_container_width=True)

# ====================== 13. REMOVED RECORDS (ADMIN ONLY) ======================
elif menu == "Removed Records":
    if st.session_state.user_role != "Administration":
        st.error("Access restricted to Administration.")
        st.stop()

    st.subheader("🗂️ Removed Records Archive")
    t_archive, t_remove = st.tabs(["📜 Archived Records", "🗑️ Remove a Record"])
    with t_archive:
        arch_df = pd.read_sql_query("SELECT * FROM removed_records ORDER BY archive_id DESC", conn)
        st.dataframe(arch_df, use_container_width=True)
    with t_remove:
        target_tbl = st.selectbox("Select Category", ["students", "payments", "grades"])
        if target_tbl == "students":
            df_r = pd.read_sql_query("SELECT student_id AS id, student_name || ' (' || grade || ')' AS label FROM students WHERE COALESCE(is_deleted,0)=0", conn)
            id_col = "student_id"
        elif target_tbl == "payments":
            df_r = pd.read_sql_query("SELECT p.payment_id AS id, s.student_name || ' - ' || p.month_year || ' (' || p.status || ')' AS label FROM payments p JOIN students s ON p.student_id=s.student_id WHERE COALESCE(p.is_deleted,0)=0", conn)
            id_col = "payment_id"
        else:
            df_r = pd.read_sql_query("SELECT g.grade_id AS id, s.student_name || ' - ' || g.subject || ' (' || g.score || ')' AS label FROM grades g JOIN students s ON g.student_id=s.student_id WHERE COALESCE(g.is_deleted,0)=0", conn)
            id_col = "grade_id"

        if df_r.empty:
            st.info("No active records available to remove in this category.")
        else:
            r_map = dict(zip(df_r["label"], df_r["id"]))
            sel_item = st.selectbox("Select Record to Archive", list(r_map.keys()))
            if st.button("Archive Selected Record"):
                archive_record(conn, target_tbl, id_col, r_map[sel_item], sel_item)
                st.success("Record moved to Removed Records archive.")
                st.rerun()

conn.close()
