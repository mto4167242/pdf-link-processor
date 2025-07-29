\# PDF Link Processor



The PDF Link Processor is a web-based utility designed to analyze PDF documents, validate their hyperlinks, and generate comprehensive reports. It allows users to upload one or more PDFs, check all embedded links against a set of user-defined keywords and HTTP status codes, and download the results as styled Excel reports and modified PDFs.



This tool is built with a Python Flask backend and a modern, responsive HTML/CSS/JavaScript frontend.





---



\## Features



\- \*\*Batch PDF Processing:\*\* Upload and analyze multiple PDF files in a single session.

\- \*\*Intelligent Link Validation:\*\*

&nbsp;   - Checks for HTTP error codes (e.g., `404 Not Found`).

&nbsp;   - Scans destination page content for user-defined invalidation keywords.

&nbsp;   - Gracefully handles and identifies non-HTTP links (`mailto:`, `ftp:`) and internal document links.

\- \*\*Multiple Output Formats:\*\*

&nbsp;   - \*\*Enhanced Excel Reports:\*\* Multi-sheet reports featuring a high-level summary, detailed link data, anchor text, and automatic conditional formatting to highlight errors.

&nbsp;   - \*\*Highlighted PDFs:\*\* A copy of the original PDF with invalid links highlighted in a user-selectable color.

&nbsp;   - \*\*Extracted PDFs:\*\* New, smaller PDFs containing only the pages with highlights, either in original order or sorted by the number of invalid links.

\- \*\*Modern Web Interface:\*\*

&nbsp;   - A clean, professional, and responsive UI that works on desktop and mobile.

&nbsp;   - Light/dark mode theme toggle.

&nbsp;   - Real-time results displayed on an interactive, searchable, and sortable table without page reloads (AJAX).

&nbsp;   - All generated files are delivered in a single, convenient `.zip` archive.



---



\## Technology Stack



\- \*\*Backend:\*\* Python 3, Flask

\- \*\*PDF Processing:\*\* PyMuPDF, pandas

\- \*\*Web Scraping:\*\* aiohttp, asyncio

\- \*\*Frontend:\*\* HTML5, CSS3, JavaScript (with jQuery for AJAX)

\- \*\*Styling:\*\* Pico.css Framework

\- \*\*Excel Generation:\*\* XlsxWriter

\- \*\*Testing (Optional):\*\* pytest



---



\## Getting Started: Running Locally



Follow these instructions to set up and run the application on your local machine for development and testing.



\### Prerequisites



\- Python 3.8 or newer

\- `pip` (Python package installer)



\### 1. Set Up the Project



First, clone or download this repository to your local machine. Navigate into the project directory using your command line or terminal.



```bash

\# Example: Navigate to the project folder

cd path/to/your/pdf\_processor\_app

2. Create a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies and avoid conflicts with other Python projects.

Generated bash

\# Create the virtual environment

python -m venv venv



\# Activate the virtual environment

\# On Windows:

venv\\Scripts\\activate

\# On macOS/Linux:

source venv/bin/activate

You will know it's active when you see (venv) at the beginning of your terminal prompt.

3. Install Dependencies

Install all the required Python libraries using the requirements.txt file. The playwright library also requires installing browser binaries.

Generated bash

\# Install Python packages

pip install -r requirements.txt



\# Install Playwright browser dependencies (only needed once)

playwright install

4. Run the Application

With the virtual environment active and dependencies installed, you can now start the Flask development server.

Generated bash

flask --app app.py run
You should see output indicating the server is running, typically on http://127.0.0.1:5000.

Generated code

\* Serving Flask app 'app'

&nbsp;\* Running on http://127.0.0.1:5000

Press CTRL+C to quit

Use code with caution.

5\. Access the Application

Open your web browser and navigate to:

http://127.0.0.1:5000

You can now use the PDF Link Processor!

Project Structure

A brief overview of the project's file organization:

Generated code

/pdf\_processor\_app

├── static/                 # Static files (logo, custom CSS/JS if needed)

│   └── logo.png

├── templates/              # HTML templates for the frontend

│   └── index.html

├── app.py                  # The main Flask application, handles routes and logic

├── processing.py           # Core PDF processing and link checking functions

├── requirements.txt        # List of all Python package dependencies

└── README.md               # This file



