import os
# Patch standard library with gevent BEFORE anything else imports
from gevent import monkey
monkey.patch_all()

from app import create_app, socketio

# Render sets FLASK_ENV=production via environment variables
app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    socketio.run(app)