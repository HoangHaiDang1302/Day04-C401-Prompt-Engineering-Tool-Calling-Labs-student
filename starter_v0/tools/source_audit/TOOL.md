---
name: source_audit
track: core
kind: local_formatter
provider: local
requires_env: []
inputs: [url, source_name, claim]
outputs: [rating, reasons, citation_guidance]
side_effect: false
---

# source_audit

Local helper for a quick citation/source suitability check.

Use it when the user asks whether a specific source, URL, domain, or claim is suitable to cite in a research digest or external write-up. It does not fetch live content; it evaluates the provided source metadata and returns a conservative citation recommendation.
