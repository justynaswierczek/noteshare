from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from . import db
import traceback
from bson import ObjectId

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        try:
            print(f"Attempting login for email: {email}")
            user = User.get_by_email(email)
            
            if not user:
                print("User not found")
                flash('Please check your login details and try again.', category='error')
                return redirect(url_for('auth.login'))

            if not check_password_hash(user.password, password):
                print("Invalid password")
                flash('Please check your login details and try again.', category='error')
                return redirect(url_for('auth.login'))

            print(f"Login successful for user: {user.id}")
            login_user(user, remember=remember)
            flash('Logged in successfully!', category='success')
            return redirect(url_for('views.home'))
        except Exception as e:
            print("Error during login:")
            print(traceback.format_exc())
            flash('An error occurred during login. Please try again.', category='error')
            return redirect(url_for('auth.login'))

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.home'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        firstName = request.form.get('firstName')
        lastName = request.form.get('lastName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        try:
            print(f"Attempting sign up for email: {email}")
            user = User.get_by_email(email)
            
            if user:
                print("Email already exists")
                flash('Email already exists.', category='error')
            elif len(email) < 4:
                flash('Email must be greater than 3 characters.', category='error')
            elif len(firstName) < 2:
                flash('First name must be greater than 1 character.', category='error')
            elif len(lastName) < 2:
                flash('Last name must be greater than 1 character.', category='error')
            elif password1 != password2:
                flash('Passwords don\'t match.', category='error')
            elif len(password1) < 7:
                flash('Password must be at least 7 characters.', category='error')
            else:
                # Create user document
                user_data = {
                    'email': email,
                    'first_name': firstName,
                    'last_name': lastName,
                    'password': generate_password_hash(password1, method='pbkdf2:sha256')
                }
                
                print("Inserting new user into database")
                print(f"User data: {user_data}")
                
                # Insert into MongoDB
                result = db.users.insert_one(user_data)
                print(f"Insert result: {result.inserted_id}")
                
                # Create User object with the inserted data
                user_data['_id'] = result.inserted_id
                new_user = User(user_data)
                
                print(f"New user created with ID: {new_user.id}")
                login_user(new_user, remember=True)
                flash('Account created successfully!', category='success')
                return redirect(url_for('views.home'))
        except Exception as e:
            print("Error during sign up:")
            print(traceback.format_exc())
            flash(f'An error occurred while creating your account: {str(e)}', category='error')

    return render_template("sign_up.html", user=current_user)