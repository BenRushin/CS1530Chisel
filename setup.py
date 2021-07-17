import sqlalchemy
db = sqlalchemy.create_engine('sqlite:///chisel.db')
from app import db
db.create_all()