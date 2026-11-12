import pandas as pd
import streamlit as st
from config import TRANSLATIONS
from database import get_conn, init_db
from pages_academic import render_dashboard, render_students, render_grades, render_report_card, render_attendance
from pages_admin import render_conduct, render_payments, render_finance, render_reports, render_staff, render_tasks, render_chat, render_change_pwd

st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = True
    st.session_state.user_name = "Head Administrator"
    st.session_state.user_role = "Administration"
    st.session_state.username = "admin"

if "lang" not in st.session_state:
    st.session_state.lang = "English"

col_spacer, col_lang = st.columns(2)
with col_lang:
    st.session_state.lang = st.selectbox("🌐 Language / Ururimi", list(TRANSLATIONS.keys()), index=list(TRANSLATIONS.keys()).index(st.session_state.lang))

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
PAGES = {
    "dashboard": render_dashboard, "students": render_students, "grades": render_grades,
    "report_card": render_report_card, "attendance": render_attendance, "conduct": render_conduct,
    "payments": render_payments, "finance": render_finance, "reports": render_reports,
    "staff": render_staff, "tasks": render_tasks, "chat": render_chat, "change_pwd": render_change_pwd
}
PAGES[active_page](conn, T)
conn.close()
