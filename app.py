from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'attendance-secret-key-2024')

# PostgreSQL configuration
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
DB_HOST = os.environ.get('DB_HOST', 'db')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'attendance_db')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ──────────────────────────── Models ────────────────────────────

class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    catalogues = db.relationship('Catalogue', backref='teacher', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Catalogue(db.Model):
    __tablename__ = 'catalogues'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    students = db.relationship('Student', backref='catalogue', lazy=True, cascade='all, delete-orphan')


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    roll_number = db.Column(db.String(30), nullable=False)
    catalogue_id = db.Column(db.Integer, db.ForeignKey('catalogues.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attendance_records = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(10), nullable=False, default='absent')  # 'present' or 'absent'
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('student_id', 'date', name='unique_student_date'),)

# ──────────────────────────── Helpers ────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'teacher_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def seed_demo_teacher():
    if not Teacher.query.filter_by(username='teacher').first():
        t = Teacher(username='teacher', full_name='Demo Teacher')
        t.set_password('password123')
        db.session.add(t)
        db.session.commit()

# ──────────────────────────── Routes ────────────────────────────

@app.route('/')
def index():
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        teacher = Teacher.query.filter_by(username=username).first()
        if teacher and teacher.check_password(password):
            session['teacher_id'] = teacher.id
            session['teacher_name'] = teacher.full_name
            flash(f'Welcome back, {teacher.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not username or not full_name or not password:
            flash('All fields are required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif Teacher.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
        else:
            t = Teacher(username=username, full_name=full_name)
            t.set_password(password)
            db.session.add(t)
            db.session.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    teacher = Teacher.query.get(session['teacher_id'])
    catalogues = Catalogue.query.filter_by(teacher_id=teacher.id).all()
    stats = []
    for cat in catalogues:
        total_students = len(cat.students)
        today_records = Attendance.query.join(Student).filter(
            Student.catalogue_id == cat.id,
            Attendance.date == date.today()
        ).all()
        present_today = sum(1 for r in today_records if r.status == 'present')
        stats.append({
            'catalogue': cat,
            'total_students': total_students,
            'present_today': present_today
        })
    return render_template('dashboard.html', teacher=teacher, stats=stats, today=date.today())


@app.route('/catalogue/new', methods=['GET', 'POST'])
@login_required
def new_catalogue():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        if not name or not subject:
            flash('Class name and subject are required.', 'error')
        else:
            cat = Catalogue(name=name, subject=subject, teacher_id=session['teacher_id'])
            db.session.add(cat)
            db.session.commit()
            flash(f'Catalogue "{name}" created!', 'success')
            return redirect(url_for('view_catalogue', catalogue_id=cat.id))
    return render_template('new_catalogue.html')


@app.route('/catalogue/<int:catalogue_id>')
@login_required
def view_catalogue(catalogue_id):
    cat = Catalogue.query.filter_by(id=catalogue_id, teacher_id=session['teacher_id']).first_or_404()
    selected_date = request.args.get('date', str(date.today()))
    try:
        sel_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        sel_date = date.today()

    students = Student.query.filter_by(catalogue_id=cat.id).order_by(Student.roll_number).all()
    attendance_map = {}
    for rec in Attendance.query.filter(
        Attendance.date == sel_date,
        Attendance.student_id.in_([s.id for s in students])
    ).all():
        attendance_map[rec.student_id] = rec.status

    # Build attendance history for last 7 dates that have records
    history_dates = db.session.query(Attendance.date).join(Student).filter(
        Student.catalogue_id == cat.id
    ).distinct().order_by(Attendance.date.desc()).limit(7).all()
    history_dates = [r.date for r in history_dates]

    return render_template('catalogue.html',
                           cat=cat, students=students,
                           attendance_map=attendance_map,
                           selected_date=sel_date,
                           history_dates=history_dates,
                           today=date.today())


@app.route('/catalogue/<int:catalogue_id>/add_student', methods=['POST'])
@login_required
def add_student(catalogue_id):
    cat = Catalogue.query.filter_by(id=catalogue_id, teacher_id=session['teacher_id']).first_or_404()
    name = request.form.get('name', '').strip()
    roll = request.form.get('roll_number', '').strip()
    if not name or not roll:
        flash('Student name and roll number are required.', 'error')
    else:
        existing = Student.query.filter_by(catalogue_id=cat.id, roll_number=roll).first()
        if existing:
            flash(f'Roll number {roll} already exists in this catalogue.', 'error')
        else:
            s = Student(name=name, roll_number=roll, catalogue_id=cat.id)
            db.session.add(s)
            db.session.commit()
            flash(f'Student "{name}" added.', 'success')
    return redirect(url_for('view_catalogue', catalogue_id=catalogue_id))


@app.route('/catalogue/<int:catalogue_id>/delete_student/<int:student_id>', methods=['POST'])
@login_required
def delete_student(catalogue_id, student_id):
    Catalogue.query.filter_by(id=catalogue_id, teacher_id=session['teacher_id']).first_or_404()
    s = Student.query.filter_by(id=student_id, catalogue_id=catalogue_id).first_or_404()
    db.session.delete(s)
    db.session.commit()
    flash(f'Student "{s.name}" removed.', 'success')
    return redirect(url_for('view_catalogue', catalogue_id=catalogue_id))


@app.route('/catalogue/<int:catalogue_id>/mark_attendance', methods=['POST'])
@login_required
def mark_attendance(catalogue_id):
    Catalogue.query.filter_by(id=catalogue_id, teacher_id=session['teacher_id']).first_or_404()
    sel_date_str = request.form.get('date', str(date.today()))
    try:
        sel_date = datetime.strptime(sel_date_str, '%Y-%m-%d').date()
    except ValueError:
        sel_date = date.today()

    students = Student.query.filter_by(catalogue_id=catalogue_id).all()
    present_ids = set(map(int, request.form.getlist('present_students')))

    for s in students:
        status = 'present' if s.id in present_ids else 'absent'
        existing = Attendance.query.filter_by(student_id=s.id, date=sel_date).first()
        if existing:
            existing.status = status
            existing.marked_at = datetime.utcnow()
        else:
            rec = Attendance(student_id=s.id, date=sel_date, status=status)
            db.session.add(rec)
    db.session.commit()
    flash(f'Attendance saved for {sel_date.strftime("%B %d, %Y")}.', 'success')
    return redirect(url_for('view_catalogue', catalogue_id=catalogue_id, date=sel_date_str))


@app.route('/catalogue/<int:catalogue_id>/delete', methods=['POST'])
@login_required
def delete_catalogue(catalogue_id):
    cat = Catalogue.query.filter_by(id=catalogue_id, teacher_id=session['teacher_id']).first_or_404()
    name = cat.name
    db.session.delete(cat)
    db.session.commit()
    flash(f'Catalogue "{name}" deleted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/catalogue/<int:catalogue_id>/report')
@login_required
def attendance_report(catalogue_id):
    cat = Catalogue.query.filter_by(id=catalogue_id, teacher_id=session['teacher_id']).first_or_404()
    students = Student.query.filter_by(catalogue_id=cat.id).order_by(Student.roll_number).all()
    report = []
    for s in students:
        total = Attendance.query.filter_by(student_id=s.id).count()
        present = Attendance.query.filter_by(student_id=s.id, status='present').count()
        pct = round((present / total * 100), 1) if total > 0 else 0
        report.append({'student': s, 'total': total, 'present': present, 'absent': total - present, 'pct': pct})
    return render_template('report.html', cat=cat, report=report)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_demo_teacher()
    app.run(debug=True, host='0.0.0.0', port=5000)
