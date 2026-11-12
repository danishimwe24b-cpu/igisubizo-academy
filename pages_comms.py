import sqlite3
import datetime
import pandas as pd
import streamlit as st
from config import CLASS_LEVELS, SUBJECT_LIST, SALARY_DEFAULTS

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
            role = c2.selectbox("Role *", list(SALARY_DEFAULTS.keys()))
            phone = c3.text_input("Phone Number")

            c4, c5, c6 = st.columns(3)
            uname = c4.text_input("Login Username *")
            pwd = c5.text_input("Initial Password *", value="123456")
            sal = c6.number_input("Monthly Salary (RWF)", value=float(SALARY_DEFAULTS[role]), step=5000.0)

            st.markdown("**Teacher Access & Assignments (Select Classes & Subjects if Role is Teacher):**")
            ac1, ac2 = st.columns(2)
            sel_classes = ac1.multiselect("Assigned Class Levels", CLASS_LEVELS, default=CLASS_LEVELS)
            sel_subjects = ac2.multiselect("Assigned Subjects", SUBJECT_LIST, default=SUBJECT_LIST)

            if st.form_submit_button(T["save"]) and f_name.strip() and uname.strip():
                classes_str = ",".join(sel_classes) if (role == "Teacher" and sel_classes) else "ALL"
                subjects_str = ",".join(sel_subjects) if (role == "Teacher" and sel_subjects) else "ALL"
                try:
                    c = conn.cursor()
                    c.execute("PRAGMA table_info(staff)")
                    cols = [col_name for _, col_name, *_ in c.fetchall()]
                    if "name" in cols:
                        c.execute(
                            "INSERT INTO staff (name, full_name, role, username, password, phone, salary, assigned_classes, assigned_subjects, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active')",
                            (f_name.strip(), f_name.strip(), role, uname.strip(), pwd.strip(), phone.strip(), sal, classes_str, subjects_str)
                        )
                    else:
                        c.execute(
                            "INSERT INTO staff (full_name, role, username, password, phone, salary, assigned_classes, assigned_subjects, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active')",
                            (f_name.strip(), role, uname.strip(), pwd.strip(), phone.strip(), sal, classes_str, subjects_str)
                        )
                    conn.commit()
                    st.success(f"Account created for **{f_name}** ({role})! Username: `{uname.strip()}` | Password: `{pwd.strip()}`")
                except sqlite3.IntegrityError:
                    st.error("Username already exists. Please choose another username.")

    with tab_assign:
        teachers_df = pd.read_sql_query(
            "SELECT staff_id, full_name, username, assigned_classes, assigned_subjects, status FROM staff WHERE role = 'Teacher'",
            conn
        )
        if teachers_df.empty:
            st.info("No Teacher accounts found. Create a Teacher account in the first tab.")
        else:
            st.dataframe(teachers_df, use_container_width=True)
            with st.form("assign_teacher_form"):
                t_map = {f"{r['full_name']} ({r['username']})": r['username'] for _, r in teachers_df.iterrows()}
                sel_teacher_label = st.selectbox("Select Teacher to Update Access", list(t_map.keys()))
                target_uname = t_map[sel_teacher_label]

                col_a1, col_a2 = st.columns(2)
                upd_classes = col_a1.multiselect("Grant Access to Class Levels", CLASS_LEVELS, default=CLASS_LEVELS)
                upd_subjects = col_a2.multiselect("Grant Access to Subjects", SUBJECT_LIST, default=SUBJECT_LIST)

                if st.form_submit_button("Save Teacher Assignments"):
                    c_str = ",".join(upd_classes) if upd_classes else "NONE"
                    s_str = ",".join(upd_subjects) if upd_subjects else "NONE"
                    conn.execute(
                        "UPDATE staff SET assigned_classes = ?, assigned_subjects = ? WHERE username = ?",
                        (c_str, s_str, target_uname)
                    )
                    conn.commit()
                    st.success(f"Updated class & subject permissions for {sel_teacher_label}!")
                    st.rerun()

    with tab_manage:
        staff_df = pd.read_sql_query(
            "SELECT staff_id, full_name, role, username, phone, salary, assigned_classes, assigned_subjects, status FROM staff",
            conn
        )
        st.dataframe(staff_df, use_container_width=True)
        if not staff_df.empty:
            with st.form("reset_staff_pwd_form"):
                c1, c2, c3 = st.columns(3)
                sel_user = c1.selectbox("Select Staff Username", staff_df["username"].dropna().tolist())
                new_staff_pwd = c2.text_input("New Password", value="123456")
                new_status = c3.selectbox("Account Status", ["Active", "Inactive"])
                if st.form_submit_button("Update Account"):
                    conn.execute(
                        "UPDATE staff SET password = ?, status = ? WHERE username = ?",
                        (new_staff_pwd.strip(), new_status, sel_user)
                    )
                    conn.commit()
                    st.success(f"Updated account `{sel_user}`!")
                    st.rerun()

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
            conn.execute(
                "INSERT INTO tasks (assigned_to, title, description, due_date, status, assigned_by) VALUES (?, ?, ?, ?, 'Pending', ?)",
                (assignee, title.strip(), desc.strip(), str(due), st.session_state.user_name)
            )
            conn.commit()
            st.success("Task assigned!")
    st.dataframe(pd.read_sql_query("SELECT * FROM tasks ORDER BY task_id DESC", conn), use_container_width=True)

def render_chat(conn, T):
    st.subheader(T["chat"])
    role = st.session_state.user_role
    user_name = st.session_state.user_name
    username = st.session_state.username

    tab_inbox, tab_send = st.tabs(["📥 Inbox & Conversations", "✉️ New Message / Parent Request"])

    with tab_inbox:
        all_msgs = pd.read_sql_query("SELECT * FROM messages ORDER BY msg_id DESC", conn)
        if all_msgs.empty:
            st.info("No messages or parent requests yet.")
        else:
            if role == "Administration":
                filtered_msgs = all_msgs
            elif role == "Parent":
                filtered_msgs = all_msgs[
                    (all_msgs["recipient"].isin(["Parents", "All", username, user_name])) |
                    (all_msgs["sender_name"] == user_name)
                ]
            else:
                role_targets = ["All Staff", role, username, user_name]
                if role == "Teacher":
                    role_targets.append("Teachers")
                filtered_msgs = all_msgs[
                    (all_msgs["recipient"].isin(role_targets)) |
                    (all_msgs["sender_name"] == user_name)
                ]

            if filtered_msgs.empty:
                st.info("Your inbox is currently empty.")
            else:
                st.dataframe(filtered_msgs, use_container_width=True)

                st.markdown("#### 💬 Quick Reply")
                with st.form("quick_reply_form"):
                    msg_options = {
                        f"#{r['msg_id']} | From {r['sender_name']} ({r['sender_role']}): {r['subject']}": r
                        for _, r in filtered_msgs.iterrows()
                    }
                    sel_msg_label = st.selectbox("Select Message to Reply To", list(msg_options.keys()))
                    reply_body = st.text_area("Write Reply *")
                    if st.form_submit_button("Send Reply") and reply_body.strip():
                        orig = msg_options[sel_msg_label]
                        reply_recipient = "Parents" if orig["sender_role"] == "Parent" else orig["sender_role"]
                        reply_subject = f"RE: {orig['subject']} (To: {orig['sender_name']})"
                        conn.execute(
                            "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (user_name, role, reply_recipient, reply_subject, reply_body.strip(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                        )
                        conn.commit()
                        st.success("Reply sent!")
                        st.rerun()

    with tab_send:
        if role == "Parent":
            children_df = pd.read_sql_query(
                "SELECT student_name, grade FROM students WHERE TRIM(parent_phone) = ?",
                conn, params=(username,)
            )
            child_options = [f"{r['student_name']} ({r['grade']})" for _, r in children_df.iterrows()] or ["My Child"]
            with st.form("parent_req_form"):
                c1, c2, c3 = st.columns(3)
                sel_child = c1.selectbox("Regarding Student", child_options)
                req_type = c2.selectbox("Request Type", ["Permission / Absence Request", "Late Arrival Notice", "Fee / Payment Inquiry", "General Message"])
