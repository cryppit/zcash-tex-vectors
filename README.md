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

Each case has an `id`, a `direction` (`decode`: TEX in; `from_transparent`: a t-address in), the `consumer_network`
(`main`, `test` or `regtest`: the network of the wallet or service checking the input), the `input`, a description and
`expect`. The same string can be valid for one network and `wrong-network` for another, so check each case on its
`consumer_network`. (Version 2 of the file added `consumer_network`; version 1 had no network context.)

- valid `decode`: `network`, `pubkey_hash` (hex), the `transparent` P2PKH form and the `script_pubkey`;
- valid `from_transparent`: `network`, `tex` and `pubkey_hash`;
- invalid: `error`, a category (see `errors` in the file). Implementations word errors differently; what matters is
  that each invalid input is rejected.

30 cases: 9 valid (two optional) and 21 invalid. The invalid ones cover a Bech32 checksum where Bech32m is required,
19-, 21- and 22-byte and empty payloads (the 22-byte one is the common bug of encoding the Base58 payload with its
prefix), excess padding (the right key hash plus one extra 5-bit group, which a decoder that drops leftover bits accepts
as the same address), mixed case, a checksum typo, a character outside the alphabet, a non-ASCII look-alike character, a
missing separator, a too-short string, a wrong HRP, a valid address for another network (decoded and converted), a P2SH
address on Mainnet and Testnet, which has no TEX form, a t1-looking address with an unknown prefix, and a Base58
checksum error.

Each invalid case fails for exactly one reason. There is no case for the 90-character limit: a TEX string over 90
characters always also has the wrong payload length, and a valid TEX address is exactly 42 (`tex`), 46 (`textest`) or
49 (`texregtest`) characters long. The codec still enforces the limit.

The all-uppercase case is required: ZIP 173 allows all-uppercase Bech32 strings (QR codes should use them), and the
ZIP 320 Owners confirmed on 18 Nov 2026 that a TEX Consumer must accept them, and must reject excess padding
([zcash/zips#1468](https://github.com/zcash/zips/issues/1468), ZIP change in
[zcash/zips#1469](https://github.com/zcash/zips/pull/1469)). `zcash_address` and Zebra reject uppercase today
([zcash/librustzcash#3306](https://github.com/zcash/librustzcash/issues/3306),
[ZcashFoundation/zebra#12517](https://github.com/ZcashFoundation/zebra/issues/12517)). The invalid cases are also
proposed for zcash-test-vectors in [zcash/zcash-test-vectors#139](https://github.com/zcash/zcash-test-vectors/pull/139).

The Testnet and Regtest strings match the ones in Zebra's tests, which were checked against `zcash_address`.

## Checklist for integrators

1. **Parse** all required valid cases and reject all invalid ones, each on its `consumer_network`. Reject mixed case,
   and accept all-uppercase (`zcash_address` 0.14.0 and Zebra reject it today: zcash/librustzcash#3306,
   ZcashFoundation/zebra#12517).
2. **Display** a TEX address as `tex1…`, never as the `t1…` form of the same key hash, and keep showing it that way in
   transaction history.
3. **Pay** to the P2PKH script of the key hash, never an empty or other script.
4. **Spend** only transparent inputs when any output pays a TEX address. Refuse, or split into the two-step flow.
5. **Sign:** a hardware wallet or signer checking an output's address must accept the TEX form of its key hash.
6. **Look up:** a node or explorer queried with a TEX address should answer for the underlying P2PKH address (Zebra 7.0.0
   returns an error for TEX in address queries, so query the P2PKH form).

## What these vectors do not test

They test addresses, not transactions. Passing them does not show that a wallet follows ZIP 320's main rule, spending
only transparent inputs when paying a TEX address, or that it builds the two-step payment from shielded funds correctly,
shows the TEX form in its history, or signs correctly on a hardware wallet. Check those against items 2–5 of the
checklist and the ZIP itself.

## Bugs these cases would have caught (2026)

| Where | What | Link |
|---|---|---|
| Zebra | `Display` printed TEX as the `t1…` address (fixed) | [#11826](https://github.com/ZcashFoundation/zebra/issues/11826), [#11880](https://github.com/ZcashFoundation/zebra/pull/11880) |
| Zebra | `Address::script()` returned an empty script for TEX (fix open) | [#11894](https://github.com/ZcashFoundation/zebra/pull/11894) |
| Zebra | Accepted a TEX address with a Bech32 checksum (fixed on `next`) | [#12254](https://github.com/ZcashFoundation/zebra/issues/12254), [#12360](https://github.com/ZcashFoundation/zebra/pull/12360) |
| librustzcash `zcash_address` | Accepts non-canonical (excess) padding, so a second string decodes to the same address (open; the ZIP 320 Owners confirmed TEX must reject it) | [#3223](https://github.com/zcash/librustzcash/issues/3223), [zips#1468](https://github.com/zcash/zips/issues/1468) |
| librustzcash `zcash_address` | Rejects an all-uppercase TEX address (open) | [#3306](https://github.com/zcash/librustzcash/issues/3306) |
| Zebra | Rejects all-uppercase TEX and accepts excess padding (open) | [#12517](https://github.com/ZcashFoundation/zebra/issues/12517) |
| blockchain_utils (Dart) | Decoded TEX payloads that weren't 20 bytes (fixed within an hour) | [#19](https://github.com/mrtnetwork/blockchain_utils/issues/19) |
| SSP Wallet | Rejected every `tex1` recipient (fix open, next release) | [#769](https://github.com/RunOnFlux/ssp-wallet/issues/769), [#770](https://github.com/RunOnFlux/ssp-wallet/pull/770) |
| xchainjs `zcash-js` | Rejected valid `tex1` recipients (fixed) | [#1782](https://github.com/xchainjs/xchainjs-lib/issues/1782), [#1783](https://github.com/xchainjs/xchainjs-lib/pull/1783) |
| Keystone firmware | A TEX output fails the transparent output address check | [#2313](https://github.com/KeystoneHQ/keystone3-firmware/issues/2313) |
| zecblock explorer | Reported TEX as an invalid transparent address (fixed) | [#136](https://github.com/Kenbak/zecblock/issues/136), [#284](https://github.com/Kenbak/zecblock/pull/284) |

## Who can pay a TEX address (18 Nov 2026)

Binance gives every ZEC user a `tex1…` deposit address, and THORChain's ZEC inbound address is often a TEX address too.
A wallet that can't pay TEX can't deposit ZEC to Binance or swap ZEC through THORChain.

- **Can pay TEX:** Zodl, Zingo, Zkool, Edge, Unstoppable, Zallet, Gem, Vultisig, OneKey, KeepKey, Coin Wallet, Vizor,
  Zafu, Noir, Zapp, ZChat, Laurel, from their code or release notes. Zodl pays from a shielded balance in two steps, and
  blocks TEX sends from Keystone and Ledger accounts.
- **Can't yet (issue open):** Cake Wallet ([#3871](https://github.com/cake-tech/cake_wallet/issues/3871)), Brave Wallet
  ([#61975](https://github.com/brave/brave-browser/issues/61975)), Ledger Live
  ([#25091](https://github.com/LedgerHQ/ledger-live/issues/25091)), Trezor
  ([#4581](https://github.com/trezor/trezor-firmware/issues/4581),
  [#35232](https://github.com/trezor/trezor-suite/issues/35232)), Keystone
  ([#2313](https://github.com/KeystoneHQ/keystone3-firmware/issues/2313)), ShapeShift (upstream
  [multicoin-address-validator#20](https://github.com/christsim/multicoin-address-validator/issues/20)), SSP Wallet (fix
  in [#770](https://github.com/RunOnFlux/ssp-wallet/pull/770)).
- **Not known:** most closed-source wallets and exchanges. If yours says "invalid address" for a `tex1…` address, the
  address is fine and the wallet is the problem.

Corrections welcome as issues; this list is from code reading and public notes, not a funded test of every wallet.

## Use it

Python 3 standard library only.

```sh
python3 -m unittest -v test_tex   # the codec matches ZIP 320, and vectors.json matches the codec
python3 tex.py                    # regenerates vectors.json
```

`tex.py` is a small reference codec (Bech32/Bech32m, Base58Check, TEX ↔ P2PKH); read it alongside the ZIP.

## Disclosure

Maintained by [Cryppit](https://github.com/cryppit), which reported Zebra #11826 (and wrote #11880) and #12254, Keystone
#2313 and zecblock #136 (and wrote the fix, merged through #284). Corrections are welcome as issues.

## Licence

MIT
