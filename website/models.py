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
            return User(user_data) if user_data else None
        except Exception:
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
            raise

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None
    except Exception:
        return None

class Note:
    def __init__(self, note_data):
        self._id = str(note_data['_id'])
        self.title = note_data.get('title', 'Untitled')
        self.content = note_data.get('content', '')
        self.user_id = note_data.get('user_id')
        self.class_id = note_data.get('class_id')
        self.is_public = note_data.get('is_public', False)
        self.created_at = note_data.get('created_at', datetime.utcnow())
        self.date = note_data.get('date', datetime.utcnow())
        self.updated_at = note_data.get('updated_at')

    def to_dict(self):
        return {
            '_id': self._id,
            'title': self.title,
            'content': self.content,
            'user_id': self.user_id,
            'class_id': self.class_id,
            'is_public': self.is_public,
            'created_at': self.created_at,
            'date': self.date,
            'updated_at': self.updated_at
        }

class File:
    def __init__(self, file_data):
        self._id = str(file_data['_id'])
        self.filename = file_data.get('filename')
        self.original_filename = file_data.get('original_filename')
        self.display_name = file_data.get('display_name')
        self.description = file_data.get('description', '')
        self.user_id = file_data.get('user_id')
        self.class_id = file_data.get('class_id')
        self.folder_id = file_data.get('folder_id')
        self.uploaded_at = file_data.get('uploaded_at', datetime.utcnow())
        self.updated_at = file_data.get('updated_at')

    def to_dict(self):
        return {
            '_id': self._id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'display_name': self.display_name,
            'description': self.description,
            'user_id': self.user_id,
            'class_id': self.class_id,
            'folder_id': self.folder_id,
            'uploaded_at': self.uploaded_at,
            'updated_at': self.updated_at
        }

class Class:
    def __init__(self, class_data):
        self._id = str(class_data['_id'])
        self.class_id = class_data.get('class_id')
        self.name = class_data.get('name', 'Untitled Class')
        self.description = class_data.get('description', '')
        self.password = class_data.get('password')
        self.creator_id = class_data.get('creator_id')
        self.created_at = class_data.get('created_at', datetime.utcnow())
        self.members = class_data.get('members', [])
        self.color = class_data.get('color', '#4CAF50')
        self.is_creator = False
        
        creator_data = db.users.find_one({'_id': ObjectId(self.creator_id)})
        self.creator = {
            'id': str(creator_data['_id']),
            'first_name': creator_data.get('first_name', ''),
            'last_name': creator_data.get('last_name', '')
        } if creator_data else None

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

class Homework:
    def __init__(self, homework_data):
        self._id = str(homework_data['_id'])
        self.title = homework_data.get('title', 'Untitled Homework')
        self.description = homework_data.get('description', '')
        self.due_date = homework_data.get('due_date')
        self.class_id = homework_data.get('class_id')
        self.creator_id = homework_data.get('creator_id')
        self.created_at = homework_data.get('created_at', datetime.utcnow())
        self.attachment = homework_data.get('attachment')

    def to_dict(self):
        return {
            '_id': self._id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'class_id': self.class_id,
            'creator_id': self.creator_id,
            'created_at': self.created_at,
            'attachment': self.attachment
        }

class Folder:
    def __init__(self, folder_data):
        self._id = str(folder_data['_id'])
        self.name = folder_data.get('name', 'Untitled Folder')
        self.description = folder_data.get('description', '')
        self.class_id = folder_data.get('class_id')
        self.user_id = folder_data.get('user_id')
        self.created_at = folder_data.get('created_at', datetime.utcnow())
        self.file_count = folder_data.get('file_count', 0)

    def to_dict(self):
        return {
            '_id': self._id,
            'name': self.name,
            'description': self.description,
            'class_id': self.class_id,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'file_count': self.file_count
        }