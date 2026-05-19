import os
import sys
import threading
import time
import webview
from flask import Flask, render_template, request, jsonify, session
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from pyngrok import ngrok

# Fix for PyInstaller resource paths
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = Flask(__name__, 
            template_folder=resource_path('templates'),
            static_folder=resource_path('static'))

app.secret_key = os.urandom(24)

# Helper to get Twilio client from session
def get_twilio_client():
    if 'account_sid' in session and 'auth_token' in session:
        return Client(session['account_sid'], session['auth_token'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/numbers', methods=['GET'])
def get_numbers():
    client = get_twilio_client()
    if not client:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        numbers = client.incoming_phone_numbers.list(limit=20)
        formatted_numbers = [{'phoneNumber': n.phone_number, 'friendlyName': n.friendly_name} for n in numbers]
        return jsonify({'numbers': formatted_numbers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    sid = data.get('sid')
    token = data.get('token')

    if not sid or not token:
        return jsonify({'error': 'Missing credentials'}), 400

    try:
        client = Client(sid, token)
        account = client.api.accounts(sid).fetch()
        
        if account.status == 'suspended':
             return jsonify({'error': 'Account is suspended'}), 401

        new_key = client.new_keys.create(friendly_name='TwilioDesktop Session')
        
        session['account_sid'] = sid
        session['auth_token'] = token
        session['api_key_sid'] = new_key.sid
        session['api_key_secret'] = new_key.secret
        
        numbers = client.incoming_phone_numbers.list(limit=20)
        formatted_numbers = [{'phoneNumber': n.phone_number, 'friendlyName': n.friendly_name} for n in numbers]

        return jsonify({'message': 'Login successful', 'numbers': formatted_numbers})
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/token', methods=['POST'])
def token():
    client = get_twilio_client()
    if not client:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # In desktop app, we MUST use the ngrok URL for Twilio to reach us
    global public_url
    base_url = public_url + "/" if not public_url.endswith("/") else public_url
    
    app_name = "TwilioDesktopDialer"
    
    try:
        apps = client.applications.list(friendly_name=app_name, limit=1)
        twiml_app_sid = None
        
        voice_url = f"{base_url}voice"
        print(f"DEBUG: Calculated Voice URL: {voice_url}")

        if apps:
            twiml_app_sid = apps[0].sid
            apps[0].update(voice_method='POST', voice_url=voice_url)
        else:
            new_app = client.applications.create(
                friendly_name=app_name,
                voice_method='POST',
                voice_url=voice_url
            )
            twiml_app_sid = new_app.sid

        access_token = AccessToken(
            session['account_sid'],
            session['api_key_sid'],
            session['api_key_secret'],
            identity='desktop_user'
        )
        
        voice_grant = VoiceGrant(
            outgoing_application_sid=twiml_app_sid,
            incoming_allow=True
        )
        access_token.add_grant(voice_grant)

        return jsonify({'token': access_token.to_jwt()})

    except Exception as e:
        print(f"ERROR in /api/token: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/voice', methods=['GET', 'POST'])
def voice():
    data = request.form.to_dict() if request.method == 'POST' else request.args.to_dict()
    response = VoiceResponse()
    to_number = data.get('To')
    caller_id = data.get('callerId')
    
    if not to_number:
        response.say("Invalid destination number.")
        return str(response)

    dial = Dial(callerId=caller_id)
    dial.number(to_number)
    response.append(dial)
    return str(response)

public_url = ""

def run_flask():
    global public_url
    port = 5000
    # Start ngrok
    try:
        public_url = ngrok.connect(port).public_url
        print(f" * Ngrok Tunnel: {public_url}")
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        # If ngrok fails, we might still want to run locally for testing, 
        # but Twilio won't work.
    
    app.run(port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Run Flask in a background thread
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Wait a bit for Flask to start
    time.sleep(2)

    # Create a GUI window pointing to the local Flask server
    webview.create_window('Twilio Outbound Caller', 'http://127.0.0.1:5000')
    webview.start()
