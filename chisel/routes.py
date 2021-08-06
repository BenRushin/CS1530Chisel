import os, secrets, random
from flask import Flask, render_template, url_for, flash, send_from_directory, abort, session, request, redirect
from flask_login import login_user, logout_user, login_required, current_user
from chisel import app, db, bcrypt
from chisel.models.Customer import Customer, Post
from chisel.models.Workout import Exercise, WorkoutSession, ExerciseModifier, ExerciseStatus
from chisel.forms import RegistrationForm, LoginForm, EmptyForm, UpdateProfileForm, PostForm
from PIL import Image
from datetime import date, datetime
from sqlalchemy import asc

@app.route('/', methods=['GET', 'POST'])
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
        customer = Customer(username=form.username.data, email=form.email.data, password=hashed_pw, bio="",dark_mode=False)
        db.session.add(customer)
        db.session.commit()
        flash(f'Welcome to Chisel, {form.username.data}!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    upcoming_sessions = WorkoutSession.query.filter( WorkoutSession.date >= datetime.now().date(), 
    WorkoutSession.user_id == current_customer.id, WorkoutSession.completed == False ).order_by( asc( WorkoutSession.date ) )

    if not upcoming_sessions:
        return render_template('dashboard.html', username=current_user.username )
        
    return render_template('dashboard.html', username=current_user.username, next_ses = upcoming_sessions.first() )

# Workout name, rep count, set count
workout_examples = {
    1: [
        ("Jog in Place (1 rep = 1 sec.)", 60, 3, 0),
        ("Fast Walk or Brisk Jog (1 rep = 1 mi.)", 1, 1, 1),
        ("Jumping Jacks", 30, 3, 2),
        ("Stair Climbing", 10, 1, 3),
        ("Mountain Climbers", 40, 2, 4)
    ],
    2: [
        ("Push-ups", 15, 3, 5),
        ("Lateral Pulldown", 10, 3, 6),
        ("Bicep Curls", 10, 3, 7),
        ("Bench Press", 10, 3, 8),
        ("Bent-over Row", 8, 3, 9)
    ],
    3: [
        ("Deadlift", 10, 3, 10),
        ("Squats", 10, 3, 11),
        ("Lunges", 20, 3, 12),
    ],
    4: [
        ("Sit-ups", 25, 3, 13),
        ("Plank (1 rep = 1 sec.)", 30, 3, 14),
        ("Side Plank (1 rep = 1 sec.)", 30, 3, 15),
    ]
}

@app.route( '/workout/update/<session_id>/<workout_id>/cancel', methods=['POST'] )
def cancel_workout( session_id = None, workout_id = None ):
    if not session_id or not workout_id:
        return redirect( url_for( 'session_list' ) )

    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    current_session = WorkoutSession.query.filter( WorkoutSession.id == session_id ).one()
    exercise_to_update = Exercise.query.filter( Exercise.session_id == session_id, Exercise.id == workout_id ).one()

    exercise_to_update.status = 1
    session_complete = True
    for e in current_session.exercises:
        if e.status == 0:
            session_complete = False
            break

    current_session.completed = session_complete
    if current_session.completed:
        flash( "Congratulations! You have completed your session.", 'success' )
    
    db.session.commit()
    return redirect( url_for( 'view_session', session_id = session_id ) )


@app.route( '/workout/update/<session_id>/<workout_id>/<tooHard>', methods=['POST'] )
@app.route( '/workout/update/<session_id>/<workout_id>/0/<tooEasy>', methods=['POST'] )
@app.route( '/workout/update/<session_id>/<workout_id>', methods=['POST'] )
def complete_workout( session_id = None, workout_id = None, tooHard = False, tooEasy = False):
    if not session_id or not workout_id:
        return redirect( url_for( 'session_list' ) )
    
    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    current_session = WorkoutSession.query.filter( WorkoutSession.id == session_id ).one()
    exercise_to_update = Exercise.query.filter( Exercise.session_id == session_id, Exercise.id == workout_id ).one()

    exercise_to_update.status = 3
    session_complete = True
    for e in current_session.exercises:
        if e.status == 0:
            session_complete = False
            break

    cur_reps = exercise_to_update.reps
    cur_sets = exercise_to_update.sets

    if tooEasy:
        if  int(cur_reps) < 12:
            cur_reps = str(int(cur_reps)+3) 
        else:
            cur_sets += 1
        flash("Exercise was made harder!", 'success')

    
    if tooHard:
        if int(cur_reps) > 8:
            cur_reps = str(int(cur_reps)-5) 
        else:
            cur_sets -= 1
        flash("Exercise was made easier!", 'success')

    exercise_to_update.customer_responded = True

    db.session.add( ExerciseModifier( exercise_id = exercise_to_update.unique_id_in_dict, rep_modifier = cur_reps, set_modifier = cur_sets, user_id = current_customer.id ) )
    db.session.commit()

    current_session.completed = session_complete
    if current_session.completed:
        flash( "Congratulations! You have completed your session.", 'success' )

    db.session.commit()
    
    return redirect( url_for( 'view_session', session_id = session_id ) )


@app.route('/create-session', methods=['GET', 'POST'])
@login_required
def create_session():
    if request.method == 'POST':
        current_customer = Customer.query.filter_by( username = current_user.username ).first()
        ses_type = int( request.form[ "sestype" ] )
        new_session = WorkoutSession( name = request.form[ "sesname" ], desc = request.form[ "sesdesc" ], 
                                      date = datetime.strptime( request.form[ "sesdate" ], '%Y-%m-%d' ), type = ses_type, user_id = current_customer.id, completed = False )

        db.session.add( new_session )
        db.session.commit()

        # print( new_session.id )
        possible_exercises = workout_examples[ ses_type ] if ses_type != 5 else workout_examples[ random.randint( 1, 4 ) ]
        
        random.shuffle( possible_exercises )
        # print( possible_exercises )
        for i in range(3):
            this_exercise = possible_exercises[ i ]
            # print( this_exercise )
            final_reps = this_exercise[ 1 ]
            final_sets = this_exercise[ 2 ]
            exercise_mods = ExerciseModifier.query.filter( ExerciseModifier.exercise_id == this_exercise[ 3 ], ExerciseModifier.user_id == current_customer.id ).all()
            for em in exercise_mods:
                final_reps = em.rep_modifier
                final_sets = em.set_modifier

            new_exercise = Exercise( name = this_exercise[ 0 ], 
                            reps = str( final_reps ),
                            sets = final_sets, session_id = new_session.id, unique_id_in_dict = this_exercise[ 3 ], customer_responded = False, status = 0 )
            db.session.add( new_exercise )

            if ses_type == 5:
                possible_exercises = workout_examples[ random.randint( 1, 4 ) ]
                random.shuffle( possible_exercises )

        db.session.commit()
        success_str = "Successfully created a new session!"
        if request.form.get( "sesredir" ):
            success_str += "\nRedirected to session list."
            flash( success_str, 'success' )
            return redirect( url_for( 'session_list' ) )
        else:
            flash( success_str, 'success' )

    return render_template('create_session.html', username=current_user.username)


@app.route('/session-list', methods=['GET', 'POST'])
@login_required
def session_list():
    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    current_sessions = WorkoutSession.query.filter( WorkoutSession.user_id == current_customer.id, WorkoutSession.completed == False ).all()
    return render_template('session_list.html', username=current_user.username, ses_list = current_sessions )


@app.route('/session-history', methods=['GET', 'POST'])
@login_required
def session_history():
    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    prev_sessions = WorkoutSession.query.filter( WorkoutSession.user_id == current_customer.id, WorkoutSession.completed == True ).all()
    return render_template('session_history.html', username=current_user.username, ses_list = prev_sessions )


@app.route('/stats', methods=['GET'])
@login_required
def statistics():
    current_customer = Customer.query.filter_by( username = current_user.username ).first()
    total_ses_count = WorkoutSession.query.filter_by( user_id = current_customer.id ).count()
    completed_ses_count = WorkoutSession.query.filter( WorkoutSession.user_id == current_customer.id, WorkoutSession.completed == True ).count()

    uncompleted_ses_count = total_ses_count - completed_ses_count
    exercises_completed = 0
    exercises_skipped = 0

    all_sessions = WorkoutSession.query.filter( WorkoutSession.user_id == current_customer.id ).all()
    for ses in all_sessions:
        completed_count = Exercise.query.filter( Exercise.session_id == ses.id, Exercise.status == 3 ).count()
        skipped_count = Exercise.query.filter( Exercise.session_id == ses.id, Exercise.status == 1 ).count()
        exercises_completed += completed_count
        exercises_skipped += skipped_count

    return render_template('stats.html', username=current_user.username, total_count = total_ses_count, 
    completed_count = completed_ses_count, uncompleted_ses = uncompleted_ses_count, completed_ex = exercises_completed, skipped_ex = exercises_skipped )

@app.route( '/session-list/delete/' )
@app.route( '/session-list/delete/<session_id>' )
def delete_session( session_id = None ):
    if not session_id:
        flash( "This session ID doesn't exist.", 'danger' )
        return redirect( url_for( 'session_list' ) )

    deleted_session_name = WorkoutSession.query.filter_by( id = session_id ).one().name
    WorkoutSession.query.filter_by( id = session_id ).delete()
    Exercise.query.filter( Exercise.session_id == session_id ).delete()
    db.session.commit()

    
    flash( "Successfully deleted session " + deleted_session_name, 'success' )
    return redirect( url_for( 'session_list' ) )

session_types = {
    1: "Cardio-Only",
    2: "Upper-body focus",
    3: "Lower-body focus",
    4: "Abdominal/core strength",
    5: "Variety"
}

@app.route( '/session-list/view/' )
@app.route( '/session-list/view/<session_id>' )
def view_session( session_id = None ):
    if not session_id:
        flash( "This session ID doesn't exist.", 'danger' )
        return redirect( url_for( 'session_list' ) )

    this_session = WorkoutSession.query.filter_by( id = session_id ).one()
    exercises = this_session.exercises

    return render_template( 'session_view.html', ses = this_session, session_type = session_types[ this_session.type ], ex_list = exercises )

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
        return render_template('connect.html', customers=customers, posts=posts, username=current_user.username, post_count = customer_post_count)
    
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
    return render_template('user_posts.html', posts=posts, user=customer, username = current_user.username, form=form)


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
                           image_file=image_file, username = current_user.username, form=form)


@app.route("/settings", methods=['GET','POST'])
@login_required
def settings():
    if request.method == "POST":
        if(request.form.get("darkmode")=="on"):
            current_user.dark_mode = True
        else:
            current_user.dark_mode = False
        db.session.commit()
    return render_template('settings.html', title='Your Settings', darkmode_enabled=current_user.dark_mode)
    


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