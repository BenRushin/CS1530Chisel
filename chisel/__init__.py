from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate


app = Flask(__name__)
app.config['SECRET_KEY'] = b'\x93\xb7d\xf4\x8do\xc4\x14~\xffw\xc1\xdd\xdc\xb6\xedt_\xe9\x96M:\x0cVa\x03\x0c5\xc0 j\xaa' # randomly generated
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chisel.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning' 

from chisel import routes
