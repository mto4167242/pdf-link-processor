# --- FILE: app.py (Final, Simplest Multi-Page Version) ---

from flask import Flask, render_template, request, send_from_directory
import os
import uuid
import asyncio
import zipfile
import pandas as pd
from processing import run_link_check, create_highlighted_pdf, extract_final_pdf

app = Flask(__name__)
if not os.path.exists('temp_files'): os.makedirs('temp_files')
app.config['TEMP_FOLDER'] = 'temp_files'

# ... save_enhanced_excel_report is unchanged and correct ...
def save_enhanced_excel_report(df, summary, excel_path):
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    job_id = str(uuid.uuid4()); job_folder = os.path.join(app.config['TEMP_FOLDER'], job_id); os.makedirs(job_folder)
    
    # We use getlist to handle multiple file uploads
    uploaded_files = request.files.getlist('pdf_file')
    if not uploaded_files or uploaded_files[0].filename == '':
        return "Error: No file selected. Please go back and try again.", 400

    keywords = [line.strip().lower() for line in request.form.get('keywords', '').splitlines() if line.strip()]
    outputs_requested = request.form.getlist('outputs')
    highlight_color = request.form.get('highlight_color', 'Yellow')
    
    all_summaries = []; output_paths = []

    for pdf_file in uploaded_files:
        source_path = os.path.join(job_folder, pdf_file.filename); pdf_file.save(source_path)
        # Use the non-streaming version of the function
        df, summary = asyncio.run(run_link_check(source_path, keywords))
        all_summaries.append(summary)

        if summary['status'] == 'success':
            base_filename = os.path.splitext(pdf_file.filename)[0]
            if 'excel' in outputs_requested:
                excel_path = os.path.join(job_folder, f"{base_filename}_report.xlsx"); save_enhanced_excel_report(df, summary, excel_path); output_paths.append(excel_path)
            
            invalid_links = df[df['valid'] == False]['url'].tolist()
            if invalid_links:
                highlighted_pdf_path = os.path.join(job_folder, f"{base_filename}_highlighted.pdf")
                create_highlighted_pdf(source_path, highlighted_pdf_path, invalid_links, highlight_color)
                if 'highlighted' in outputs_requested: output_paths.append(highlighted_pdf_path)
                if 'extracted' in outputs_requested:
                    extracted_path = os.path.join(job_folder, f"{base_filename}_extracted.pdf");
                    if extract_final_pdf(highlighted_pdf_path, extracted_path, sort_by_count=False) > 0: output_paths.append(extracted_path)
                if 'sorted' in outputs_requested:
                    sorted_path = os.path.join(job_folder, f"{base_filename}_sorted.pdf");
                    if extract_final_pdf(highlighted_pdf_path, sorted_path, sort_by_count=True) > 0: output_paths.append(sorted_path)

    zip_filename = None
    if output_paths:
        zip_filename = f"PDF_Results_{job_id[:8]}.zip"
        zip_path = os.path.join(app.config['TEMP_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in output_paths: zipf.write(file_path, os.path.basename(file_path))

    # Render a completely new page with the results
    return render_template('results.html', summaries=all_summaries, zip_file=zip_filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['TEMP_FOLDER'], filename, as_attachment=True)