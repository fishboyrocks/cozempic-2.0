# Context Surgeon
### Surgical context cleaning for Claude Desktop; the scalpel, not the sledgehammer.

---

## What This Is

Claude Desktop conversations have a **context limit**: a fixed amount of text and image data Claude can hold in its head at once. When a conversation gets long enough, Claude Desktop will offer to "compact" it. The native compact replaces your entire conversation history with a vague summary blob. Behavioral corrections you gave Claude, specific technical details, nuanced analysis, decisions that took hours to establish; all of it gets flattened into something generic and useless.

**Context Surgeon does the opposite.** It strips actual bloat (thinking blocks, repeated system tags, duplicate content) while surgically extracting and preserving the things that matter most: your explicit corrections ("don't use em dashes"), technical decisions, and the most recent turns of conversation verbatim. The output is a structured briefing document you paste into a fresh conversation to pick up exactly where you left off.

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

1. Open the conversation in Claude Desktop.
2. Click somewhere in the conversation text area to make sure it is the active element.
3. Press `Ctrl + A` to select all text in the conversation window. (In some versions of Claude Desktop, this selects only the input box; if so, proceed to step 4.)
4. If Ctrl+A selected the input box instead of the conversation: manually click at the very beginning of the first message in the conversation, hold `Shift`, then press `Ctrl + End` to select everything from there to the bottom.
5. Press `Ctrl + C` to copy.
6. Open **Notepad** (press the Windows key, type `notepad`, press Enter).
7. Press `Ctrl + V` to paste.
8. Press `Ctrl + S` to save. Name the file `conversation.txt` and save it to your Desktop or Documents folder.

**What you will get:** All user messages, all of Claude's text responses, references to any files or images that were analyzed, and the full text of all Claude's analysis. You will not get the actual image pixel data, but you do not need it; the briefing captures the conclusions.

**For very long conversations (multiple hours, many images):** The pasted text may be extremely long, potentially hundreds of thousands of characters. This is fine for the CLI approach. It may make Notepad slow; if so, download Notepad++ (free at https://notepad-plus-plus.org) which handles large files gracefully.

### A note on files in other formats (PDFs, Word documents, spreadsheets, code files)

When you attached a PDF or document and Claude analyzed it, the text content of that document was sent to Claude as text. That text analysis is captured in the conversation copy-paste. The original binary file is not, but again, you do not need it; the analysis text is what matters for the briefing.

---

## Option A: Using the MCP Tools in Claude Desktop

**Use this option when:** Your conversation is moderately long (under about 20,000 words of text), contains few or no images, and you want to do everything within Claude Desktop.

**Do not use this option when:** Your conversation is extremely long, contains many images, or you are near the context limit in the conversation you are trying to save. In those cases, the act of pasting a huge conversation into another chat to run the tool will itself consume most of that chat's context. Use Option B instead.

### How to invoke the tools

In a **fresh, empty Claude Desktop conversation**, type a message asking Claude to use a specific tool. You paste your conversation text directly into your message. Example:

```
Please use the create_briefing tool with this conversation:

[paste your conversation text here]
```

Claude will call the Context Surgeon MCP tool and return the result. For very long pastes, give it a moment.

### The four MCP tools

**`create_briefing`** is the main tool you will use. It:
- Scans every user message for behavioral corrections ("don't use em dashes", "always check the primary source", "prefer semicolons over dashes") and puts them at the top
- Compresses older turns aggressively while keeping code blocks completely intact
- Keeps your most recent 10 turns (configurable) exactly as written
- Returns a structured Markdown document you paste into a new conversation

Example usage:
```
Use create_briefing with verbatim_turns set to 15 on this conversation:
[paste]
```

**`diagnose_conversation`** tells you how bloated a conversation is before you decide what to do. Use it to see token estimates, how many duplicate blocks exist, and savings projections. Good for deciding which prescription to use.

**`prune_conversation`** is like create_briefing but returns the raw pruned conversation text instead of a formatted briefing. Useful if you want to process the output further.

**`extract_rules`** finds only the behavioral corrections from a conversation. Use this if you just need a quick list of "things I told Claude during this session" without the full briefing workflow.

---

## Option B: Using the Command Line (Recommended for Long or Image-Heavy Conversations)

**Use this option when:** Your conversation is extremely long, contains many images, you are close to the context limit, or you simply want a faster, cleaner process.

The command line does not require pasting anything into Claude Desktop. It reads your saved `conversation.txt` file directly and writes a `briefing.md` file. This is the right approach for the kind of conversation you are describing.

### Basic usage

Open Command Prompt and run:
```
python C:\Users\YourName\Documents\context_surgeon.py prune C:\Users\YourName\Desktop\conversation.txt --output C:\Users\YourName\Desktop\briefing.md
```

When it finishes, it prints a summary to the screen (how many turns were compressed, how many tokens were saved, which behavioral rules were preserved) and writes the briefing to `briefing.md`.

### Adjust how many recent turns are kept verbatim

The `--verbatim` flag controls how many of your most recent turns are kept exactly as written. Everything older gets compressed.

```
python context_surgeon.py prune conversation.txt --verbatim 20 --output briefing.md
```

For a long research conversation where recent context matters a lot, try 20 to 30. For a conversation you just want to summarize from scratch, 5 to 10 is fine.

### Adjust the compression intensity

The `--rx` flag sets the prescription:

| Prescription | What it does | When to use it |
|---|---|---|
| `gentle` | Strips thinking blocks and XML noise only | Conversation is not very repetitive |
| `standard` | Also removes duplicate repeated content | Most conversations (default) |
| `aggressive` | Also compresses older verbose turns | Very long conversations; image-heavy |

For a conversation approaching its context limit after hours of work and dozens of images, use aggressive:
```
python context_surgeon.py prune conversation.txt --verbatim 15 --rx aggressive --output briefing.md
```

### Just diagnose first

Before committing to a prescription, see what you are dealing with:
```
python context_surgeon.py diagnose conversation.txt
```

This prints a report showing token estimates, duplicate content, noise blocks, and what each prescription would save. No files are modified.

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

*Context Surgeon v1.0.0; github.com/fishboyrocks/cozempic-2.0*
