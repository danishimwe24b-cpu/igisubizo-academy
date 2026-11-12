import datetime
import pandas as pd
import streamlit as st

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
                recipient = c3.selectbox("Send To", ["Administration", "Register Officer", "Teachers"])
                body = st.text_area("Request Details *")
                if st.form_submit_button("Submit Request") and body.strip():
                    full_subject = f"[{req_type}] - {sel_child}"
                    conn.execute(
                        "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (user_name, "Parent", recipient, full_subject, body.strip(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                    )
                    conn.commit()
                    st.success("Your request has been sent!")
                    st.rerun()
        else:
            with st.form("staff_msg_form"):
                c1, c2 = st.columns(2)
                recipient = c1.selectbox("Send To", ["All Staff", "Administration", "Register Officer", "Teachers", "Parents"])
                subject = c2.text_input("Subject *")
                body = st.text_area("Message Content *")
                if st.form_submit_button("Send Message") and body.strip():
                    conn.execute(
                        "INSERT INTO messages (sender_name, sender_role, recipient, subject, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (user_name, role, recipient, subject.strip() or "General Notice", body.strip(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                    )
                    conn.commit()
                    st.success("Message sent!")
                    st.rerun()

def render_change_pwd(conn, T):
    st.subheader(T["change_pwd"])
    if st.session_state.user_role == "Parent":
        st.info("Parent portal uses your registered phone number and default PIN (`1234`). Contact the Register Officer to update your phone number.")
        return

    with st.form("pwd_form"):
        curr_pwd = st.text_input("Current Password", type="password")
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        if st.form_submit_button(T["save"]):
            df_check = pd.read_sql_query(
                "SELECT * FROM staff WHERE LOWER(TRIM(username)) = ? AND TRIM(password) = ?",
                conn, params=(st.session_state.username.lower(), curr_pwd.strip())
            )
            if df_check.empty:
                st.error("Current password is incorrect.")
            elif not new_pwd.strip() or new_pwd.strip() != confirm_pwd.strip():
                st.error("New passwords do not match or are empty.")
            else:
                conn.execute(
                    "UPDATE staff SET password = ? WHERE LOWER(TRIM(username)) = ?",
                    (new_pwd.strip(), st.session_state.username.lower())
                )
                conn.commit()
                st.success("Password updated successfully!")
