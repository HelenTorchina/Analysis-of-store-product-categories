from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Подключение к базе данных
class Config(object):
    SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/dbname'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


db = SQLAlchemy()

# Создание приложения
def create_app():
    server = Flask(__name__)
    server.config.from_object(Config)
    db.init_app(server)

    from .dashboard import create_dashapp
    dash_app = create_dashapp(server)
    return server 
