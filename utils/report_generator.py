from fpdf import FPDF
from pypdf import PdfWriter
import io
import time
import hashlib

def generate_evaluation_pdf(user_data, final_verdict, audit_logs, transcript_bytes=None, ielts_bytes=None):
    """
    Generates a professional report and merges student uploads:
    Page 1: Executive Decision & Scores
    Page 2: Full System Audit Log & Transcript
    Appended Pages: Raw Transcript and IELTS PDFs
    """
    
    # 1. UNIQUE ID GENERATION
    name_raw = user_data.get('name', 'unknown')
    name_hash = hashlib.md5(name_raw.encode()).hexdigest()[:6].upper()
    timestamp_id = time.strftime('%y%m%d') 
    candidate_id = f"WS-{timestamp_id}-{name_hash}"

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    
    # ==========================================
    # PAGE 1: THE EXECUTIVE SUMMARY
    # ==========================================
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Admissions Evaluation Report", ln=True, align='C')
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"CANDIDATE ID: {candidate_id}", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # Profile Section
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " Candidate Profile", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.ln(2)
    pdf.cell(0, 7, f"Name: {user_data.get('name', 'N/A')}", ln=True)
    pdf.cell(0, 7, f"Target Program: {user_data.get('degree', 'N/A')}", ln=True)
    pdf.ln(5)

    # Decision Block
    decision = final_verdict.get("overall_recommendation", "N/A")
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, "Final Decision: ", ln=0)
    if decision == "Admit": pdf.set_text_color(0, 128, 0)
    elif decision == "Conditional Admission": pdf.set_text_color(255, 140, 0)
    else: pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, decision.upper(), ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # Executive Summary
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " Executive Summary", ln=True, fill=True)
    pdf.ln(2)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 7, final_verdict.get("executive_summary", "No summary provided."))
    pdf.ln(10)

    # Score Breakdown
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " Cognitive Scorecard", ln=True, fill=True)
    pdf.ln(2)
    pdf.set_font("Arial", '', 11)
    sub_scores = final_verdict.get("sub_scores", {})
    if isinstance(sub_scores, str):  # Just in case it was stored as a string
        import json
        try:
            sub_scores = json.loads(sub_scores)
        except:
            sub_scores = {}
            
    for cat, score in sub_scores.items():
        pdf.cell(0, 7, f"- {cat.replace('_', ' ').capitalize()}: {score}/10", ln=True)

    # ==========================================
    # PAGE 2: THE SYSTEM AUDIT LOG
    # ==========================================
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "System Audit Log & Technical Reasoning", ln=True)
    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "This section contains the raw internal reasoning of the AI specialists.", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    for log in audit_logs:
        # Log Title Line
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(0, 8, f" [{log.get('time', '')}] {log.get('label', 'Log')}", ln=True, fill=True)
        
        # Log Content
        pdf.set_font("Arial", '', 9)
        content = str(log.get('content', '')) # Convert JSON or text to string
        pdf.multi_cell(0, 5, content)
        pdf.ln(2)

    # Get the raw bytes of the generated scorecard
    scorecard_bytes = pdf.output(dest='S').encode('latin-1', errors='ignore')

    # ==========================================
    # MERGE THE FILES USING PYPDF
    # ==========================================
    merger = PdfWriter()
    
    # 1. Add the Scorecard
    merger.append(io.BytesIO(scorecard_bytes))
    
    # 2. Add the Transcript (if it exists)
    if transcript_bytes:
        try:
            merger.append(io.BytesIO(transcript_bytes))
        except Exception as e:
            print(f"Failed to merge transcript: {e}")
            
    # 3. Add the IELTS (if it exists)
    if ielts_bytes:
        try:
            merger.append(io.BytesIO(ielts_bytes))
        except Exception as e:
            print(f"Failed to merge IELTS: {e}")

    # Output final binary
    output = io.BytesIO()
    merger.write(output)
    final_combined_pdf = output.getvalue()

    return final_combined_pdf, candidate_id