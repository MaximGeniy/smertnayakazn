# -*- coding: utf-8 -*-
"""
Сервер голосования: Flask + SQLite.
Голоса сохраняются в БД, один голос на session_id (один браузер = один голос).
"""
import sqlite3
import os
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.')
DB_PATH = os.path.join(os.path.dirname(__file__), 'votes.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                choice TEXT NOT NULL CHECK(choice IN ('yes', 'no')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/results', methods=['GET'])
def get_results():
    """Возвращает количество голосов «Да» и «Нет»."""
    with get_db() as conn:
        row = conn.execute('''
            SELECT
                SUM(CASE WHEN choice = 'yes' THEN 1 ELSE 0 END) AS yes_count,
                SUM(CASE WHEN choice = 'no' THEN 1 ELSE 0 END) AS no_count
            FROM votes
        ''').fetchone()
    yes_count = row['yes_count'] or 0
    no_count = row['no_count'] or 0
    return jsonify({
        'yes': yes_count,
        'no': no_count,
        'total': yes_count + no_count,
    })


@app.route('/api/vote', methods=['POST'])
def vote():
    """
    Принимает JSON: { "choice": "yes" | "no", "session_id": "..." }.
    Один session_id = один голос (повторный голос с тем же session_id вернёт ошибку).
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Нужен JSON'}), 400
    choice = (data.get('choice') or '').strip().lower()
    session_id = (data.get('session_id') or '').strip()
    if choice not in ('yes', 'no'):
        return jsonify({'error': 'choice должен быть "yes" или "no"'}), 400
    if not session_id:
        return jsonify({'error': 'Нужен session_id'}), 400

    try:
        with get_db() as conn:
            conn.execute(
                'INSERT INTO votes (session_id, choice) VALUES (?, ?)',
                (session_id, choice)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Вы уже голосовали', 'already_voted': True}), 409

    return jsonify({'ok': True, 'choice': choice})


@app.route('/api/check', methods=['POST'])
def check_voted():
    """Проверяет, голосовал ли уже этот session_id."""
    data = request.get_json() or {}
    session_id = (data.get('session_id') or '').strip()
    if not session_id:
        return jsonify({'voted': False})
    with get_db() as conn:
        row = conn.execute(
            'SELECT 1 FROM votes WHERE session_id = ?',
            (session_id,)
        ).fetchone()
    return jsonify({'voted': row is not None})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

