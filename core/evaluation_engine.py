import json
from .ai_client import client

class EvaluationEngine:
    def __init__(self, transcript_report, interview_history, user_data):
        self.transcript_report = transcript_report
        self.interview_history = interview_history
        self.user_data = user_data
        
        # Extract the final rubric state from the interviewer to see what was actually completed
        self.final_interview_state = self._extract_final_state()


    def _extract_final_state(self):
        """Finds the last assistant message to see which items were marked 'completed' vs 'failed'."""
        for msg in reversed(self.interview_history):
            if msg['role'] == 'assistant':
                try:
                    data = json.loads(msg['content'])
                    if "rubric_state" in data:
                        return data["rubric_state"]
                except:
                    continue
        return {}


    def _call_llm(self, role_prompt, task_prompt):
        """Helper method to keep the LLM calls clean and DRY."""
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": role_prompt},
                    {"role": "user", "content": task_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0 # strict grading
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"score": 0, "critique": f"Evaluation Error: {str(e)}"}


    # --- LAYER 1: THE FOUR SPECIALIST EVALUATORS ---

    def _evaluate_motivation(self):
        role = "You are the Director of Research Admissions. Your only job is to evaluate 'Motivation & Focus'."
        task = f"""
        Review this interview history.
        INTERVIEW STATUS FOR THIS ITEM: {self.final_interview_state.get('motivation_and_focus', 'unknown')}
        
        RUBRIC (Score 1-10):
        - 1-3: Vague, generic ("I want to learn more"), or refused to answer.
        - 4-7: Named a specific field, but lacked a compelling 'Why'.
        - 8-10: Named a highly specific sub-field or problem and articulated a clear, profound motivation.
        
        HISTORY: {json.dumps(self.interview_history)}
        
        OUTPUT JSON: {{ "score": int, "critique": "1 sentence justification" }}
        """
        return self._call_llm(role, task)


    def _evaluate_trajectory(self):
        role = "You are the Head of Academic Advising. Your only job is to evaluate 'Trajectory Alignment'."
        task = f"""
        Review this interview history against the candidate's background.
        BACKGROUND: {self.transcript_report}
        INTERVIEW STATUS FOR THIS ITEM: {self.final_interview_state.get('trajectory_alignment', 'unknown')}
        
        RUBRIC (Score 1-10):
        - 1-3: Unexplained pivot, or passive reliance on the school ("I'll just take your classes").
        - 4-7: Logical progression, but surface-level connections to past work.
        - 8-10: Brilliant synthesis. They proved how their past (even if a different field) creates a unique advantage for their future.
        
        HISTORY: {json.dumps(self.interview_history)}
        
        OUTPUT JSON: {{ "score": int, "critique": "1 sentence justification" }}
        """
        return self._call_llm(role, task)


    def _evaluate_technical(self):
        role = "You are a Tenured Professor. Your only job is to evaluate 'Technical & Methodological Depth'."
        task = f"""
        Review this interview history. Look for the 'stress test' question.
        INTERVIEW STATUS FOR THIS ITEM: {self.final_interview_state.get('technical_depth', 'unknown')}
        
        RUBRIC (Score 1-10):
        - 1-3: Surrendered ("I don't know") or gave buzzwords without substance.
        - 4-7: Solved the problem using standard, textbook answers.
        - 8-10: Used 'First-Principles Reasoning'. Broke the complex constraint down into foundational logic to find a solution.
        
        HISTORY: {json.dumps(self.interview_history)}
        
        OUTPUT JSON: {{ "score": int, "critique": "1 sentence justification" }}
        """
        return self._call_llm(role, task)


    def _evaluate_transcript(self):
        role = "You are the Admissions Auditor. Your only job is to evaluate 'Transcript Validation'."
        task = f"""
        Review this interview history alongside their transcript.
        BACKGROUND: {self.transcript_report}
        INTERVIEW STATUS FOR THIS ITEM: {self.final_interview_state.get('transcript_validation', 'unknown')}
        
        RUBRIC (Score 1-10):
        - 1-3: Could not explain a grade, or gave generic "I studied hard" answers.
        - 4-7: Adequately explained a class project or challenge.
        - 8-10: Provided deep, verifiable evidence of their learning strategy (e.g., active recall, building from scratch) that matches their high grades.
        
        HISTORY: {json.dumps(self.interview_history)}
        
        OUTPUT JSON: {{ "score": int, "critique": "1 sentence justification" }}
        """
        return self._call_llm(role, task)


    # --- LAYER 2: THE FINAL AGGREGATOR ---

    def generate_final_scorecard(self):
        """Orchestrates the 4 evaluators and makes the final admissions decision."""
        
        # 1. Gather Sub-Scores
        focus_eval = self._evaluate_motivation()
        traj_eval = self._evaluate_trajectory()
        tech_eval = self._evaluate_technical()
        trans_eval = self._evaluate_transcript()
        
        # Calculate raw average
        total_score = sum(
            [focus_eval.get('score', 0), traj_eval.get('score', 0), tech_eval.get('score', 0), trans_eval.get('score', 0)]
        )
        avg_score = total_score / 4.0

        # 2. The Final Decision (The "Dean")
        role = "You are the Dean of Graduate Admissions. Make the final high-stakes decision."
        task = f"""
        You have received the reports from your 4 specialists.
        
        1. Motivation Score: {focus_eval.get('score')} - {focus_eval.get('critique')}
        2. Trajectory Score: {traj_eval.get('score')} - {traj_eval.get('critique')}
        3. Technical Score: {tech_eval.get('score')} - {tech_eval.get('critique')}
        4. Transcript Score: {trans_eval.get('score')} - {trans_eval.get('critique')}
        
        Average Cognitive Score: {avg_score}/10
        
        DECISION RULES:
        - OVERALL AVERAGE < 5: "Reject"
        - ANY INDIVIDUAL SCORE <= 3: "Reject" (No weak links allowed in elite programs).
        - AVERAGE 5 to 7.5, OR Trajectory is low due to a pivot but Technical is high: "Conditional Admission" (Must assign bridge courses).
        - AVERAGE > 7.5 and no scores below 5: "Admit"

        OUTPUT JSON:
        {{
            "overall_recommendation": "Admit" | "Conditional Admission" | "Reject",
            "executive_summary": "A powerful 2-sentence summary of the candidate's cognitive profile based on the 4 critiques.",
            "final_cognitive_score": {avg_score},
            "sub_scores": {{
                "motivation": {focus_eval.get('score')},
                "trajectory": {traj_eval.get('score')},
                "technical": {tech_eval.get('score')},
                "transcript": {trans_eval.get('score')}
            }},
            "required_prerequisites": ["List of courses", "or null if Admit/Reject"],
            "red_flags": "List any scores under 4 or 'system_enforced_end' warnings, or null."
        }}
        """
        
        return self._call_llm(role, task)
    

    def generate_applicant_message(self, final_verdict):
            """
            Translates the internal JSON verdict into a clean, 
            concise paragraph for the applicant UI.
            """
            decision = final_verdict.get("overall_recommendation")
            summary = final_verdict.get("executive_summary")
            
            # Accessing user_data from 'self'
            candidate_name = self.user_data.get('first_name', 'Applicant') 
            
            role = "You are a Professional Admissions Counselor and Career Coach."
            task = f"""
            Based on the following internal committee decision, write a 3-sentence message to {candidate_name}.
            
            INTERNAL DECISION: {decision}
            COMMITTEE SUMMARY: {summary}
            
            STRICT FORMATTING RULES:
            1. DO NOT include "Dear [Name]", "Sincerely", or any sign-offs.
            2. DO NOT include headers or subject lines.
            3. START the message directly by addressing {candidate_name}.
            4. ONLY return the plain text paragraph.
            
            CONTENT RULES:
            - If REJECTED: Be professional and encouraging. Do not mention specific scores. Mention 'areas for further technical development'.
            - If ADMITTED: Be celebratory and welcoming.
            - If CONDITIONAL: Explain they have potential but need to complete specific bridges.
            - Tone: Sophisticated, empathetic, and academic.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": role},
                    {"role": "user", "content": task}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content