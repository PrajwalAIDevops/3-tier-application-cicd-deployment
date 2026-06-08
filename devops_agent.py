import os
import re
import sys
import traceback
from langchain_groq import ChatGroq

OUTPUT_FILE = "/tmp/ai_recommendation.txt"


def save_output(content):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def extract_errors(logs):
    patterns = [
        r".*ERROR.*",
        r".*Exception.*",
        r".*FAILED.*",
        r".*failed.*",
        r".*permission denied.*",
        r".*command not found.*",
        r".*denied.*",
        r".*ImagePullBackOff.*",
        r".*CrashLoopBackOff.*"
    ]

    results = []

    for line in logs.splitlines():
        for p in patterns:
            if re.search(p, line, re.IGNORECASE):
                results.append(line)

    return "\n".join(results[-30:])


try:

    job_name = sys.argv[1]
    build_number = sys.argv[2]
    log_file = sys.argv[3]

    if not os.path.exists(log_file):
        save_output("❌ Jenkins log file not found")
        sys.exit(0)

    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        logs = f.read()

    logs = logs[-15000:]

    known_errors = {
        "permission denied":
            """
Root Cause:
Permission issue.

Fix:
Check file ownership.

Example:
sudo chown -R jenkins:jenkins <path>
chmod 644 <file>
""",

        "command not found":
            """
Root Cause:
Required binary missing.

Fix:
Install package or update PATH.
""",

        "docker: permission denied":
            """
Root Cause:
Jenkins cannot access Docker socket.

Fix:
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
""",

        "quality gate failed":
            """
Root Cause:
SonarQube Quality Gate failed.

Fix:
Resolve Sonar issues before deployment.
""",

        "ImagePullBackOff":
            """
Root Cause:
Kubernetes cannot pull image.

Fix:
Verify image tag and registry credentials.
"""
    }

    for key, fix in known_errors.items():

        if key.lower() in logs.lower():

            save_output(f"""
🚨 AI DevOps Analysis

Job: {job_name}
Build: #{build_number}

Detected Error:
{key}

{fix}
""")

            sys.exit(0)

    groq_key = os.getenv("GROQ_API_KEY")

    if not groq_key:
        save_output("❌ GROQ_API_KEY missing")
        sys.exit(0)

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=groq_key,
        temperature=0
    )

    error_section = extract_errors(logs)

    prompt = f"""
You are a Senior DevOps Engineer.

Analyze Jenkins failure.

Rules:
1. Identify failed stage.
2. Extract exact error.
3. Explain root cause.
4. Give fix.
5. Do not guess.
6. If uncertain say:
   'Insufficient log evidence'

Job:
{job_name}

Build:
{build_number}

Logs:
{error_section}
"""

    response = llm.invoke(prompt)

    save_output(response.content)

except Exception:
    save_output(traceback.format_exc())
