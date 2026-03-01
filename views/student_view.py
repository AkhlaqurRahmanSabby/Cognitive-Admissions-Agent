import streamlit as st
import time
import json
from core import InterviewEngine, EvaluationEngine
from utils import TranscriptProcessor, IELTSProcessor, generate_evaluation_pdf

# --- REGIONAL DATA ---
EXEMPT_COUNTRIES = ["Canada", "United States", "United Kingdom", "Ireland", "Germany", "France", "Netherlands", "Sweden", "Norway", "Denmark", "Finland", "Switzerland"]
OTHER_COUNTRIES = ["India", "China", "Brazil", "Nigeria", "Pakistan", "Bangladesh", "Iran", "South Korea", "Japan", "Vietnam", "Other"]
ALL_COUNTRIES = sorted(EXEMPT_COUNTRIES + OTHER_COUNTRIES)

def handle_login_routing(username):
    """Checks the database to see if the user has already applied or abandoned."""
    app_record = st.session_state.db.get_application_by_username(username)
    
    if not app_record:
        st.session_state.phase = "intake"
    elif app_record['status'] == 'evaluated':
        st.session_state.phase = "completed"
        st.session_state.saved_verdict = json.loads(app_record['final_verdict_json'])
    else:
        # If the status is still 'interviewing' but they logged out/refreshed
        st.session_state.phase = "abandoned"

def render_student_portal():
    # ==========================================
    # PHASE 0: AUTHENTICATION
    # ==========================================
    if "student_logged_in" not in st.session_state:
        st.session_state.student_logged_in = False
        st.session_state.username = None

    if not st.session_state.student_logged_in:
        st.title("🎓 Applicant Portal")
        st.markdown("Please log in or create an account to start or resume your application.")
        
        tab1, tab2 = st.tabs(["Log In", "Create Account"])
        
        # --- LOGIN LOGIC ---
        with tab1:
            log_user = st.text_input("Username", key="log_user")
            log_pass = st.text_input("Password", type="password", key="log_pass")
            
            if st.button("Log In", use_container_width=True):
                if not log_user or not log_pass:
                    st.warning("Please enter both username and password.")
                else:
                    # Now it expects two values back (success boolean, and the message)
                    is_valid, message = st.session_state.db.verify_login(log_user, log_pass)
                    
                    if is_valid:
                        st.session_state.student_logged_in = True
                        st.session_state.username = log_user
                        st.success(message)
                        handle_login_routing(log_user) # Route based on history
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message) # This will now specifically say "Username not found" or "Incorrect password"
                
        # --- REGISTRATION LOGIC ---
        with tab2:
            reg_user = st.text_input("Choose Username", key="reg_user")
            reg_pass = st.text_input("Choose Password", type="password", key="reg_pass")
            
            if st.button("Create Account", use_container_width=True):
                if not reg_user or not reg_pass:
                    st.warning("Please fill in both fields.")
                else:
                    success, message = st.session_state.db.create_account(reg_user, reg_pass)
                    
                    if success:
                        st.session_state.student_logged_in = True
                        st.session_state.username = reg_user
                        st.session_state.phase = "intake" # Fresh start
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message) # Shows "Username already exists" if taken

        return # Stop execution until logged in

    # Show who is logged in
    st.sidebar.success(f"Logged in as: **{st.session_state.username}**")
    if st.sidebar.button("Log Out"):
        st.session_state.clear()
        st.rerun()

    # ==========================================
    # PHASE 1: INTAKE FORM
    # ==========================================
    if st.session_state.phase == "intake":
        CANADIAN_UNIVERSITIES = ["University of Toronto", "University of British Columbia", "McGill University", "McMaster University", "University of Alberta", "University of Waterloo", "Western University", "Queen's University", "University of Calgary", "Dalhousie University", "University of Ottawa", "Simon Fraser University", "University of Victoria", "Université de Montréal", "Université Laval", "York University", "Other"]
        TOP_PHD_PROGRAMS = ["PhD in Computer Science (AI/ML)", "PhD in Cognitive Psychology", "PhD in Bioinformatics", "PhD in Engineering", "PhD in Economics"]

        st.title("🎓 Application Initialization")
        st.markdown("Welcome. Please provide your academic background to begin the assessment.")
        st.divider()

        with st.form("intake_form", border=False):
            st.subheader("Candidate Information")
            name_col1, name_col2 = st.columns(2)
            first_name = name_col1.text_input("First Name", placeholder="e.g., Jane")
            last_name = name_col2.text_input("Last Name", placeholder="e.g., Doe")

            col1, col2 = st.columns(2)
            citizenship = col1.selectbox("Citizenship", options=["Select a country..."] + ALL_COUNTRIES)
            target_program = col2.selectbox("Target Graduate Program", options=["Select a program..."] + TOP_PHD_PROGRAMS)
            
            col3, col4 = st.columns(2)
            alma_mater = col3.selectbox("Previous University", options=["Select a university..."] + CANADIAN_UNIVERSITIES)
            previous_degree = col4.text_input("Previous Degree Earned", placeholder="e.g., BSc Mathematics")

            st.divider()
            st.subheader("Required Documents")
            transcript_file = st.file_uploader("Upload Official Transcript (Required PDF)", type=["pdf"])
            ielts_file = st.file_uploader("Upload IELTS Result (Required if not exempt)", type=["pdf"])

            st.divider()
            # 🔴 STRICT WARNING CHECKBOX
            st.warning("⚠️ **CRITICAL INSTRUCTIONS BEFORE PROCEEDING**")
            consent_checked = st.checkbox("I understand that once I begin the Cognitive Engine assessment, I cannot pause, refresh, or stop midway. Exiting the browser early will result in an automatic rejection.", value=False)

            submitted = st.form_submit_button("Start Assessment", type="primary", use_container_width=True)

        if submitted:
            errors = []
            if not first_name: errors.append("First Name")
            if not last_name: errors.append("Last Name")
            if target_program == "Select a program...": errors.append("Target Program")
            if citizenship == "Select a country...": errors.append("Citizenship")
            if not transcript_file: errors.append("Transcript PDF")
            if not consent_checked: errors.append("Consent Agreement")

            is_exempt = citizenship in EXEMPT_COUNTRIES
            if not is_exempt and not ielts_file:
                st.error("🛑 An IELTS result is required for applicants from your country.")
                errors.append("IELTS Result")

            if errors:
                st.error(f"🛑 Missing Required Fields: {', '.join(errors)}")
            else:
                st.session_state.user_data = {
                    "username": st.session_state.username,
                    "name": f"{first_name} {last_name}",
                    "first_name": first_name,
                    "last_name": last_name,
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
    # PHASE 2: PROCESSING SCREEN
    # ==========================================
    elif st.session_state.phase == "processing":
        st.title("⚙️ Validating Credentials")
        with st.spinner("Reviewing your academic history..."):
            try:
                # IELTS GATE
                ielts_summary = "IELTS waived."
                if not st.session_state.user_data["is_exempt"]:
                    ielts_processor = IELTSProcessor()
                    ielts_scores = ielts_processor.extract_ielts_scores(st.session_state.ielts_bytes)
                    passed, _ = ielts_processor.check_ielts_threshold(ielts_scores)
                    if not passed:
                        st.error("🛑 AUTOMATIC REJECTION: Minimum language proficiency not met.")
                        st.stop()
                    ielts_summary = f"IELTS Cleared. Overall: {ielts_scores.get('overall')}."

                # TRANSCRIPT PROCESS
                tp = TranscriptProcessor()
                raw_json = tp.extract_transcript_data(st.session_state.transcript_bytes)
                st.session_state.audit_logs.append({"icon": "📄", "label": "OCR", "content": raw_json, "is_json": True, "time": time.strftime("%H:%M:%S")})
                
                report = tp.generate_transcript_report(raw_json, st.session_state.user_data)
                st.session_state.transcript_report = report
                st.session_state.audit_logs.append({"icon": "🧐", "label": "Registrar", "content": report, "is_json": False, "time": time.strftime("%H:%M:%S")})
                
                # --- DB SYNC: Create Record with Username ---
                st.session_state.candidate_id = st.session_state.db.create_candidate_record(st.session_state.user_data, report, st.session_state.audit_logs)

                # ENGINE START
                st.session_state.interview_engine = InterviewEngine(st.session_state.user_data, report)
                init_res = st.session_state.interview_engine.start_interview()
                audio = st.session_state.audio_processor.generate_audio(init_res["question"])
                st.session_state.chat_display.append(("assistant", init_res["question"], audio))
                
                st.session_state.db.sync_to_db(st.session_state.candidate_id, st.session_state.chat_display, st.session_state.audit_logs)
                st.session_state.phase = "interview"
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # ==========================================
    # PHASE 3: INTERVIEW UI
    # ==========================================
    elif st.session_state.phase == "interview":
        st.title("🎙️ Admissions Interview")
        
        for msg in st.session_state.chat_display:
            with st.chat_message(msg[0]):
                st.markdown(msg[1])
                if len(msg) == 3 and msg[2]: st.audio(msg[2])

        if "last_processed_audio" not in st.session_state: 
            st.session_state.last_processed_audio = None
            
        if "is_processing" not in st.session_state:
            st.session_state.is_processing = False

        audio_input = st.audio_input("🎤 Speak (Optional)", key=f"mic_{len(st.session_state.chat_display)}", disabled=st.session_state.is_processing)
        text_input = st.chat_input("Type response...", disabled=st.session_state.is_processing)

        user_input = text_input
        if audio_input and audio_input != st.session_state.last_processed_audio:
            with st.spinner("Transcribing..."):
                user_input = st.session_state.audio_processor.transcribe_audio(audio_input.getvalue())
                st.session_state.last_processed_audio = audio_input

        if user_input and not st.session_state.is_processing:
            st.session_state.is_processing = True 
            
            st.session_state.chat_display.append(("user", user_input))
            st.session_state.audit_logs.append({"icon": "👤", "label": "User", "content": user_input, "is_json": False, "time": time.strftime("%H:%M:%S")})

            with st.chat_message("user"):
                st.markdown(user_input)

            with st.spinner("Analyzing..."):
                res = st.session_state.interview_engine.generate_response(user_input)
                ai_text = res["question"]
                ai_audio = st.session_state.audio_processor.generate_audio(ai_text)
                
                st.session_state.audit_logs.append({"icon": "🧠", "label": "AI Reasoning", "content": {"eval": res.get("evaluation")}, "is_json": True, "time": time.strftime("%H:%M:%S")})
                st.session_state.chat_display.append(("assistant", ai_text, ai_audio))
                
                st.session_state.db.sync_to_db(st.session_state.candidate_id, st.session_state.chat_display, st.session_state.audit_logs)

                # Unlock UI for the next turn
                st.session_state.is_processing = False 

                if res.get("is_complete"):
                    st.session_state.phase = "evaluation"
                st.rerun()

    # ==========================================
    # PHASE 4: EVALUATION
    # ==========================================
    elif st.session_state.phase == "evaluation":
        st.title("⚖️ Status Update")
        with st.spinner("Consolidating reports..."):
            hist = st.session_state.interview_engine.get_interview_data_for_evaluation()
            evaluator = EvaluationEngine(st.session_state.transcript_report, hist, st.session_state.user_data)
            
            if "final_verdict" not in st.session_state:
                st.session_state.final_verdict = evaluator.generate_final_scorecard()
                st.session_state.applicant_letter = evaluator.generate_applicant_message(st.session_state.final_verdict)
                st.session_state.audit_logs.append({"icon": "🏛️", "label": "Verdict", "content": st.session_state.final_verdict, "is_json": True, "time": time.strftime("%H:%M:%S")})
                
                # Generate the PDF to save to DB
                pdf_bytes, c_id = generate_evaluation_pdf(st.session_state.user_data, st.session_state.final_verdict, st.session_state.audit_logs)
                
                # --- DB SYNC: Save Verdict AND PDF ---
                st.session_state.db.update_final_verdict(st.session_state.candidate_id, st.session_state.final_verdict, st.session_state.audit_logs, pdf_bytes)

        decision = st.session_state.final_verdict.get("overall_recommendation", "Error")
        
        if decision == "Admit":
            st.success(f"**Decision: {decision}** 🎉")
            st.balloons()
        elif decision == "Conditional Admission":
            st.warning(f"**Decision: {decision}** ⚠️")
        else:
            st.error(f"**Decision: {decision}** 🛑")
            
        st.write("---") # Visual divider

        with st.container(border=True):
            st.subheader("Official Correspondence")
            st.write(st.session_state.applicant_letter)
            
        st.write("")
        if st.button("Log Out & Finish", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # ==========================================
    # EDGE CASE 1: ALREADY COMPLETED
    # ==========================================
    elif st.session_state.phase == "completed":
        st.title("🏛️ Application Complete")
        st.info("You have already completed the admissions process for this cycle.")
        
        verdict = st.session_state.saved_verdict
        decision = verdict.get("overall_recommendation", "Unknown")
        
        if decision == "Admit":
            st.success(f"**Final Status: {decision}** 🎉")
        elif decision == "Conditional Admission":
            st.warning(f"**Final Status: {decision}** ⚠️")
        else:
            st.error(f"**Final Status: {decision}** 🛑")
            
        st.markdown("Your official evaluation is on file with the admissions office. You may log out.")

    # ==========================================
    # EDGE CASE 2: ABANDONED MIDWAY
    # ==========================================
    elif st.session_state.phase == "abandoned":
        st.title("🛑 Application Terminated")
        st.error("**Status: Automatic Rejection**")
        st.markdown("""
        Our records indicate that you started the Cognitive Assessment but **abandoned the session midway** (by refreshing the page, closing the browser, or losing connection). 
        
        As per the consent agreement signed at the start of the application, **sessions cannot be resumed or retaken.** Your application has been flagged and rejected.
        """)