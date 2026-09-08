# This file contains the prompts designed by the AI Engine / Product Manager

SYSTEM_PROMPT = \"\"\"
You are an advanced AI assistant built for the AI2B Hackathon.
Your goal is to provide deep insights based on the provided data context.
Be concise, analytical, and format your output cleanly using markdown.
\"\"\"

def build_rag_prompt(user_query: str, retrieved_context: str) -> str:
    \"\"\"
    Helper to construct a RAG prompt dynamically.
    \"\"\"
    return f\"\"\"
    Context extracted from the dataset:
    {retrieved_context}
    
    Based ONLY on the context above, answer the following query:
    {user_query}
    \"\"\"
