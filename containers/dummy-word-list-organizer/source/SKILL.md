---
name: dummy-word-list-organizer
description: Trim, deduplicate, and sort a bounded list of ASCII words without providers or external effects.
---

# Dummy Word List Organizer

## Workflow

1. Validate a bounded list of words and the optional duplicate-removal flag.
2. Trim ASCII whitespace and reject empty strings or control characters.
3. Optionally remove exact duplicates, then sort case-insensitively with an ASCII byte tie-break.
4. Return the exact sorted words and original/final counts.
