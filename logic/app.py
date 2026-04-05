import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from data.db_session import global_init
from data.user import User
from data.cache import start as get_problem
from data.ai import check_answer, get_ai_response, NoKeyError
from collections import defaultdict
import time

from config import SUBJECTS, translator, lang

_ai_last_call: dict[str, float] = defaultdict(float)
AI_COOLDOWN = 15

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'very_secret')

@app.route('/')
def index():
    return redirect(url_for('profile') if current_user.is_authenticated else url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            flash('Username and password are required.')
            return render_template('auth.html', mode='register')
        user = User.register(username, password)
        if not user:
            flash('Username already taken.')
            return render_template('auth.html', mode='register')
        login_user(user)
        return redirect(url_for('profile'))
    return render_template('auth.html', mode='register')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.authenticate(username, password)
        if not user:
            flash('Invalid credentials.')
            return render_template('auth.html', mode='login')
        login_user(user)
        return redirect(url_for('profile'))
    return render_template('auth.html', mode='login')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    for i in current_user.get_achievements():
        print(i)
    if session.get("lang") is None: 
        session["lang"] = lang
    print(session["lang"])
    return render_template('profile.html', username=current_user.username, stats=current_user.get_stats(), subjects=SUBJECTS,
                         lang=session["lang"], trans=translator, achievements=current_user.get_achievements())

@app.route('/set_language', methods=['POST'])
@login_required
def set_language():
    data = request.get_json()
    lang = data.get('lang')
    if lang in ['en', 'ru']:
        session['lang'] = lang
    return jsonify({'status': 'ok'})

@app.route('/problem', methods=['GET', 'POST'])
@login_required
def problem():
    if request.method == 'POST':
        subject = ' '.join([word.capitalize() for word in request.form.get('subject', '').split()])
        difficulty = request.form.get('difficulty', 'any').lower()

        if subject not in SUBJECTS:
            flash('Invalid subject.')
            return redirect(url_for('profile'))

        if difficulty != 'any' and (not difficulty.isdigit() or int(difficulty) not in range(1, 11)):
            flash('Invalid difficulty.')
            return redirect(url_for('profile'))

        p = get_problem(subject, difficulty, current_user.get_solved(), session["lang"])
        if not p:
            flash('No unsolved problems found. Cache may still be loading - try again in about 10 minutes.')
            return redirect(url_for('profile'))

        session['current_problem'] = p
        session['problem_subject'] = subject
        session['problem_difficulty'] = difficulty
        return redirect(url_for('problem'))

    p = session.get('current_problem')
    if not p:
        return redirect(url_for('profile'))
    print(p)
    return render_template('problem.html', problem=p)


@app.route('/problem/more')
@login_required
def problem_more():
    subject = session.get('problem_subject')
    difficulty = session.get('problem_difficulty')
    if not subject or not difficulty:
        flash('No previous problem context.')
        return redirect(url_for('profile'))

    if session.pop('answer_verified', None):
        p = session.get('current_problem')
        if p:
            current_user.mark_solved(p['id'], p['subject'], p['difficulty'])

    p = get_problem(subject, difficulty, current_user.get_solved(), session["lang"])
    if not p:
        flash('No unsolved problems found.')
        return redirect(url_for('profile'))

    session['current_problem'] = p
    return redirect(url_for('problem'))


@app.route('/problem/confirm', methods=['POST'])
@login_required
def problem_confirm():
    p = session.get('current_problem')
    if not p:
        return redirect(url_for('profile'))
    if not session.get('answer_verified'):
        flash('You must verify your answer before marking as solved.')
        return redirect(url_for('problem'))
    current_user.mark_solved(p['id'], p['subject'], p['difficulty'])
    session.pop('current_problem', None)
    session.pop('answer_verified', None)
    flash('Problem marked as solved!')
    return redirect(url_for('profile'))


@app.route('/problem/ai', methods=['POST'])
@login_required
def problem_ai():
    p = session.get('current_problem')
    if not p:
        return jsonify({'error': 'No active problem.'}), 400

    mode = request.form.get('mode')
    user_answer = request.form.get('answer', '').strip()
    if not user_answer and mode == 'check': return

    if mode not in ('check', 'hint', 'steps', 'explain'):
        return jsonify({'error': 'Invalid mode.'}), 400

    uid = str(current_user.id)
    now = time.time()
    elapsed = now - _ai_last_call[uid]
    if elapsed < AI_COOLDOWN:
        wait = int(AI_COOLDOWN - elapsed)
        return jsonify({'error': 'rate_limited', 'wait': wait}), 429

    _ai_last_call[uid] = now

    try:
        if mode == 'check':
            result = check_answer(p, user_answer)
            if result['verdict'] == 'CORRECT':
                session['answer_verified'] = True
            return jsonify(result)

        text = get_ai_response(p, mode, user_answer)
        return jsonify({'text': text})

    except NoKeyError:
        return jsonify({'error': 'AI is not configured.'}), 503
