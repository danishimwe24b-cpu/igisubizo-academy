import datetime
import pandas as pd
import streamlit as st
from config import CLASS_LEVELS, SUBJECT_LIST
from database import generate_report_card_pdf

def render_dashboard(conn, T):
    st.subheader(T["dashboard"])
    students_df = pd.read_sql_query("SELECT * FROM students WHERE status='Active'", conn)
    payments_df = pd.read_sql_query("SELECT * FROM payments", conn)
    staff_df = pd.read_sql_query("SELECT * FROM staff WHERE status='Active'", conn)
    expenses_df = pd.read_sql_query("SELECT * FROM monthly_budgets", conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(T["active_students"], len(students_df))
    total_fees = payments_df['amount'].sum() if (not payments_df.empty and 'amount' in payments_df) else 0
    col2.metric(T["total_collected"], f"{total_fees:,.0f} RWF")
    col3.metric("Active Staff", len(staff_df))
    total_exp = expenses_df['spent_amount'].sum() if (not expenses_df.empty and 'spent_amount' in expenses_df) else 0
    col4.metric("Total Expenses", f"{total_exp:,.0f} RWF")

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

def render_students(conn, T):
    st.subheader(T["students"])
    tab1, tab2 = st.tabs(["📋 Student Roster", "➕ Register New Student"])
    with tab1:
        selected_class = st.selectbox(T["select_grade"], ["All Classes"] + CLASS_LEVELS)
        if selected_class == "All Classes":
            df_st = pd.read_sql_query("SELECT * FROM students ORDER BY grade, student_name", conn)
        else:
            df_st = pd.read_sql_query("SELECT * FROM students WHERE grade = ? ORDER BY student_name", conn, params=(selected_class,))
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

def render_grades(conn, T):
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

def render_report_card(conn, T):
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

def render_attendance(conn, T):
    st.subheader(T["attendance"])
    col1, col2 = st.columns(2)
    sel_class = col1.selectbox(T["select_grade"], CLASS_LEVELS)
    att_date = col2.date_input("Date", datetime.date.today())
    students_df = pd.read_sql_query("SELECT student_id, student_name FROM students WHERE grade = ? AND status='Active'", conn, params=(sel_class,))
    if students_df.empty:
        st.warning(f"No active students in {sel_class}.")
    else:
        with st.form("attendance_form"):
            records = []
            for _, row in students_df.iterrows():
                c1, c2, c3 = st.columns(3)
                c1.write(f"**{row['student_name']}**")
                status = c2.selectbox("Status", ["Present", "Absent", "Late", "Excused"], key=f"att_{row['student_id']}")
                note = c3.text_input("Notes", key=f"note_{row['student_id']}")
                records.append((int(row['student_id']), str(att_date), status, st.session_state.user_name, note))
            if st.form_submit_button(T["save"]):
                conn.executemany("INSERT INTO attendance (student_id, date, status, teacher, notes) VALUES (?, ?, ?, ?, ?)", records)
                conn.commit()
                st.success(f"Attendance saved for {sel_class}!")
    st.markdown("#### Recent Attendance Logs")
    st.dataframe(pd.read_sql_query("SELECT a.date, s.grade, s.student_name, a.status, a.notes, a.teacher FROM attendance a JOIN students s ON a.student_id = s.student_id ORDER BY a.attendance_id DESC LIMIT 20", conn), use_container_width=True)
