import json
from .ai_client import client

class EvaluationEngine:
    def __init__(self, transcript_report, interview_history, user_data, reference_data=None):
        self.transcript_report = transcript_report
        self.interview_history = interview_history
        self.user_data = user_data
        self.reference_data = reference_data or [] # List of referee chat transcripts
        
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
                temperature=0.2 # Slight temperature increase to allow for nuanced debate
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"score": 0, "critique": f"Evaluation Error: {str(e)}", "stance": "Error"}

    # ==========================================
    # LAYER 1: THE FIVE SPECIALISTS
    # ==========================================
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

    def _evaluate_references(self):
        role = "You are the Reference Auditor. Your only job is to verify the candidate's claims against their professional endorsements."
        task = f"""
        Review the AI interview transcripts conducted with the candidate's professional/academic references.
        
        REFERENCE TRANSCRIPTS:
        {json.dumps(self.reference_data)}
        
        RUBRIC (Score 1-10):
        - 1-3: Referees expressed serious reservations, contradicted the candidate's claims, or could not speak to their abilities.
        - 4-7: Standard, positive references but lacking specific examples of elite performance.
        - 8-10: Glowing endorsements with highly specific, verified examples of the candidate solving complex problems.
        
        OUTPUT JSON: {{ "score": int, "critique": "1 sentence justification summarizing the consensus of all referees" }}
        """
        return self._call_llm(role, task)

    # ==========================================
    # LAYER 2: THE MULTI-AGENT COMMITTEE DEBATE
    # ==========================================
    def _agent_strict_professor(self, sub_scores):
        role = "You are the 'Strict Professor'. You are highly skeptical of candidates, especially those switching fields."
        task = f"""
        Review the candidate's background, interview, and preliminary specialist scores (which now include Reference Checks).
        BACKGROUND: {self.transcript_report}
        INTERVIEW: {json.dumps(self.interview_history)}
        SCORES: {json.dumps(sub_scores)}
        
        Your job is to find the FLAWS. Look closely at the 'references' score. Did the referees fail to back up the candidate's claims? If they are switching fields, point out their naive assumptions. Be ruthless but academic.
        
        OUTPUT JSON: {{ "stance": "A 2-sentence highly critical argument against admission." }}
        """
        return self._call_llm(role, task)

    def _agent_visionary_dean(self, sub_scores):
        role = "You are the 'Visionary Dean'. You look for potential, grit, and interdisciplinary advantages."
        task = f"""
        Review the candidate's background, interview, and preliminary specialist scores (which now include Reference Checks).
        BACKGROUND: {self.transcript_report}
        INTERVIEW: {json.dumps(self.interview_history)}
        SCORES: {json.dumps(sub_scores)}
        
        Your job is to find the HIDDEN POTENTIAL. Look closely at the 'references' score. Did the referees highlight exceptional grit or adaptability? Argue why they are worth taking a risk on.
        
        OUTPUT JSON: {{ "stance": "A 2-sentence highly supportive argument for admission, focusing on adaptability and unique perspective." }}
        """
        return self._call_llm(role, task)

    # ==========================================
    # LAYER 3: THE FINAL AGGREGATOR
    # ==========================================
    def generate_final_scorecard(self):
        """Orchestrates the specialists, the debate, and makes the final decision."""
        
        # 1. Gather Sub-Scores
        focus_eval = self._evaluate_motivation()
        traj_eval = self._evaluate_trajectory()
        tech_eval = self._evaluate_technical()
        trans_eval = self._evaluate_transcript()
        ref_eval = self._evaluate_references()
        
        sub_scores = {
            "motivation": focus_eval.get('score', 0),
            "trajectory": traj_eval.get('score', 0),
            "technical": tech_eval.get('score', 0),
            "transcript": trans_eval.get('score', 0),
            "references": ref_eval.get('score', 0)
        }
        
        avg_score = sum(sub_scores.values()) / 5.0

        # 2. Trigger the Committee Debate
        prof_critique = self._agent_strict_professor(sub_scores)
        dean_critique = self._agent_visionary_dean(sub_scores)

        # 3. The Final Decision (The "Committee Chair")
        role = "You are the Chair of Graduate Admissions. You must synthesize the specialist scores and the committee debate into a final decision."
        task = f"""
        You have received the data for {self.user_data.get('name')}.
        
        SPECIALIST SCORES (Average: {avg_score}/10):
        1. Motivation: {sub_scores['motivation']} - {focus_eval.get('critique')}
        2. Trajectory: {sub_scores['trajectory']} - {traj_eval.get('critique')}
        3. Technical: {sub_scores['technical']} - {tech_eval.get('critique')}
        4. Transcript: {sub_scores['transcript']} - {trans_eval.get('critique')}
        5. References: {sub_scores['references']} - {ref_eval.get('critique')}
        
        THE DEBATE:
        - Strict Professor's Argument: {prof_critique.get('stance')}
        - Visionary Dean's Argument: {dean_critique.get('stance')}
        
        DECISION RULES:
        - OVERALL AVERAGE < 5: "Reject"
        - ANY INDIVIDUAL SCORE <= 3: "Reject" (If References are 3 or below, it's an automatic fail).
        - If the candidate is switching fields (High Trajectory, Low Technical), and the Visionary Dean's argument is compelling: Override the technical gap and issue "Conditional Admission" with required bridge courses.
        - If the Strict Professor correctly identifies a fatal flaw (e.g., terrible references or zero technical skill): "Reject".
        - AVERAGE > 7.5 and no scores below 5: "Admit"

        OUTPUT JSON:
        {{
            "overall_recommendation": "Admit" | "Conditional Admission" | "Reject",
            "chair_reasoning": "A 1-sentence explanation of exactly why you sided with either the Professor or the Dean based on the rules.",
            "executive_summary": "A powerful 2-sentence summary weighing the candidate's profile.",
            "final_cognitive_score": {avg_score},
            "sub_scores": {json.dumps(sub_scores)},
            "committee_debate": {{
                "strict_professor_stance": {json.dumps(prof_critique.get('stance', ''))},
                "visionary_dean_stance": {json.dumps(dean_critique.get('stance', ''))}
            }},
            "required_prerequisites": ["List of courses", "or null if Admit/Reject"],
            "red_flags": "List any critical issues raised by the Strict Professor."
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