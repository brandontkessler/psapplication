from flask import render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from main_app import db, bcrypt
from main_app.models import User
from main_app.users.forms import RegistrationForm, LoginForm


users = Blueprint('users', __name__)


@users.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: # If user is logged in, redirect
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit(): # For valid post request
        hashed_password = bcrypt.generate_password_hash(form.password.data)\
                                .decode('utf-8')
        user = User(email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('You have been registered, now you can log in', 'success')
        return redirect(url_for('users.login'))
    return render_template('register.html', title="Register", form=form)


@users.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,
                                               form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check email and password',
                  'danger')
    return render_template('login.html', title="Login", form=form)

@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))
