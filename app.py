import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
import re
import logging

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

user_data_folder = "user_data"

def save_user_data(username, password):  # Remove the email parameter
    user_data = {
        "username": username,
        "password": password  # Remove the email key from the user data dictionary
    }
    filename = f"{username}.json"
    filepath = os.path.join(user_data_folder, filename)
    with open(filepath, "w") as file:
        json.dump(user_data, file)

def check_user_credentials(username, email):
    filename = f"{username}.json"
    filepath = os.path.join(user_data_folder, filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            saved_data = json.load(file)
            return saved_data["email"] == email
    return False

# Get the current directory where the script is located
current_directory = os.path.dirname(os.path.abspath(__file__))

# Define the path to the 'static' folder
static_folder = os.path.join(current_directory, 'static')

logos_folder = os.path.join(static_folder, 'logos')

# Define the path to the 'video_info' folder
video_info_folder = os.path.join(static_folder, 'video_info')

# Define the path to the 'uploads' folder
uploads_folder = os.path.join(current_directory, 'uploads')

# Create necessary folders if they don't exist
for folder in [video_info_folder, uploads_folder, os.path.join(static_folder, 'thumbnails')]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def sanitize_video_id(video_id):
    # Remove special characters
    video_id = re.sub(r'[^\w\s.-]', '', video_id)
    # Normalize font
    video_id = video_id.lower()
    return video_id

def get_logo_path():
    return os.path.join(logos_folder, 'logo.png')

@app.route('/')
def something():
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Authenticate user
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists
        user_filename = f"{username}.json"
        user_filepath = os.path.join(user_data_folder, user_filename)
        if os.path.exists(user_filepath):
            with open(user_filepath, 'r') as file:
                user_data = json.load(file)
                if user_data['password'] == password:
                    session['logged_in'] = True
                    return redirect(url_for('dashboard'))
        
        # If user does not exist or password is incorrect, show error
        return render_template('login.html', error='Invalid credentials')
    else:
        return render_template('login.html')

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]  # Change email to password
        save_user_data(username, password)  # Update the save_user_data function call
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route('/logout', methods=['POST'])
def logout():
    # Clear the session data to log the user out
    session.clear()
    # Redirect the user to the home page (or any other desired page)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'logged_in' in session:
        return render_template('dashboard.html')
    else:
        return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files or 'thumbnail' not in request.files:
        return redirect(request.url)

    video = request.files['video']
    title = request.form['title']
    thumbnail = request.files['thumbnail']

    if video.filename == '' or thumbnail.filename == '':
        return redirect(request.url)

    # Remove hashtags from title
    title = title.replace('#', '')

    if video and thumbnail:
        # Remove spaces from filenames
        video_filename = secure_filename(video.filename)
        thumbnail_filename = secure_filename(thumbnail.filename)

        video_id = video_filename.split('.')[0]  # Extract video ID from filename
        video_id = sanitize_video_id(video_id)   # Sanitize video ID
        video.save(os.path.join(uploads_folder, video_filename))
        
        # Rename thumbnail to match video filename
        thumbnail_extension = os.path.splitext(thumbnail_filename)[1].lower()
        if thumbnail_extension in ['.jpg', '.jpeg', '.png']:
            thumbnail_filename = video_filename.split('.')[0] + thumbnail_extension
            thumbnail.save(os.path.join(static_folder, 'thumbnails', thumbnail_filename))

            # Save video information to a JSON file in 'video_info' folder
            video_info = {'title': title}  # Exclude 'thumbnail' attribute
            with open(os.path.join(video_info_folder, f"{video_id}.json"), 'w') as file:
                json.dump(video_info, file)
        else:
            return "Invalid thumbnail format. Please upload a JPEG, PNG, or JPG file."

    return redirect(url_for('home'))


from flask import render_template, send_from_directory

@app.route('/watch/<video_id>')
def watch(video_id):
    # Serve the requested video file if it exists
    video_path = os.path.join(uploads_folder, f"{video_id}.mp4")
    if os.path.exists(video_path):
        return send_from_directory(uploads_folder, f"{video_id}.mp4")
    
    # Render the template if the video file doesn't exist
    return render_template('watch.html', video_id=video_id, video_title=video_title, videos=videos)

@app.route('/home')
def home():
    videos = {}
    query = request.args.get('query')  # Get the search query from the URL parameters
    try:
        # Read video information from JSON files in 'video_info' folder
        for filename in os.listdir(video_info_folder):
            if filename.endswith('.json'):
                with open(os.path.join(video_info_folder, filename), 'r') as file:
                    try:
                        data = json.load(file)
                        video_id = filename.split('.')[0]  # Extract video ID from filename
                        videos[video_id] = {'title': data['title']}  # Exclude 'thumbnail' attribute
                    except json.JSONDecodeError as e:
                        logging.error("Error decoding JSON while loading video information from file %s: %s", filename, e)
    except FileNotFoundError as e:
        logging.error("File not found while loading video information: %s", e)

    # Filter videos based on search query
    if query:
        filtered_videos = {video_id: info for video_id, info in videos.items() if query.lower() in info['title'].lower()}
        if not filtered_videos:
            return "Nothing found."
        videos = filtered_videos

    logging.debug("Videos: %s", videos)  # Log videos dictionary for debugging
    return render_template('home.html', videos=videos)

@app.route('/search')
def search():
    query = request.args.get('query')  # Get the search query from the URL parameters
    if query:
        # Redirect to the home page with the search query as a parameter
        return redirect(url_for('home', query=query))
    else:
        # If no query is provided, simply redirect to the home page
        return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
