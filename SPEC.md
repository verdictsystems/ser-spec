# Sealed Evidence Record (SER) v0.1 — Specification

Status: **frozen**. Version 0.1 is complete and will not change. Additive changes belong in a future version with a new `schema` string.
Errata: see §10. An erratum corrects text that misdescribes the frozen algorithm; it changes no rule, derived value or vector.
Licence: Apache License 2.0 (see `LICENSE`). Patent commitment: see §9.

A Sealed Evidence Record is a small, self-describing JSON document that records one action taken by (or with) an AI system, together with values that let any holder re-derive the record's integrity without contacting the party that produced it. This document is normative. Two independent reference implementations (TypeScript, Rust) and a third stdlib-only Python verifier in this repository reproduce every vector in `vectors/ser-v0.1-vectors.json` byte for byte.

The words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Envelope

A sealed record (the *envelope*) is a JSON object:

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | MUST equal `"ser.v0.1.legal_ai_output"`. |
| `evidence_record_id` | string | `"ser_"` followed by the first 32 hex characters of `payload_hash` (§5). |
| `payload_hash` | string | Lowercase hex SHA-256 of the canonical form of `record` (§4). |
| `merkle_root` | string | The **record commitment** (§5). The wire name is historical; in v0.1 it is a domain-separated hash of one record, not a tree root. |
| `record` | object | The sealed content (§2). |
| `transparency_anchor` | object, optional | Public-log anchor (§6). Present when anchoring was attempted. |

Only `record` is covered by `payload_hash`. The four committed values (`schema`, `evidence_record_id`, `payload_hash`, `merkle_root`) are derived from `record`; `transparency_anchor` is outside the hash and is authenticated only by the public log it points to (§7).

## 2. The record

`record` is a JSON object with exactly these seventeen fields. All fields MUST be present; optional inputs are represented as `null`, an empty array, or an empty object, never omitted.

| Field | Type | Notes |
|---|---|---|
| `schema` | string | MUST equal `"ser.v0.1.legal_ai_output"`. |
| `matter_id` | string | Caller-defined identifier. May be empty. |
| `workflow` | string | One of §3. |
| `input_summary` | string | What the AI system was given. May be empty. |
| `output_summary` | string | What it produced. May be empty. |
| `human_review_status` | string | One of §3. |
| `attorney_reviewer` | string or null | Reviewer identity as supplied by the caller. |
| `model_provider` | string | Defaults to `"unknown"` when not supplied. |
| `model` | string or null | |
| `prompt_hash` | string or null | Caller-supplied digest of the full prompt. Not verified by this spec. |
| `output_hash` | string or null | Caller-supplied digest of the full output. Not verified by this spec. |
| `source_system` | string | Defaults to `"unknown"`. |
| `citations` | array of string | Defaults to `[]`. |
| `risk_flags` | array of string | Defaults to `[]`. |
| `metadata` | object | Defaults to `{}`. Arbitrary JSON; canonicalised like everything else. |
| `event_time` | string or null | ISO 8601, caller-supplied. |
| `received_at` | string | ISO 8601, set by the sealer at seal time. |

## 3. Enumerations

`workflow`: `contract_review`, `brief_drafting`, `nda_triage`, `legal_research`, `regulatory_monitoring`, `docket_watch`, `agentic_action`, `live_demo`, `other`.

`human_review_status`: `pending`, `approved`, `revised`, `rejected`, `not_required`, `demo_no_review`.

Verifiers MUST NOT reject a record for an unlisted enum value; the value is part of the hashed content and integrity is what is being checked. Producers MUST use listed values.

## 4. Canonical form

The canonical form of `record` is a UTF-8 string produced by these rules, applied recursively:

1. Objects: keys sorted by **UTF-16 code-unit order** (plain string comparison in JavaScript; equal to code-point order for keys in the Basic Multilingual Plane). Members whose value is `undefined` are dropped. No whitespace: `{"k":v,"k2":v2}`.
2. Arrays: elements in order, no whitespace: `[a,b]`.
3. Strings: serialised exactly as ECMAScript `JSON.stringify` serialises a string: `"` and `\` escaped; U+0008, U+0009, U+000A, U+000C, U+000D as `\b \t \n \f \r`; other code points below U+0020 as `\u00XX` (lowercase hex); every other code point, including non-ASCII, U+007F, U+2028 and U+2029, emitted raw. A lone surrogate, which only a `\uD800`–`\uDFFF` escape in the input JSON can produce, is emitted as `\uXXXX` in lowercase hex, as `JSON.stringify` has done since ES2019 (Erratum 1).
4. Numbers, booleans and `null`: as `JSON.stringify`.
5. Nesting deeper than 50 levels or a cyclic structure MUST be rejected.

*Informative; replaced by Erratum 1 (§10).* General-purpose JSON serialisers do not produce this form, and the vectors cannot show that one does: they contain no number, no non-ASCII key, no lone surrogate and no nesting deeper than 2. The differences:

- **Key order.** Python's `sort_keys=True` and jq's `-S` sort by code point. The orders differ when, at the first differing position, one key has a character at U+10000 or above and the other has one in U+E000–U+FFFF: in canonical form a key starting U+1F600 sorts before one starting U+FB01.
- **Numbers.** A number is the IEEE-754 double that `JSON.parse` reads, serialised by ECMAScript Number::toString: plain decimal for 1e-6 ≤ |x| < 1e21 (`0.00001`, `100`, `15000000000000000`), exponent form outside that range (`1e-7`, `1e+21`). `-0` serialises as `0`. An integer literal beyond 2^53 rounds to the nearest double (`9007199254740993` becomes `9007199254740992`), and a literal beyond the double range serialises as `null`, as ±Infinity does. Python's `repr` writes `1e-05`, `1e-07`, `1e+16` and `100.0`; jq 1.7.1 writes `1E-7`.
- **Strings.** Python's `json.dumps(..., ensure_ascii=False)` follows rule 3 except that it emits lone surrogates raw. jq escapes U+007F, so `jq -cSj` fails vector `json_escape_control_chars`.
- **Depth.** Neither tool enforces rule 5.

`canonical()` in `tools/verify.py` implements rules 1–5 with the Python standard library.

## 5. Derived values

```
payload_hash        = hex( SHA-256( UTF-8( canonical(record) ) ) )        # 64 lowercase hex chars
merkle_root         = hex( SHA-256( UTF-8( "verdict-ser-v0.1:" + payload_hash ) ) )
evidence_record_id  = "ser_" + payload_hash[0:32]
```

`"verdict-ser-v0.1"` is the domain separator. The commitment is a second hash over the ASCII hex of the first, prefixed with the separator and a colon.

## 6. Transparency anchor

When present, `transparency_anchor` is one of:

```json
{ "status": "anchored",
  "rekor_log_id": "<hex>", "rekor_log_index": <int or null>,
  "rekor_url": "https://rekor.sigstore.dev/api/v1/log/entries/<uuid>",
  "signing_algorithm": "ecdsa-p256-sha256",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----...",
  "anchored_at": "<ISO 8601>" }
```
or
```json
{ "status": "deferred", "reason": "<short ascii>", "attempted_at": "<ISO 8601>" }
```

An anchored record was produced as follows. Let `D` be the UTF-8 bytes of the `merkle_root` hex string. The producer signs `D` with ECDSA P-256 over SHA-256 and submits a Sigstore Rekor `hashedrekord` (apiVersion 0.0.1) whose `spec.data.hash.value` is `hex(SHA-256(D))`, with the DER signature and the SPKI PEM public key, both base64, in `spec.signature`. Rekor returns the entry UUID, log index, log ID and `integratedTime`, which the producer copies into the anchor.

## 7. Verification

**Offline (self-consistency).** From `record` alone recompute canonical form, `payload_hash`, `merkle_root` and `evidence_record_id` (§4–5). Each MUST equal the envelope's claimed value, and both `schema` fields MUST equal the v0.1 string. A failure means the content was changed after the values were computed, or the values are wrong.

**A pass proves only that the content is self-consistent.** All four committed values derive from the content, so an editor who recomputes all four produces a record that passes. A pass does not prove when the record was sealed, who sealed it, or that the described event happened.

**Anchor (historical authenticity).** Fetch the Rekor entry at `rekor_url`. Decode its body. Check that `spec.data.hash.value` equals `hex(SHA-256(UTF-8(merkle_root)))` recomputed from the record; that the DER signature verifies over the UTF-8 bytes of `merkle_root` with the embedded public key; and read `integratedTime` and `logIndex` from the entry. If these hold, the record's commitment existed no later than `integratedTime` in a log the producer does not control. Rekor inclusion proofs MAY additionally be checked against the log's signed tree head.

**What the anchor does not prove.** In v0.1 the signing key is not bound to any party: a producer MAY sign with an ephemeral key. The anchor establishes *when a commitment existed*, not *who made it*. Binding keys to parties is out of scope for v0.1.

`tools/verify.py` implements both checks with the Python standard library and `openssl`.

## 8. Conformance

An implementation conforms if it reproduces `canonical`, `payload_hash`, `merkle_root` and `evidence_record_id` for every entry in `vectors/ser-v0.1-vectors.json`. The vectors are frozen and were generated by the TypeScript reference; the Rust and Python implementations reproduce all of them.

## 9. Licence and patent commitment

This specification is licensed under the Apache License 2.0. Verdict Systems Inc. has published a RAND-Z (reasonable and non-discriminatory, zero-royalty) patent licensing commitment for conformant Sealed Evidence Record implementations. The commitment is scoped to conformant implementations, version-pinned to the conformance test in §8, and subject to defensive-termination terms. The controlling text is at https://verdict.systems/ip-policy; this section summarises it and does not replace it. Verdict has filed patent applications in the United States; none has been examined or granted at the date of this document.

## 10. Errata

**Erratum 1 (2026-09-28), §4.** The informative paragraph at the end of §4 read:

> Python: `json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` produces the identical string for all v0.1 records (proven by the vectors). `jq -cSj` produces it for records whose keys are within the BMP.

Both sentences were false, and the vectors proved neither. `json.dumps` sorts keys by code point, formats floats with Python's `repr` and has no depth limit. A verifier built on it therefore reported a payload-hash mismatch on genuine records whose `metadata` held keys that code-point order and UTF-16 order sort differently, or a number such as `0.00001` or `1e-7`, and it passed records nested deeper than rule 5 allows. `jq -cSj` escapes U+007F and fails vector `json_escape_control_chars`. The text now in §4 replaces the paragraph. The erratum also adds a sentence to rule 3: `JSON.stringify` escapes lone surrogates, a case the rule's list omitted.

Nothing normative changes. Rules 1–5 as the TypeScript reference implements them, the derived values, the domain separator and the 24 vectors stand as published. `tools/verify.py` now implements §4 directly (see `CHANGELOG.md`).
