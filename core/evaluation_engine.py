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
        Review this interview history. Look specifically for how the candidate articulates their driving thesis.
        INTERVIEW STATUS FOR THIS ITEM: {self.final_interview_state.get('motivation_and_focus', 'unknown')}
        
        RUBRIC (Score 1-10):
        - 1-3: Vague, generic ("I want to learn more"), or refused to answer.
        - 4-7: Named a specific field, but lacked a compelling 'Why'.
        - 8-10: Named a highly specific sub-field or problem and articulated a clear, profound motivation.
        
        HISTORY: {json.dumps(self.interview_history)}
        
        OUTPUT JSON: 
        {{ 
            "score": int, 
            "detailed_analysis": "A robust 4-5 sentence paragraph evaluating their motivation.",
            "direct_quote": "Extract 1 exact, verbatim quote from the candidate that proves your score."
        }}
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
        - 8-10: Brilliant synthesis. They proved how their past creates a unique advantage for their future.
        
        HISTORY: {json.dumps(self.interview_history)}
        
        OUTPUT JSON: 
        {{ 
            "score": int, 
            "detailed_analysis": "A robust 4-5 sentence paragraph evaluating their trajectory and fit.",
            "direct_quote": "Extract 1 exact, verbatim quote from the candidate that proves your score."
        }}
        """
        return self._call_llm(role, task)

    def _evaluate_technical(self):
        role = "You are a Tenured Professor. Your only job is to evaluate 'Technical & Methodological Depth'."
        task = f"""
        Review this interview history. Look for the 'stress test' or scenario question.
        INTERVIEW STATUS FOR THIS ITEM: {self.final_interview_state.get('technical_depth', 'unknown')}
        
        RUBRIC (Score 1-10):
        - 1-3: Surrendered ("I don't know") or gave buzzwords without substance.
        - 4-7: Solved the problem using standard, textbook answers.
        - 8-10: Used 'First-Principles Reasoning'. Broke the complex constraint down into foundational logic to find a solution.
        
        HISTORY: {json.dumps(self.interview_history)}
        
        OUTPUT JSON: 
        {{ 
            "score": int, 
            "detailed_analysis": "A robust 4-5 sentence paragraph evaluating their technical depth.",
            "direct_quote": "Extract 1 exact, verbatim quote from the candidate demonstrating their reasoning."
        }}
        """
        return self._call_llm(role, task)

    def _evaluate_transcript(self):
        role = "You are the Admissions Auditor. Your only job is to evaluate 'Transcript Validation'."
        task = f"""
        Review this interview history alongside their transcript. Look for discussions of specific grades or gaps.
        BACKGROUND: {self.transcript_report}
        INTERVIEW STATUS FOR THIS ITEM: {self.final_interview_state.get('transcript_validation', 'unknown')}
        
        RUBRIC (Score 1-10):
        - 1-3: Could not explain a grade, or gave generic "I studied hard" answers.
        - 4-7: Adequately explained a class project or challenge.
        - 8-10: Provided deep, verifiable evidence of their learning strategy that matches their high grades.
        
        HISTORY: {json.dumps(self.interview_history)}
        
        OUTPUT JSON: 
        {{ 
            "score": int, 
            "detailed_analysis": "A robust 4-5 sentence paragraph evaluating their academic foundation.",
            "direct_quote": "Extract 1 exact, verbatim quote from the candidate proving their claims."
        }}
        """
        return self._call_llm(role, task)

    def _evaluate_references(self):
        role = "You are the Reference Auditor. Your only job is to verify candidate claims against professional endorsements."
        task = f"""
        Review the AI interview transcripts conducted with the candidate's professional/academic references.
        
        REFERENCE TRANSCRIPTS:
        {json.dumps(self.reference_data)}
        
        RUBRIC (Score 1-10):
        - 1-3: Referees expressed serious reservations, contradicted claims, or could not speak to their abilities.
        - 4-7: Standard, positive references but lacking specific examples of elite performance.
        - 8-10: Glowing endorsements with highly specific, verified examples of the candidate solving complex problems.
        
        OUTPUT JSON: 
        {{ 
            "score": int, 
            "detailed_analysis": "A robust 3-4 sentence paragraph summarizing the consensus and specifics of all referees.",
            "direct_quote": "Extract 1 exact, verbatim quote from one of the referees that best represents the consensus."
        }}
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
        
        # 1. Gather Sub-Scores & Verifiable Receipts
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
        scores_list = list(sub_scores.values())
        max_disagreement = max(scores_list) - min(scores_list)

        # Base confidence is 100%. For every 1 point of disagreement between the highest and lowest specialist, subtract 5%.
        # Example: If Technical is 3 and Motivation is 9, delta is 6. Confidence drops by 30% to 70%.
        calculated_confidence = 100 - (max_disagreement * 5)

        # 2. Trigger the Committee Debate
        prof_critique = self._agent_strict_professor(sub_scores)
        dean_critique = self._agent_visionary_dean(sub_scores)

        # 3. The Final Decision (The "Department Chair")
        role = "You are the Chair of Graduate Admissions. You must synthesize the verifiable specialist data and the committee debate into a final Executive Summary."
        task = f"""
        You are finalizing the application file for an Anonymized Applicant.
        
        SPECIALIST VERIFICATIONS (Average: {avg_score}/10):
        1. Behavioral Psychologist (Vision): {sub_scores['motivation']}/10 - {focus_eval.get('detailed_analysis')} | Quote: "{focus_eval.get('direct_quote')}"
        2. Program Alignment Director: {sub_scores['trajectory']}/10 - {traj_eval.get('detailed_analysis')} | Quote: "{traj_eval.get('direct_quote')}"
        3. Technical SME: {sub_scores['technical']}/10 - {tech_eval.get('detailed_analysis')} | Quote: "{tech_eval.get('direct_quote')}"
        4. Academic Auditor (Resilience): {sub_scores['transcript']}/10 - {trans_eval.get('detailed_analysis')} | Quote: "{trans_eval.get('direct_quote')}"
        5. Reference Cross-Checker: {sub_scores['references']}/10 - {ref_eval.get('detailed_analysis')} | Quote: "{ref_eval.get('direct_quote')}"
        
        THE DEBATE:
        - Strict Professor's Stance: {prof_critique.get('stance')}
        - Visionary Dean's Stance: {dean_critique.get('stance')}
        
        DECISION RULES:
        - OVERALL AVERAGE < 5: "Reject"
        - ANY INDIVIDUAL SCORE <= 1: "Reject" (If References are 1 or below, it's an automatic fail).
        - If the candidate is switching fields (High Trajectory, Low Technical), and the Visionary Dean's argument is compelling: Override the technical gap and issue "Conditional Admit".
        - If the Strict Professor correctly identifies a fatal flaw (e.g., terrible references or zero technical skill): "Reject".
        - AVERAGE > 7.5 and no scores below 5: "Admit"

        OUTPUT JSON FORMAT:
        {{
            "overall_recommendation": "Admit" | "Conditional Admit" | "Reject",
            "system_confidence_score": {calculated_confidence},
            "executive_summary": "A powerful 3-4 sentence summary from your perspective as the Chair. Weigh the candidate's core strengths, address the committee debate, and justify your final recommendation.",
            "strengths": ["Bullet point 1", "Bullet point 2", "Bullet point 3"],
            "weaknesses": ["Bullet point 1", "Bullet point 2", or None if none available],
            "specialists": {{
                "Behavioral Psychologist": "**Score: {sub_scores['motivation']}/10** - {focus_eval.get('detailed_analysis')} *(Proof: \"{focus_eval.get('direct_quote')}\")*",
                "Program Alignment Director": "**Score: {sub_scores['trajectory']}/10** - {traj_eval.get('detailed_analysis')} *(Proof: \"{traj_eval.get('direct_quote')}\")*",
                "Technical SME": "**Score: {sub_scores['technical']}/10** - {tech_eval.get('detailed_analysis')} *(Proof: \"{tech_eval.get('direct_quote')}\")*",
                "Academic Auditor": "**Score: {sub_scores['transcript']}/10** - {trans_eval.get('detailed_analysis')} *(Proof: \"{trans_eval.get('direct_quote')}\")*",
                "Reference Cross-Checker": "**Score: {sub_scores['references']}/10** - {ref_eval.get('detailed_analysis')} *(Proof: \"{ref_eval.get('direct_quote')}\")*"
            }},
            "risk_and_anomalies": ["List any contradictions, highly adversarial references, or areas where the candidate's dialect/communication style may have confused the AI.", "If none, output 'No anomalies detected.'"]
        }}
        """
        
        return self._call_llm(role, task)