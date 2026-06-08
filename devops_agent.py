import os
import re
import sys
from langchain_groq import ChatGroq

JOB_NAME = sys.argv[1]
BUILD_NUMBER = sys.argv[2]
LOG_FILE = sys.argv[3]

OUTPUT_FILE = "ai_recommendation.txt"

# ----------------------------------
# READ LOG
# ----------------------------------

with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
    logs = f.read()

# ----------------------------------
# STAGE DETECTION
# ----------------------------------

stage_match = re.findall(
    r"Stage \"([^\"]+)\"",
    logs,
    re.IGNORECASE
)

failed_stage = stage_match[-1] if stage_match else "Unknown"

# ----------------------------------
# ERROR EXTRACTION
# ----------------------------------

ERROR_PATTERNS = [
    r".*ERROR.*",
    r".*Exception.*",
    r".*FAILED.*",
    r".*failed.*",
    r".*permission denied.*",
    r".*command not found.*",
    r".*denied.*",
    r".*ImagePullBackOff.*",
]

errors = []

for line in logs.splitlines():

    for pattern in ERROR_PATTERNS:

        if re.search(pattern, line, re.IGNORECASE):
            errors.append(line.strip())

error_text = "\n".join(errors[-20:])

# ----------------------------------
# RULE ENGINE
# ----------------------------------

KNOWN_ERRORS = {

    "permission denied":
        """
Root Cause:
File permission issue.

Fix:
sudo chown jenkins:jenkins <file>
or
chmod 644 <file>
""",

    "command not found":
        """
Root Cause:
Required binary not installed.

Fix:
Install tool or verify PATH variable.
""",

    "quality gate failed":
        """
Root Cause:
SonarQube Quality Gate failed.

Fix:
Resolve critical Sonar issues before deployment.
""",

    "ImagePullBackOff":
        """
Root Cause:
Kubernetes cannot pull image.

Fix:
Verify image tag and registry credentials.
"""
}

for keyword, fix in KNOWN_ERRORS.items():

    if keyword.lower() in logs.lower():

        result = f"""
🚨 CI/CD Failure Analysis

Failed Stage:
{failed_stage}

Detected Error:
{keyword}

{fix}
"""

        with open(OUTPUT_FILE, "w") as f:
            f.write(result)

        sys.exit(0)

# ----------------------------------
# SEND ONLY RELEVANT LOGS TO GROQ
# ----------------------------------

groq_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=groq_key,
    temperature=0
)

prompt = f"""
You are a Senior DevOps Engineer.

Analyze Jenkins failure.

Rules:

1. Identify failed stage.
2. Extract exact error.
3. Explain root cause.
4. Give fix.
5. Do not guess.

Job:
{JOB_NAME}

Build:
{BUILD_NUMBER}

Stage:
{failed_stage}

Error Snippets:

{error_text}
"""

response = llm.invoke(prompt)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(response.content)
