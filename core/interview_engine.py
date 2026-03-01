import json
import time
from ai_client import client

class InterviewEngine:
    def __init__(self, user_data, transcript_report):
        self.user_data = user_data
        self.transcript_report = transcript_report
        self.history = []
        
        # --- TIMING & SAFETY DEFAULTS ---
        self.start_time = None
        self.max_time_seconds = 600  # 10 Minutes hard limit
        self.absolute_max_turns = 10 # Failsafe to prevent infinite loops

        # Initial system prompt
        self.history.append(self._get_system_prompt())

    def _get_system_prompt(self):
            return {
                "role": "system",
                "content": f"""
                You are the Head of Admissions for a {self.user_data['degree']} program. 
                Candidate: {self.user_data['name']}.
                
                BACKGROUND DATA (Read this, but DO NOT mention it in your first question):
                "{self.transcript_report}"

                YOUR MISSION: Replace the Statement of Purpose (SOP). You must uncover their true motivation, evaluate if their trajectory makes sense, and test their technical readiness.

                THE EVALUATION RUBRIC (Follow strictly in order):
                1. "motivation_and_focus": Open the interview by asking what specific research area or problem they want to focus on and WHY. Do NOT assume their interest based on their past transcript. Let them state it freely.
                2. "trajectory_alignment": Compare their stated focus to their BACKGROUND DATA. 
                - If it is a PIVOT (e.g., they studied bioinformatics but now want to do pure NLP), challenge the pivot. Ask why they are switching and how they plan to bridge the knowledge gap.
                - If it ALIGNS, ask how their specific past coursework prepared them for this next leap.
                3. "technical_depth": Present a complex, real-world constraint or scenario related to the specific focus they just stated. Test if they actually understand the field they claim to be passionate about.
                4. "transcript_validation": Finally, ask a targeted question about their transcript (e.g., asking about a low grade or testing a high grade).

                RULES OF ENGAGEMENT:
                - Address ONE rubric item at a time. Do not move to the next until the current one is "completed" or "failed".
                - IF THEY ARE VAGUE OR EVASIVE: Push back. But if they fail to give a good answer after 3 attempts on the same topic, mark it "failed" and MOVE ON.
                - If all 4 rubric items are either "completed" or "failed", set "is_interview_complete" to true and give a polite sign-off.

                MANDATORY JSON OUTPUT FORMAT:
                {{
                    "internal_reasoning": "What is your assessment of their last answer? What rubric item are you evaluating?",
                    "rubric_state": {{
                        "motivation_and_focus": "pending" | "completed" | "failed",
                        "trajectory_alignment": "pending" | "completed" | "failed",
                        "technical_depth": "pending" | "completed" | "failed",
                        "transcript_validation": "pending" | "completed" | "failed"
                    }},
                    "question_to_candidate": "Your next conversational question. (Or your final goodbye if complete).",
                    "is_interview_complete": boolean
                }}
                """
            }
    

    def start_interview(self):
        """Kicks off the interview and the timer."""
        self.start_time = time.time()
        return self.generate_response(user_input=None)
    

    def generate_response(self, user_input=None):
        """Processes the turn, tracks time, and returns the AI's JSON output."""
        
        # 1. Enforce Hard Time Limit
        if self.start_time and (time.time() - self.start_time) > self.max_time_seconds:
            return self._force_end("Your 10-minute assessment window has closed. Thank you for your time.")

        # 2. Add user input if it exists
        if user_input:
            self.history.append({"role": "user", "content": user_input})

        # 3. Failsafe to prevent API looping costs
        user_turns = len([m for m in self.history if m['role'] == 'user'])
        if user_turns >= self.absolute_max_turns:
            return self._force_end(
                "We have reached the end of this session. The Admissions Committee will now review the responses provided thus far. "
                "Please wait while we generate your final evaluation."
            )

        # 4. Call the LLM
        try:
            response = client.chat.completions.create(
                model="gpt-4o", # 4o is required for strict JSON rubric tracking
                messages=self.history,
                response_format={"type": "json_object"},
                temperature=0.3 # Keep it analytical, not creative
            )
            
            # Parse the output
            ai_data = json.loads(response.choices[0].message.content)
            
            # Save the AI's full JSON response to history so it Remembers its Rubric State
            self.history.append({"role": "assistant", "content": json.dumps(ai_data)})
            
            return {
                "question": ai_data.get("question_to_candidate", "System error: no question generated."),
                "is_complete": ai_data.get("is_interview_complete", False),
                "evaluation": ai_data.get("internal_reasoning", "No evaluation provided."), # FIXED: Mapping the new key back to the old one
                "rubric_status": ai_data.get("rubric_state", {})
            }

        except Exception as e:
            return self._force_end(f"System latency error. Assessment paused. ({str(e)})")


    def _force_end(self, message):
        """Helper to gracefully crash/end the interview if constraints hit."""
        return {
            "question": message,
            "is_complete": True,
            "rubric_status": {"system_enforced_end": True}
        }


    def get_interview_data_for_evaluation(self):
        """
        Called after 'is_complete' is true. 
        Passes the entire structured history to the EvaluationEngine.
        """
        return self.history