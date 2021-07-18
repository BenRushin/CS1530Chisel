import os, secrets
from flask import Flask, render_template, url_for, flash, send_from_directory, session, request, redirect
from flask_login import login_user, logout_user, login_required, current_user
from chisel import app, db, bcrypt
from chisel.models.Customer import Customer
from chisel.forms import RegistrationForm, LoginForm, UpdateProfileForm
from PIL import Image

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
    return render_template('dashboard.html')


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))




    

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
