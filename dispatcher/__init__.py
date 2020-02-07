"""
Create Flask application.
"""
import os
import traceback
from flask import Flask, jsonify
from flask_pymongo import PyMongo

from dispatcher.routes.base import base
from dispatcher.errors import (
    AbstractApiException, GenericApiError, UncatchedApiError, AuthenticationError
)

mdb = PyMongo()

def respond_error(exception):
    """
    Transform an error class to a HTTP Response.

    :param Exception exception: any exception
    :rtype: flask.Response
    """
    if not issubclass(exception.__class__, AbstractApiException):
        message = str(exception)
        payload = {}

        exception = UncatchedApiError(
            message=message,
            status_code=500,
            payload=payload
        )

    traceback.print_exc()
    response = jsonify(exception.to_dict())
    response.status_code = exception.status_code

    return response

def register_extensions(app):
    """
    Register all extensions for app.

    :param FlaskClient app:
    """
    mdb.init_app(app)

def create_app():
    app = Flask(__name__)
    app.register_error_handler(code_or_exception=GenericApiError, f=respond_error)
    app.register_error_handler(code_or_exception=UncatchedApiError, f=respond_error)
    app.register_error_handler(code_or_exception=AuthenticationError, f=respond_error)
    if not app.config['DEBUG']:
        app.register_error_handler(code_or_exception=Exception, f=respond_error)
    
    app.register_blueprint(base)

    app.config["MONGO_URI"] = "mongodb://localhost:27017/naas"
    
    register_extensions(app)

    return app
