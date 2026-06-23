# Changelog

## [1.2.0] - 2026-06-22

_Stable release. All 1.2.0 features stabilized and verified._

### Added

- Add persistent rule store with SHA-256 checksum verification, automatic `.bak` backup, and recovery on corruption ([`3365e5d`])
- Add `rules-status` CLI command to display current rule count, capacity percentage, and status ([`d0ed19d`])
- Add `CONTEXT_SURGEON_RULES_STORE` environment variable to configure rule store path ([`a2efadb`])
- Add `CONTEXT_SURGEON_MAX_STORE_RULES` environment variable to configure store capacity (default: 30, aligned with conservative IFScale research for free-tier models) ([`996d8a2`])
- Add `CONTEXT_SURGEON_DEFAULT_VERBATIM` environment variable to configure number of recent turns preserved verbatim ([`ee4f801`])
- Add `CONTEXT_SURGEON_REVIEW_MODE` environment variable to surface near-duplicate rule candidates for manual review ([`fea490c`])
- Add `CONTEXT_SURGEON_STRICT_VERSION_CHECK` environment variable to turn version mismatches into hard errors (useful for CI) ([`4907399`])
- Add `IMPLICIT_CORRECTION_RE` for broader behavioral correction detection using patterns such as "actually,", "that's not right", and apology-follow-up signals ([`452a663`])
- Add audit logging for rule store changes (timestamped updates logged to stderr) ([`0486ae7`])
- Add `MIN_RULE_LEN` (10) to filter out empty or near-empty rules during extraction and merging
- Add multiple capacity and integrity safeguards:
  - Warning when store reaches 80% capacity
  - Error when hard cap is reached
  - Safeguard to truncate on load if count exceeds cap
  - Emergency length warning for individual rules exceeding 2000 characters
  - Length limit safeguard preventing save of rules exceeding 1200 characters
  - Non-string rule filter on load and before save
  - Duplicate detection before save
  - Empty input safeguard in `extract_rules_with_store()`
  - Skip save when final rule list is empty
  - Prevention of no-op saves when rules are unchanged
- Add low rule count warning in `cmd_prune()` when very few rules extracted from long conversation
- Add safety net in `extract_rules_with_store()` to force inclusion of safety-critical rules (containing "anti-trans hate crime", "physical safety", "jeopardy from an") if extraction fails ([`06817d8`])
- Add bypass of `MAX_RULE_LEN` for safety-critical sentences so they are never truncated ([`c87936c`])
- Improve Format 3 (date-separator) user-turn detection with additional first-person and question heuristics ([`f8179e5`], [`2cc5223`])
- Improve `rules-status` output with actionable guidance for FULL and APPROACHING CAPACITY states ([`e88b434`])

### Changed

- Change default `MAX_STORE_RULES` from 500 (arbitrary) to 30 (conservative, IFScale-aligned for free-tier models) ([`996d8a2`])
- Change default `MAX_RULE_LEN` to 800 (conservative: 441 observed maximum + 359 character margin) ([`0686527`])
- Change default `MAX_RULE_STORE_LEN_SAVE` to 1200 (conservative threshold between extraction cap and emergency warning)

### Fixed

- Fix version guard to use static dual-constant comparison instead of fragile file-reading at import time ([`4874f45`])
- Fix docstring header version to match `__version__` constant ([`ed522df`])

## [1.1.0-alpha] - 2026-06-20

_Pre-release introducing persistent rule store and broader correction detection._

### Added

- Add `IMPLICIT_CORRECTION_RE` for implicit correction signals ("actually,", "that's not right", etc.)
- Add `_atomic_write()` helper with `fsync()` + `os.replace()` for atomic file operations
- Add persistent rule store infrastructure (`_load_rules_store()`, `_save_rules_store()`, `merge_rules()`, `extract_rules_with_store()`)
- Add bigram overlap calculation as informational flag only (never used for merging decisions)
- Add `CONTEXT_SURGEON_RULES_STORE` environment variable support
- Add `MAX_STORE_RULES` constant (initially 500, later reduced)
- Add `REVIEW_MODE` support via `CONTEXT_SURGEON_REVIEW_MODE`

### Changed

- Change `extract_rules()` to also scan `IMPLICIT_CORRECTION_RE` patterns in addition to `CORRECTION_RE`

[3365e5d]: https://github.com/fishboyrocks/cozempic-2.0/commit/3365e5d
[d0ed19d]: https://github.com/fishboyrocks/cozempic-2.0/commit/d0ed19d
[a2efadb]: https://github.com/fishboyrocks/cozempic-2.0/commit/a2efadb
[996d8a2]: https://github.com/fishboyrocks/cozempic-2.0/commit/996d8a2
[ee4f801]: https://github.com/fishboyrocks/cozempic-2.0/commit/ee4f801
[fea490c]: https://github.com/fishboyrocks/cozempic-2.0/commit/fea490c
[4907399]: https://github.com/fishboyrocks/cozempic-2.0/commit/4907399
[452a663]: https://github.com/fishboyrocks/cozempic-2.0/commit/452a663
[0486ae7]: https://github.com/fishboyrocks/cozempic-2.0/commit/0486ae7
[06817d8]: https://github.com/fishboyrocks/cozempic-2.0/commit/06817d8
[c87936c]: https://github.com/fishboyrocks/cozempic-2.0/commit/c87936c
[f8179e5]: https://github.com/fishboyrocks/cozempic-2.0/commit/f8179e5
[2cc5223]: https://github.com/fishboyrocks/cozempic-2.0/commit/2cc5223
[e88b434]: https://github.com/fishboyrocks/cozempic-2.0/commit/e88b434
[4874f45]: https://github.com/fishboyrocks/cozempic-2.0/commit/4874f45
[ed522df]: https://github.com/fishboyrocks/cozempic-2.0/commit/ed522df

[1.2.0]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.2.0
[1.1.0-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.1.0-alpha

# Changelog

## [1.0.7-alpha] - 2026-06-19

_Pre-release; not yet verified against the user's actual `conversation.txt`. Promote to 1.0.7 once confirmed. Supersedes [1.0.6-alpha], which was never tested before this quality-verification pass found further issues in it._

### Fixed

- Fix the right-trim step stranding closing punctuation that the v1.0.6 boundary-extension had just added: a hard cut at exactly `MAX_RULE_LEN` chars could land precisely between a period and a closing paren, silently re-dropping it ([`6e50171`])
- Fix a spurious "…" being appended when punctuation-absorption walked all the way to the natural end of the string with nothing actually truncated ([`6e50171`])
- Cap the original v1.0.6 boundary-extension loop at 5 chars (previously uncapped), matching the bound already on the right-trim absorption loop, so a pathological run of consecutive closing punctuation can't inflate the candidate sentence before the length check runs ([`6e50171`])
- Add curly/smart quotes (U+2019, U+201D) to the closing-punctuation set; not exercised by the user's actual conversation but a near-zero-cost robustness improvement ([`6e50171`])

## [1.0.6-alpha] - 2026-06-19

_Pre-release; superseded by [1.0.7-alpha] before this was ever tested. Tag left unmodified per SemVer's immutability rule._

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
[2726c8a]: https://github.com/fishboyrocks/cozempic-2.0/commit/2726c8a1a64ba8576da389d0960dfc041ef7ab2f
[6e50171]: https://github.com/fishboyrocks/cozempic-2.0/commit/6e501719865f8aade3cd433c8f7c0e0e7596a620
[4d4b6d2]: https://github.com/fishboyrocks/cozempic-2.0/commit/4d4b6d208ef33e8caac4fdccbf736b06c7ffbb45
[a51a15f]: https://github.com/fishboyrocks/cozempic-2.0/commit/a51a15fa4a058d9f2ecec8852b4be58a91b722a7
[e15030d]: https://github.com/fishboyrocks/cozempic-2.0/commit/e15030d59a239378b55d09153091985c969dda75
[d81fe39]: https://github.com/fishboyrocks/cozempic-2.0/commit/d81fe398cb61840ec1af7fad0fcfc97d9c055940
[a943451]: https://github.com/fishboyrocks/cozempic-2.0/commit/a943451bf1da3590d9e8765a993a01701619059e
[aac5002]: https://github.com/fishboyrocks/cozempic-2.0/commit/aac5002f12c160b20db0159998955f8b736b58c9
[8add84a]: https://github.com/fishboyrocks/cozempic-2.0/commit/8add84a3ff9e01a56c2178029ed97a74dff43487

[1.0.8-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.8-alpha
[1.0.7-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.7-alpha
[1.0.6-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.6-alpha
[1.0.5-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.5-alpha
[1.0.4]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.4
[1.0.4-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.4-alpha
[1.0.3-alpha]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.3-alpha
[1.0.2]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.2
[1.0.1]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.1
[1.0.0]: https://github.com/fishboyrocks/cozempic-2.0/releases/tag/v1.0.0
