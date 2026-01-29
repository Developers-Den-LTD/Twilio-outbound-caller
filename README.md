# Twilio Outbound Caller

A simple Flask-based web application that allows you to make outbound calls directly from your browser using the Twilio Voice SDK v2.

## Prerequisites

Before you begin, ensure you have the following:

- **Python 3.10+** installed on your system.
- A **Twilio Account** (Account SID and Auth Token).
- At least one **Twilio Phone Number** in your account.
- An **ngrok** account and auth token (for creating a public tunnel to receive Twilio webhooks).

## Setup Instructions

1. **Clone or Download** the project files to your local machine.

2. **Install Dependencies**:
   Navigate to the project directory and run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure ngrok**:
   Ensure you have ngrok installed and authenticated on your system:
   ```bash
   ngrok config add-authtoken <your_auth_token>
   ```

## How to Run

1. **Start the Application**:
   Run the following command in your terminal:
   ```bash
   python app.py
   ```
   The application will automatically:
   - Start the Flask server on port 5000.
   - Initialise an ngrok tunnel.
   - Print the public ngrok URL to the console (e.g., `* Ngrok Tunnel: https://xxxx.ngrok-free.dev`).

2. **Access the Web Interface**:
   Open a web browser and navigate to the **Ngrok Tunnel URL** printed in your terminal.
   > [!IMPORTANT]
   > You **must** use the ngrok URL (HTTPS) instead of `localhost` for the Twilio Voice SDK and microphone permissions to work correctly.

3. **Log In**:
   Enter your Twilio **Account SID** and **Auth Token** in the login form.

4. **Make a Call**:
   - Select a **Caller ID** from the dropdown (these are your Twilio numbers).
   - Enter the destination phone number using the dialpad or your keyboard.
   - Click **Call**.
   - Grant microphone permissions when prompted by your browser.

## Project Structure

- `app.py`: The Flask backend handling authentication, token generation, and the TwiML webhook.
- `templates/index.html`: The frontend UI using Twilio Voice SDK v2 and Tailwind CSS.
- `requirements.txt`: Python dependencies.

## Troubleshooting

- **Microphone Issues**: Ensure you are accessing the site via **HTTPS** (the ngrok URL). Browsers block microphone access on non-secure (HTTP) connections.
- **Ngrok Errors**: If you see an ngrok error, ensure no other ngrok processes are running and that your auth token is configured.
- **TwiML Error**: The app automatically creates a TwiML application named "TwilioBrowserDialer" in your Twilio console. If calls fail, verify the "Voice URL" for this app in your Twilio console matches your current ngrok URL.
