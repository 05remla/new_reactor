import os
import sys
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

api_key = os.environ.get("GOOGLE_API_KEY", "dummy")
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, include_thoughts=True)
    print("SUCCESS: include_thoughts=True accepted!")
except Exception as e:
    print("ERROR:", e)
