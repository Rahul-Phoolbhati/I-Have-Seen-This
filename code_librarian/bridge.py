#!/usr/bin/env python3
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# ── Args ─────────────────────────────────────────────────────────────────
user_arg    = sys.argv[1] if len(sys.argv) > 1 else ""
session_id  = sys.argv[2] if len(sys.argv) > 2 else "unknown"
project_dir = sys.argv[3] if len(sys.argv) > 3 else "unknown"

# ── Log to file AND stdout (so Claude Code sees it live) ─────────────────
LOG_DIR = Path.home() / ".claude" / "my_script_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG_FILE = LOG_DIR / f"latest_log_file.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
    force=True
)
log = logging.getLogger(__name__)

# force stdout flush so Claude Code streams it live
sys.stdout.reconfigure(line_buffering=True)

log.info(f"Script started")
log.info(f"User arg    : {user_arg!r}")
log.info(f"Session ID  : {session_id}")
log.info(f"Project dir : {project_dir}")
log.info(f"Log file    : {LOG_FILE}")

# ── Read transcript ───────────────────────────────────────────────────────
def find_transcript(session_id):
    projects_dir = Path.home() / ".claude" / "projects"
    matches = list(projects_dir.rglob(f"{session_id}.jsonl"))
    return matches[0] if matches else None

def parse_transcript(file_path):
    cleaned_messages = []
    if not file_path:
        return ""
        
    with open(file_path, "r") as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                
                # Check for User messages
                if data.get("type") == "user":
                    content = data.get("message", {}).get("content", "")
                    # Sometimes content is a list of dicts, sometimes a string
                    if isinstance(content, list):
                        text = " ".join([item.get("text", "") for item in content if item.get("type") == "text"])
                    else:
                        text = content
                    cleaned_messages.append(f"USER: {text}")

                # Check for Assistant messages
                elif data.get("type") == "assistant":
                    content_list = data.get("message", {}).get("content", [])
                    text = " ".join([item.get("text", "") for item in content_list if item.get("type") == "text"])
                    cleaned_messages.append(f"CLAUDE: {text}")
                    
            except Exception as e:
                log.error(f"Failed to parse line: {e}")
                
    return "\n".join(cleaned_messages)

transcript_path = find_transcript(session_id)
if transcript_path:
    log.info(f"Transcript  : {transcript_path}")
    chat_for_agent = parse_transcript(transcript_path)
    # messages = [json.loads(l) for l in transcript_path.read_text().splitlines() if l.strip()]

    # log.info(f"Messages    : {chat_for_agent}")
else:
    log.warning("No transcript found")

if chat_for_agent:
    script_dir = Path(__file__).parent
    sys.path.append(str(script_dir / "src"))

    # Now this should work
    from code_librarian.crew import CodeLibrarian
    # from src.code_librarian.crew import CodeLibrarian
    
    inputs = {
        'chat_history': chat_for_agent,  # The cleaned text
        'project_path': project_dir
    }
    
    # Run the crew

    log.info("🚀 HANDING OFF TO AGENT...")
    result = CodeLibrarian().crew().kickoff(inputs=inputs)

    log.info("-------------------------------------------")
    log.info(f"🤖 AGENT RESPONSE RECEIVED:")
    log.info(result.raw) # This is the Markdown note the agent made
    log.info("-------------------------------------------")

    log.info("Final bridge cleanup...")
    log.info("Done ✅")
