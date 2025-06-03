import os
import logging
import random
from flask import Flask, request, redirect, send_from_directory, url_for, render_template, session, jsonify
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS
from psycopg2 import sql
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
from functools import wraps
import jwt
import datetime


load_dotenv()


app = Flask(__name__)
CORS()
app.secret_key = os.getenv('z4SmkdMLHM8BBeSCrCEqmtgZbDXZkqeI', 'i9Tm-OuklqOH6S4dL5TAOfFUL8eZEBGw')
app.config['UPLOAD_FOLDER'] = 'C:/Users/banshika/OneDrive/Desktop/cam/ball game/.vscode/my-website'


memes = []

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# PostgreSQL connection parameters
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 'gum_chat'),
    user=os.getenv('DB_USER', 'banshika'),
    password=os.getenv('DB_PASSWORD', 'banshika'),
    host=os.getenv('DB_HOST', 'banshika'),
    port=os.getenv('DB_PORT', '5432')
)

# User signup route
@app.route('/signup', methods=['POST'])
def signup():
    if 'profile_picture' not in request.files:
        return jsonify({"error": "Profile picture is required."}), 400

    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400

    # Secure the filename and save the file
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    data = request.form 
    username = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"error": "All fields are required."}), 400

    hashed_password = generate_password_hash(password)

    cursor = conn.cursor()
    try:
        # Check if the username or email already exists
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s;", (username, email))
        if cursor.fetchone():
            return jsonify({"error": "Username or email already exists."}), 409

        # Insert the new user
        cursor.execute(
            "INSERT INTO users (username, email, password, profile_picture) VALUES (%s, %s, %s, %s) RETURNING id;",
            (username, email, hashed_password, file_path)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        logging.info(f"User  {username} registered successfully.")

        # Redirect to login page after successful signup
        return jsonify({"message": "User  registered successfully!", "redirect": url_for('login')}), 201
    except Exception as e:
        conn.rollback()
        logging.error(f"An error occurred during signup: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = data['password']

    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users WHERE username = %s;", (username,))
    user = cursor.fetchone()
    cursor.close()

    if user and check_password_hash(user[1], password):
        token = jwt.encode({
            'user_id': user[0],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expiration
        }, app.secret_key, algorithm='HS256')
        return jsonify({'token': token}), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']

        if not token:
            return jsonify({'error': 'Unauthorized access'}), 401

        try:
            data = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            current_user_id = data['user_id']
        except Exception as e:
            return jsonify({'error': 'Unauthorized access'}), 401

        return f(current_user_id, *args, **kwargs)
    return decorated_function

  # Render the chat page

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized access"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/chat', methods=['GET'],endpoint='chat_page')
def chat_page():
    return render_template('chat.html')

@app.route('/check_login', methods=['GET'])
def check_login():
    if 'user_id' in session:
        return jsonify({"message": "User  is logged in", "user_id": session['user_id']}), 200
    else:
        return jsonify({"error": "User  is not logged in"}), 401

# Routes for the main application
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/')
def home():
    return render_template('signup.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/getstarted')
def getstarted():
    return render_template('getstarted.html')

@app.route('/inbox')
def inbox():
    return render_template('inbox.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/videos/<path:path>')
def send_videos(path):
    return send_from_directory('templates/videos', path)

@app.route('/AudioTrack')
def AudioTrack():
    return render_template('AudioTrack.html')

@app.route('/memehouse')
def memehouse():
    return render_template('memehouse.html')

@app.route('/videoshort')
def videoshort():
    return render_template('videoshort.html')



@app.route('/images/<path:path>')
def send_images(path):
    return send_from_directory('templates/images', path)

@app.route('/songs/<path:path>')
def send_songs(path):
    return send_from_directory('templates/songs', path)

@app.route('/swipematching', methods=['GET', 'POST'])
def swipematching():
    if request.method == 'POST':
        if 'profile_picture' not in request.files:
            return redirect(request.url)
        
        file = request.files['profile_picture']
        if file.filename == '':
            return redirect(request.url)
        
        # Secure the filename and save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Save the file path in session
        session['profile_picture_url'] = file_path
        
        return redirect(url_for('swipe_matching'))

    # For GET request
    profile_picture_url = session.get('profile_picture_url', None)
    return render_template('swipematching.html', profile_picture_url=profile_picture_url)

@app.route('/moodBoardProfiles')
def moodBoardProfiles():
    return render_template('moodBoardProfiles.html')
    

@app.route('/lovecalculator')
def lovecalculator():
    return render_template('lovecalculator.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/login', methods=['GET'], endpoint='login_page')
def login_page():
    return render_template('login.html')  # Render your login template

@app.route('/memes', methods=['GET'])
def get_memes():
    return jsonify(memes)


@app.route('/like/<int:id>', methods=['POST'])
def like_meme(id):
    meme = next((m for m in memes if m['id'] == id), None)
    if meme:
        meme['likes'] += 1
        return jsonify(meme)
    return jsonify({'error': 'Meme not found'}), 404

@app.route('/comment/<int:id>', methods=['POST'])
def add_comment(id):
    meme = next((m for m in memes if m['id'] == id), None)
    if meme:
        comment = request.json.get('comment')
        if comment:
            meme['comments'].append(comment)
            return jsonify(meme)
        return jsonify({'error': 'Comment is required'}), 400
    return jsonify({'error': 'Meme not found'}), 404


@app.route('/users', methods=['GET'])
@login_required  # Ensure that only logged-in users can access this route
def get_users():
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users;")  # Adjust the query as needed
    users = cursor.fetchall()
    cursor.close()

    # Convert the user data to a list of dictionaries
    user_list = [{'id': user[0], 'username': user[1]} for user in users]
    return jsonify(user_list)  # Return the user list as JSON


@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    logging.info("User  logged out successfully.")
    return redirect(url_for('home'))

# Error handling for bad requests
@app.errorhandler(400)
def handle_bad_request(e):
    return jsonify({"error": "Bad request: " + str(e)}), 400

# Error handling for conflicts
@app.errorhandler(409)
def handle_conflict(e):
    return jsonify({"error": "Conflict: " + str(e)}), 409

# General error handler
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"An error occurred: {str(e)}")
    return jsonify({"error": "An internal error occurred."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
