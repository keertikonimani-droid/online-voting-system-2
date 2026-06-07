from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(minutes=10)

DATABASE = 'voting.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS elections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            party TEXT,
            election_id INTEGER NOT NULL,
            FOREIGN KEY (election_id) REFERENCES elections(id)
        );

        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            election_id INTEGER NOT NULL,
            candidate_id INTEGER NOT NULL,
            voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (election_id) REFERENCES elections(id),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id),
            UNIQUE(user_id, election_id)
        );
    ''')

    admin = conn.execute('SELECT * FROM users WHERE is_admin = 1').fetchone()
    if not admin:
        seed_dummy_data(conn)

    conn.commit()
    conn.close()


def seed_dummy_data(conn):
    import random
    random.seed(42)

    now = datetime.now()
    password = generate_password_hash('password123')

    # Admin user
    conn.execute(
        'INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)',
        ('Admin', 'admin@voting.gov', generate_password_hash('admin123'), 1)
    )

    # 30 student voters (class assignment style)
    students = [
        ('Keerti', '1DA25CS078'), ('Hullamma', '1DA25CS067'),
        ('Disha Naskar', '1DA25CS053'), ('Dhanyashree', '1DA25CS048'),
        ('Aarav Sharma', '1DA25CS001'), ('Ananya Gupta', '1DA25CS002'),
        ('Rohan Mehta', '1DA25CS003'), ('Priya Patel', '1DA25CS004'),
        ('Vikram Singh', '1DA25CS005'), ('Neha Reddy', '1DA25CS006'),
        ('Arjun Kumar', '1DA25CS007'), ('Kavya Nair', '1DA25CS008'),
        ('Aditya Joshi', '1DA25CS009'), ('Sneha Iyer', '1DA25CS010'),
        ('Rahul Verma', '1DA25CS011'), ('Divya Rao', '1DA25CS012'),
        ('Siddharth Das', '1DA25CS013'), ('Meera Krishnan', '1DA25CS014'),
        ('Nikhil Hegde', '1DA25CS015'), ('Pooja Shetty', '1DA25CS016'),
        ('Amit Kulkarni', '1DA25CS017'), ('Riya Deshmukh', '1DA25CS018'),
        ('Varun Patil', '1DA25CS019'), ('Ishita Bhat', '1DA25CS020'),
        ('Kunal Gowda', '1DA25CS021'), ('Tanvi Agarwal', '1DA25CS022'),
        ('Harsh Mishra', '1DA25CS023'), ('Swati Pandey', '1DA25CS024'),
        ('Manish Tiwari', '1DA25CS025'), ('Anjali Saxena', '1DA25CS026'),
    ]

    for name, roll in students:
        email = f"{roll.lower()}@college.edu"
        conn.execute(
            'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
            (name, email, password)
        )

    # Election 1: Student Council President 2026
    conn.execute(
        'INSERT INTO elections (title, description, start_date, end_date) VALUES (?, ?, ?, ?)',
        ('Student Council 2026', 'Vote for your student council president',
         now.isoformat(), (now + timedelta(days=2)).isoformat())
    )

    # Election 2: Class Representative
    conn.execute(
        'INSERT INTO elections (title, description, start_date, end_date) VALUES (?, ?, ?, ?)',
        ('Class Representative', 'Choose your class representative for CS section',
         now.isoformat(), (now + timedelta(days=5)).isoformat())
    )

    # Election 3: Best Project Award (already ended — for results demo)
    conn.execute(
        'INSERT INTO elections (title, description, start_date, end_date) VALUES (?, ?, ?, ?)',
        ('Best Project Award', 'Vote for the best mini project of the semester',
         (now - timedelta(days=5)).isoformat(), (now + timedelta(days=3)).isoformat())
    )

    # Candidates for Election 1 (Student Council) — matches PPT slide
    conn.executemany(
        'INSERT INTO candidates (name, party, election_id) VALUES (?, ?, ?)',
        [
            ('Candidate A', 'Independent', 1),
            ('Candidate B', 'Democratic Party', 1),
            ('Candidate C', 'Green Party', 1),
            ('Candidate D', 'Progressive Party', 1),
        ]
    )

    # Candidates for Election 2 (Class Rep)
    conn.executemany(
        'INSERT INTO candidates (name, party, election_id) VALUES (?, ?, ?)',
        [
            ('Aarav Sharma', 'Independent', 2),
            ('Ananya Gupta', 'Student Alliance', 2),
            ('Rohan Mehta', 'Unity Party', 2),
        ]
    )

    # Candidates for Election 3 (Best Project)
    conn.executemany(
        'INSERT INTO candidates (name, party, election_id) VALUES (?, ?, ?)',
        [
            ('Online Voting System', 'Team Keerti', 3),
            ('Smart Attendance', 'Team Aarav', 3),
            ('Chat Application', 'Team Vikram', 3),
            ('Weather Dashboard', 'Team Neha', 3),
        ]
    )

    # Pre-cast votes for Election 1 — ~45%, 35%, 15%, 5% split (PPT style)
    # user_ids 2-31 are the 30 students (admin is id 1)
    election1_votes = (
        [1] * 12 +  # Candidate A: 12 votes (45%)
        [2] * 9 +   # Candidate B: 9 votes (35%)
        [3] * 4 +   # Candidate C: 4 votes (15%)
        [4] * 1      # Candidate D: 1 vote (5%)
    )
    random.shuffle(election1_votes)
    for i, candidate_id in enumerate(election1_votes[:26]):
        user_id = i + 2  # students start at id 2
        conn.execute(
            'INSERT INTO votes (user_id, election_id, candidate_id) VALUES (?, ?, ?)',
            (user_id, 1, candidate_id)
        )

    # Pre-cast votes for Election 3 (Best Project) — all 30 voted
    election3_votes = (
        [8] * 14 +   # Online Voting System: 14 votes (47%)
        [9] * 9 +    # Smart Attendance: 9 votes (30%)
        [10] * 5 +   # Chat Application: 5 votes (17%)
        [11] * 2     # Weather Dashboard: 2 votes (7%)
    )
    random.shuffle(election3_votes)
    for i, candidate_id in enumerate(election3_votes[:30]):
        user_id = i + 2
        conn.execute(
            'INSERT INTO votes (user_id, election_id, candidate_id) VALUES (?, ?, ?)',
            (user_id, 3, candidate_id)
        )


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = bool(user['is_admin'])

            if user['is_admin']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        conn = get_db()
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            conn.close()
            flash('Email already registered.', 'error')
            return render_template('register.html')

        conn.execute(
            'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
            (name, email, generate_password_hash(password))
        )
        conn.commit()
        conn.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    elections = conn.execute(
        'SELECT * FROM elections WHERE is_active = 1 AND end_date > ?',
        (datetime.now().isoformat(),)
    ).fetchall()

    voted_elections = conn.execute(
        'SELECT election_id FROM votes WHERE user_id = ?',
        (session['user_id'],)
    ).fetchall()
    voted_ids = [v['election_id'] for v in voted_elections]
    conn.close()

    return render_template('dashboard.html', elections=elections, voted_ids=voted_ids)


@app.route('/vote/<int:election_id>', methods=['GET', 'POST'])
@login_required
def vote(election_id):
    conn = get_db()

    existing_vote = conn.execute(
        'SELECT id FROM votes WHERE user_id = ? AND election_id = ?',
        (session['user_id'], election_id)
    ).fetchone()
    if existing_vote:
        conn.close()
        flash('You have already voted in this election.', 'error')
        return redirect(url_for('dashboard'))

    election = conn.execute('SELECT * FROM elections WHERE id = ? AND is_active = 1', (election_id,)).fetchone()
    if not election:
        conn.close()
        flash('Election not found or has ended.', 'error')
        return redirect(url_for('dashboard'))

    candidates = conn.execute('SELECT * FROM candidates WHERE election_id = ?', (election_id,)).fetchall()

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        if not candidate_id:
            flash('Please select a candidate.', 'error')
            return render_template('vote.html', election=election, candidates=candidates)

        conn.execute(
            'INSERT INTO votes (user_id, election_id, candidate_id) VALUES (?, ?, ?)',
            (session['user_id'], election_id, int(candidate_id))
        )
        conn.commit()
        conn.close()

        flash('Your vote has been submitted successfully!', 'success')
        return redirect(url_for('confirmation', election_id=election_id))

    conn.close()
    return render_template('vote.html', election=election, candidates=candidates)


@app.route('/confirmation/<int:election_id>')
@login_required
def confirmation(election_id):
    code = secrets.token_hex(8).upper()
    return render_template('confirmation.html', code=code, election_id=election_id)


@app.route('/results/<int:election_id>')
@login_required
def results(election_id):
    conn = get_db()
    election = conn.execute('SELECT * FROM elections WHERE id = ?', (election_id,)).fetchone()
    candidates = conn.execute('''
        SELECT c.id, c.name, c.party, COUNT(v.id) as vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id
        WHERE c.election_id = ?
        GROUP BY c.id
        ORDER BY vote_count DESC
    ''', (election_id,)).fetchall()

    total_votes = sum(c['vote_count'] for c in candidates)
    conn.close()

    return render_template('results.html', election=election, candidates=candidates, total_votes=total_votes)


@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db()
    total_voters = conn.execute('SELECT COUNT(*) as cnt FROM users WHERE is_admin = 0').fetchone()['cnt']
    total_votes = conn.execute('SELECT COUNT(*) as cnt FROM votes').fetchone()['cnt']
    unique_voters = conn.execute('SELECT COUNT(DISTINCT user_id) as cnt FROM votes').fetchone()['cnt']
    elections = conn.execute('SELECT * FROM elections').fetchall()

    election_stats = []
    for election in elections:
        candidates = conn.execute('''
            SELECT c.name, c.party, COUNT(v.id) as vote_count
            FROM candidates c
            LEFT JOIN votes v ON c.id = v.candidate_id
            WHERE c.election_id = ?
            GROUP BY c.id
            ORDER BY vote_count DESC
        ''', (election['id'],)).fetchall()
        election_stats.append({
            'election': election,
            'candidates': candidates,
            'total': sum(c['vote_count'] for c in candidates)
        })

    conn.close()

    turnout = round((unique_voters / total_voters * 100), 1) if total_voters > 0 else 0

    return render_template('admin.html',
                           total_voters=total_voters,
                           total_votes=total_votes,
                           turnout=turnout,
                           election_stats=election_stats)


@app.route('/admin/election/create', methods=['GET', 'POST'])
@admin_required
def create_election():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        candidates_raw = request.form.get('candidates', '').strip()

        if not title or not start_date or not end_date or not candidates_raw:
            flash('All fields are required.', 'error')
            return render_template('create_election.html')

        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO elections (title, description, start_date, end_date) VALUES (?, ?, ?, ?)',
            (title, description, start_date, end_date)
        )
        election_id = cursor.lastrowid

        for line in candidates_raw.split('\n'):
            parts = line.strip().split(',')
            if len(parts) >= 1 and parts[0].strip():
                name = parts[0].strip()
                party = parts[1].strip() if len(parts) > 1 else 'Independent'
                conn.execute(
                    'INSERT INTO candidates (name, party, election_id) VALUES (?, ?, ?)',
                    (name, party, election_id)
                )

        conn.commit()
        conn.close()
        flash('Election created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('create_election.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', debug=False, port=5000)
