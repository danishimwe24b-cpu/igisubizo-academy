import streamlit as st
import pandas as pd
import sqlite3
import datetime 
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER

# ====================== CONFIG ======================
CLASS_LEVELS = ["P1A", "P1B", "P2A", "P2B", "P3A", "P3B", "P4A", "P4B", "P5", "P6"]
SUBJECT_LIST = ["English", "Kinyarwanda", "Mathematics", "SET", "SST", "French", "Kiswahili"]

PAYMENT_MONTHS = []
for year in [2026, 2027, 2028, 2029, 2030]:
    start_month = 11 if year == 2026 else 1
    end_month = 12
    for m in range(start_month, end_month + 1):
        PAYMENT_MONTHS.append(f"{year}-{m:02d}")

PAYMENT_STATUS = [
    "Paid", "Not paid", "Late 5 days", "Late 5-10 days",
    "Late 15 days", "Bonus", "Drop out"
]

MONTHLY_FEE = 5000

# ====================== DATABASE ======================
def get_conn():
    return sqlite3.connect("igisubizo_academy.db", check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
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
    """)

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
            teacher TEXT
        )
    """)

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

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            month_year TEXT,
            amount REAL DEFAULT 5000,
            status TEXT DEFAULT 'Not paid',
            paid_date TEXT,
            recorded_by TEXT,
            UNIQUE(student_id, month_year)
        )
    """)

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

    # Default admin
    c.execute("SELECT COUNT(*) FROM staff WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status)
            VALUES ('Head Administrator', 'Administration', 'admin', 'admin123', '0780000000', 'ALL', 'ALL', 'Active')
        """)

    conn.commit()
    conn.close()

init_db()

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

# ====================== SESSION ======================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.session_state.username = ""
    st.session_state.assigned_classes = "ALL"
    st.session_state.assigned_subjects = "ALL"

# ====================== LOGIN ======================
if not st.session_state.logged_in:
    st.markdown("""
    <div style="background:linear-gradient(90deg,#0B6E4F,#0A3D62);padding:25px;border-radius:12px;color:white;text-align:center;">
        <h1>🎓 IGISUBIZO ACADEMY</h1>
        <p>School Management System</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("System Login")
    st.info("Default Admin → Username: `admin`  |  Password: `admin123`")

    with st.form("login_form"):
        role = st.selectbox("Select Role", ["Administration", "Teacher", "Register Officer"])
        uname = st.text_input("Username").strip()
        pwd = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
            conn = get_conn()
            df = pd.read_sql_query(
                "SELECT * FROM staff WHERE LOWER(username)=? AND password=? AND role=? AND status='Active'",
                conn, params=(uname.lower(), pwd, role)
            )
            conn.close()
            if not df.empty:
                rec = df.iloc[0]
                st.session_state.logged_in = True
                st.session_state.user_name = rec["full_name"]
                st.session_state.user_role = rec["role"]
                st.session_state.username = rec["username"]
                st.session_state.assigned_classes = rec["assigned_classes"] or "ALL"
                st.session_state.assigned_subjects = rec["assigned_subjects"] or "ALL"
                st.rerun()
            else:
                st.error("Invalid username, password or role")
    st.stop()

# ====================== SIDEBAR ======================
with st.sidebar:
    st.success(f"👤 {st.session_state.user_name}\n\n**{st.session_state.user_role}**")
    if st.session_state.user_role == "Teacher":
        st.caption(f"Classes: {st.session_state.assigned_classes}")
        st.caption(f"Subjects: {st.session_state.assigned_subjects}")
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.divider()

    if st.session_state.user_role == "Administration":
        menu = st.radio("Menu", [
            "Dashboard", "Students", "Staff & Teachers", "Grades",
            "Attendance", "Payments", "Report Card", "Messages"
        ])
    elif st.session_state.user_role == "Teacher":
        menu = st.radio("Menu", ["Grades", "Attendance", "Report Card", "Messages"])
    else:
        menu = st.radio("Menu", ["Students", "Payments", "Report Card", "Messages"])

# ====================== HELPERS ======================
def get_allowed_classes():
    if st.session_state.assigned_classes == "ALL":
        return CLASS_LEVELS
    return [c.strip() for c in st.session_state.assigned_classes.split(",") if c.strip()]

def get_allowed_subjects():
    if st.session_state.assigned_subjects == "ALL":
        return SUBJECT_LIST
    return [s.strip() for s in st.session_state.assigned_subjects.split(",") if s.strip()]

# ====================== DASHBOARD ======================
if menu == "Dashboard":
    st.header("📊 Dashboard")
    conn = get_conn()
    active_students = pd.read_sql_query("SELECT COUNT(*) as c FROM students WHERE status='Active'", conn).iloc[0]["c"]
    total_paid = pd.read_sql_query("SELECT COALESCE(SUM(amount),0) as t FROM payments WHERE status='Paid'", conn).iloc[0]["t"]
    active_staff = pd.read_sql_query("SELECT COUNT(*) as c FROM staff WHERE status='Active'", conn).iloc[0]["c"]
    conn.close()

    c1, c2, c3 = st.columns(3)
    c1.metric("Active Students", active_students)
    c2.metric("Total Fees Collected", f"{total_paid:,.0f} RWF")
    c3.metric("Active Staff", active_staff)

# ====================== STUDENTS ======================
elif menu == "Students":
    st.header("👥 Students")
    conn = get_conn()

    tab1, tab2, tab3 = st.tabs(["Student List", "Add Student", "Manage Status / Delete"])

    with tab1:
        grade = st.selectbox("Select Class Level", ["All"] + CLASS_LEVELS)
        if grade == "All":
            df = pd.read_sql_query("SELECT * FROM students ORDER BY grade, student_name", conn)
        else:
            df = pd.read_sql_query("SELECT * FROM students WHERE grade=? ORDER BY student_name", conn, params=(grade,))
        st.dataframe(df, use_container_width=True)

    with tab2:
        with st.form("add_student"):
            name = st.text_input("Student Full Name *")
            g = st.selectbox("Class Level", CLASS_LEVELS)
            pname = st.text_input("Parent Name")
            phone = st.text_input("Parent Phone")
            email = st.text_input("Parent Email")
            if st.form_submit_button("Save Student") and name.strip():
                conn.execute(
                    "INSERT INTO students (student_name, grade, parent_name, parent_phone, parent_email, status, created_at) VALUES (?,?,?,?,?,'Active',?)",
                    (name.strip(), g, pname.strip(), phone.strip(), email.strip(), str(datetime.date.today()))
                )
                conn.commit()
                st.success("Student added successfully")
                st.rerun()

    with tab3:
        st.subheader("Change Status or Delete Inactive")
        df = pd.read_sql_query("SELECT student_id, student_name, grade, status FROM students ORDER BY grade, student_name", conn)
        st.dataframe(df, use_container_width=True)

        sid = st.number_input("Student ID", min_value=1, step=1)
        new_status = st.selectbox("New Status", ["Active", "Inactive"])
        col1, col2 = st.columns(2)
        if col1.button("Update Status"):
            conn.execute("UPDATE students SET status=? WHERE student_id=?", (new_status, sid))
            conn.commit()
            st.success("Status updated")
            st.rerun()
        if col2.button("Delete Inactive Student"):
            conn.execute("DELETE FROM students WHERE student_id=? AND status='Inactive'", (sid,))
            conn.commit()
            st.success("Inactive student deleted (if existed)")
            st.rerun()

    conn.close()

# ====================== STAFF & TEACHERS ======================
elif menu == "Staff & Teachers":
    st.header("👨‍🏫 Staff & Teachers")
    conn = get_conn()

    tab1, tab2, tab3 = st.tabs(["Create Account", "Assign Classes & Subjects", "Reset / Delete"])

    with tab1:
        with st.form("create_staff"):
            name = st.text_input("Full Name *")
            role = st.selectbox("Role", ["Teacher", "Register Officer", "Administration"])
            uname = st.text_input("Username *")
            pwd = st.text_input("Temporary Password", value="123456")
            phone = st.text_input("Phone")
            classes = st.multiselect("Assigned Classes (for Teachers)", CLASS_LEVELS)
            subjects = st.multiselect("Assigned Subjects (for Teachers)", SUBJECT_LIST)
            if st.form_submit_button("Create Account") and name and uname:
                cls = ",".join(classes) if classes else "ALL"
                sub = ",".join(subjects) if subjects else "ALL"
                try:
                    conn.execute(
                        "INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status) VALUES (?,?,?,?,?,?,?,'Active')",
                        (name.strip(), role, uname.strip(), pwd.strip(), phone.strip(), cls, sub)
                    )
                    conn.commit()
                    st.success(f"Account created! Username: {uname} | Password: {pwd}")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")

    with tab2:
        teachers = pd.read_sql_query("SELECT username, full_name, assigned_classes, assigned_subjects FROM staff WHERE role='Teacher'", conn)
        st.dataframe(teachers, use_container_width=True)
        if not teachers.empty:
            sel = st.selectbox("Select Teacher", teachers["username"].tolist())
            new_cls = st.multiselect("New Classes", CLASS_LEVELS)
            new_sub = st.multiselect("New Subjects", SUBJECT_LIST)
            if st.button("Update Assignment"):
                conn.execute(
                    "UPDATE staff SET assigned_classes=?, assigned_subjects=? WHERE username=?",
                    (",".join(new_cls) if new_cls else "NONE", ",".join(new_sub) if new_sub else "NONE", sel)
                )
                conn.commit()
                st.success("Updated")
                st.rerun()

    with tab3:
        staff = pd.read_sql_query("SELECT staff_id, full_name, role, username, status FROM staff", conn)
        st.dataframe(staff, use_container_width=True)
        sid = st.number_input("Staff ID", min_value=1, step=1)
        new_pwd = st.text_input("New Password", value="123456")
        new_stat = st.selectbox("Status", ["Active", "Inactive"])
        c1, c2 = st.columns(2)
        if c1.button("Update Password & Status"):
            conn.execute("UPDATE staff SET password=?, status=? WHERE staff_id=?", (new_pwd, new_stat, sid))
            conn.commit()
            st.success("Updated")
            st.rerun()
        if c2.button("Delete Inactive Staff"):
            conn.execute("DELETE FROM staff WHERE staff_id=? AND status='Inactive'", (sid,))
            conn.commit()
            st.success("Deleted if inactive")
            st.rerun()

    conn.close()

# ====================== GRADES ======================
elif menu == "Grades":
    st.header("📝 Grades")
    conn = get_conn()
    allowed_classes = get_allowed_classes()
    allowed_subjects = get_allowed_subjects()

    grade = st.selectbox("Select Class Level", allowed_classes)
    students = pd.read_sql_query(
        "SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
        conn, params=(grade,)
    )

    if students.empty:
        st.warning("No active students in this class")
    else:
        with st.form("grade_form"):
            student_map = dict(zip(students["student_name"], students["student_id"]))
            sel_student = st.selectbox("Student", list(student_map.keys()))
            subject = st.selectbox("Subject", allowed_subjects)
            assess = st.selectbox("Assessment", ["Homework", "Exercise", "Quiz", "Exam", "Midterm"])
            score = st.number_input("Score", 0.0, 100.0, 70.0)
            term = st.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
            if st.form_submit_button("Save Grade"):
                conn.execute(
                    "INSERT INTO grades (student_id, subject, assessment_type, score, max_score, term, date, teacher) VALUES (?,?,?,?,100,?,?,?)",
                    (student_map[sel_student], subject, assess, score, term, str(datetime.date.today()), st.session_state.user_name)
                )
                conn.commit()
                st.success("Grade saved")
                st.rerun()

        st.dataframe(pd.read_sql_query(
            "SELECT g.date, s.student_name, g.subject, g.assessment_type, g.score, g.term, g.teacher FROM grades g JOIN students s ON g.student_id=s.student_id WHERE s.grade=? ORDER BY g.grade_id DESC LIMIT 30",
            conn, params=(grade,)
        ), use_container_width=True)
    conn.close()

# ====================== ATTENDANCE ======================
elif menu == "Attendance":
    st.header("📅 Attendance")
    conn = get_conn()
    allowed_classes = get_allowed_classes()
    grade = st.selectbox("Select Class Level", allowed_classes)
    att_date = st.date_input("Date", datetime.date.today())
    students = pd.read_sql_query(
        "SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
        conn, params=(grade,)
    )

    if students.empty:
        st.warning("No active students")
    else:
        with st.form("att_form"):
            records = []
            for _, row in students.iterrows():
                c1, c2 = st.columns([3, 2])
                c1.write(f"**{row['student_name']}**")
                status = c2.selectbox("Status", ["Present", "Absent", "Late", "Permission"], key=f"a{row['student_id']}")
                records.append((row["student_id"], str(att_date), status, st.session_state.user_name, ""))
            if st.form_submit_button("Save Attendance"):
                conn.executemany(
                    "INSERT INTO attendance (student_id, date, status, teacher, notes) VALUES (?,?,?,?,?)",
                    records
                )
                conn.commit()
                st.success("Attendance saved")
                st.rerun()
    conn.close()

# ====================== PAYMENTS ======================
elif menu == "Payments":
    st.header("💳 Payments")
    if st.session_state.user_role not in ["Administration", "Register Officer"]:
        st.warning("Only Administration and Register Officer can manage payments")
        st.stop()

    conn = get_conn()
    tab1, tab2 = st.tabs(["Record Payment", "Payment Overview"])

    with tab1:
        grade = st.selectbox("Class Level", CLASS_LEVELS, key="pay_grade")
        students = pd.read_sql_query(
            "SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
            conn, params=(grade,)
        )
        if students.empty:
            st.warning("No active students")
        else:
            with st.form("pay_form"):
                smap = dict(zip(students["student_name"], students["student_id"]))
                student = st.selectbox("Student", list(smap.keys()))
                month = st.selectbox("Month", PAYMENT_MONTHS)
                status = st.selectbox("Payment Status", PAYMENT_STATUS)
                amount = st.number_input("Amount (RWF)", value=MONTHLY_FEE, step=500)
                if st.form_submit_button("Save Payment"):
                    try:
                        conn.execute(
                            "INSERT INTO payments (student_id, month_year, amount, status, paid_date, recorded_by) VALUES (?,?,?,?,?,?)",
                            (smap[student], month, amount, status, str(datetime.date.today()), st.session_state.user_name)
                        )
                        conn.commit()
                        st.success("Payment recorded")
                    except sqlite3.IntegrityError:
                        conn.execute(
                            "UPDATE payments SET amount=?, status=?, paid_date=?, recorded_by=? WHERE student_id=? AND month_year=?",
                            (amount, status, str(datetime.date.today()), st.session_state.user_name, smap[student], month)
                        )
                        conn.commit()
                        st.success("Payment updated")
                    st.rerun()

    with tab2:
        st.dataframe(pd.read_sql_query(
            "SELECT s.student_name, s.grade, p.month_year, p.amount, p.status, p.paid_date FROM payments p JOIN students s ON p.student_id=s.student_id ORDER BY p.month_year DESC, s.grade",
            conn
        ), use_container_width=True)

    conn.close()

# ====================== REPORT CARD ======================
elif menu == "Report Card":
    st.header("📄 Generate Report Card")
    conn = get_conn()
    allowed_classes = get_allowed_classes()
    grade = st.selectbox("Class Level", allowed_classes)
    students = pd.read_sql_query(
        "SELECT * FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
        conn, params=(grade,)
    )

    if students.empty:
        st.warning("No students")
    else:
        name = st.selectbox("Student", students["student_name"].tolist())
        term = st.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
        student = students[students["student_name"] == name].iloc[0]
        grades = pd.read_sql_query(
            "SELECT * FROM grades WHERE student_id=? AND term=?",
            conn, params=(int(student["student_id"]), term)
        )

        if grades.empty:
            st.info("No grades for this term")
        else:
            st.dataframe(grades[["subject", "assessment_type", "score", "max_score"]], use_container_width=True)

            # PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [
                Paragraph("IGISUBIZO ACADEMY", styles["Title"]),
                Paragraph(f"Report Card - {term}", styles["Heading2"]),
                Spacer(1, 12),
                Paragraph(f"<b>Student:</b> {student['student_name']}<br/><b>Class:</b> {student['grade']}<br/><b>Parent:</b> {student['parent_name']} ({student['parent_phone']})", styles["Normal"]),
                Spacer(1, 16)
            ]
            data = [["Subject", "Assessment", "Score", "Max", "%"]]
            for _, r in grades.iterrows():
                pct = (r["score"] / r["max_score"] * 100) if r["max_score"] else 0
                data.append([r["subject"], r["assessment_type"], f"{r['score']:.1f}", f"{r['max_score']:.1f}", f"{pct:.1f}%"])
            t = Table(data)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B6E4F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            story.append(t)
            doc.build(story)
            buffer.seek(0)
            st.download_button("⬇️ Download PDF Report Card", data=buffer,
                               file_name=f"Report_{name.replace(' ', '_')}_{term}.pdf",
                               mime="application/pdf")
    conn.close()

# ====================== MESSAGES ======================
elif menu == "Messages":
    st.header("💬 Messages & Parent Requests")
    conn = get_conn()
    with st.form("msg_form"):
        recipient = st.selectbox("Send To", ["Administration", "Teachers", "Register Officer", "All Staff"])
        subject = st.text_input("Subject")
        body = st.text_area("Message")
        if st.form_submit_button("Send") and body.strip():
            conn.execute(
                "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (?,?,?,?,?,?)",
                (st.session_state.user_name, st.session_state.user_role, recipient, subject, body, str(datetime.datetime.now()))
            )
            conn.commit()
            st.success("Message sent")
            st.rerun()

    st.dataframe(pd.read_sql_query("SELECT * FROM messages ORDER BY msg_id DESC LIMIT 50", conn), use_container_width=True)
    conn.close()
