"""Tests for tex.py and vectors.json. Run: python3 -m unittest -v test_tex (from this folder)."""
from __future__ import annotations

import json
import os
import unittest

import tex

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP320_T1 = "t1VmmGiyjVNeCjxDZzg7vZmd99WyzVby9yC"
ZIP320_TEX = "tex1s2rt77ggv6q989lr49rkgzmh5slsksa9khdgte"


class Zip320Vector(unittest.TestCase):
    def test_t1_to_tex_matches_the_zip(self):
        self.assertEqual(tex.tex_from_transparent(ZIP320_T1), ZIP320_TEX)

    def test_tex_to_t1_matches_the_zip(self):
        d = tex.decode_tex(ZIP320_TEX)
        self.assertEqual(d["network"], "main")
        self.assertEqual(tex.p2pkh(d["network"], d["pubkey_hash"]), ZIP320_T1)

    def test_script_is_p2pkh(self):
        pkh = tex.decode_tex(ZIP320_TEX)["pubkey_hash"]
        self.assertEqual(tex.script_pubkey(pkh), "76a914" + pkh.hex() + "88ac")


class Errors(unittest.TestCase):
    def err(self, s):
        with self.assertRaises(tex.TexError) as c:
            tex.decode_tex(s)
        return c.exception.code

    def test_bech32_checksum_is_not_bech32m(self):
        pkh = tex.decode_tex(ZIP320_TEX)["pubkey_hash"]
        self.assertEqual(self.err(tex.bech32_encode("tex", pkh, "bech32")), "not-bech32m")

    def test_wrong_lengths(self):
        self.assertEqual(self.err(tex.bech32_encode("tex", bytes(19), "bech32m")), "bad-length")
        self.assertEqual(self.err(tex.bech32_encode("tex", bytes(21), "bech32m")), "bad-length")
        self.assertEqual(self.err(tex.bech32_encode("tex", bytes([0x1C, 0xB8]) + bytes(20), "bech32m")), "bad-length")

    def test_case_rules(self):
        self.assertEqual(tex.decode_tex(ZIP320_TEX.upper())["network"], "main")
        self.assertEqual(self.err("tex1S2rt77ggv6q989lr49rkgzmh5slsksa9khdgte"), "mixed-case")

    def test_checksum_and_charset(self):
        self.assertEqual(self.err("tex1s2rt77ggv6q989lr49rkgzmh5slsksa9khdgtf"), "bad-checksum")
        self.assertEqual(self.err("tex1s2rt77ggv6q989lr49rkgzmh5slsksa9khdgtb"), "invalid-char")
        self.assertEqual(self.err("texs2rt77ggv6q989lr49rkgzmh5slsksa9khdgte"), "no-separator")

    def test_hrp(self):
        pkh = bytes(range(20))
        self.assertEqual(self.err(tex.bech32_encode("zs", pkh, "bech32m")), "unknown-hrp")
        self.assertEqual(tex.decode_tex(tex.bech32_encode("textest", pkh, "bech32m"))["network"], "test")
        self.assertEqual(tex.decode_tex(tex.bech32_encode("texregtest", pkh, "bech32m"))["network"], "regtest")

    def test_too_long(self):
        self.assertEqual(self.err(tex.bech32_encode("tex", bytes(60), "bech32m")), "too-long")

    def test_p2sh_has_no_tex_form(self):
        t3 = tex.base58check_encode(bytes([0x1C, 0xBD]) + bytes(20))
        with self.assertRaises(tex.TexError) as c:
            tex.tex_from_transparent(t3)
        self.assertEqual(c.exception.code, "not-p2pkh")


class Vectors(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(HERE, "vectors.json")) as f:
            self.v = json.load(f)

    def test_file_is_exactly_what_gen_produces(self):
        self.assertEqual(self.v, tex.build_vectors())

    def test_every_case_matches_the_reference_codec(self):
        for case in self.v["cases"]:
            with self.subTest(case["id"]):
                self.assertEqual(tex.run_case(case), case["expect"])

    def test_cover_valid_and_invalid_and_both_directions(self):
        cases = self.v["cases"]
        self.assertGreaterEqual(sum(c["expect"]["valid"] for c in cases), 6)
        self.assertGreaterEqual(sum(not c["expect"]["valid"] for c in cases), 10)
        self.assertEqual({c["direction"] for c in cases}, {"decode", "from_transparent"})
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        self.assertEqual([c["id"] for c in cases if c.get("optional")], ["zip320-key-regtest", "uppercase-mainnet"])


if __name__ == "__main__":
    unittest.main()
