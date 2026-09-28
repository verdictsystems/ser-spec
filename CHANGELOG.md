# Changelog

## v0.1, Erratum 1 (2026-09-28)
No change to the v0.1 algorithm, wire format, domain separator or vectors.

- `SPEC.md` §4 no longer claims that Python `json.dumps(..., sort_keys=True, ...)` and `jq -cSj` reproduce the canonical form. Both differ from rules 1–5 on inputs the vectors do not contain; the replacement text lists how. Rule 3 now states that lone surrogates are escaped, as `JSON.stringify` escapes them. See `SPEC.md` §10.
- `tools/verify.py`: `canonical()` implements §4 directly instead of calling `json.dumps`. Keys sort in UTF-16 code-unit order, numbers are read as doubles and written by ECMAScript Number::toString, strings are escaped as `JSON.stringify` escapes them, and nesting deeper than 50 fails a `canonical_form` check. Input is read as UTF-8, and `NaN` and `Infinity`, which are not JSON, are rejected. Genuine records whose `metadata` holds keys that code-point and UTF-16 order sort differently, or numbers such as `0.00001` or `1e-7`, used to fail `payload_hash` and now pass. All 24 vectors still reproduce.

## v0.1 — frozen
Initial public publication of the SER v0.1 specification, 24 conformance vectors, and the Python reference verifier. The wire format, canonical form, domain separator (`verdict-ser-v0.1`) and derived values are frozen and will not change.
