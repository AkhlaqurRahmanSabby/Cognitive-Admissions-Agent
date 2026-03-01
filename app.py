import streamlit as st
import time
from core import InterviewEngine, EvaluationEngine
from utils import TranscriptProcessor, generate_evaluation_pdf, extract_ielts_scores, check_ielts_threshold, extract_transcript_data, generate_transcript_report

# --- SESSION STATE INITIALIZATION ---
if "phase" not in st.session_state:
    st.session_state.phase = "intake"
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "transcript_report" not in st.session_state:
    st.session_state.transcript_report = ""
if "interview_engine" not in st.session_state:
    st.session_state.interview_engine = None
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []
if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = []

st.set_page_config(page_title="AI Admissions Portal", page_icon="🎓", layout="centered")

# --- REGIONAL DATA ---
EXEMPT_COUNTRIES = [
    "Canada", "United States", "United Kingdom", "Ireland", "Germany", 
    "France", "Netherlands", "Sweden", "Norway", "Denmark", "Finland", "Switzerland"
]
OTHER_COUNTRIES = [
    "India", "China", "Brazil", "Nigeria", "Pakistan", "Bangladesh", 
    "Iran", "South Korea", "Japan", "Vietnam", "Other"
]
ALL_COUNTRIES = sorted(EXEMPT_COUNTRIES + OTHER_COUNTRIES)


def render_auditor_sidebar():
    with st.sidebar:
        st.title("🛡️ System Auditor View")
        st.markdown("---")
        
        if not st.session_state.audit_logs:
            st.info("Awaiting system initialization...")
            return

        # Display logs in reverse order (newest at the bottom)
        for log in st.session_state.audit_logs:
                    with st.expander(f"{log['icon']} {log['label']}", expanded=False):
                        st.caption(f"Time: {log['time']}")
                        if log['is_json']:
                            st.json(log['content'])
                        else:
                            st.info(log['content'])

render_auditor_sidebar()

# ==========================================
# PHASE 1: INTAKE FORM
# ==========================================
if st.session_state.phase == "intake":
    CANADIAN_UNIVERSITIES = ["University of Toronto", "University of British Columbia", "McGill University", "McMaster University", "University of Alberta", "University of Waterloo", "Western University", "Queen's University", "University of Calgary", "Dalhousie University", "University of Ottawa", "Simon Fraser University", "University of Victoria", "Université de Montréal", "Université Laval", "York University"]
    TOP_PHD_PROGRAMS = ["PhD in Computer Science (AI/ML)", "PhD in Cognitive Psychology", "PhD in Bioinformatics", "PhD in Engineering", "PhD in Economics"]

    st.title("🎓 Admissions Portal")
    st.markdown("Welcome. Please provide your academic background to begin the cognitive assessment.")
    st.divider()

    with st.container():
        st.subheader("Candidate Information")
        name_col1, name_col2 = st.columns(2)
        with name_col1:
            first_name = st.text_input("First Name", placeholder="e.g., Jane")
        with name_col2:
            last_name = st.text_input("Last Name", placeholder="e.g., Doe")

        col1, col2 = st.columns(2)
        with col1:
            citizenship = st.selectbox("Citizenship", options=["Select a country..."] + ALL_COUNTRIES)
        with col2:
            target_program = st.selectbox("Target Graduate Program", options=["Select a program..."] + TOP_PHD_PROGRAMS)
            
        col3, col4 = st.columns(2)
        with col3:
            alma_mater = st.selectbox("Previous University", options=["Select a university..."] + CANADIAN_UNIVERSITIES)
        with col4:
            previous_degree = st.text_input("Previous Degree Earned", placeholder="e.g., BSc Mathematics")

    st.divider()

    with st.container():
        st.subheader("Required Documents")
        st.markdown("Please upload your documents in **PDF format** only.")
        transcript_file = st.file_uploader("Upload Official Transcript (Required)", type=["pdf"])
        
        # Dynamic IELTS Label based on citizenship
        is_exempt = citizenship in EXEMPT_COUNTRIES
        ielts_label = "Upload IELTS Result (Optional for your region)" if is_exempt else "Upload IELTS Result (Required)"
        ielts_file = st.file_uploader(ielts_label, type=["pdf"])

    st.write("") 

    if st.button("Initialize Assessment Engine", type="primary", use_container_width=True, key="init_btn"):
        errors = []
        if not first_name: errors.append("First Name")
        if not last_name: errors.append("Last Name")
        if target_program == "Select a program...": errors.append("Target Program")
        if citizenship == "Select a country...": errors.append("Citizenship")
        if alma_mater == "Select a university...": errors.append("Previous University")
        if not transcript_file: errors.append("Transcript PDF")

        if not is_exempt and not ielts_file:
            st.error("🛑 An IELTS result is strictly required for applicants from your country.")

        if errors:
            st.error(f"🛑 Missing Required Fields: {', '.join(errors)}")
        else:
            # All clear - Save to session state
            st.session_state.user_data = {
                "name": f"{first_name} {last_name}",
                "first_name": first_name,
                "citizenship": citizenship,
                "is_exempt": is_exempt,
                "degree": target_program,
                "alma_mater": alma_mater,
                "previous_degree": previous_degree
            }
            
            st.session_state.transcript_bytes = transcript_file.getvalue()
            st.session_state.ielts_bytes = ielts_file.getvalue() if ielts_file else None
            
            st.session_state.phase = "processing"
            st.rerun()

# ==========================================
# PHASE 2: PROCESSING SCREEN (HARD GATES)
# ==========================================
elif st.session_state.phase == "processing":
    st.title("⚙️ Cognitive Engine Initialization")
    st.markdown("Please hold while our AI parses your academic history...")
    
    with st.spinner("Verifying institutional credentials and language requirements..."):
        try:
            # --- STRICT IELTS HARD GATE ---
            ielts_summary = "IELTS waived based on North American/European citizenship."
            if not st.session_state.user_data["is_exempt"]:
                if st.session_state.ielts_bytes:
                    ielts_scores = extract_ielts_scores(st.session_state.ielts_bytes)
                    passed, failed_bands = check_ielts_threshold(ielts_scores)
                    
                    if not passed:
                        st.error(f"🛑 **AUTOMATIC REJECTION:** Minimum language proficiency not met.")
                        st.warning(f"Failed bands: {failed_bands} | Overall Score: {ielts_scores.get('overall')}")
                        st.info("Your application cannot proceed. Please retake the IELTS and achieve a minimum of 7.0 overall and 7.0 in all bands.")
                        
                        if st.button("Start New Application"):
                            st.session_state.clear()
                            st.rerun()
                        st.stop() # THIS KILLS THE PROCESS AND PREVENTS THE INTERVIEW
                    else:
                        ielts_summary = f"IELTS Cleared. Overall: {ielts_scores.get('overall')}. All bands >= 7.0."
                else:
                    st.error("System Error: IELTS document missing but required.")
                    st.stop()

            # --- TRANSCRIPT PROCESSING ---
            parsed_transcript_json = extract_transcript_data(st.session_state.transcript_bytes)
            if not parsed_transcript_json:
                st.error("Failed to parse transcript. Please ensure the PDF is readable.")
                st.stop()

            st.session_state.audit_logs.append({
                "icon": "📄",
                "label": "OCR: Raw Transcript Extraction",
                "content": parsed_transcript_json,
                "is_json": True,
                "time": time.strftime("%H:%M:%S")
            })
                
            transcript_summary = generate_transcript_report(parsed_transcript_json, st.session_state.user_data)
            st.session_state.audit_logs.append({
                "icon": "🧐",
                "label": "Registrar's Analytical Opinion",
                "content": transcript_summary,
                "is_json": False,
                "time": time.strftime("%H:%M:%S")
            })
            
            # --- COMPILE REPORT ---
            combined_report = f"""
            Candidate: {st.session_state.user_data['name']}
            Citizenship: {st.session_state.user_data['citizenship']}
            Targeting: {st.session_state.user_data['degree']}
            Previous Degree: {st.session_state.user_data['previous_degree']} from {st.session_state.user_data['alma_mater']}
            
            TRANSCRIPT EVALUATION:
            {transcript_summary}
            
            LANGUAGE PROFICIENCY:
            {ielts_summary}
            """
            st.session_state.transcript_report = combined_report
            
            # Initialize the Interview Engine
            st.session_state.interview_engine = InterviewEngine(
                user_data=st.session_state.user_data,
                transcript_report=st.session_state.transcript_report
            )
            
            initial_response = st.session_state.interview_engine.start_interview()
            st.session_state.chat_display.append(("assistant", initial_response["question"]))
            
            st.session_state.phase = "interview"
            st.rerun()
            
        except Exception as e:
            st.error(f"Error processing documents: {str(e)}")
            if st.button("Go Back"):
                st.session_state.phase = "intake"
                st.rerun()

# ==========================================
# PHASE 3: THE INTERVIEW UI
# ==========================================
elif st.session_state.phase == "interview":
    st.title("🎙️ Admissions Interview")
    st.success(f"Credentials verified. Welcome, {st.session_state.user_data['first_name']}. The assessment will now begin.")
    
    for role, content in st.session_state.chat_display:
        with st.chat_message(role):
            st.markdown(content)

    if user_input := st.chat_input("Type your response here..."):
        st.session_state.chat_display.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        st.session_state.audit_logs.append({
            "icon": "👤",
            "label": f"Candidate Response (Turn {len(st.session_state.chat_display)})",
            "content": user_input,
            "is_json": False,
            "time": time.strftime("%H:%M:%S")
        })

        with st.spinner("Analyzing response..."):
            engine_response = st.session_state.interview_engine.generate_response(user_input)
            st.session_state.audit_logs.append({
                "icon": "🧠",
                "label": f"Interviewer Reasoning (Turn {len(st.session_state.chat_display)})",
                "content": {
                    "ai_internal_evaluation": engine_response.get("evaluation"),
                    "current_rubric_state": engine_response.get("rubric_status")
                },
                "is_json": True,
                "time": time.strftime("%H:%M:%S")
            })
            st.session_state.chat_display.append(("assistant", engine_response["question"]))
            
            if engine_response.get("is_complete", False):
                st.session_state.audit_logs.append({
                    "icon": "✅",
                    "label": "Interview Cycle Complete",
                    "content": "All rubric items addressed or turn limit reached. Moving to Evaluation Engine.",
                    "is_json": False,
                    "time": time.strftime("%H:%M:%S")
                })
                time.sleep(2) 
                st.session_state.phase = "evaluation"
                st.rerun()
            else:
                st.rerun()

# ==========================================
# PHASE 4: FINAL EVALUATION (APPLICANT VIEW)
# ==========================================
elif st.session_state.phase == "evaluation":
    st.title("⚖️ Admissions Decision Portal")
    
    with st.spinner("Consolidating reports and finalizing verdict..."):
        interview_history = st.session_state.interview_engine.get_interview_data_for_evaluation()
        evaluator = EvaluationEngine(
            transcript_report=st.session_state.transcript_report,
            interview_history=interview_history,
            user_data=st.session_state.user_data
        )
        
        if "final_verdict" not in st.session_state:
            st.session_state.final_verdict = evaluator.generate_final_scorecard()
            st.session_state.applicant_letter = evaluator.generate_applicant_message(st.session_state.final_verdict)
            
            # Internal logging still happens in the background/sidebar
            st.session_state.audit_logs.append({
                "icon": "🏛️",
                "label": "Final Committee Consensus (JSON)",
                "content": st.session_state.final_verdict,
                "is_json": True,
                "time": time.strftime("%H:%M:%S")
            })

    # --- UI RENDER START ---
    final_verdict = st.session_state.final_verdict
    decision = final_verdict.get("overall_recommendation", "Error")

    # 1. Official Status Bar
    if decision == "Admit":
        st.success(f"**Decision: {decision}** 🎉")
        st.balloons()
    elif decision == "Conditional Admission":
        st.warning(f"**Decision: {decision}** ⚠️")
    else:
        st.error(f"**Decision: {decision}** 🛑")

    # 2. Professional Correspondence & PDF
    with st.container(border=True):
        st.subheader("Official Correspondence")
        # Polished LLM-generated message
        st.write(st.session_state.applicant_letter)
        
        st.divider()
        
        # Generate PDF and Candidate ID (Returns tuple)
        pdf_bytes, candidate_id = generate_evaluation_pdf(
            st.session_state.user_data, 
            final_verdict,
            st.session_state.audit_logs)
        
        # Display Candidate ID as a professional footer/reference
        st.caption(f"Reference ID: {candidate_id}")
        
        # Use ID and last name for the tracking filename
        safe_last_name = st.session_state.user_data.get('last_name', 'Candidate')
        tracking_filename = f"{candidate_id}_{safe_last_name}_Evaluation.pdf"
        
        st.download_button(
            label="📥 Download Official Evaluation Report (Internal Use)",
            data=pdf_bytes,
            file_name=tracking_filename,
            mime="application/pdf",
            use_container_width=True
        )

    # 3. Navigation
    st.write("")
    if st.button("Start New Application", use_container_width=True):
        st.session_state.clear()
        st.rerun()