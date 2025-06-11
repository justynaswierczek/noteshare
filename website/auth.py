# Importowanie niezbędnych modułów
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from . import db, limiter
from flask_limiter.util import get_remote_address
import traceback
from bson import ObjectId
import re

auth = Blueprint('auth', __name__)

def validate_password(password):
    """Validate password strength.
    
    Args:
        password (str): Password to validate
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"
    
    return True, ""

def get_email():
    return request.form.get('email')


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("3 per minute", key_func=get_email)
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        try:
            print(f"Attempting login for email: {email}")
            # Próba znalezienia użytkownika w bazie danych
            user = User.get_by_email(email)
            
            # Sprawdzenie czy użytkownik istnieje
            if not user:
                print("User not found")
                flash('Please check your login details and try again.', category='error')
                return redirect(url_for('auth.login'))

            # Weryfikacja hasła
            if not check_password_hash(user.password, password):
                print("Invalid password")
                flash('Please check your login details and try again.', category='error')
                return redirect(url_for('auth.login'))

            # Logowanie udane - tworzenie sesji użytkownika
            print(f"Login successful for user: {user.id}")
            login_user(user, remember=remember)
            flash('Logged in successfully!', category='success')
            return redirect(url_for('views.home'))
        except Exception as e:
            # Obsługa błędów podczas logowania
            print("Error during login:")
            print(traceback.format_exc())
            flash('An error occurred during login. Please try again.', category='error')
            return redirect(url_for('auth.login'))

    # Obsługa żądania GET - wyświetlenie formularza logowania
    return render_template("login.html", user=current_user)

# Endpoint do wylogowania - wymaga zalogowanego użytkownika
@auth.route('/logout')
@login_required
def logout():
    # Wylogowanie użytkownika i przekierowanie do strony głównej
    logout_user()
    return redirect(url_for('views.home'))

# Endpoint do rejestracji - obsługuje metody GET i POST
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    # Obsługa żądania POST (próba rejestracji)
    if request.method == 'POST':
        # Pobieranie danych z formularza
        email = request.form.get('email')
        firstName = request.form.get('firstName')
        lastName = request.form.get('lastName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        print(f"Debug - Form data received:")
        print(f"Email: {email}")
        print(f"First Name: {firstName}")
        print(f"Last Name: {lastName}")
        print(f"Password 1: {password1}")
        print(f"Password 2: {password2}")

        try:
            # Sprawdzenie czy email już istnieje
            user = User.get_by_email(email)
            
            # Walidacja danych
            if user:
                flash('Email already exists.', 'error')
                return redirect(url_for('auth.sign_up'))
            elif len(email) < 4:
                flash('Email must be greater than 4 characters.', 'error')
                return redirect(url_for('auth.sign_up'))
            elif len(firstName) < 2:
                flash('First name must be greater than 2 character.', 'error')
                return redirect(url_for('auth.sign_up'))
            elif len(lastName) < 2:
                flash('Last name must be greater than 2 character.', 'error')
                return redirect(url_for('auth.sign_up'))
            
            # Sprawdzenie czy hasła są takie same
            if not password1 or not password2:
                flash('Both password fields are required.', 'error')
                return redirect(url_for('auth.sign_up'))
                
            if password1 != password2:
                print("Debug - Passwords do not match!")
                flash('Passwords do not match. Please make sure both passwords are identical.', 'error')
                return redirect(url_for('auth.sign_up'))
            
            # Walidacja siły hasła
            is_valid, error_message = validate_password(password1)
            if not is_valid:
                print(f"Debug - Password validation failed: {error_message}")
                flash(error_message, 'error')
                return redirect(url_for('auth.sign_up'))
            
            # Przygotowanie danych użytkownika do zapisu
            user_data = {
                'email': email,
                'first_name': firstName,
                'last_name': lastName,
                'password': generate_password_hash(password1, method='pbkdf2:sha256')
            }
            
            # Zapisanie użytkownika w bazie danych MongoDB
            result = db.users.insert_one(user_data)
            
            # Utworzenie obiektu użytkownika i zalogowanie
            user_data['_id'] = result.inserted_id
            new_user = User(user_data)
            
            login_user(new_user, remember=True)
            flash('Account created successfully!', 'success')
            return redirect(url_for('views.home'))
        except Exception as e:
            print("Error during sign up:")
            print(traceback.format_exc())
            flash(f'An error occurred while creating your account: {str(e)}', 'error')
            return redirect(url_for('auth.sign_up'))

    # Obsługa żądania GET - wyświetlenie formularza rejestracji
    return render_template("sign_up.html", user=current_user)