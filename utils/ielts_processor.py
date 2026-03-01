import pdfplumber
import json
import io
from core.ai_client import client

class IELTSProcessor:
    def __init__(self):
        # Thresholds stored as class attributes
        self.min_overall = 7.0
        self.min_band = 7.0
        self.model = "gpt-4o-mini"

    def extract_ielts_scores(self, pdf_file):
        """
        Extract text from PDF while preserving visual layout, 
        then use OpenAI to parse the scores cleanly.
        """
        print("Reading PDF with pdfplumber to preserve layout...")
        
        # 1. Extract text keeping the visual layout intact
        raw_text = ""
        try:
            with pdfplumber.open(io.BytesIO(pdf_file)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(layout=True) 

                    if page_text:
                        raw_text += page_text + "\n"
                        
        except Exception as e:
            print(f"Failed to read PDF: {e}")
            return {}

        # 2. Ask OpenAI to extract the data from the now-clean text
        prompt = f"""
        Here is the text extracted from an IELTS Test Report Form:
        ---
        {raw_text}
        ---
        Please extract the scores for Listening, Reading, Writing, Speaking, and Overall Band Score.
        Return ONLY a valid JSON dictionary with the following exact lowercase keys: 
        listening, reading, writing, speaking, overall.
        All values should be floats. Do not include any markdown formatting, backticks, or other text.
        """

        print("Sending text to OpenAI for structuring...")
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={ "type": "json_object" }
            )
            
            result_str = response.choices[0].message.content
            bands = json.loads(result_str)
            
            return bands
            
        except Exception as e:
            print(f"Failed to extract via OpenAI: {e}")
            return {}

    def check_ielts_threshold(self, ielts_scores):
        """
        Check IELTS scores against minimum thresholds.
        Returns a tuple: (passed: bool, failed_bands: list)
        """
        if not ielts_scores:
            return False, ["extraction_failed"]
            
        failed_bands = [
            band for band, score in ielts_scores.items() 
            if band != "overall" and float(score) < self.min_band
        ]
        
        overall_score = float(ielts_scores.get("overall", 0))
        passed = overall_score >= self.min_overall and len(failed_bands) == 0

        return passed, failed_bands