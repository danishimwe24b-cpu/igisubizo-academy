import sqlite3
import datetime
import pandas as pd
import streamlit as st
from config import CLASS_LEVELS, SUBJECT_LIST, PAYMENT_MONTHS, MONTHLY_FEE, SALARY_DEFAULTS

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
            conn.execute(
                "INSERT INTO conduct (person_type, person_name, grade_or_role, incident_type, points_change, notes, date, recorded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (p_type, p_name.strip(), grade_role.strip(), inc_type, pts, notes.strip(), str(datetime.date.today()), st.session_state.user_name)
            )
            conn.commit()
            st.success("Conduct record saved!")
    st.dataframe(pd.read_sql_query("SELECT * FROM conduct ORDER BY conduct_id DESC", conn), use_container_width=True)

def render_payments(conn, T):
    st.subheader(T["payments"])

    if st.session_state.user_role == "Parent":
        st.markdown("#### My Child's Fee Payment History")
        st.dataframe(pd.read_sql_query(
            "SELECT s.student_name, s.grade, p.month_year, p.amount, p.paid_date FROM payments p JOIN students s ON p.student_id = s.student_id WHERE TRIM(s.parent_phone) = ? ORDER BY p.month_year ASC",
            conn, params=(st.session_state.username,)
        ), use_container_width=True)
        return

    tab_record, tab_matrix, tab_unpaid = st.tabs([
        "💳 Record Payment (By Class Level)",
        "📅 Month-by-Month Tracker (By Class Level)",
        "⚠️ Unpaid Students Audit"
    ])

    with tab_record:
        sel_level = st.selectbox(T["select_grade"], CLASS_LEVELS, key="pay_record_level")
        class_students = pd.read_sql_query(
            "SELECT student_id, student_name FROM students WHERE grade = ? AND status='Active' ORDER BY student_name",
            conn, params=(sel_level,)
        )

        if class_students.empty:
            st.warning(f"No active students found in {sel_level}.")
        else:
            with st.form("payment_by_level_form"):
                c1, c2, c3 = st.columns(3)
                student_map = dict(zip(class_students["student_name"], class_students["student_id"]))
                sel_student = c1.selectbox(f"Select Student in {sel_level}", list(student_map.keys()))
                sel_month = c2.selectbox("Select Month", PAYMENT_MONTHS)
                amount = c3.number_input("Amount Paid (RWF)", min_value=500, value=MONTHLY_FEE, step=500)

                if st.form_submit_button(T["save"]):
                    try:
                        conn.execute(
                            "INSERT INTO payments (student_id, month_year, amount, paid_date, recorded_by) VALUES (?, ?, ?, ?, ?)",
                            (int(student_map[sel_student]), sel_month, amount, str(datetime.date.today()), st.session_state.user_name)
                        )
                        conn.commit()
                        st.success(f"Recorded {amount:,.0f} RWF for {sel_student} ({sel_level}) — {sel_month}!")
                    except sqlite3.IntegrityError:
                        st.error(f"{sel_student} has already paid for {sel_month}.")

        st.markdown(f"#### Recent Payments in {sel_level}")
        st.dataframe(pd.read_sql_query(
            """
            SELECT p.payment_id, s.student_name, s.grade, p.month_year, p.amount, p.paid_date, p.recorded_by
            FROM payments p JOIN students s ON p.student_id = s.student_id
            WHERE s.grade = ?
            ORDER BY p.payment_id DESC
            """,
            conn, params=(sel_level,)
        ), use_container_width=True)

    with tab_matrix:
        col_m1, col_m2 = st.columns(2)
        matrix_level = col_m1.selectbox("Select Class Level", CLASS_LEVELS, key="pay_matrix_level")
        matrix_year = col_m2.selectbox("Select Academic Year", ["2026", "2027"], key="pay_matrix_year")

        year_months = [m for m in PAYMENT_MONTHS if m.startswith(matrix_year)]
        students_lvl = pd.read_sql_query(
            "SELECT student_id, student_name FROM students WHERE grade = ? AND status='Active' ORDER BY student_name",
            conn, params=(matrix_level,)
        )

        if students_lvl.empty:
            st.info(f"No active students in {matrix_level}.")
        else:
            pay_records = pd.read_sql_query(
                "SELECT p.student_id, p.month_year, p.amount FROM payments p JOIN students s ON p.student_id = s.student_id WHERE s.grade = ?",
                conn, params=(matrix_level,)
            )
            paid_lookup = {(row["student_id"], row["month_year"]): row["amount"] for _, row in pay_records.iterrows()}

            matrix_rows = []
            for _, st_row in students_lvl.iterrows():
                sid = st_row["student_id"]
                row_dict = {"Student Name": st_row["student_name"]}
                total_paid_yr = 0
                for m in year_months:
                    parts = m.split(" ")
                    short_label = parts.pop() if len(parts) > 1 else m
                    legacy_key = m.split(" ").pop(0)
                    amt = paid_lookup.get((sid, m)) or paid_lookup.get((sid, legacy_key))
                    if amt:
                        row_dict[short_label] = f"PAID ({int(amt):,})"
                        total_paid_yr += amt
                    else:
                        row_dict[short_label] = "UNPAID"
                row_dict[f"Total {matrix_year} (RWF)"] = f"{int(total_paid_yr):,}"
                matrix_rows.append(row_dict)

            st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True)

    with tab_unpaid:
        c_u1, c_u2 = st.columns(2)
        audit_level = c_u1.selectbox("Filter by Class Level", ["All Classes"] + CLASS_LEVELS, key="pay_audit_level")
        check_month = c_u2.selectbox("Select Month to Audit", PAYMENT_MONTHS, key="pay_audit_month")
        legacy_month = check_month.split(" ").pop(0)

        if audit_level == "All Classes":
            unpaid_df = pd.read_sql_query(
                """
                SELECT student_id, student_name, grade, parent_name, parent_phone
                FROM students
                WHERE status='Active' AND student_id NOT IN (
                    SELECT student_id FROM payments WHERE month_year IN (?, ?)
                )
                ORDER BY grade, student_name
                """,
                conn, params=(check_month, legacy_month)
            )
        else:
            unpaid_df = pd.read_sql_query(
                """
                SELECT student_id, student_name, grade, parent_name, parent_phone
                FROM students
                WHERE status='Active' AND grade = ? AND student_id NOT IN (
                    SELECT student_id FROM payments WHERE month_year IN (?, ?)
                )
                ORDER BY student_name
                """,
                conn, params=(audit_level, check_month, legacy_month)
            )

        st.write(f"**Unpaid Students ({audit_level} — {check_month}):** {len(unpaid_df)}")
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
            conn.execute(
                "INSERT INTO monthly_budgets (month_year, category, allocated_amount, spent_amount, description, date) VALUES (?, ?, 0, ?, ?, ?)",
                (m_yr, cat, spent, desc.strip(), str(datetime.date.today()))
            )
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
            conn.execute(
                "INSERT INTO teacher_reports (teacher_name, grade, week_ending, topics_covered, challenges, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
                (st.session_state.user_name, sel_class, str(wk_date), topics.strip(), challenges.strip(), str(datetime.date.today()))
            )
            conn.commit()
            st.success("Weekly report submitted!")
    st.dataframe(pd.read_sql_query("SELECT * FROM teacher_reports ORDER BY report_id DESC", conn), use_container_width=True)

def render_staff(conn, T):
    st.subheader(T["staff"])
    tab_add, tab_assign, tab_manage = st.tabs([
        "➕ Create Staff / Teacher Account",
        "📚 Assign Classes & Subjects to Teachers",
        "🔑 Reset Passwords & Status"
    ])

    with tab_add:
        with st.form("add_staff_form"):
            c1, c2, c3 = st.columns(3)
            f_name = c1.text_input("Full Name *")
