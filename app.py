import os
from flask import Flask
import threading
import time

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Telegram Bot</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .status { color: green; font-size: 24px; }
            </style>
        </head>
        <body>
            <h1>🤖 Telegram Bot</h1>
            <p class="status">✅ Bot is running successfully!</p>
            <p>Owner ID: 1484010221</p>
            <p>Deployed on Render.com</p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return "OK"

def run_bot():
    """تشغيل البوت بعد تأخير بسيط"""
    time.sleep(10)  # انتظر 10 ثواني لضمان تشغيل Flask أولاً
    try:
        from bot import main
        main()
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == '__main__':
    # بدء البوت في thread منفصل
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # تشغيل خادم Flask
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port)