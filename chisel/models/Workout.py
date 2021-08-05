import enum
from flask_sqlalchemy import SQLAlchemy
from chisel import app, db
from datetime import datetime

class ExerciseStatus(enum.Enum):
    NO_RESPONSE = 0,
    CANCELLED = 1,
    INCOMPLETE = 2,
    COMPLETE = 3

class WorkoutSession(db.Model):
    id = db.Column( db.Integer, primary_key = True )
    name = db.Column( db.String( 128 ), nullable = False )
    desc = db.Column( db.Text, nullable = True )
    date = db.Column( db.DateTime )
    type = db.Column( db.Integer )
    completed = db.Column( db.Boolean, default = False )
    user_id = db.Column( db.Integer, db.ForeignKey( 'customer.id' ), nullable = False )
    exercises = db.relationship( 'Exercise', backref='workout_session' )

class Exercise(db.Model):
    id = db.Column( db.Integer, primary_key = True )
    name = db.Column( db.String( 128 ), nullable = False )
    reps = db.Column( db.Text, nullable = True )
    sets = db.Column( db.Integer, nullable = False )
    session_id = db.Column( db.Integer, db.ForeignKey( 'workout_session.id' ), nullable = False )
    status = db.Column( db.Integer )
    # completed_reps = db.Column( db.Integer )
    # completed_sets = db.Column( db.Integer )