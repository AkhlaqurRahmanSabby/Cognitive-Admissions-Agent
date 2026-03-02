import streamlit as st
import json

def render_admin_portal():
    st.title("🏛️ Admissions Command Center")
    st.markdown("Review AI-prepared dossiers and make final admissions decisions.")

    # Fetch all records
    records = st.session_state.db.get_all_candidates()
    
    if not records:
        st.info("No applications found in the system.")
        return

    # --- TOP LEVEL DASHBOARD METRICS ---
    PROGRAM_CAPACITY = 50 
    
    evaluated_count = len([r for r in records if r['status'] == 'evaluated']) # Pending Admin review
    admitted_count = len([r for r in records if r['status'] == 'admit'])
    rejected_count = len([r for r in records if r['status'] == 'reject'])
    in_progress = len([r for r in records if r['status'] in ['interviewing', 'pending_references']])
    
    seats_left = PROGRAM_CAPACITY - admitted_count

    st.subheader("Cohort Capacity & Workflow")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Decisions Pending", evaluated_count, delta="Action Required", delta_color="inverse")
    c2.metric("Seats Remaining", seats_left, f"Out of {PROGRAM_CAPACITY}")
    c3.metric("Total Admitted", admitted_count)
    c4.metric("In Progress (AI Stage)", in_progress)
    
    st.divider()

    # --- CANDIDATE LIST ---
    st.subheader("Applicant Dossiers")
    for r in records:
        status = r['status'].upper()
        
        # Determine status color & icon
        if status == "EVALUATED":
            status_icon, color = "🟡", "orange" # Ready for Admin
        elif status == "ADMIT":
            status_icon, color = "🟢", "green"
        elif status == "REJECT":
            status_icon, color = "🔴", "red"
        elif status == "CONDITIONAL":
            status_icon, color = "🔵", "blue"
        elif status == "PENDING_REFERENCES":
            status_icon, color = "⏳", "gray"
        else:
            status_icon, color = "⚪", "gray"
        
        # Parse user data safely
        user_data = {}
        if r.get('user_data_json'):
            try: user_data = json.loads(r['user_data_json'])
            except: pass

        with st.expander(f"{status_icon} {r['first_name']} {r['last_name']} — {r['program']} (Status: {status})"):
            st.caption(f"**App ID:** `{r['candidate_id']}` | **Applied:** {r['created_at']} | **User:** `{r['username']}`")
            
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📄 Profile & Transcript", "💬 Interview", "🧠 AI Logs", "🤝 References", "⚖️ Executive Dossier & Decision"])
            
            # --- TAB 1: PROFILE & TRANSCRIPT ---
            with tab1:
                colA, colB = st.columns(2)
                with colA:
                    st.markdown(f"**Citizenship:** {user_data.get('citizenship', 'N/A')}")
                    st.markdown(f"**Previous Degree:** {user_data.get('previous_degree', 'N/A')}")
                with colB:
                    st.markdown(f"**Alma Mater:** {user_data.get('alma_mater', 'N/A')}")
                    st.markdown(f"**IELTS Requirement:** {'Waived' if user_data.get('is_exempt') else 'Required'}")
                st.divider()
                st.subheader("Registrar Analysis")
                if r['transcript_report']: st.info(r['transcript_report'])
                else: st.write("No transcript report generated yet.")

            # --- TAB 2: INTERVIEW CHAT ---
            with tab2:
                if r['chat_history_json']:
                    history = json.loads(r['chat_history_json'])
                    with st.container(height=400):
                        for msg in history:
                            with st.chat_message(msg['role']): st.write(msg['content'])
                else: st.write("No chat history available.")

            # --- TAB 3: SYSTEM AUDIT LOGS ---
            with tab3:
                if r['audit_logs_json']:
                    logs = json.loads(r['audit_logs_json'])
                    for log in logs: 
                        with st.expander(f"{log['icon']} {log.get('time', '')} - {log['label']}"):
                            if log['is_json'] and isinstance(log['content'], dict):
                                for key, value in log['content'].items():
                                    st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                            else: st.write(log['content'])

            # --- TAB 4: REFERENCE CHECKS ---
            with tab4:
                references = st.session_state.db.get_references_by_candidate(r['candidate_id'])
                if references:
                    for idx, ref in enumerate(references):
                        status_color = "🟢" if ref['status'] == 'completed' else "⏳"
                        with st.expander(f"{status_color} Reference {idx+1}: {ref['referee_name']} ({ref['referee_designation']})"):
                            st.write(f"**Contact:** {ref['referee_email']}")
                            if ref['chat_history_json']:
                                ref_history = json.loads(ref['chat_history_json'])
                                st.markdown("##### AI Verification Chat")
                                with st.container(height=300):
                                    for msg in ref_history:
                                        with st.chat_message(msg['role']): st.write(msg['content'])
                            elif ref['status'] == 'pending':
                                st.info("Invitation sent. Waiting for referee.")
                else: st.write("No references requested yet.")

            # --- TAB 5: THE NEW EXECUTIVE DOSSIER & FINAL DECISION ---
            with tab5:
                if status in ["EVALUATED", "ADMIT", "REJECT", "CONDITIONAL"] and r['final_verdict_json']:
                    verdict = json.loads(r['final_verdict_json'])
                    
                    st.subheader("AI Committee Executive Dossier")
                    st.info(f"**AI Recommendation:** {verdict.get('overall_recommendation', 'N/A')}")
                    
                    # 1. The Full Picture (Chair Summary)
                    st.markdown("#### 🏛️ Department Chair Summary")
                    st.write(verdict.get("executive_summary", "Detailed summary pending new Evaluation Engine format."))
                    
                    # 2. Strengths & Weaknesses
                    colS, colW = st.columns(2)
                    with colS:
                        st.markdown("#### 📈 Key Strengths")
                        for s in verdict.get("strengths", ["Data pending format update."]): st.markdown(f"- {s}")
                    with colW:
                        st.markdown("#### 📉 Areas of Concern")
                        for w in verdict.get("weaknesses", ["Data pending format update."]): st.markdown(f"- {w}")
                    
                    st.divider()
                    
                    # 3. The 5 Specialists
                    st.markdown("#### 🧠 Specialist Sub-Reports")
                    specialists = verdict.get("specialists", {
                        "Academic Auditor": "Pending new engine format.",
                        "Technical SME": "Pending new engine format.",
                        "Behavioral Psychologist": "Pending new engine format.",
                        "Program Alignment Director": "Pending new engine format.",
                        "Reference Cross-Checker": "Pending new engine format."
                    })
                    for spec_name, spec_notes in specialists.items():
                        with st.expander(f"Report: {spec_name}"):
                            st.write(spec_notes)
                    
                    st.divider()

                    # 4. OFFICIAL HUMAN OVERRIDE / FINAL DECISION
                    if status == "EVALUATED":
                        st.markdown("### ⚖️ Official Administrative Action")
                        st.markdown("Please review the dossier above. This action is final and will instantly update the student's portal.")
                        
                        btn1, btn2, btn3 = st.columns(3)
                        with btn1:
                            if st.button("✅ Admit Candidate", key=f"admit_{r['candidate_id']}", use_container_width=True, type="primary"):
                                st.session_state.db.update_admin_decision(r['candidate_id'], "admit")
                                st.rerun()
                        with btn2:
                            if st.button("⚠️ Conditional Admit", key=f"cond_{r['candidate_id']}", use_container_width=True):
                                st.session_state.db.update_admin_decision(r['candidate_id'], "conditional")
                                st.rerun()
                        with btn3:
                            if st.button("🛑 Reject Candidate", key=f"rej_{r['candidate_id']}", use_container_width=True):
                                st.session_state.db.update_admin_decision(r['candidate_id'], "reject")
                                st.rerun()
                    else:
                        st.success(f"### Final Administrative Decision Logged: {status}")
                
                elif status == "PENDING_REFERENCES":
                    st.warning("Dossier generation is paused pending completion of all reference checks.")