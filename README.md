# cozempic
Claude Desktop-compatible MCP Server

CONTEXT SURGEON — Surgical context cleaning for Claude Desktop. The scalpel where the native compact is a sledgehammer.

context_surgeon.py  v1.0.0

PREREQUISITES
  Python 3.10 or newer. Zero pip packages required (pure stdlib).
  Check version : python --version   (or python3 --version)
  Download 3.10+: https://www.python.org/downloads/
  Windows note  : during install, check "Add Python to PATH"

  No pip install needed. This script uses only the Python standard
  library. If Python itself is missing or outdated, the script
  detects this at startup and prints the download URL.

INSTALL AS MCP SERVER (run once; then restart Claude Desktop)
  python context_surgeon.py setup-mcp

CLI USAGE
  python context_surgeon.py discover                    find Claude Desktop data
  python context_surgeon.py diagnose conversation.json  analyze for bloat
  python context_surgeon.py prune    conversation.json  compress + create briefing
  python context_surgeon.py prune conversation.txt --verbatim 10 --rx standard
  python context_surgeon.py prune conversation.txt --output briefing.md
  python context_surgeon.py prune - < pasted_convo.txt  read from stdin

MCP TOOLS (available in Claude Desktop after setup-mcp + restart)
  diagnose_conversation   token estimates, noise counts, savings projections
  prune_conversation      surgical pruning with configurable prescription
  create_briefing         compress to fresh-start document; paste into new chat
  extract_rules           extract behavioral corrections ("don't do X", "always Y")

WHY THIS IS BETTER THAN THE NATIVE COMPACT
  Native compact: summarizes everything into a blob. Key technical
  details, behavioral corrections, code, specific constraints? Gone.

  This tool:
    - Extracts "don't do X" / "always Y" corrections and leads with them
    - Keeps your last N turns character-perfect
    - Compresses only the prose fat from older turns
    - NEVER touches code blocks
    - Reports exactly what changed and what was preserved

WORKFLOW
  1. As your conversation approaches its context limit, export it
     from Claude Desktop (or copy-paste the entire conversation to
     a text or JSON file).
  2. Run:  python context_surgeon.py prune convo.txt --output briefing.md
  3. Open a new Claude Desktop conversation.
  4. Paste the contents of briefing.md as your first message.
  5. Continue exactly where you left off with full context headroom.

NOTE ON "81/100 ATTACHMENTS" vs. CONTEXT LENGTH
  If your limit is project knowledge files (Claude Desktop projects
  allow up to 100 knowledge files): that is a different constraint
  from conversation context. Remove outdated/redundant files via
  Claude Desktop's UI (project settings -> knowledge). This script
  addresses conversation context length, not the knowledge file cap.

INPUT FORMATS
  JSON    Claude.ai / Claude Desktop export, or raw Claude API
          messages array: [{"role":"user","content":"..."}, ...]
  JSONL   Claude Code session (partial compatibility)
  Text    User: ... / Human: ... / Assistant: ... / Claude: ...
  Stdin   Pass - as the filename to read from stdin

PRESCRIPTIONS
  gentle      strip thinking blocks + XML noise only
  standard    + deduplicate repeated-content turns           [default]
  aggressive  + compress verbose older turns (code blocks always preserved)

VERBATIM TURNS
  The N most recent turns are kept character-perfect; only older
  turns are processed according to the prescription. Default: 10.

v1.0.0 | https://github.com/fishboyrocks/cozempic-2.0
