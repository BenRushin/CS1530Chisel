from flask_sqlalchemy import SQLAlchemy
from appbase import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120))
    
    def __repr__(self):
        return '<User %r>' % self.name