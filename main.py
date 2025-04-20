from app import create_app, socketio
from flask import render_template
import os
from dotenv import load_dotenv

load_dotenv()

app = create_app()

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
