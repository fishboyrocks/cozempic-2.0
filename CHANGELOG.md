# Changelog

## [1.0.6-alpha] - 2026-06-19

_Pre-release; not yet verified against the user's actual `conversation.txt`. Promote to 1.0.6 once confirmed._

### Fixed

- Fix `_sentence_around` dropping closing punctuation immediately following a sentence-ending period (e.g. "...anywhere else.) hence why..." lost the trailing `)`, producing unbalanced parens), found by checking every rule across all 6 real briefing outputs for paren balance after v1.0.5-alpha verification ([`a8106c2`])

## [1.0.5-alpha] - 2026-06-18

_Pre-release; not yet verified against the user's actual `conversation.txt`. Promote to 1.0.5 once confirmed._

### Fixed

- Fix `_sentence_around`'s `MAX_RULE_LEN` re-anchor trigger: it fired whenever the keyword's position exceeded half of `MAX_RULE_LEN`, rather than checking whether a plain right-trim would actually cut the keyword off, discarding fitting leading context for no benefit. An initial diagnosis attempt blamed this on Claude Desktop wrapping prose mid-word; that was checked directly against a real 298K+ char export and found false, so no wrap-detection logic was added — the real fix is purely the re-anchor condition ([`4d4b6d2`])
- Raise `MAX_RULE_LEN` from 350 to 460, based on measuring the natural (uncapped) length of every real correction-trigger sentence in the same export: the longest was 441 chars and happened to be the single most safety-critical rule in the conversation ([`4d4b6d2`])

## [1.0.4] - 2026-06-18

_Stable release combining [1.0.3-alpha] and [1.0.4-alpha], verified against the user's real `conversation.txt` and an independent second capture, with identical results on both._

### Added

- Add `collapse_exact_repeats()`: collapse byte-identical (whitespace-normalized) text chunks of 60+ chars that recur across different assistant turns, keeping the first occurrence in full. Applied to `standard` and `aggressive` only, so `gentle` stays pure noise-removal and the three prescriptions are no longer functionally identical to each other ([`a51a15f`])

### Fixed

- Strip Claude Desktop copy-paste UI chrome (doubled thinking-summary lines, standalone "Show more" labels) in `clean()`, so `gentle` and `standard` report real non-zero savings instead of a ~3-token no-op regardless of prescription or verbatim setting ([`a51a15f`])

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

[a8106c2]: https://github.com/fishboyrocks/cozempic-2.0/commit/a8106c26d24657ea4e443181dcbb0c56d0ad6dc6
[4d4b6d2]: https://github.com/fishboyrocks/cozempic-2.0/commit/4d4b6d208ef33e8caac4fdccbf736b06c7ffbb45
[a51a15f]: https://github.com/fishboyrocks/cozempic-2.0/commit/a51a15fa4a058d9f2ecec8852b4be58a91b722a7
[e15030d]: https://github.com/fishboyrocks/cozempic-2.0/commit/e15030d59a239378b55d09153091985c969dda75
[d81fe39]: https://github.com/fishboyrocks/cozempic-2.0/commit/d81fe398cb61840ec1af7fad0fcfc97d9c055940
[a943451]: https://github.com/fishboyrocks/cozempic-2.0/commit/a943451bf1da3590d9e8765a993a01701619059e
[aac5002]: https://github.com/fishboyrocks/cozempic-2.0/commit/aac5002f12c160b20db0159998955f8b736b58c9
[8add84a]: https://github.com/fishboyrocks/cozempic-2.0/commit/8add84a3ff9e01a56c2178029ed97a74dff43487

[1.0.6-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.6-alpha
[1.0.5-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.5-alpha
[1.0.4]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.4
[1.0.4-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.4-alpha
[1.0.3-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.3-alpha
[1.0.2]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.2
[1.0.1]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.1
[1.0.0]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.0
