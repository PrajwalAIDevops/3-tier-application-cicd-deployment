import sys
import os
from typing import TypedDict, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# 1. Define LangGraph State
class AgentState(TypedDict):
    error_logs: str
    build_number: str
    job_name: str
    recommendation: Optional[str]

# Initialize Groq LLM using the key injected by Jenkins
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Using llama3-70b-8192 for deep DevOps reasoning capabilities
llm = ChatGroq(model="llama3-70b-8192", groq_api_key=GROQ_API_KEY)

# 2. Node 1: Analyze logs and generate markdown recommendations
def analyze_logs_node(state: AgentState):
    logs = state["error_logs"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert DevOps SRE Agent. Analyze the provided Jenkins pipeline error logs.\n"
            "Identify exactly why it failed (e.g., NPM compilation error, Trivy vulnerability barrier, "
            "Docker build failure, or incorrect environment variables/DB credentials).\n\n"
            "Provide your output strictly in this markdown layout:\n"
            "*💥 Detected Error:* <Brief 1-line error summary>\n"
            "*🔍 Root Cause:* <Technical explanation of why it failed>\n"
            "*🛠️ Step-by-Step Fix:* \n"
            "1. <Actionable fix step>\n"
            "2. <Actionable fix step>"
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

# 3. Node 2: Write output back to a text file for Jenkins to read back
def write_output_node(state: AgentState):
    with open("ai_recommendation.txt", "w") as f:
        f.write(state["recommendation"])
    return state

# 4. Build and Compile the LangGraph Workflow
workflow = StateGraph(AgentState)
workflow.add_node("analyze_logs", analyze_logs_node)
workflow.add_node("write_output", write_output_node)

workflow.set_entry_point("analyze_logs")
workflow.add_edge("analyze_logs", "write_output")
workflow.add_edge("write_output", END)

app = workflow.compile()

if __name__ == "__main__":
    # Expects execution: python devops_agent.py <job_name> <build_number> <log_file_path>
    if len(sys.argv) > 3:
        job_name = sys.argv[1]
        build_number = sys.argv[2]
        log_file_path = sys.argv[3]
        
        if os.path.exists(log_file_path):
            with open(log_file_path, "r", errors="ignore") as f:
                log_content = f.read()
        else:
            log_content = "Log file missing or could not be found by agent."

        # Execute Agent Graph
        initial_state = {
            "job_name": job_name,
            "build_number": build_number,
            "error_logs": log_content
        }
        app.invoke(initial_state)
