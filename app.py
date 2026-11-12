import sqlite3
import datetime
import pandas as pd
import streamlit as st
from config import CLASS_LEVELS, SUBJECT_LIST, PAYMENT_MONTHS, MONTHLY_FEE, SALARY_DEFAULTS, TRANSLATIONS
from database import get_conn, init_db, generate_report_card_pdf

st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = True
    st.session_state.user_name = "Head Administrator"
    st.session_state.user_role = "Administration"
    st.session_state.username = "admin"

if "lang" not in st.session_state:
    st.session_state.lang = "English"

col_spacer, col_lang = st.columns([3, 1])

with col_lang:
    st.session_state.lang = st.selectbox(
        "🌐 Language / Ururimi",
        list(TRANSLATIONS.keys()),
        index=list(TRANSLATIONS.keys()).index(st.session_state.lang)
    )

T = TRANSLATIONS[st.session_state.lang]

st.markdown(f"""
<div style="background: linear-gradient(90deg, #0b5345 0%, #154360 100%); padding: 24px; border-radius: 12px; color: white; margin-bottom: 20px;">
    <h1 style="margin: 0; color: white;">{T['title']}</h1>
    <p style="margin: 5px 0 0 0; opacity: 0.9;">{T['subtitle']}</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.logged_in:
    st.subheader(T["login_header"])
    with st.form("login_form"):
        role = st.selectbox(T["select_role"], ["Administration", "Teacher", "Register Officer", "Parent"])
        uname = st.text_input(T["username"], placeholder="admin")
        pwd = st.text_input(T["password"], type="password", placeholder="admin123")
        if st.form_submit_button(T["login_btn"]):
            conn = get_conn()
            if role == "Parent":
                df_p = pd.read_sql_query("SELECT * FROM students WHERE parent_phone = ?", conn, params=(uname,))
                if not df_p.empty and pwd == "1234":
                    st.session_state.logged_in = True
                    st.session_state.user_name = df_p.iloc["parent_name"]
                    st.session_state.user_role = "Parent"
                    st.session_state.username = uname
                    st.rerun()
                else:
                    st.error("Invalid Parent Phone or PIN (Default PIN: 1234)")
            else:
                df_s = pd.read_sql_query("SELECT * FROM staff WHERE username = ? AND password = ? AND status = 'Active'", conn, params=(uname, pwd))
                if not df_s.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_name = df_s.iloc["full_name"]
                    st.session_state.user_role = df_s.iloc["role"]
                    st.session_state.username = uname
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try username: admin / password: admin123")
            conn.close()
    st.stop()

with st.sidebar:
    st.success(f"👤 **{st.session_state.user_name}**\n\nRole: **{st.session_state.user_role}**")
    if st.button(T["logout_btn"], use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.divider()
    nav_keys = ["dashboard", "students", "grades", "report_card", "attendance", "conduct", "payments", "finance", "reports", "staff", "tasks", "chat", "change_pwd"]
    nav_labels = [T[k] for k in nav_keys]
    selected_label = st.radio(T["menu"], nav_labels)
    active_page = nav_keys[nav_labels.index(selected_label)]

conn = get_conn()

if active_page == "dashboard":
    st.subheader(T["dashboard"])
    students_df = pd.read_sql_query("SELECT * FROM students WHERE status='Active'", conn)
    payments_df = pd.read_sql_query("SELECT * FROM payments", conn)
    staff_df = pd.read_sql_query("SELECT * FROM staff WHERE status='Active'", conn)
    expenses_df = pd.read_sql_query("SELECT * FROM monthly_budgets", conn)

    c1, c2, c3 = st.columns([2, 2, 3])

    c1.metric(T["active_students"], len(students_df))
    c2.metric(T["total_collected"], f"{payments_df['amount'].sum():,.0f} RWF" if not payments_df.empty else "0 RWF")
    c3.metric("Active Staff", len(staff_df))
    c4.metric("Total Expenses", f"{expenses_df['spent_amount'].sum():,.0f} RWF" if not expenses_df.empty else "0 RWF")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Students per Class Level")
        if not students_df.empty:
            st.bar_chart(students_df['grade'].value_counts().reindex(CLASS_LEVELS, fill_value=0))
        else:
            st.info("No students registered yet.")
    with col_b:
        st.markdown("#### Recent Fee Payments")
        if not payments_df.empty:
            st.dataframe(pd.read_sql_query("SELECT s.student_name, s.grade, p.month_year, p.amount, p.paid_date FROM payments p JOIN students s ON p.student_id = s.student_id ORDER BY p.payment_id DESC LIMIT 10", conn), use_container_width=True)
        else:
            st.info("No fee payments recorded yet.")

elif active_page == "students":
    st.subheader(T["students"])
    tab1, tab2 = st.tabs(["📋 Student Roster", "➕ Register New Student"])
    with tab1:
        selected_class = st.selectbox(T["select_grade"], ["All Classes"] + CLASS_LEVELS)
        q = "SELECT * FROM students ORDER BY grade, student_name" if selected_class == "All Classes" else "SELECT * FROM students WHERE grade = ? ORDER BY student_name"
        df_st = pd.read_sql_query(q, conn) if selected_class == "All Classes" else pd.read_sql_query(q, conn, params=(selected_class,))
        st.dataframe(df_st, use_container_width=True)
    with tab2:
        with st.form("add_student_form"):
            s_name = st.text_input("Student Full Name *")
            s_grade = st.selectbox("Class Level *", CLASS_LEVELS)
            p_name = st.text_input("Parent / Guardian Name")
            p_phone = st.text_input("Parent Phone Number")
            p_email = st.text_input("Parent Email (Optional)")
            if st.form_submit_button(T["save"]) and s_name.strip():
                conn.execute("INSERT INTO students (student_name, grade, parent_name, parent_phone, parent_email, status, created_at) VALUES (?, ?, ?, ?, ?, 'Active', ?)", (s_name.strip(), s_grade, p_name.strip(), p_phone.strip(), p_email.strip(), str(datetime.date.today())))
                conn.commit()
                st.success(f"Student '{s_name}' added to {s_grade}!")
                st.rerun()

elif active_page == "grades":
    st.subheader(T["grades"])
    sel_class = st.selectbox(T["select_grade"], CLASS_LEVELS)
    students_in_class = pd.read_sql_query("SELECT student_id, student_name FROM students WHERE grade = ? AND status='Active'", conn, params=(sel_class,))
    if students_in_class.empty:
        st.warning(f"No active students found in {sel_class}.")
    else:
        with st.form("add_grade_form"):
            col1, col2, col3 = st.columns(3)
            student_map = dict(zip(students_in_class["student_name"], students_in_class["student_id"]))
            sel_student = col1.selectbox("Student", list(student_map.keys()))
            sel_subject = col2.selectbox("Subject", SUBJECT_LIST)
            sel_term = col3.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
            col4, col5, col6 = st.columns(3)
            assess_type = col4.selectbox("Assessment Type", ["Exam", "Midterm", "Quiz / Homework"])
            score = col5.number_input("Score Obtained", 0.0, 100.0, 75.0)
            max_score = col6.number_input("Max Score", 1.0, 100.0, 100.0)
            if st.form_submit_button(T["save"]):
                conn.execute("INSERT INTO grades (student_id, subject, assessment_type, score, max_score, term, date, teacher) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (student_map[sel_student], sel_subject, assess_type, score, max_score, sel_term, str(datetime.date.today()), st.session_state.user_name))
                conn.commit()
                st.success("Grade recorded!")
        st.dataframe(pd.read_sql_query("SELECT g.grade_id, s.student_name, s.grade, g.term, g.subject, g.assessment_type, g.score, g.max_score, g.date FROM grades g JOIN students s ON g.student_id = s.student_id WHERE s.grade = ? ORDER BY g.grade_id DESC", conn, params=(sel_class,)), use_container_width=True)

elif active_page == "report_card":
    st.subheader(T["report_card"])
    sel_class = st.selectbox(T["select_grade"], CLASS_LEVELS)
    students_df = pd.read_sql_query("SELECT * FROM students WHERE grade = ? AND status='Active'", conn, params=(sel_class,))
    if students_df.empty:
        st.warning("No students in this class.")
    else:
        col1, col2 = st.columns(2)
        sel_name = col1.selectbox("Select Student", students_df["student_name"].tolist())
        sel_term = col2.selectbox("Select Term", ["Term 1", "Term 2", "Term 3"])
        student_row = students_df[students_df["student_name"] == sel_name].iloc
        grades_df = pd.read_sql_query("SELECT * FROM grades WHERE student_id = ? AND term = ?", conn, params=(int(student_row["student_id"]), sel_term))
        if grades_df.empty:
            st.info(f"No grades recorded yet for {sel_name} in {sel_term}.")
        else:
            st.dataframe(grades_df[["subject", "assessment_type", "score", "max_score"]], use_container_width=True)
            st.download_button("📄 Download Official Report Card (PDF)", data=generate_report_card_pdf(student_row, grades_df, sel_term), file_name=f"ReportCard_{sel_name.replace(' ', '_')}_{sel_term}.pdf", mime="application/pdf")

elif active_page == "attendance":
    st.subheader(T["attendance"])
    col1, col2 = st.columns(2)
    sel_class = col1.selectbox(T["select_grade"], CLASS_LEVELS)
    att_date = col2.date_input("Date", datetime.date.today())
    students_df = pd.read_sql_query("SELECT student_id, student_name FROM students WHERE grade = ? AND status='Active'", conn, params=(sel_class,))
    if not students_df.empty:
        with st.form("attendance_form"):
            records = []
