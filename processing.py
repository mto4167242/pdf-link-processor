# --- FILE: processing.py (Definitive Production Version) ---

import fitz
import pandas as pd
import aiohttp
import asyncio
import os
import time

async def check_link(session, url, keywords):
    # This logic is correct and unchanged
    if not url.startswith(('http://', 'https://')): return {"valid": True, "status_code": "N/A", "reason": "Non-HTTP Link"}
    try:
        async with session.get(url, timeout=20, ssl=False) as response:
            status_code = response.status; text = await response.text(); text_lc = text.lower()
            for keyword in keywords:
                if keyword in text_lc: return {"valid": False, "status_code": status_code, "reason": "Matched Keyword"}
            return {"valid": True, "status_code": status_code, "reason": "OK"}
    except Exception as e: return {"valid": False, "status_code": "Error", "reason": f"{type(e).__name__}"}

async def check_link_with_semaphore(sem, session, url, keywords):
    async with sem: return await check_link(session, url, keywords)

async def run_link_check_stream(pdf_path, keywords):
    start_time = time.time()
    try: doc = fitz.open(pdf_path)
    except Exception as e:
        yield f"event: error\ndata: Could not open '{os.path.basename(pdf_path)}'. It may be corrupt or password-protected.\n\n"
        return

    links_to_check = [];
    for page_num, page in enumerate(doc):
        for link in page.get_links():
            link_info = {"page": page_num + 1, "url": link.get("uri"), "anchor_text": ""}
            try:
                if link.get('from'): link_info["anchor_text"] = page.get_textbox(link['from'])
            except: pass
            if link.get('kind') == fitz.LINK_GOTO: link_info.update({"url": f"Internal -> Page {link.get('page', 0) + 1}", "link_type": "Internal"})
            elif link.get('kind') == fitz.LINK_URI: link_info.update({"link_type": "External"})
            links_to_check.append(link_info)

    if not links_to_check:
        yield f"event: complete\ndata: <article><h4>Results for {os.path.basename(doc.name)}</h4><p>No hyperlinks were found in this PDF.</p></article>\n\n"
        return

    total_links = len(links_to_check)
    yield f"data: {{\"progress\": 0, \"total\": {total_links}, \"message\": \"Found {total_links} links. Starting checks...\"}}\n\n"

    http_links = [l for l in links_to_check if l.get('link_type') == 'External' and l.get('url', '').startswith('http')]
    other_links = [l for l in links_to_check if l not in http_links]
    
    all_results = []; progress = 0
    if http_links:
        # --- 3. SAFER SEMAPHORE FOR RENDER FREE TIER ---
        sem = asyncio.Semaphore(15)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [check_link_with_semaphore(sem, session, item["url"], keywords) for item in http_links]
            for i, task in enumerate(asyncio.as_completed(tasks)):
                response = await task
                original_link_info = http_links[i] # This is a simple way to keep track
                all_results.append({**original_link_info, **response})
                progress += 1
                # --- NEW: BATCHED PROGRESS UPDATES ---
                if progress % 10 == 0 or progress == total_links: # Update every 10 links or on the last one
                    yield f"data: {{\"progress\": {progress}, \"total\": {total_links}, \"message\": \"Checking link...\"}}\n\n"
    
    for item in other_links:
        all_results.append({**item, "valid": True, "status_code": "N/A", "reason": "Internal or Non-HTTP Link"})
        progress += 1
        if progress % 10 == 0 or progress == total_links:
            yield f"data: {{\"progress\": {progress}, \"total\": {total_links}, \"message\": \"Processing internal link...\"}}\n\n"

    df = pd.DataFrame(all_results)
    
    end_time = time.time(); total_time = round(end_time - start_time, 2)
    df_json = df.to_json(orient='split')
    yield f"event: final_data\ndata: {{\"dataframe\": {df_json}, \"total_time\": {total_time}}}\n\n"

# The helper functions (create_highlighted_pdf, etc.) are correct.
def create_highlighted_pdf(source_pdf_path, output_pdf_path, invalid_links, color_name="Yellow"):
    COLOR_MAP = {"Yellow": (1, 1, 0), "Pink": (1, 0.7, 0.8), "Green": (0.5, 1, 0.5), "Blue": (0.7, 0.8, 1)}
    highlight_color = COLOR_MAP.get(color_name, (1, 1, 0))
    doc = fitz.open(source_pdf_path); target_links = set(invalid_links)
    for page in doc:
        for link in page.get_links():
             if link.get("kind") == fitz.LINK_URI and link.get("uri") in target_links:
                try: highlight = page.add_highlight_annot(link["from"]); highlight.set_colors(stroke=highlight_color); highlight.update()
                except: pass
    doc.save(output_pdf_path); return True

def extract_final_pdf(source_path, output_path, sort_by_count=False):
    doc = fitz.open(source_path); pages_to_extract = []
    for i, page in enumerate(doc):
        count = 0
        for annot in page.annots():
            if annot.type[0] == 8: count += 1
        if count > 0: pages_to_extract.append({"page_num": i, "count": count})
    if not pages_to_extract: return 0
    if sort_by_count: pages_to_extract.sort(key=lambda p: p["count"], reverse=True)
    new_doc = fitz.open()
    for item in pages_to_extract: new_doc.insert_pdf(doc, from_page=item["page_num"], to_page=item["page_num"])
    new_doc.save(output_path); return len(pages_to_extract)