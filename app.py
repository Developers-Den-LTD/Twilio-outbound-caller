import os
from flask import Flask, render_template, request, jsonify, session, g
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from pyngrok import ngrok

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Helper to get Twilio client from session
def get_twilio_client():
    if 'account_sid' in session and 'auth_token' in session:
        kwargs = {}
        if session.get('region'):
            kwargs['region'] = session.get('region')
        if session.get('edge'):
            kwargs['edge'] = session.get('edge')
        return Client(session['account_sid'], session['auth_token'], **kwargs)
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
    region = data.get('region')
    edge = data.get('edge')

    if not sid or not token:
        return jsonify({'error': 'Missing credentials'}), 400

    try:
        # Validate credentials by fetching the account
        kwargs = {}
        if region: kwargs['region'] = region
        if edge: kwargs['edge'] = edge
        client = Client(sid, token, **kwargs)
        account = client.api.accounts(sid).fetch()
        
        if account.status == 'suspended':
             return jsonify({'error': 'Account is suspended'}), 401

        # Create an API Key for signing the Access Token
        # Note: In a production app, manage these keys carefully. 
        # Here we create a key for the session.
        new_key = client.new_keys.create(friendly_name='TwilioBrowserDialer Session')
        
        # Save to session
        session['account_sid'] = sid
        session['auth_token'] = token
        session['api_key_sid'] = new_key.sid
        session['api_key_secret'] = new_key.secret
        session['region'] = region
        session['edge'] = edge
        
        # Fetch incoming phone numbers (using the same client)
        numbers = client.incoming_phone_numbers.list(limit=20)
        formatted_numbers = [{'phoneNumber': n.phone_number, 'friendlyName': n.friendly_name} for n in numbers]

        return jsonify({'message': 'Login successful', 'numbers': formatted_numbers})
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/token', methods=['POST'])
def token():
    """
    1. Checks/Creates a TwiML application.
    2. Generates an Access Token for the browser client.
    """
    client = get_twilio_client()
    if not client:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # We need a public URL for the Voice URL.
    # We rely on request.host_url which should include ngrok if accessed via ngrok.
    base_url = request.host_url
    
    app_name = "TwilioBrowserDialer"
    
    try:
        # Find existing TwiML app
        apps = client.applications.list(friendly_name=app_name, limit=1)
        twiml_app_sid = None
        
        voice_url = f"{base_url}voice"
        print(f"DEBUG: Calculated Voice URL: {voice_url}")

        if apps:
            twiml_app_sid = apps[0].sid
            # Always update for debugging
            print(f"DEBUG: Updating TwiML App {twiml_app_sid} to {voice_url}")
            apps[0].update(voice_method='POST', voice_url=voice_url)
        else:
            # Create new TwiML App
            print(f"DEBUG: Creating new TwiML App with {voice_url}")
            new_app = client.applications.create(
                friendly_name=app_name,
                voice_method='POST',
                voice_url=voice_url
            )
            twiml_app_sid = new_app.sid

        # Generate Access Token using API Key
        # AccessToken(account_sid, api_key_sid, api_key_secret, ...)
        kwargs = {}
        if session.get('region'):
            kwargs['region'] = session.get('region')
            
        access_token = AccessToken(
            session['account_sid'],
            session['api_key_sid'],
            session['api_key_secret'],
            identity='browser_user',
            **kwargs
        )
        
        # Grant Voice capability
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
    """
    Twilio Webhook: Called when the browser client initiates a call.
    Expects 'To' in the request form data or query params.
    """
    print("DEBUG: /voice webhook HIT")
    # Merge args and form to handle both GET and POST data
    data = request.form.to_dict() if request.method == 'POST' else request.args.to_dict()
    print(f"DEBUG: Data: {data}")
    
    response = VoiceResponse()
    
    to_number = data.get('To')
    
    # 'From' will be client:browser_user usually.
    # We want to set the callerId to one of the user's Twilio numbers.
    # The client should send this as a custom parameter if possible, 
    # OR we rely on a default.
    # For this implementation, let's pass it as a param 'callerId' from the client.
    # Twilio JS SDK allows passing params in `.connect(params)`.
    
    caller_id = data.get('callerId')
    
    if not to_number:
        response.say("Invalid destination number.")
        return str(response)

    dial = Dial(callerId=caller_id)
    
    # Check if we are dialing a valid number
    if to_number:
         dial.number(to_number)
    else:
        response.say("Please enter a phone number.")
        return str(response)
        
    response.append(dial)
    return str(response)

if __name__ == '__main__':
    # Automatically start ngrok for development
    port = 5000
    public_url = ngrok.connect(port).public_url
    print(f" * Ngrok Tunnel: {public_url}")
    
    # Update config or environment if needed, though we use request.host_url in app
    
    app.run(debug=True, port=port, use_reloader=False) # use_reloader=False to prevent double ngrok tunnels
