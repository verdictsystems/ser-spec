#!/usr/bin/env python3
"""Reference verifier for SER v0.1 (Sealed Evidence Record). Standard library only.

Usage:
  verify.py record.json            offline self-consistency checks
  verify.py record.json --anchor   also confirm the Sigstore Rekor anchor (network)
  verify.py --vectors vectors/ser-v0.1-vectors.json   reproduce every frozen vector

Exit code 0 = every check passed, 1 = a check failed, 2 = usage.
"""
import base64, hashlib, json, subprocess, sys, tempfile, urllib.request

SCHEMA = "ser.v0.1.legal_ai_output"
DOMAIN = "verdict-ser-v0.1"

def canonical(obj) -> str:
    """SER v0.1 canonical form: keys sorted by code unit, no whitespace,
    JSON string escaping per ECMAScript JSON.stringify, non-ASCII kept raw."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def derive(record: dict) -> dict:
    c = canonical(record)
    payload_hash = sha256_hex(c)
    commitment = sha256_hex(f"{DOMAIN}:{payload_hash}")
    return {
        "canonical": c,
        "payload_hash": payload_hash,
        "merkle_root": commitment,           # wire-format name of the record commitment
        "evidence_record_id": f"ser_{payload_hash[:32]}",
    }

def check_offline(ser: dict) -> list:
    d = derive(ser["record"])
    checks = [
        ("schema_version", SCHEMA, ser.get("schema"), ser.get("schema") == SCHEMA and ser["record"].get("schema") == SCHEMA),
        ("payload_hash", d["payload_hash"], ser.get("payload_hash"), d["payload_hash"] == ser.get("payload_hash")),
        ("record_commitment", d["merkle_root"], ser.get("merkle_root"), d["merkle_root"] == ser.get("merkle_root")),
        ("evidence_record_id", d["evidence_record_id"], ser.get("evidence_record_id"), d["evidence_record_id"] == ser.get("evidence_record_id")),
    ]
    return checks

def check_anchor(ser: dict) -> list:
    a = ser.get("transparency_anchor")
    if not a or a.get("status") != "anchored":
        return [("anchor_present", "anchored", (a or {}).get("status"), False)]
    commitment = ser["merkle_root"]
    expected_leaf = sha256_hex(commitment)   # Rekor hashedrekord stores sha256 of the commitment bytes
    url = a["rekor_url"]
    uuid = url.rstrip("/").split("/")[-1]
    with urllib.request.urlopen(f"https://rekor.sigstore.dev/api/v1/log/entries/{uuid}") as r:
        entry = json.load(r)[uuid]
    body = json.loads(base64.b64decode(entry["body"]))
    logged = body["spec"]["data"]["hash"]["value"]
    checks = [("rekor_hash_matches_commitment", expected_leaf, logged, logged == expected_leaf),
              ("rekor_log_index", str(a.get("rekor_log_index")), str(entry.get("logIndex")), str(entry.get("logIndex")) == str(a.get("rekor_log_index")))]
    # signature over the commitment bytes, public key embedded in the log entry
    pub = base64.b64decode(body["spec"]["signature"]["publicKey"]["content"])
    sig = base64.b64decode(body["spec"]["signature"]["content"])
    with tempfile.TemporaryDirectory() as t:
        open(f"{t}/pub.pem", "wb").write(pub); open(f"{t}/sig.der", "wb").write(sig)
        open(f"{t}/data", "wb").write(commitment.encode())
        ok = subprocess.run(["openssl", "dgst", "-sha256", "-verify", f"{t}/pub.pem", "-signature", f"{t}/sig.der", f"{t}/data"],
                            capture_output=True, text=True)
        checks.append(("rekor_signature_over_commitment", "Verified OK", ok.stdout.strip() or ok.stderr.strip(), ok.returncode == 0))
    checks.append(("rekor_integrated_time", "present", str(entry.get("integratedTime")), entry.get("integratedTime") is not None))
    return checks

def report(checks) -> bool:
    ok = True
    for name, expected, actual, passed in checks:
        ok &= bool(passed)
        print(f"{'PASS' if passed else 'FAIL'}  {name:34s} expected={expected}  actual={actual}")
    return ok

def run_vectors(path: str) -> bool:
    v = json.load(open(path))
    ok = True
    for vec in v["vectors"]:
        rec = build_record(vec["input"], vec["received_at"])
        d = derive(rec)
        for k in ("canonical", "payload_hash", "merkle_root", "evidence_record_id"):
            p = d[k] == vec["expected"][k]
            ok &= p
            if not p:
                print(f"FAIL  {vec['name']}.{k}\n  expected={vec['expected'][k]}\n  actual  ={d[k]}")
    print(f"{'PASS' if ok else 'FAIL'}  {len(v['vectors'])} vectors, schema {v['schema']}, domain {v['domain_separator']}")
    return ok

def build_record(inp: dict, received_at: str) -> dict:
    """Mirror of sealRecord()'s record construction (defaults applied, key order irrelevant)."""
    return {
        "schema": SCHEMA,
        "matter_id": inp["matter_id"],
        "workflow": inp["workflow"],
        "input_summary": inp["input_summary"],
        "output_summary": inp["output_summary"],
        "human_review_status": inp["human_review_status"],
        "attorney_reviewer": inp.get("attorney_reviewer"),
        "model_provider": inp.get("model_provider") or "unknown",
        "model": inp.get("model"),
        "prompt_hash": inp.get("prompt_hash"),
        "output_hash": inp.get("output_hash"),
        "source_system": inp.get("source_system") or "unknown",
        "citations": inp.get("citations") or [],
        "risk_flags": inp.get("risk_flags") or [],
        "metadata": inp.get("metadata") or {},
        "event_time": inp.get("event_time"),
        "received_at": received_at,
    }

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(2)
    if args[0] == "--vectors":
        sys.exit(0 if run_vectors(args[1]) else 1)
    ser = json.load(open(args[0]))
    checks = check_offline(ser)
    if "--anchor" in args:
        checks += check_anchor(ser)
    good = report(checks)
    print("\nRESULT: " + ("content self-consistent" + (" and anchor confirmed" if "--anchor" in args else "; anchor not checked (run with --anchor)") if good else "FAILED"))
    sys.exit(0 if good else 1)
