# app/admin/__init__.py
from flask import Blueprint

admin = Blueprint('admin', __name__)

from . import routes
from . import metric_keys_api
from . import debug_routes
