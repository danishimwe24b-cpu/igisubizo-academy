import streamlit as st
import pandas as pd
import psycopg2

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
for year in range(2026, 2031):

    start = 11 if year == 2026 else 1
    for m in range(start, 13):
        PAYMENT_MONTHS.append(f"{year}-{m:02d}")

PAYMENT_STATUS = ["Paid", "Not paid", "Late 5 days", "Late 5-10 days", "Late 15 days", "Bonus", "Drop out"]
MONTHLY_FEE = 5000

# ====================== DATABASE (NEON POSTGRESQL) ======================
def get_db_url():
    url = st.secrets.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        st.error("Missing DATABASE_URL in Streamlit Secrets or Environment Variables.")
        st.stop()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "&channel_binding=require" in url:
        url = url.replace("&channel_binding=require", "")
    return url


class NeonConnWrapper:
    """Wraps a fresh psycopg2 connection so existing .execute() calls work cleanly."""
    def __init__(self):
        self.raw = psycopg2.connect(get_db_url())

    def cursor(self):
        if self.raw.closed:
            self.raw = psycopg2.connect(get_db_url())
        return self.raw.cursor()

    def execute(self, sql, params=None):
        cur = self.cursor()
        sql_pg = sql.replace("?", "%s")
        if params is not None:
            cur.execute(sql_pg, params)
        else:
            cur.execute(sql_pg)
        return cur

    def commit(self):
        if not self.raw.closed:
            self.raw.commit()

    def close(self):
        if not self.raw.closed:
            self.raw.close()


def get_conn():
    return NeonConnWrapper()


def read_sql(query, params=None):
    """Reads data directly using a fresh psycopg2 connection."""
    conn = psycopg2.connect(get_db_url())
    try:
        sql_pg = query.replace("?", "%s")
        return pd.read_sql_query(sql_pg, conn, params=params)
    finally:
        conn.close()


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            staff_id SERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            assigned_classes TEXT,
            assigned_subjects TEXT,
            status TEXT DEFAULT 'Active'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id SERIAL PRIMARY KEY,
            student_name TEXT NOT NULL,
            gender TEXT,
            dob TEXT,
            grade TEXT NOT NULL,
            parent_name TEXT,
            parent_phone TEXT,
            address TEXT,
            enrollment_date TEXT,
            status TEXT DEFAULT 'Active'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            grade_id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(student_id),
            subject TEXT,
            term TEXT,
            exam_type TEXT,
            score REAL,
            max_score REAL DEFAULT 100,
            teacher TEXT,
            date_recorded TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(student_id),
            date TEXT,
            status TEXT,
            teacher TEXT,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS teacher_attendance (
            attendance_id SERIAL PRIMARY KEY,
            teacher_name VARCHAR(150) NOT NULL,
            date DATE NOT NULL,
            arrival_time TIME,
            departure_time TIME,
            status VARCHAR(30) NOT NULL,
            notes TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (teacher_name, date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS lesson_reports (
            report_id SERIAL PRIMARY KEY,
            teacher_name VARCHAR(150) NOT NULL,
            grade VARCHAR(50) NOT NULL,
            subject VARCHAR(100) NOT NULL,
            lesson_date DATE NOT NULL,
            lesson_topic VARCHAR(255) NOT NULL,
            learning_objectives TEXT NOT NULL,
            lesson_activities TEXT,
            exercises_given TEXT,
            homework TEXT,
            objective_achieved VARCHAR(50) NOT NULL,
            overall_comment TEXT,
            challenges TEXT,
            next_steps TEXT,
            prepared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (teacher_name, grade, subject, lesson_date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(student_id),
            amount REAL,
            payment_type TEXT,
            term TEXT,
            payment_date TEXT,
            receipt_no TEXT,
            recorded_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conduct (
            conduct_id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(student_id),
            date TEXT,
            incident_type TEXT,
            description TEXT,
            action_taken TEXT,
            reported_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            perm_id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students(student_id),
            date TEXT,
            type TEXT,
            reason TEXT,
            status TEXT,
            approved_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            msg_id SERIAL PRIMARY KEY,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            body TEXT,
            sent_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notif_id SERIAL PRIMARY KEY,
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
    
# ====================== PAGE SETUP ======================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

init_db()

# Custom CSS
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
                df = read_sql(
                    "SELECT * FROM staff WHERE LOWER(username)=%s AND password=%s AND role=%s AND status='Active'",
                    params=(uname.lower(), pwd, role)
                )
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


# ====================== HELPERS ======================
def allowed_classes():
    if st.session_state.assigned_classes == "ALL":
        return CLASS_LEVELS
    return [x.strip() for x in st.session_state.assigned_classes.split(",") if x.strip()]


def allowed_subjects():
    if st.session_state.assigned_subjects == "ALL":
        return SUBJECT_LIST
    return [x.strip() for x in st.session_state.assigned_subjects.split(",") if x.strip()]


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

if "menu" not in locals():
    menu = "Dashboard"

if menu == "Dashboard":
    st.markdown("<div class='main-header'><h2>📊 Administration Dashboard</h2></div>", unsafe_allow_html=True)

    active_students = read_sql("SELECT COUNT(*) as c FROM students WHERE status='Active'").iloc[0]["c"]
    inactive_students = read_sql("SELECT COUNT(*) as c FROM students WHERE status='Inactive'").iloc[0]["c"]
    total_paid = read_sql("SELECT COALESCE(SUM(amount),0) as t FROM payments WHERE status='Paid'").iloc[0]["t"]
    active_staff = read_sql("SELECT COUNT(*) as c FROM staff WHERE status='Active'").iloc[0]["c"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Students", active_students)
    c2.metric("Inactive Students", inactive_students)
    c3.metric("Fees Collected", f"{total_paid:,.0f} RWF")
    c4.metric("Active Staff", active_staff)

    st.subheader("Students per Class Level")
    df = read_sql("SELECT grade, COUNT(*) as total FROM students WHERE status='Active' GROUP BY grade")
    if not df.empty:
        st.bar_chart(df.set_index("grade"))
    else:
        st.info("No active students yet")

    st.subheader("Recent Payments")
    st.dataframe(read_sql("""
        SELECT s.student_name, s.grade, p.month_year, p.amount, p.status, p.paid_date
        FROM payments p JOIN students s ON p.student_id = s.student_id
        ORDER BY p.payment_id DESC LIMIT 15
    """), use_container_width=True)

# ====================== STUDENTS ======================
elif menu == "Students":
    st.header("👥 Students Management")
    conn = get_conn()
    tab1, tab2, tab3, tab4 = st.tabs(["Active Students", "Add Student", "Edit Student", "Change Status"])

    with tab1:
        grade = st.selectbox("Filter by Class Level", ["All"] + CLASS_LEVELS, key="stu_filter_grade")
        if grade == "All":
            df = read_sql(
                "SELECT student_id, student_name, grade, gender, parent_name, parent_phone, parent_email, status FROM students WHERE status='Active' ORDER BY grade, student_name"
            )
        else:
            df = read_sql(
                "SELECT student_id, student_name, grade, gender, parent_name, parent_phone, parent_email, status FROM students WHERE grade=%s AND status='Active' ORDER BY student_name",
                params=(grade,)
            )
        st.dataframe(df, use_container_width=True)

    with tab2:
        with st.form("add_student_form", clear_on_submit=True):
            name = st.text_input("Student Full Name *")
            col1, col2 = st.columns(2)
            g = col1.selectbox("Class Level", CLASS_LEVELS)
            gender = col2.selectbox("Gender", ["Male", "Female"])
            pname = st.text_input("Parent / Guardian Name")
            phone = st.text_input("Parent Phone")
            email = st.text_input("Parent Email")
            if st.form_submit_button("💾 Save Student"):
                if name.strip():
                    conn.execute(
                        "INSERT INTO students (student_name, grade, gender, parent_name, parent_phone, parent_email, status, created_at) VALUES (%s,%s,%s,%s,%s,%s,'Active',%s)",
                        (name.strip(), g, gender, pname.strip(), phone.strip(), email.strip(), str(datetime.date.today()))
                    )
                    conn.commit()
                    st.success(f"Student **{name.strip()}** added successfully!")
                    st.rerun()
                else:
                    st.error("Student Full Name is required.")

    with tab3:
        st.subheader("✏️ Edit Student Information")
        all_students = read_sql("SELECT * FROM students ORDER BY grade, student_name")
        if all_students.empty:
            st.info("No students available to edit.")
        else:
            student_ids = all_students["student_id"].tolist()
            student_labels = {
                int(r["student_id"]): f"ID #{r['student_id']} - {r['student_name']} ({r['grade']})"
                for _, r in all_students.iterrows()
            }
            selected_sid = st.selectbox(
                "Select Student to Edit",
                student_ids,
                format_func=lambda x: student_labels[x],
                key="edit_stu_selector"
            )
            stu = all_students[all_students["student_id"] == selected_sid].iloc[0]

            with st.form(key=f"edit_student_form_{selected_sid}"):
                new_name = st.text_input("Student Full Name *", value=str(stu["student_name"] or ""))
                c1, c2 = st.columns(2)
                curr_grade = str(stu["grade"])
                new_grade = c1.selectbox(
                    "Class Level",
                    CLASS_LEVELS,
                    index=CLASS_LEVELS.index(curr_grade) if curr_grade in CLASS_LEVELS else 0
                )
                gender_opts = ["Male", "Female"]
                curr_gender = str(stu["gender"])
                new_gender = c2.selectbox(
                    "Gender",
                    gender_opts,
                    index=gender_opts.index(curr_gender) if curr_gender in gender_opts else 0
                )
                new_pname = st.text_input("Parent / Guardian Name", value=str(stu["parent_name"] or ""))
                new_phone = st.text_input("Parent Phone", value=str(stu["parent_phone"] or ""))
                new_email = st.text_input("Parent Email", value=str(stu["parent_email"] or ""))

                if st.form_submit_button("💾 Update Student Information", use_container_width=True):
                    if new_name.strip():
                        conn.execute("""
                            UPDATE students
                            SET student_name=%s, grade=%s, gender=%s, parent_name=%s, parent_phone=%s, parent_email=%s
                            WHERE student_id=%s
                        """, (
                            new_name.strip(), new_grade, new_gender,
                            new_pname.strip(), new_phone.strip(), new_email.strip(),
                            int(selected_sid)
                        ))
                        conn.commit()
                        st.success(f"Updated **{new_name.strip()}** successfully!")
                        st.rerun()
                    else:
                        st.error("Student Full Name cannot be empty.")

    with tab4:
        df = read_sql("SELECT student_id, student_name, grade, status FROM students ORDER BY grade, student_name")
        st.dataframe(df, use_container_width=True)
        sid = st.number_input("Student ID", min_value=1, step=1, key="status_stu_id")
        new_status = st.selectbox("New Status", ["Active", "Inactive"], key="status_stu_val")
        if st.button("Update Status"):
            conn.execute("UPDATE students SET status=%s WHERE student_id=%s", (new_status, int(sid)))
            conn.commit()
            st.success("Status updated – Inactive students are removed from active lists")
            st.rerun()
    conn.close()

# ====================== STAFF ======================
elif menu == "Staff & Teachers":
    st.header("👨‍🏫 Staff & Teachers")
    conn = get_conn()
    tab1, tab2, tab3, tab4 = st.tabs([
        "Create Account", "Edit Staff / Teacher", "Assign Classes & Subjects", "Manage Accounts"
    ])

    with tab1:
        with st.form("create_staff_form", clear_on_submit=True):
            name = st.text_input("Full Name *")
            role = st.selectbox("Role", ["Teacher", "Register Officer", "Administration"])
            uname = st.text_input("Username *")
            pwd = st.text_input("Temporary Password", value="123456")
            phone = st.text_input("Phone")
            classes = st.multiselect("Assigned Classes (Teachers)", CLASS_LEVELS)
            subjects = st.multiselect("Assigned Subjects (Teachers)", SUBJECT_LIST)
            if st.form_submit_button("Create Account"):
                if name.strip() and uname.strip():
                    cls = ",".join(classes) if classes else "ALL"
                    sub = ",".join(subjects) if subjects else "ALL"
                    try:
                        conn.execute(
                            "INSERT INTO staff (full_name, role, username, password, phone, assigned_classes, assigned_subjects, status) VALUES (%s,%s,%s,%s,%s,%s,%s,'Active')",
                            (name.strip(), role, uname.strip(), pwd.strip(), phone.strip(), cls, sub)
                        )
                        conn.commit()
                        st.success(f"Account created → Username: `{uname.strip()}` | Password: `{pwd.strip()}`")
                        st.rerun()
                    except psycopg2.IntegrityError:
                        conn.raw.rollback()
                        st.error("Username already exists.")
                else:
                    st.error("Full Name and Username are required.")

    with tab2:
        st.subheader("✏️ Edit Staff / Teacher Details")
        staff_df = read_sql("SELECT * FROM staff ORDER BY full_name")
        if staff_df.empty:
            st.info("No staff accounts found.")
        else:
            staff_ids = staff_df["staff_id"].tolist()
            staff_labels = {
                int(r["staff_id"]): f"ID #{r['staff_id']} - {r['full_name']} (@{r['username']} | {r['role']})"
                for _, r in staff_df.iterrows()
            }
            selected_staff_id = st.selectbox(
                "Select Staff Member to Edit",
                staff_ids,
                format_func=lambda x: staff_labels[x],
                key="edit_staff_selector"
            )
            stf = next(iter(staff_df[staff_df["staff_id"] == selected_staff_id].to_dict("records")))

            with st.form(key=f"edit_staff_form_{selected_staff_id}"):
                ed_name = st.text_input("Full Name *", value=str(stf["full_name"] or ""))
                role_opts = ["Teacher", "Register Officer", "Administration"]
                curr_role = str(stf["role"])
                ed_role = st.selectbox(
                    "Role",
                    role_opts,
                    index=role_opts.index(curr_role) if curr_role in role_opts else 0
                )
                ed_uname = st.text_input("Username *", value=str(stf["username"] or ""))
                ed_phone = st.text_input("Phone", value=str(stf["phone"] or ""))

                curr_cls = [c.strip() for c in str(stf["assigned_classes"] or "").split(",") if c.strip() in CLASS_LEVELS]
                curr_sub = [s.strip() for s in str(stf["assigned_subjects"] or "").split(",") if s.strip() in SUBJECT_LIST]

                ed_classes = st.multiselect("Assigned Classes", CLASS_LEVELS, default=curr_cls)
                ed_subjects = st.multiselect("Assigned Subjects", SUBJECT_LIST, default=curr_sub)

                if st.form_submit_button("💾 Update Staff Details", use_container_width=True):
                    if ed_name.strip() and ed_uname.strip():
                        cls_val = ",".join(ed_classes) if ed_classes else "ALL"
                        sub_val = ",".join(ed_subjects) if ed_subjects else "ALL"
                        try:
                            conn.execute("""
                                UPDATE staff
                                SET full_name=%s, role=%s, username=%s, phone=%s, assigned_classes=%s, assigned_subjects=%s
                                WHERE staff_id=%s
                            """, (
                                ed_name.strip(), ed_role, ed_uname.strip(), ed_phone.strip(),
                                cls_val, sub_val, int(selected_staff_id)
                            ))
                            conn.commit()
                            st.success(f"Updated **{ed_name.strip()}** successfully!")
                            st.rerun()
                        except psycopg2.IntegrityError:
                            conn.raw.rollback()
                            st.error("That username is already taken by another account.")
                    else:
                        st.error("Full Name and Username cannot be empty.")

    with tab3:
        tdf = read_sql("SELECT username, full_name, assigned_classes, assigned_subjects FROM staff WHERE role='Teacher' AND status='Active'")
        st.dataframe(tdf, use_container_width=True)
        if not tdf.empty:
            sel = st.selectbox("Select Teacher", tdf["username"].tolist(), key="assign_teacher_sel")
            new_cls = st.multiselect("Classes", CLASS_LEVELS, key="assign_cls")
            new_sub = st.multiselect("Subjects", SUBJECT_LIST, key="assign_sub")
            if st.button("Update Assignment"):
                conn.execute("UPDATE staff SET assigned_classes=%s, assigned_subjects=%s WHERE username=%s",
                             (",".join(new_cls) if new_cls else "NONE", ",".join(new_sub) if new_sub else "NONE", sel))
                conn.commit()
                st.success("Updated")
                st.rerun()

    with tab4:
        sdf = read_sql("SELECT staff_id, full_name, role, username, status FROM staff")
        st.dataframe(sdf, use_container_width=True)
        sid = st.number_input("Staff ID", min_value=1, step=1, key="manage_staff_id")
        new_pwd = st.text_input("New Password", value="123456", key="manage_staff_pwd")
        new_stat = st.selectbox("Status", ["Active", "Inactive"], key="manage_staff_stat")
        c1, c2 = st.columns(2)
        if c1.button("Update Password & Status"):
            conn.execute("UPDATE staff SET password=%s, status=%s WHERE staff_id=%s", (new_pwd, new_stat, int(sid)))
            conn.commit()
            st.success("Updated")
            st.rerun()
        if c2.button("Delete Inactive Staff"):
            conn.execute("DELETE FROM staff WHERE staff_id=%s AND status='Inactive'", (int(sid),))
            conn.commit()
            st.success("Deleted if inactive")
            st.rerun()
    conn.close()

# ====================== GRADES ======================
elif menu == "Grades":
    st.header("📝 Grades, Totals & P1–P3 Language Skills")
    conn = get_conn()
    classes = allowed_classes()
    subjects = allowed_subjects()

    tab1, tab2, tab3 = st.tabs([
        "Record Assessment Scores",
        "P1–P3 Speaking, Reading & Writing",
        "Student Auto-Totals & Progress"
    ])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        sel_class = c1.selectbox("Class Level", classes, key="gr_class")
        sel_subj = c2.selectbox("Subject", subjects, key="gr_subj")
        sel_term = c3.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="gr_term")
        sel_type = c4.selectbox("Assessment Type", ASSESSMENT_TYPES, key="gr_type")

        col_m, col_d = st.columns(2)
        max_score = col_m.number_input("Out Of (Maximum Marks)", min_value=1.0, value=20.0, step=1.0, key="gr_max")
        assess_date = col_d.date_input("Assessment Date", value=datetime.date.today(), key="gr_date")

        students = read_sql(
            "SELECT student_id, student_name FROM students WHERE grade=%s AND status='Active' ORDER BY student_name",
            params=(sel_class,)
        )

        if students.empty:
            st.warning("No active students in this class.")
        else:
            with st.form(key=f"grades_entry_{sel_class}_{sel_subj}_{sel_term}"):
                st.write(f"Enter marks out of **{max_score:.0f}** for **{sel_class} — {sel_subj} ({sel_type})**")
                entries = []
                for _, row in students.iterrows():
                    sid = int(row["student_id"])
                    sc1, sc2 = st.columns([3, 2])
                    sc1.write(f"**{row['student_name']}**")
                    val = sc2.number_input(
                        f"Score / {max_score:.0f}",
                        min_value=0.0,
                        max_value=float(max_score),
                        value=0.0,
                        step=0.5,
                        key=f"sc_{sid}_{sel_subj}_{sel_type}",
                        label_visibility="collapsed"
                    )
                    entries.append((sid, val))

                if st.form_submit_button("💾 Save All Assessment Scores", use_container_width=True):
                    cur = conn.cursor()
                    for sid, val in entries:
                        cur.execute("""
                            INSERT INTO grades (student_id, subject, assessment_type, score, max_score, term, date, teacher)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (sid, sel_subj, sel_type, val, max_score, sel_term, str(assess_date), st.session_state.user_name))
                    conn.commit()
                    st.success(f"Saved {len(entries)} scores ({sel_subj} - {sel_type})! Totals updated automatically.")
                    st.rerun()

    with tab2:
        st.subheader("🗣️ P1, P2 & P3 Language Skills (Speaking, Reading & Writing)")
        lower_classes = [c for c in classes if c.startswith(("P1", "P2", "P3"))]
        if not lower_classes:
            st.info("This tab applies to P1, P2, and P3 classes.")
        else:
            lc1, lc2, lc3 = st.columns(3)
            l_class = lc1.selectbox("Select P1–P3 Class", lower_classes, key="lang_cls")
            l_term = lc2.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="lang_term")
            l_lang = lc3.selectbox("Language", ["English", "Kinyarwanda"], key="lang_choice")

            l_students = read_sql(
                "SELECT student_id, student_name FROM students WHERE grade=%s AND status='Active' ORDER BY student_name",
                params=(l_class,)
            )
            skill_levels = ["Excellent", "Very Good", "Good", "Needs Improvement"]

            if l_students.empty:
                st.warning("No active students in this class.")
            else:
                with st.form(key=f"lang_skills_{l_class}_{l_term}_{l_lang}"):
                    skill_rows = []
                    for _, srow in l_students.iterrows():
                        sid = int(srow["student_id"])
                        c_name, c_sp, c_rd, c_wr = st.columns([2.5, 1.5, 1.5, 1.5])
                        c_name.write(f"**{srow['student_name']}**")
                        sp = c_sp.selectbox("Speaking", skill_levels, key=f"sp_{sid}_{l_lang}_{l_term}")
                        rd = c_rd.selectbox("Reading", skill_levels, key=f"rd_{sid}_{l_lang}_{l_term}")
                        wr = c_wr.selectbox("Writing", skill_levels, key=f"wr_{sid}_{l_lang}_{l_term}")
                        skill_rows.append((sid, sp, rd, wr))

                    if st.form_submit_button("💾 Save Language Skills", use_container_width=True):
                        cur = conn.cursor()
                        for sid, sp, rd, wr in skill_rows:
                            cur.execute("""
                                INSERT INTO language_skills (student_id, term, language, speaking, reading, writing, teacher)
                                VALUES (%s,%s,%s,%s,%s,%s,%s)
                                ON CONFLICT(student_id, term, language)
                                DO UPDATE SET speaking=EXCLUDED.speaking, reading=EXCLUDED.reading, writing=EXCLUDED.writing, teacher=EXCLUDED.teacher
                            """, (sid, l_term, l_lang, sp, rd, wr, st.session_state.user_name))
                        conn.commit()
                        st.success(f"Saved {l_lang} skills for {l_class} ({l_term})!")
                        st.rerun()

    with tab3:
        st.subheader("📊 Automatic Subject Totals & Student Progress")
        p_c1, p_c2 = st.columns(2)
        p_class = p_c1.selectbox("Class", classes, key="tot_cls")
        p_term = p_c2.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="tot_term")

        p_students = read_sql(
            "SELECT student_id, student_name FROM students WHERE grade=%s AND status='Active' ORDER BY student_name",
            params=(p_class,)
        )
        if not p_students.empty:
            sel_p_stu = st.selectbox("Select Student", p_students["student_name"].tolist(), key="tot_stu")
            psid = int(p_students[p_students["student_name"] == sel_p_stu].iloc[0]["student_id"])

            tot_df = read_sql("""
                SELECT subject AS "Subject",
                       COUNT(*) AS "Assessments",
                       SUM(score) AS "Total_Score",
                       SUM(max_score) AS "Total_Out_Of",
                       ROUND((SUM(score) * 100.0 / SUM(max_score))::numeric, 1) AS "Percentage"
                FROM grades
                WHERE student_id=%s AND term=%s
                GROUP BY subject
            """, params=(psid, p_term))

            if tot_df.empty:
                st.info("No assessments recorded yet for this student in this term.")
            else:
                tot_df["Result"] = tot_df.apply(lambda r: f"{r['Total_Score']:.1f} / {r['Total_Out_Of']:.1f}", axis=1)
                st.dataframe(tot_df[["Subject", "Assessments", "Result", "Percentage"]], use_container_width=True)

                raw_prog = read_sql("""
                    SELECT date, subject, ROUND((score * 100.0 / max_score)::numeric, 1) AS pct
                    FROM grades WHERE student_id=%s AND term=%s ORDER BY date ASC
                """, params=(psid, p_term))
                st.line_chart(raw_prog.pivot_table(index="date", columns="subject", values="pct", aggfunc="mean"))
    conn.close()
    # ====================== ATTENDANCE & LESSON REPORT ======================
elif menu == "Attendance":
    st.header("📅 Daily Attendance & Lesson Preparation")
    conn = get_conn()
    classes = allowed_classes()
    teacher_name = st.session_state.user_name

    # Shared Class & Date selectors at the top
    col1, col2 = st.columns(2)
    sel_class = col1.selectbox("Select Class", classes, key="att_class")
    att_date = col2.date_input("Date", value=datetime.date.today(), key="att_date")
    date_str = str(att_date)

    # Organize into 3 clean tabs
    tab_students, tab_teacher, tab_lesson = st.tabs([
        "👨‍🎓 Student Attendance",
        "👩‍🏫 Teacher Attendance",
        "📘 Lesson Preparation & Report"
    ])

    # -------------------- TAB 1: STUDENT ATTENDANCE --------------------
    with tab_students:
        students = read_sql(
            "SELECT student_id, student_name FROM students WHERE grade=%s AND status='Active' ORDER BY student_name",
            params=(sel_class,)
        )

        if students.empty:
            st.warning("No active students in this class.")
        else:
            existing_df = read_sql(
                "SELECT student_id, status, notes FROM attendance WHERE date=%s ORDER BY attendance_id ASC",
                params=(date_str,)
            ).drop_duplicates(subset=["student_id"], keep="last")
            existing = existing_df.set_index("student_id").to_dict("index")

            with st.form("attendance_form"):
                st.write(f"Recording student attendance for **{sel_class}** on **{date_str}**")
                records = []
                for _, row in students.iterrows():
                    sid = int(row["student_id"])
                    prev_status = existing.get(sid, {}).get("status", "Present")
                    prev_notes = existing.get(sid, {}).get("notes", "")

                    c1, c2, c3 = st.columns([2, 1.5, 2.5])
                    c1.write(f"**{row['student_name']}**")
                    status_opts = ["Present", "Absent", "Late", "Excused"]
                    status = c2.selectbox(
                        "Status",
                        status_opts,
                        index=status_opts.index(prev_status) if prev_status in status_opts else 0,
                        key=f"att_st_{sid}_{date_str}",
                        label_visibility="collapsed"
                    )
                    notes = c3.text_input(
                        "Notes",
                        value=prev_notes or "",
                        placeholder="Optional note...",
                        key=f"att_nt_{sid}_{date_str}",
                        label_visibility="collapsed"
                    )
                    records.append((sid, status, notes))

                if st.form_submit_button("💾 Save Student Attendance", use_container_width=True):
                    c = conn.cursor()
                    for sid, status, notes in records:
                        c.execute(
                            "SELECT attendance_id FROM attendance WHERE student_id=%s AND date=%s ORDER BY attendance_id ASC",
                            (sid, date_str)
                        )
                        rows = c.fetchall()
                        if rows:
                            keep_id = rows[-1][0]
                            if len(rows) > 1:
                                c.execute(
                                    "DELETE FROM attendance WHERE student_id=%s AND date=%s AND attendance_id != %s",
                                    (sid, date_str, keep_id)
                                )
                            c.execute(
                                "UPDATE attendance SET status=%s, notes=%s, teacher=%s WHERE attendance_id=%s",
                                (status, notes, teacher_name, keep_id)
                            )
                        else:
                            c.execute(
                                "INSERT INTO attendance (student_id, date, status, teacher, notes) VALUES (%s,%s,%s,%s,%s)",
                                (sid, date_str, status, teacher_name, notes)
                            )
                    conn.commit()
                    st.success(f"Attendance saved for {len(records)} students on {date_str}!")
                    st.rerun()

            st.subheader("Student Attendance History")
            hist = read_sql("""
                SELECT a.date, s.student_name, a.status, a.notes, a.teacher
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE s.grade = %s
                ORDER BY a.date DESC, s.student_name
            """, params=(sel_class,))
            st.dataframe(hist, use_container_width=True)

    # -------------------- TAB 2: TEACHER ATTENDANCE --------------------
    with tab_teacher:
        st.subheader(f"Teacher Attendance — {teacher_name}")
        t_existing = read_sql(
            "SELECT arrival_time, departure_time, status, notes FROM teacher_attendance WHERE teacher_name=%s AND date=%s",
            params=(teacher_name, date_str)
        )

        default_status = "Present"
        default_arr = datetime.time(8, 0)
        default_dep = datetime.time(16, 0)
        default_notes = ""

        if not t_existing.empty:
            row_t = t_existing.iloc[0]
            default_status = row_t["status"] or "Present"
            if row_t["arrival_time"]:
                default_arr = row_t["arrival_time"]
            if row_t["departure_time"]:
                default_dep = row_t["departure_time"]
            default_notes = row_t["notes"] or ""

        with st.form("teacher_attendance_form"):
            tc1, tc2, tc3 = st.columns(3)
            t_status_opts = ["Present", "Late", "Absent", "Excused / On Leave"]
            t_status = tc1.selectbox(
                "Attendance Status",
                t_status_opts,
                index=t_status_opts.index(default_status) if default_status in t_status_opts else 0
            )
            arr_time = tc2.time_input("Arrival Time", value=default_arr)
            dep_time = tc3.time_input("Departure Time", value=default_dep)
            t_notes = st.text_area(
                "Remarks / Reason (if late or absent)",
                value=default_notes,
                placeholder="Optional notes..."
            )

            if st.form_submit_button("💾 Save Teacher Attendance", use_container_width=True):
                c = conn.cursor()
                c.execute("""
                    INSERT INTO teacher_attendance (teacher_name, date, arrival_time, departure_time, status, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (teacher_name, date)
                    DO UPDATE SET
                        arrival_time = EXCLUDED.arrival_time,
                        departure_time = EXCLUDED.departure_time,
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes,
                        recorded_at = CURRENT_TIMESTAMP
                """, (teacher_name, date_str, arr_time, dep_time, t_status, t_notes.strip()))
                conn.commit()
                st.success(f"Teacher attendance recorded for {date_str}!")
                st.rerun()

        st.subheader("My Attendance Log")
        t_hist = read_sql("""
            SELECT date, status, arrival_time, departure_time, notes
            FROM teacher_attendance
            WHERE teacher_name = %s
            ORDER BY date DESC
        """, params=(teacher_name,))
        st.dataframe(t_hist, use_container_width=True)

    # -------------------- TAB 3: LESSON PREPARATION & REPORT --------------------
    with tab_lesson:
        st.subheader(f"Lesson Preparation & Evaluation ({sel_class} — {date_str})")

        with st.form("lesson_prep_form"):
            lc1, lc2 = st.columns(2)
            subject = lc1.text_input("Subject *", placeholder="e.g., Mathematics, Science, English")
            lesson_topic = lc2.text_input("Lesson Topic *", placeholder="e.g., Solving Linear Equations")

            learning_objectives = st.text_area(
                "🎯 Learning Objectives *",
                placeholder="What should students know or be able to do by the end of this lesson?"
            )
            lesson_activities = st.text_area(
                "📝 Teaching & Learning Activities",
                placeholder="Briefly describe the introduction, main teaching steps, and student activities..."
            )

            ex1, ex2 = st.columns(2)
            exercises_given = ex1.text_area(
                "✍️ Class Exercises Given",
                placeholder="List the exercises, page numbers, or questions assigned during class..."
            )
            homework = ex2.text_area(
                "🏠 Homework / Take-Home Assignment",
                placeholder="Optional homework or follow-up practice..."
            )

            st.markdown("---")
            st.markdown("### 📊 Post-Lesson Evaluation")

            achieved_opts = ["Yes - Fully Achieved", "Partially Achieved", "No - Needs Reteaching"]
            objective_achieved = st.selectbox("Was the learning objective achieved?", achieved_opts)

            overall_comment = st.text_area(
                "💬 Overall Comment on Objective Achievement *",
                placeholder="Summarize student understanding, participation, and how well the objective was met..."
            )

            ev1, ev2 = st.columns(2)
            challenges = ev1.text_area(
                "⚠️ Challenges / Students Needing Support",
                placeholder="Any concepts students struggled with or specific students needing extra help..."
            )
            next_steps = ev2.text_area(
                "➡️ Next Steps for Next Lesson",
                placeholder="Plan for the next class based on today's outcome..."
            )

# ====================== PAYMENTS ======================
# ====================== PAYMENTS ======================
elif menu == "Payments":
    st.header("💳 School Fees, Petty Cash Expenses & Monthly Budget")
    conn = get_conn()

    # Ensure expenses and monthly_budgets tables exist in Neon PostgreSQL
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            expense_id SERIAL PRIMARY KEY,
            month_year TEXT NOT NULL,
            budget_line TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            expense_date TEXT,
            recorded_by TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            budget_id SERIAL PRIMARY KEY,
            month_year TEXT NOT NULL,
            budget_line TEXT NOT NULL,
            planned_amount REAL NOT NULL DEFAULT 0,
            notes TEXT,
            updated_by TEXT,
            UNIQUE(month_year, budget_line)
        )
    """)
    conn.commit()

    BUDGET_LINES = [
        "001. Graduation",
        "002. Students rewards",
        "003. Students motivation",
        "004. Printer ink",
        "005. Ream of paper",
        "006. Salary for safe walker",
        "007. Salaries for the teacher",
        "008. Salaries for the cleaner & security",
        "009. Savings",
        "010. Books",
        "011. Printing",
        "012. Cost of service",
        "013. Electricity",
        "014. Internet",
        "015. Transport",
        "016. Founders Share",
        "017. Withdrawal Cost",
        "018. Purchase of materials",
        "019. Chalks",
        "020. Rent",
        "021. Professional cost",
        "022. Connections",
        "023. Bulbs",
        "024. Cleaning materials",
        "025. Renovations"
    ]

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Record Payment",
        "Payment Records",
        "Update Payment Status",
        "💸 Petty Cash & Monthly Expenses",
        "📊 Monthly Budget & Summary"
    ])
# -------------------- TAB 1: RECORD STUDENT PAYMENT --------------------
    with tab1:
        sel_class = st.selectbox("Select Class", CLASS_LEVELS, key="pay_class")
        students = read_sql(
            "SELECT student_id, student_name FROM students WHERE grade=%s AND status='Active' ORDER BY student_name",
            params=(sel_class,)
        )

        if students.empty:
            st.warning("No active students in this class.")
        else:
            student_dict = {
                f"{row['student_name']} (ID #{row['student_id']})": int(row["student_id"])
                for _, row in students.iterrows()
            }
            sel_student_label = st.selectbox("Select Student", list(student_dict.keys()), key="pay_student")
            sid = student_dict[sel_student_label]

            paid_months_df = read_sql(
                "SELECT month_year, amount, status, paid_date FROM payments WHERE student_id=%s ORDER BY month_year ASC",
                params=(sid,)
            )
            if not paid_months_df.empty:
                recorded_list = [
                    f"{r['month_year']} ({r['status']})" for _, r in paid_months_df.iterrows()
                ]
                st.info(f"**Already recorded for {sel_student_label}:** " + ", ".join(recorded_list))

            with st.form("payment_form"):
                col1, col2 = st.columns(2)
                month_year = col1.selectbox("Select Month (Current or Future)", PAYMENT_MONTHS)
                amount = col2.number_input("Amount (RWF)", min_value=0, value=MONTHLY_FEE, step=500)

                col3, col4 = st.columns(2)
                status = col3.selectbox("Payment Status", PAYMENT_STATUS)
                paid_date = col4.date_input("Payment Date", value=datetime.date.today())

                if st.form_submit_button("💾 Record Payment", use_container_width=True):
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT payment_id, status FROM payments WHERE student_id=%s AND month_year=%s",
                        (sid, month_year)
                    )
                    existing_pay = cur.fetchone()

                    if existing_pay:
                        st.error(
                            f"⚠️ **{sel_student_label}** is already recorded for **{month_year}** "
                            f"(Status: **{existing_pay[1]}**). Only one record per student per month is allowed."
                        )
                    else:
                        try:
                            cur.execute("""
                                INSERT INTO payments (student_id, month_year, amount, status, paid_date, recorded_by)
                                VALUES (%s,%s,%s,%s,%s,%s)
                            """, (sid, month_year, amount, status, str(paid_date), st.session_state.user_name))
                            conn.commit()
                            st.success(f"Payment recorded for **{sel_student_label}** for **{month_year}**!")
                            st.rerun()
                        except psycopg2.IntegrityError:
                            conn.raw.rollback()
                            st.error(f"⚠️ Duplicate blocked: **{sel_student_label}** already has a payment for **{month_year}**.")
# -------------------- TAB 2: PAYMENT RECORDS --------------------
with tab2:
        c1, c2 = st.columns(2)
        filter_month = c1.selectbox("Filter by Month", ["All"] + PAYMENT_MONTHS, key="filter_pay_month")
        filter_status = c2.selectbox("Filter by Status", ["All"] + PAYMENT_STATUS, key="filter_pay_status")

        query = """
            SELECT p.payment_id, s.student_name, s.grade, p.month_year, p.amount, p.status, p.paid_date, p.recorded_by
            FROM payments p
            JOIN students s ON p.student_id = s.student_id
            WHERE 1=1
        """
        params = []
        if filter_month != "All":
            query += " AND p.month_year = %s"
            params.append(filter_month)
        if filter_status != "All":
            query += " AND p.status = %s"
            params.append(filter_status)

        query += " ORDER BY p.month_year DESC, s.grade, s.student_name"
        pay_df = read_sql(query, params=params if params else None)
        st.dataframe(pay_df, use_container_width=True)

    # -------------------- TAB 3: UPDATE PAYMENT STATUS --------------------
    with tab3:
        st.subheader("✏️ Update Existing Payment Record")
        all_pays = read_sql("""
            SELECT p.payment_id, s.student_name, s.grade, p.month_year, p.amount, p.status, p.paid_date
            FROM payments p
            JOIN students s ON p.student_id = s.student_id
            ORDER BY p.payment_id DESC
        """)

        if all_pays.empty:
            st.info("No payment records available to update.")
        else:
            pay_options = {
                f"#{r['payment_id']} | {r['student_name']} ({r['grade']}) - {r['month_year']} [{r['status']}]": r
                for _, r in all_pays.iterrows()
            }
            sel_pay_label = st.selectbox("Select Payment Record", list(pay_options.keys()))
            rec = pay_options[sel_pay_label]

            with st.form("edit_payment_form"):
                c1, c2 = st.columns(2)
                upd_amount = c1.number_input("Amount (RWF)", min_value=0, value=int(rec["amount"]), step=500)
                upd_status = c2.selectbox(
                    "New Status",
                    PAYMENT_STATUS,
                    index=PAYMENT_STATUS.index(rec["status"]) if rec["status"] in PAYMENT_STATUS else 0
                )
                upd_date = st.date_input("Payment Date", value=datetime.date.today())

                if st.form_submit_button("Update Payment"):
                    conn.execute(
                        "UPDATE payments SET amount=%s, status=%s, paid_date=%s, recorded_by=%s WHERE payment_id=%s",
                        (upd_amount, upd_status, str(upd_date), st.session_state.user_name, int(rec["payment_id"]))
                    )
                    conn.commit()
                    st.success("Payment record updated!")
                    st.rerun()
# -------------------- TAB 4: PETTY CASH & MONTHLY EXPENSES --------------------
    with tab4:
        st.subheader("💸 Petty Cash & Monthly Expenses Room")
        exp_month = st.selectbox("Select Month", PAYMENT_MONTHS, key="petty_cash_month")

        # Automatic monthly calculation: Total Collected vs Total Expenses Deducted
        collected_df = read_sql(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE month_year=%s AND status='Paid'",
            params=(exp_month,)
        )
        month_collected = float(collected_df["total"].iat[0])

        expenses_sum_df = read_sql(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE month_year=%s",
            params=(exp_month,)
        )
        month_expenses = float(expenses_sum_df["total"].iat[0])
        net_remaining = month_collected - month_expenses

        m1, m2, m3 = st.columns(3)
        m1.metric(f"Total Collected ({exp_month})", f"{month_collected:,.0f} RWF")
        m2.metric(f"Total Expenses Deducted ({exp_month})", f"- {month_expenses:,.0f} RWF")
        m3.metric(
            f"Net Balance After Expenses ({exp_month})",
            f"{net_remaining:,.0f} RWF",
            delta=f"{net_remaining:,.0f} RWF"
        )

        if net_remaining < 0:
            st.warning(f"⚠️ Expenses for **{exp_month}** exceed collected fees by **{abs(net_remaining):,.0f} RWF**.")

        st.divider()
        st.write(f"### Record Petty Cash Expense for **{exp_month}**")
        with st.form("record_expense_form", clear_on_submit=True):
            ec1, ec2 = st.columns(2)
            sel_budget_line = ec1.selectbox("Select Budget Line *", BUDGET_LINES)
            exp_amount = ec2.number_input("Expense Amount (RWF) *", min_value=0.0, value=0.0, step=500.0)

            ec3, ec4 = st.columns(2)
            exp_date = ec3.date_input("Expense Date", value=datetime.date.today())
            exp_desc = ec4.text_input("Details / Receipt Note", placeholder="e.g., Bought 5 boxes of white chalk...")

            if st.form_submit_button("💾 Deduct & Save Expense", use_container_width=True):
                if exp_amount > 0:
                    conn.execute("""
                        INSERT INTO expenses (month_year, budget_line, amount, description, expense_date, recorded_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        exp_month,
                        sel_budget_line,
                        float(exp_amount),
                        exp_desc.strip(),
                        str(exp_date),
                        st.session_state.user_name
                    ))
                    conn.commit()
                    st.success(
                        f"Deducted **{exp_amount:,.0f} RWF** under **{sel_budget_line}** "
                        f"from **{exp_month}** collected funds!"
                    )
                    st.rerun()
                else:
                    st.error("Please enter an expense amount greater than 0 RWF.")

        st.subheader(f"Recorded Petty Cash Expenses — {exp_month}")
        month_exp_df = read_sql("""
            SELECT expense_id, budget_line, amount, description, expense_date, recorded_by
            FROM expenses
            WHERE month_year=%s
            ORDER BY expense_id DESC
        """, params=(exp_month,))

        if month_exp_df.empty:
            st.info(f"No petty cash expenses recorded for {exp_month} yet.")
        else:
            st.dataframe(month_exp_df, use_container_width=True)

            # Option for Administration to remove an erroneous expense entry
            if st.session_state.user_role == "Administration":
                with st.expander("🗑️ Delete an Expense Entry"):
                    del_exp_id = st.number_input("Enter Expense ID to Delete", min_value=1, step=1, key="del_exp_id")
                    if st.button("Delete Expense", key="btn_del_exp"):
                        conn.execute("DELETE FROM expenses WHERE expense_id=%s AND month_year=%s", (int(del_exp_id), exp_month))
                        conn.commit()
                        st.success(f"Expense #{int(del_exp_id)} deleted and balance restored.")
                        st.rerun()
 # -------------------- TAB 5: MONTHLY BUDGET & FINANCIAL SUMMARY --------------------
with tab5:
        st.subheader("📊 Monthly Budget Planning & Financial Summary")
        bud_month = st.selectbox("Select Month to Plan / Review", PAYMENT_MONTHS, key="budget_plan_month")

        # Fetch monthly totals
        b_coll_df = read_sql(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE month_year=%s AND status='Paid'",
            params=(bud_month,)
        )
        b_collected = float(b_coll_df["total"].iat[0])

        b_exp_df = read_sql(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE month_year=%s",
            params=(bud_month,)
        )
        b_spent = float(b_exp_df["total"].iat[0])

        b_plan_df = read_sql(
            "SELECT COALESCE(SUM(planned_amount), 0) AS total FROM monthly_budgets WHERE month_year=%s",
            params=(bud_month,)
        )
        b_planned_total = float(b_plan_df["total"].iat[0])
        b_net_cash = b_collected - b_spent

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Fees Collected", f"{b_collected:,.0f} RWF")
        k2.metric("Planned Budget", f"{b_planned_total:,.0f} RWF")
        k3.metric("Actual Expenses", f"{b_spent:,.0f} RWF")
        k4.metric("Net Balance", f"{b_net_cash:,.0f} RWF")

        st.divider()
        st.write(f"### Set / Update Planned Budget Line for **{bud_month}**")
        with st.form("monthly_budget_form", clear_on_submit=True):
            bc1, bc2 = st.columns(2)
            plan_line = bc1.selectbox("Budget Line *", BUDGET_LINES, key="plan_budget_line")
            plan_amt = bc2.number_input("Planned Budget Amount (RWF) *", min_value=0.0, value=0.0, step=1000.0)
            plan_note = st.text_input("Budget Planning Note (Optional)", placeholder="e.g., Monthly allocation based on expected expenses...")

            if st.form_submit_button("💾 Save Monthly Budget Allocation", use_container_width=True):
                conn.execute("""
                    INSERT INTO monthly_budgets (month_year, budget_line, planned_amount, notes, updated_by)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (month_year, budget_line)
                    DO UPDATE SET
                        planned_amount = EXCLUDED.planned_amount,
                        notes = EXCLUDED.notes,
                        updated_by = EXCLUDED.updated_by
                """, (bud_month, plan_line, float(plan_amt), plan_note.strip(), st.session_state.user_name))
                conn.commit()
                st.success(f"Saved budget plan of **{plan_amt:,.0f} RWF** for **{plan_line}** ({bud_month})!")
                st.rerun()

        st.subheader(f"Budget vs. Actual Expenses Breakdown — {bud_month}")
        planned_rows = read_sql(
            "SELECT budget_line, planned_amount, notes FROM monthly_budgets WHERE month_year=%s",
            params=(bud_month,)
        )
        actual_rows = read_sql(
            "SELECT budget_line, COALESCE(SUM(amount), 0) AS actual_spent FROM expenses WHERE month_year=%s GROUP BY budget_line",
            params=(bud_month,)
        )

        planned_map = dict(zip(planned_rows["budget_line"], planned_rows["planned_amount"])) if not planned_rows.empty else {}
        notes_map = dict(zip(planned_rows["budget_line"], planned_rows["notes"])) if not planned_rows.empty else {}
        actual_map = dict(zip(actual_rows["budget_line"], actual_rows["actual_spent"])) if not actual_rows.empty else {}

        summary_data = []
        for line in BUDGET_LINES:
            p_val = float(planned_map.get(line, 0.0))
            a_val = float(actual_map.get(line, 0.0))
            rem_val = p_val - a_val
            summary_data.append({
                "Budget Line": line,
                "Planned Budget (RWF)": p_val,
                "Actual Expenses (RWF)": a_val,
                "Remaining Budget (RWF)": rem_val,
                "Notes": notes_map.get(line, "")
            })

        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)

        st.subheader("All-Months Financial Overview (Collected vs. Expenses)")
        all_months_overview = read_sql("""
            WITH months AS (
                SELECT DISTINCT month_year FROM payments
                UNION
                SELECT DISTINCT month_year FROM expenses
                UNION
                SELECT DISTINCT month_year FROM monthly_budgets
            ),
            p_tot AS (
                SELECT month_year, COALESCE(SUM(amount), 0) AS collected
                FROM payments
                WHERE status = 'Paid'
                GROUP BY month_year
            ),
            e_tot AS (
                SELECT month_year, COALESCE(SUM(amount), 0) AS expenses
                FROM expenses
                GROUP BY month_year
            ),
            b_tot AS (
                SELECT month_year, COALESCE(SUM(planned_amount), 0) AS budgeted
                FROM monthly_budgets
                GROUP BY month_year
            )
            SELECT
                m.month_year AS "Month",
                COALESCE(p.collected, 0) AS "Collected (RWF)",
                COALESCE(b.budgeted, 0) AS "Planned Budget (RWF)",
                COALESCE(e.expenses, 0) AS "Total Expenses (RWF)",
                (COALESCE(p.collected, 0) - COALESCE(e.expenses, 0)) AS "Net Balance (RWF)"
            FROM months m
            LEFT JOIN p_tot p ON m.month_year = p.month_year
            LEFT JOIN e_tot e ON m.month_year = e.month_year
            LEFT JOIN b_tot b ON m.month_year = b.month_year
            ORDER BY m.month_year DESC
        """)
        if not all_months_overview.empty:
            st.dataframe(all_months_overview, use_container_width=True)

    conn.close()


# ====================== REPORT CARDS ======================
elif menu == "Report Cards":
    st.header("📄 Report Cards")
    st.header("📄 Report Cards")
    classes = allowed_classes() if st.session_state.user_role == "Teacher" else CLASS_LEVELS

    tab1, tab2 = st.tabs(["Single Student", "Whole Class / Level"])

    with tab1:
        grade = st.selectbox("Class Level", classes, key="rc1")
        students = read_sql(
            "SELECT * FROM students WHERE grade=%s AND status='Active' ORDER BY student_name",
            params=(grade,)
        )
        if not students.empty:
            name = st.selectbox("Student", students["student_name"].tolist())
            term = st.selectbox("Term", ["Term 1", "Term 2", "Term 3"], key="term1")
            student = next(iter(students[students["student_name"] == name].to_dict("records")))
            grades_df = read_sql(
                "SELECT * FROM grades WHERE student_id=%s AND term=%s",
                params=(int(student["student_id"]), term)
            )

            if grades_df.empty:
                st.info("No grades recorded for this term")
            else:
                all_students = read_sql(
                    "SELECT student_id FROM students WHERE grade=%s AND status='Active'", params=(grade,)
                )
                averages = []
                for sid in all_students["student_id"]:
                    gdf = read_sql("SELECT score, max_score FROM grades WHERE student_id=%s AND term=%s", params=(int(sid), term))
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

                t = Table(data, colWidths=(120, 90, 60, 60, 60))
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
        class_students = read_sql(
            "SELECT student_id, student_name FROM students WHERE grade=%s AND status='Active' ORDER BY student_name",
            params=(grade2,)
        )
        st.write(f"Active students in {grade2}: {len(class_students)}")
        st.dataframe(class_students, use_container_width=True)
# ====================== CODE OF CONDUCT ======================
elif menu == "Code of Conduct":
    st.header("IGISUBIZO ACADEMY School Code of Conduct")
    st.markdown("""
    ### Applies To:** Students, Teachers, Administration, Support Staff

   

## CODE OF CONDUCT AND PROFESSIONAL ETHICS POLICY



### 1. PURPOSE OF THE POLICY

Igisubizo Academy is committed to providing quality education in a safe, respectful, inclusive, and disciplined environment. Every child deserves an opportunity to learn, develop their abilities, and reach their full potential.

This policy establishes clear standards of conduct for everyone working, studying, or participating in activities at Igisubizo Academy. It protects the rights of children, recognizes the professional rights of teachers and staff, and establishes accountability for misconduct.

Every member of the school community must understand that protecting students, maintaining professional standards, and supporting learning are shared responsibilities.

### 2. OUR CORE VALUES

Every decision and action at Igisubizo Academy must reflect the following values:

1. **Child Protection:** Every child has the right to safety, dignity, and protection from abuse.
2. **Professionalism:** Teachers and staff must demonstrate competence, responsibility, honesty, and integrity.
3. **Respect:** Every person must be treated fairly, without discrimination, humiliation, or harassment.
4. **Accountability:** Everyone is responsible for their actions and must accept appropriate consequences for misconduct.
5. **Excellence:** Teaching, learning, and school operations must meet established quality standards.
6. **Integrity:** No person may use their position for personal gain, exploitation, or dishonesty.
7. **Inclusion:** Every student deserves equal opportunities to participate and learn, regardless of background, disability, gender, or financial circumstances.

### 3. NON-NEGOTIABLE STANDARDS

The following standards are mandatory. No teacher, staff member, administrator, or student is above these rules.

**NON-NEGOTIABLE 1: ZERO TOLERANCE FOR CHILD ABUSE**

Physical abuse, sexual abuse, sexual exploitation, harassment, threats, degrading treatment, and deliberate emotional harm are strictly prohibited. No staff member may use physical punishment or humiliate a student as a form of discipline.

**NON-NEGOTIABLE 2: NO ALCOHOL OR DRUG IMPAIRMENT AT WORK**

Teachers and staff must never report for duty under the influence of alcohol or illegal drugs, consume alcohol or illegal drugs while on duty, or teach or supervise students while impaired by any substance. A person suspected of being impaired must not be permitted to supervise students while the concern is assessed. The administration must take immediate protective action and follow a fair disciplinary process.

**NON-NEGOTIABLE 3: NO TEACHING WITHOUT LESSON PREPARATION**

Every teacher must prepare the lesson before entering the classroom. Preparation includes clear learning objectives, appropriate teaching materials, planned activities, and a method for checking students' understanding.

Entering class without preparing the lesson is a serious professional failure. An emergency or other genuine obstacle must be communicated to the academic supervisor as soon as possible, and an alternative teaching plan must be arranged. Repeated failure to prepare, or deliberate disregard of this requirement, may result in formal disciplinary action.

**NON-NEGOTIABLE 4: NO UNAUTHORIZED ABSENCE OR ABANDONMENT OF STUDENTS**

Teachers and staff must attend work according to their schedules. No teacher may leave a class, leave students unsupervised, or abandon assigned responsibilities without proper authorization and a safe handover.

**NON-NEGOTIABLE 5: NO DISCRIMINATION OR FAVORITISM**

Every student must have fair access to teaching, assessment, support, and school activities. No student may be mistreated because of poverty,  status, disability, gender, religion, family background, academic performance, or any other personal characteristic.

**NON-NEGOTIABLE 6: NO SEXUAL MISCONDUCT OR EXPLOITATION**

Any sexual activity, sexual harassment, grooming, or exploitation involving a staff member and a student is prohibited. Where a student is under 18, sexual activity with that child is prohibited regardless of purported consent. No employee may request money, gifts, favors, or sexual activity in exchange for grades, admission, protection, or special treatment.

**NON-NEGOTIABLE 7: NO FRAUD, THEFT, OR MISUSE OF SCHOOL RESOURCES**

Stealing school property, falsifying attendance or academic records, cheating, misusing school funds, taking unauthorized payments, or deliberately falsifying financial information is prohibited.

**NON-NEGOTIABLE 8: NO RETALIATION AGAINST PEOPLE WHO REPORT CONCERNS**

No student, teacher, or staff member may be threatened, punished, intimidated, or discriminated against for reporting a concern in good faith. Knowingly making a false allegation may be addressed through a fair process, but an unsubstantiated report is not automatically a false report.

### 4. CODE OF CONDUCT FOR TEACHERS

Every teacher at Igisubizo Academy must meet the following professional standards.

#### 4.1 Lesson Planning and Teaching Quality

Teachers must:

- Prepare lesson plans before teaching each lesson.
- Follow the approved curriculum, timetable, and learning objectives.
- Arrive in class with the required teaching and learning materials.
- Explain concepts clearly and use appropriate teaching methods.
- Give students opportunities to ask questions, practise, and receive feedback.
- Assign and mark homework and assessments appropriately.
- Maintain accurate attendance, assessment, and academic progress records.
- Identify students who need additional support and take reasonable steps to help them.
- Never invent lesson preparation records or falsify academic results.
- Participate in professional development and accept constructive feedback.

**Required standard:** A teacher must not enter class intending to improvise the entire lesson without preparation. Where an unexpected emergency prevents normal preparation, the teacher must inform the supervisor and arrange a suitable alternative.

#### 4.2 Attendance and Punctuality

Teachers must:

- Report to work on time and attend all assigned lessons.
- Notify the administration promptly when illness or an emergency prevents attendance.
- Obtain approval for leave according to school procedures.
- Never ask an unauthorized person to take over a class.
- Never leave students alone without an approved supervision arrangement.
- Use teaching hours for teaching and learning-related responsibilities.

Repeated lateness, unexplained absence, missed lessons, or leaving students unsupervised will be treated as misconduct.

#### 4.3 Professional Behavior

Teachers must:

- Maintain professional language, dress, conduct, and relationships.
- Never report for work while impaired by alcohol or drugs.
- Never smoke or consume intoxicating substances in prohibited school areas.
- Avoid shouting at, insulting, threatening, or humiliating students.
- Never demand personal payments or gifts from students or parents.
- Never use student information, photographs, or videos without appropriate authorization and consent.
- Maintain appropriate boundaries when communicating with students in person or online.
- Report safeguarding concerns immediately through the designated reporting procedure.

#### 4.4 Fairness and Accountability

Teachers must assess students fairly, provide equal learning opportunities, protect confidential information, and explain academic decisions professionally.

No teacher may intentionally lower a student's marks because of a personal disagreement or increase marks in exchange for money, gifts, or favors.

### 5. CODE OF CONDUCT FOR ADMINISTRATION AND SUPPORT STAFF

All administrators and support staff must:

1. Perform their assigned duties honestly and competently.
2. Respect students, teachers, parents, colleagues, and visitors.
3. Protect children and report suspected abuse or unsafe conditions.
4. Maintain confidentiality and safeguard school records.
5. Use school funds, equipment, and materials only for authorized purposes.
6. Follow financial procedures and maintain accurate records.
7. Avoid conflicts of interest, bribery, fraud, and favoritism.
8. Report to work fit for duty and never supervise children while impaired.
9. Carry out responsibilities according to approved schedules and procedures.
10. Treat employees fairly and avoid discrimination, intimidation, and abuse of authority.

School leaders must also provide reasonable supervision, communicate expectations clearly, and apply disciplinary procedures consistently.

### 6. RIGHTS AND RESPONSIBILITIES OF STUDENTS

Students have the right to:

- Learn in a safe and supportive environment.
- Be treated with dignity and without discrimination.
- Receive fair teaching, assessment, and feedback.
- Express concerns respectfully and be heard.
- Report bullying, abuse, or unsafe situations without retaliation.
- Have their personal information handled appropriately.
- Receive clear explanations of school rules and disciplinary decisions.

Students are responsible for:

- Respecting teachers, staff, fellow students, and visitors.
- Attending lessons regularly and arriving on time.
- Completing assignments and participating in learning.
- Avoiding bullying, fighting, cheating, stealing, and abusive language.
- Following reasonable school instructions.
- Protecting school property and keeping the environment clean.
- Reporting serious safety concerns to a trusted adult.

### 7. RIGHTS AND RESPONSIBILITIES OF TEACHERS AND STAFF

Igisubizo Academy recognizes that teachers and staff also have rights that must be protected.

They have the right to:

- Be treated with dignity, fairness, and professional respect.
- Work in a reasonably safe environment.
- Receive clear job responsibilities, schedules, and performance expectations.
- Receive agreed compensation and employment benefits in accordance with their contracts and applicable law.
- Raise concerns about working conditions without retaliation.
- Receive feedback and a fair opportunity to respond to allegations.
- Be protected against discrimination, harassment, and arbitrary disciplinary action.
- Receive appropriate guidance, supervision, and professional development opportunities.

These rights do not remove the responsibility to meet professional standards or protect students.

### 8. CHILD SAFEGUARDING AND REPORTING

Every person at Igisubizo Academy has a responsibility to protect children from harm.

When a safeguarding concern arises:

1. Take immediate steps to protect the child from further harm.
2. Report the concern promptly to the designated safeguarding person or school administration.
3. Record factual information accurately and confidentially.
4. Do not interrogate the child, conduct an unauthorized investigation, or promise absolute secrecy.
5. Refer serious matters to the appropriate child protection or other competent authorities in accordance with applicable law.
6. Protect the child from retaliation and unnecessary exposure of personal information.

If the concern involves the head of the school or the designated safeguarding person, the report must be directed to an independent, authorized alternative.

The school must not conceal allegations or prioritize its reputation over the safety of a child.

### 9. DISCIPLINARY ACTIONS AND CONSEQUENCES

Igisubizo Academy will take misconduct seriously. The response will depend on the nature of the violation, its impact, the available evidence, any previous misconduct, and the requirements of applicable law.

#### 9.1 Serious Misconduct

Examples include:

- Reporting for work intoxicated or teaching while impaired.
- Physical punishment, child abuse, sexual misconduct, or exploitation.
- Deliberately abandoning students or placing them in danger.
- Repeatedly refusing to prepare lessons after clear instructions and reasonable support.
- Fraud, theft, falsification of records, or misuse of school funds.
- Retaliation against a person who reports a concern.
- Deliberately concealing serious safeguarding incidents.

Possible measures include immediate protective action, removal from student-facing duties while an investigation is conducted where appropriate, a formal written warning, suspension in accordance with applicable rules, and termination of employment where justified.

Serious safeguarding allegations must be referred to the appropriate authorities when required. Any temporary removal from duties is a protective measure, not a declaration that the allegation has been proven.

#### 9.2 Repeated Poor Performance or Misconduct

Examples include:

- Repeatedly arriving late.
- Regularly entering class without prepared lessons.
- Frequently missing lessons without authorization.
- Failing to mark assignments or maintain required records.
- Repeatedly ignoring reasonable instructions.

Depending on the circumstances, the school may use:

1. A documented supervisory meeting.
2. A written warning and clear expectations.
3. A performance improvement plan with a deadline.
4. A final written warning where justified.
5. Further disciplinary action, including termination where appropriate and lawful.

Repeated misconduct after warnings may lead to stronger consequences. However, child abuse, sexual exploitation, serious fraud, and other grave violations do not need to be treated as minor first-time offenses.

#### 9.3 Student Misconduct

Student discipline should be age-appropriate, proportionate, and focused on safety, responsibility, and learning.

Possible measures include a verbal warning, a documented behavior meeting, parent or guardian involvement, a behavior improvement plan, and suspension or other serious measures where justified and lawful.

Physical punishment, degrading treatment, discrimination, and denial of a child's basic protection are never acceptable disciplinary measures.

### 10. FAIR DISCIPLINARY PROCEDURES

Before imposing a disciplinary sanction, the school will, as appropriate to the seriousness and urgency of the case:

- Record the alleged misconduct.
- Take immediate steps to protect students and other affected persons.
- Inform the person concerned of the allegations and give them a reasonable opportunity to respond.
- Review relevant evidence impartially.
- Keep confidential records of the process and outcome.
- Communicate the decision and any applicable review or appeal procedure.
- Apply sanctions consistently and in accordance with employment agreements, school policies, and applicable Rwandan law.

Immediate protective action may be necessary before the investigation is complete. It must not be used as a substitute for a fair investigation.

### 11. IMPLEMENTATION AND COMPLIANCE

The school administration is responsible for communicating this policy, providing appropriate orientation, maintaining reporting procedures, and ensuring consistent implementation.

Every teacher and staff member must receive and acknowledge the policy before assuming duties or as part of the school's formal induction process. Students and parents or guardians must receive an age-appropriate explanation of the student rules.

The policy should be reviewed periodically and updated when necessary to reflect changes in school operations, child protection requirements, and applicable law.

### 12. DECLARATION AND SIGNATURE

I confirm that I have read and understood the Igisubizo Academy Code of Conduct and Professional Ethics Policy. I agree to follow its requirements, protect the rights and safety of children, respect the rights of colleagues and students, and accept fair disciplinary procedures for violations.

**Full Name:** Dan Ishimwe/ Murwanashyaka Elie

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
                    "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
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
                    "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
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
                    "INSERT INTO notifications (title, message, created_by, created_at) VALUES (%s,%s,%s,%s)",
                    (title, msg, st.session_state.user_name, str(datetime.datetime.now()))
                )
                conn.commit()
                st.success("Notification sent")
                st.rerun()

    st.subheader("All Notifications")
    st.dataframe(read_sql("SELECT * FROM notifications ORDER BY notif_id DESC"), use_container_width=True)
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
                "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (st.session_state.user_name, st.session_state.user_role, recipient, subject, body, str(datetime.datetime.now()))
            )
            conn.commit()
            st.success("Message sent")
            st.rerun()
    st.dataframe(read_sql("SELECT * FROM messages ORDER BY msg_id DESC LIMIT 50"), use_container_width=True)
    conn.close()

# ====================== REMOVED RECORDS ======================
elif menu == "Removed Records":
    st.header("🗑️ Removed / Inactive Records")
    st.subheader("Inactive Students")
    st.dataframe(read_sql("SELECT * FROM students WHERE status='Inactive'"), use_container_width=True)
    st.subheader("Inactive Staff")
    st.dataframe(read_sql("SELECT * FROM staff WHERE status='Inactive'"), use_container_width=True)
