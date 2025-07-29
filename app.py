# --- FILE: app.py (Definitive Production Version) ---

import os
import uuid
import asyncio
import zipfile
import pandas as pd
import json
import logging
from flask import Flask, render_template, request, Response, send_from_directory
from flask_talisman import Talisman
from processing import run_link_check_stream, create_highlighted_pdf, extract_final_pdf

# --- 1. SETUP LOGGING ---
# This sets up a logger that will print detailed, timestamped messages to the Render console.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
if not os.path.exists('temp_files'):
    os.makedirs('temp_files')
app.config['TEMP_FOLDER'] = 'temp_files'

# --- 2. SETUP SECURITY HEADERS ---
# The content_security_policy=None is important to allow our inline scripts and styles to work.
Talisman(app, content_security_policy=None)

# --- The save_enhanced_excel_report helper function is unchanged and correct ---
def save_enhanced_excel_report(df, summary, excel_path):
    try:
        logging.info(f"Generating Excel report for {summary.get('filename')}...")
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            workbook = writer.book; summary_sheet = workbook.add_worksheet('Summary'); header_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'}); bold_format = workbook.add_format({'bold': True})
            summary_sheet.write('A1', 'Analysis Summary', header_format); summary_sheet.write('A3', 'Filename:', bold_format); summary_sheet.write('B3', summary.get('filename')); summary_sheet.write('A4', 'Total Pages:', bold_format); summary_sheet.write('B4', summary.get('total_pages')); summary_sheet.write('A6', 'Link Scorecard', header_format); summary_sheet.write('A7', 'Total Links Found:', bold_format); summary_sheet.write('B7', summary.get('total_links')); summary_sheet.write('A8', 'Valid Links:', bold_format); summary_sheet.write('B8', summary.get('valid_links')); summary_sheet.write('A9', 'Invalid Links:', bold_format); summary_sheet.write('B9', summary.get('invalid_links'))
            if summary.get('error_breakdown'):
                summary_sheet.write('A11', 'Invalid Link Breakdown', header_format); row = 11
                for reason, count in summary['error_breakdown'].items(): summary_sheet.write(row, 0, reason, bold_format); summary_sheet.write(row, 1, count); row += 1
            summary_sheet.set_column('A:A', 25)
            if not df.empty:
                df.to_excel(writer, sheet_name='All Links Data', index=False); data_sheet = writer.sheets['All Links Data']; invalid_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'}); data_sheet.conditional_format(f'A2:G{len(df) + 1}', {'type': 'formula', 'criteria': f'=INDIRECT("D"&ROW())=FALSE', 'format': invalid_format})
                for i, col in enumerate(df.columns): width = max(df[col].astype(str).str.len().max(), len(col)) + 2; data_sheet.set_column(i, i, min(width, 60))
        logging.info("Excel report generated successfully.")
    except Exception as e:
        logging.error(f"Failed to generate Excel report: {e}")
        raise # Re-raise the exception to be caught by the main handler

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    job_id = str(uuid.uuid4()); job_folder = os.path.join(app.config['TEMP_FOLDER'], job_id); os.makedirs(job_folder)
    logging.info(f"New job started with ID: {job_id}")
    
    pdf_file = request.files.get('pdf_file')
    if not pdf_file or pdf_file.filename == '':
        logging.warning("Process attempt failed: No file was selected.")
        def error_stream(): yield "event: error\ndata: No file was selected.\n\n"
        return Response(error_stream(), mimetype='text/event-stream')

    source_path = os.path.join(job_folder, pdf_file.filename); pdf_file.save(source_path)
    keywords = [line.strip().lower() for line in request.form.get('keywords', '').splitlines() if line.strip()]
    outputs_requested = request.form.getlist('outputs')
    highlight_color = request.form.get('highlight_color', 'Yellow')
    logging.info(f"Processing file '{pdf_file.filename}' with {len(keywords)} keywords.")

    def event_stream():
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            final_df = None; total_time = 0

            async def consume_stream_wrapper():
                nonlocal final_df, total_time
                async for message in run_link_check_stream(source_path, keywords):
                    if message.startswith("event: final_data"):
                        data_json = message.split("data: ")[1].strip()
                        final_data = json.loads(data_json)
                        final_df = pd.read_json(final_data['dataframe'], orient='split')
                        total_time = final_data['total_time']
                    else:
                        yield message
            
            async def consume_and_yield():
                async for item in consume_stream_wrapper():
                    yield item

            for message in loop.run_until_complete(self_contained_run(consume_and_yield)):
                yield message

            if final_df is not None:
                final_html = generate_final_files_and_html(final_df, job_id, job_folder, source_path, pdf_file.filename, outputs_requested, highlight_color, total_time)
                yield f"event: complete\ndata: {final_html}\n\n"
            logging.info(f"Job {job_id} completed successfully.")
        except Exception as e:
            logging.error(f"Critical error during job {job_id}: {e}", exc_info=True) # exc_info=True prints the full traceback
            yield f"event: error\ndata: A critical error occurred. Please check the server logs for job ID {job_id}.\n\n"

    return Response(event_stream(), mimetype='text/event-stream')

async def self_contained_run(async_gen_func):
    results = []
    async for item in async_gen_func():
        results.append(item)
    return results

def generate_final_files_and_html(df, job_id, job_folder, source_path, filename, outputs, color, total_time):
    try:
        logging.info(f"Job {job_id}: Starting final file generation.")
        output_paths = []; base_filename = os.path.splitext(filename)[0]
        invalid_count = len(df) - int(df['valid'].sum())
        summary = {"filename": filename, "total_pages": int(df['page'].max()), "total_links": len(df), "valid_links": int(df['valid'].sum()), "invalid_links": invalid_count, "error_breakdown": df[df['valid'] == False]['reason'].value_counts().to_dict() if invalid_count > 0 else {}}
        if 'excel' in outputs:
            excel_path = os.path.join(job_folder, f"{base_filename}_report.xlsx"); save_enhanced_excel_report(df, summary, excel_path); output_paths.append(excel_path)
        
        invalid_links = df[df['valid'] == False]['url'].tolist()
        if invalid_links:
            logging.info(f"Job {job_id}: Found {len(invalid_links)} invalid links to highlight.")
            highlighted_pdf_path = os.path.join(job_folder, f"{base_filename}_highlighted.pdf")
            create_highlighted_pdf(source_path, highlighted_pdf_path, invalid_links, color)
            if 'highlighted' in outputs: output_paths.append(highlighted_pdf_path)
            if 'extracted' in outputs:
                extracted_path = os.path.join(job_folder, f"{base_filename}_extracted.pdf"); 
                if extract_final_pdf(highlighted_pdf_path, extracted_path, sort_by_count=False) > 0: output_paths.append(extracted_path)
            if 'sorted' in outputs:
                sorted_path = os.path.join(job_folder, f"{base_filename}_sorted.pdf"); 
                if extract_final_pdf(highlighted_pdf_path, sorted_path, sort_by_count=True) > 0: output_paths.append(sorted_path)
        
        final_html = f"<h4>Processing Complete!</h4><p>Finished checking {summary['total_links']} links in {total_time} seconds.</p>"
        if output_paths:
            zip_filename = f"PDF_Results_{job_id[:8]}.zip"; zip_path = os.path.join(app.config['TEMP_FOLDER'], zip_filename)
            logging.info(f"Job {job_id}: Creating zip file with {len(output_paths)} items.")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in output_paths: zipf.write(file_path, os.path.basename(file_path))
            final_html += f'<hr><a href="/download/{zip_filename}" role="button">Download All Results (.zip)</a>'
        else:
            final_html += "<hr><p>No output files were generated based on your selections.</p>"
        logging.info(f"Job {job_id}: Final HTML response generated.")
        return f"<article>{final_html}</article>"
    except Exception as e:
        logging.error(f"Job {job_id}: Error during final file generation: {e}", exc_info=True)
        return f"<article><h4 style='color:red;'>Error During File Generation</h4><p>The link checking was successful, but an error occurred while creating the output files. Please check the server logs for job ID {job_id}.</p></article>"

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['TEMP_FOLDER'], filename, as_attachment=True)