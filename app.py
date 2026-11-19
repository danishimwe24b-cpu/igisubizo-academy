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
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT NOT NULL,
            category TEXT,
            description TEXT,
            amount REAL NOT NULL,
            expense_date TEXT,
            recorded_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS teacher_attendance (
            t_att_id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER,
            date TEXT,
            status TEXT,
            notes TEXT,
            recorded_by TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS language_skills (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            term TEXT,
            language TEXT,
            speaking TEXT,
            reading TEXT,
            writing TEXT,
            teacher TEXT,
            UNIQUE(student_id, term, language)
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
    # ====================== TOP NOTIFICATION & MESSAGE BANNER ======================
conn_banner = get_conn()
latest_notifs = pd.read_sql_query("SELECT title, message, created_by, created_at FROM notifications ORDER BY notif_id DESC LIMIT 2", conn_banner)
recent_msgs = pd.read_sql_query("SELECT sender_name, recipient, subject, created_at FROM messages ORDER BY msg_id DESC LIMIT 3", conn_banner)
conn_banner.close()

if not latest_notifs.empty or not recent_msgs.empty:
    with st.expander("🔔 Latest School Notifications & Recent Messages", expanded=True):
        col_n, col_m = st.columns(2)
        with col_n:
            st.markdown("**📢 Announcements**")
            if latest_notifs.empty:
                st.caption("No announcements yet.")
            else:
                for _, n in latest_notifs.iterrows():
                    st.info(f"**{n['title']}** — {n['message']} *(by {n['created_by']})*")
        with col_m:
            st.markdown("**💬 Recent Messages / Permissions**")
            if recent_msgs.empty:
                st.caption("No recent messages.")
            else:
                for _, m in recent_msgs.iterrows():
                    st.warning(f"**To {m['recipient']}:** {m['subject']} *(from {m['sender_name']})*")

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

    conn.execute("CREATE TABLE IF NOT EXISTS expenses (expense_id INTEGER PRIMARY KEY AUTOINCREMENT, month_year TEXT NOT NULL, category TEXT, description TEXT, amount REAL NOT NULL, expense_date TEXT, recorded_by TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS teacher_attendance (t_att_id INTEGER PRIMARY KEY AUTOINCREMENT, staff_id INTEGER, date TEXT, status TEXT, notes TEXT, recorded_by TEXT)")
    conn.commit()

    active_students = int(pd.read_sql_query("SELECT COUNT(*) as c FROM students WHERE status='Active'", conn).iloc[0]["c"])
    inactive_students = int(pd.read_sql_query("SELECT COUNT(*) as c FROM students WHERE status='Inactive'", conn).iloc[0]["c"])
    active_staff = int(pd.read_sql_query("SELECT COUNT(*) as c FROM staff WHERE status='Active'", conn).iloc[0]["c"])
    total_all_time = float(pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) as t FROM payments WHERE status='Paid'", conn).iloc[0]["t"])

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Active Students", active_students)
    top2.metric("Inactive Students", inactive_students)
    top3.metric("Active Staff", active_staff)
    top4.metric("All-Time Collected", f"{total_all_time:,.0f} RWF")

    st.divider()
    st.subheader("💰 Monthly Fees, Expenses & Automatic Share Split (÷ 2)")

    curr_ym = datetime.date.today().strftime("%Y-%m")
    default_idx = PAYMENT_MONTHS.index(curr_ym) if curr_ym in PAYMENT_MONTHS else 0
    selected_month = st.selectbox("Select Month", PAYMENT_MONTHS, index=default_idx, key="dash_month_sel")

    collected_month = float(pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) as t FROM payments WHERE month_year=? AND status='Paid'", conn, params=(selected_month,)).iloc[0]["t"])
    used_month = float(pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) as t FROM expenses WHERE month_year=?", conn, params=(selected_month,)).iloc[0]["t"])

    total_shares_pool = collected_month - used_month
    share_per_person = total_shares_pool / 2.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Collected ({selected_month})", f"{collected_month:,.0f} RWF")
    m2.metric(f"Total Used ({selected_month})", f"{used_month:,.0f} RWF")
    m3.metric("Remaining (Total Shares)", f"{total_shares_pool:,.0f} RWF")
    m4.metric("Each Share (÷ 2)", f"{share_per_person:,.0f} RWF")

    fin_col1, fin_col2 = st.columns([1, 1.6])

    with fin_col1:
        with st.form(key=f"add_expense_form_{selected_month}", clear_on_submit=True):
            st.markdown(f"**➕ Record Expense for {selected_month}**")
            exp_cat = st.selectbox("Category", ["Salaries & Allowances", "Supplies & Chalk", "Utilities (Water/Power)", "Maintenance", "Food / Kitchen", "Transport / Admin", "Other"])
            exp_desc = st.text_input("Description")
            exp_amt = st.number_input("Amount Used (RWF)", min_value=0.0, step=500.0)
            exp_date = st.date_input("Date", value=datetime.date.today())

            if st.form_submit_button("💾 Save Expense", use_container_width=True):
                if exp_amt > 0:
                    conn.execute("INSERT INTO expenses (month_year, category, description, amount, expense_date, recorded_by) VALUES (?,?,?,?,?,?)", (selected_month, exp_cat, exp_desc.strip(), exp_amt, str(exp_date), st.session_state.user_name))
                    conn.commit()
                    st.success(f"Expense of {exp_amt:,.0f} RWF saved for {selected_month}!")
                    st.rerun()
                else:
                    st.error("Enter an amount greater than 0.")

    with fin_col2:
        st.markdown("**📅 Automatic Monthly Financial Summary**")
        pay_by_m = pd.read_sql_query("SELECT month_year, COALESCE(SUM(amount), 0) AS Collected FROM payments WHERE status='Paid' GROUP BY month_year", conn)
        exp_by_m = pd.read_sql_query("SELECT month_year, COALESCE(SUM(amount), 0) AS Used FROM expenses GROUP BY month_year", conn)

        if pay_by_m.empty and exp_by_m.empty:
            st.info("No payments or expenses recorded yet.")
        else:
            summary_df = pd.merge(pay_by_m, exp_by_m, on="month_year", how="outer").fillna(0).sort_values("month_year")
            summary_df["Total Shares (Remaining)"] = summary_df["Collected"] - summary_df["Used"]
            summary_df["Each Share (÷ 2)"] = summary_df["Total Shares (Remaining)"] / 2.0
            display_df = summary_df.copy()
            for col in ["Collected", "Used", "Total Shares (Remaining)", "Each Share (÷ 2)"]:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f} RWF")
            display_df.rename(columns={"month_year": "Month"}, inplace=True)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    month_exp_df = pd.read_sql_query("SELECT expense_id, expense_date, category, description, amount, recorded_by FROM expenses WHERE month_year=? ORDER BY expense_id DESC", conn, params=(selected_month,))
    if not month_exp_df.empty:
        with st.expander(f"📋 Itemized Expenses for {selected_month} ({len(month_exp_df)} items)"):
            st.dataframe(month_exp_df, use_container_width=True, hide_index=True)
            del_col1, del_col2 = st.columns([2, 1])
            del_exp_id = del_col1.selectbox("Select Expense ID to Remove", month_exp_df["expense_id"].tolist(), key=f"del_exp_sel_{selected_month}")
            if del_col2.button("🗑️ Delete Expense", key=f"del_exp_btn_{selected_month}"):
                conn.execute("DELETE FROM expenses WHERE expense_id=?", (int(del_exp_id),))
                conn.commit()
                st.success(f"Deleted expense #{del_exp_id}.")
                st.rerun()

    st.divider()
    tab_perf, tab_t_att, tab_overview = st.tabs(["🏆 Weekly Teacher Performance Ranking", "🕒 Record Teacher Attendance", "📈 Classes & Recent Payments"])

    with tab_perf:
        st.subheader("Automatic Weekly Teacher Performance Evaluation (Last 7 Days)")
        week_ago = str(datetime.date.today() - datetime.timedelta(days=7))
        teachers = pd.read_sql_query("SELECT staff_id, full_name, assigned_classes, assigned_subjects FROM staff WHERE role='Teacher' AND status='Active'", conn)

        if teachers.empty:
            st.info("No active teachers registered yet.")
        else:
            perf_rows = []
            for _, t in teachers.iterrows():
                t_id = int(t["staff_id"])
                t_name = t["full_name"]

                t_present = int(pd.read_sql_query("SELECT COUNT(*) as c FROM teacher_attendance WHERE staff_id=? AND date>=? AND status='Present'", conn, params=(t_id, week_ago)).iloc[0]["c"])
                t_att_pts = min((t_present / 5.0) * 30.0, 30.0)

                s_att_days = int(pd.read_sql_query("SELECT COUNT(DISTINCT date) as c FROM attendance WHERE teacher=? AND date>=?", conn, params=(t_name, week_ago)).iloc[0]["c"])
                s_att_pts = min((s_att_days / 5.0) * 25.0, 25.0)

                gr_count = int(pd.read_sql_query("SELECT COUNT(*) as c FROM grades WHERE teacher=? AND date>=?", conn, params=(t_name, week_ago)).iloc[0]["c"])
                gr_pts = min((gr_count / 10.0) * 25.0, 25.0)

                rep_count = int(pd.read_sql_query("SELECT COUNT(*) as c FROM messages WHERE sender_name=? AND substr(created_at,1,10)>=?", conn, params=(t_name, week_ago)).iloc[0]["c"])
                rep_pts = 20.0 if rep_count >= 1 else 0.0

                total_score = round(t_att_pts + s_att_pts + gr_pts + rep_pts, 1)
                rating = "🌟 Excellent" if total_score >= 85 else ("✅ Good" if total_score >= 65 else ("⚠️ Fair" if total_score >= 45 else "🔻 Needs Follow-up"))

                perf_rows.append({
                    "Teacher": t_name,
                    "Classes": t["assigned_classes"],
                    "Teacher Present": f"{t_present}/5 days",
                    "Student Att. Logged": f"{s_att_days}/5 days",
                    "Grades Logged": gr_count,
                    "Weekly Reports": rep_count,
                    "Performance Score": f"{total_score}%",
                    "Numeric_Score": total_score,
                    "Rating": rating
                })

            perf_df = pd.DataFrame(perf_rows).sort_values(by="Numeric_Score", ascending=False)
            top_teacher = perf_df.iloc[0]
            st.success(f"🥇 **Top Performing Teacher This Week:** {top_teacher['Teacher']} ({top_teacher['Performance Score']} — {top_teacher['Rating']})")
            st.dataframe(perf_df.drop(columns=["Numeric_Score"]), use_container_width=True, hide_index=True)

    with tab_t_att:
        st.subheader("Daily Teacher & Staff Attendance Log")
        t_date = st.date_input("Select Date", value=datetime.date.today(), key="t_att_date")
        t_date_str = str(t_date)
        all_t = pd.read_sql_query("SELECT staff_id, full_name, role FROM staff WHERE status='Active' ORDER BY full_name", conn)

        if not all_t.empty:
            existing_t_df = pd.read_sql_query("SELECT staff_id, status, notes FROM teacher_attendance WHERE date=? ORDER BY t_att_id ASC", conn, params=(t_date_str,)).drop_duplicates(subset=["staff_id"], keep="last")
            existing_t = existing_t_df.set_index("staff_id").to_dict("index")

            with st.form(key=f"teacher_att_form_{t_date_str}"):
                t_records = []
                for _, tr in all_t.iterrows():
                    sid = int(tr["staff_id"])
                    prev_st = existing_t.get(sid, {}).get("status", "Present")
                    prev_nt = existing_t.get(sid, {}).get("notes", "")
                    t_opts = ["Present", "Late", "Absent", "On Leave"]

                    tc1, tc2, tc3 = st.columns([2.5, 1.5, 2.5])
                    tc1.write(f"**{tr['full_name']}** ({tr['role']})")
# ====================== STAFF ======================
elif menu == "Staff & Teachers":
    st.header("👨🏫 Staff & Teachers")
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
    st.header("📅 Daily Attendance")
    conn = get_conn()
    classes = allowed_classes()

    col1, col2 = st.columns(2)
    sel_class = col1.selectbox("Select Class", classes, key="att_class")
    att_date = col2.date_input("Date", value=datetime.date.today(), key="att_date")
    date_str = str(att_date)

    students = pd.read_sql_query(
        "SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
        conn, params=(sel_class,)
    )

    if students.empty:
        st.warning("No active students in this class.")
    else:
        # Load existing attendance safely (drop_duplicates prevents ValueError if old duplicates exist)
        existing_df = pd.read_sql_query(
            "SELECT student_id, status, notes FROM attendance WHERE date=? ORDER BY attendance_id ASC",
            conn, params=(date_str,)
        ).drop_duplicates(subset=["student_id"], keep="last")
        existing = existing_df.set_index("student_id").to_dict("index")

        with st.form("attendance_form"):
            st.write(f"Recording attendance for **{sel_class}** on **{date_str}**")
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

            if st.form_submit_button("💾 Save Attendance", use_container_width=True):
                c = conn.cursor()
                for sid, status, notes in records:
                    # Clean up any old duplicate rows for this student & date, then insert/update cleanly
                    c.execute(
                        "SELECT attendance_id FROM attendance WHERE student_id=? AND date=? ORDER BY attendance_id ASC",
                        (sid, date_str)
                    )
                    rows = c.fetchall()
                    if rows:
                        keep_id = rows[-1][0]
                        # Delete extra duplicates if any existed
                        if len(rows) > 1:
                            c.execute(
                                "DELETE FROM attendance WHERE student_id=? AND date=? AND attendance_id != ?",
                                (sid, date_str, keep_id)
                            )
                        c.execute(
                            "UPDATE attendance SET status=?, notes=?, teacher=? WHERE attendance_id=?",
                            (status, notes, st.session_state.user_name, keep_id)
                        )
                    else:
                        c.execute(
                            "INSERT INTO attendance (student_id, date, status, teacher, notes) VALUES (?,?,?,?,?)",
                            (sid, date_str, status, st.session_state.user_name, notes)
                        )
                conn.commit()
                st.success(f"Attendance saved for {len(records)} students on {date_str}!")
                st.rerun()

        st.subheader("Attendance History for Class")
        hist = pd.read_sql_query("""
            SELECT a.date, s.student_name, a.status, a.notes, a.teacher
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE s.grade = ?
            ORDER BY a.date DESC, s.student_name
        """, conn, params=(sel_class,))
        st.dataframe(hist, use_container_width=True)
    conn.close()

# ====================== PAYMENTS ======================
elif menu == "Payments":
    st.header("💳 School Fees & Payments")
    conn = get_conn()

    tab1, tab2, tab3 = st.tabs(["Record Payment", "Payment Records", "Update Payment Status"])

    with tab1:
        sel_class = st.selectbox("Select Class", CLASS_LEVELS, key="pay_class")
        students = pd.read_sql_query(
            "SELECT student_id, student_name FROM students WHERE grade=? AND status='Active' ORDER BY student_name",
            conn, params=(sel_class,)
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

            # Display already recorded months for this student
            paid_months_df = pd.read_sql_query(
                "SELECT month_year, amount, status, paid_date FROM payments WHERE student_id=? ORDER BY month_year ASC",
                conn, params=(sid,)
            )
            if not paid_months_df.empty:
                recorded_list = [
                    f"{r['month_year']} ({r['status']})" for _, r in paid_months_df.iterrows()
                ]
                st.info(f"**Already recorded for {sel_student_label}:** " + ", ".join(recorded_list))

            with st.form("payment_form"):
                col1, col2 = st.columns(2)
                # Dropdown showing current & future months (2026-11 to 2030-12)
                month_year = col1.selectbox("Select Month (Current or Future)", PAYMENT_MONTHS)
                amount = col2.number_input("Amount (RWF)", min_value=0, value=MONTHLY_FEE, step=500)

                col3, col4 = st.columns(2)
                status = col3.selectbox("Payment Status", PAYMENT_STATUS)
                paid_date = col4.date_input("Payment Date", value=datetime.date.today())

                if st.form_submit_button("💾 Record Payment", use_container_width=True):
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT payment_id, status FROM payments WHERE student_id=? AND month_year=?",
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
                                VALUES (?,?,?,?,?,?)
                            """, (sid, month_year, amount, status, str(paid_date), st.session_state.user_name))
                            conn.commit()
                            st.success(f"Payment recorded for **{sel_student_label}** for **{month_year}**!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(f"⚠️ Duplicate blocked: **{sel_student_label}** already has a payment for **{month_year}**.")

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
            query += " AND p.month_year = ?"
            params.append(filter_month)
        if filter_status != "All":
            query += " AND p.status = ?"
            params.append(filter_status)

        query += " ORDER BY p.month_year DESC, s.grade, s.student_name"
        pay_df = pd.read_sql_query(query, conn, params=params)
        st.dataframe(pay_df, use_container_width=True)

    with tab3:
        st.subheader("✏️ Update Existing Payment Record")
        all_pays = pd.read_sql_query("""
            SELECT p.payment_id, s.student_name, s.grade, p.month_year, p.amount, p.status, p.paid_date
            FROM payments p
            JOIN students s ON p.student_id = s.student_id
            ORDER BY p.payment_id DESC
        """, conn)

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
                        "UPDATE payments SET amount=?, status=?, paid_date=?, recorded_by=? WHERE payment_id=?",
                        (upd_amount, upd_status, str(upd_date), st.session_state.user_name, int(rec["payment_id"]))
                    )
                    conn.commit()
                    st.success("Payment record updated!")
                    st.rerun()

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
