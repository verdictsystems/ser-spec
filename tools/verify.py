#!/usr/bin/env python3
"""Reference verifier for SER v0.1 (Sealed Evidence Record). Standard library only.

Usage:
  verify.py record.json            offline self-consistency checks
  verify.py record.json --anchor   also confirm the Sigstore Rekor anchor (network)
  verify.py --vectors vectors/ser-v0.1-vectors.json   reproduce every frozen vector

Exit code 0 = every check passed, 1 = a check failed, 2 = usage.
"""
import base64, hashlib, json, math, re, subprocess, sys, tempfile, urllib.request

SCHEMA = "ser.v0.1.legal_ai_output"
DOMAIN = "verdict-ser-v0.1"
MAX_DEPTH = 50

class CanonicalError(ValueError):
    """The value has no SER v0.1 canonical form (SPEC.md §4.5)."""

def canonical(obj) -> str:
    """SER v0.1 canonical form (SPEC.md §4), byte-identical to the frozen TypeScript
    stableStringify. json.dumps is not a substitute: it sorts keys by code point,
    formats floats differently and has no depth limit (see the §4 erratum)."""
    return _canon(obj, 0)

def _canon(v, depth: int) -> str:
    if depth > MAX_DEPTH:                   # §4.5, checked for every value as stableStringify does
        raise CanonicalError(f"depth {depth}")
    if v is None: return "null"
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, (int, float)): return _number(v)
    if isinstance(v, str): return _string(v)
    if isinstance(v, list):
        return "[" + ",".join(_canon(x, depth + 1) for x in v) + "]"
    if isinstance(v, dict):                 # §4.1: UTF-16 code-unit order, what JavaScript's < compares
        keys = sorted(v, key=lambda k: k.encode("utf-16-be", "surrogatepass"))
        return "{" + ",".join(_string(k) + ":" + _canon(v[k], depth + 1) for k in keys) + "}"
    raise TypeError(f"not a JSON value: {v!r}")

def _number(x) -> str:
    """ECMAScript Number::toString (§4.4). JSON numbers are IEEE-754 doubles, as JSON.parse reads them."""
    try:
        x = float(x)
    except OverflowError:                   # integer literal beyond double range: JSON.parse gives ±Infinity
        x = math.inf if x > 0 else -math.inf
    if not math.isfinite(x): return "null"  # JSON.stringify(NaN), JSON.stringify(±Infinity)
    if x == 0: return "0"                   # includes -0
    if x < 0: return "-" + _number(-x)
    # repr gives the shortest round-trip digits; recover s (k digits) and n with x = 0.s × 10^n
    mant, _, exp = repr(x).partition("e")
    whole, _, frac = mant.partition(".")
    digits = (whole + frac).lstrip("0")
    n = len(digits) - len(frac) + int(exp or 0)
    s = digits.rstrip("0"); k = len(s)
    if k <= n <= 21: return s + "0" * (n - k)
    if 0 < n <= 21: return s[:n] + "." + s[n:]
    if -6 < n <= 0: return "0." + "0" * -n + s
    e = n - 1
    return (s if k == 1 else s[0] + "." + s[1:]) + ("e+" if e >= 0 else "e-") + str(abs(e))

_ESCAPE = re.compile(r'["\\\x00-\x1f\ud800-\udfff]')
_SHORT = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}

def _string(s: str) -> str:
    """ECMAScript JSON.stringify of a string (§4.3): short escapes, other C0 controls and lone
    surrogates as lowercase \\uXXXX, every other code point raw (including U+007F, U+2028, U+2029)."""
    return '"' + _ESCAPE.sub(lambda m: _SHORT.get(m[0]) or f"\\u{ord(m[0]):04x}", s) + '"'

def _reject_constant(name):
    raise ValueError(f"{name} is not JSON (RFC 8259)")

def load_json(path: str):
    """Read a file the way JSON.parse would: UTF-8, and NaN / Infinity rejected."""
    with open(path, encoding="utf-8") as f:
        return json.load(f, parse_constant=_reject_constant)

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
    try:
        d = derive(ser["record"])
    except CanonicalError as e:
        return [("canonical_form", f"depth <= {MAX_DEPTH} (SPEC.md §4.5)", e, False)]
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
    v = load_json(path)
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
    ser = load_json(args[0])
    checks = check_offline(ser)
    if "--anchor" in args:
        checks += check_anchor(ser)
    good = report(checks)
    print("\nRESULT: " + ("content self-consistent" + (" and anchor confirmed" if "--anchor" in args else "; anchor not checked (run with --anchor)") if good else "FAILED"))
    sys.exit(0 if good else 1)
