import os
from flask import Flask
import threading
import subprocess
import sys
import time

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Bot</title>
        <style>
            body { 
                font-family: 'Arial', sans-serif; 
                text-align: center; 
                padding: 50px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                padding: 40px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            .status { 
                color: #00ff88; 
                font-size: 28px; 
                margin: 20px 0;
            }
            .info {
                background: rgba(255, 255, 255, 0.2);
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Telegram User Data Bot</h1>
            <div class="status">✅ Bot is running successfully!</div>
            <div class="info">
                <strong>Owner ID:</strong> 1484010221
            </div>
            <div class="info">
                <strong>Platform:</strong> Render.com
            </div>
            <div class="info">
                <strong>Status:</strong> <span style="color: #00ff88;">Active</span>
            </div>
            <p>This bot is handling user data management and search operations.</p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/status')
def status():
    return {
        "status": "running",
        "service": "telegram-bot",
        "platform": "render",
        "timestamp": time.time()
    }

def run_bot():
    """تشغيل البوت في عملية منفصلة"""
    print("🚀 Starting Telegram Bot...")
    try:
        # تشغيل البوت كعملية فرعية
        subprocess.run([sys.executable, "bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Bot process failed: {e}")
        print("🔄 Restarting bot in 10 seconds...")
        time.sleep(10)
        run_bot()  # إعادة التشغيل
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("🔄 Restarting bot in 10 seconds...")
        time.sleep(10)
        run_bot()  # إعادة التشغيل

if __name__ == '__main__':
    # بدء البوت في thread منفصل
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # تشغيل خادم Flask على المنفذ المطلوب
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 Starting Flask server on port {port}")
    print(f"📡 Server will be available at: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)