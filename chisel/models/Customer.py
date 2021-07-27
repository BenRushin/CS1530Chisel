from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from chisel import app, db, login_manager
from datetime import datetime

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('customer.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('customer.id'))
)

class Customer(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    bio = db.Column(db.String(300), nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    posts = db.relationship('Post', backref='author', lazy=True)
    sessions = db.relationship( 'WorkoutSession', backref='customer' )

    followed = db.relationship(
        'Customer', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def follow(self, customer):
        if not self.is_following(customer):
            self.followed.append(customer)

    def unfollow(self, customer):
        if self.is_following(customer):
            self.followed.remove(customer)

    def is_following(self, customer):
        return self.followed.filter(
            followers.c.followed_id == customer.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)

        # we include ALL own posts and admin (user_id=1) posts!
        own = Post.query.filter_by(user_id=self.id)
        admin = Post.query.filter_by(user_id=1) 
        return followed.union(own).union(admin).order_by(Post.date_posted.desc())

    def __repr__(self):
        return '<User %r>' % self.username


@login_manager.user_loader
def load_user(user_id):
    return Customer.query.get(int(user_id))


# eventually we can move this to its own file...if we needed
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"

class WorkoutSession(db.Model):
    id = db.Column( db.Integer, primary_key = True )
    name = db.Column( db.String( 128 ), nullable = False )
    desc = db.Column( db.Text, nullable = True )
    date = db.Column( db.DateTime )
    type = db.Column( db.Integer )
    user_id = db.Column( db.Integer, db.ForeignKey( 'customer.id' ), nullable = False )
    exercises = db.relationship( 'Exercise', backref='workout_session' )

class Exercise(db.Model):
    id = db.Column( db.Integer, primary_key = True )
    name = db.Column( db.String( 128 ), nullable = False )
    reps = db.Column( db.Text, nullable = True )
    sets = db.Column( db.Integer, nullable = False )
    session_id = db.Column( db.Integer, db.ForeignKey( 'workout_session.id' ), nullable = False )