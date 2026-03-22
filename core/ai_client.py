import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

USE_AZURE = os.getenv("USE_AZURE", "false").lower() == "true"

if USE_AZURE:
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")

    client = OpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        base_url=f"{azure_endpoint}/openai/v1/",
    )

else:
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )