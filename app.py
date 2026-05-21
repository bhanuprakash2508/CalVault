from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, send_from_directory, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json 
import os 
import re
import uuid
import mimetypes
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_FILE  = os.path.join(BASE_DIR, 'vault_data.json')
UPLOAD_DIR = os.path.join(BASE_DIR, 'vault_files')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed extensions by category 
ALLOWED_AUDIO = {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'weba'}
ALLOWED_VIDEO = {'mp4', 'webm', 'mkv', 'mov', 'avi', 'ogv', 'm4v'}
ALLOWED_PDF   = {'pdf'}
ALLOWED_DOC   = {'doc', 'docx', 'odt', 'rtf'}
ALLOWED_SHEET = {'xls', 'xlsx', 'ods', 'csv'}
ALLOWED_TEXT  = {'txt', 'md', 'json', 'xml', 'log'}
ALLOWED_EXT   = (ALLOWED_AUDIO | ALLOWED_VIDEO | ALLOWED_PDF |
                 ALLOWED_DOC   | ALLOWED_SHEET  | ALLOWED_TEXT)

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


def load_data():
    default_data = {
        'pin_hash': '',
        'pin_len': 4,
        'pw_hash': '',
        'entries': [],
        'files': []
    }
    if not os.path.exists(DATA_FILE):
        return default_data.copy()
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return default_data.copy()

    # Backward compatibility
    if not isinstance(data, dict):
        data = {}
    data.setdefault('pin_hash', '')
    data.setdefault('pin_len', 4)
    data.setdefault('pw_hash', '')
    data.setdefault('entries', [])
    data.setdefault('files', [])

    # Normalize uploaded file
    normalized = []
    for item in data.get('files', []):
        if not isinstance(item, dict):
            continue
        original_name = item.get('original_name') or item.get('label') or 'file'
        kind = item.get('kind') or file_kind(original_name)
        item.setdefault('original_name', original_name)
        item.setdefault('kind', kind)
        item.setdefault('icon', kind_icon(kind))
        item.setdefault('mimetype', mimetypes.guess_type(original_name)[0] or 'application/octet-stream')
        item.setdefault('label', original_name)
        normalized.append(item)
    data['files'] = normalized

    return data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_setup():
    d = load_data()
    return bool(d.get('pin_hash') and d.get('pw_hash'))

def is_unlocked():
    return session.get('unlocked') is True

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def file_kind(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext in ALLOWED_AUDIO:  return 'audio'
    if ext in ALLOWED_VIDEO:  return 'video'
    if ext in ALLOWED_PDF:    return 'pdf'
    if ext in ALLOWED_DOC:    return 'doc'
    if ext in ALLOWED_SHEET:  return 'sheet'
    return 'text'

def kind_icon(kind):
    return {'audio':'🎵', 'video':'🎬', 'pdf':'📄',
            'doc':'📝', 'sheet':'📊', 'text':'🗒'}.get(kind, '📁')

# ROUTES
@app.route('/')
def index():
    return redirect(url_for('setup') if not is_setup() else url_for('calendar'))

# SETUP
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if is_setup():
        return redirect(url_for('calendar'))
    error = None
    if request.method == 'POST':
        pin      = request.form.get('pin', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        if not re.match(r'^\d+(-\d+)+$', pin):
            error = 'PIN must be dates separated by hyphens (e.g. 3-7-14-21)'
        else:
            dates = [int(d) for d in pin.split('-')]
            if len(dates) < 2 or len(dates) > 8:
                error = 'Enter between 2 and 8 dates'
            elif any(d < 1 or d > 31 for d in dates):
                error = 'Each date must be between 1 and 31'
            elif len(password) < 4:
                error = 'Vault password must be at least 4 characters'
            elif password != confirm:
                error = 'Passwords do not match'
            else:
                save_data({'pin_hash': generate_password_hash(pin),
                           'pin_len':  len(dates),
                           'pw_hash':  generate_password_hash(password),    
                           'entries':  [], 'files': []})
                return redirect(url_for('calendar'))
    return render_template('setup.html', error=error)

# CALENDAR
@app.route('/calendar')
def calendar():
    if not is_setup():
        return redirect(url_for('setup'))
    return render_template('calendar.html', pin_len=load_data().get('pin_len', 4))

@app.route('/verify-pin', methods=['POST'])
def verify_pin():
    if not is_setup():
        return jsonify({'ok': False})
    body    = request.get_json()
    pin_str = '-'.join(str(d) for d in body.get('sequence', []))
    if check_password_hash(load_data()['pin_hash'], pin_str):
        session['calendar_passed'] = True
        return jsonify({'ok': True})
    return jsonify({'ok': False})

# UNLOCK
@app.route('/unlock', methods=['GET', 'POST'])
def unlock():
    if not is_setup():               return redirect(url_for('setup'))
    if not session.get('calendar_passed'): return redirect(url_for('calendar'))
    error = None
    if request.method == 'POST':
        if check_password_hash(load_data()['pw_hash'], request.form.get('password', '')):
            session['unlocked'] = True
            session.pop('calendar_passed', None)
            return redirect(url_for('vault'))
        error = 'Incorrect password. Try again.'
    return render_template('unlock.html', error=error)

# VAULT
@app.route('/vault')
def vault():
    if not is_setup():    return redirect(url_for('setup'))
    if not is_unlocked(): return redirect(url_for('calendar'))
    data    = load_data()
    tab     = request.args.get('tab', 'All')
    subtab  = request.args.get('subtab', 'all')   # for Files: all/audio/video/docs

    entries = data.get('entries', [])
    files   = data.get('files', [])

    if tab == 'Files':
        entries = []
        if subtab == 'audio':
            files = [f for f in files if f['kind'] == 'audio']
        elif subtab == 'video':
            files = [f for f in files if f['kind'] == 'video']
        elif subtab == 'docs':
            files = [f for f in files if f['kind'] in ('pdf','doc','sheet','text')]
        # subtab == 'all' → keep all
    else:
        files = []
        if tab != 'All':
            entries = [e for e in entries if e.get('category') == tab]

    pw_updated = session.pop('pw_updated', False)
    return render_template('vault.html',
                           entries=entries, files=files,
                           current_tab=tab, subtab=subtab,
                           kind_icon=kind_icon,
                           pw_updated=pw_updated)

# PASSWORD CRUD
@app.route('/add-entry', methods=['POST'])
def add_entry():
    if not is_unlocked(): return redirect(url_for('calendar'))
    data  = load_data()
    entry = {'name':     request.form.get('name','').strip(),
             'username': request.form.get('username','').strip(),
             'password': request.form.get('password',''),
             'category': request.form.get('category','Other'),
             'created':  datetime.now().strftime('%d %b %Y, %I:%M %p')}
    if entry['name']:
        data['entries'].append(entry)
        save_data(data)
    return redirect(url_for('vault'))

@app.route('/edit-entry/<int:idx>', methods=['POST'])
def edit_entry(idx):
    if not is_unlocked(): return redirect(url_for('calendar'))
    data    = load_data()
    entries = data.get('entries', [])
    if 0 <= idx < len(entries):
        entries[idx] = {'name':     request.form.get('name','').strip(),
                        'username': request.form.get('username','').strip(),
                        'password': request.form.get('password',''),
                        'category': request.form.get('category','Other')}
        data['entries'] = entries
        save_data(data)
    return redirect(url_for('vault'))

@app.route('/delete-entry/<int:idx>', methods=['POST'])
def delete_entry(idx):
    if not is_unlocked(): return redirect(url_for('calendar'))
    data    = load_data()
    entries = data.get('entries', [])
    if 0 <= idx < len(entries):
        entries.pop(idx)
        data['entries'] = entries
        save_data(data)
    return redirect(url_for('vault'))

# FILE UPLOAD
@app.route('/upload-file', methods=['POST'])
def upload_file():
    if not is_unlocked(): return redirect(url_for('calendar'))
    if 'file' not in request.files:
        return redirect(url_for('vault', tab='Files'))
    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return redirect(url_for('vault', tab='Files'))

    original_name = secure_filename(f.filename)
    ext           = original_name.rsplit('.', 1)[-1].lower()
    stored_name   = f"{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(UPLOAD_DIR, stored_name))

    kind     = file_kind(original_name)
    mimetype = mimetypes.guess_type(original_name)[0] or 'application/octet-stream'

    data = load_data()
    data.setdefault('files', []).append({
        'original_name': original_name,
        'stored_name':   stored_name,
        'kind':          kind,
        'icon':          kind_icon(kind),
        'mimetype':      mimetype,
        'label':         request.form.get('label','').strip() or original_name,
        'created':       datetime.now().strftime('%d %b %Y, %I:%M %p'),
    })
    save_data(data)
    return redirect(url_for('vault', tab='Files', subtab='all'))

# FILE STREAM
@app.route('/stream-file/<stored_name>')
def stream_file(stored_name):
    if not is_unlocked():
        abort(403)

    data = load_data()
    entry = next((f for f in data.get('files', []) if f.get('stored_name') == stored_name), None)
    if not entry:
        abort(404)

    return send_from_directory(
        UPLOAD_DIR,
        stored_name,
        mimetype=entry.get('mimetype', 'application/octet-stream'),
        download_name=entry.get('original_name'),
        conditional=True
    )


# FILE DOWNLOAD
@app.route('/download-file/<stored_name>')
def download_file(stored_name):
    if not is_unlocked(): abort(403)
    data  = load_data()
    entry = next((f for f in data.get('files',[]) if f['stored_name']==stored_name), None)
    if not entry: abort(404)
    return send_from_directory(UPLOAD_DIR, stored_name,
                               as_attachment=True,
                               download_name=entry['original_name'])

# FILE DELETE
@app.route('/delete-file/<stored_name>', methods=['POST'])
def delete_file(stored_name):
    if not is_unlocked(): return redirect(url_for('calendar'))
    data  = load_data()
    files = data.get('files', [])
    entry = next((f for f in files if f['stored_name']==stored_name), None)
    if entry:
        files.remove(entry)
        data['files'] = files
        save_data(data)
        disk = os.path.join(UPLOAD_DIR, stored_name)
        if os.path.exists(disk): os.remove(disk)
    return redirect(url_for('vault', tab='Files'))

# SETTINGS
@app.route('/change-password', methods=['POST'])
def change_password():
    if not is_unlocked(): return redirect(url_for('calendar'))
    data       = load_data()
    current_pw = request.form.get('current_pw', '')
    new_pw     = request.form.get('new_pw', '')
    base_ctx   = dict(entries=data.get('entries',[]), files=data.get('files',[]),
                      current_tab='All', subtab='all',
                      kind_icon=kind_icon, show_settings=True)
    if not check_password_hash(data['pw_hash'], current_pw):
        return render_template('vault.html', settings_error='Current password is incorrect', **base_ctx)
    if len(new_pw) < 4:
        return render_template('vault.html', settings_error='New password must be at least 4 characters', **base_ctx)
    data['pw_hash'] = generate_password_hash(new_pw)
    save_data(data)
    # Redirect to vault — modal closes, toast shows success
    session['pw_updated'] = True
    return redirect(url_for('vault'))

# RESET
@app.route('/reset', methods=['POST'])
def reset():
    import shutil
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
    session.clear()
    return redirect(url_for('setup'))

# LOGOUT
@app.route('/logout')
def logout():
    session.pop('unlocked', None)
    session.pop('calendar_passed', None)
    return redirect(url_for('calendar'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
