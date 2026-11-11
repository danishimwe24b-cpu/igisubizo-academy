import streamlit as st
import pandas as pd
import sqlite3
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
import io

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect('igisubizo_academy.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            grade TEXT NOT NULL,
            parent_name TEXT,
            parent_phone TEXT,
            parent_email TEXT,
            status TEXT DEFAULT 'Active',
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject TEXT,
            score REAL,
            max_score REAL DEFAULT 100,
            term TEXT,
            date TEXT,
            teacher TEXT,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT,
            teacher TEXT,
            notes TEXT,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_conn():
    return sqlite3.connect('igisubizo_academy.db')

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="Igisubizo Academy", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0B6E4F 0%, #0A3D62 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🎓 IGISUBIZO ACADEMY</h1>
    <p>Student Information & Report Card System</p>
</div>
""", unsafe_allow_html=True)

# ==================== SIDEBAR ====================
menu = st.sidebar.radio("Menu", [
    "Dashboard",
    "Students",
    "Enter Grades",
    "Attendance",
    "Generate Report Card"
])

# ==================== DASHBOARD ====================
if menu == "Dashboard":
    st.subheader("📊 Dashboard")
    conn = get_conn()
    students_df = pd.read_sql_query("SELECT * FROM students WHERE status='Active'", conn)
    grades_df = pd.read_sql_query("SELECT * FROM grades", conn)
    attendance_df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()

    col1, col2, col3 = st.columns(3)
    col1.metric("Active Students", len(students_df))
    col2.metric("Grades Recorded", len(grades_df))
    col3.metric("Attendance Records", len(attendance_df))

    if not students_df.empty:
        st.write("### Students per Grade")
        st.bar_chart(students_df['grade'].value_counts().sort_index())
        st.write("### Recent Students")
        st.dataframe(students_df[['student_name', 'grade', 'parent_name', 'parent_phone']].tail(10), use_container_width=True)
    else:
        st.info("No students yet. Go to Students menu to add.")

# ==================== STUDENTS ====================
elif menu == "Students":
    st.subheader("👥 Student Information")

    with st.expander("➕ Register New Student", expanded=True):
        with st.form("add_student", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Student Full Name *")
            grade = col2.selectbox("Grade *", ["P1", "P2", "P3", "P4", "P5", "P6"])
            parent_name = col1.text_input("Parent / Guardian Name")
            parent_phone = col2.text_input("Parent Phone Number")
            parent_email = col1.text_input("Parent Email")
            submitted = st.form_submit_button("Save Student")

            if submitted:
                if name and grade:
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO students (student_name, grade, parent_name, parent_phone, parent_email, status, created_at)
                        VALUES (?, ?, ?, ?, ?, 'Active', ?)
                    ''', (name, grade, parent_name, parent_phone, parent_email, datetime.date.today().isoformat()))
                    conn.commit()
                    conn.close()
                    st.success(f"Student {name} registered successfully!")
                else:
                    st.error("Student Name and Grade are required.")

    st.write("### All Students")
    conn = get_conn()
    students_df = pd.read_sql_query("SELECT * FROM students ORDER BY grade, student_name", conn)
    conn.close()
    if not students_df.empty:
        st.dataframe(students_df[['student_id', 'student_name', 'grade', 'parent_name', 'parent_phone', 'parent_email', 'status']], use_container_width=True)
    else:
        st.warning("No students found.")

# ==================== ENTER GRADES ====================
elif menu == "Enter Grades":
    st.subheader("📝 Enter Grades")
    conn = get_conn()
    students_df = pd.read_sql_query("SELECT student_id, student_name, grade FROM students WHERE status='Active' ORDER BY grade, student_name", conn)
    conn.close()

    if students_df.empty:
        st.error("Please register students first.")
    else:
        students_df['display'] = students_df['student_name'] + " (" + students_df['grade'] + ")"
        student_dict = dict(zip(students_df['display'], students_df['student_id']))

        with st.form("enter_grade", clear_on_submit=True):
            selected = st.selectbox("Select Student", list(student_dict.keys()))
            col1, col2 = st.columns(2)
            subject = col1.selectbox("Subject", ["English", "Kinyarwanda", "Mathematics", "SET", "SST"])
            score = col2.number_input("Score", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            term = col1.selectbox("Term", ["Term 1", "Term 2", "Term 3"])
            teacher = col2.text_input("Teacher Name")
            date = st.date_input("Date", datetime.date.today())

            if st.form_submit_button("Save Grade"):
                sid = student_dict[selected]
                conn = get_conn()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO grades (student_id, subject, score, max_score, term, date, teacher)
                    VALUES (?, ?, ?, 100, ?, ?, ?)
                ''', (sid, subject, score, term, date.isoformat(), teacher))
                conn.commit()
                conn.close()
                st.success(f"Grade saved for {selected} — {subject}: {score}")

        st.write("### Recent Grades")
        conn = get_conn()
        recent = pd.read_sql_query('''
            SELECT g.date, s.student_name, s.grade, g.subject, g.score, g.term, g.teacher
            FROM grades g JOIN students s ON g.student_id = s.student_id
            ORDER BY g.grade_id DESC LIMIT 15
        ''', conn)
        conn.close()
        if not recent.empty:
            st.dataframe(recent, use_container_width=True)

# ==================== ATTENDANCE ====================
elif menu == "Attendance":
    st.subheader("📅 Attendance")
    conn = get_conn()
    students_df = pd.read_sql_query("SELECT student_id, student_name, grade FROM students WHERE status='Active' ORDER BY grade, student_name", conn)
    conn.close()

    if students_df.empty:
        st.error("Please register students first.")
    else:
        selected_grade = st.selectbox("Select Grade", ["P1", "P2", "P3", "P4", "P5", "P6"])
        date = st.date_input("Date", datetime.date.today())
        teacher = st.text_input("Teacher Name")

        grade_students = students_df[students_df['grade'] == selected_grade]

        if grade_students.empty:
            st.warning(f"No students in {selected_grade}")
        else:
            st.write(f"### Students in {selected_grade}")
            status_options = ["Present", "Absent", "Late", "Permission"]
            attendance_data = []

            for _, row in grade_students.iterrows():
                col1, col2 = st.columns([3, 2])
                col1.write(f"**{row['student_name']}**")
                status = col2.selectbox("Status", status_options, key=f"att_{row['student_id']}", label_visibility="collapsed")
                attendance_data.append({"student_id": row['student_id'], "status": status})

            if st.button("Save Attendance"):
                conn = get_conn()
                c = conn.cursor()
                for item in attendance_data:
                    c.execute('''
                        INSERT INTO attendance (student_id, date, status, teacher, notes)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (item['student_id'], date.isoformat(), item['status'], teacher, ""))
                conn.commit()
                conn.close()
                st.success(f"Attendance saved for {selected_grade}")

# ==================== GENERATE REPORT CARD ====================
elif menu == "Generate Report Card":
    st.subheader("📄 Generate Report Card")
    conn = get_conn()
    students_df = pd.read_sql_query("SELECT student_id, student_name, grade, parent_name, parent_phone FROM students WHERE status='Active' ORDER BY grade, student_name", conn)
    conn.close()

    if students_df.empty:
        st.error("No students available.")
    else:
        students_df['display'] = students_df['student_name'] + " (" + students_df['grade'] + ")"
        student_dict = dict(zip(students_df['display'], students_df['student_id']))

        selected = st.selectbox("Select Student", list(student_dict.keys()))
        term_filter = st.selectbox("Term", ["All Terms", "Term 1", "Term 2", "Term 3"])

        if st.button("Generate & Download Report Card", type="primary"):
            sid = student_dict[selected]
            conn = get_conn()
            student = pd.read_sql_query(f"SELECT * FROM students WHERE student_id = {sid}", conn).iloc[0]

            if term_filter == "All Terms":
                grades = pd.read_sql_query(f"SELECT * FROM grades WHERE student_id = {sid}", conn)
            else:
                grades = pd.read_sql_query(f"SELECT * FROM grades WHERE student_id = {sid} AND term = '{term_filter}'", conn)

            # Position in class
            same_grade = pd.read_sql_query(f"SELECT student_id FROM students WHERE grade = '{student['grade']}' AND status='Active'", conn)
            averages = []
            for other_id in same_grade['student_id']:
                other_grades = pd.read_sql_query(f"SELECT score FROM grades WHERE student_id = {other_id}", conn)
                if not other_grades.empty:
                    averages.append({"student_id": other_id, "average": other_grades['score'].mean()})
            conn.close()

            position = "N/A"
            total_in_class = len(same_grade)
            if averages:
                avg_df = pd.DataFrame(averages).sort_values("average", ascending=False).reset_index(drop=True)
                for idx, row in avg_df.iterrows():
                    if row['student_id'] == sid:
                        position = f"{idx + 1} out of {total_in_class}"
                        break

            # Create PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#0B6E4F"), alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Bold")
            subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor("#0A3D62"), alignment=TA_CENTER, spaceAfter=12)
            normal = ParagraphStyle('NormalCustom', parent=styles['Normal'], fontSize=10, leading=14)
            header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, fontName="Helvetica-Bold", textColor=colors.white)

            story = []
            story.append(Paragraph("IGISUBIZO ACADEMY", title_style))
            story.append(Paragraph("Student Academic Report Card", subtitle_style))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0B6E4F"), spaceAfter=12))

            info_text = f"""
            <b>Student Name:</b> {student['student_name']}<br/>
            <b>Grade / Level:</b> {student['grade']}<br/>
            <b>Parent / Guardian:</b> {student['parent_name'] or '—'}<br/>
            <b>Parent Phone:</b> {student['parent_phone'] or '—'}<br/>
            <b>Report Date:</b> {datetime.date.today().strftime('%d %B %Y')}<br/>
            <b>Position in Class:</b> {position}
            """
            story.append(Paragraph(info_text, normal))
            story.append(Spacer(1, 15))
            story.append(Paragraph("<b>Subject Results</b>", styles['Heading3']))
            story.append(Spacer(1, 6))

            subjects = ["English", "Kinyarwanda", "Mathematics", "SET", "SST"]
            table_data = [[Paragraph("Subject", header_style), Paragraph("Score", header_style),
                           Paragraph("Max", header_style), Paragraph("Term", header_style), Paragraph("Teacher", header_style)]]

            total_score = 0
            count = 0

            if not grades.empty:
                for subj in subjects:
                    subj_grades = grades[grades['subject'] == subj]
                    if not subj_grades.empty:
                        avg_score = subj_grades['score'].mean()
                        latest = subj_grades.iloc[-1]
                        table_data.append([
                            Paragraph(subj, normal),
                            Paragraph(f"{avg_score:.1f}", normal),
                            Paragraph("100", normal),
                            Paragraph(str(latest['term']), normal),
                            Paragraph(str(latest['teacher'] or "—"), normal)
                        ])
                        total_score += avg_score
                        count += 1
                    else:
                        table_data.append([Paragraph(subj, normal), Paragraph("—", normal), Paragraph("100", normal), Paragraph("—", normal), Paragraph("—", normal)])
            else:
                for subj in subjects:
                    table_data.append([Paragraph(subj, normal), Paragraph("—", normal), Paragraph("100", normal), Paragraph("—", normal), Paragraph("—", normal)])

            t = Table(table_data, colWidths=[3.5*cm, 2.5*cm, 2*cm, 2.5*cm, 4*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0B6E4F")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F0F7F4")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#0A3D62")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(t)
            story.append(Spacer(1, 15))

            average = (total_score / count) if count > 0 else 0
            summary = f"""
            <b>Average Score:</b> {average:.1f} / 100<br/>
            <b>Position in Class:</b> {position}<br/>
            <b>Subjects Recorded:</b> {count}
            """
            story.append(Paragraph(summary, normal))
            story.append(Spacer(1, 20))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0A3D62"), spaceAfter=10))
            story.append(Paragraph("<i>Generated by Igisubizo Academy Student System.</i>", ParagraphStyle('Footer', parent=normal, fontSize=8, textColor=colors.grey)))

            doc.build(story)
            buffer.seek(0)

            file_name = f"ReportCard_{student['student_name'].replace(' ', '_')}_{student['grade']}.pdf"
            st.download_button("⬇️ Download Report Card (PDF)", data=buffer, file_name=file_name, mime="application/pdf")
            st.success("Report Card ready! Click the download button above.")
