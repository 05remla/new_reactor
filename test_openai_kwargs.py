from langchain_openai import ChatOpenAI
try:
    llm = ChatOpenAI(model="gpt-4o", include_reasoning=True)
    print("SUCCESS include_reasoning")
except Exception as e:
    print("ERROR include_reasoning:", e)
