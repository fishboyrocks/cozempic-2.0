# Context Surgeon

### Surgical context cleaning for Claude Desktop; the scalpel, not the sledgehammer.

---

## What This Is

Claude Desktop conversations have a **context limit**: a fixed amount of text and image data Claude can hold in its head at once. When a conversation gets long enough, Claude Desktop will offer to "compact" it. The native compact replaces your entire conversation history with a vague summary blob. Behavioral corrections you gave Claude, specific technical details, nuanced analysis, decisions that took hours to establish; all of it gets flattened into something generic and useless.

**Context Surgeon does the opposite.** It strips actual bloat (thinking blocks, repeated system tags, duplicate content) while surgically extracting and preserving the things that matter most: your explicit corrections ("don't use em dashes"), technical decisions, and the most recent turns of conversation verbatim. The output is a structured briefing document you paste into a fresh conversation to pick up exactly where you left off.

---

## What's New in v1.2.0

- **Persistent Rule Store** — Behavioral corrections are now saved to `~/.config/context-surgeon/rules.json` with SHA-256 checksum verification, automatic backup, and recovery on corruption. Rules accumulate across conversations instead of being lost on every reset.
- **Configurable Parameters** — Store path, capacity, verbatim turns, review mode, and version checking are all configurable via environment variables.
- **Rules Status Command** — `rules-status` shows current rule count, capacity percentage, and status at a glance.
- **Review Mode** — Optional mode to surface near-duplicate rule candidates for manual review before they are merged.
- **Hardened Safety Features** — Multiple layers of protection for critical rules, including a safety net that forces inclusion of safety-critical rules if extraction fails, and guaranteed preservation of safety-critical sentences even when they exceed normal length limits.
- **Audit Logging** — Rule store changes are logged with timestamps for traceability.

---

## Critical Facts About Image-Heavy Conversations

This section applies directly if your conversation contains uploaded image files that Claude has analyzed.

**Images are not text.** When Claude analyzes images you attach, those images are sent to Anthropic's servers as visual data and consume a substantial chunk of your context window. A typical image uses 1,000 to 2,000 tokens. Thirty images means potentially 30,000 to 60,000 tokens devoted to image data alone.

**Here is what Context Surgeon can and cannot do with an image-heavy conversation:**

| What it CAN do | What it CANNOT do |
|---|---|
| Compress Claude's text analysis of the images | Compress the image pixel data itself |
| Extract key conclusions from image discussions | "Un-send" images to reclaim their tokens |
| Preserve correction rules and decisions | Capture image content in the copy-paste step |
| Create a text briefing you can continue from | Make images automatically re-appear in a new chat |

**The practical upshot:** Context Surgeon compresses the text portion of your conversation, which can still save 40 to 60 percent of your token budget. For the image tokens, the solution is different: when you start a fresh conversation using the briefing, you simply re-attach only the images that are still relevant to ongoing work. Images from earlier analysis stages that are already summarized in the briefing do not need to come with you.

**For any conversation with more than about ten images or files, use the command-line workflow (Option B below), not the MCP workflow.** Pasting fifty thousand words of conversation history into another Claude chat to run the MCP tool would itself use most of that chat's context window. The command line bypasses this entirely.

---

## Prerequisites

You need **Python 3.10 or newer**. That is the only requirement; the script uses no additional packages.

**Check if you already have it:**
1. Press `Win + R`, type `cmd`, press Enter.
2. In the black window that opens, type:
   ```
   python --version
   ```
3. If you see `Python 3.10.x` or higher, you are ready.
4. If you see `Python 3.8` or older, or if Windows says the command is not recognized, you need to install it.

**Install Python 3.10+:**
1. Go to **https://www.python.org/downloads/**
2. Click the yellow "Download Python 3.x.x" button.
3. Run the installer. **On the first screen, check the box that says "Add Python to PATH"** before clicking Install. This step is mandatory; skipping it means the commands below will not work.
4. After installation, close and reopen the Command Prompt window.
5. Run `python --version` again to confirm it works.

---

## Installation

**Step 1: Download the script.**
1. Go to **https://github.com/fishboyrocks/cozempic-2.0**
2. Click on `context_surgeon.py` in the file list.
3. Click the download button (the icon that looks like a downward arrow with a line under it, in the top-right area of the file view).
4. Save the file somewhere permanent. A good location is your Documents folder: `C:\Users\YourName\Documents\context_surgeon.py`

**Step 2: Register it as a Claude Desktop MCP server.**

Open Command Prompt (`Win + R`, type `cmd`, Enter) and run:
```
python C:\Users\YourName\Documents\context_surgeon.py setup-mcp
```
Replace `YourName` with your actual Windows username. The script will print a confirmation message and the location of your Claude Desktop config file.

**Step 3: Restart Claude Desktop completely.**
Close it from the system tray (right-click the Claude icon in the bottom-right corner of your screen, then "Quit") and reopen it. The MCP tools are not active until you do this.

**Step 4: Verify it worked.**
In a new Claude Desktop conversation, type:
```
Use the diagnose_conversation tool with this text: Hello world
```
If Claude responds with something like "No turns found" instead of an error about a missing tool, the MCP is active.

---

## How to Get Your Conversation Text Out of Claude Desktop

This is the step most instructions skip. There are two approaches depending on what is available in your version of Claude Desktop.

### Method A: Look for a Share or Export button (check your version first)

Claude Desktop may have a share or export feature. Look for:
- A share icon (box with an arrow pointing up) at the top of a conversation
- A `...` menu or three-dot menu near the conversation title
- A "Share conversation" option when you right-click the conversation in the sidebar

If you find one, use it. An option to copy the conversation as text or download it is ideal. The exact location and availability of this feature depends on your version of Claude Desktop; if you do not see it, use Method B.

### Method B: Copy and paste (always works, the reliable fallback)

For a long conversation with many files and images, this captures all of Claude's text responses and your text messages. It does not capture image binary data, but that is expected and fine.

---

## Quick Start

### Option A: MCP Tools (for shorter conversations)

After installation and restart, use the tools directly in Claude Desktop:
- `diagnose_conversation` — analyze a conversation for bloat
- `prune_conversation` — surgically prune and return statistics
- `create_briefing` — generate a full briefing document
- `extract_rules` — extract behavioral corrections only
- `rules-status` — show current rule store capacity and status

### Option B: Command Line (recommended for long or image-heavy conversations)

```bash
# See what is in your Claude Desktop data folder
python context_surgeon.py discover

# Diagnose a conversation (no changes made)
python context_surgeon.py diagnose conversation.txt

# Standard compression, 10 most recent turns verbatim
python context_surgeon.py prune conversation.txt --output briefing.md

# Aggressive compression, 20 most recent turns verbatim (recommended for long/image-heavy)
python context_surgeon.py prune conversation.txt --verbatim 20 --rx aggressive --output briefing.md

# Gentle compression (strip noise only, no deduplication or compression)
python context_surgeon.py prune conversation.txt --rx gentle --output briefing.md

# Check rule store status
python context_surgeon.py rules-status
```

---

## Step 3: Start Your Fresh Conversation

After you have `briefing.md`:

1. Open `briefing.md` in Notepad or any text editor.
2. Press `Ctrl + A` to select all, then `Ctrl + C` to copy.
3. Open a **new Claude Desktop conversation**.
4. Paste the briefing as your **very first message** in the new conversation.
5. Send it. Claude reads the briefing and knows the context.
6. Continue your work as if the conversation never restarted.

**For conversations where images are still needed going forward:** After pasting the briefing, attach only the images relevant to your current work. Do not re-attach everything from the old conversation; only what you still need to actively analyze. The briefing already contains Claude's text conclusions about the earlier images.

---

## Understand What the Briefing Looks Like

The briefing has three sections:

**Section 1: Behavioral Rules.** These are the explicit instructions you gave Claude during the conversation. "Don't use em dashes." "Always cite the primary source." "Use metric units." These appear first so Claude applies them immediately.

**Section 2: Compressed History.** Older turns, stripped of repetitive content and compressed to key points. Code blocks are kept completely intact regardless of how old they are.

**Section 3: Recent Turns (Verbatim).** The last N turns (however many you specified with `--verbatim`) copied exactly as written, nothing changed.

---

## Configuration (Environment Variables)

Context Surgeon supports the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTEXT_SURGEON_RULES_STORE` | `~/.config/context-surgeon/rules.json` | Path to the persistent rule store |
| `CONTEXT_SURGEON_MAX_STORE_RULES` | `30` | Maximum number of rules to keep (IFScale-aligned for free-tier models) |
| `CONTEXT_SURGEON_DEFAULT_VERBATIM` | `10` | Default number of recent turns to keep verbatim |
| `CONTEXT_SURGEON_REVIEW_MODE` | `0` | Set to `1` to surface near-duplicate rule candidates for manual review |
| `CONTEXT_SURGEON_STRICT_VERSION_CHECK` | `0` | Set to `1` to turn version mismatches into hard errors (useful for CI) |

Example:
```bash
export CONTEXT_SURGEON_MAX_STORE_RULES=50
export CONTEXT_SURGEON_DEFAULT_VERBATIM=15
```

---

## Troubleshooting

**"python is not recognized as an internal or external command"**
You either do not have Python installed, or you did not check "Add Python to PATH" during installation. Reinstall Python from https://www.python.org/downloads/ and check that box.

**"No turns found"**
Context Surgeon could not parse the format of your conversation file. Try a different copy method: if you used Ctrl+A in Claude Desktop and the text looks truncated, try the Shift+Ctrl+End method described in the Get Your Conversation section. Alternatively, save as a `.txt` file if it was saved as `.rtf`.

**The tool runs but the briefing seems very short**
If the aggressive prescription compressed too aggressively, increase `--verbatim` to keep more recent turns intact. Try `--verbatim 25` and `--rx standard`.

**The MCP tool says "No turns found" in Claude Desktop**
The conversation text you pasted was parsed as a single unstructured block rather than as turns. Make sure the pasted text actually contains recognizable `User:` / `Assistant:` alternation or is in JSON format.

**Claude Desktop does not seem to know about the context-surgeon tools after restarting**
Run `python context_surgeon.py discover` to confirm the MCP config was written correctly. Check that `%APPDATA%\Claude\claude_desktop_config.json` exists and contains a `context-surgeon` entry. If not, re-run `setup-mcp`.

**The conversation is so long that even copying it crashes Notepad**
Use Notepad++ instead (https://notepad-plus-plus.org). It handles files of any size. For truly massive conversations, consider using VS Code (https://code.visualstudio.com), which is free and excellent at large files.

---

## Quick Reference

```
# See what is in your Claude Desktop data folder
python context_surgeon.py discover

# Diagnose a conversation (no changes made)
python context_surgeon.py diagnose conversation.txt

# Standard compression, 10 most recent turns verbatim
python context_surgeon.py prune conversation.txt --output briefing.md

# Aggressive compression, 20 most recent turns verbatim (recommended for long/image-heavy)
python context_surgeon.py prune conversation.txt --verbatim 20 --rx aggressive --output briefing.md

# Gentle compression (strip noise only, no deduplication or compression)
python context_surgeon.py prune conversation.txt --rx gentle --output briefing.md

# Check rule store status
python context_surgeon.py rules-status

# Just extract behavioral rules, nothing else
# (use the extract_rules MCP tool, or pipe through the CLI)
python context_surgeon.py diagnose conversation.txt | head -20
```

---

## When to Use MCP vs. Command Line: The Decision Rule

If your conversation has **more than about 15,000 words of text** or **more than five to ten image files**, use the command line. The MCP workflow requires pasting the full conversation into a new chat, which adds to that chat's context usage and is impractical for the kind of deep, image-heavy research conversations this tool is designed for.

Use the MCP tools for:
- Quick diagnostics when you want to stay in Claude Desktop
- Shorter conversations (under an hour of back-and-forth)
- Extracting behavioral rules without doing a full prune

Use the command line for:
- Everything involving long conversations
- Everything involving images
- Situations where you are already close to the context limit
- Batch processing or any time you want the output saved as a proper file

---

*Context Surgeon v1.2.0; github.com/fishboyrocks/cozempic-2.0*

---
