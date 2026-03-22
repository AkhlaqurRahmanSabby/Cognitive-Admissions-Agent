# 🎓 Cognitive Admissions Agent

[![Live Demo](https://img.shields.io/badge/Live_Demo-Available_Now-success?style=for-the-badge&logo=streamlit)](https://cognitive-admissions-agent.streamlit.app/)
&nbsp;&nbsp;&nbsp;&nbsp;
[![YouTube Demo](https://img.shields.io/badge/Video_Demo-Watch_on_YouTube-red?style=for-the-badge&logo=youtube)](https://youtu.be/L49TjL9gMzU?si=sA5cSR8DQAKX4egC)

University admissions is a legacy batch-processing workflow constrained by human review capacity. This project rebuilds admissions as an AI-native system where applicants are evaluated through live cognitive interviews and automatically verified credentials rather than static applications. 

The prototype tests whether AI can take on real cognitive and operational responsibility, conducting structured interviews, probing reasoning in real time, and producing credible, verifiable evaluation reports, while humans safely retain responsibility for final judgment.

---

## Human / AI Responsibility Boundary

### **Capability Unlock**

Admissions officers can now verify baseline competence and detect inconsistencies between a candidate’s transcript, interview responses, and referee testimony across thousands of applicants, a process previously limited by hours of manual review per file.

### **Critical Human Decision**

The final admission decision must remain human because it involves cohort-level tradeoffs, balancing diversity of background, risk tolerance, and institutional strategy, that cannot be ethically or operationally delegated to an AI evaluating candidates in isolation.

While the system can assess individual readiness and surface risks, only a human administrator can determine whether a high-variance or non-traditional candidate aligns with the institution’s broader goals for a given year.

---

## The Architecture

This platform shifts away from "AI-as-a-wrapper" and utilizes a **Multi-Agent Evaluation Pipeline** combined with a robust **Human-in-the-Loop (HITL)** architecture.

### 1. The Interactive AI Interviewer (`InterviewEngine`)
Replaces the traditional Statement of Purpose (SOP) with a live, adaptive cognitive assessment. 
* **Core Topics:** Replaces rigid questionnaires with flexible, conversational topics (Intellectual Vision, Problem-Solving Logic, Research Adaptability, and Program Fit).
* **Dynamic Probing:** The AI actively prevents rehearsed answers by asking deep follow-up questions, presenting opposing viewpoints, and using real-world scenarios to test the applicant's true understanding.
* **Stable Interface:** Custom frontend locks prevent users from submitting multiple messages while the AI is thinking, ensuring a smooth and uninterrupted assessment.

### 2. The Multi-Agent Evaluation Pipeline (`EvaluationEngine`)
Once data is collected, a pipeline of isolated AI Specialists reviews the candidate's transcript, interview history, and professional reference checks.
* **Specialist Agents:** 5 distinct agents (Behavioral Psychologist, Program Alignment Director, Technical Subject Matter Expert (SME), Academic Auditor, and Reference Cross-Checker) independently score the candidate.
* **Clear Evidence:** To prevent AI errors and build trust, specialists must provide a `detailed_analysis` paragraph and extract a `direct_quote` directly from the candidate's interview transcript to justify their score.
* **The Department Chair:** A final synthesizer agent gathers the specialist sub-reports, simulates a committee debate, and builds a comprehensive JSON Executive Summary.

### 3. Human-in-the-Loop Command Center (Admin Portal)
AI does the heavy lifting of data extraction, cognitive assessment, and synthesis, but **humans make the final call.**
* Consolidates applicant demographics, Registrar transcript analysis, and the AI Executive Summary into a single dashboard.
* Human administrators review the clear evidence provided by the AI and issue binding `Admit`, `Conditional Admit`, or `Reject` overrides that instantly update the student's portal.

## Tech Stack
* **Frontend:** Streamlit (Python)
* **LLM Orchestration:** OpenAI API (`gpt-4o` for strict JSON adherence & logical routing)
* **Architecture:** Azure-ready — `ai_client.py` abstracts the LLM client, enabling a single environment variable switch (`USE_AZURE=true`) to migrate from public OpenAI to secure Azure OpenAI with zero changes to application logic.
* **Deployment:** Docker · Azure Container Registry · Azure App Service
* **Database:** SQLite with custom state-routing managers
* **Audio Processing:** OpenAI Whisper / Text-to-Speech

---

## Local Installation & Setup

Follow these steps to run the Cognitive Admissions Agent on your local machine.

### Prerequisites
* **Python 3.8+** installed on your system.
* An active **OpenAI API Key** (required for the LLM and audio processing).

### 1. Clone the Repository
Open your terminal and clone the repository to your local machine:
```bash
git clone https://github.com/AkhlaqurRahmanSabby/Cognitive-Admissions-Agent.git
cd Cognitive-Admissions-Agent
```

### 2. Install Dependencies
Install all required Python libraries:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
This application requires an OpenAI API key to function. 
1. Create a new file named `.env` in the root directory of the project.
2. Add your API key to the file:
```env
OPENAI_API_KEY="your-api-key-here"
```

### 4. Run the Application
Start the Streamlit server:
```bash
streamlit run app.py
```
*(Note: If your main entry file has a different name, replace `app.py` with the correct filename)*

---

## How to Test the Full Flow Locally

To experience the full Human-in-the-Loop architecture, we recommend simulating a complete application cycle:

1. **The Applicant:** Select the "Student Applicant" view. Create a test account, upload a sample PDF transcript, and complete the live AI interview. At the end, submit a dummy reference email.
2. **The Referee:** Log out and switch to the "Referee" view. Create an account using the dummy email you just provided. Complete the AI reference verification chat.
3. **The Administrator:** Log out and switch to the "School Admin" view.

### Admin Access (Local Demo Only)

> **Demo Admin Password:** `demo_admin`
>
> This static password is provided solely for demonstration.  
> In a production deployment, this would be replaced with secure authentication and role-based access control.

You will now see the fully generated Executive Summary, complete with specialist sub-reports, verifiable quotes, and the final Admit/Reject override buttons.

## Project Structure

* `/core/` - Contains the foundational AI engines (`interview_engine.py`, `evaluation_engine.py`, `reference_engine.py`).
* `/views/` - Contains the Streamlit UI files for the three distinct portals (`student_view.py`, `referee_view.py`, `admin_view.py`).
* `/utils/` - Helper functions for PDF processing, database management (`db_manager.py`), and audio handling.
* `app.py` - The main entry point and routing hub for the Streamlit application.
