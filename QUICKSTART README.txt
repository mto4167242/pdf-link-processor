1. Navigate to Project Directory
cd path/to/your/pdf_processor_app

2. Set Up Virtual Environment
# Create and activate (Windows)
python -m venv venv && venv\Scripts\activate

# Create and activate (macOS/Linux)
python -m venv venv && source venv/bin/activate

3. Install Dependencies
pip install -r requirements.txt
playwright install

4. Run the App
flask --app app.py run

5. Open in Browser
Navigate to: http://127.0.0.1:5000

6. Close App
CTRL+C