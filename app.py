# --- FILE: app.py (DIAGNOSTIC VERSION) ---

from flask import Flask, render_template, request, Response
import os

app = Flask(__name__)
# We don't need other imports for this test
# ... all other imports removed for clarity ...

# Create a dummy temp folder so the app starts
if not os.path.exists('temp_files'): os.makedirs('temp_files')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    # --- THIS IS THE CRITICAL DIAGNOSTIC CODE ---
    print("--- NEW REQUEST RECEIVED ---")
    print(f"Request Method: {request.method}")
    print(f"Request Headers: {request.headers}")
    print(f"Request Content-Type: {request.content_type}")
    print(f"Request Content-Length: {request.content_length}")
    
    # Check the form data (text fields)
    try:
        print(f"Request Form Data (request.form): {request.form.to_dict()}")
    except Exception as e:
        print(f"Error reading request.form: {e}")

    # Check the file data
    try:
        print(f"Request Files Data (request.files): {request.files.to_dict()}")
    except Exception as e:
        print(f"Error reading request.files: {e}")
    
    print("--- END OF REQUEST DUMP ---")
    # --- END OF DIAGNOSTIC CODE ---

    # For this test, we will always return the same error so the frontend reacts predictably.
    def error_stream():
        yield "event: error\ndata: Diagnostic test complete. Check server logs.\n\n"
    
    return Response(error_stream(), mimetype='text/event-stream')

# We need a dummy download route so the app doesn't crash on startup
@app.route('/download/<filename>')
def download_file(filename):
    return "Download route is disabled for this test."