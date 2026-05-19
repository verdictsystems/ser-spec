<p align="center">
  <a href="https://verdict.systems"><img src="https://verdict.systems/brand/sigil.svg" alt="Verdict — sealed chain node" width="120" height="120" /></a>
</p>

<h1 align="center">ser-spec</h1>

<p align="center">
  <strong>Sealed Evidence Record</strong> — open specification for cryptographically sealed AI agent evidence.<br/>
  Apache 2.0. Forever.
</p>

<p align="center">
  <a href="https://verdict.systems/patents">Patent portfolio (USPTO)</a> ·
  <a href="https://verdict.systems/ip-policy">RAND-Z licensing commitment</a> ·
  <a href="https://verdict.systems/api/mcp">Live reference endpoint</a>
</p>

---

## What is a Sealed Evidence Record?

A Sealed Evidence Record (SER) is a content-addressed, Merkle-rooted, transparency-log-anchored record of an AI agent action. One record renders into:

- **SOC 2** dossier
- **EU AI Act Article 12** retention log
- **FRE 902(14)** self-authenticating court exhibit
- **Insurer underwriting** packet

The format is open. The Verdict reference implementation seals every record to the public [Sigstore Rekor](https://rekor.sigstore.dev) transparency log.

## Current state

SER v0.1 (`ser.v0.1.legal_ai_output`) is implemented and live at:

- **Remote MCP endpoint:** `https://verdict.systems/api/mcp` (JSON-RPC 2.0, MCP protocol 2025-06-18)
- **Stdio package:** [`@verdict-systems/mcp`](https://www.npmjs.com/package/@verdict-systems/mcp)
- **Schema reference:** see the `verdict_create_evidence_record` tool output

The v0.1 schema reference document lands in this repo within the next sprint. The IETF I-D draft follows.

## Licensing

Apache 2.0 for the specification. RAND-Z patent commitment for conformant implementations — see [verdict.systems/ip-policy](https://verdict.systems/ip-policy) for scope, conformance test, and defensive-termination terms.

## Patent portfolio

The Verdict patent portfolio (USPTO 19/657,024 non-provisional + two provisionals filed May 6, 2026) exists to keep this specification from being captured or forked into a closed proprietary standard. The portfolio does not block conformant SER adoption.
