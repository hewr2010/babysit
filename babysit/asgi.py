"""
ASGI entry point for babysit app
Usage: uvicorn babysit.asgi:app --host 0.0.0.0 --port 5000
"""
from asgiref.wsgi import WsgiToAsgi
from .app import create_app

flask_app = create_app()
app = WsgiToAsgi(flask_app)
