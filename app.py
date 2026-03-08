import streamlit as st
from views.student_view import render_student_portal
from views.admin_view import render_admin_portal
from views.referee_view import render_referee_portal
from utils import DatabaseManager, AudioProcessor

st.set_page_config(page_title="Cognitive Admissions Agent", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")


# --- GLOBAL SESSION STATE INITIALIZATION ---
# We initialize the Database and Audio Processor here so they persist across all views
if "db" not in st.session_state:
    st.session_state.db = DatabaseManager()
if "audio_processor" not in st.session_state:
    st.session_state.audio_processor = AudioProcessor()

# Initialize core student variables just in case they haven't been set
if "phase" not in st.session_state:
    st.session_state.phase = "intake"
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []
if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = []

# ==========================================
# MASTER ROUTER & ACCESS CONTROL
# ==========================================
with st.sidebar:
    with st.expander("🔐 Portal Access", expanded=False):
        st.markdown("Select your role to route to the correct interface.")
        
        user_role = st.radio("Select View:", ["Student Applicant", "Referee", "School Admin"])
        
        st.divider()
        
        # --- ADMIN SECURITY GATE ---
        if user_role == "School Admin":
            pwd = st.text_input("Admin Password", type="password", help="Hint: demo_admin")
            if pwd != "demo_admin":
                st.warning("🔒 Please enter the correct admin password to access the Command Center.")
                st.stop() # Stops the rest of the app from loading until password is correct
            else:
                st.success("Access Granted.")

# ==========================================
# VIEW DISPATCHER
# ==========================================
# Based on the sidebar selection, render the correct isolated file
if user_role == "Student Applicant":
    render_student_portal()

elif user_role == "Referee":
    render_referee_portal()

elif user_role == "School Admin":
    render_admin_portal()