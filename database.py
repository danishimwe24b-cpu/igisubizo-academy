import io
import sqlite3
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def get_conn():
    return sqlite3.connect('igisubizo_academy.db', timeout=15, check_same_thread=False)

def ensure_column(cursor, table_name, column_name, column_def):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_cols = [row for row in cursor.fetchall()]
    if column_name not in existing_cols:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        grade TEXT NOT NULL,
        parent_name TEXT,
        parent_phone TEXT,
        parent_email TEXT,
        status TEXT DEFAULT 'Active',
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        subject TEXT,
        assessment_type TEXT DEFAULT 'Exam',
        score REAL,
        max_score REAL DEFAULT 100,
        term TEXT,
        date TEXT,
        teacher TEXT,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')
    ensure_column(c, "grades", "assessment_type", "TEXT DEFAULT 'Exam'")
    ensure_column(c, "grades", "max_score", "REAL DEFAULT 100")

    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        teacher TEXT,
        notes TEXT,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        month_year TEXT,
        amount REAL DEFAULT 5000,
        paid_date TEXT,
        recorded_by TEXT,
        UNIQUE(student_id, month_year),
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS monthly_budgets (
        budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_year TEXT,
        category TEXT,
        allocated_amount REAL,
        spent_amount REAL DEFAULT 0,
        description TEXT,
        date TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS conduct (
        conduct_id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_type TEXT,
        person_name TEXT,
        grade_or_role TEXT,
        incident_type TEXT,
        points_change INTEGER,
        notes TEXT,
        date TEXT,
        recorded_by TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS teacher_reports (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_name TEXT,
        grade TEXT,
        week_ending TEXT,
        topics_covered TEXT,
        challenges TEXT,
        submitted_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS staff (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        role TEXT,
        username TEXT UNIQUE,
        password TEXT,
        phone TEXT,
        salary REAL,
        status TEXT DEFAULT 'Active'
    )''')
    for col, col_def in [
        ("full_name", "TEXT"), ("role", "TEXT"), ("username", "TEXT"),
        ("password", "TEXT"), ("phone", "TEXT"), ("salary", "REAL DEFAULT 50000"),
        ("status", "TEXT DEFAULT 'Active'")
    ]:
        ensure_column(c, "staff", col, col_def)

    c.execute("PRAGMA table_info(staff)")
    staff_cols = [row for row in c.fetchall()]
    if "name" in staff_cols:
        c.execute("UPDATE staff SET full_name = name WHERE full_name IS NULL")

    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        assigned_to TEXT,
        title TEXT,
        description TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'Pending',
        assigned_by TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_name TEXT,
        sender_role TEXT,
        recipient TEXT,
        subject TEXT,
        message TEXT,
        created_at TEXT
    )''')

    c.execute("SELECT COUNT(*) FROM staff WHERE username = 'admin'")
    if c.fetchone() == 0:
        if "name" in staff_cols:
            c.execute(
                "INSERT OR IGNORE INTO staff (name, full_name, role, username, password, phone, salary, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')",
                ("Head Administrator", "Head Administrator", "Administration", "admin", "admin123", "0780000000", 60000)
            )
        else:
            c.execute(
                "INSERT OR IGNORE INTO staff (full_name, role, username, password, phone, salary, status) VALUES (?, ?, ?, ?, ?, ?, 'Active')",
                ("Head Administrator", "Administration", "admin", "admin123", "0780000000", 60000)
            )

    conn.commit()
    conn.close()

def generate_report_card_pdf(student_row, grades_df, term):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("<b>IGISUBIZO ACADEMY</b>", styles['Title']),
        Paragraph(f"Official Student Report Card - {term}", styles['Heading2']),
        Spacer(1, 12),
        Paragraph(
            f"<b>Student Name:</b> {student_row['student_name']}<br/>"
            f"<b>Class Level:</b> {student_row['grade']}<br/>"
            f"<b>Parent / Guardian:</b> {student_row['parent_name']} ({student_row['parent_phone']})<br/>"
            f"<b>Date Issued:</b> {datetime.date.today()}",
            styles['Normal']
        ),
        Spacer(1, 16)
    ]

    data = [["Subject", "Assessment", "Score", "Max Score", "Percentage"]]
    total_score, total_max = 0, 0
    for _, row in grades_df.iterrows():
        pct = (row['score'] / row['max_score'] * 100) if row['max_score'] else 0
        data.append([row['subject'], row['assessment_type'], f"{row['score']:.1f}", f"{row['max_score']:.1f}", f"{pct:.1f}%"])
        total_score += row['score']
        total_max += row['max_score']

    overall_pct = (total_score / total_max * 100) if total_max > 0 else 0
    data.append(["TOTAL / AVERAGE", "-", f"{total_score:.1f}", f"{total_max:.1f}", f"{overall_pct:.1f}%"])

    table = Table(data, colWidths=)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f5132")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.extend([table, Spacer(1, 24), Paragraph("Head Administrator Signature: _______________________", styles['Normal'])])
    doc.build(elements)
    buffer.seek(0)
    return buffer
