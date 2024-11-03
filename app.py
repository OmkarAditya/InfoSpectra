from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
from firebase_admin import auth, credentials, initialize_app, firestore, storage
import os
from dotenv import load_dotenv
from datetime import datetime

from query import initialize_qa_chain

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
def initialize_firebase():
    """Initialize Firebase with credentials from either file or environment variable"""
    try:
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
            # For Render deployment - use JSON string directly
            cred_info = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            # Handle the credential info as a dictionary
            if isinstance(cred_info, str):
                try:
                    cred_dict = json.loads(cred_info)
                except json.JSONDecodeError:
                    print("Error decoding JSON credential string")
                    return False
            else:
                cred_dict = cred_info
                
            cred = credentials.Certificate(cred_dict)
        else:
            # Local environment - use file path
            cred = credentials.Certificate(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        
        initialize_app(cred, {'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')})
        return True
    except Exception as e:
        print(f"Firebase initialization error: {str(e)}")
        return False

# Initialize Firebase
if not initialize_firebase():
    raise RuntimeError("Failed to initialize Firebase")# Initialize Firestore

    
db = firestore.client()
user_collection = db.collection('users')
query_collection = db.collection('queries')

@app.route('/')
def index():
    return redirect(url_for('query'))  # Redirect to query directly for all users

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    try:
        # Check if the email already exists in Firebase
        user = auth.get_user_by_email(email)
        return jsonify({"status": "error", "message": "Email already registered."}), 400
    except auth.UserNotFoundError:
        try:
            user = auth.create_user(email=email, password=password)
            # On successful registration, set cookie and redirect to query
            resp = make_response(jsonify({"status": "success", "user_id": user.uid}))
            resp.set_cookie('user_id', user.uid, httponly=True)
            # Store new user in Firestore
            user_collection.add({"user_id": user.uid, "frequency": 1, "email": email})
            return resp, 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    try:
        # Check if the user exists
        user = auth.get_user_by_email(email)

        # Set a cookie with the user's ID
        resp = make_response(jsonify({"status": "success", "user_id": user.uid}))
        resp.set_cookie('user_id', user.uid, httponly=True)  # Secure cookie to store user ID
        return resp
    except auth.UserNotFoundError:
        return jsonify({"error": "Invalid email or password."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/query', methods=['GET', 'POST'])
def query():
    user_id = request.cookies.get('user_id')
    
    if not user_id:
        return redirect(url_for('login_page'))  # Redirect to login if no cookie

    if request.method == 'POST':

        # Handle user prompt input
        user_prompt = request.form.get('prompt')
        # Call initialize_qa_chain with the user query to check cache and get answer
        answer = initialize_qa_chain(user_prompt)
        return render_template('query.html', answer=answer)

        # Get the user's collection based on user_id
        user_collection_ref = db.collection(user_id)

        # Check if this is a new collection or an existing one
        user_documents = user_collection_ref.stream()
        frequency = 0
        
        # Calculate frequency of prompts
        for doc in user_documents:
            frequency += 1  # Increment the frequency for each existing document

        # Check if frequency exceeds the limit of n
        n = 10
        if frequency >= n:
            # If frequency is n or more, return an alert via JavaScript
            alert_message = f"<script>alert('You have reached the maximum limit of {n} prompts. You cannot submit more prompts.');</script>"
            return alert_message + render_template('query.html')


        # Otherwise, process the new prompt
        answer = qa_chain({"query": user_prompt})["result"]  # Call your QA chain for the answer

        # Add the new document with prompt, answer, timestamp, and updated frequency
        user_collection_ref.add({
            "prompt": user_prompt,
            "answer": answer,
            "timestamp": datetime.utcnow(),
            "frequency": frequency + 1  # Update frequency
        })

        return render_template('query.html', answer=answer)

    return render_template('query.html')  # Render the query page on GET

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and file.filename.endswith('.pdf'):
            bucket = storage.bucket()
            blob = bucket.blob(f"pdfs/{file.filename}")
            blob.upload_from_file(file, content_type='application/pdf')
            blob.make_public()
            file_url = blob.public_url

            return jsonify({'message': 'File uploaded successfully!', 'file_url': file_url}), 200
        else:
            return jsonify({'error': 'File type not allowed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/logout', methods=['POST'])
def logout():
    resp = make_response(jsonify({"status": "success"}))
    resp.set_cookie('user_id', '', expires=0)  # Clear the cookie
    return resp


if __name__ == "__main__":
    app.run(debug=True)
