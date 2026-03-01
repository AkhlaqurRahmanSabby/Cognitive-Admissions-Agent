import io
from core.ai_client import client

class AudioProcessor:
    def __init__(self):
        self.transcribe_model = "whisper-1"
        self.speech_model = "tts-1"
        self.voice = "nova" # Other options: echo, fable, onyx, allpy, shimmer

    def transcribe_audio(self, audio_bytes):
        """Converts user's voice into text."""
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "candidate_response.wav"

            response = client.audio.transcriptions.create(
                model=self.transcribe_model,
                file=audio_file,
            )
            return response.text
        except Exception as e:
            print(f"Audio transcription error: {e}")
            return None

    def generate_audio(self, text):
        """Converts AI's text response into spoken audio bytes."""
        try:
            response = client.audio.speech.create(
                model=self.speech_model,
                voice=self.voice,
                input=text
            )
            return response.content
        except Exception as e:
            print(f"TTS error: {e}")
            return None