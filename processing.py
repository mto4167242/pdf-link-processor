# --- FILE: processing.py (Corrected and Final Version) ---

import fitz  # PyMuPDF
import pandas as pd
import aiohttp
import asyncio
import os  # <-- THE MISSING IMPORT IS NOW ADDED

async def check_link(session, url, keywords):
    if not url.startswith(('http://', 'https://')):
        return {"valid": True, "status_code": "N/A", "reason": "Non-HTTP Link"}
    try:
        async with session.get(url, timeout=20, ssl=False) as response:
            status_code = response.status
            if status_code >= 400:
                return {"valid": False, "status_code": status_code, "reason": "HTTP Error"}
            text = await response.text()
            text_lc = text.lower()
            for keyword in keywords:
                if keyword in text_lc:
                    return {"valid": False, "status_code": status_code, "reason": "Matched Keyword"}
            return {"valid": True, "status_code": status_code, "reason": "OK"}
    except Exception as e:
        return {"valid": False, "status_code": "Error", "reason": f"{type(e).__name__}"}

async def run_link_check(pdf_path, keywords):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        summary = {"status": "error", "message": f"Could not open '{os.path.basename(pdf_path)}'. It may be corrupt or password-protected."}
        return pd.DataFrame(), summary

    links_to_check = []
    for page_num, page in enumerate(doc):
        # CORRECTED: page.get_links() has no arguments
        for link in page.get_links():
            # Use .get() for safety in case a key is missing
            link_info = {"page": page_num + 1, "url": link.get("uri"), "anchor_text": ""}
            try:
                # get_textbox can fail if the link area is empty
                link_info["anchor_text"] = page.get_textbox(link['from'])
            except:
                pass # Leave anchor_text blank if it fails
            
            if link.get('kind') == fitz.LINK_GOTO:
                link_info.update({"url": f"Internal -> Page {link.get('page', 0) + 1}", "link_type": "Internal"})
            elif link.get('kind') == fitz.LINK_URI:
                link_info.update({"link_type": "External"})
            links_to_check.append(link_info)

    if not links_to_check:
        summary = {"status": "no_links", "message": f"The PDF '{os.path.basename(doc.name)}' was processed successfully, but no hyperlinks were found inside."}
        return pd.DataFrame(), summary

    http_links = [l for l in links_to_check if l.get('link_type') == 'External' and l.get('url', '').startswith('http')]
    other_links = [l for l in links_to_check if l not in http_links]
    
    results = []
    if http_links:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [check_link(session, item["url"], keywords) for item in http_links]
            responses = await asyncio.gather(*tasks)
            for i, item in enumerate(http_links):
                results.append({**item, **responses[i]})
    
    for item in other_links:
        results.append({**item, "valid": True, "status_code": "N/A", "reason": "Internal or Non-HTTP Link"})

    df = pd.DataFrame(results).sort_values(by="page").reset_index(drop=True)
    
    invalid_count = len(df) - int(df['valid'].sum())
    summary = {
        "status": "success",
        "message": f"All {len(df)} links in '{os.path.basename(doc.name)}' are valid. No errors found! 🎉" if invalid_count == 0 else "Processing complete.",
        "filename": os.path.basename(doc.name), "total_pages": len(doc), "total_links": len(df),
        "valid_links": int(df['valid'].sum()), "invalid_links": invalid_count,
        "error_breakdown": df[df['valid'] == False]['reason'].value_counts().to_dict() if invalid_count > 0 else {}
    }
    
    # Ensure all columns exist before reordering
    all_cols = ['page', 'anchor_text', 'url', 'valid', 'status_code', 'reason', 'link_type']
    for col in all_cols:
        if col not in df:
            df[col] = None
    df = df[all_cols]
    
    return df, summary

def create_highlighted_pdf(source_pdf_path, output_pdf_path, invalid_links, color_name="Yellow"):
    COLOR_MAP = {"Yellow": (1, 1, 0), "Pink": (1, 0.7, 0.8), "Green": (0.5, 1, 0.5), "Blue": (0.7, 0.8, 1)}
    highlight_color = COLOR_MAP.get(color_name, (1, 1, 0))
    doc = fitz.open(source_pdf_path)
    target_links = set(invalid_links)
    for page in doc:
        # CORRECTED: page.get_links() has no arguments
        for link in page.get_links():
             if link.get("kind") == fitz.LINK_URI and link.get("uri") in target_links:
                try:
                    highlight = page.add_highlight_annot(link["from"])
                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()
                except:
                    pass # Failsafe in case of weird link geometry
    doc.save(output_pdf_path)
    return True

# ... The rest of the file (count_highlights, extract_final_pdf) remains the same ...
def count_highlights(page):
    count = 0
    for annot in page.annots():
        if annot.type[0] == 8: count += 1
    return count

def extract_final_pdf(source_path, output_path, sort_by_count=False):
    doc = fitz.open(source_path)
    pages_to_extract = []
    for i, page in enumerate(doc):
        highlight_count = count_highlights(page)
        if highlight_count > 0: pages_to_extract.append({"page_num": i, "count": highlight_count})
    if not pages_to_extract: return 0
    if sort_by_count: pages_to_extract.sort(key=lambda p: p["count"], reverse=True)
    new_doc = fitz.open()
    for item in pages_to_extract:
        new_doc.insert_pdf(doc, from_page=item["page_num"], to_page=item["page_num"])
    new_doc.save(output_path)
    return len(pages_to_extract)