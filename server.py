from flask import Flask, render_template, request, send_file, jsonify, Response
import os
import speech_recognition as sr
from functools import wraps

app = Flask(__name__)

# --- CONFIGURATION ---
USER_ID = "Real Time Speech Converter"        
USER_PASSWORD = "321"    
UPLOAD_DIR = "uploads"
ESP_AUDIO = os.path.join(UPLOAD_DIR, "audio.wav")
MSG_FILE = "message.txt"
NEW_AUDIO_AVAILABLE = False  # Global flag for the popup system

if not os.path.exists(UPLOAD_DIR): 
    os.makedirs(UPLOAD_DIR)

# --- SECURITY ---
def check_auth(username, password):
    return username == USER_ID and password == USER_PASSWORD

def authenticate():
    return Response(
    'Could not verify your login level.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- ROUTES ---

@app.route('/')
@requires_auth  
def index(): 
    return render_template('index.html')

@app.route('/portable_voice', methods=['POST'])
def receive_esp():
    global NEW_AUDIO_AVAILABLE
    with open(ESP_AUDIO, "wb") as f: 
        f.write(request.data)
    NEW_AUDIO_AVAILABLE = True # Trigger for the frontend popup
    return "OK", 200

@app.route('/check_new_audio')
@requires_auth
def check_audio():
    global NEW_AUDIO_AVAILABLE
    if NEW_AUDIO_AVAILABLE:
        NEW_AUDIO_AVAILABLE = False # Reset flag after reporting
        return jsonify({"new": True})
    return jsonify({"new": False})

@app.route('/get_portable_voice')
@requires_auth
def send_to_web():
    return send_file(ESP_AUDIO) if os.path.exists(ESP_AUDIO) else ("404", 404)

@app.route('/transcribe_voice')
@requires_auth
def transcribe():
    if not os.path.exists(ESP_AUDIO): return jsonify({"text": "No file found."})
    lang = request.args.get('lang', 'en-IN')
    r = sr.Recognizer()
    try:
        with sr.AudioFile(ESP_AUDIO) as source:
            r.adjust_for_ambient_noise(source)
            audio = r.record(source)
            text = r.recognize_google(audio, language=lang)
            return jsonify({"text": text})
    except Exception as e:
        return jsonify({"text": f"Error: {str(e)}"})

@app.route('/send_text', methods=['POST'])
@requires_auth
def save_text():
    message = request.json['text'].strip() 
    with open(MSG_FILE, "w", encoding='utf-8') as f: 
        f.write(message)
    return "OK", 200

@app.route('/get_text')
def esp_check():
    if os.path.exists(MSG_FILE):
        try:
            with open(MSG_FILE, "r", encoding='utf-8') as f: 
                content = f.read()
            os.remove(MSG_FILE) # ESP32 consumes the message
            return content, 200
        except: pass
    return "NO_MESSAGE", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)