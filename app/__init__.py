from flask import Flask
from dotenv import load_dotenv
from .config import DevConfig
from .database.db import create_tables
from .extensions import mail, socketio
from .state import cleanup_inactive_rooms
from .sockets.handlers import register_socketio_events

# Import Blueprints
from .routes.main_routes import main_routes as main_bp
from .routes.auth_routes import auth_routes as auth_bp
from .routes.utility_routes import utility_routes as util_bp
from .routes.message_routes import message_routes as message_bp

import threading

def create_app(test_config=None):
    load_dotenv()

    app = Flask(__name__)

    if test_config:
        app.config.from_mapping(test_config)
    else:
        app.config.from_object(DevConfig)

    # Initialize extensions
    mail.init_app(app)
    socketio.init_app(app)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(util_bp)
    app.register_blueprint(message_bp)

    # Register Socket.IO events
    register_socketio_events()

    # Create DB tables
    create_tables()

    return app


def start_background_threads():
    # Start a thread for cleaning up inactive rooms
    thread = threading.Thread(target=cleanup_inactive_rooms)
    thread.daemon = True
    thread.start()
