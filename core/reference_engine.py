import json
from .ai_client import client

class ReferenceEngine:
    def __init__(self, student_data, referee_data):
        self.student_name = student_data.get("name", "the candidate")
        self.target_program = student_data.get("degree", "graduate studies")
        self.student_context = student_data.get("transcript_report", "")
        
        self.referee_name = referee_data.get("name", "Reference")
        self.referee_designation = referee_data.get("designation", "Professional")
        
        self.max_turns = 4
        self.system_prompt = f"""
        You are the 'Reference Verification Agent' for an elite university.
        You are interviewing {self.referee_name} ({self.referee_designation}) regarding their recommendation for {self.student_name}.
        {self.student_name} is applying for: {self.target_program}.
        
        STUDENT BACKGROUND CONTEXT: {self.student_context}
        
        YOUR DIRECTIVES:
        1. Ask highly specific, professional questions to verify the candidate's capabilities, work ethic, and technical depth.
        2. Do NOT ask generic questions like "What are their strengths?" Ask things like: "Can you detail a specific instance where {self.student_name} had to overcome a complex problem in your lab/class?"
        3. You have a maximum of {self.max_turns} questions.
        4. Maintain a highly respectful, academic, and concise tone.
        
        OUTPUT FORMAT:
        You must strictly output a JSON object:
        {{
            "question": "Your text to the referee",
            "is_complete": boolean (true if you have asked {self.max_turns} questions and they have answered the final one)
        }}
        """


    def start_interview(self):
        """Generates the very first targeted question."""
        task = f"Greet the referee professionally. If their designation ({self.referee_designation}) is 'Professor' or implies a doctorate, address them as 'Dr. {self.referee_name.split()[-1]}'. Otherwise, simply address them politely as '{self.referee_name}'. Thank them for their time, and ask your first specific question regarding {self.student_name}'s past performance."
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task}
        ]
        
        return self._call_llm(messages)


    def generate_response(self, chat_history, user_input):
        """Processes the referee's answer and generates the next question."""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Build the conversation history
        for msg in chat_history:
            messages.append({"role": msg[0], "content": msg[1]})
            
        messages.append({"role": "user", "content": user_input})
        
        turn_count = sum(1 for msg in chat_history if msg[0] == "assistant")
        
        if turn_count >= self.max_turns - 1:
            messages.append({"role": "system", "content": "This is the final turn. Thank the referee for their time, confirm the reference is complete, and set 'is_complete' to true."})
            
        return self._call_llm(messages)


    def _call_llm(self, messages):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3
            )
            return json.loads(response.choices[0].message.content)
        
        except Exception as e:
            return {"question": f"System error: {str(e)}", "is_complete": True}