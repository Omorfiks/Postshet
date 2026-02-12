from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
import json
import traceback
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# PostgreSQL
import psycopg2
import psycopg2.extras

load_dotenv()

app = Flask(__name__)
CORS(app)

# Конфигурация
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# Строка подключения к PostgreSQL (например, от Render)
DATABASE_URL = os.environ.get('DATABASE_URL')

app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', '').strip().lstrip('@')
LOGIN_TOKEN_SECRET = os.environ.get('LOGIN_TOKEN_SECRET', '')
SITE_BASE_URL = (os.environ.get('SITE_BASE_URL') or '').rstrip('/')
LOGIN_TOKEN_TTL_SECONDS = 600  # 10 минут

# ID администраторов из .env (ADMIN_TELEGRAM_IDS=id1,id2,...)
ADMIN_TELEGRAM_IDS = set()
for x in (os.environ.get('ADMIN_TELEGRAM_IDS') or '').replace(' ', '').split(','):
    if x:
        try:
            ADMIN_TELEGRAM_IDS.add(int(x))
        except ValueError:
            pass

# Сессия: живёт 30 дней, не пропадает при закрытии браузера (важно для мобильного входа)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if SITE_BASE_URL.lower().startswith('https'):
    app.config['SESSION_COOKIE_SECURE'] = True

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    """
    Открыть соединение с PostgreSQL.
    Использует DATABASE_URL из окружения.
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL не задан в окружении")
    return psycopg2.connect(DATABASE_URL)


def verify_telegram_login_hash(data, bot_token):
    """Проверка подписи данных Telegram Login Widget."""
    if not bot_token or 'hash' not in data:
        return False
    received_hash = data.pop('hash', None)
    data_check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, received_hash)


def get_current_user_id():
    """Идентификатор пользователя: только из сессии (Telegram). Реакции — только для авторизованных."""
    user = session.get('user')
    if user and user.get('telegram_id'):
        return 'tg_' + str(user['telegram_id'])
    return None


def fetch_telegram_user_photo(telegram_id):
    """Скачать фото профиля пользователя из Telegram Bot API, сохранить в uploads, вернуть URL или None."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    try:
        api_base = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}'
        with urlopen(Request(f'{api_base}/getUserProfilePhotos?user_id={telegram_id}&limit=1')) as r:
            data = json.loads(r.read().decode())
        if not data.get('ok') or not data.get('result', {}).get('photos'):
            return None
        photos = data['result']['photos'][0]
        file_id = photos[-1]['file_id']
        with urlopen(Request(f'{api_base}/getFile?file_id={file_id}')) as r:
            file_data = json.loads(r.read().decode())
        if not file_data.get('ok'):
            return None
        file_path = file_data['result']['file_path']
        download_url = f'https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}'
        ext = os.path.splitext(file_path)[1] or '.jpg'
        filename = f'user_avatar_{telegram_id}{ext}'
        full_path = os.path.join(UPLOAD_FOLDER, filename)
        with urlopen(Request(download_url)) as r:
            with open(full_path, 'wb') as f:
                f.write(r.read())
        return f'/uploads/{filename}'
    except (HTTPError, URLError, OSError, KeyError, IndexError, TypeError, ValueError):
        return None


# Инициализация БД (PostgreSQL)
def init_db():
    conn = get_db()
    c = conn.cursor()

    # Таблица постов
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            media_type TEXT,
            media_path TEXT,
            caption TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Таблица реакций (агрегат счётчиков по типу на пост)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reactions (
            id SERIAL PRIMARY KEY,
            post_id INTEGER,
            reaction_type TEXT,
            count INTEGER DEFAULT 1,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """
    )

    # Реакции пользователей: одна запись на (пост, пользователь)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_reactions (
            post_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            reaction_type TEXT NOT NULL,
            PRIMARY KEY (post_id, user_id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """
    )

    # Таблица информации о канале
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_info (
            id INTEGER PRIMARY KEY,
            name TEXT,
            avatar_url TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Таблица пользователей (привязка Telegram)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            photo_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Одноразовые токены для входа через бота (мобильный flow)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS login_tokens (
            token TEXT PRIMARY KEY,
            telegram_id BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    from flask import request
    site_origin = request.host_url.rstrip('/') if request else ''
    return render_template('index.html', telegram_bot_username=TELEGRAM_BOT_USERNAME, site_origin=site_origin)


@app.route('/auth/telegram/start')
def auth_telegram_start():
    """Страница с виджетом для входа (открывается в popup). Редирект после входа — на callback, без postMessage."""
    from flask import redirect, url_for
    if not TELEGRAM_BOT_USERNAME:
        return redirect(url_for('index'))
    callback_url = url_for('auth_telegram_callback', _external=True)
    return render_template('auth_telegram_start.html',
                           telegram_bot_username=TELEGRAM_BOT_USERNAME,
                           callback_url=callback_url)


@app.route('/auth/telegram/callback')
def auth_telegram_callback():
    """Сюда Telegram редиректит после входа (та же вкладка). Проверяем hash, ставим сессию, редирект на главную."""
    from flask import request, redirect, url_for
    data = {k: request.args.get(k) for k in ('id', 'first_name', 'last_name', 'username', 'photo_url', 'auth_date', 'hash') if request.args.get(k) is not None}
    if not data or 'hash' not in data:
        return redirect(url_for('index'))
    data_copy = {k: str(v) for k, v in data.items() if v is not None}
    if not TELEGRAM_BOT_TOKEN or not verify_telegram_login_hash(data_copy.copy(), TELEGRAM_BOT_TOKEN):
        return redirect(url_for('index'))
    telegram_id = data_copy.get('id')
    username = data_copy.get('username') or ''
    first_name = data_copy.get('first_name') or ''
    last_name = data_copy.get('last_name') or ''
    photo_url = data_copy.get('photo_url') or ''
    user = {'telegram_id': int(telegram_id), 'username': username, 'first_name': first_name, 'last_name': last_name, 'photo_url': photo_url}
    user['is_admin'] = user['telegram_id'] in ADMIN_TELEGRAM_IDS
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO users (telegram_id, username, first_name, last_name, photo_url)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (telegram_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            photo_url = EXCLUDED.photo_url
        """,
        (telegram_id, username, first_name, last_name, photo_url),
    )
    conn.commit()
    conn.close()
    session['user'] = user
    session.permanent = True
    # Если открыто в popup — закрыть и обновить главную; иначе редирект на главную
    return '''<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>if(window.opener){window.opener.location.reload();window.close();}else{window.location.href="/";}</script>
<p>Вход выполнен.</p></body></html>'''


@app.route('/auth/telegram/verify')
def auth_telegram_verify():
    """Вход по одноразовому токену (мобильный flow: пользователь перешёл по ссылке из бота)."""
    token = request.args.get('token')
    if not token:
        return redirect(url_for('index'))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT telegram_id, created_at FROM login_tokens WHERE token = %s', (token,))
    row = c.fetchone()
    if not row:
        conn.close()
        return redirect(url_for('index'))
    telegram_id, created_at = row
    try:
        created = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
    except (TypeError, ValueError):
        created = datetime.utcnow() - timedelta(days=1)  # неверный формат — считаем просроченным
    if (datetime.utcnow() - created).total_seconds() > LOGIN_TOKEN_TTL_SECONDS:
        c.execute('DELETE FROM login_tokens WHERE token = %s', (token,))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    c.execute('DELETE FROM login_tokens WHERE token = %s', (token,))
    c.execute('SELECT username, first_name, last_name, photo_url FROM users WHERE telegram_id = %s', (telegram_id,))
    user_row = c.fetchone()
    if user_row:
        username, first_name, last_name, photo_url = user_row
    else:
        username, first_name, last_name, photo_url = '', '', '', ''
        # В PostgreSQL аналог INSERT OR IGNORE — ON CONFLICT DO NOTHING
        c.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, photo_url)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO NOTHING
            """,
            (telegram_id, '', '', '', ''),
        )
    conn.commit()
    conn.close()
    photo_url = photo_url or ''
    if not photo_url:
        photo_url = fetch_telegram_user_photo(telegram_id) or ''
        if photo_url:
            conn2 = get_db()
            c2 = conn2.cursor()
            c2.execute('UPDATE users SET photo_url = %s WHERE telegram_id = %s', (photo_url, telegram_id))
            conn2.commit()
            conn2.close()
    user = {'telegram_id': int(telegram_id), 'username': username or '', 'first_name': first_name or '', 'last_name': last_name or '', 'photo_url': photo_url or ''}
    user['is_admin'] = user['telegram_id'] in ADMIN_TELEGRAM_IDS
    session['user'] = user
    session.permanent = True
    return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/posts')
def get_posts():
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    c.execute(
        """
        SELECT p.*,
               string_agg(r.reaction_type || ':' || r.count::text, ',') AS reactions
        FROM posts p
        LEFT JOIN reactions r ON p.id = r.post_id
        GROUP BY p.id
        ORDER BY p.created_at DESC
        """
    )

    posts = []
    for row in c.fetchall():
        post = dict(row)
        reactions = {}
        if post.get('reactions'):
            for reaction in post['reactions'].split(','):
                r_type, count = reaction.split(':')
                reactions[r_type] = int(count)
        post['reactions'] = reactions
        posts.append(post)

    user_id = get_current_user_id()
    if user_id and posts:
        post_ids = [p['id'] for p in posts]
        c.execute(
            """
            SELECT post_id, reaction_type
            FROM user_reactions
            WHERE user_id = %s AND post_id = ANY(%s)
            """,
            (user_id, post_ids),
        )
        my_by_post = {row['post_id']: row['reaction_type'] for row in c.fetchall()}
        for post in posts:
            post['my_reaction'] = my_by_post.get(post['id'])
    else:
        for post in posts:
            post['my_reaction'] = None

    conn.close()
    return jsonify(posts)

@app.route('/api/posts', methods=['POST'])
def create_post():
    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO posts (telegram_id, media_type, media_path, caption)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (telegram_id) DO NOTHING
        RETURNING id
        """,
        (data['telegram_id'], data['media_type'], data['media_path'], data.get('caption', '')),
    )

    row = c.fetchone()
    if row:
        post_id = row[0]
    else:
        c.execute('SELECT id FROM posts WHERE telegram_id = %s', (data['telegram_id'],))
        post_id = c.fetchone()[0]

    conn.commit()
    conn.close()
    return jsonify({'id': post_id, 'status': 'success'})

def _reactions_dict_for_post(c, post_id):
    """Собрать словарь {reaction_type: count} для поста из таблицы reactions."""
    c.execute('SELECT reaction_type, count FROM reactions WHERE post_id = %s', (post_id,))
    return {row[0]: row[1] for row in c.fetchall()}


@app.route('/api/posts/<int:post_id>/reactions', methods=['POST'])
def add_reaction(post_id):
    data = request.get_json(silent=True) or {}
    reaction_type = data.get('reaction_type')
    if not reaction_type:
        return jsonify({'error': 'reaction_type required'}), 400

    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth_required'}), 401

    conn = None
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute('SELECT reaction_type FROM user_reactions WHERE post_id = %s AND user_id = %s', (post_id, user_id))
        row = c.fetchone()
        current = row[0] if row else None

        if current == reaction_type:
            # Снять реакцию: та же эмоция — удаляем
            c.execute('DELETE FROM user_reactions WHERE post_id = %s AND user_id = %s', (post_id, user_id))
            c.execute('SELECT id, count FROM reactions WHERE post_id = %s AND reaction_type = %s', (post_id, reaction_type))
            r = c.fetchone()
            if r:
                rid, count = r
                if count <= 1:
                    c.execute('DELETE FROM reactions WHERE id = %s', (rid,))
                else:
                    c.execute('UPDATE reactions SET count = count - 1 WHERE id = %s', (rid,))
            my_reaction = None
            is_new = False
        elif current is not None:
            # Сменить реакцию: другая эмоция — у старой -1, у новой +1
            c.execute(
                'UPDATE user_reactions SET reaction_type = %s WHERE post_id = %s AND user_id = %s',
                (reaction_type, post_id, user_id),
            )
            # Уменьшить старую
            c.execute('SELECT id, count FROM reactions WHERE post_id = %s AND reaction_type = %s', (post_id, current))
            r = c.fetchone()
            if r:
                rid, count = r
                if count <= 1:
                    c.execute('DELETE FROM reactions WHERE id = %s', (rid,))
                else:
                    c.execute('UPDATE reactions SET count = count - 1 WHERE id = %s', (rid,))
            # Увеличить новую
            c.execute('SELECT id, count FROM reactions WHERE post_id = %s AND reaction_type = %s', (post_id, reaction_type))
            r = c.fetchone()
            if r:
                c.execute('UPDATE reactions SET count = count + 1 WHERE id = %s', (r[0],))
            else:
                c.execute(
                    'INSERT INTO reactions (post_id, reaction_type, count) VALUES (%s, %s, 1)',
                    (post_id, reaction_type),
                )
            my_reaction = reaction_type
            is_new = True
        else:
            # Новая реакция
            c.execute(
                'INSERT INTO user_reactions (post_id, user_id, reaction_type) VALUES (%s, %s, %s)',
                (post_id, user_id, reaction_type),
            )
            c.execute('SELECT id, count FROM reactions WHERE post_id = %s AND reaction_type = %s', (post_id, reaction_type))
            r = c.fetchone()
            if r:
                c.execute('UPDATE reactions SET count = count + 1 WHERE id = %s', (r[0],))
            else:
                c.execute(
                    'INSERT INTO reactions (post_id, reaction_type, count) VALUES (%s, %s, 1)',
                    (post_id, reaction_type),
                )
            my_reaction = reaction_type
            is_new = True

        reactions = _reactions_dict_for_post(c, post_id)
        conn.commit()
        return jsonify({'reactions': reactions, 'my_reaction': my_reaction, 'is_new': is_new})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'server_error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """Удаление поста. Только для администраторов."""
    user = session.get('user')
    if not user or user.get('telegram_id') not in ADMIN_TELEGRAM_IDS:
        return jsonify({'error': 'forbidden'}), 403
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, media_path FROM posts WHERE id = %s', (post_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'not_found'}), 404
    _, media_path = row
    c.execute('DELETE FROM user_reactions WHERE post_id = %s', (post_id,))
    c.execute('DELETE FROM reactions WHERE post_id = %s', (post_id,))
    c.execute('DELETE FROM posts WHERE id = %s', (post_id,))
    conn.commit()
    conn.close()
    if media_path:
        full_path = os.path.join(UPLOAD_FOLDER, media_path)
        if os.path.isfile(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass
    return jsonify({'ok': True})


@app.route('/api/channel-info')
def get_channel_info():
    conn = get_db()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    c.execute('SELECT * FROM channel_info WHERE id = 1')
    info = c.fetchone()
    conn.close()

    if info:
        return jsonify(dict(info))
    return jsonify({'name': 'Telegram Channel', 'avatar_url': ''})

@app.route('/api/channel-info', methods=['POST'])
def update_channel_info():
    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO channel_info (id, name, avatar_url, updated_at)
        VALUES (1, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            avatar_url = EXCLUDED.avatar_url,
            updated_at = EXCLUDED.updated_at
        """,
        (data['name'], data.get('avatar_url', '')),
    )

    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})


@app.route('/api/me')
def get_me():
    """Текущий пользователь из сессии."""
    user = session.get('user')
    if not user:
        return jsonify({})
    user = dict(user)
    user['is_admin'] = user.get('telegram_id') in ADMIN_TELEGRAM_IDS
    return jsonify(user)


@app.route('/api/create-login-token', methods=['POST'])
def api_create_login_token():
    """Создать одноразовый токен для входа (вызывает бот при /start login). Защита: LOGIN_TOKEN_SECRET."""
    data = request.json or {}
    secret = data.get('secret')
    telegram_id = data.get('telegram_id')
    if not LOGIN_TOKEN_SECRET or secret != LOGIN_TOKEN_SECRET or telegram_id is None:
        return jsonify({'ok': False, 'error': 'Forbidden'}), 403
    try:
        telegram_id = int(telegram_id)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Invalid telegram_id'}), 400
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    username = (data.get('username') or '').strip().lstrip('@')
    token = secrets.token_urlsafe(32)
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO login_tokens (token, telegram_id) VALUES (%s, %s)', (token, telegram_id))
    c.execute(
        """
        INSERT INTO users (telegram_id, username, first_name, last_name, photo_url)
        VALUES (
            %s,
            %s,
            %s,
            %s,
            COALESCE((SELECT photo_url FROM users WHERE telegram_id = %s), '')
        )
        ON CONFLICT (telegram_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name
        """,
        (telegram_id, username, first_name, last_name, telegram_id),
    )
    conn.commit()
    conn.close()
    base = SITE_BASE_URL or request.host_url.rstrip('/')
    login_url = f'{base}/auth/telegram/verify?token={token}'
    return jsonify({'ok': True, 'token': token, 'login_url': login_url})


@app.route('/api/auth/telegram', methods=['POST'])
def auth_telegram():
    """Привязка аккаунта Telegram: проверка hash и сохранение в сессию."""
    data = request.json
    if not data:
        return jsonify({'ok': False, 'error': 'No data'}), 400
    # Все поля в строках для проверки hash (пустые значения Telegram может включать в подпись)
    data_copy = {k: str(v) for k, v in data.items() if v is not None}
    if not TELEGRAM_BOT_TOKEN or not verify_telegram_login_hash(data_copy.copy(), TELEGRAM_BOT_TOKEN):
        return jsonify({'ok': False, 'error': 'Invalid hash'}), 403
    telegram_id = data_copy.get('id')
    username = data_copy.get('username') or ''
    first_name = data_copy.get('first_name') or ''
    last_name = data_copy.get('last_name') or ''
    photo_url = data_copy.get('photo_url') or ''
    user = {
        'telegram_id': int(telegram_id),
        'username': username,
        'first_name': first_name,
        'last_name': last_name,
        'photo_url': photo_url
    }
    user['is_admin'] = user['telegram_id'] in ADMIN_TELEGRAM_IDS
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO users (telegram_id, username, first_name, last_name, photo_url)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (telegram_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            photo_url = EXCLUDED.photo_url
        """,
        (telegram_id, username, first_name, last_name, photo_url),
    )
    conn.commit()
    conn.close()
    session['user'] = user
    session.permanent = True
    return jsonify({'ok': True, 'user': user})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'ok': True})


if __name__ == '__main__':
    # Порт 80 нужен, чтобы origin был http://127.0.0.1 и совпадал с frame-ancestors виджета Telegram.
    # На Windows для порта 80 может потребоваться запуск от администратора. Или задайте PORT в .env.
    port = int(os.environ.get('PORT', 80))
    app.run(debug=True, host='0.0.0.0', port=port)
