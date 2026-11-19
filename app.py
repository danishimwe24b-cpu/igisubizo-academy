import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import os
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

PAYMENT_STATUS = ["Paid", "Not paid", "Late 5 days", "Late 5-10 days", "Late 15 days", "Bonus", "Drop out"]
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
            gender TEXT DEFAULT 'Male',
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
            assessment_type TEXT,
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            created_by TEXT,
            created_at TEXT
        )
    """)

    # Default Admin
    c.execute("SELECT COUNT(*) FROM staff WHERE username='admin'")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status)
            VALUES ('Head Administrator', 'Administration', 'admin', 'admin123', '0780000000', 'ALL', 'ALL', 'Active')
        """)

    conn.commit()
    conn.close()

init_db()

# ====================== PAGE SETUP ======================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

# Custom CSS with logo background attempt
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

# ====================== LOGIN ======================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=180)
        st.markdown("<h2 style='text-align:center;'>IGISUBIZO ACADEMY</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;'>School Management System</p>", unsafe_allow_html=True)

        st.info("Default Admin: username `admin` / password `admin123`")

        with st.form("login_form"):
            role = st.selectbox("Select Role", ["Administration", "Teacher", "Register Officer"])
            uname = st.text_input("Username").strip()
            pwd = st.text_input("Password", type="password").strip()
            if st.form_submit_button("Login", use_container_width=True):
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
                    st.error("Invalid credentials or role")
    st.stop()

# ====================== SIDEBAR ======================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
    st.success(f"👤 **{st.session_state.user_name}**\n\n{st.session_state.user_role}")
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
            "Dashboard", "Students", "Staff & Teachers", "Grades",
            "Attendance", "Payments", "Report Cards", "Code of Conduct",
            "Permission & Emergency", "Notifications", "Messages", "Removed Records"
        ])
    elif st.session_state.user_role == "Teacher":
        menu = st.radio("Navigation", [
            "Grades", "Attendance", "Report Cards", "Code of Conduct",
            "Permission & Emergency", "Notifications", "Messages"
        ])
    else:
        menu = st.radio("Navigation", [
            "Students", "Payments", "Report Cards", "Code of Conduct",
            "Permission & Emergency", "Messages"
        ])

# ====================== HELPERS ======================
def allowed_classes():
    if st.session_state.assigned_classes == "ALL":
        return CLASS_LEVELS
    return [x.strip() for x in st.session_state.assigned_classes.split(",") if x.strip()]

def allowed_subjects():
    if st.session_state.assigned_subjects == "ALL":
        return SUBJECT_LIST
    return [x.strip() for x in st.session_state.assigned_subjects.split(",") if x.strip()]

# ====================== DASHBOARD ======================
if menu == "Dashboard":
    st.markdown("<div class='main-header'><h2>📊 Administration Dashboard</h2></div>", unsafe_allow_html=True)
    conn = get_conn()

    active_students = pd.read_sql_query("SELECT COUNT(*) as c FROM students WHERE status='Active'", conn).iloc[0]["c"]
    inactive_students = pd.read_sql_query("SELECT COUNT(*) as c FROM students WHERE status='Inactive'", conn).iloc[0]["c"]
    total_paid = pd.read_sql_query("SELECT COALESCE(SUM(amount),0) as t FROM payments WHERE status='Paid'", conn).iloc[0]["t"]
    active_staff = pd.read_sql_query("SELECT COUNT(*) as c FROM staff WHERE status='Active'", conn).iloc[0]["c"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Students", active_students)
    c2.metric("Inactive Students", inactive_students)
    c3.metric("Fees Collected", f"{total_paid:,.0f} RWF")
    c4.metric("Active Staff", active_staff)

    st.subheader("Students per Class Level")
    df = pd.read_sql_query("SELECT grade, COUNT(*) as total FROM students WHERE status='Active' GROUP BY grade", conn)
    if not df.empty:
        st.bar_chart(df.set_index("grade"))
    else:
        st.info("No active students yet")

    st.subheader("Recent Payments")
    st.dataframe(pd.read_sql_query("""
        SELECT s.student_name, s.grade, p.month_year, p.amount, p.status, p.paid_date
        FROM payments p JOIN students s ON p.student_id = s.student_id
        ORDER BY p.payment_id DESC LIMIT 15
    """, conn), use_container_width=True)
    conn.close()

# ====================== STUDENTS ======================
elif menu == "Students":
    st.header("👥 Students Management")
    conn = get_conn()
    tab1, tab2, tab3 = st.tabs(["Active Students", "Add Student", "Change Status"])

    with tab1:
        grade = st.selectbox("Filter by Class Level", ["All"] + CLASS_LEVELS)
        if grade == "All":
            df = pd.read_sql_query("SELECT student_id, student_name, grade, gender, parent_name, parent_phone, status FROM students WHERE status='Active' ORDER BY grade, student_name", conn)
        else:
            df = pd.read_sql_query("SELECT student_id, student_name, grade, gender, parent_name, parent_phone, status FROM students WHERE grade=? AND status='Active' ORDER BY student_name", conn, params=(grade,))
        st.dataframe(df, use_container_width=True)

    with tab2:
        with st.form("add_student"):
            name = st.text_input("Student Full Name *")
            col1, col2 = st.columns(2)
            g = col1.selectbox("Class Level", CLASS_LEVELS)
            gender = col2.selectbox("Gender", ["Male", "Female"])
            pname = st.text_input("Parent / Guardian Name")
            phone = st.text_input("Parent Phone")
            email = st.text_input("Parent Email")
            if st.form_submit_button("Save Student") and name.strip():
                conn.execute(
                    "INSERT INTO students (student_name, grade, gender, parent_name, parent_phone, parent_email, status, created_at) VALUES (?,?,?,?,?,?,'Active',?)",
                    (name.strip(), g, gender, pname.strip(), phone.strip(), email.strip(), str(datetime.date.today()))
                )
                conn.commit()
                st.success("Student added successfully")
                st.rerun()

    with tab3:
        df = pd.read_sql_query("SELECT student_id, student_name, grade, status FROM students ORDER BY grade, student_name", conn)
        st.dataframe(df, use_container_width=True)
        sid = st.number_input("Student ID", min_value=1, step=1)
        new_status = st.selectbox("New Status", ["Active", "Inactive"])
        if st.button("Update Status"):
            conn.execute("UPDATE students SET status=? WHERE student_id=?", (new_status, int(sid)))
            conn.commit()
            st.success("Status updated – Inactive students are removed from active lists")
            st.rerun()
    conn.close()

# ====================== STAFF ======================
elif menu == "Staff & Teachers":
    st.header("👨‍🏫 Staff & Teachers")
    conn = get_conn()
    tab1, tab2, tab3 = st.tabs(["Create Account", "Assign Classes & Subjects", "Manage Accounts"])

    with tab1:
        with st.form("create_staff"):
            name = st.text_input("Full Name *")
            role = st.selectbox("Role", ["Teacher", "Register Officer", "Administration"])
            uname = st.text_input("Username *")
            pwd = st.text_input("Temporary Password", value="123456")
            phone = st.text_input("Phone")
            classes = st.multiselect("Assigned Classes (Teachers)", CLASS_LEVELS)
            subjects = st.multiselect("Assigned Subjects (Teachers)", SUBJECT_LIST)
            if st.form_submit_button("Create Account") and name and uname:
                cls = ",".join(classes) if classes else "ALL"
                sub = ",".join(subjects) if subjects else "ALL"
                try:
                    conn.execute(
                        "INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status) VALUES (?,?,?,?,?,?,?,'Active')",
                        (name.strip(), role, uname.strip(), pwd.strip(), phone.strip(), cls, sub)
                    )
                    conn.commit()
                    st.success(f"Account created → Username: `{uname}` | Password: `{pwd}`")
                except:
                    st.error("Username already exists")

    with tab2:
        tdf = pd.read_sql_query("SELECT username, full_name, assigned_classes, assigned_subjects FROM staff WHERE role='Teacher' AND status='Active'", conn)
        st.dataframe(tdf, use_container_width=True)
        if not tdf.empty:
            sel = st.selectbox("Select Teacher", tdf["username"].tolist())
            new_cls = st.multiselect("Classes", CLASS_LEVELS)
            new_sub = st.multiselect("Subjects", SUBJECT_LIST)
            if st.button("Update Assignment"):
                conn.execute("UPDATE staff SET assigned_classes=?, assigned_subjects=? WHERE username=?",
                             (",".join(new_cls) if new_cls else "NONE", ",".join(new_sub) if new_sub else "NONE", sel))
                conn.commit()
                st.success("Updated")
                st.rerun()

    with tab3:
        sdf = pd.read_sql_query("SELECT staff_id, full_name, role, username, status FROM staff", conn)
        st.dataframe(sdf, use_container_width=True)
        sid = st.number_input("Staff ID", min_value=1, step=1)
        new_pwd = st.text_input("New Password", value="123456")
        new_stat = st.selectbox("Status", ["Active", "Inactive"])
        c1, c2 = st.columns(2)
        if c1.button("Update Password & Status"):
            conn.execute("UPDATE staff SET password=?, status=? WHERE staff_id=?", (new_pwd, new_stat, int(sid)))
            conn.commit()
            st.success("Updated")
            st.rerun()
        if c2.button("Delete Inactive Staff"):
            conn.execute("DELETE FROM staff WHERE staff_id=? AND status='Inactive'", (int(sid),))
            conn.commit()
            st.success("Deleted if inactive")
            st.rerun()
    conn.close()

# ====================== GRADES ======================
elif menu == "Grades":
    st.header("📝 Grades & Progress")
    conn = get_conn()
    classes = allowed_classes()
    subjects = allowed_subjects()

    grade = st.selectbox("Select Class Level", classes)
    students = pd.read_sql_query(
        "SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
        conn, params=(grade,)
    )

    if students.empty:
        st.warning("No active students in this class")
    else:
        with st.form("grade_form"):
            smap = dict(zip(students["student_name"], students["student_id"]))
            student = st.selectbox("Student", list(smap.keys()))
            subject = st.selectbox("Subject", subjects)
            assess = st.selectbox("Assessment Type", ASSESSMENT_TYPES)
            score = st.number_input("Score", 0.0, 100.0, 70.0)
            term = st.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
            if st.form_submit_button("Save Grade"):
                conn.execute(
                    "INSERT INTO grades (student_id, subject, assessment_type, score, max_score, term, date, teacher) VALUES (?,?,?,?,100,?,?,?)",
                    (smap[student], subject, assess, score, term, str(datetime.date.today()), st.session_state.user_name)
                )
                conn.commit()
                st.success("Grade saved")
                st.rerun()

        st.dataframe(pd.read_sql_query("""
            SELECT g.date, s.student_name, g.subject, g.assessment_type, g.score, g.term, g.teacher
            FROM grades g JOIN students s ON g.student_id = s.student_id
            WHERE s.grade = ? ORDER BY g.grade_id DESC LIMIT 40
        """, conn, params=(grade,)), use_container_width=True)
    conn.close()

# ====================== ATTENDANCE ======================
elif menu == "Attendance":
    st.header("📅 Class Attendance")
    conn = get_conn()
    grade = st.selectbox("Select Class Level", allowed_classes())
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
                status = c2.selectbox("Status", ["Present", "Absent", "Late", "Permission"], key=f"att{row['student_id']}")
                records.append((row["student_id"], str(att_date), status, st.session_state.user_name, ""))
            if st.form_submit_button("Save Attendance"):
                conn.executemany("INSERT INTO attendance (student_id, date, status, teacher, notes) VALUES (?,?,?,?,?)", records)
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
    tab1, tab2 = st.tabs(["Record / Update Payment", "All Payments by Class"])

    with tab1:
        grade = st.selectbox("Class Level", CLASS_LEVELS, key="pgrade")
        students = pd.read_sql_query(
            "SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
            conn, params=(grade,)
        )
        if not students.empty:
            with st.form("pay_form"):
                smap = dict(zip(students["student_name"], students["student_id"]))
                student = st.selectbox("Student", list(smap.keys()))
                month = st.selectbox("Month", PAYMENT_MONTHS)
                status = st.selectbox("Status", PAYMENT_STATUS)
                amount = st.number_input("Amount (RWF)", value=MONTHLY_FEE, step=500)
                if st.form_submit_button("Save Payment"):
                    try:
                        conn.execute(
                            "INSERT INTO payments (student_id, month_year, amount, status, paid_date, recorded_by) VALUES (?,?,?,?,?,?)",
                            (smap[student], month, amount, status, str(datetime.date.today()), st.session_state.user_name)
                        )
                        conn.commit()
                        st.success("Payment saved")
                    except sqlite3.IntegrityError:
                        conn.execute(
                            "UPDATE payments SET amount=?, status=?, paid_date=?, recorded_by=? WHERE student_id=? AND month_year=?",
                            (amount, status, str(datetime.date.today()), st.session_state.user_name, smap[student], month)
                        )
                        conn.commit()
                        st.success("Payment updated")
                    st.rerun()

    with tab2:
        st.dataframe(pd.read_sql_query("""
            SELECT s.student_name, s.grade, s.gender, p.month_year, p.amount, p.status, p.paid_date, p.recorded_by
            FROM payments p JOIN students s ON p.student_id = s.student_id
            WHERE s.status='Active'
            ORDER BY s.grade, s.student_name, p.month_year
        """, conn), use_container_width=True)
    conn.close()

# ====================== REPORT CARDS ======================
elif menu == "Report Cards":
    st.header("📄 Report Cards")
    conn = get_conn()
    classes = allowed_classes() if st.session_state.user_role == "Teacher" else CLASS_LEVELS

    tab1, tab2 = st.tabs(["Single Student", "Whole Class / Level"])

    with tab1:
        grade = st.selectbox("Class Level", classes, key="rc1")
        students = pd.read_sql_query(
            "SELECT * FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
            conn, params=(grade,)
        )
        if not students.empty:
            name = st.selectbox("Student", students["student_name"].tolist())
            term = st.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="term1")
            student = students[students["student_name"] == name].iloc[0]
            grades_df = pd.read_sql_query(
                "SELECT * FROM grades WHERE student_id=? AND term=?",
                conn, params=(int(student["student_id"]), term)
            )

            if grades_df.empty:
                st.info("No grades recorded for this term")
            else:
                # Calculate rank
                all_students = pd.read_sql_query(
                    "SELECT student_id FROM students WHERE grade=? AND status='Active'", conn, params=(grade,)
                )
                averages = []
                for sid in all_students["student_id"]:
                    gdf = pd.read_sql_query("SELECT score, max_score FROM grades WHERE student_id=? AND term=?", conn, params=(int(sid), term))
                    if not gdf.empty:
                        avg = (gdf["score"] / gdf["max_score"] * 100).mean()
                        averages.append({"student_id": sid, "avg": avg})
                rank = "N/A"
                if averages:
                    adf = pd.DataFrame(averages).sort_values("avg", ascending=False).reset_index(drop=True)
                    for i, row in adf.iterrows():
                        if row["student_id"] == student["student_id"]:
                            rank = f"{i+1} out of {len(adf)}"
                            break

                st.write(f"**Rank in {grade}:** {rank}")
                st.dataframe(grades_df[["subject", "assessment_type", "score", "max_score"]], use_container_width=True)

                # Generate PDF
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('Title', parent=styles['Title'], alignment=TA_CENTER, textColor=colors.HexColor("#0B6E4F"))
                story = []

                if os.path.exists("logo.png"):
                    img = Image("logo.png", width=2.8*cm, height=2.8*cm)
                    img.hAlign = 'CENTER'
                    story.append(img)
                    story.append(Spacer(1, 8))

                story.append(Paragraph("IGISUBIZO ACADEMY", title_style))
                story.append(Paragraph(f"Official Report Card – {term}", styles['Heading2']))
                story.append(Spacer(1, 10))
                story.append(Paragraph(
                    f"<b>Student:</b> {student['student_name']}<br/>"
                    f"<b>Class:</b> {student['grade']}<br/>"
                    f"<b>Gender:</b> {student.get('gender', '—')}<br/>"
                    f"<b>Parent:</b> {student['parent_name']} ({student['parent_phone']})<br/>"
                    f"<b>Rank in Class:</b> {rank}<br/>"
                    f"<b>Date:</b> {datetime.date.today()}", styles['Normal']))
                story.append(Spacer(1, 12))

                data = [["Subject", "Assessment", "Score", "Max", "%"]]
                total_score = total_max = 0
                for _, r in grades_df.iterrows():
                    pct = (r["score"] / r["max_score"] * 100) if r["max_score"] else 0
                    data.append([r["subject"], r["assessment_type"], f"{r['score']:.1f}", f"{r['max_score']:.1f}", f"{pct:.1f}%"])
                    total_score += r["score"]
                    total_max += r["max_score"]
                overall = (total_score / total_max * 100) if total_max else 0
                data.append(["AVERAGE", "", f"{total_score:.1f}", f"{total_max:.1f}", f"{overall:.1f}%"])

                t = Table(data, colWidths=[120, 90, 60, 60, 60])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B6E4F")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
                ]))
                story.append(t)
                story.append(Spacer(1, 20))
                story.append(Paragraph("Head Administrator Signature: _______________________", styles['Normal']))
                doc.build(story)
                buffer.seek(0)

                st.download_button("⬇️ Download Report Card (PDF)", data=buffer,
                                   file_name=f"Report_{name.replace(' ', '_')}_{term}.pdf",
                                   mime="application/pdf")

    with tab2:
        st.subheader("Generate for Whole Class")
        st.info("Select a class and term. You can download report cards one by one from the list below (full batch download will be improved later).")
        grade2 = st.selectbox("Class Level", classes, key="rc2")
        term2 = st.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="term2")
        class_students = pd.read_sql_query(
            "SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
            conn, params=(grade2,)
        )
        st.write(f"Active students in {grade2}: {len(class_students)}")
        st.dataframe(class_students, use_container_width=True)

    conn.close()

# ====================== CODE OF CONDUCT ======================
elif menu == "Code of Conduct":
    st.header("📜 School Code of Conduct")
    st.markdown("""
    ### Igisubizo Academy – Code of Conduct

    **For Students:**
    - Respect teachers, staff and fellow students
    - Attend classes regularly and on time
    - Complete all homework and assignments
    - Wear the correct school uniform
    - No fighting, bullying or bad language
    - Take care of school property

    **For Teachers & Staff:**
    - Be professional and punctual
    - Prepare lessons properly
    - Treat all students fairly
    - Report any serious issues to Administration

    **Consequences:**
    - Warning → Conduct record → Parent meeting → Suspension
    """)

# ====================== PERMISSION & EMERGENCY ======================
elif menu == "Permission & Emergency":
    st.header("🚨 Permission & Emergency")
    tab1, tab2 = st.tabs(["Request Permission", "Report Emergency"])

    with tab1:
        with st.form("perm_form"):
            st.write("Protocol for requesting permission (student absence / late / outing)")
            student_name = st.text_input("Student Name")
            reason = st.selectbox("Reason", ["Medical", "Family", "Travel", "Other"])
            details = st.text_area("Details")
            if st.form_submit_button("Submit Permission Request"):
                conn = get_conn()
                conn.execute(
                    "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (?,?,?,?,?,?)",
                    (st.session_state.user_name, st.session_state.user_role, "Administration",
                     f"Permission Request - {student_name}", f"Reason: {reason}\n{details}", str(datetime.datetime.now()))
                )
                conn.commit()
                conn.close()
                st.success("Permission request sent to Administration")

    with tab2:
        with st.form("emerg_form"):
            st.write("Report any emergency immediately")
            emerg_type = st.selectbox("Type", ["Medical Emergency", "Safety Issue", "Behavioral Crisis", "Other"])
            details = st.text_area("What happened?")
            if st.form_submit_button("Submit Emergency Report"):
                conn = get_conn()
                conn.execute(
                    "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (?,?,?,?,?,?)",
                    (st.session_state.user_name, st.session_state.user_role, "Administration",
                     f"EMERGENCY - {emerg_type}", details, str(datetime.datetime.now()))
                )
                conn.commit()
                conn.close()
                st.success("Emergency report sent!")

# ====================== NOTIFICATIONS ======================
elif menu == "Notifications":
    st.header("🔔 Notifications")
    conn = get_conn()

    if st.session_state.user_role == "Administration":
        with st.form("notif_form"):
            title = st.text_input("Title")
            msg = st.text_area("Message to Teachers / Staff")
            if st.form_submit_button("Send Notification"):
                conn.execute(
                    "INSERT INTO notifications (title, message, created_by, created_at) VALUES (?,?,?,?)",
                    (title, msg, st.session_state.user_name, str(datetime.datetime.now()))
                )
                conn.commit()
                st.success("Notification sent")
                st.rerun()

    st.subheader("All Notifications")
    st.dataframe(pd.read_sql_query("SELECT * FROM notifications ORDER BY notif_id DESC", conn), use_container_width=True)
    conn.close()

# ====================== MESSAGES ======================
elif menu == "Messages":
    st.header("💬 Messages")
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

# ====================== REMOVED RECORDS ======================
elif menu == "Removed Records":
    st.header("🗑️ Removed / Inactive Records")
    conn = get_conn()
    st.subheader("Inactive Students")
    st.dataframe(pd.read_sql_query("SELECT * FROM students WHERE status='Inactive'", conn), use_container_width=True)
    st.subheader("Inactive Staff")
    st.dataframe(pd.read_sql_query("SELECT * FROM staff WHERE status='Inactive'", conn), use_container_width=True)
    conn.close()
