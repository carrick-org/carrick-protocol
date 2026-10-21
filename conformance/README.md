# Conformance suite

One Python file, standard library only (Python 3.11 or later). It checks a running server, or a
memory repository on disk, against the Carrick Protocol 0.9, and says which levels pass.

## Check a server

```sh
export CARRICK_TOKEN=...        # an owner token that can read and write everything
python3 carrick_conformance.py server https://memory.example.com --write
```

- Tokens are read from the environment, never from the command line.
- Without `--write`, the suite only reads. It also registers one OAuth test client, as any app does
  when it first connects.
- With `--write`, it saves a few notes in a new namespace, `conformance/run-<id>`, and retracts them
  all at the end. Notes are never deleted (spec section 2.5), so the retracted notes stay in that
  namespace's history. Use a test account if you can.
- `--levels core,federation,moving` picks the levels (all by default).
- `--publication <slug>` checks a publication. Without it, the suite checks the first listed one.
- To check the peer endpoints, connect a second server as a peer and put its credential in
  `CARRICK_PEER_CREDENTIAL`. (`LODESTONE_TOKEN` and `LODESTONE_PEER_CREDENTIAL`, the earlier names, also work.)
- `--json` prints the results as JSON.

## Check a memory repository

```sh
python3 carrick_conformance.py repo path/to/memory-repo
```

This reads only. It checks the folders, the frontmatter of every note, the pinned notes, the digest
names, and looks for a few common shapes of secret.

## Reading the results

Each check is one of:

| Mark | Meaning |
| --- | --- |
| `pass` | Meets the specification |
| `FAIL` | Breaks a MUST |
| `warn` | Breaks a SHOULD |
| `skip` | Not checked (the line says why) |
| `n/a` | The server does not claim this optional level |

At the end, each level is `pass`, `FAIL`, `not proven` (some checks were skipped) or
`not supported`. The exit code is 1 if any check failed, otherwise 0.

A server passes Core only when it passes with `--write`.

## What it cannot check

Some rules can't be seen from outside, such as "store only a hash of the credential" or "never
re-share another server's notes". The suite checks what a client can see; the rest is up to each
provider. Import (Moving) is started in each provider's own way, so it is checked by hand: export
from one server, import into another, and run the suite against both.
