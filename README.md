# ZIP 320 TEX address test vectors

Test cases for [ZIP 320](https://zips.z.cash/zip-0320) TEX addresses (transparent-source-only addresses), for anyone who
parses, displays, pays or signs to them: wallets, exchanges, swap providers, explorers and hardware wallets.

ZIP 320 publishes one reference pair (`tex1s2rt77ggv6q989lr49rkgzmh5slsksa9khdgte` ↔
`t1VmmGiyjVNeCjxDZzg7vZmd99WyzVby9yC`). [`vectors.json`](vectors.json) adds Testnet and Regtest forms, edge values and
the invalid inputs implementations get wrong, each with the expected result or error category.

## What a TEX address is

The 20-byte key hash of a transparent P2PKH address, re-encoded in Bech32m with the HRP `tex` (Mainnet) or `textest`
(Testnet). `texregtest` (Regtest) is not in ZIP 320; it is the convention librustzcash and Zebra use, and its case is
marked `optional`. A payment to a TEX address locks to the ordinary P2PKH script, `76a914 <key hash> 88ac`.

**The rule that matters:** a sender MUST spend only transparent inputs in a transaction that pays a TEX address. To pay
from shielded funds, a wallet first unshields to an ephemeral transparent address in one transaction, then pays the
TEX address from it in a second.

## The vectors

Each case has an `id`, a `direction` (`decode`: TEX in; `from_transparent`: a t-address in), the `input`, a description
and `expect`:

- valid `decode`: `network`, `pubkey_hash` (hex), the `transparent` P2PKH form and the `script_pubkey`;
- valid `from_transparent`: `network`, `tex` and `pubkey_hash`;
- invalid: `error`, a category (see `errors` in the file). Implementations word errors differently; what matters is
  that each invalid input is rejected.

21 cases: 8 valid (two optional) and 13 invalid, including a Bech32 checksum where Bech32m is required, 19-, 21- and
22-byte payloads (the last is the common bug of encoding the Base58 payload with its prefix), mixed case, a checksum
typo, a character outside the alphabet, a wrong HRP, the 90-character limit, and a P2SH address, which has no TEX form.

The Testnet and Regtest strings match the ones in Zebra's tests, which were checked against `zcash_address`.

## Checklist for integrators

1. **Parse** all required valid cases and reject all invalid ones. Reject mixed case. All-uppercase is optional: BIP 173
   allows it, ZIP 320 does not mention it, and `zcash_address` 0.14.0 and Zebra reject it.
2. **Display** a TEX address as `tex1…`, never as the `t1…` form of the same key hash, and keep showing it that way in
   transaction history.
3. **Pay** to the P2PKH script of the key hash, never an empty or other script.
4. **Spend** only transparent inputs when any output pays a TEX address. Refuse, or split into the two-step flow.
5. **Sign:** a hardware wallet or signer checking an output's address must accept the TEX form of its key hash.
6. **Look up:** a node or explorer queried with a TEX address should answer for the underlying P2PKH address (Zebra 7.0.0
   returns an error for TEX in address queries, so query the P2PKH form).

## Bugs these cases would have caught (2026)

| Where | What | Link |
|---|---|---|
| Zebra | `Display` printed TEX as the `t1…` address (fixed) | [#11826](https://github.com/ZcashFoundation/zebra/issues/11826), [#11880](https://github.com/ZcashFoundation/zebra/pull/11880) |
| Zebra | `Address::script()` returned an empty script for TEX (fix open) | [#11894](https://github.com/ZcashFoundation/zebra/pull/11894) |
| xchainjs `zcash-js` | Rejected valid `tex1` recipients (fixed) | [#1782](https://github.com/xchainjs/xchainjs-lib/issues/1782), [#1783](https://github.com/xchainjs/xchainjs-lib/pull/1783) |
| Keystone firmware | A TEX output fails the transparent output address check | [#2313](https://github.com/KeystoneHQ/keystone3-firmware/issues/2313) |
| zecblock explorer | Reported TEX as an invalid transparent address (fixed) | [#136](https://github.com/Kenbak/zecblock/issues/136), [#284](https://github.com/Kenbak/zecblock/pull/284) |

## Use it

Python 3 standard library only.

```sh
python3 -m unittest -v test_tex   # the codec matches ZIP 320, and vectors.json matches the codec
python3 tex.py                    # regenerates vectors.json
```

`tex.py` is a small reference codec (Bech32/Bech32m, Base58Check, TEX ↔ P2PKH); read it alongside the ZIP.

## Disclosure

Maintained by [Cryppit](https://github.com/cryppit), which reported Zebra #11826 (and wrote #11880), Keystone #2313 and
zecblock #136 (and wrote the fix, merged through #284). Corrections are welcome as issues.

## Licence

MIT
