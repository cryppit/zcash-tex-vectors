#!/usr/bin/env python3
"""Reference codec for ZIP 320 TEX addresses, and the generator for vectors.json.

A TEX address is the 20-byte validating key hash of a transparent P2PKH address, re-encoded in Bech32m (BIP 350) with
the HRP "tex" (Mainnet) or "textest" (Testnet). "texregtest" (Regtest) is not in ZIP 320; it is the HRP that
librustzcash and Zebra use. Python stdlib only. `python3 tex.py` rewrites vectors.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_CONST, BECH32M_CONST = 1, 0x2BC830A3
MAX_LEN = 90  # BIP 173 / BIP 350; ZIP 320 does not lift it (unlike ZIP 316 unified addresses)
TEX_HRP = {"tex": "main", "textest": "test", "texregtest": "regtest"}
P2PKH_PREFIX = {"main": bytes([0x1C, 0xB8]), "test": bytes([0x1D, 0x25]), "regtest": bytes([0x1D, 0x25])}
P2SH_PREFIXES = (bytes([0x1C, 0xBD]), bytes([0x1C, 0xBA]))
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

ERRORS = {
    "invalid-char": "a character outside the Bech32 (or Base58) alphabet",
    "mixed-case": "upper and lower case mixed (BIP 173 forbids it; all-uppercase is allowed)",
    "too-long": "longer than 90 characters",
    "no-separator": "no '1' separator, or an empty HRP",
    "too-short": "fewer than 6 characters after the separator",
    "bad-checksum": "the checksum matches neither Bech32 nor Bech32m (or the Base58Check checksum is wrong)",
    "unknown-hrp": "the HRP is not tex, textest or texregtest",
    "not-bech32m": "a Bech32 checksum where ZIP 320 requires Bech32m",
    "bad-padding": "non-zero or excess padding bits",
    "bad-length": "the payload is not 20 bytes (or the transparent address is not 22 bytes)",
    "not-p2pkh": "a P2SH address: ZIP 320 defines TEX for P2PKH only",
    "unknown-prefix": "not a Zcash transparent address prefix",
    "wrong-network": "a valid address, but for a different network than the one the consumer is using",
}


class TexError(ValueError):
    def __init__(self, code: str):
        super().__init__(f"{code}: {ERRORS[code]}")
        self.code = code


# ---------- Bech32 / Bech32m (BIP 173, BIP 350) ----------

def _polymod(values: list[int]) -> int:
    gen = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    chk = 1
    for v in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if (top >> i) & 1 else 0
    return chk


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _convertbits(data: bytes | list[int], frombits: int, tobits: int, pad: bool) -> list[int]:
    acc = bits = 0
    out: list[int] = []
    maxv = (1 << tobits) - 1
    for v in data:
        acc = (acc << frombits) | v
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            out.append((acc >> bits) & maxv)
    if pad:
        if bits:
            out.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise TexError("bad-padding")
    return out


def bech32_encode(hrp: str, payload: bytes, spec: str) -> str:
    return bech32_encode_data(hrp, _convertbits(payload, 8, 5, True), spec)


def bech32_encode_data(hrp: str, data: list[int], spec: str) -> str:
    """Encode 5-bit groups as given, so a test can build data the byte encoder never would (e.g. excess padding)."""
    const = BECH32M_CONST if spec == "bech32m" else BECH32_CONST
    pm = _polymod(_hrp_expand(hrp) + data + [0] * 6) ^ const
    return hrp + "1" + "".join(CHARSET[d] for d in data + [(pm >> 5 * (5 - i)) & 31 for i in range(6)])


def bech32_decode(s: str) -> tuple[str, list[int], str]:
    """(hrp, 5-bit data without checksum, "bech32" | "bech32m"). Applies the 90-character limit."""
    if any(ord(c) < 33 or ord(c) > 126 for c in s):
        raise TexError("invalid-char")
    if s.lower() != s and s.upper() != s:
        raise TexError("mixed-case")
    if len(s) > MAX_LEN:
        raise TexError("too-long")
    s = s.lower()
    pos = s.rfind("1")
    if pos < 1:
        raise TexError("no-separator")
    if len(s) - pos - 1 < 6:
        raise TexError("too-short")
    hrp = s[:pos]
    if any(c not in CHARSET for c in s[pos + 1:]):
        raise TexError("invalid-char")
    data = [CHARSET.find(c) for c in s[pos + 1:]]
    check = _polymod(_hrp_expand(hrp) + data)
    if check not in (BECH32_CONST, BECH32M_CONST):
        raise TexError("bad-checksum")
    return hrp, data[:-6], "bech32m" if check == BECH32M_CONST else "bech32"


# ---------- Base58Check ----------

def _dsha(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def base58check_encode(payload: bytes) -> str:
    raw = payload + _dsha(payload)[:4]
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + out


def base58check_decode(s: str) -> bytes:
    n = 0
    for c in s:
        if c not in B58:
            raise TexError("invalid-char")
        n = n * 58 + B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\0" * (len(s) - len(s.lstrip("1"))) + raw
    if len(raw) < 4 or _dsha(raw[:-4])[:4] != raw[-4:]:
        raise TexError("bad-checksum")
    return raw[:-4]


# ---------- TEX ----------

NETWORK_HRP = {net: hrp for hrp, net in TEX_HRP.items()}


def decode_tex(s: str) -> dict:
    hrp, data, spec = bech32_decode(s)
    if hrp not in TEX_HRP:
        raise TexError("unknown-hrp")
    if spec != "bech32m":
        raise TexError("not-bech32m")
    pkh = bytes(_convertbits(data, 5, 8, False))
    if len(pkh) != 20:
        raise TexError("bad-length")
    return {"network": TEX_HRP[hrp], "pubkey_hash": pkh}


def decode_tex_for(s: str, network: str) -> dict:
    """Decode a TEX address as a consumer on `network` must: one for any other network is rejected."""
    d = decode_tex(s)
    if d["network"] != network:
        raise TexError("wrong-network")
    return d


def p2pkh(network: str, pkh: bytes) -> str:
    return base58check_encode(P2PKH_PREFIX[network] + pkh)


def tex_from_transparent(t: str, network: str) -> str:
    """The TEX form of a P2PKH address, for a consumer on `network` (Testnet and Regtest share the P2PKH prefix)."""
    raw = base58check_decode(t)
    if len(raw) != 22:
        raise TexError("bad-length")
    if raw[:2] in P2SH_PREFIXES:
        raise TexError("not-p2pkh")
    if raw[:2] == P2PKH_PREFIX[network]:
        return bech32_encode(NETWORK_HRP[network], raw[2:], "bech32m")
    if raw[:2] in P2PKH_PREFIX.values():
        raise TexError("wrong-network")
    raise TexError("unknown-prefix")


def script_pubkey(pkh: bytes) -> str:
    """OP_DUP OP_HASH160 <20 bytes> OP_EQUALVERIFY OP_CHECKSIG: what a payment to a TEX address must lock to."""
    return "76a914" + pkh.hex() + "88ac"


# ---------- vectors ----------

def run_case(case: dict) -> dict:
    """The expected result of one case, computed by this reference codec."""
    try:
        net = case["consumer_network"]
        if case["direction"] == "decode":
            d = decode_tex_for(case["input"], net)
            pkh = d["pubkey_hash"]
            return {"valid": True, "network": d["network"], "pubkey_hash": pkh.hex(),
                    "transparent": p2pkh(d["network"], pkh), "script_pubkey": script_pubkey(pkh)}
        out = tex_from_transparent(case["input"], net)
        d = decode_tex_for(out, net)
        return {"valid": True, "network": d["network"], "tex": out, "pubkey_hash": d["pubkey_hash"].hex()}
    except TexError as e:
        return {"valid": False, "error": e.code}


def build_vectors() -> dict:
    zip_t1 = "t1VmmGiyjVNeCjxDZzg7vZmd99WyzVby9yC"
    zip_tex = "tex1s2rt77ggv6q989lr49rkgzmh5slsksa9khdgte"
    k = decode_tex(zip_tex)["pubkey_hash"]
    enc = bech32_encode
    nonascii = zip_tex[:-1] + "\u0435"  # CYRILLIC SMALL LETTER IE, which looks like "e"
    raw = [
        ("decode", "main", "zip320-mainnet", zip_tex, "The ZIP 320 reference vector."),
        ("decode", "test", "zip320-key-testnet", enc("textest", k, "bech32m"), "The same key hash on Testnet (HRP textest; P2PKH prefix 0x1D25, tm...)."),
        ("decode", "regtest", "zip320-key-regtest", enc("texregtest", k, "bech32m"), "Regtest (HRP texregtest). Not in ZIP 320: the librustzcash and Zebra convention. Its P2PKH form uses the Testnet prefix."),
        ("decode", "main", "uppercase-mainnet", zip_tex.upper(), "All-uppercase must decode (ZIP 173 allows it; the ZIP 320 Owners confirmed it in zcash/zips#1468). zcash_address and Zebra reject it today. Encoders output lowercase."),
        ("decode", "main", "zero-hash-mainnet", enc("tex", bytes(20), "bech32m"), "Edge value: an all-zero key hash."),
        ("decode", "test", "ff-hash-testnet", enc("textest", b"\xff" * 20, "bech32m"), "Edge value: an all-0xff key hash."),
        ("decode", "main", "bech32-not-bech32m", enc("tex", k, "bech32"), "The right payload with a Bech32 (BIP 173) checksum. ZIP 320 requires Bech32m."),
        ("decode", "main", "payload-19-bytes", enc("tex", k[:19], "bech32m"), "A valid Bech32m string whose payload is 19 bytes."),
        ("decode", "main", "payload-21-bytes", enc("tex", k + b"\x00", "bech32m"), "A valid Bech32m string whose payload is 21 bytes."),
        ("decode", "main", "payload-with-prefix", enc("tex", P2PKH_PREFIX["main"] + k, "bech32m"), "A common bug: encoding the 22-byte Base58 payload (prefix included) instead of the 20-byte hash."),
        ("decode", "main", "payload-empty", enc("tex", b"", "bech32m"), "HRP and checksum only."),
        ("decode", "main", "excess-padding", bech32_encode_data("tex", _convertbits(k, 8, 5, True) + [0], "bech32m"), "The ZIP 320 key hash plus one extra all-zero 5-bit group. ZIP 173 allows at most 4 padding bits, so this must be rejected; a decoder that drops leftover bits reads the same key hash from a second string (librustzcash #3223)."),
        ("decode", "main", "mixed-case", "tex1S2rt77ggv6q989lr49rkgzmh5slsksa9khdgte", "One uppercase character: must be rejected."),
        ("decode", "main", "checksum-typo", zip_tex[:-1] + "f", "The last character changed: the checksum fails."),
        ("decode", "main", "invalid-character", zip_tex[:-1] + "b", "'b' is not in the Bech32 alphabet."),
        ("decode", "main", "non-ascii-character", nonascii, "The last character replaced by a Cyrillic letter that looks like 'e'. Only US-ASCII characters 33-126 are allowed."),
        ("decode", "main", "no-separator", "texs2rt77ggv6q989lr49rkgzmh5slsksa9khdgte", "The '1' separator removed."),
        ("decode", "main", "too-short", "tex1qqqqq", "Fewer than 6 characters after the separator, so there is no room for the checksum."),
        ("decode", "main", "unknown-hrp", enc("textestnet", k, "bech32m"), "A plausible but wrong HRP; only tex, textest and texregtest are TEX."),
        ("decode", "main", "testnet-tex-on-mainnet", enc("textest", k, "bech32m"), "A valid Testnet TEX address given to a Mainnet consumer."),
        ("decode", "test", "mainnet-tex-on-testnet", zip_tex, "A valid Mainnet TEX address given to a Testnet consumer."),
        ("decode", "main", "regtest-tex-on-mainnet", enc("texregtest", k, "bech32m"), "A valid Regtest TEX address given to a Mainnet consumer."),
        ("from_transparent", "main", "zip320-t1-to-tex", zip_t1, "The ZIP 320 reference vector, t1 to tex."),
        ("from_transparent", "test", "testnet-tm-to-textest", p2pkh("test", k), "A Testnet P2PKH address to textest."),
        ("from_transparent", "regtest", "regtest-tm-to-texregtest", p2pkh("test", k), "On Regtest the same tm... address converts to texregtest, because Regtest shares the Testnet P2PKH prefix."),
        ("from_transparent", "main", "p2sh-has-no-tex", base58check_encode(P2SH_PREFIXES[0] + k), "A Mainnet P2SH (t3...) address: ZIP 320 defines TEX for P2PKH only."),
        ("from_transparent", "test", "testnet-p2sh-has-no-tex", base58check_encode(P2SH_PREFIXES[1] + k), "A Testnet P2SH (t2...) address: no TEX form either."),
        ("from_transparent", "main", "tm-on-mainnet", p2pkh("test", k), "A valid Testnet P2PKH address given to a Mainnet consumer."),
        ("from_transparent", "main", "unknown-prefix", base58check_encode(bytes([0x1C, 0xB9]) + k), "Looks like a t1 address, but its 2-byte prefix is 0x1CB9 (one off from t1's 0x1CB8), which is not a Zcash transparent prefix. Catches validators that only check for a leading t1."),
        ("from_transparent", "main", "t1-bad-checksum", zip_t1[:-1] + "D", "The ZIP 320 t1 address with its last character changed."),
    ]
    cases = [{"id": i, "direction": d, "consumer_network": n, "input": s, "description": desc} for d, n, i, s, desc in raw]
    for c in cases:
        c["expect"] = run_case(c)
        if c["id"] in ("zip320-key-regtest", "regtest-tm-to-texregtest"):
            c["optional"] = True  # not in ZIP 320; a Mainnet/Testnet-only consumer may treat it as unknown
    return {
        "name": "ZIP 320 TEX address test vectors",
        "spec": "https://zips.z.cash/zip-0320",
        "version": 2,
        "errors": ERRORS,
        "fields": {
            "consumer_network": "the network of the consumer (main, test or regtest): the same string is valid on one network and wrong-network on the others",
            "decode": "input is a TEX address; expect gives network, the 20-byte pubkey_hash (hex), its transparent P2PKH form and the scriptPubKey a payment must use",
            "from_transparent": "input is a transparent address; expect gives the TEX form",
            "error": "a category, not a message: implementations word errors differently, but each invalid input must be rejected",
        },
        "cases": cases,
    }


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vectors.json")
    with open(path, "w") as f:
        json.dump(build_vectors(), f, indent=1)
        f.write("\n")
    v = build_vectors()
    print(f"wrote {path}: {len(v['cases'])} cases, {sum(c['expect']['valid'] for c in v['cases'])} valid")
    sys.exit(0)
