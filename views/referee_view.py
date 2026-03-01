import streamlit as st
import time
import json
from core.reference_engine import ReferenceEngine
from core.evaluation_engine import EvaluationEngine
from utils import generate_evaluation_pdf

def render_referee_portal():
    # ==========================================
    # PHASE 0: AUTHENTICATION
    # ==========================================
    if "referee_logged_in" not in st.session_state:
        st.session_state.referee_logged_in = False
        st.session_state.referee_email = None

    if not st.session_state.referee_logged_in:
        st.title("🤝 Official Reference Portal")
        st.markdown("Log in or register using your official institutional email address to view pending requests.")
        
        tab1, tab2 = st.tabs(["Log In", "Create Account"])
        
        with tab1:
            log_email = st.text_input("Official Email", key="log_ref_email").lower()
            log_pass = st.text_input("Password", type="password", key="log_ref_pass")
            if st.button("Log In", use_container_width=True):
                is_valid, msg = st.session_state.db.verify_referee_login(log_email, log_pass)
                if is_valid:
                    st.session_state.referee_logged_in = True
                    st.session_state.referee_email = log_email
                    st.session_state.referee_phase = "dashboard"
                    st.success(msg)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)
                    
        with tab2:
            reg_email = st.text_input("Official Email", key="reg_ref_email").lower()
            reg_pass = st.text_input("Choose Password", type="password", key="reg_ref_pass")
            if st.button("Create Account", use_container_width=True):
                success, msg = st.session_state.db.create_referee_account(reg_email, reg_pass)
                if success:
                    st.session_state.referee_logged_in = True
                    st.session_state.referee_email = reg_email
                    st.session_state.referee_phase = "dashboard"
                    st.success(msg)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(msg)
        return

    # Sidebar Logout
    st.sidebar.success(f"Secure Session: **{st.session_state.referee_email}**")
    if st.sidebar.button("Log Out"):
        st.session_state.clear()
        st.rerun()

    # ==========================================
    # PHASE 1: REFEREE DASHBOARD
    # ==========================================
    if st.session_state.get("referee_phase") == "dashboard":
        st.title("📬 Pending Reference Requests")
        st.markdown("Candidates who have requested your endorsement will appear below. You have 7 business days to complete these.")
        
        requests = st.session_state.db.get_references_by_email(st.session_state.referee_email)
        
        if not requests:
            st.info("You currently have no pending reference requests on file.")
        else:
            for req in requests:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.subheader(f"Candidate: {req['candidate_name']}")
                        st.caption(f"Program: {req['candidate_program']} | Status: {req['status'].upper()}")
                    with col2:
                        if req['status'] == 'pending':
                            if st.button("Start Evaluation", key=f"start_{req['id']}", type="primary"):
                                
                                # Package data for the ReferenceEngine
                                student_data = {
                                    "name": req['candidate_name'], 
                                    "degree": req['candidate_program'], 
                                    "transcript_report": req['transcript_report']
                                }
                                referee_data = {
                                    "name": req['referee_name'], 
                                    "designation": req['referee_designation']
                                }
                                
                                st.session_state.current_ref_id = req['id']
                                st.session_state.current_candidate_id = req['candidate_id'] # Save this for later!
                                st.session_state.ref_engine = ReferenceEngine(student_data, referee_data)
                                st.session_state.ref_chat = []
                                st.session_state.ref_processing = False
                                
                                # Start interview
                                init_res = st.session_state.ref_engine.start_interview()
                                st.session_state.ref_chat.append(("assistant", init_res.get("question", "Hello.")))
                                
                                st.session_state.referee_phase = "interview"
                                st.rerun()
                        else:
                            st.button("Completed", key=f"done_{req['id']}", disabled=True)

    # ==========================================
    # PHASE 2: THE DYNAMIC INTERVIEW
    # ==========================================
    elif st.session_state.get("referee_phase") == "interview":
        st.title("⚖️ Candidate Endorsement Interview")
        
        for msg in st.session_state.ref_chat:
            with st.chat_message(msg[0]):
                st.markdown(msg[1])

        user_input = st.chat_input("Type your detailed response here...", disabled=st.session_state.ref_processing)
        
        if user_input and not st.session_state.ref_processing:
            st.session_state.ref_processing = True
            st.session_state.ref_chat.append(("user", user_input))
            
            with st.chat_message("user"):
                st.markdown(user_input)
                
            with st.spinner("Analyzing response and verifying claims..."):
                history_to_pass = st.session_state.ref_chat[:-1] 
                res = st.session_state.ref_engine.generate_response(history_to_pass, user_input)
                
                st.session_state.ref_chat.append(("assistant", res["question"]))
                st.session_state.ref_processing = False
                
                if res.get("is_complete"):
                    # 1. Save the Reference
                    st.session_state.db.complete_reference(st.session_state.current_ref_id, st.session_state.ref_chat)
                    
                    # 2. THE DOMINO EFFECT: Check if we should trigger the final evaluation
                    is_ready, ref_logs = st.session_state.db.check_references_completed(st.session_state.current_candidate_id)
                    
                    if is_ready:
                        # Fetch the candidate's full profile silently
                        c_data = st.session_state.db.get_candidate_for_evaluation(st.session_state.current_candidate_id)
                        user_data = json.loads(c_data['user_data_json'])
                        chat_hist = json.loads(c_data['chat_history_json'])
                        audit_logs = json.loads(c_data['audit_logs_json'])
                        
                        # Spin up the Evaluation Engine
                        evaluator = EvaluationEngine(c_data['transcript_report'], chat_hist, user_data, ref_logs)
                        final_verdict = evaluator.generate_final_scorecard()
                        
                        # Log it
                        audit_logs.append({"icon": "🏛️", "label": "Final Verdict", "content": final_verdict, "is_json": True, "time": time.strftime("%H:%M:%S")})
                        
                        # Generate the PDF
                        pdf_bytes, _ = generate_evaluation_pdf(
                            user_data, 
                            final_verdict, 
                            audit_logs,
                            transcript_bytes=c_data.get('transcript_blob'),
                            ielts_bytes=c_data.get('ielts_blob')
                        )
                        
                        # Save everything to the database!
                        st.session_state.db.update_final_verdict(st.session_state.current_candidate_id, final_verdict, audit_logs, pdf_bytes)

                    st.session_state.referee_phase = "completed"
                st.rerun()

    # ==========================================
    # PHASE 3: COMPLETION
    # ==========================================
    elif st.session_state.get("referee_phase") == "completed":
        st.title("✅ Endorsement Submitted")
        st.success("Thank you for your time. Your verification has been securely transmitted to the Graduate Admissions Committee.")
        
        if st.button("Return to Dashboard", use_container_width=True):
            st.session_state.referee_phase = "dashboard"
            st.rerun()