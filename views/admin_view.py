import streamlit as st
import json

def render_admin_portal():
    st.title("🏛️ Institutional Admissions Command Center")
    st.markdown("Review applicant data, AI reasoning, and final evaluations.")

    # Fetch all records from the Database
    records = st.session_state.db.get_all_candidates()
    
    if not records:
        st.info("No applications found in the system. Waiting for candidates to apply.")
        return

    # --- TOP LEVEL METRICS ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Applications", len(records))
    c2.metric("Evaluated (Complete)", len([r for r in records if r['status'] == 'evaluated']))
    c3.metric("In Progress", len([r for r in records if r['status'] == 'interviewing']))
    
    st.divider()

    # --- CANDIDATE LIST ---
    for r in records:
        # Determine status color
        status = r['status'].upper()
        status_icon = "🟢" if status == "EVALUATED" else "🟡"
        
        with st.expander(f"{status_icon} {r['first_name']} {r['last_name']} — {r['program']}"):
            
            # Basic Info Header
            st.caption(f"**Application ID:** `{r['candidate_id']}` | **Applied:** {r['created_at']} | **User:** `{r['username']}`")
            
            # Create Tabs for deep-diving into the student profile
            tab1, tab2, tab3, tab4 = st.tabs([
                "📄 Overview & Transcript", 
                "💬 Interview Chat", 
                "🧠 AI Audit Logs", 
                "⚖️ Final Verdict & PDF"
            ])
            
            # --- TAB 1: TRANSCRIPT REPORT ---
            with tab1:
                st.subheader("Registrar Analysis")
                if r['transcript_report']:
                    st.info(r['transcript_report'])
                else:
                    st.write("No transcript report generated yet.")

            # --- TAB 2: INTERVIEW CHAT ---
            with tab2:
                st.subheader("Raw Interview Transcript")
                if r['chat_history_json']:
                    history = json.loads(r['chat_history_json'])
                    if not history:
                        st.write("Interview has not started yet.")
                    for msg in history:
                        with st.chat_message(msg['role']):
                            st.write(msg['content'])
                else:
                    st.write("No chat history available.")

            # --- TAB 3: SYSTEM AUDIT LOGS (The Old Sidebar) ---
            with tab3:
                st.subheader("System Timeline & Internal Reasoning")
                if r['audit_logs_json']:
                    logs = json.loads(r['audit_logs_json'])
                    if not logs:
                        st.write("No logs recorded.")
                    for log in logs: # Chronological order
                        with st.container(border=True):
                            st.markdown(f"**{log['icon']} {log['label']}** `({log['time']})`")
                            if log['is_json']:
                                st.json(log['content'])
                            else:
                                st.write(log['content'])
                else:
                    st.write("No audit logs available.")

            # --- TAB 4: FINAL EVALUATION & PDF DOWNLOAD ---
            with tab4:
                st.subheader("Final Committee Decision")
                if r['final_verdict_json']:
                    verdict = json.loads(r['final_verdict_json'])
                    
                    # High-level metrics
                    col1, col2 = st.columns(2)
                    col1.metric("Overall Score", f"{verdict.get('overall_score', 0)}/10")
                    col2.metric("Recommendation", verdict.get('overall_recommendation', 'N/A'))
                    
                    # Full JSON
                    st.json(verdict)
                    
                    # PDF Download Button (Extracting BLOB from DB)
                    if r.get('pdf_blob'):
                        st.divider()
                        safe_last_name = r.get('last_name', 'Candidate')
                        file_name = f"{r['candidate_id']}_{safe_last_name}_Evaluation.pdf"
                        
                        st.download_button(
                            label=f"📥 Download Official PDF Report ({safe_last_name})",
                            data=r['pdf_blob'],
                            file_name=file_name,
                            mime="application/pdf",
                            key=f"dl_{r['candidate_id']}",
                            use_container_width=True
                        )
                    else:
                        st.warning("PDF report not found in the database.")
                        
                else:
                    st.warning("Applicant has not yet completed the evaluation phase.")