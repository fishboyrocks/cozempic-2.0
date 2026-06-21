#!/usr/bin/env python3
"""
context_surgeon.py  v1.0.7-alpha
 _______________________________________________________________
|                                                               |
|  CONTEXT SURGEON — Surgical context cleaning for Claude       |
|  Desktop. The scalpel where the native compact is a           |
|  sledgehammer.                                                |
|_______________________________________________________________|

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
  Text    User: / You: / **User**: / **Assistant**: / Claude: ...
          Solo-line labels (You on its own line, then message text)
          Date-separator fallback (May 16 / Jun 3 style; Claude Desktop
          copy-paste; dates mark assistant-response starts)
  Stdin   Pass - as the filename to read from stdin

PRESCRIPTIONS
  gentle      strip thinking blocks + XML noise only
  standard    + deduplicate repeated-content turns           [default]
  aggressive  + compress verbose older turns (code blocks always preserved)

VERBATIM TURNS
  The N most recent turns are kept character-perfect; only older
  turns are processed according to the prescription. Default: 10.

v1.0.7-alpha | https://github.com/fishboyrocks/cozempic-2.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
# ruff: noqa: E741

# ---- Windows UTF-8 fix -------------------------------------------------------
# Without this, MCP JSON-RPC over stdio silently mangles non-ASCII on Windows
# (default cp1252 encoding). Must run before any I/O.
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.stdin  = _io.TextIOWrapper(sys.stdin.buffer,  encoding="utf-8", errors="replace")


# ---- Constants ---------------------------------------------------------------

# Before bumping this: classify the change FIRST, then derive the number --
# don't anchor on "what's the next sequential digit." Removed/renamed/changed
# the signature of any CLI command, MCP tool, or public function? -> MAJOR.
# Added any new CLI flag, MCP tool, function, or capability? -> MINOR (this
# is what v1.0.4 should have been -- it added collapse_exact_repeats() and
# got versioned as a patch by mistake). Otherwise, purely corrects existing
# behavior with no new surface -> PATCH. Debugging effort and lines changed
# are irrelevant to this classification.
__version__         = "1.1.0-alpha"  # 1.1.0 line: atomic writes + broader detection
CHARS_PER_TOKEN     = 3.1       # calibrated from real Claude sessions (cozempic/tokens.py)
DEFAULT_CONTEXT_WIN = 200_000   # conservative 200 K baseline; real window varies by plan/model
DEFAULT_VERBATIM    = 10        # recent turns kept verbatim by default
MAX_STORE_RULES     = int(os.environ.get("CONTEXT_SURGEON_MAX_STORE_RULES", "500"))
MCP_MAX_INPUT_CHARS = 2_000_000   # ~2MB safety limit for MCP tool calls
REVIEW_MODE = os.environ.get("CONTEXT_SURGEON_REVIEW_MODE", "0") == "1"
_SAFETY_PATTERNS = ("anti-trans hate crime", "physical safety", "jeopardy from an")
RULES_STORE_PATH    = Path(
    os.environ.get("CONTEXT_SURGEON_RULES_STORE", 
                   str(Path.home() / ".config" / "context-surgeon" / "rules.json"))
)
MAX_RULES           = 20        # IFScale: >30 irrelevant rules measurably degrades adherence
MAX_RULE_LEN        = 460       # max chars per extracted rule sentence
                                  # v1.0.5: raised from 350. Measured natural
                                  # (uncapped) lengths of every real
                                  # correction-trigger sentence in a 298K+
                                  # char conversation: longest was 441 chars,
                                  # next-longest 347. 350 was clipping that
                                  # one sentence -- the safety-critical one
                                  # naming the actual danger ("...jeopardy
                                  # from an anti-trans hate crime") -- right
                                  # at the word before the threat itself.
                                  # 460 covers it with margin without being
                                  # an arbitrary guess.

# v1.0.6: closing punctuation that should never be stranded one character
# behind a sentence-ending period -- "...else.) hence..." should keep the
# ")". Includes straight AND curly/smart quotes (checked against the real
# conversation: zero curly-quote-after-period instances existed there, but
# this function is meant to be reusable beyond one conversation, and the
# cost of covering them is one constant, not new complexity).
_CLOSING_PUNCT = ")]\"'\u2019\u201d"
INPUT_WARN_MB       = 5         # warn if conversation input exceeds this size

THINKING_RE = re.compile(
    r"<thinking>\s*.*?\s*</thinking>"
    r"|<think>\s*.*?\s*</think>",
    re.DOTALL | re.IGNORECASE,
)

XML_NOISE_RE = re.compile(
    r"<system-reminder>.*?</system-reminder>"
    r"|<local-command(?:-caveat|-stdout|-stderr)?>.*?"
    r"</local-command(?:-caveat|-stdout|-stderr)?>"
    r"|<command-(?:name|message|args)>.*?</command-(?:name|message|args)>",
    re.DOTALL,
)

CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```|`[^`\n]+`")

# ---- v1.0.1 text-parser patterns --------------------------------------------
# NOTE: Python's re module does NOT support variable-length lookbehinds.
# We anchor with ^ + re.MULTILINE instead, which is equivalent and correct.
# \s* after ^ also consumes any stray \r left from Windows CRLF line endings.

# Format 1: colon-separated role labels.
# Handles plain ("User: "), markdown-bold ("**Assistant**: "), "You: ",
# timestamped variants ("[2:30 PM] You: "), and Claude model names
# ("Claude Sonnet 4.6: ").  Captured group 1 = raw role string.
_COLON_RE = re.compile(
    r"^\s*"
    r"(?:\[\d{1,2}:\d{2}(?:\s*[AP]M)?\])?\s*"       # optional leading [time]
    r"(?:\*\*|__)? "                                    # optional **/__"
    r"(You|User|Human|Assistant|Claude(?:\s+[A-Za-z0-9][A-Za-z0-9.]*){0,3}|AI)"
    r"(?:\*\*|__)? "                                    # optional closing **/__"
    r"\s*(?:\[\d{1,2}:\d{2}(?:\s*[AP]M)?\])?\s*"    # optional trailing [time]
    r":\s*",                                           # required colon
    re.IGNORECASE | re.MULTILINE,
)

# Format 2: solo-line labels — "You" or "Claude" alone on a line, no colon.
# Claude Desktop copy-paste sometimes produces this exact format.
_SOLO_RE = re.compile(
    r"^\s*(You|User|Human|Assistant|Claude(?:\s+[A-Za-z0-9][A-Za-z0-9.]*){0,3}|AI)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Format 3: Claude Desktop date-separator fallback.
# Claude Desktop inserts a bare "Month Day" line before each assistant
# response in copy-paste output.  Used only when Formats 1 and 2 find
# no recognizable role labels at all.
_DATE_RE = re.compile(
    r"^\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# ---- v1.0.2 gentle / standard prescription patterns -------------------------

# Boilerplate opening phrases stripped from assistant turns in all prescriptions.
# Matches the first sentence/line when it is pure acknowledgment with no content.
_BOILERPLATE_OPEN_RE = re.compile(
    r"^\s*"
    r"(?:Of course[!,]? \s+|Certainly[!,]? \s+|Sure[!,]? \s+|Absolutely[!,]? \s+|"
    r"Great(?:\s+question)?[!,]? \s+)"
    r"[^\n]*\n\n?",
    re.IGNORECASE,
)
_BOILERPLATE_OPENV2_RE = re.compile(
    r"^\s*(?:I'?(?:'ll|'d)(?: be)? (?:happy|glad|delighted)(?: to)? (?:help|analyze|review|look at|work through)[^\n]*\n\n?"
    r"|Let me (?:carefully |thoroughly |systematically )?(?:analyze|review|work through|look at|help|walk you through)[^\n]*\n\n?"
    r"|I'?(?:'ve)? (?:carefully |thoroughly )?(?:reviewed|analyzed|evaluated|gone through|looked at)[^\n]*\n\n?)",
    re.IGNORECASE,
)

# Boilerplate closing phrases stripped from assistant turns in all prescriptions.
_BOILERPLATE_CLOSE_RE = re.compile(
    r"\n+(?:(?:Let|Please let) me know(?: if| what| how)[^\n]*"
    r"|(?:Feel|Please feel) free to (?:ask|let me know|reach out|share)[^\n]*"
    r"|(?:I )?[Hh]ope this (?:helps?|(?:has been|was) helpful|gives?|provides?)[^\n]*"
    r"|[Ii]'?(?:'m|'ll) (?:here|happy|available|glad)(?: to)? (?:help|assist|answer|make|revisit|adjust)[^\n]*"
    r"|[Hh]appy to (?:help|assist|elaborate|dive|explore|clarify|discuss|revisit|adjust)[^\n]*"
    r"|[Ww]ould you like (?:me to|to)[^\n]*"
    r"|[Ii]s there anything (?:else|more|other)[^\n]*"
    r"|[Ww]ant me to[^\n]*)"
    r"[.!?]?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Standard prescription only: strip pure acknowledgment openers before the
# actual content begins.  Targets turns that open with "Yes, you're right" /
# "I understand" / "That's a good point" before giving substantive response.
_ACK_OPENER_RE = re.compile(
    r"^\s*(?:Yes(?:,| -)? (?:you(?:'re| are) right|absolutely|exactly|that(?:'s| is) (?:correct|a good point|fair))[^\n]*\n\n?"
    r"|I(?: fully)? understand[^\n]*\n\n?"
    r"|That(?:'s| is)(?: a)? (?:great|good|fair|excellent|valid)[^\n]*\n\n?"
    r"|You(?:'re| are)(?: absolutely| totally)? right[^\n]*\n\n?)",
    re.IGNORECASE,
)

# ---- v1.0.3-alpha: Claude Desktop copy-paste UI artifact stripping ----------
# Verified against a real 298,608-char / 34-turn Claude Desktop export
# (Ctrl+A/Ctrl+C/Ctrl+V capture): 36 doubled thinking-summary-line pairs
# (max 107 chars, e.g. "Analyzed ten outfits against transgender passing
# criteria systematically" appearing twice in a row) and 12 standalone
# "Show more" truncation-button labels, none carrying information not
# already present in the surrounding turn content.  Applied unconditionally
# in clean() so it benefits every prescription AND verbatim/recent turns
# without affecting the verbatim guarantee (pure UI chrome, zero content).
_DUP_LINE_MAX_LEN = 200  # generous margin above the 107-char observed max;
                          # longer duplicate blocks are deduplicate()'s job

# ---- v1.0.4-alpha: exact-repeat paragraph/sentence collapsing (standard+) ---
# Splits on sentence-end+capital OR blank-line breaks, so a varying label
# ("Note I wrote to stylist:" vs "Your revised note:") doesn't block
# detection of identical inner content that follows it.
_REPEAT_SPLIT_RE  = re.compile(r'((?<=[.!?])\s+(?=[A-Z])|\n{2,})')
_MIN_COLLAPSE_LEN = 60  # chars; keeps short per-item verdicts ("Select it.",
                          # "Reject it.") untouched -- those are real per-item
                          # decisions, not redundant restatement, even when
                          # they repeat verbatim across many outfits/items.

# Patterns that signal a behavioral correction in a user turn.
# Word boundaries (\b) prevent false matches inside longer words.
CORRECTION_RE = re.compile(
    r"\b(?:"
    r"don'?t"
    r"|do not"
    r"|please don'?t"
    r"|never"
    r"|always"
    r"|stop\s+\w+ing"
    r"|from now on"
    r"|remember to\b"
    r"|remember that\b"
    r"|make sure to\b"
    r"|make sure you\b"
    r"|you shouldn'?t"
    r"|use .{1,30} instead"
    r")\b",
    re.IGNORECASE,
)

# 1.1.0: broader implicit-correction signals (adapted from cozempic's
# classify_turn technique, written from scratch, exact-match extraction only).
# These catch soft corrections ("actually,", "that's not right", apology-
# follow-ups) that the original keyword list misses, while still feeding
# the exact same hardened _sentence_around() path.
IMPLICIT_CORRECTION_RE = re.compile(
    r"\b(?:"
    r"actually[,.]"
    r"|that's not right"
    r"|that's incorrect"
    r"|no[, ]that's"
    r"|wait[, ]no"
    r"|I meant"
    r"|I said"
    r"|sorry[, ]but"
    r"|actually[, ]I"
    r")\b",
    re.IGNORECASE,
)


# ---- Data structures ---------------------------------------------------------

@dataclass
class Turn:
    """A single conversation turn."""
    role:    str    # "user" | "assistant" | "system"
    content: str
    index:   int = 0

    def tokens(self) -> int:
        """Estimated token count using the calibrated chars-per-token ratio."""
        return max(1, int(len(self.content) / CHARS_PER_TOKEN))


@dataclass
class PruneStats:
    orig_turns:   int
    final_turns:  int
    orig_tokens:  int
    final_tokens: int
    saved_tokens: int
    saved_pct:    float
    prescription: str
    verbatim:     int
    rules_found:  int
    rules: list[str] = field(default_factory=list)


# ---- Prerequisite check ------------------------------------------------------

def check_prerequisites() -> None:
    """
    Verify Python 3.10+. Zero pip packages are required; this script
    uses only the Python standard library.

    If Python is too old or missing:
      1. Download Python 3.10+: https://www.python.org/downloads/
      2. Windows: during install, check "Add Python to PATH"
      3. Rerun this script.
    """
    if sys.version_info < (3, 10):
        print(
            f"ERROR: Python 3.10 or newer is required.\n"
            f"You have: {sys.version}\n\n"
            f"Download Python 3.10+: https://www.python.org/downloads/\n"
            f"Windows tip: check 'Add Python to PATH' during installation.\n"
            f"After installing, rerun: python context_surgeon.py ...",
            file=sys.stderr,
        )
        sys.exit(1)


# ---- Conversation parsing ----------------------------------------------------

def parse_conversation(source: str) -> list[Turn]:
    """
    Parse a conversation from JSON, JSONL, or plain text.
    Returns a list of Turn objects. Never raises; falls back gracefully.
    """
    source = source.strip()
    if not source:
        return []

    size_mb = len(source) / 1_048_576
    if size_mb > INPUT_WARN_MB:
        print(
            f"Warning: input is {size_mb:.1f} MB; processing may be slow.",
            file=sys.stderr,
        )

    # JSON (array or wrapped dict)
    if source[0] in ("[", "{"):
        try:
            return _parse_json(source)
        except Exception:
            pass  # fall through to JSONL / text

    # JSONL (one JSON object per line — Claude Code session format)
    first_nonblank = next((l.strip() for l in source.splitlines() if l.strip()), "")
    if first_nonblank.startswith("{"):
        try:
            return _parse_jsonl(source)
        except Exception:
            pass

    # Plain text (User: / Assistant: alternation)
    return _parse_text(source)


def _normalize_role(raw: str) -> str:
    r = raw.strip().lower()
    # "Claude Sonnet 4.6", "Claude Opus 4", etc. → assistant
    if r.startswith("claude"):
        r = "claude"
    if r in ("human", "user", "you"):
        return "user"
    if r in ("assistant", "claude", "ai"):
        return "assistant"
    return r


def _content_to_str(content: object) -> str:
    """Flatten any Claude API content representation to a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                parts.append(block.get("text", ""))
            elif btype == "thinking":
                # Wrap so the thinking-strip regex catches it
                parts.append(f"<thinking>{block.get('thinking', '')}</thinking>")
            elif btype == "tool_use":
                inp = json.dumps(block.get("input", {}), ensure_ascii=False)
                parts.append(f"[tool:{block.get('name', '')} {inp[:200]}]")
            elif btype == "tool_result":
                rc = block.get("content", "")
                parts.append(f"[result: {_content_to_str(rc)[:300]}]")
            # image / document blocks carry no useful text; intentionally skipped
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        # Unusual but handle gracefully
        return json.dumps(content, ensure_ascii=False)
    return str(content) if content is not None else ""


def _parse_json(source: str) -> list[Turn]:
    data = json.loads(source)

    # Unwrap common container keys
    if isinstance(data, dict):
        for key in ("messages", "conversation", "chat_messages", "turns"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            # Maybe the whole dict is a single message
            if "role" in data or "type" in data:
                data = [data]
            else:
                raise ValueError("Unrecognized JSON dict structure")

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array")

    turns: list[Turn] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        role = _normalize_role(
            item.get("role") or item.get("type") or "unknown"
        )
        if role not in ("user", "assistant", "system"):
            continue
        content = _content_to_str(item.get("content", ""))
        if content.strip():
            turns.append(Turn(role=role, content=content, index=i))

    return turns


def _parse_jsonl(source: str) -> list[Turn]:
    turns: list[Turn] = []
    idx = 0
    for line in source.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        mtype = obj.get("type", "")
        if mtype not in ("user", "assistant"):
            continue
        inner   = obj.get("message", {})
        content = _content_to_str(inner.get("content", ""))
        if content.strip():
            turns.append(Turn(role=mtype, content=content, index=idx))
            idx += 1
    return turns


def _turns_from_matches(
    matches: list[re.Match],
    source: str,
    role_fn,          # callable(match) -> "user" | "assistant"
) -> list[Turn]:
    """
    Slice *source* into Turn objects using pre-computed regex match objects
    as turn-start markers.  Content runs from match.end() to the start of
    the next match (or EOF for the final turn).  Preamble before the first
    match is discarded automatically.  All Turn fields are keyword-assigned
    to satisfy the dataclass field ordering (index has a default; using
    positional args would require matching field order exactly).
    """
    turns: list[Turn] = []
    idx = 0
    for i, m in enumerate(matches):
        role          = role_fn(m)
        content_start = m.end()
        content_end   = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        content       = source[content_start:content_end].strip()
        if content:
            turns.append(Turn(role=role, content=content, index=idx))
            idx += 1
    return turns


def _parse_text(source: str) -> list[Turn]:
    """
    Parse a plain-text conversation into Turn objects.

    Three formats attempted in priority order:

    Format 1 — colon labels (most specific; tried first):
        "User: text"   "You: text"   "Claude: text"
        "**User**: text"  "**Assistant**: text"   (tool's own briefing output)
        "[2:30 PM] You: text"                      (timestamped variants)
        "Claude Sonnet 4.6: text"                  (model-name variants)

    Format 2 — solo-line labels (no colon; Claude Desktop native):
        A bare "You" or "Claude" alone on its own line, followed by the
        message text on subsequent lines.

    Format 3 — date-separator fallback (Claude Desktop copy-paste):
        "May 16" / "Jun 3" on its own line marks the START of each
        assistant response.  Content before the first date = user turn 0
        (never dropped).  Each subsequent inter-date block = assistant turn.
        NOTE: inter-date blocks may contain a concatenated Claude response
        AND the user's next message when no solo-line labels are present.
        Role assignment is approximate in this mode; treat briefings produced
        by Format 3 as structural scaffolds, not ground-truth transcripts.

    Frontmatter strip:
        If the source is one of this tool's own briefing documents, strip
        everything up through the "## CONVERSATION HISTORY" header line
        before running pattern scans, so the header/rules metadata does not
        create false turn splits.  Case-insensitive; handles both "##
        CONVERSATION HISTORY" and "## Conversation History" variants.
    """
    # ---- Frontmatter strip (case-insensitive) --------------------------------
    lower    = source.lower()
    ch_pos   = lower.find("## conversation history")
    if ch_pos != -1:
        newline_after = source.find("\n", ch_pos)
        source = source[newline_after + 1:] if newline_after != -1 else source[ch_pos:]

    # ---- Format 1: colon-separated role labels --------------------------------
    colon_matches = list(_COLON_RE.finditer(source))
    if len(colon_matches) >= 2:
        return _turns_from_matches(
            colon_matches,
            source,
            role_fn=lambda m: _normalize_role(m.group(1)),
        )

    # ---- Format 2: solo-line role labels (no colon) --------------------------
    solo_matches = list(_SOLO_RE.finditer(source))
    if len(solo_matches) >= 2:
        return _turns_from_matches(
            solo_matches,
            source,
            role_fn=lambda m: _normalize_role(m.group(1)),
        )

    # ---- Format 3: Claude Desktop date-separator fallback --------------------
    date_matches = list(_DATE_RE.finditer(source))
    if date_matches:
        turns: list[Turn] = []
        idx = 0
        # Capture content BEFORE the first date separator as user turn 0.
        pre = source[:date_matches[0].start()].strip()
        if pre:
            turns.append(Turn(role="user", content=pre, index=idx))
            idx += 1
        # Each post-date block is labeled assistant (dates precede Claude responses).
        for i, m in enumerate(date_matches):
            content_start = m.end()
            content_end   = date_matches[i + 1].start() if i + 1 < len(date_matches) else len(source)
            chunk = source[content_start:content_end].strip()
            if chunk:
                turns.append(Turn(role="assistant", content=chunk, index=idx))
                idx += 1
        if len(turns) >= 2:
            return turns

    # ---- Single-match edge case: use it rather than dropping the label -------
    if colon_matches:
        return _turns_from_matches(
            colon_matches, source, role_fn=lambda m: _normalize_role(m.group(1))
        )
    if solo_matches:
        return _turns_from_matches(
            solo_matches, source, role_fn=lambda m: _normalize_role(m.group(1))
        )

    # ---- Fallback: single blob ------------------------------------------------
    content = source.strip()
    return [Turn(role="user", content=content, index=0)] if content else []


# ---- Content cleaning --------------------------------------------------------

def strip_thinking(text: str) -> str:
    return THINKING_RE.sub("", text).strip()


def strip_xml_noise(text: str) -> str:
    return XML_NOISE_RE.sub("", text).strip()


def strip_ui_artifacts(text: str) -> str:
    """
    Remove Claude Desktop copy-paste UI chrome: the literal "Show more"
    expand-button label, and doubled thinking-summary lines (Claude Desktop
    renders the collapsed-thinking summary as both a label element and
    flattened text, so Ctrl+A/Ctrl+C/Ctrl+V produces it twice in a row).

    Only collapses adjacent duplicate lines at or under _DUP_LINE_MAX_LEN
    chars, so legitimate longer repeated content is left to deduplicate().
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line     = lines[i]
        stripped = line.strip()
        if stripped == "Show more":
            i += 1
            continue
        if (
            stripped
            and i + 1 < len(lines)
            and lines[i + 1].strip() == stripped
            and len(stripped) <= _DUP_LINE_MAX_LEN
        ):
            out.append(line)
            i += 2
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def clean(turn: Turn) -> Turn:
    """Remove noise from a turn without compressing any content."""
    c = strip_thinking(turn.content)
    c = strip_xml_noise(c)
    c = strip_ui_artifacts(c)
    c = re.sub(r"\n{3,}", "\n\n", c).strip()
    return Turn(role=turn.role, content=c, index=turn.index)


def strip_boilerplate(text: str) -> str:
    """
    Remove common LLM opening/closing filler from an assistant turn.
    Applied by the gentle prescription (and inherited by standard/aggressive).

    Targets:
      - Opening: "Of course!", "Certainly!", "I'd be happy to analyze..."
      - Opening v2: "Let me carefully review...", "I've thoroughly looked at..."
      - Closing: "Let me know if you need anything", "Feel free to ask", "Hope this helps"
    """
    # Strip boilerplate opening (first line only; count=1 prevents greedy sweep)
    text = _BOILERPLATE_OPEN_RE.sub("", text, count=1)
    text = _BOILERPLATE_OPENV2_RE.sub("", text, count=1)
    # Strip boilerplate closing (last matching line)
    text = _BOILERPLATE_CLOSE_RE.sub("", text)
    return text.strip()


def strip_acknowledgment(text: str) -> str:
    """
    Remove pure acknowledgment openers from an assistant turn.
    Applied by the standard prescription (in addition to strip_boilerplate).

    Targets first sentences that are entirely reactive with no actual content:
    "Yes, you're right about that.", "I understand.", "That's a great point."
    """
    return _ACK_OPENER_RE.sub("", text, count=1).strip()


# ---- Behavioral rule extraction ----------------------------------------------

def _sentence_around(text: str, start: int, end: int) -> str:
    """
    Extract the sentence containing the match at [start, end).

    v1.0.2 fix: the old implementation capped the left boundary at
    'start-250', which truncated sentence beginnings whenever the previous
    sentence-end punctuation was more than 250 chars away — causing "mid-word"
    starts and dropped parentheticals like "I had a lumbar spinal fusion (with
    hardware ... years of rehab), so I have..." being returned as
    "years of rehab), so I have...".

    v1.0.5 fix: the v1.0.2 re-anchor step triggered whenever the keyword's
    position exceeded HALF of MAX_RULE_LEN ('kw_pos > MAX_RULE_LEN // 2'),
    rather than checking whether a plain right-trim would actually cut the
    keyword off. On a 441-char sentence with the keyword at position 197
    (which fits comfortably within a 350-char right-trim), this still
    re-anchored and discarded 21 chars of perfectly-fittable leading context
    ("it's okay to hurt my ") for zero benefit, producing "feelings! it's
    CRUCIAL..." instead of "it's okay to hurt my feelings! it's CRUCIAL...".

    v1.0.6 fix: the period-followed-by-closing-punctuation gap ("...else.)
    hence...") losing its ")" was fixed at the boundary-finding stage, but
    a second, more subtle version of the same bug existed at the right-trim
    stage: a hard cut at exactly MAX_RULE_LEN chars can land precisely
    between a period and the closing punctuation the boundary extension
    just added, stripping it right back off again when the extension is
    itself what pushes the sentence 1+ chars over the cap. Found via direct
    construction of a sentence landing at exactly MAX_RULE_LEN chars before
    extension, not by inspection alone. Fix: the right-trim cut point now
    absorbs the same closing punctuation the boundary extension does,
    capped at 5 chars as a safety bound against pathological input (real
    prose never has long runs of consecutive closing punctuation).
    """
    # ---- left boundary: most recent sentence-end marker before match ------
    left_dot = text.rfind(".", 0, start)
    left_nl  = text.rfind("\n", 0, start)

    if left_dot != -1 and left_nl != -1:
        raw_left = max(left_dot + 1, left_nl + 1)
    elif left_dot != -1:
        raw_left = left_dot + 1
    elif left_nl != -1:
        raw_left = left_nl + 1
    else:
        raw_left = 0

    while raw_left < start and text[raw_left] in " \t":
        raw_left += 1
    left = raw_left

    # ---- right boundary: next sentence-end marker after match --------------
    right_dot = text.find(".", end)
    right_nl  = text.find("\n", end)

    if right_dot != -1 and right_nl != -1:
        right = min(right_dot + 1, right_nl)
    elif right_dot != -1:
        right = right_dot + 1
    elif right_nl != -1:
        right = right_nl
    else:
        right = len(text)

    # v1.0.6: if the sentence-ending period is immediately followed by
    # closing punctuation -- "...anywhere else.) hence why..." -- include
    # it too. Without this, "(luckily I don't really feel endangered
    # anywhere else.)" was extracted as "...anywhere else." with the
    # closing paren silently dropped, since the period (not the paren)
    # was what the boundary search matched on. Capped at 5 chars, same
    # bound as the right-trim absorption below -- without this cap, a
    # pathological run of consecutive closing punctuation could inflate
    # `result` arbitrarily before the length check even runs, making the
    # right-trim step's own cap meaningless (it only bounds what IT adds,
    # not what this earlier loop already pulled in).
    extended = 0
    while right < len(text) and text[right] in _CLOSING_PUNCT and extended < 5:
        right += 1
        extended += 1

    result  = text[left:right].strip()
    keyword = text[start:end]
    kw_pos  = result.find(keyword)
    if kw_pos == -1:
        kw_pos = max(0, start - left)  # fallback, should not normally happen

    # ---- MAX_RULE_LEN cap: only re-anchor if a plain right-trim would ------
    # ---- actually cut the keyword off; otherwise just right-trim normally -
    if len(result) > MAX_RULE_LEN:
        kw_end = kw_pos + len(keyword)
        if kw_end > MAX_RULE_LEN:
            new_left = max(0, kw_pos - MAX_RULE_LEN // 2)
            # Snap BACKWARD to the start of whatever word we're sitting in
            # the middle of, so re-anchoring never discards a leading word
            # entirely (a few extra included characters is harmless; losing
            # a whole word/sentence is not).
            if new_left > 0 and result[new_left - 1] != " ":
                prev_space = result.rfind(" ", 0, new_left)
                new_left = prev_space + 1 if prev_space != -1 else 0
            result = result[new_left:].strip()
        if len(result) > MAX_RULE_LEN:
            trimmed    = result[:MAX_RULE_LEN]
            last_space = trimmed.rfind(" ")
            cut_point  = last_space if last_space > MAX_RULE_LEN - 40 else MAX_RULE_LEN
            # Absorb a SMALL run of closing punctuation immediately after
            # the cut point (capped at 5 chars) so the hard truncation
            # doesn't strand an orphaned ")" right after it -- this is
            # exactly what happens when the boundary extension above is
            # itself what pushed the sentence just over MAX_RULE_LEN.
            absorbed = 0
            while (cut_point < len(result)
                   and result[cut_point] in _CLOSING_PUNCT
                   and absorbed < 5):
                cut_point += 1
                absorbed  += 1
            if cut_point >= len(result):
                # Absorption reached the natural end of the string --
                # nothing was actually removed, so no "…" marker belongs
                # here; adding one anyway would itself be a fabricated
                # truncation signal on text that was never cut.
                result = result[:cut_point]
            else:
                result = result[:cut_point] + "…"

    return result


def extract_rules(turns: list[Turn]) -> list[str]:
    """
    Extract explicit behavioral corrections from user turns.

    Implements a simplified version of cozempic's behavioral digest:
    the content most critical to carry forward when resetting context.
    Patterns: "don't do X", "never use Y", "always add Z",
              "from now on", "remember that", "make sure to" ...
    """
    seen:  set[str]  = set()
    rules: list[str] = []

    for turn in turns:
        if turn.role != "user":
            continue
        for regex in (CORRECTION_RE, IMPLICIT_CORRECTION_RE):
            for m in regex.finditer(turn.content):
                sentence = _sentence_around(turn.content, m.start(), m.end())
                if len(sentence) < 10 or len(sentence) > MAX_RULE_LEN:
                    continue
                key = re.sub(r"\s+", " ", sentence.lower().strip())
                if key in seen:
                    continue
                seen.add(key)
                rules.append(sentence)
                if len(rules) >= MAX_RULES:
                    return rules

    return rules


# ---- 1.1.0 Persistent Rule Store ---------------------------------------------

def _bigrams(text: str) -> set[str]:
    """Return word bigrams for informational overlap scoring only."""
    words = re.findall(r"\b\w+\b", text.lower())
    return {" ".join(pair) for pair in zip(words, words[1:])}


def _load_rules_store() -> dict:
    """Load the persistent rules store with SHA-256 checksum verification (FMECA F02)."""
    if not RULES_STORE_PATH.exists():
        return {"rules": [], "last_updated": None}
    try:
        with open(RULES_STORE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "rules" not in data:
            return {"rules": [], "last_updated": None}

        # Verify checksum if present
        if "checksum" in data:
            stored_checksum = data["checksum"]
            rules_str = json.dumps(data.get("rules", []), sort_keys=True)
            computed_checksum = hashlib.sha256(rules_str.encode("utf-8")).hexdigest()
            if stored_checksum != computed_checksum:
                # Checksum failed — try backup
                backup = RULES_STORE_PATH.with_suffix(".json.bak")
                if backup.exists():
                    try:
                        with open(backup, encoding="utf-8") as bf:
                            backup_data = json.load(bf)
                        if isinstance(backup_data, dict) and "rules" in backup_data:
                            return backup_data
                    except Exception:
                        pass
                # No valid backup — return empty to avoid corrupted data
                return {"rules": [], "last_updated": None}
        return data
    except Exception:
        return {"rules": [], "last_updated": None}


def _save_rules_store(data: dict) -> None:
    """Atomically save the rules store with SHA-256 checksum for strong integrity (FMECA F02/F06)."""
    RULES_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Compute checksum of the rules list
    rules_str = json.dumps(data.get("rules", []), sort_keys=True)
    checksum = hashlib.sha256(rules_str.encode("utf-8")).hexdigest()
    data["checksum"] = checksum

    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    _atomic_write(RULES_STORE_PATH, content)

    # Post-write integrity verification
    try:
        with open(RULES_STORE_PATH, encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict) or "rules" not in loaded or "checksum" not in loaded:
            raise ValueError("Store missing required fields")
        # Verify checksum
        loaded_rules_str = json.dumps(loaded.get("rules", []), sort_keys=True)
        loaded_checksum = hashlib.sha256(loaded_rules_str.encode("utf-8")).hexdigest()
        if loaded_checksum != loaded["checksum"]:
            raise ValueError("Checksum mismatch after write")
    except Exception as e:
        backup = RULES_STORE_PATH.with_suffix(".json.bak")
        if backup.exists():
            try:
                backup_content = backup.read_text(encoding="utf-8")
                _atomic_write(RULES_STORE_PATH, backup_content)
            except Exception:
                pass
        raise RuntimeError(f"Rule store integrity verification failed: {e}") from e
def merge_rules(new_rules: list[str], store: dict) -> tuple[list[str], list[dict]]:
    """
    Merge new rules into the store using exact-match only.

    Returns (final_rules, info_flags).
    info_flags contains entries with bigram overlap for informational use only.
    """
    existing = set(store.get("rules", []))
    final_rules = list(existing)
    info_flags: list[dict] = []

    for rule in new_rules:
        key = rule.strip()
        if not key:
            continue
        if key in existing:
            continue

        # Exact match first
        if key not in existing:
            final_rules.append(key)
            existing.add(key)

            # Bigram overlap is calculated for informational purposes only
            # (never used as a merge decision)
            overlaps = []
            for existing_rule in list(existing):
                if existing_rule == key:
                    continue
                b1 = _bigrams(key)
                b2 = _bigrams(existing_rule)
                if b1 and b2:
                    overlap = len(b1 & b2) / max(len(b1), len(b2))
                    if overlap >= 0.5:
                        overlaps.append({
                            "rule": existing_rule[:80],
                            "overlap": round(overlap, 2)
                        })

            if overlaps:
                info_flags.append({
                    "new_rule": key[:80],
                    "near_duplicates": overlaps[:3]
                })

    # When REVIEW_MODE=1, info_flags will contain near-duplicate candidates for manual review
    return final_rules, info_flags


def extract_rules_with_store(turns: list[Turn], use_store: bool = True) -> tuple[list[str], list[dict]]:
    """
    Extract rules and optionally merge with the persistent store.

    When use_store=False, behaves exactly like the original extract_rules().
    """
    fresh_rules = extract_rules(turns)  # original function

    # Safety net for critical rules (FMECA F01) - does not modify _sentence_around()
    safety_keywords = ("anti-trans hate crime", "physical safety", "jeopardy from an")
    for turn in turns:
        if turn.role != "user":
            continue
        for kw in safety_keywords:
            if kw.lower() in turn.content.lower():
                # Check if this safety content made it into fresh_rules
                found = any(kw.lower() in r.lower() for r in fresh_rules)
                if not found:
                    # Force include a minimal version of the safety rule
                    for sent in turn.content.split("."):
                        if kw.lower() in sent.lower() and len(sent) > 30:
                            fresh_rules.append(sent.strip() + ".")
                            break
                break

    if not use_store:
        return fresh_rules, []

    store = _load_rules_store()
    final_rules, info_flags = merge_rules(fresh_rules, store)

    # Update store
    store["rules"] = final_rules[:MAX_STORE_RULES]
    store["last_updated"] = datetime.now().isoformat()
    _save_rules_store(store)

    return final_rules, info_flags


# ---- Deduplication -----------------------------------------------------------

def deduplicate(turns: list[Turn]) -> list[Turn]:
    """
    Remove turns whose first 2000 chars hash to the same value as an
    earlier turn, keeping only the MOST RECENT occurrence of each.
    """
    hash_to_last: dict[str, int] = {}
    for i, turn in enumerate(turns):
        key = hashlib.md5(turn.content[:2000].encode("utf-8")).hexdigest()
        hash_to_last[key] = i  # always overwrite with the latest index

    keep = set(hash_to_last.values())
    return [t for i, t in enumerate(turns) if i in keep]


def collapse_exact_repeats(turns: list[Turn]) -> list[Turn]:
    """
    Collapse EXACT (whitespace-normalized) repeated text chunks that recur
    across different assistant turns, keeping the FIRST occurrence in full
    and replacing later occurrences with a compact, self-contained marker.
    Unlike deduplicate() (whole-turn, keeps latest), this works at
    sentence/paragraph granularity within otherwise-unique turns and keeps
    the first occurrence, since a briefing is read top-to-bottom and the
    first appearance is where the context is actually established.

    Deliberately EXACT-match only, never fuzzy/near-duplicate. A fuzzy pass
    using difflib.SequenceMatcher was built and tested against a real
    conversation before this was written, and rejected: even at 0.90-0.96
    similarity ratio it routinely flagged sentence pairs differing only in
    the exact detail that matters in a conversation built around precise
    physical/style constraints -- e.g. "Ran 2 commands...19/19 checks" vs
    "Ran 3 commands...21/21 checks", "Add those two items" vs "Add that one
    item", "barely brushing waistband" vs "brushing waistband". Character-
    level similarity does not track semantic importance, so only chunks
    that are byte-identical after whitespace normalization are ever
    touched here -- there is no ratio at which two non-identical strings
    are safe to silently merge in this tool's intended use case.

    _MIN_COLLAPSE_LEN guards against collapsing short repeated verdicts
    ("Select it.", "Reject it.") that are real per-item decisions, not
    redundant restatement, even though they legitimately repeat verbatim
    across many distinct items.

    Only ever called on the "old" turn set in prune(); recent/verbatim
    turns are never passed to this function, so the verbatim guarantee for
    them is completely unaffected regardless of what repeats elsewhere.
    """
    seen: dict[str, int] = {}
    result: list[Turn] = []

    for turn in turns:
        if turn.role != "assistant":
            result.append(turn)
            continue

        parts = _REPEAT_SPLIT_RE.split(turn.content)
        new_parts: list[str] = []
        for idx, part in enumerate(parts):
            if idx % 2 == 1:
                new_parts.append(part)  # separator: keep verbatim, untouched
                continue
            key = re.sub(r"\s+", " ", part.strip())
            if len(key) >= _MIN_COLLAPSE_LEN and key in seen:
                preview = key[:50].rstrip()
                leading  = part[:len(part) - len(part.lstrip())]
                trailing = part[len(part.rstrip()):]
                new_parts.append(f'{leading}[Repeated, unchanged: "{preview}..."]{trailing}')
            else:
                if len(key) >= _MIN_COLLAPSE_LEN:
                    seen.setdefault(key, turn.index)
                new_parts.append(part)

        new_content = "".join(new_parts)
        result.append(Turn(role=turn.role, content=new_content, index=turn.index))

    return result


# ---- Compression (aggressive prescription only) ------------------------------

def compress(turn: Turn) -> Turn:
    """
    Compress a turn to its most informative sentences.
    Code blocks are NEVER modified; first paragraph is always kept verbatim.
    Only applied to old turns under the aggressive prescription.
    """
    content = turn.content

    # Protect code blocks before any processing
    saved_blocks: list[str] = []

    def _save_block(m: re.Match) -> str:
        saved_blocks.append(m.group(0))
        return f"\x00CB{len(saved_blocks)-1}\x00"

    content = CODE_BLOCK_RE.sub(_save_block, content)
    content = strip_thinking(content)
    content = strip_xml_noise(content)

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", content) if p.strip()]

    def _restore(text: str) -> str:
        for i, block in enumerate(saved_blocks):
            text = text.replace(f"\x00CB{i}\x00", block)
        return text

    # Short or code-only turn: just restore and return
    if len(paragraphs) <= 2:
        return Turn(role=turn.role, content=_restore(content).strip(), index=turn.index)

    result_parts: list[str] = []

    # Always keep the first paragraph (usually the key question or decision)
    result_parts.append(_restore(paragraphs[0]))

    for para in paragraphs[1:]:
        para_restored = _restore(para)
        # Any paragraph that contains a code block is kept in full
        if "```" in para_restored:
            result_parts.append(para_restored)
            continue
        # Non-code paragraphs: extract high-signal sentences
        sentences = re.split(r"(?<=[.!?])\s+", para_restored)
        key_sents: list[str] = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 20:
                continue
            if re.search(
                r"\b(?:error|result|output|fixed|fix|note|warning|important|"
                r"must|should|resolved|completed|configured|installed|"
                r"returns?|raises?|set|use|run|add|remove|decided|conclusion)\b",
                sent, re.IGNORECASE,
            ):
                key_sents.append(f"- {sent}")
        if key_sents:
            result_parts.extend(key_sents[:4])

    result = "\n\n".join(result_parts)

    orig_t = turn.tokens()
    comp_t = int(len(result) / CHARS_PER_TOKEN)
    if orig_t > comp_t + 30:
        result = f"[~{orig_t}to{comp_t}t]\n{result}"

    return Turn(role=turn.role, content=result, index=turn.index)


# ---- Main prune orchestrator -------------------------------------------------

_PRESCRIPTIONS: dict[str, dict[str, bool]] = {
    "gentle":     {"boilerplate": True,  "acknowledge": False, "dedup": False, "compress": False, "collapse_repeats": False},
    "standard":   {"boilerplate": True,  "acknowledge": True,  "dedup": True,  "compress": False, "collapse_repeats": True},
    "aggressive": {"boilerplate": True,  "acknowledge": True,  "dedup": True,  "compress": True,  "collapse_repeats": True},
}


def prune(
    turns:        list[Turn],
    verbatim:     int = DEFAULT_VERBATIM,
    prescription: str = "standard",
) -> tuple[list[Turn], PruneStats]:
    """
    Main pruning entry point.
    verbatim: number of most-recent turns to keep untouched.
    prescription: "gentle" | "standard" | "aggressive"
    """
    if prescription not in _PRESCRIPTIONS:
        prescription = "standard"
    cfg = _PRESCRIPTIONS[prescription]

    orig_tokens = sum(t.tokens() for t in turns)
    rules, _    = extract_rules_with_store(turns, use_store=True)

    # Clamp verbatim to [0, len(turns)]
    verbatim = max(0, min(verbatim, len(turns)))

    if verbatim == 0:
        old, recent = turns, []
    elif verbatim >= len(turns):
        old, recent = [], turns
    else:
        old    = turns[:-verbatim]
        recent = turns[-verbatim:]

    # Process older turns
    processed: list[Turn] = []
    for t in old:
        c = clean(t)
        if cfg["boilerplate"] and c.role == "assistant":
            stripped = strip_boilerplate(c.content)
            if stripped:
                c = Turn(role=c.role, content=stripped, index=c.index)
        if cfg["acknowledge"] and c.role == "assistant":
            stripped = strip_acknowledgment(c.content)
            if stripped:
                c = Turn(role=c.role, content=stripped, index=c.index)
        processed.append(c)
    if cfg["dedup"]:
        processed = deduplicate(processed)
    if cfg["collapse_repeats"]:
        processed = collapse_exact_repeats(processed)
    if cfg["compress"]:
        processed = [compress(t) for t in processed]

    # Clean recent turns (noise only; never compress)
    cleaned_recent = [clean(t) for t in recent]

    final = processed + cleaned_recent
    # Drop turns that became empty after cleaning
    final = [t for t in final if t.content.strip()]

    final_tokens = sum(t.tokens() for t in final)
    saved = orig_tokens - final_tokens
    pct   = round(saved / orig_tokens * 100, 1) if orig_tokens > 0 else 0.0

    return final, PruneStats(
        orig_turns   = len(turns),
        final_turns  = len(final),
        orig_tokens  = orig_tokens,
        final_tokens = final_tokens,
        saved_tokens = saved,
        saved_pct    = pct,
        prescription = prescription,
        verbatim     = verbatim,
        rules_found  = len(rules),
        rules        = rules,
    )


# ---- Briefing document generator ---------------------------------------------

def create_briefing(turns: list[Turn], verbatim: int = DEFAULT_VERBATIM) -> str:
    """
    Produce a structured briefing document for starting a fresh conversation.
    Paste this as the first message in a new Claude Desktop chat.

    Structure:
      1. Compression stats header
      2. Behavioral rules (extracted corrections) — read first
      3. Compressed conversation history
      4. Most recent N turns verbatim
    """
    rules, _ = extract_rules_with_store(turns, use_store=True)
    pruned, stats = prune(turns, verbatim, "aggressive")
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = [
        "# CONVERSATION BRIEFING",
        f"*Compressed by context_surgeon v{__version__} on {ts}*",
        "",
        f"*Original: {stats.orig_turns} turns, ~{stats.orig_tokens:,} tokens*",
        f"*Compressed: {stats.final_turns} turns, ~{stats.final_tokens:,} tokens*",
        f"*Saved: {stats.saved_pct}% | Last {verbatim} turns verbatim*",
        "",
        "> **How to use**: Paste this entire document as your first message in a new",
        "> Claude Desktop conversation. It carries forward your behavioral corrections,",
        "> compressed history, and verbatim recent context; without the native compact's",
        "> overgeneralization.",
        "",
    ]

    if rules:
        lines += [
            "---",
            "",
            "## BEHAVIORAL RULES",
            "*These corrections were explicitly stated during the original conversation.*",
            "*Apply them throughout this session.*",
            "",
        ]
        lines += [f"- {r}" for r in rules]
        lines.append("")

    lines += [
        "---",
        "",
        "## CONVERSATION HISTORY",
        f"*Older turns: aggressive compression (code blocks always verbatim).*",
        f"*Last {verbatim} turns: verbatim.*",
        "",
    ]

    for turn in pruned:
        label = "**User**" if turn.role == "user" else "**Assistant**"
        lines.append(f"{label}: {turn.content}")
        lines.append("")

    lines += [
        "---",
        f"*context_surgeon v{__version__} ; github.com/fishboyrocks/cozempic-2.0*",
    ]

    return "\n".join(lines)


# ---- Diagnosis ---------------------------------------------------------------

def diagnose_text(turns: list[Turn]) -> str:
    """Return a formatted diagnosis report as a string."""
    if not turns:
        return "No turns found."

    total_chars  = sum(len(t.content) for t in turns)
    total_tokens = sum(t.tokens() for t in turns)
    ctx_pct      = total_tokens / DEFAULT_CONTEXT_WIN * 100

    thinking_n = sum(1 for t in turns if THINKING_RE.search(t.content))
    xml_n      = sum(1 for t in turns if XML_NOISE_RE.search(t.content))
    rules      = extract_rules(turns)

    hashes: dict[str, int] = {}
    for t in turns:
        key = hashlib.md5(t.content[:2000].encode("utf-8")).hexdigest()
        hashes[key] = hashes.get(key, 0) + 1
    dupes = sum(1 for v in hashes.values() if v > 1)

    top5 = sorted(turns, key=lambda t: t.tokens(), reverse=True)[:5]

    sep   = "-" * 56
    lines = [
        sep,
        "CONTEXT SURGEON -- DIAGNOSIS",
        sep,
        f"Turns:              {len(turns)}",
        f"Characters:         {total_chars:,}",
        f"Tokens (est.):      {total_tokens:,}",
        f"Context fill:       {ctx_pct:.1f}%  (200 K window baseline)",
        "",
        "Noise detected:",
        f"  Thinking blocks:  {thinking_n}",
        f"  XML noise turns:  {xml_n}",
        f"  Duplicate turns:  {dupes}",
        f"  Correction rules: {len(rules)}",
        "",
        "Largest 5 turns:",
    ]
    for t in top5:
        bar = "#" * min(24, t.tokens() // 200)
        lines.append(f"  {bar} Turn {t.index:>3} ({t.role:<9}): ~{t.tokens():,} tokens")

    lines += [
        "",
        "Estimated savings by prescription:",
    ]
    for rx in ("gentle", "standard", "aggressive"):
        _, s = prune(turns, DEFAULT_VERBATIM, rx)
        lines.append(
            f"  {rx:<12}  ~{s.saved_tokens:,} tokens saved  ({s.saved_pct}%)"
        )
    lines.append(sep)
    return "\n".join(lines)


# ---- Claude Desktop discovery ------------------------------------------------

def find_data_dirs() -> list[Path]:
    """Locate all candidate Claude Desktop data directories on this machine."""
    home = Path.home()
    candidates: list[Path] = []
    if sys.platform == "win32":
        appdata      = os.environ.get("APPDATA")      or str(home / "AppData" / "Roaming")
        localappdata = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        candidates   = [
            Path(appdata)      / "Claude",
            Path(localappdata) / "Claude",
            home / ".claude",    # Claude Code also uses this; may overlap
        ]
    elif sys.platform == "darwin":
        candidates = [
            home / "Library" / "Application Support" / "Claude",
            home / ".claude",
        ]
    else:
        xdg        = os.environ.get("XDG_CONFIG_HOME") or str(home / ".config")
        candidates = [
            Path(xdg) / "Claude",
            home / ".local" / "share" / "Claude",
            home / ".claude",
        ]
    return [p for p in candidates if p.exists()]


def find_mcp_config() -> Path | None:
    """Locate claude_desktop_config.json."""
    home = Path.home()
    if sys.platform == "win32":
        appdata   = os.environ.get("APPDATA") or str(home / "AppData" / "Roaming")
        candidate = Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "darwin":
        candidate = (
            home / "Library" / "Application Support"
            / "Claude" / "claude_desktop_config.json"
        )
    else:
        xdg       = os.environ.get("XDG_CONFIG_HOME") or str(home / ".config")
        candidate = Path(xdg) / "Claude" / "claude_desktop_config.json"
    return candidate if candidate.exists() else None


# ---- MCP server (pure stdlib; zero external dependencies) --------------------

_TOOLS = [
    {
        "name": "diagnose_conversation",
        "description": (
            "Analyze a Claude Desktop conversation for context bloat. "
            "Returns token estimates, noise counts, duplicate turns, and "
            "savings projections for each prescription tier. "
            "Supports JSON export, JSONL, or plain User:/Assistant: text."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_text": {
                    "type": "string",
                    "description": "The conversation to analyze (JSON, JSONL, or plain text)",
                }
            },
            "required": ["conversation_text"],
        },
    },
    {
        "name": "prune_conversation",
        "description": (
            "Surgically prune a conversation to reduce token count without losing nuance. "
            "Strips thinking blocks and XML noise from all turns; deduplicates repeated content; "
            "optionally compresses verbose older turns (code blocks are always kept verbatim). "
            "Keeps the most recent N turns character-perfect. "
            "Returns the pruned conversation text and statistics."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_text": {"type": "string"},
                "verbatim_turns": {
                    "type": "integer",
                    "description": "Recent turns to keep verbatim (default 10)",
                    "default": 10,
                },
                "prescription": {
                    "type": "string",
                    "enum": ["gentle", "standard", "aggressive"],
                    "description": (
                        "gentle=noise only; standard=+dedup; "
                        "aggressive=+compress old turns"
                    ),
                    "default": "standard",
                },
            },
            "required": ["conversation_text"],
        },
    },
    {
        "name": "create_briefing",
        "description": (
            "Create a structured briefing document to paste at the start of a fresh conversation. "
            "Extracts behavioral corrections ('don't do X', 'always Y') and leads with them. "
            "Compresses old turns aggressively; keeps recent N turns verbatim. "
            "Use this when your conversation is approaching its context limit; "
            "paste the output as the first message in a new Claude Desktop chat."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_text": {"type": "string"},
                "verbatim_turns": {
                    "type": "integer",
                    "description": "Recent turns to keep verbatim (default 10)",
                    "default": 10,
                },
            },
            "required": ["conversation_text"],
        },
    },
    {
        "name": "extract_rules",
        "description": (
            "Extract behavioral correction rules from a conversation. "
            "Scans for 'don't do X', 'always Y', 'from now on', 'remember that' patterns. "
            "These are the highest-value content to preserve when resetting context; "
            "paste them at the top of a new conversation to maintain continuity."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_text": {"type": "string"},
            },
            "required": ["conversation_text"],
        },
    },
]


def _call_tool(name: str, args: dict) -> str:
    """Dispatch an MCP tool call and return the result as text."""
    text  = args.get("conversation_text", "")
    if len(text) > MCP_MAX_INPUT_CHARS:
        return f"ERROR: Input too large ({len(text):,} chars). Maximum allowed: {MCP_MAX_INPUT_CHARS:,} chars. Use the CLI for large conversations."

    turns = parse_conversation(text)

    if name == "diagnose_conversation":
        if not turns:
            return (
                "No turns found. Paste the conversation (JSON export, JSONL, "
                "or User: / Assistant: plain text)."
            )
        return diagnose_text(turns)

    if name == "prune_conversation":
        if not turns:
            return "No turns found."
        v  = max(0, int(args.get("verbatim_turns", DEFAULT_VERBATIM)))
        rx = str(args.get("prescription", "standard"))
        pruned_turns, stats = prune(turns, v, rx)
        sep = "-" * 40
        out: list[str] = [
            f"Pruned: {stats.orig_turns} to {stats.final_turns} turns | "
            f"~{stats.orig_tokens:,} to ~{stats.final_tokens:,} tokens | "
            f"{stats.saved_pct}% saved",
            "",
        ]
        if stats.rules:
            out.append("Behavioral rules preserved:")
            out.extend(f"  - {r}" for r in stats.rules)
            out.append("")
        out.append("PRUNED CONVERSATION:")
        out.append(sep)
        for t in pruned_turns:
            label = "User" if t.role == "user" else "Assistant"
            out.append(f"{label}: {t.content}")
            out.append("")
        return "\n".join(out)

    if name == "create_briefing":
        if not turns:
            return "No turns found."
        v = max(0, int(args.get("verbatim_turns", DEFAULT_VERBATIM)))
        return create_briefing(turns, v)

    if name == "extract_rules":
        if not turns:
            return "No turns found."
        rules, info_flags = extract_rules_with_store(turns, use_store=True)
        if not rules:
            return "No behavioral correction rules detected in this conversation."
        sep = "-" * 40
        out = ["BEHAVIORAL CORRECTIONS:", sep]
        out.extend(f"{i}. {r}" for i, r in enumerate(rules, 1))
        if info_flags:
            out.append("")
            out.append("Near-duplicate candidates (informational only):")
            for flag in info_flags[:3]:
                out.append(f"  - {flag['new_rule']}")
        return "\n".join(out)

    return f"Unknown tool: {name}"


def run_mcp() -> None:
    """
    Run as an MCP server using line-delimited JSON-RPC 2.0 over stdio.
    Handles initialize, tools/list, tools/call, ping.
    Notifications (no id field) are silently ignored per the MCP spec.
    """
    SERVER_INFO = {"name": "context-surgeon", "version": __version__}

    while True:
        try:
            raw = sys.stdin.readline()
        except (KeyboardInterrupt, EOFError):
            break
        if not raw:
            break
        raw = raw.strip()
        if not raw:
            continue

        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            continue

        req_id = req.get("id")        # None for notifications
        method = req.get("method", "")
        params = req.get("params") or {}

        # Per MCP spec: notifications have no id; send no response.
        if req_id is None:
            continue

        resp: dict = {"jsonrpc": "2.0", "id": req_id}

        try:
            if method == "initialize":
                resp["result"] = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO,
                }
            elif method == "tools/list":
                resp["result"] = {"tools": _TOOLS}
            elif method == "tools/call":
                result_text = _call_tool(
                    params.get("name", ""),
                    params.get("arguments") or {},
                )
                resp["result"] = {
                    "content": [{"type": "text", "text": result_text}]
                }
            elif method == "ping":
                resp["result"] = {}
            else:
                resp["result"] = {}
        except Exception as exc:
            resp["error"] = {
                "code": -32603,
                "message": f"Internal error: {exc}",
            }

        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


# ---- Atomic write helper (1.1.0) --------------------------------------------

def _atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Write content to *path* atomically.

    Uses a unique temporary file in the same directory, fsync before
    rename, and os.replace for the final atomic swap. This guarantees
    that on crash the target either contains the old complete file or
    the new complete file — never a truncated partial write.

    This is the recommended pattern for any file that a user may
    repeatedly overwrite (briefings, config files).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use a unique suffix so concurrent runs cannot collide
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_path)

    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, path)
    except Exception:
        # Clean up the temp file on any failure
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


# ---- CLI commands ------------------------------------------------------------

def _read_input(path: str) -> str:
    """Read conversation source from a file path or stdin ('-')."""
    if path == "-":
        return sys.stdin.read()
    p = Path(path)
    if not p.exists():
        print(f"Error: file not found: {p}", file=sys.stderr)
        sys.exit(1)
    try:
        return p.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_discover(_: argparse.Namespace) -> None:
    sep = "-" * 56
    print(f"\nCONTEXT SURGEON -- DISCOVERY\n{sep}")

    dirs = find_data_dirs()
    if dirs:
        for d in dirs:
            print(f"\nFound: {d}")
            try:
                items = sorted(d.rglob("*"))
            except PermissionError:
                print("  (permission denied reading directory contents)")
                continue
            for item in items[:60]:
                if not item.is_file():
                    continue
                try:
                    kb = item.stat().st_size // 1024
                except OSError:
                    kb = 0
                flag = ""
                suf    = item.suffix.lower()
                name_l = item.name.lower()
                if suf in (".db", ".sqlite", ".sqlite3"):
                    flag = "  <- SQLite database"
                elif suf == ".jsonl":
                    flag = "  <- JSONL session (cozempic-compatible)"
                elif "config" in name_l and suf == ".json":
                    flag = "  <- Config file"
                elif any(k in str(item).lower() for k in ("indexeddb", "leveldb")):
                    flag = "  <- LevelDB / IndexedDB"
                try:
                    rel = item.relative_to(d)
                    print(f"  {rel}  ({kb} KB){flag}")
                except ValueError:
                    print(f"  {item}  ({kb} KB){flag}")
    else:
        print("No Claude Desktop data directory found.")
        print("Is Claude Desktop installed?")

    print()
    cfg = find_mcp_config()
    if cfg:
        print(f"MCP config: {cfg}")
        try:
            with open(cfg, encoding="utf-8") as f:
                data = json.load(f)
            svrs = data.get("mcpServers", {})
            print(f"  Configured servers: {', '.join(svrs) or '(none)'}")
        except Exception:
            print("  (could not parse config file)")
    else:
        print("MCP config: not found -- run setup-mcp to create it.")

    print(f"\nPython: {sys.version}")
    print(f"Platform: {sys.platform} / {platform.machine()}")


def cmd_diagnose(args: argparse.Namespace) -> None:
    source = _read_input(args.file)
    turns  = parse_conversation(source)
    if not turns:
        print(
            "No turns found. Supported formats: JSON, JSONL, "
            "plain text (User: / Assistant: alternation).",
            file=sys.stderr,
        )
        sys.exit(1)
    print(diagnose_text(turns))


def cmd_prune(args: argparse.Namespace) -> None:
    source = _read_input(args.file)
    turns  = parse_conversation(source)
    if not turns:
        print("No turns found.", file=sys.stderr)
        sys.exit(1)

    briefing = create_briefing(turns, args.verbatim)
    _, stats  = prune(turns, args.verbatim, args.rx)

    sep = "-" * 56
    print(sep, file=sys.stderr)
    print("PRUNING COMPLETE", file=sys.stderr)
    print(sep, file=sys.stderr)
    print(f"Turns:   {stats.orig_turns} -> {stats.final_turns}", file=sys.stderr)
    print(f"Tokens:  ~{stats.orig_tokens:,} -> ~{stats.final_tokens:,}", file=sys.stderr)
    print(f"Saved:   ~{stats.saved_tokens:,} tokens  ({stats.saved_pct}%)", file=sys.stderr)
    print(f"Rules:   {stats.rules_found} behavioral corrections preserved", file=sys.stderr)
    for r in stats.rules[:5]:
        print(f"         -> {r[:72]}", file=sys.stderr)
    print(sep, file=sys.stderr)

    output_path = getattr(args, "output", None)
    if output_path:
        _atomic_write(Path(output_path), briefing)
        print(f"\nBriefing saved -> {output_path}", file=sys.stderr)
        print(
            "Paste its contents as the first message in a new "
            "Claude Desktop conversation.",
            file=sys.stderr,
        )
    else:
        print(briefing)


def cmd_setup_mcp(_: argparse.Namespace) -> None:
    """Register context_surgeon.py as a Claude Desktop MCP server."""
    script  = str(Path(sys.argv[0]).resolve())
    python  = sys.executable

    cfg_path = find_mcp_config()
    if cfg_path is None:
        # Create the config file in the expected location
        home = Path.home()
        if sys.platform == "win32":
            appdata  = os.environ.get("APPDATA") or str(home / "AppData" / "Roaming")
            cfg_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
        elif sys.platform == "darwin":
            cfg_path = (
                home / "Library" / "Application Support"
                / "Claude" / "claude_desktop_config.json"
            )
        else:
            xdg      = os.environ.get("XDG_CONFIG_HOME") or str(home / ".config")
            cfg_path = Path(xdg) / "Claude" / "claude_desktop_config.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        config: dict = {}
    else:
        try:
            with open(cfg_path, encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["context-surgeon"] = {
        "command": python,
        "args":    [script, "--mcp"],
    }

    # Backup before writing
    if cfg_path.exists():
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = cfg_path.with_suffix(f".{ts}.bak")
        shutil.copy2(cfg_path, backup)
        print(f"Config backed up -> {backup}")

    _atomic_write(cfg_path, json.dumps(config, indent=2, ensure_ascii=False) + "\n")

    print(f"\ncontext-surgeon registered in:\n  {cfg_path}")
    print("Next step: restart Claude Desktop.")
    print("Available MCP tools after restart:")
    for t in _TOOLS:
        print(f"  {t['name']}")
    print("Workflow:")
    print("  1. Conversation approaching its context limit?")
    print("     Call create_briefing with your conversation text pasted in.")
    print("  2. Start a new conversation; paste the briefing as the first message.")
    print("  3. Continue -- full context headroom, no nuance lost.")
    print("Or use the CLI directly (no MCP needed):")
    print(f"  python {script} prune conversation.txt --output briefing.md")


# ---- CLI parser --------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="context_surgeon",
        description=(
            "Surgical context cleaning for Claude Desktop. "
            "Scalpel precision; not the native compact's sledgehammer."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(f"""
        EXAMPLES
          python context_surgeon.py discover
          python context_surgeon.py diagnose conversation.json
          python context_surgeon.py prune conversation.json
          python context_surgeon.py prune conversation.txt --verbatim 15 --rx aggressive
          python context_surgeon.py prune conversation.txt --output briefing.md
          python context_surgeon.py prune - < pasted_convo.txt
          python context_surgeon.py setup-mcp

        PRESCRIPTIONS
          gentle      strip thinking blocks + XML noise only
          standard    + deduplicate repeated-content turns        [default]
          aggressive  + compress verbose older turns
                        (code blocks are ALWAYS kept verbatim)

        v{__version__} -- github.com/fishboyrocks/cozempic-2.0
        """),
    )
    p.add_argument("--mcp",     action="store_true", help="Run as MCP server (stdio transport)")
    p.add_argument("--version", action="version",    version=f"context_surgeon {__version__}")

    sub = p.add_subparsers(dest="command")

    sub.add_parser("discover",   help="Find Claude Desktop data directories + MCP config")

    pd = sub.add_parser("diagnose", help="Analyze a conversation for bloat and savings potential")
    pd.add_argument("file", help="Conversation file or - for stdin")

    pp = sub.add_parser("prune", help="Prune and generate a fresh-start briefing document")
    pp.add_argument("file", help="Conversation file or - for stdin")
    pp.add_argument(
        "--verbatim", type=int, default=DEFAULT_VERBATIM,
        help=f"Recent turns to preserve verbatim (default {DEFAULT_VERBATIM})",
    )
    pp.add_argument(
        "--rx", choices=list(_PRESCRIPTIONS), default="standard",
        help="Pruning prescription (default: standard)",
    )
    pp.add_argument(
        "--output", "-o", metavar="FILE",
        help="Save briefing to this file (default: stdout)",
    )

    sub.add_parser("setup-mcp", help="Register as a Claude Desktop MCP server (run once; then restart Claude Desktop)")
    return p


# ---- Entry point -------------------------------------------------------------

def main() -> None:
    check_prerequisites()
    parser = _build_parser()
    args   = parser.parse_args()

    if args.mcp:
        run_mcp()
        return

    commands = {
        "discover":  cmd_discover,
        "diagnose":  cmd_diagnose,
        "prune":     cmd_prune,
        "setup-mcp": cmd_setup_mcp,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
