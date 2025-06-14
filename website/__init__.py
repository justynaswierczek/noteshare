from flask import Flask
from flask_pymongo import PyMongo
from flask_login import LoginManager
from os import path
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
from flask import session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables from .env file
load_dotenv()

# Initialize Flask extensions
mongo = PyMongo()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)

# Initialize MongoDB client and database globally
try:
    print("Initializing MongoDB connection...")
    client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/notesharebase'))
    # Test the connection
    client.server_info()
    print("Successfully connected to MongoDB!")
    
    db = client.notesharebase
    print(f"Connected to database: {db.name}")
    
    # List all databases
    print("Available databases:")
    for db_name in client.list_database_names():
        print(f"- {db_name}")
    
    # List collections in our database
    print(f"\nCollections in {db.name}:")
    for collection in db.list_collection_names():
        print(f"- {collection}")
        
except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")
    print("Full error details:")
    import traceback
    print(traceback.format_exc())
    raise

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['MONGO_URI'] = os.getenv('MONGODB_URI')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))
    
    # Session configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes in seconds
    app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookie over HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Protect against CSRF
    
    # Initialize extensions
    mongo.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from .views import views
    from .auth import auth
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Clear any existing session
    @app.before_request
    def clear_session():
        if not session.get('_fresh'):
            session.clear()
    
    # Initialize MongoDB collections
    try:
        # List existing collections
        existing_collections = db.list_collection_names()
        print(f"\nExisting collections: {existing_collections}")
        
        # Create collections if they don't exist
        collections = ['users', 'notes', 'files', 'classes', 'activities', 'folders', 'announcements', 'events', 'homework']
        for collection in collections:
            if collection not in existing_collections:
                print(f"Creating collection: {collection}")
                db.create_collection(collection)
                print(f"Created collection: {collection}")
            else:
                print(f"Collection {collection} already exists")
        
        # Create indexes
        print("\nCreating indexes...")
        db.users.create_index('email', unique=True)
        db.notes.create_index('user_id')
        db.notes.create_index('class_id')
        db.files.create_index('user_id')
        db.files.create_index('class_id')
        db.files.create_index('folder_id')
        db.classes.create_index('class_id', unique=True)
        db.classes.create_index('creator_id')
        db.folders.create_index('class_id')
        db.folders.create_index('user_id')
        db.announcements.create_index('class_id')
        db.events.create_index('class_id')
        db.homework.create_index('class_id')
        print("Indexes created successfully!")
        
        print("\nDatabase and collections initialized successfully!")
    except Exception as e:
        print(f"Error initializing collections: {str(e)}")
        print("Full error details:")
        import traceback
        print(traceback.format_exc())
        raise

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            # Convert the string ID to MongoDB's ObjectId
            user_data = db.users.find_one({'_id': ObjectId(user_id)})
            if user_data:
                # Instantiate the User class with the retrieved data
                return User(user_data)
            return None
        except Exception as e:
            # Handle potential errors, e.g., invalid ObjectId format
            print(f"Error loading user with ID {user_id}: {str(e)}")
            return None

    return app

