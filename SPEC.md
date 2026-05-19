# Sealed Evidence Record (SER) — Specification v0.1

**Status:** v0.1 · living draft · Apache-2.0 · reference implementation live at `https://verdict.systems/api/mcp`
**Schema id:** `ser.v0.1.legal_ai_output`
**Editors:** Verdict Systems Inc.
**Patent posture:** RAND-Z for conformant implementations — see https://verdict.systems/ip-policy

---

## 1. Abstract

A Sealed Evidence Record (SER) is a content-addressed, Merkle-rooted,
transparency-log-anchored record of a single AI agent action. One SER renders
into a SOC 2 dossier, an EU AI Act Article 12 retention log, and an
FRE 902(14) self-authenticating exhibit without re-deriving provenance.

This document specifies SER v0.1 as it is implemented today. It is faithful to
the live reference endpoint, not aspirational. An IETF Internet-Draft follows;
this is the normative source until it lands.

## 2. Record model

A SER binds, at creation time:

1. A **canonical payload** — the structured summary of the agent action
   (matter scope, workflow class, input summary, output summary, human review
   disposition, optional model identity, optional content hashes, citations,
   risk flags).
2. A **server-attested `received_at`** timestamp, bound *into* the canonical
   hash. An optional caller-supplied `event_time` travels alongside as
   advisory, never as the trust anchor.
3. A **SHA-256 payload hash** over the canonically serialized payload.
4. A **Merkle root** (RFC 6962-style) over the record's hashed components.
5. A **transparency anchor** — a Sigstore Rekor `hashedrekord` (v0.0.1) entry
   over the Merkle root, signed and independently verifiable on the public
   `rekor.sigstore.dev` log.

Canonical serialization is deterministic: stable key ordering, depth and cycle
guards, no floating ambiguity. Identical inputs MUST yield an identical payload
hash across implementations. This is the conformance hinge.

## 3. Operations

SER v0.1 defines three operations. The reference endpoint exposes them as MCP
tools (JSON-RPC 2.0, MCP protocol 2025-06-18).

### 3.1 Create evidence record — `verdict_create_evidence_record`

Seals an agent action into a SER.

| Field | Req | Notes |
|---|---|---|
| `matter_id` | ✔ | Caller-scoped matter/case identifier |
| `workflow` | ✔ | Workflow class (e.g. `contract_review`, `brief_drafting`, `legal_research`) |
| `input_summary` | ✔ | Plain-language summary of the agent's input |
| `output_summary` | ✔ | Plain-language summary of the agent's output |
| `human_review_status` | ✔ | `pending` \| `approved` \| `revised` \| `rejected` \| `not_required` |
| `attorney_reviewer` | – | Reviewer identity if reviewed |
| `model_provider`, `model` | – | Model identity |
| `prompt_hash`, `output_hash` | – | Caller content hashes (bound into payload) |
| `source_system` | – | Originating system |
| `citations[]`, `risk_flags[]` | – | Provenance + risk surface |
| `metadata` | – | Opaque caller object |
| `event_time` | – | Advisory caller timestamp (never the anchor) |

Non-destructive. Returns the payload hash, Merkle root, record id, and the
Rekor anchor (logIndex + entry).

### 3.2 Score evidence readiness — `verdict_score_evidence_readiness`

Read-only. Scores how defensible an agent's evidence posture is, independent of
any single record. Required: `matter_id`, `workflow`, and the booleans
`has_model_version`, `has_prompt_hash`, `has_output_hash`, `has_human_review`,
`has_citations`, `has_policy_version`. Optional: `has_terminal_state`,
`has_retention_policy`, `has_source_document_ids`, `has_rekor_anchor`.

### 3.3 Export FRE 902(14) certificate — `verdict_export_fre902_certificate`

Read-only. Produces a draft self-authenticating certificate from a sealed
record. Required: `evidence_record_id`, `custodian_name`, `organization`,
`payload_hash`, `merkle_root`, `record_timestamp`. Optional:
`system_description`, `exhibit_label`. Output is a draft for a qualified
custodian; it does not assert legal conclusions.

## 4. Transparency anchor

Each record's Merkle root is submitted to Sigstore Rekor as a `hashedrekord`
v0.0.1 entry. Verification is independent of Verdict: fetch the entry from
`rekor.sigstore.dev` (or the human viewer at `search.sigstore.dev`), confirm
the inclusion proof and signed checkpoint, decode the leaf, and match it to the
record's Merkle root. No trust in Verdict is required at verification time —
this is the property the whole format exists to deliver.

The public reference endpoint anchors with an ephemeral ECDSA P-256 key per
instance and labels itself `surface.tier=public_sandbox`. Production tenants use
an Ed25519 key in a FIPS 140-2 Level 3 HSM. The sandbox is deliberately and
visibly not the production trust model.

## 5. Conformance

An implementation is conformant if it passes the `conformance-suite` in this
org: deterministic canonical hashing, RFC 6962 Merkle construction,
server-attested `received_at` binding, chain-of-custody linkage
(`signer`, `prior_root`, `retention_class`), valid Rekor `hashedrekord`
signature verification, and a correct FRE 902(14) field set. Passing the suite
brings the implementation under the RAND-Z patent commitment.

## 6. Versioning & IP

`ser.v0.1.legal_ai_output` is the current schema id. Breaking changes bump the
minor; the schema id is the version contract. The Verdict patent portfolio
(USPTO 19/657,024 non-provisional + two provisional applications filed
2026-05-06) exists to prevent capture of this format into a closed proprietary
standard; it does not block conformant adoption. Full scope, conformance gate,
and defensive-termination terms: https://verdict.systems/ip-policy

Apache-2.0. Forever.
