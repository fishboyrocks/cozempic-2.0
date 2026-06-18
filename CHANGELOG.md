# Changelog

## [1.0.4-alpha] - 2026-06-18

_Pre-release; not yet verified against the user's actual `conversation.txt`. Promote to 1.0.4 once confirmed._

### Added

- Add `collapse_exact_repeats()`: collapse byte-identical (whitespace-normalized) text chunks of 60+ chars that recur across different assistant turns, keeping the first occurrence in full. Applied to `standard` and `aggressive` only, so `gentle` stays pure noise-removal and the three prescriptions are no longer functionally identical to each other ([`e15030d`])

## [1.0.3-alpha] - 2026-06-17

_Pre-release; not yet verified against the user's actual `conversation.txt`. Promote to 1.0.3 once confirmed._

### Fixed

- Strip Claude Desktop copy-paste UI chrome (doubled thinking-summary lines, standalone "Show more" labels) in `clean()`, so `gentle` and `standard` report real non-zero savings instead of the prior ~3-token no-op ([`d81fe39`])

## [1.0.2] - 2026-06-07

### Fixed

- Stop `_sentence_around` truncating extracted correction rules mid-sentence by removing an incorrect 250-character left-boundary cap, capping extraction length from the right instead ([`a943451`])
- Make `gentle` and `standard` prescriptions distinct from a no-op by stripping assistant-turn opening/closing boilerplate (`gentle`) and acknowledgment openers (`standard`) ([`a943451`])

## [1.0.1] - 2026-06-06

### Fixed

- Rewrite `_parse_text` to use `finditer` across three formats (colon-labeled, solo-line, and Claude Desktop date-separator) instead of a single colon-only `split()`, fixing conversations with no `User:`/`Assistant:` labels collapsing into one unparsed turn ([`aac5002`])

## [1.0.0] - 2026-06-03

_Initial release._

### Added

- Add `context_surgeon.py`: CLI (`discover`, `diagnose`, `prune`, `setup-mcp`) and stdio MCP server (`diagnose_conversation`, `prune_conversation`, `create_briefing`, `extract_rules`) for pruning Claude Desktop conversation exports ([`8add84a`])

[e15030d]: https://github.com/fishboyrocks/cozempic-2.0/commit/e15030d59a239378b55d09153091985c969dda75
[d81fe39]: https://github.com/fishboyrocks/cozempic-2.0/commit/d81fe398cb61840ec1af7fad0fcfc97d9c055940
[a943451]: https://github.com/fishboyrocks/cozempic-2.0/commit/a943451bf1da3590d9e8765a993a01701619059e
[aac5002]: https://github.com/fishboyrocks/cozempic-2.0/commit/aac5002f12c160b20db0159998955f8b736b58c9
[8add84a]: https://github.com/fishboyrocks/cozempic-2.0/commit/8add84a3ff9e01a56c2178029ed97a74dff43487

[1.0.4-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.4-alpha
[1.0.3-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.3-alpha
[1.0.2]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.2
[1.0.1]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.1
[1.0.0]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.0
