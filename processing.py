# --- FILE: processing.py (Final Version with Your Original Validation Logic) ---

import fitz
import pandas as pd
import aiohttp
import asyncio
import os

async def check_link(session, url, keywords):
    """
    This function mirrors the logic from your original script.
    A link is ONLY invalid if a keyword is found or a connection error occurs.
    """
    if not url.startswith(('http://', 'https://')):
        return {"valid": True, "status_code": "N/A", "reason": "Non-HTTP Link"}
    
    try:
        async with session.get(url, timeout=20, ssl=False) as response:
            status_code = response.status
            text = await response.text()
            text_lc = text.lower()
            
            for keyword in keywords:
                if keyword in text_lc:
                    return {"valid": False, "status_code": status_code, "reason": "Matched Keyword"}
            
            # If no keywords found, the link is VALID, eliminating false positives.
            return {"valid": True, "status_code": status_code, "reason": "OK"}
            
    except Exception as e:
        return {"valid": False, "status_code": "Error", "reason": f"{type(e).__name__}"}


async def run_link_check(pdf_path, keywords):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        summary = {"status": "error", "message": f"Could not open '{os.path.basename(pdf_path)}'."}
        return pd.DataFrame(), summary

    links_to_check = []
    for page_num, page in enumerate(doc):
        for link in page.get_links():
            link_info = {"page": page_num + 1, "url": link.get("uri"), "anchor_text": ""}
            try:
                if link.get('from'): link_info["anchor_text"] = page.get_textbox(link['from'])
            except Exception: pass
            if link.get('kind') == fitz.LINK_GOTO:
                link_info.update({"url": f"Internal -> Page {link.get('page', 0) + 1}", "link_type": "Internal"})
            elif link.get('kind') == fitz.LINK_URI:
                link_info.update({"link_type": "External"})
            links_to_check.append(link_info)

    if not links_to_check:
        summary = {"status": "no_links", "message": f"PDF '{os.path.basename(doc.name)}' has no hyperlinks."}
        return pd.DataFrame(), summary

    http_links = [l for l in links_to_check if l.get('link_type') == 'External' and l.get('url', '').startswith('http')]
    other_links = [l for l in links_to_check if l not in http_links]
    
    results = []
    if http_links:
        # Use a semaphore for stability on Render
        sem = asyncio.Semaphore(15)
        connector = aiohttp.TCPConnector(ssl=False)
        async def check_link_with_semaphore(session, url, keywords):
            async with sem:
                return await check_link(session, url, keywords)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [check_link_with_semaphore(session, item["url"], keywords) for item in http_links]
            responses = await asyncio.gather(*tasks)
            for i, item in enumerate(http_links): results.append({**item, **responses[i]})
    
    for item in other_links: results.append({**item, "valid": True, "status_code": "N/A", "reason": "Internal or Non-HTTP Link"})
    df = pd.DataFrame(results).sort_values(by="page").reset_index(drop=True)
    
    invalid_count = len(df) - int(df['valid'].sum())
    summary = {
        "status": "success", "message": f"Checked {len(df)} links. Found {invalid_count} invalid links." if invalid_count > 0 else f"All {len(df)} links are valid!",
        "filename": os.path.basename(doc.name), "total_pages": len(doc), "total_links": len(df),
        "valid_links": int(df['valid'].sum()), "invalid_links": invalid_count,
        "error_breakdown": df[df['valid'] == False]['reason'].value_counts().to_dict() if invalid_count > 0 else {}
    }
    all_cols = ['page', 'anchor_text', 'url', 'valid', 'status_code', 'reason', 'link_type']
    for col in all_cols:
        if col not in df.columns: df[col] = pd.NA
    df = df[all_cols]
    return df, summary

# The helper functions (create_highlighted_pdf, etc.) are correct and do not need to be changed.
def create_highlighted_pdf(source_pdf_path, output_pdf_path, invalid_links, color_name="Yellow"):
    COLOR_MAP = {"Yellow": (1, 1, 0), "Pink": (1, 0.7, 0.8), "Green": (0.5, 1, 0.5), "Blue": (0.7, 0.8, 1)}
    highlight_color = COLOR_MAP.get(color_name, (1, 1, 0))
    doc = fitz.open(source_pdf_path); target_links = set(invalid_links)
    for page in doc:
        for link in page.get_links():
             if link.get("kind") == fitz.LINK_URI and link.get("uri") in target_links:
                try:
                    highlight = page.add_highlight_annot(link["from"]); highlight.set_colors(stroke=highlight_color); highlight.update()
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