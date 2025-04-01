"""
Views module for the website application.
Contains all the route handlers and view functions.
"""

# Standard library imports
import json
import os
import random
import string
from datetime import datetime

# Third-party imports
import bleach
from bson import ObjectId
from flask import (
    Blueprint, flash, render_template, request, jsonify,
    redirect, url_for, send_from_directory, current_app
)
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Local imports
from .models import Note, Class, File, Activity, Homework, Folder
from . import db

views = Blueprint('views', __name__)

def generate_class_id():
    """Generate a unique 6-character class ID.
    
    Returns:
        str: A unique 6-character class ID.
    """
    while True:
        class_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        existing_class = db.classes.find_one({'class_id': class_id})
        if not existing_class:
            return class_id

def allowed_file(filename):
    """Check if the file extension is allowed.
    
    Args:
        filename (str): The name of the file to check.
        
    Returns:
        bool: True if the file extension is allowed, False otherwise.
    """
    allowed_extensions = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif',
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'
    }
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    """Handle the home page route.
    
    Returns:
        str: Rendered home page template.
    """
    # Get personal notes
    personal_notes_list = list(db.notes.find({'user_id': current_user.id}).sort('created_at', -1))
    
    # Get classes where user is creator or member
    created_classes = list(db.classes.find({'creator_id': current_user.id}).sort('created_at', -1))
    created_classes = [Class(class_data) for class_data in created_classes]
    
    joined_classes = list(db.classes.find({'members': current_user.id}).sort('created_at', -1))
    joined_classes = [Class(class_data) for class_data in joined_classes]
    
    # Get recent activities from all classes the user is in
    class_ids = [c.class_id for c in created_classes + joined_classes]
    recent_activities = []
    if class_ids:
        activities = list(db.activities.find(
            {'class_id': {'$in': class_ids}}
        ).sort('created_at', -1).limit(10))
        recent_activities = [Activity(activity) for activity in activities]
    
    if request.method == 'POST':
        note_text = request.form.get('note')
        if not note_text:
            flash('Note cannot be empty!', category='error')
        else:
            try:
                # Create note document
                note_data = {
                    'title': 'Quick Note',
                    'content': note_text,
                    'user_id': current_user.id,
                    'class_id': None,
                    'is_public': True,
                    'created_at': datetime.utcnow(),
                    'date': datetime.utcnow()
                }
                
                # Insert into MongoDB
                db.notes.insert_one(note_data)
                flash('Note added successfully!', category='success')
                return redirect(url_for('views.personal_notes'))
            except Exception as e:
                flash(f'An error occurred while adding the note: {str(e)}', category='error')

    return render_template(
        "home.html",
        user=current_user,
        personal_notes=personal_notes_list,
        created_classes=created_classes,
        joined_classes=joined_classes,
        recent_activities=recent_activities
    )

@views.route('/delete-note/<note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    """Delete a note.
    
    Args:
        note_id (str): The ID of the note to delete.
        
    Returns:
        Response: Redirect to the appropriate page.
    """
    try:
        note = db.notes.find_one({'_id': ObjectId(note_id)})
        if not note:
            flash('Note not found!', category='error')
            return redirect(url_for('views.personal_notes'))
        
        if note['user_id'] != current_user.id:
            flash('You do not have permission to delete this note!', category='error')
            return redirect(url_for('views.personal_notes'))
        
        db.notes.delete_one({'_id': ObjectId(note_id)})
        flash('Note deleted successfully!', category='success')
        
    except Exception as e:
        flash(f'An error occurred while deleting the note: {str(e)}', category='error')
    
    return redirect(url_for('views.personal_notes'))

@views.route('/classes')
@login_required
def classes():
    """Handle the classes page route.
    
    Returns:
        str: Rendered classes page template.
    """
    # Get page number from query parameters, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 8  # Number of classes per page
    
    user_id = str(current_user.id)
    print(f"Fetching classes for user ID: {user_id}")
    
    # Query for all classes where user is creator or member
    classes_query = {
        '$or': [
            {'creator_id': user_id},
            {'members': user_id}
        ]
    }
    
    # Get total count for pagination
    total_classes = db.classes.count_documents(classes_query)
    
    # Calculate total pages
    total_pages = (total_classes + per_page - 1) // per_page
    
    # Get paginated classes
    classes_cursor = (
        db.classes.find(classes_query)
        .sort('created_at', -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    
    # Convert to Class objects and determine if user created or joined each class
    all_classes = []
    for class_data in classes_cursor:
        class_obj = Class(class_data)
        class_obj.is_creator = class_data['creator_id'] == user_id
        all_classes.append(class_obj)
    
    return render_template(
        "classes.html",
        user=current_user,
        all_classes=all_classes,
        page=page,
        total_pages=total_pages
    )

@views.route('/class/<class_id>')
@login_required
def class_view(class_id):
    """Handle the class view page route.
    
    Args:
        class_id (str): The ID of the class to view.
        
    Returns:
        str: Rendered class view template.
    """
    try:
        print("\n=== CLASS VIEW LOG ===")
        print(f"Accessing class: {class_id}")
        
        # Get class data
        class_data = db.classes.find_one({'class_id': class_id})
        if not class_data:
            print("Class not found")
            flash('Class not found!', category='error')
            return redirect(url_for('views.home'))
            
        # Convert IDs to strings for comparison
        user_id = str(current_user.id)
        creator_id = str(class_data['creator_id'])
        members = [str(m) for m in class_data.get('members', [])]
        
        is_creator = user_id == creator_id
        is_member = user_id in members
        
        print(f"Access check - User: {user_id}, Creator: {creator_id}, Members: {members}")
        print(f"Is Creator: {is_creator}, Is Member: {is_member}")
        
        if not is_creator and not is_member:
            print("Access denied")
            flash('You do not have access to this class!', category='error')
            return redirect(url_for('views.home'))
            
        # Get class content
        notes = list(db.notes.find({'class_id': class_id}).sort('created_at', -1))
        files = list(db.files.find({'class_id': class_id}).sort('uploaded_at', -1))
        announcements = list(db.announcements.find({'class_id': class_id}).sort('created_at', -1))
        events = list(db.events.find({'class_id': class_id}).sort('date', 1))
        homework = list(db.homework.find({'class_id': class_id}).sort('due_date', 1))
        folders = list(db.folders.find({'class_id': class_id}).sort('created_at', -1))
        
        # Prepare events for FullCalendar
        events_json = [
            {
                'title': event['title'],
                'start': event['date'].isoformat(),
                'description': event.get('description', ''),
                'id': str(event['_id'])
            }
            for event in events
        ]
        
        print(f"Found: {len(notes)} notes, {len(files)} files, "
              f"{len(announcements)} announcements, {len(events)} events, {len(folders)} folders")
        
        class_obj = Class(class_data)
        notes = [Note(note) for note in notes]
        files = [File(file_data) for file_data in files]
        homework = [Homework(hw_data) for hw_data in homework]
        folders = [Folder(folder_data) for folder_data in folders]
        
        print("Rendering template")
        return render_template(
            "class_view.html",
            class_obj=class_obj,
            notes=notes,
            files=files,
            announcements=announcements,
            events=events,
            events_json=json.dumps(events_json),
            homework=homework,
            folders=folders,
            user=current_user,
            is_creator=is_creator,
            is_member=is_member,
            now=datetime.utcnow()
        )
        
    except Exception as e:
        print("\nERROR IN CLASS VIEW")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'An error occurred: {str(e)}', category='error')
        return redirect(url_for('views.home'))

def generate_unique_class_id():
    """Generate a unique 6-character class ID"""
    while True:
        # Generate a random 6-character string using uppercase letters and numbers
        class_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # Check if this ID already exists
        existing_class = db.classes.find_one({'class_id': class_id})
        if not existing_class:
            return class_id

@views.route('/create-class', methods=['GET', 'POST'])
@login_required
def create_class():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        password = request.form.get('password')
        
        print(f"Creating class with name: {name}, description: {description}")  # Debug log
        print(f"Current user ID: {current_user.id}")  # Debug log
        print(f"Current user ID type: {type(current_user.id)}")  # Debug log
        
        if not name:
            flash('Class name is required!', category='error')
        elif len(password) < 4:
            flash('Password must be at least 4 characters long!', category='error')
        else:
            # Generate a unique class ID
            class_id = generate_unique_class_id()
            print(f"Generated unique class ID: {class_id}")  # Debug log
            
            # Create class document
            class_data = {
                'class_id': class_id,
                'name': name,
                'description': description,
                'password': generate_password_hash(password, method='pbkdf2:sha256'),
                'creator_id': str(current_user.id),  # Ensure creator_id is stored as string
                'created_at': datetime.utcnow(),
                'members': [],  # Initialize empty members list
                'color': request.form.get('color', '#4CAF50')  # Default to green if no color selected
            }
            
            try:
                print(f"Inserting class data: {class_data}")  # Debug log
                # Insert into MongoDB
                result = db.classes.insert_one(class_data)
                class_data['_id'] = result.inserted_id
                new_class = Class(class_data)
                print(f"Class created successfully with ID: {result.inserted_id}")  # Debug log
                
                # Verify the class was created
                created_class = db.classes.find_one({'_id': result.inserted_id})
                print(f"Verified created class: {created_class}")  # Debug log
                
                flash('Class created successfully!', category='success')
                return redirect(url_for('views.home'))
            except Exception as e:
                print(f"Error creating class: {str(e)}")  # Debug log
                flash(f'An error occurred while creating the class: {str(e)}', category='error')
    
    return render_template("create_class.html", user=current_user)

@views.route('/join-class', methods=['GET', 'POST'])
@login_required
def join_class():
    if request.method == 'POST':
        class_id = request.form.get('class_id')
        password = request.form.get('password')
        
        print(f"Attempting to join class {class_id}")  # Debug log
        print(f"Current user ID: {current_user.id}")  # Debug log
        
        if not class_id or not password:
            flash('Class ID and password are required!', category='error')
        else:
            # Find the class by class_id
            class_data = db.classes.find_one({'class_id': class_id})
            if not class_data:
                flash('Class not found!', category='error')
            else:
                class_obj = Class(class_data)
                user_id = str(current_user.id)
                print(f"Class members: {class_obj.members}")  # Debug log
                print(f"Class creator: {class_obj.creator_id}")  # Debug log
                
                # Check if user is already a member
                if user_id in [str(m) for m in class_obj.members]:
                    flash('You are already a member of this class!', category='error')
                # Check if user is the creator
                elif user_id == str(class_obj.creator_id):
                    flash('You cannot join your own class!', category='error')
                # Verify password
                elif not check_password_hash(class_obj.password, password):
                    flash('Invalid password!', category='error')
                else:
                    try:
                        # Add user to members list
                        print(f"Adding user {user_id} to class members")  # Debug log
                        db.classes.update_one(
                            {'_id': ObjectId(class_obj._id)},
                            {'$addToSet': {'members': user_id}}  # Use addToSet to prevent duplicates
                        )
                        
                        # Create activity record
                        activity_data = {
                            'user_id': current_user.id,
                            'class_id': class_id,
                            'action': 'joined the class',
                            'details': f'Joined {class_obj.name}',
                            'created_at': datetime.utcnow()
                        }
                        db.activities.insert_one(activity_data)
                        
                        flash('Successfully joined the class!', category='success')
                        return redirect(url_for('views.class_view', class_id=class_id))
                    except Exception as e:
                        print(f"Error joining class: {str(e)}")  # Debug log
                        flash(f'An error occurred while joining the class: {str(e)}', category='error')
    
    return render_template("join_class.html", user=current_user)

@views.route('/add-note', methods=['POST'])
@login_required
def add_note():
    """Add a new note.
    
    Returns:
        Response: JSON response indicating success or failure.
    """
    try:
        print("\n=== ADD NOTE LOG ===")
        
        note_text = request.form.get('note')
        class_id = request.form.get('class_id')
        user_id = str(current_user.id)
        
        print(f"Adding note - Class: {class_id}, User: {user_id}")
        print(f"Note content length: {len(note_text) if note_text else 0}")
        
        if not note_text or not note_text.strip():
            print("Note is empty")
            return jsonify({
                'success': False,
                'error': 'Note cannot be empty!'
            }), 400
        
        # Verify class exists and user has access
        if class_id:
            class_data = db.classes.find_one({'class_id': class_id})
            if not class_data:
                print("Class not found")
                return jsonify({
                    'success': False,
                    'error': 'Class not found!'
                }), 404
            
            # Convert IDs to strings for comparison
            creator_id = str(class_data['creator_id'])
            members = [str(m) for m in class_data.get('members', [])]
            
            if user_id != creator_id and user_id not in members:
                print("Access denied")
                return jsonify({
                    'success': False,
                    'error': 'You do not have permission to add notes to this class!'
                }), 403
        
        # Create note document
        note_data = {
            'title': 'Class Note' if class_id else 'Personal Note',
            'content': note_text.strip(),
            'user_id': user_id,
            'class_id': class_id,
            'is_public': bool(class_id),
            'created_at': datetime.utcnow(),
            'date': datetime.utcnow()
        }
        
        # Insert note
        result = db.notes.insert_one(note_data)
        note_id = result.inserted_id
        
        # Create activity record for class note
        if class_id:
            activity_data = {
                'user_id': user_id,
                'class_id': class_id,
                'action': 'added a note',
                'details': f'Added a note in {class_data["name"]}',
                'created_at': datetime.utcnow()
            }
            db.activities.insert_one(activity_data)
        
        return jsonify({
            'success': True,
            'message': 'Note added successfully',
            'note_id': str(note_id)
        })
        
    except Exception as e:
        print("\n=== ADD NOTE ERROR ===")
        print(f"Error adding note: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An error occurred while adding the note: {str(e)}'
        }), 500

@views.route('/upload-file', methods=['POST'])
@login_required
def upload_file():
    """Upload a file.
    
    Returns:
        Response: Redirect to the appropriate page.
    """
    if 'file' not in request.files:
        flash('No file selected!', category='error')
        return redirect(url_for('views.home'))
    
    file = request.files['file']
    class_id = request.form.get('class_id')
    folder_id = request.form.get('folder_id')
    display_name = request.form.get('display_name')
    description = request.form.get('description')
    
    if not file.filename:
        flash('No file selected!', category='error')
    else:
        try:
            # Save file with timestamp to ensure unique name
            filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Create file document
            file_data = {
                'filename': filename,
                'original_filename': file.filename,
                'display_name': display_name or file.filename,
                'description': description,
                'user_id': current_user.id,
                'class_id': class_id,
                'folder_id': folder_id,
                'uploaded_at': datetime.utcnow()
            }
            
            # Insert file into MongoDB
            db.files.insert_one(file_data)
            
            # Update folder file count if file is in a folder
            if folder_id:
                db.folders.update_one(
                    {'_id': ObjectId(folder_id)},
                    {'$inc': {'file_count': 1}}
                )
            
            # Create activity record for class file
            if class_id:
                class_data = db.classes.find_one({'class_id': class_id})
                class_name = class_data['name'] if class_data else 'Unknown Class'
                
                activity_data = {
                    'user_id': current_user.id,
                    'class_id': class_id,
                    'action': 'uploaded a file',
                    'details': f'Uploaded {display_name or file.filename} in {class_name}',
                    'created_at': datetime.utcnow()
                }
                db.activities.insert_one(activity_data)
            
            flash('File uploaded successfully!', category='success')
        except Exception as e:
            flash(f'An error occurred while uploading the file: {str(e)}', category='error')
    
    if class_id:
        return redirect(url_for('views.class_view', class_id=class_id))
    return redirect(url_for('views.home'))

@views.route('/download-file/<file_id>')
@login_required
def download_file(file_id):
    try:
        file_data = db.files.find_one({'_id': ObjectId(file_id)})
        if file_data:
            return send_from_directory(
                current_app.config['UPLOAD_FOLDER'],
                file_data['filename'],
                as_attachment=True,
                download_name=file_data['original_filename']
            )
        flash('File not found!', category='error')
    except Exception as e:
        flash(f'An error occurred while downloading the file: {str(e)}', category='error')
    
    if file_data and file_data.get('class_id'):
        return redirect(url_for('views.class_view', class_id=file_data['class_id']))
    return redirect(url_for('views.home'))

@views.route('/delete-file/<file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    try:
        file_data = db.files.find_one({'_id': ObjectId(file_id)})
        if file_data and file_data['user_id'] == current_user.id:
            # Delete file from filesystem
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_data['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete from database
            db.files.delete_one({'_id': ObjectId(file_id)})
            flash('File deleted successfully!', category='success')
        else:
            flash('You can only delete your own files!', category='error')
    except Exception as e:
        flash(f'An error occurred while deleting the file: {str(e)}', category='error')
    
    if file_data and file_data.get('class_id'):
        return redirect(url_for('views.class_view', class_id=file_data['class_id']))
    return redirect(url_for('views.home'))

@views.route('/edit-class/<class_id>', methods=['GET', 'POST'])
@login_required
def edit_class(class_id):
    try:
        # Get class data
        class_data = db.classes.find_one({'class_id': class_id})
        if not class_data:
            flash('Class not found!', category='error')
            return redirect(url_for('views.home'))
        
        class_obj = Class(class_data)
        
        # Check if user is the creator
        if str(current_user.id) != class_obj.creator_id:
            flash('You can only edit classes you created!', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
        
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            color = request.form.get('color')
            
            if not name:
                flash('Class name is required!', category='error')
            else:
                # Update class document
                update_data = {
                    'name': name,
                    'description': description,
                    'color': color
                }
                
                db.classes.update_one(
                    {'_id': ObjectId(class_obj._id)},
                    {'$set': update_data}
                )
                flash('Class updated successfully!', category='success')
                return redirect(url_for('views.class_view', class_id=class_id))
        
        return render_template("edit_class.html", class_obj=class_obj, user=current_user)
    except Exception as e:
        flash(f'An error occurred: {str(e)}', category='error')
        return redirect(url_for('views.home'))

@views.route('/edit-note/<note_id>', methods=['POST'])
@login_required
def edit_note(note_id):
    try:
        print(f"Attempting to edit note {note_id}")
        note = db.notes.find_one({'_id': ObjectId(note_id)})
        if not note:
            print(f"Note {note_id} not found")
            return jsonify({'error': 'Note not found!'}), 404
        
        if note['user_id'] != current_user.id:
            print(f"Permission denied for user {current_user.id} to edit note {note_id}")
            return jsonify({'error': 'You do not have permission to edit this note!'}), 403
        
        data = request.get_json() if request.is_json else request.form
        title = data.get('title')
        content = data.get('content')
        
        print(f"Received edit data - Title: {title}, Content length: {len(content) if content else 0}")

        if not title or not content:
            print("Missing title or content in edit request")
            return jsonify({'error': 'Title and content are required!'}), 400

        # Sanitize HTML content
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                       'blockquote', 'pre', 'code', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img', 'a']
        allowed_attrs = {
            '*': ['class', 'style'],
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'title', 'width', 'height']
        }
        
        clean_content = bleach.clean(
            content, 
            tags=allowed_tags, 
            attributes=allowed_attrs,
            strip=True
        )
        
        update_data = {
            'title': title,
            'content': clean_content,
            'updated_at': datetime.utcnow()
        }
        print(f"Updating note {note_id} with data: {update_data}")
        
        result = db.notes.update_one(
            {'_id': ObjectId(note_id)},
            {'$set': update_data}
        )
        
        print(f"Update result: {result.modified_count} document(s) modified")
        
        return jsonify({
            'success': True,
            'message': 'Note updated successfully'
        })
            
    except Exception as e:
        print(f"Error editing note: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update note: {str(e)}'}), 500

@views.route('/personal-notes')
@login_required
def personal_notes():
    try:
        # Get only personal notes (where class_id is None) for the current user
        notes_data = db.notes.find({
            'user_id': current_user.id,
            'class_id': None  # Only get notes that are not associated with any class
        }).sort('created_at', -1)
        personal_notes = [Note(note) for note in notes_data]
        return render_template('personal_notes.html', personal_notes=personal_notes)
    except Exception as e:
        print(f"Error fetching personal notes: {str(e)}")
        flash('Error fetching notes', 'error')
        return redirect(url_for('views.home'))

@views.route('/api/personal-notes', methods=['GET'])
@login_required
def get_personal_notes():
    try:
        notes_data = db.notes.find({'user_id': current_user.id})
        notes = [Note(note).to_dict() for note in notes_data]
        return jsonify(notes)
    except Exception as e:
        print(f"Error fetching personal notes: {str(e)}")
        return jsonify({'error': 'Failed to fetch notes'}), 500

@views.route('/get-note/<note_id>')
@login_required
def get_note(note_id):
    try:
        note = db.notes.find_one({'_id': ObjectId(note_id)})
        if note and note['user_id'] == current_user.id:
            return jsonify({
                'id': str(note['_id']),
                'title': note['title'],
                'content': note['content'],
                'date': note['date'].isoformat()
            })
        return jsonify({'error': 'Note not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@views.route('/create-personal-note', methods=['POST'])
@login_required
def create_personal_note():
    try:
        data = request.get_json() if request.is_json else request.form
        title = data.get('title')
        content = data.get('content')

        print(f"Received note data - Title: {title}, Content length: {len(content) if content else 0}")

        if not title or not content:
            print("Missing title or content")
            return jsonify({'error': 'Title and content are required!'}), 400

        # Sanitize HTML content
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                       'blockquote', 'pre', 'code', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img', 'a']
        allowed_attrs = {
            '*': ['class', 'style'],
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'title', 'width', 'height']
        }
        
        clean_content = bleach.clean(
            content, 
            tags=allowed_tags, 
            attributes=allowed_attrs,
            strip=True
        )

        note_data = {
            'title': title,
            'content': clean_content,
            'user_id': current_user.id,
            'date': datetime.utcnow(),
            'created_at': datetime.utcnow(),
            'is_public': False,
            'class_id': None
        }
        
        print(f"Inserting note with data: {note_data}")
        result = db.notes.insert_one(note_data)
        print(f"Note inserted successfully with ID: {result.inserted_id}")
        
        return jsonify({
            'success': True,
            'id': str(result.inserted_id),
            'message': 'Note created successfully'
        })
            
    except Exception as e:
        print(f"Error creating note: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create note: {str(e)}'}), 500

@views.route('/delete-class/<class_id>', methods=['POST'])
@login_required
def delete_class(class_id):
    try:
        # Get class data
        class_data = db.classes.find_one({'class_id': class_id})
        if not class_data:
            flash('Class not found!', category='error')
            return redirect(url_for('views.home'))
        
        class_obj = Class(class_data)
        
        # Check if user is the creator
        if str(current_user.id) != class_obj.creator_id:
            flash('You can only delete classes you created!', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
        
        # Verify class name confirmation
        confirm_name = request.form.get('confirm_name')
        if confirm_name != class_obj.name:
            flash('Class name confirmation does not match!', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
        
        # Delete all notes associated with this class
        db.notes.delete_many({'class_id': class_id})
        
        # Delete all files associated with this class
        files = db.files.find({'class_id': class_id})
        for file in files:
            # Delete file from filesystem
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Delete all files from database
        db.files.delete_many({'class_id': class_id})
        
        # Delete all activities associated with this class
        db.activities.delete_many({'class_id': class_id})
        
        # Finally, delete the class itself
        db.classes.delete_one({'_id': ObjectId(class_obj._id)})
        
        flash('Class deleted successfully!', category='success')
        return redirect(url_for('views.home'))
        
    except Exception as e:
        flash(f'An error occurred while deleting the class: {str(e)}', category='error')
        return redirect(url_for('views.class_view', class_id=class_id))

@views.route('/leave-class/<class_id>', methods=['POST'])
@login_required
def leave_class(class_id):
    try:
        # Get class data
        class_data = db.classes.find_one({'class_id': class_id})
        if not class_data:
            flash('Class not found!', category='error')
            return redirect(url_for('views.home'))
        
        class_obj = Class(class_data)
        
        # Check if user is a member
        user_id = str(current_user.id)
        if user_id == class_obj.creator_id:
            flash('Class creator cannot leave their own class!', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
        
        if user_id not in class_obj.members:
            flash('You are not a member of this class!', category='error')
            return redirect(url_for('views.home'))
        
        # Remove user from members list
        db.classes.update_one(
            {'_id': ObjectId(class_obj._id)},
            {'$pull': {'members': user_id}}
        )
        
        # Create activity record
        activity_data = {
            'user_id': current_user.id,
            'class_id': class_id,
            'action': 'left the class',
            'details': f'Left {class_obj.name}',
            'created_at': datetime.utcnow()
        }
        db.activities.insert_one(activity_data)
        
        flash('You have successfully left the class.', category='success')
        return redirect(url_for('views.home'))
        
    except Exception as e:
        flash(f'An error occurred while leaving the class: {str(e)}', category='error')
        return redirect(url_for('views.class_view', class_id=class_id))

@views.route('/add-announcement', methods=['POST'])
@login_required
def add_announcement():
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        class_id = request.form.get('class_id')
        
        if not title or not content or not class_id:
            flash('Please fill in all fields', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
            
        # Check if user is class creator
        class_data = db.classes.find_one({'class_id': class_id})
        if not class_data or str(class_data['creator_id']) != str(current_user.id):
            flash('You do not have permission to post announcements', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
            
        announcement = {
            'title': title,
            'content': content,
            'class_id': class_id,
            'user_id': current_user.id,
            'created_at': datetime.utcnow()
        }
        
        db.announcements.insert_one(announcement)
        flash('Announcement posted successfully', category='success')
        
    except Exception as e:
        flash(f'Error posting announcement: {str(e)}', category='error')
        
    return redirect(url_for('views.class_view', class_id=class_id))

@views.route('/delete-announcement/<announcement_id>', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    try:
        announcement = db.announcements.find_one({'_id': ObjectId(announcement_id)})
        if not announcement:
            flash('Announcement not found', category='error')
            return redirect(url_for('views.home'))
            
        class_id = announcement['class_id']
        class_data = db.classes.find_one({'class_id': class_id})
        
        if not class_data or str(class_data['creator_id']) != str(current_user.id):
            flash('You do not have permission to delete this announcement', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
            
        db.announcements.delete_one({'_id': ObjectId(announcement_id)})
        flash('Announcement deleted successfully', category='success')
        
    except Exception as e:
        flash(f'Error deleting announcement: {str(e)}', category='error')
        return redirect(url_for('views.home'))
        
    return redirect(url_for('views.class_view', class_id=class_id))

@views.route('/calendar')
@login_required
def calendar():
    """Handle the calendar page route.
    
    Returns:
        str: Rendered calendar page template.
    """
    try:
        print("\n=== CALENDAR VIEW LOG ===")
        user_id = str(current_user.id)
        
        # Get all classes where the user is either a creator or a member
        user_classes = list(db.classes.find({
            '$or': [
                {'creator_id': user_id},
                {'members': user_id}
            ]
        }))
        
        print(f"Found {len(user_classes)} classes for user {user_id}")
        
        # Get all events from these classes
        all_events = []
        for class_obj in user_classes:
            try:
                class_id = class_obj.get('class_id')
                class_name = class_obj.get('name', 'Unknown Class')
                
                if not class_id:
                    print(f"Skipping class without class_id: {class_obj}")
                    continue
                
                print(f"Processing class: {class_name} ({class_id})")
                
                events = list(db.events.find({
                    'class_id': class_id
                }).sort('date', 1))
                
                print(f"Found {len(events)} events in class {class_name}")
                
                for event in events:
                    try:
                        event_date = event.get('date')
                        if not event_date:
                            print(f"Skipping event without date: {event}")
                            continue
                        
                        # Ensure event_date is a datetime object
                        if isinstance(event_date, str):
                            try:
                                event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                            except ValueError:
                                print(f"Invalid date format in event: {event}")
                                continue
                            
                        event_dict = {
                            'id': str(event['_id']),
                            'title': event.get('title', 'Untitled Event'),
                            'start': event_date.isoformat(),
                            'description': event.get('description', ''),
                            'className': class_name,
                            'classId': class_id,
                            'extendedProps': {
                                'className': class_name,
                                'description': event.get('description', ''),
                                'classId': class_id
                            }
                        }
                        all_events.append(event_dict)
                        print(f"Added event: {event_dict['title']} on {event_dict['start']}")
                    except Exception as e:
                        print(f"Error processing event: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Error processing class {class_obj.get('class_id', 'unknown')}: {str(e)}")
                continue
        
        print(f"Total events found: {len(all_events)}")
        events_json = json.dumps(all_events, default=str)
        return render_template('calendar.html', events_json=events_json)
        
    except Exception as e:
        print(f"\nError in calendar view: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Error loading calendar. Please try again later.', category='error')
        return redirect(url_for('views.home'))

@views.route('/add-event', methods=['POST'])
@login_required
def add_event():
    """Add a new event to a class.
    
    Returns:
        Response: Redirect to the appropriate page.
    """
    try:
        print("\n=== ADD EVENT LOG ===")
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('date')
        class_id = request.form.get('class_id')
        
        if not all([title, date_str, class_id]):
            flash('Please fill in all required fields', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
            
        # Check if user is class creator or member
        class_data = db.classes.find_one({'class_id': class_id})
        if not class_data:
            flash('Class not found', category='error')
            return redirect(url_for('views.home'))
            
        user_id = str(current_user.id)
        creator_id = str(class_data['creator_id'])
        members = [str(m) for m in class_data.get('members', [])]
        
        if user_id != creator_id and user_id not in members:
            flash('You do not have permission to add events', category='error')
            return redirect(url_for('views.home'))
            
        # Convert date string to datetime
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
            
        event = {
            'title': title,
            'description': description,
            'date': event_date,
            'class_id': class_id,
            'user_id': user_id,
            'created_at': datetime.utcnow()
        }
        
        db.events.insert_one(event)
        
        # Create activity record
        activity_data = {
            'user_id': user_id,
            'class_id': class_id,
            'action': 'added an event',
            'details': f'Added event: {title}',
            'created_at': datetime.utcnow()
        }
        db.activities.insert_one(activity_data)
        
        flash('Event added successfully', category='success')
        
    except Exception as e:
        print(f"Error adding event: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error adding event: {str(e)}', category='error')
        return redirect(url_for('views.home'))
        
    return redirect(url_for('views.class_view', class_id=class_id))

@views.route('/delete-event/<event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    """Delete an event.
    
    Args:
        event_id (str): The ID of the event to delete.
        
    Returns:
        Response: Redirect to the appropriate page.
    """
    try:
        event = db.events.find_one({'_id': ObjectId(event_id)})
        if not event:
            flash('Event not found', category='error')
            return redirect(url_for('views.home'))
            
        class_id = event['class_id']
        class_data = db.classes.find_one({'class_id': class_id})
        
        if not class_data or str(class_data['creator_id']) != str(current_user.id):
            flash('You do not have permission to delete this event', category='error')
            return redirect(url_for('views.class_view', class_id=class_id))
            
        db.events.delete_one({'_id': ObjectId(event_id)})
        flash('Event deleted successfully', category='success')
        
    except Exception as e:
        flash(f'Error deleting event: {str(e)}', category='error')
        return redirect(url_for('views.home'))
        
    return redirect(url_for('views.class_view', class_id=class_id))

@views.route('/add-homework/<class_id>', methods=['POST'])
@login_required
def add_homework(class_id):
    """Add a new homework assignment to a class."""
    try:
        # Get class data
        class_data = db.classes.find_one({'class_id': class_id})
        if not class_data:
            return jsonify({'success': False, 'error': 'Class not found!'})

        # Check if user is the creator
        if str(current_user.id) != str(class_data['creator_id']):
            return jsonify({'success': False, 'error': 'Only class creator can add homework!'})

        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = request.form.get('due_date')
        
        if not all([title, description, due_date]):
            return jsonify({'success': False, 'error': 'All fields are required!'})

        # Convert due_date string to datetime
        due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')

        # Handle file attachment if present
        attachment = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                # Save file with timestamp to ensure unique name
                filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                attachment = filename

        # Create homework document
        homework_data = {
            'title': title,
            'description': description,
            'due_date': due_date,
            'class_id': class_id,
            'creator_id': str(current_user.id),
            'created_at': datetime.utcnow(),
            'attachment': attachment
        }

        # Insert into MongoDB
        result = db.homework.insert_one(homework_data)
        homework_id = str(result.inserted_id)

        # Create activity record
        activity_data = {
            'type': 'homework',
            'user_id': current_user.id,
            'class_id': class_id,
            'action': 'added homework',
            'details': f'Added homework: {title}',
            'created_at': datetime.utcnow(),
            'homework_id': homework_id,
            'title': title,
            'due_date': due_date,
            'class_name': class_data['name']
        }
        db.activities.insert_one(activity_data)

        return jsonify({
            'success': True,
            'message': 'Homework added successfully!',
            'homework': {
                'id': homework_id,
                'title': title,
                'description': description,
                'due_date': due_date.strftime('%Y-%m-%d %H:%M'),
                'attachment': attachment
            }
        })

    except Exception as e:
        print(f"Error adding homework: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@views.route('/delete-homework/<homework_id>', methods=['POST'])
@login_required
def delete_homework(homework_id):
    """Delete a homework assignment."""
    try:
        print("\n=== DELETE HOMEWORK LOG ===")
        print(f"Request method: {request.method}")
        print(f"Request path: {request.path}")
        print(f"Request form data: {request.form}")
        print(f"Attempting to delete homework with ID: {homework_id}")
        print(f"Current user ID: {current_user.id}")
        
        # Get homework data
        homework = db.homework.find_one({'_id': ObjectId(homework_id)})
        if not homework:
            print(f"Homework not found with ID: {homework_id}")
            flash('Homework not found!', category='error')
            return redirect(url_for('views.home'))

        print(f"Found homework: {homework}")
        print(f"Homework creator ID: {homework['creator_id']}")
        print(f"Current user ID type: {type(current_user.id)}")
        print(f"Creator ID type: {type(homework['creator_id'])}")

        # Check if user is the creator
        if str(current_user.id) != str(homework['creator_id']):
            print("Permission denied - user is not the creator")
            flash('You can only delete your own homework assignments!', category='error')
            return redirect(url_for('views.class_view', class_id=homework['class_id']))

        # Delete attachment file if exists
        if homework.get('attachment'):
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], homework['attachment'])
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete from database
        result = db.homework.delete_one({'_id': ObjectId(homework_id)})
        print(f"Delete result: {result.deleted_count} documents deleted")

        # Create activity record
        activity_data = {
            'type': 'homework',
            'user_id': current_user.id,
            'class_id': homework['class_id'],
            'action': 'deleted homework',
            'details': f'Deleted homework: {homework["title"]}',
            'created_at': datetime.utcnow()
        }
        db.activities.insert_one(activity_data)

        flash('Homework deleted successfully!', category='success')

    except Exception as e:
        print(f"Error deleting homework: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error deleting homework: {str(e)}', category='error')

    return redirect(url_for('views.class_view', class_id=homework['class_id']))

@views.route('/add-folder', methods=['POST'])
@login_required
def add_folder():
    """Add a new folder to a class."""
    try:
        # Get form data
        name = request.form.get('name')
        color = request.form.get('color')
        class_id = request.form.get('class_id')
        
        if not all([name, color, class_id]):
            return jsonify({'success': False, 'error': 'All fields are required!'})

        # Get class data
        class_data = db.classes.find_one({'class_id': class_id})
        if not class_data:
            return jsonify({'success': False, 'error': 'Class not found!'})

        # Check if user is the creator
        if str(current_user.id) != str(class_data['creator_id']):
            return jsonify({'success': False, 'error': 'Only class creator can add folders!'})

        # Create folder document
        folder_data = {
            'name': name,
            'color': color,
            'class_id': class_id,
            'creator_id': str(current_user.id),
            'created_at': datetime.utcnow(),
            'file_count': 0
        }

        # Insert into MongoDB
        result = db.folders.insert_one(folder_data)
        folder_id = str(result.inserted_id)

        # Create activity record
        activity_data = {
            'type': 'folder',
            'user_id': current_user.id,
            'class_id': class_id,
            'action': 'added folder',
            'details': f'Added folder: {name}',
            'created_at': datetime.utcnow(),
            'folder_id': folder_id,
            'class_name': class_data['name']
        }
        db.activities.insert_one(activity_data)

        return jsonify({
            'success': True,
            'message': 'Folder added successfully!',
            'folder': {
                'id': folder_id,
                'name': name,
                'color': color
            }
        })

    except Exception as e:
        print(f"Error adding folder: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@views.route('/get-folder-files/<folder_id>')
@login_required
def get_folder_files(folder_id):
    """Get all files in a folder."""
    try:
        # Get folder data
        folder = db.folders.find_one({'_id': ObjectId(folder_id)})
        if not folder:
            return jsonify({'success': False, 'error': 'Folder not found!'})

        # Get files in the folder
        files = list(db.files.find({'folder_id': folder_id}).sort('uploaded_at', -1))
        
        # Convert files to File objects and then to dictionaries
        files = [File(file_data).to_dict() for file_data in files]

        return jsonify({
            'success': True,
            'folder': {
                'id': str(folder['_id']),
                'name': folder['name'],
                'color': folder['color']
            },
            'files': files
        })

    except Exception as e:
        print(f"Error getting folder files: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@views.route('/edit-file/<file_id>', methods=['POST'])
@login_required
def edit_file(file_id):
    """Edit file details (display name and description)."""
    try:
        # Get file data
        file_data = db.files.find_one({'_id': ObjectId(file_id)})
        if not file_data:
            return jsonify({'success': False, 'error': 'File not found!'})

        # Check if user is the creator
        if str(current_user.id) != str(file_data['user_id']):
            return jsonify({'success': False, 'error': 'You can only edit your own files!'})

        # Get form data
        display_name = request.form.get('display_name')
        description = request.form.get('description')

        if not display_name:
            return jsonify({'success': False, 'error': 'Display name is required!'})

        # Update file document
        update_data = {
            'display_name': display_name,
            'description': description,
            'updated_at': datetime.utcnow()
        }

        db.files.update_one(
            {'_id': ObjectId(file_id)},
            {'$set': update_data}
        )

        # Create activity record
        class_id = file_data.get('class_id')
        if class_id:
            class_data = db.classes.find_one({'class_id': class_id})
            if class_data:
                activity_data = {
                    'user_id': current_user.id,
                    'class_id': class_id,
                    'action': 'edited file',
                    'details': f'Edited file: {display_name}',
                    'created_at': datetime.utcnow()
                }
                db.activities.insert_one(activity_data)

        return jsonify({
            'success': True,
            'message': 'File updated successfully!',
            'file': {
                'id': file_id,
                'display_name': display_name,
                'description': description
            }
        })

    except Exception as e:
        print(f"Error editing file: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

