Twilio Outbound Caller (Desktop Version)
=======================================

This is a standalone version of the Twilio Outbound Caller.

How to use:
1. Run `Twilio-Caller.exe`.
2. A window will open with the dialer UI.
3. Sign in with your Twilio Account SID and Auth Token.
4. The application automatically starts an ngrok tunnel to allow Twilio to reach your local machine for voice webhooks.

Note:
- You must have an active internet connection.
- If you have an ngrok account, it's recommended to authenticate ngrok on your machine once using the command: `ngrok config add-authtoken <YOUR_TOKEN>` (though it may work without it for short sessions).

Built with Flask, PyWebView, and PyInstaller.
