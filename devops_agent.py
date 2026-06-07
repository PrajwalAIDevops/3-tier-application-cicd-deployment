import sys
import os
from typing import TypedDict, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    error_logs: str
    build_number: str
    job_name: str
    recommendation: Optional[str]

# Fetch key from Jenkins environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# FIX: Switched from deprecated model to active 2026 production endpoint
llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=GROQ_API_KEY, temperature=0.1)

def clean_and_optimize_logs(raw_log_path: str) -> str:
    """Reads full log file from start to finish safely using UTF-8."""
    with open(raw_log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    # Trim continuous download noise but keep 100% of pipeline structural commands and errors
    filtered_lines = []
    for line in lines:
        if any(clutter in line for clutter in ["% completed", "Extracting", "Downloading", "Progress"]):
            continue
        filtered_lines.append(line)
        
    return "".join(filtered_lines)

def analyze_logs_node(state: AgentState):
    logs = state["error_logs"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an automated DevOps SRE Engine scanning a complete end-to-end Jenkins pipeline console log.\n"
            "Your main objective is to extract the EXACT technical mismatch or typo from the commands executed.\n\n"
            
            "Look for details like:\n"
            "- Discrepancies between variables defined vs variables used.\n"
            "- Typos in Docker tags or image references during push or build commands.\n"
            "- Configuration parameter collisions.\n\n"
            
            "Format your response cleanly using bold Slack markdown layout:\n"
            "💥 *Failed Stage:* <Name of stage that broke>\n"
            "🔍 *Extracted Exact Error:* <Quote the exact error statement or mismatched data line directly from the text log>\n"
            "🛠️ *Actionable Fix:* \n"
            "```\n"
            "<Provide the precise string modification or setup fix>\n"
            "```"
        )),
        ("user", "Analyze logs chronologically for Job: {job_name} | Build: #{build_number}\n\nLogs:\n{logs}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "job_name": state["job_name"], 
        "build_number": state["build_number"], 
        "logs": logs
    })
    
    state["recommendation"] = response.content
    return state

def write_output_node(state: AgentState):
    with open("ai_recommendation.txt", "w", encoding="utf-8") as f:
        f.write(state["recommendation"])
    return state

# Graph Setup
workflow = StateGraph(AgentState)
workflow.add_node("analyze_logs", analyze_logs_node)
workflow.add_node("write_output", write_output_node)
workflow.set_entry_point("analyze_logs")
workflow.add_edge("analyze_logs", "write_output")
workflow.add_edge("write_output", END)
app = workflow.compile()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        job_name = sys.argv[1]
        build_number = sys.argv[2]
        log_file_path = sys.argv[3]
        
        if os.path.exists(log_file_path):
            processed_logs = clean_and_optimize_logs(log_file_path)
        else:
            processed_logs = "Log file missing or could not be found."

        initial_state = {
            "job_name": job_name,
            "build_number": build_number,
            "error_logs": processed_logs
        }
        app.invoke(initial_state)
