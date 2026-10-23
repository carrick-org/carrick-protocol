# Changelog

## 0.9 (draft), unreleased

### 21 October 2026: the Carrick logo and badge

- New `brand/` folder: the Waterline symbol, lockups, favicons, the GitHub avatar, colour tokens
  and the "Carrick compatible" badge for servers that pass Core, plus the scripts that build them.
  No change to the specification.

### 21 October 2026: the Carrick Protocol

- The protocol is renamed the **Carrick Protocol**, and moves to `carrick-org/carrick-protocol`.
  Servers that pass Core are "Carrick compatible". Lodestone is the first server to implement it.
- New wire names: `carrick/1`, `/.well-known/carrick` and `X-Carrick-Follower`. The earlier names
  (`lodestone/1`, `/.well-known/lodestone`, `X-Lodestone-Follower`) mean the same and stay accepted
  everywhere (section 1, Versioning). Nothing breaks.
- The conformance suite is now `conformance/carrick_conformance.py` and reads `CARRICK_TOKEN`. The old
  file name and `LODESTONE_TOKEN` still work. A server that only uses the earlier names gets warnings,
  not failures.
- Schema ids point at this repository (`raw.githubusercontent.com/carrick-org/carrick-protocol/v0.9/`).

### 23 October 2026: renaming, merging and removing a namespace

- New section 2.12, all optional (MAY): how a rename moves notes and digests and keeps uids, the
  `[renamed]` table in `config/namespaces.toml` (prefix match, longest key wins, kept flat), merging
  without widening what is shared, and removing a namespace with a `removed_with` key so it can be
  restored exactly. Writers SHOULD resolve names through `[renamed]`.
- New optional frontmatter field `removed_with`. Written down from Lodestone 0.33.

### 17 October 2026: the connections file's address

- Section 5.1: the connections file is also listed in the discovery file, as
  `endpoints.connections`, with the same access rules as the memory bundle.

### 17 October 2026: five open questions settled

- **No breaking changes unless there is no other way** (section 1, Versioning). Any unavoidable
  break is announced well ahead, with warnings and a stated version or date.
- **Q1, ids.** Every tool and federation endpoint that takes a note's id accepts its path or its
  `uid`; `get` used to accept only the path. Long-term references should use the `uid`.
- **Q3, namespace names.** A namespace segment can no longer be a kind folder's name (`facts`,
  `decisions`, `preferences`, `people`, `threads`, `entities`, `_inbox`). Readers go by a note's
  `namespace:` line. Kinds added later use folders starting with `_`.
- **Q8 and Q9, credentials.** No credential moves between providers. The connections file now holds
  addresses, names and kinds only: the hashes of incoming credentials are removed, and an `apps`
  list is added for a sign-in checklist. The owner re-invites readers, asks again for shares, and
  signs in again in each app.
- **Q12, discovery.** `/.well-known/lodestone` is required in Core with `protocol`, `base_url` and
  `levels`. The owner's name appears only once they have a listed publication.
- The conformance suite checks all of these. The discovery checks move from Federation to Core.

### 16 October 2026: first draft

First public draft of the Carrick Protocol.

- Core: the memory format and the owner interface (six MCP tools and OAuth sign-in), written down
  from how Lodestone works today.
- Federation: from the `lodestone/1` protocol Lodestone already uses, plus guests, publications,
  follower counting and a `levels` field in the discovery document.
- Moving: export, import, the "moved to" record and your own domain. New; not yet built anywhere.
- Open questions, schemas, an example repository and the conformance suite.
