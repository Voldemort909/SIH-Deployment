"""
Flask Extension Instances
Centralized to prevent circular dependencies between models, routes, and the application factory.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# SQLAlchemy ORM instance
db = SQLAlchemy()

# Database migration utility
migrate = Migrate()

# Cross-Origin Resource Sharing handler
cors = CORS()
