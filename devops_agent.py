import os
import sys
import traceback
from langchain_groq import ChatGroq

OUTPUT_FILE = "/tmp/ai_recommendation.txt"

def save_output(content):
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"Failed to write output: {e}")

try:

    job_name = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    build_number = sys.argv[2] if len(sys.argv) > 2 else "0"
    log_file = sys.argv[3] if len(sys.argv) > 3 else "full_pipeline_log.txt"

    if not os.path.exists(log_file):
        save_output("❌ Log file not found.")
        sys.exit(0)

    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        logs = f.read()

    logs = logs[-12000:]

    known_errors = {
        "permission denied":
            "🛠 Fix: Check file ownership and permissions.",
        "command not found":
            "🛠 Fix: Required binary is missing from PATH.",
        "quality gate failed":
            "🛠 Fix: Resolve SonarQube Quality Gate issues.",
        "ImagePullBackOff":
            "🛠 Fix: Verify image tag and registry credentials.",
        "docker: permission denied":
            "🛠 Fix: Add jenkins user to docker group."
    }

    for key, fix in known_errors.items():
        if key.lower() in logs.lower():

            result = f"""
🚨 CI/CD Failure Analysis

Job: {job_name}
Build: #{build_number}

Detected Error:
{key}

{fix}
"""

            save_output(result)
            sys.exit(0)

    groq_key = os.getenv("GROQ_API_KEY")

    if not groq_key:
        save_output("❌ GROQ_API_KEY missing.")
        sys.exit(0)

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=groq_key,
        temperature=0
    )

    prompt = f"""
You are a Senior DevOps Engineer.

Analyze this Jenkins failure.

Return:

Failed Stage:
Root Cause:
Fix:

Logs:

{logs}
"""

    response = llm.invoke(prompt)

    save_output(response.content)

except Exception:

    save_output(
        "❌ AI Agent Error\n\n" +
        traceback.format_exc()
    )
