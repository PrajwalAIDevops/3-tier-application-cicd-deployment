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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model="llama3-70b-8192", groq_api_key=GROQ_API_KEY)

def clean_and_optimize_logs(raw_log_path: str) -> str:
    """
    Scans the entire log chronologically, filtering out verbose clutter 
    (like continuous download percentages) while retaining stage status 
    and detailed failure markers to protect the LLM context limits.
    """
    optimized_lines = []
    with open(raw_log_path, "r", errors="ignore") as f:
        lines = f.readlines()

    for line in lines:
        # Retain structural framework blocks, errors, and environment definitions
        if any(marker in line for marker in ["[Pipeline]", "stage", "ERROR", "failed", "exit", "tag", "Mismatch"]):
            optimized_lines.append(line)
        # Skip repetitive dependency installation and image pulling percentages
        elif any(clutter in line for clutter in ["% completed", "Extracting", "Downloading", "Fetch"]):
            continue
        else:
            # Keep standard output lines up to a reasonable buffer length
            if len(optimized_lines) < 250:
                optimized_lines.append(line)
            else:
                # Keep sliding window on the actual end errors
                optimized_lines.pop(0)
                optimized_lines.append(line)

    return "".join(optimized_lines)

def analyze_logs_node(state: AgentState):
    logs = state["error_logs"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an elite Site Reliability Engineer (SRE). You are reviewing an optimized, "
            "end-to-end trace of a failed Jenkins pipeline.\n\n"
            "Track the pipeline flow chronologically to diagnose exactly where the configuration or data went wrong. "
            "Identify structural faults, mismatched environment values, or typographical errors in your analysis.\n\n"
            "Provide your findings in crisp Slack markdown:\n"
            "💥 *Failed Stage:* <Name of stage>\n"
            "🔍 *Root Cause Analysis:* <Technical description of the mismatch or failure>\n"
            "🛠️ *Actionable Fix:* \n"
            "```\n"
            "<Provide the exact command, code modification, or environment key fix>\n"
            "```"
        )),
        ("user", "Job: {job_name} | Build: #{build_number}\n\nLogs:\n{logs}")
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
    with open("ai_recommendation.txt", "w") as f:
        f.write(state["recommendation"])
    return state

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
            # Read the whole log but optimize it safely before passing it to Groq
            processed_logs = clean_and_optimize_logs(log_file_path)
        else:
            processed_logs = "Log file missing or could not be found."

        initial_state = {
            "job_name": job_name,
            "build_number": build_number,
            "error_logs": processed_logs
        }
        app.invoke(initial_state)
