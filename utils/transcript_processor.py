import pdfplumber
import json
import io
from core.ai_client import client

# Thresholds
MIN_OVERALL_CGPA = 3.0
COURSE_WARNING_THRESHOLD = 3.3

def extract_transcript_data(pdf_file):
    """
    Step 1: Extract text and parse into JSON, now including Student Name.
    """
    print("Reading Transcript PDF...")
    raw_text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_file)) as pdf:
            for page in pdf.pages:
                raw_text += (page.extract_text(layout=True) or "") + "\n"

    except Exception as e:
        print(f"Failed to read PDF: {e}")
        return None

    prompt = f"""
    Text from transcript:
    ---
    {raw_text}
    ---
    MISSION: You are a Senior Registrar. Extract a clean academic history from this raw text.

    REASONING STEPS:
    1. INSTITUTIONAL CONTEXT: Identify the university and its grading scale (e.g., 4.3 or 4.0).
    2. COURSE IDENTITY (THE 'FUZZY MATCH'):
       - Intelligently identify course titles. Course titles are unique. Sometimes they are on the immediate next line.
       - Never write "Topics in Computing Science" in a course title. Those are just generic descriptions. 
       - Merge any descriptive words into a single 'course_title'. 
       - IGNORE generic headers like 'Topics in Computing Science' if a more specific sub-title (like 'Programming Languages') exists right next to it.
    3. STUDENT GRADE (THE 'HIERARCHY OF TRUTH'):
       - Locate the student's specific letter grade ONLY (A, B+, CR, etc.). Might be called grade remark. 
       - NEVER extract any numeric grade.
       - Ignore class averages even if they are numeric.
       - Use the MAPPING below to convert letters to a 4.0 scale.
    4. DEGREE COMPLETION: 
       - If thesis is passed, or complete or approved, degree is complete.
       - If it is explicitly mentioned that degree requirements are complete, that means complete too.
       - If these are present, set "degree_status" to "Completed/Passed".
       - Otherwise, if thesis courses show "PASS" or "APPR", set to "Completed/Passed".
       - Else, set to "In Progress" or "Not Found".

    UNIVERSAL MAPPING:
    A+/A = 4.0, A- = 3.7, B+ = 3.3, B = 3.0, B- = 2.7, C+ = 2.3, C = 2.0
    
    Return ONLY JSON:
    {{
        "student_name": "string",
        "grading_scale_used": "string",
        "max_cgpa": float,
        "explicit_cgpa": float or null,
        "graded_courses": [ {{ "course_name": "string", "grade": float }} ],
        "non_graded_courses": [ {{ "course_name": "string", "status": "string" }} ],
        "thesis_status: "string"
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={ "type": "json_object" }
        )
        data = json.loads(response.choices[0].message.content)
        
        raw_graded = data.get("graded_courses", [])
        valid_graded = [c for c in raw_graded if isinstance(c.get("grade"), (int, float))]
        
        if valid_graded:
            data["calculated_cgpa_raw"] = round(sum(c["grade"] for c in valid_graded) / len(valid_graded), 2)
            norm_sum = sum(min(c["grade"], 4.0) for c in valid_graded)
            data["calculated_cgpa_4_0_scale"] = round(norm_sum / len(valid_graded), 2)
        else:
            data["calculated_cgpa_raw"] = 0.0
            data["calculated_cgpa_4_0_scale"] = 0.0

        return data
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def generate_transcript_report(transcript_data, user_data):
    """
    Step 2: Generate the 3-line summary using personal pronouns.
    """
    name = user_data.get('name', 'The candidate')
    pronoun = user_data.get('pronoun_subject', 'they') 
    possessive = user_data.get('pronoun_possessive', 'their')

    prompt = f"""
    Write a 3-line professional academic summary for {name}.
    Data: {json.dumps(transcript_data)}
    
    - Use the student's name: {name} and {pronoun}/{possessive} pronouns.
    - Mention their Normalized CGPA: {transcript_data.get('calculated_cgpa_4_0_scale')} / 4.0.
    - Confirm if they meet the threshold of {MIN_OVERALL_CGPA}.
    - State Thesis status and any courses below {COURSE_WARNING_THRESHOLD}.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content