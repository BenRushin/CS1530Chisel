import os, secrets
from flask import Flask, render_template, url_for, flash, send_from_directory, abort, session, request, redirect
from flask_login import login_user, logout_user, login_required, current_user
from chisel import app, db, bcrypt
from chisel.models.Customer import Customer, Post, WorkoutSession
from chisel.forms import RegistrationForm, LoginForm, EmptyForm, UpdateProfileForm, PostForm
from PIL import Image
from datetime import date, datetime

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        customer = Customer.query.filter_by(email=form.email.data).first()
        if customer and bcrypt.check_password_hash(customer.password, form.password.data):
            login_user(customer, remember=form.remember.data)
            flash('Successful login!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard')) 
        else:
            flash('Invalid Login!', 'danger')
    return render_template('login.html', form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        customer = Customer(username=form.username.data, email=form.email.data, password=hashed_pw, bio="")
        db.session.add(customer)
        db.session.commit()
        flash(f'Welcome to Chisel, {form.username.data}!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    upcoming_sessions = WorkoutSession.query.filter( WorkoutSession.date >= datetime.today(), WorkoutSession.user_id == current_customer.id )

    if not upcoming_sessions:
        return render_template('dashboard.html', username=current_user.username )
        
    return render_template('dashboard.html', username=current_user.username, next_ses = upcoming_sessions.first() )
    
@app.route('/create-session', methods=['GET', 'POST'])
@login_required
def create_session():
    if request.method == 'POST':
        current_customer = Customer.query.filter_by( username = current_user.username ).first()
        new_session = WorkoutSession( name = request.form[ "sesname" ], desc = request.form[ "sesdesc" ], 
                                      date = datetime.strptime( request.form[ "sesdate" ], '%Y-%m-%d' ), type = int( request.form[ "sestype" ] ), user_id = current_customer.id )
        db.session.add( new_session )
        db.session.commit()
        success_str = "Successfully created a new session!"
        if request.form.get( "sesredir" ):
            success_str += "\nRedirected to session list."
            flash( success_str )
            return redirect( url_for( 'session_list' ) )
        else:
            flash( success_str )

    return render_template('create_session.html', username=current_user.username)


@app.route('/session-list', methods=['GET', 'POST'])
@login_required
def session_list():
    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    return render_template('session_list.html', username=current_user.username, ses_list = current_customer.sessions )


@app.route( '/session-list/delete/' )
@app.route( '/session-list/delete/<session_id>' )
def delete_session( session_id = None ):
    if not session_id:
        flash( "This room ID doesn't exist." )
        return redirect( url_for( 'session_list' ) )

    deleted_session_name = WorkoutSession.query.filter_by( id = session_id ).one().name
    WorkoutSession.query.filter_by( id = session_id ).delete()
    db.session.commit()

    
    flash( "Successfully deleted session " + deleted_session_name )
    return redirect( url_for( 'session_list' ) )



@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/connect")
@login_required
def connect():
    page = request.args.get('page', 1, type=int)
    # we want to query only followers posts using this:
    posts = Customer.followed_posts(current_user).paginate(page=page, per_page=5)
    # if we want to query ALL posts, we can use:
    #posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=2)
    
    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    customer_post_count = Post.query.filter_by( user_id = current_customer.id ).count()

    # and here is the search function
    q = request.args.get('q')
    if q:
        customers = Customer.query.filter(Customer.username.startswith(q) | Customer.email.startswith(q)).limit(10).all()
        return render_template('connect.html', customers=customers, username=current_user.username, post_count = customer_post_count)
    
    return render_template('connect.html', posts=posts, username=current_user.username, post_count = customer_post_count)




@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('connect'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('connect'))



@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    customer = Customer.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=customer)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    form = EmptyForm()
    return render_template('user_posts.html', posts=posts, user=customer, form=form)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture = random_hex + f_ext
    pic_path = os.path.join(app.root_path, 'static/images/profile_pics/', picture)

    output_size = (161, 161) 
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(pic_path)

    return picture


@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.bio.data = current_user.bio
    image_file = url_for('static', filename='images/profile_pics/'+current_user.image_file)
    return render_template('profile.html', title='Your Profile',
                           image_file=image_file, form=form)



@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = Customer.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username), 'warning')
            return redirect(url_for('dashboard'))
        if user == current_user:
            flash('You cannot follow yourself!', 'warning')
            return redirect(url_for('user_posts', username=username))
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username), 'success')
        return redirect(url_for('user_posts', username=username))
    else:
        return redirect(url_for('dashboard'))

@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = Customer.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username), 'warning')
            return redirect(url_for('dashboard'))
        if user == current_user:
            flash('You cannot unfollow yourself!', 'warning')
            return redirect(url_for('user_posts', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash('You are no longer following {}!'.format(username), 'primary')
        return redirect(url_for('user_posts', username=username))
    else:
        return redirect(url_for('dashboard'))