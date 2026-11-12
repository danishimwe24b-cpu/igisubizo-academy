import sqlite3
import datetime
import pandas as pd
import streamlit as st
from config import CLASS_LEVELS, PAYMENT_MONTHS, MONTHLY_FEE, SALARY_DEFAULTS

def render_conduct(conn, T):
    st.subheader(T["conduct"])
    with st.form("conduct_form"):
        c1, c2, c3 = st.columns(3)
        p_type = c1.selectbox("Category", ["Student", "Staff"])
        p_name = c2.text_input("Full Name *")
        grade_role = c3.text_input("Class Level or Staff Role")
        c4, c5 = st.columns(2)
        inc_type = c4.selectbox("Record Type", ["Commendation (+)", "Warning (-)", "Suspension (-)"])
        pts = c5.number_input("Points Change", value=5 if "+" in inc_type else -5)
        notes = st.text_area("Incident / Achievement Details")
        if st.form_submit_button(T["save"]) and p_name.strip():
            conn.execute("INSERT INTO conduct (person_type, person_name, grade_or_role, incident_type, points_change, notes, date, recorded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (p_type, p_name.strip(), grade_role, inc_type, pts, notes, str(datetime.date.today()), st.session_state.user_name))
            conn.commit()
            st.success("Conduct record saved!")
    st.dataframe(pd.read_sql_query("SELECT * FROM conduct ORDER BY conduct_id DESC", conn), use_container_width=True)

def render_payments(conn, T):
    st.subheader(T["payments"])
    tab_pay, tab_unpaid = st.tabs(["💳 Record & View Payments", "⚠️ Unpaid Students Check"])
    with tab_pay:
        students_df = pd.read_sql_query("SELECT student_id, student_name, grade FROM students WHERE status='Active'", conn)
        if not students_df.empty:
            with st.form("payment_form"):
                c1, c2, c3 = st.columns(3)
                s_options = {f"{r['student_name']} ({r['grade']})": r['student_id'] for _, r in students_df.iterrows()}
                sel_s = c1.selectbox("Select Student", list(s_options.keys()))
                sel_month = c2.selectbox("Billing Month", PAYMENT_MONTHS)
                amount = c3.number_input("Amount Paid (RWF)", min_value=500, value=MONTHLY_FEE, step=500)
                if st.form_submit_button(T["save"]):
                    try:
                        conn.execute("INSERT INTO payments (student_id, month_year, amount, paid_date, recorded_by) VALUES (?, ?, ?, ?, ?)", (int(s_options[sel_s]), sel_month, amount, str(datetime.date.today()), st.session_state.user_name))
                        conn.commit()
                        st.success(f"Payment of {amount:,.0f} RWF recorded!")
                    except sqlite3.IntegrityError:
                        st.error("Payment for this student and month is already recorded.")
        st.dataframe(pd.read_sql_query("SELECT p.payment_id, s.student_name, s.grade, p.month_year, p.amount, p.paid_date, p.recorded_by FROM payments p JOIN students s ON p.student_id = s.student_id ORDER BY p.payment_id DESC", conn), use_container_width=True)
    with tab_unpaid:
        check_month = st.selectbox("Select Month to Audit", PAYMENT_MONTHS)
        unpaid_df = pd.read_sql_query("SELECT student_id, student_name, grade, parent_name, parent_phone FROM students WHERE status='Active' AND student_id NOT IN (SELECT student_id FROM payments WHERE month_year = ?)", conn, params=(check_month,))
        st.write(f"**Unpaid Students for {check_month}:** {len(unpaid_df)}")
        st.dataframe(unpaid_df, use_container_width=True)

def render_finance(conn, T):
    st.subheader(T["finance"])
    with st.form("finance_form"):
        c1, c2, c3 = st.columns(3)
        m_yr = c1.selectbox("Month", PAYMENT_MONTHS)
        cat = c2.selectbox("Category", ["Salaries", "Teaching Materials", "Utilities & Maintenance", "Food & Kitchen", "Other"])
        spent = c3.number_input("Expense Amount (RWF)", min_value=0.0, step=1000.0)
        desc = st.text_input("Expense Description")
        if st.form_submit_button(T["save"]):
            conn.execute("INSERT INTO monthly_budgets (month_year, category, allocated_amount, spent_amount, description, date) VALUES (?, ?, 0, ?, ?, ?)", (m_yr, cat, spent, desc, str(datetime.date.today())))
            conn.commit()
            st.success("Expense recorded!")
    st.dataframe(pd.read_sql_query("SELECT * FROM monthly_budgets ORDER BY budget_id DESC", conn), use_container_width=True)

def render_reports(conn, T):
    st.subheader(T["reports"])
    with st.form("weekly_report_form"):
        c1, c2 = st.columns(2)
        sel_class = c1.selectbox("Class Level", CLASS_LEVELS)
        wk_date = c2.date_input("Week Ending", datetime.date.today())
        topics = st.text_area("Topics Covered This Week")
        challenges = st.text_area("Challenges / Support Needed")
        if st.form_submit_button(T["save"]):
            conn.execute("INSERT INTO teacher_reports (teacher_name, grade, week_ending, topics_covered, challenges, submitted_at) VALUES (?, ?, ?, ?, ?, ?)", (st.session_state.user_name, sel_class, str(wk_date), topics, challenges, str(datetime.date.today())))
            conn.commit()
            st.success("Weekly report submitted!")
    st.dataframe(pd.read_sql_query("SELECT * FROM teacher_reports ORDER BY report_id DESC", conn), use_container_width=True)

def render_staff(conn, T):
    st.subheader(T["staff"])
    with st.form("add_staff_form"):
        c1, c2, c3 = st.columns(3)
        f_name = c1.text_input("Full Name *")
        role = c2.selectbox("Role", list(SALARY_DEFAULTS.keys()))
        phone = c3.text_input("Phone Number")
        c4, c5, c6 = st.columns(3)
        uname = c4.text_input("Login Username *")
        pwd = c5.text_input("Initial Password *", value="123456")
        sal = c6.number_input("Monthly Salary (RWF)", value=float(SALARY_DEFAULTS[role]), step=5000.0)
        if st.form_submit_button(T["save"]) and f_name.strip() and uname.strip():
            try:
                conn.execute("INSERT INTO staff (full_name, role, username, password, phone, salary, status) VALUES (?, ?, ?, ?, ?, ?, 'Active')", (f_name.strip(), role, uname.strip(), pwd, phone, sal))
                conn.commit()
                st.success(f"Staff '{f_name}' added!")
            except sqlite3.IntegrityError:
                st.error("Username already exists.")
    st.dataframe(pd.read_sql_query("SELECT staff_id, full_name, role, username, phone, salary, status FROM staff", conn), use_container_width=True)

def render_tasks(conn, T):
    st.subheader(T["tasks"])
    staff_list = pd.read_sql_query("SELECT full_name FROM staff WHERE status='Active'", conn)["full_name"].dropna().tolist()
    with st.form("task_form"):
        c1, c2, c3 = st.columns(3)
        assignee = c1.selectbox("Assign To", staff_list if staff_list else ["Head Administrator"])
        title = c2.text_input("Task Title *")
        due = c3.date_input("Due Date", datetime.date.today())
        desc = st.text_area("Instructions")
        if st.form_submit_button(T["save"]) and title.strip():
            conn.execute("INSERT INTO tasks (assigned_to, title, description, due_date, status, assigned_by) VALUES (?, ?, ?, ?, 'Pending', ?)", (assignee, title.strip(), desc, str(due), st.session_state.user_name))
            conn.commit()
            st.success("Task assigned!")
    st.dataframe(pd.read_sql_query("SELECT * FROM tasks ORDER BY task_id DESC", conn), use_container_width=True)

def render_chat(conn, T):
    st.subheader(T["chat"])
    with st.form("msg_form"):
        c1, c2 = st.columns(2)
        recipient = c1.selectbox("Send To", ["All Staff", "Administration", "Teachers", "Parents"])
        subject = c2.text_input("Subject / Request Type")
        body = st.text_area("Message")
        if st.form_submit_button("Send Message") and body.strip():
            conn.execute("INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (?, ?, ?, ?, ?, ?)", (st.session_state.user_name, st.session_state.user_role, recipient, subject, body, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.success("Message sent!")
    st.dataframe(pd.read_sql_query("SELECT * FROM messages ORDER BY msg_id DESC", conn), use_container_width=True)

def render_change_pwd(conn, T):
    st.subheader(T["change_pwd"])
    with st.form("pwd_form"):
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        if st.form_submit_button(T["save"]):
            if new_pwd and new_pwd == confirm_pwd:
                conn.execute("UPDATE staff SET password = ? WHERE username = ?", (new_pwd, st.session_state.username))
                conn.commit()
                st.success("Password updated successfully!")
            else:
                st.error("Passwords do not match or are empty.")
