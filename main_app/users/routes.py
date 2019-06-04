from flask import render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from main_app import db, bcrypt
from main_app.models import User
from main_app.users.forms import RegistrationForm, LoginForm
from main_app.users.token import gen_token, verify_token
from main_app.users.util import send_email


users = Blueprint('users', __name__)


@users.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: # If user is logged in, redirect
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit(): # For valid post request
        hashed_password = bcrypt.generate_password_hash(form.password.data)\
                                .decode('utf-8')
        user = User(email=form.email.data,
                    password=hashed_password,
                    confirmed=False)
        db.session.add(user)
        db.session.commit()

        token = gen_token(user.email)
        confirm_url = url_for('users.confirm_email', token=token, _external=True)
        html = render_template('emails/confirm.html', confirm_url=confirm_url)
        subject = "Email Confirmation - Thanks for registering, please confirm"
        send_email(user.email, subject, html)

        login_user(user)

        flash('A confirmation email has been sent.', 'success')
        return redirect(url_for("users.unconfirmed"))
    return render_template('register.html', title="Register", form=form)


@users.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            # if user is redirected to login page,
            # we can access the parameter of the page that they came from
            # and direct them back to the page they were trying to access
            # before logging in.
            next_page = request.args.get('next')
            flash('You are logged in', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login unsuccessful. Check email or password', 'danger')
    return render_template('login.html', title='Login', form=form)


@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@users.route("/confirm/<token>")
@login_required
def confirm_email(token):
    try:
        email = verify_token(token)

        user = User.query.filter_by(email=email).first_or_404()
        if user.confirmed:
            flash('Account is already confirmed. Please login.', 'success')
        else:
            user.confirmed = True

            db.session.add(user)
            db.session.commit()
            flash('You have been confirmed. Thanks!', 'success')
            return redirect(url_for('main.home'))
    except:
        flash('The confirmation link is invalid or has expired', 'danger')
        return redirect(url_for('users.unconfirmed'))


@users.route('/unconfirmed')
@login_required
def unconfirmed():
    if current_user.confirmed:
        return redirect(url_for('main.home'))
    return render_template('unconfirmed.html')


@users.route('/resend_confirmation')
@login_required
def resend_confirmation():
    token = gen_token(current_user.email)
    confirm_url = url_for('users.confirm_email', token=token, _external=True)
    html = render_template('emails/confirm.html', confirm_url=confirm_url)
    subject = "Confirmation Email - Resent"
    send_email(current_user.email, subject, html)
    flash('A new confirmation email has been sent.', 'success')
    return redirect(url_for('users.unconfirmed'))
