# ser-spec — Sealed Evidence Record v0.1

The open specification for the Sealed Evidence Record (SER): a JSON record of one AI-system action whose integrity any holder can re-derive, and whose existence at a point in time can be confirmed against the public Sigstore Rekor log, without contacting the producer.

- **[SPEC.md](SPEC.md)** — normative specification (frozen at v0.1)
- **[vectors/ser-v0.1-vectors.json](vectors/ser-v0.1-vectors.json)** — 24 frozen conformance vectors
- **[tools/verify.py](tools/verify.py)** — standard-library Python verifier (offline checks, optional Rekor anchor check)

## Verify a record in one command

```bash
python3 tools/verify.py record.json --anchor
```

Offline it recomputes the canonical form, payload hash, record commitment and id from the record content. With `--anchor` it also fetches the Rekor entry, checks the logged hash against your recomputation, verifies the signature with the public key embedded in the entry (via `openssl`), and prints the log's integrated time.

## Prove your implementation conforms

```bash
python3 tools/verify.py --vectors vectors/ser-v0.1-vectors.json
# PASS  24 vectors, schema ser.v0.1.legal_ai_output, domain verdict-ser-v0.1
```

## What a pass means

A passing offline check means the content is **self-consistent**: every committed value re-derives from the record. It does not prove when the record was sealed, who sealed it, or that the described event happened; an editor who recomputes every value produces a record that passes. Historical authenticity comes from the anchor check against a log the producer does not run. Section 7 of the spec says this precisely, and the verifier's output says it too.

## Reference implementations

- TypeScript `@verdict/core` and Rust `verdict-edge` (Verdict Systems; the TypeScript reference generated the vectors, the Rust implementation reproduces them byte for byte)
- Python `tools/verify.py` in this repository, written independently from the specification text

## Licence

Apache License 2.0. Patent commitment in SPEC.md §9.
