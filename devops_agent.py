import sys
import os
import traceback
from typing import TypedDict, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    error_logs: str
    build_number: str
    job_name: str
    recommendation: Optional[str]

def clean_and_optimize_logs(raw_log_path: str) -> str:
    """Safely extracts log files while protecting context window bounds."""
    if not os.path.exists(raw_log_path) or os.path.getsize(raw_log_path) == 0:
        return "Warning: The pipeline log file was empty or could not be generated properly."

    with open(raw_log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    filtered_lines = []
    for line in lines:
        if any(clutter in line for clutter in ["% completed", "Extracting", "Downloading", "Progress", "Refining"]):
            continue
        filtered_lines.append(line)
        
    full_log_string = "".join(filtered_lines)
    
    if len(full_log_string) > 12000:
        return "...[Truncated Logs]...\n" + full_log_string[-12000:]
        
    return full_log_string

def analyze_logs_node(state: AgentState):
    logs = state["error_logs"]
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        state["recommendation"] = "❌ *AI Agent Environment Error:* The `GROQ_API_KEY` was missing from system runtime."
        return state

    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=GROQ_API_KEY, temperature=0.1)
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an automated DevOps SRE Engine scanning a complete end-to-end Jenkins pipeline console log.\n"
                "Your main objective is to extract the EXACT technical mismatch, typo, or misconfiguration from the commands executed.\n\n"
                "Format your response cleanly using bold Slack markdown layout exactly like this:\n"
                "💥 *Failed Stage:* <Name of stage that broke>\n"
                "🔍 *Extracted Exact Error:* <Quote the exact error statement or mismatched data line directly from the text log>\n"
                "🛠 *Actionable Fix:* \n"
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
    except Exception as e:
        state["recommendation"] = f"❌ *AI Agent Internal API Error:* Failed to reach Groq. Details: {str(e)}"
    
    return state

def write_output_node(state: AgentState):
    with open("ai_recommendation.txt", "w", encoding="utf-8") as f:
        f.write(state["recommendation"])
    return state

# Graph Initialization
workflow = StateGraph(AgentState)
workflow.add_node("analyze_logs", analyze_logs_node)
workflow.add_node("write_output", write_output_node)
workflow.set_entry_point("analyze_logs")
workflow.add_edge("analyze_logs", "write_output")
workflow.add_edge("write_output", END)
app = workflow.compile()

if __name__ == "__main__":
    try:
        # FIX: Safe positional fallback guard checking to eliminate runtime IndexError crashes
        job_name = sys.argv[1] if len(sys.argv) > 1 else "Unknown-Job"
        build_number = sys.argv[2] if len(sys.argv) > 2 else "0"
        log_file_path = sys.argv[3] if len(sys.argv) > 3 else "full_pipeline_log.txt"
        
        processed_logs = clean_and_optimize_logs(log_file_path)
        initial_state = {
            "job_name": job_name,
            "build_number": build_number,
            "error_logs": processed_logs
        }
        app.invoke(initial_state)
    except Exception as e:
        with open("ai_recommendation.txt", "w", encoding="utf-8") as f:
            f.write(f"❌ *AI Agent Core Crash:* Traceback tracking caught:\n```\n{traceback.format_exc()}\n```")
