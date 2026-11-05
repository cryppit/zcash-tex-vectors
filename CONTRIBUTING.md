# Contributing

Issues and pull requests are welcome, especially a TEX address case that an implementation gets wrong and these vectors
don't cover yet.

## Ground rules

- **`vectors.json` is generated.** Never edit it by hand. Change `tex.py`, then run `python3 tex.py`; a test fails if the file
  differs from what the codec produces.
- **Follow the specs.** Every case must follow from ZIP 320, ZIP 316 or the Bech32m and Base58Check definitions. Cite the
  section if a case is not obvious.
- **Each invalid case fails for one reason.** Give it the expected error category so a consumer can tell why it failed.
- **Test data only.** No address from a real person's wallet.

## Development

Python 3 standard library only, no dependencies.

```bash
python3 -m unittest -v test_tex
```

Write the failing test first.

## Pull requests

For commits, branches and review, follow [librustzcash's contribution guidelines](https://github.com/zcash/librustzcash/blob/main/CONTRIBUTING.md),
the reference style for Zcash projects, adapted to Python where they are Rust-specific.

Keep one change per pull request, and say which implementation or spec text the change relates to. By contributing you
agree that your contribution is licensed under the MIT licence of this repository.
