from flask_login import UserMixin
from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.first_name = user_data['first_name']
        self.last_name = user_data['last_name']
        self.password = user_data['password']

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get_by_email(email):
        try:
            user_data = db.users.find_one({'email': email})
            if user_data:
                return User(user_data)
            return None
        except Exception as e:
            print(f"Error getting user by email: {str(e)}")
            return None

    def save(self):
        try:
            user_data = {
                'email': self.email,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'password': self.password
            }
            if hasattr(self, 'id') and self.id:
                db.users.update_one({'_id': ObjectId(self.id)}, {'$set': user_data})
            else:
                result = db.users.insert_one(user_data)
                self.id = str(result.inserted_id)
        except Exception as e:
            print(f"Error saving user: {str(e)}")
            raise

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(user_data)
        return None
    except Exception as e:
        print(f"Error loading user: {str(e)}")
        return None

class Note:
    def __init__(self, note_data):
        self.id = str(note_data['_id'])
        self.title = note_data.get('title', '')
        self.content = note_data.get('content', '')
        self.user_id = note_data['user_id']
        self.date = note_data.get('date', datetime.utcnow())
        
        # Get user information
        user_data = db.users.find_one({'_id': ObjectId(self.user_id)})
        if user_data:
            self.user = {
                'id': str(user_data['_id']),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }
        else:
            self.user = None

    def to_dict(self):
        return {
            '_id': self.id,
            'title': self.title,
            'content': self.content,
            'user_id': self.user_id,
            'date': self.date,
            'user': self.user
        }

class File:
    def __init__(self, file_data):
        self.id = str(file_data['_id'])
        self.filename = file_data['filename']
        self.original_filename = file_data['original_filename']
        self.display_name = file_data.get('display_name', file_data['original_filename'])
        self.description = file_data.get('description', '')
        self.user_id = file_data['user_id']
        self.class_id = file_data.get('class_id')
        self.folder_id = file_data.get('folder_id')
        self.uploaded_at = file_data.get('uploaded_at', datetime.utcnow())
        
        # Get user information
        user_data = db.users.find_one({'_id': ObjectId(self.user_id)})
        if user_data:
            self.user = {
                'id': str(user_data['_id']),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }
        else:
            self.user = None

    def to_dict(self):
        return {
            '_id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'display_name': self.display_name,
            'description': self.description,
            'user_id': self.user_id,
            'class_id': self.class_id,
            'folder_id': self.folder_id,
            'uploaded_at': self.uploaded_at,
            'user': self.user
        }

class Class:
    def __init__(self, class_data):
        print(f"Initializing Class with data: {class_data}")  # Debug log
        self._id = str(class_data['_id'])
        self.class_id = class_data['class_id']
        self.name = class_data['name']
        self.description = class_data.get('description', '')
        self.password = class_data.get('password', '')
        self.creator_id = class_data['creator_id']
        self.created_at = class_data['created_at']
        self.members = class_data.get('members', [])
        self.color = class_data.get('color', '#4CAF50')  # Default to green if no color is set
        
        # Get creator information
        creator_data = db.users.find_one({'_id': ObjectId(self.creator_id)})
        if creator_data:
            self.creator = {
                'id': str(creator_data['_id']),
                'first_name': creator_data.get('first_name', ''),
                'last_name': creator_data.get('last_name', '')
            }
        else:
            self.creator = None
        print(f"Class initialized: {self.name} (ID: {self._id})")  # Debug log

    def to_dict(self):
        return {
            '_id': self._id,
            'class_id': self.class_id,
            'name': self.name,
            'description': self.description,
            'password': self.password,
            'creator_id': self.creator_id,
            'created_at': self.created_at,
            'members': self.members,
            'creator': self.creator,
            'color': self.color
        }

class Activity:
    def __init__(self, activity_data):
        self.id = str(activity_data['_id'])
        self.class_id = activity_data['class_id']
        self.user_id = activity_data['user_id']
        self.action = activity_data['action']
        self.details = activity_data.get('details', '')
        self.created_at = activity_data['created_at']
        
        # Get user information
        user_data = db.users.find_one({'_id': ObjectId(self.user_id)})
        if user_data:
            self.user = {
                'id': str(user_data['_id']),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }
        else:
            self.user = None

    def to_dict(self):
        return {
            '_id': self.id,
            'class_id': self.class_id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'created_at': self.created_at,
            'user': self.user
        }

class Event:
    def __init__(self, event_data):
        self.id = str(event_data['_id'])
        self.title = event_data.get('title', '')
        self.description = event_data.get('description', '')
        self.date = event_data.get('date')
        self.class_id = event_data.get('class_id', '')
        self.user_id = event_data.get('user_id', '')
        self.created_at = event_data.get('created_at', datetime.utcnow())

        # Get user information
        user_data = db.users.find_one({'_id': ObjectId(self.user_id)})
        if user_data:
            self.user = {
                'id': str(user_data['_id']),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }
        else:
            self.user = None

    def to_dict(self):
        return {
            '_id': self.id,
            'title': self.title,
            'description': self.description,
            'date': self.date,
            'class_id': self.class_id,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'user': self.user
        }

class Homework:
    def __init__(self, homework_data):
        self.id = str(homework_data['_id'])
        self.title = homework_data.get('title', '')
        self.description = homework_data.get('description', '')
        self.due_date = homework_data.get('due_date')
        self.class_id = homework_data.get('class_id', '')
        self.creator_id = homework_data.get('creator_id', '')
        self.created_at = homework_data.get('created_at', datetime.utcnow())
        self.attachment = homework_data.get('attachment', None)

        # Get creator information
        creator_data = db.users.find_one({'_id': ObjectId(self.creator_id)})
        if creator_data:
            self.creator = {
                'id': str(creator_data['_id']),
                'first_name': creator_data.get('first_name', ''),
                'last_name': creator_data.get('last_name', '')
            }
        else:
            self.creator = None

        # Get class information
        class_data = db.classes.find_one({'class_id': self.class_id})
        if class_data:
            self.class_name = class_data.get('name', '')
        else:
            self.class_name = ''

    def to_dict(self):
        return {
            '_id': self.id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'class_id': self.class_id,
            'creator_id': self.creator_id,
            'created_at': self.created_at,
            'attachment': self.attachment,
            'creator': self.creator,
            'class_name': self.class_name
        }

class Folder:
    def __init__(self, folder_data):
        self.id = str(folder_data['_id'])
        self.name = folder_data.get('name', '')
        self.color = folder_data.get('color', '#FCB447')
        self.class_id = folder_data.get('class_id', '')
        self.creator_id = folder_data.get('creator_id', '')
        self.created_at = folder_data.get('created_at', datetime.utcnow())
        self.file_count = folder_data.get('file_count', 0)

        # Get creator information
        creator_data = db.users.find_one({'_id': ObjectId(self.creator_id)})
        if creator_data:
            self.creator = {
                'id': str(creator_data['_id']),
                'first_name': creator_data.get('first_name', ''),
                'last_name': creator_data.get('last_name', '')
            }
        else:
            self.creator = None

    def to_dict(self):
        return {
            '_id': self.id,
            'name': self.name,
            'color': self.color,
            'class_id': self.class_id,
            'creator_id': self.creator_id,
            'created_at': self.created_at,
            'file_count': self.file_count,
            'creator': self.creator
        }