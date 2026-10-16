# 6. Open questions

These are the parts of 0.9 that we are not yet sure about. Some are awkward things in how
Lodestone works today that we did not want to freeze into the specification. Each one says what
the draft does now. Comments are welcome as issues on this repository.

## Q1. Two ids for one note

A note has a permanent `id` in its frontmatter (a ULID), but the tools use its path
(`memory/proj/garden/facts/beans.md`) as `id` and call the permanent one `uid`. Paths change when
a note is renamed or its kind changes; uids don't. Today `get` accepts only the path, while
`forget` and the federation `note` endpoint accept either.

*Draft:* tools return the path as `id` and the ULID as `uid`; `get` MUST accept the path and MAY
accept the uid. *Question:* should 1.0 require every tool to accept both, or switch tools to the
uid?

## Q2. Document kinds in `recall`

`recall`'s `kinds` filter and each hit's `kind` describe the kind of *document* (`memory`,
`digest`, `conversation`, `session`, `artifact`, …), while a note's `kind` is `fact`, `decision`
and so on. The same word means two things, and most document kinds depend on the provider's
archive.

*Draft:* only `memory` and `digest` are defined. *Question:* rename the argument (to `sources`?),
and add a filter by note kind?

## Q3. Namespace segments that look like kind folders

A namespace such as `proj/facts` puts notes at `memory/proj/facts/facts/…`, which is hard to read
and easy to get wrong. Today's server allows it.

*Draft:* SHOULD NOT. *Question:* make it MUST NOT in 1.0?

## Q4. How much YAML

Frontmatter is a small part of YAML, so that it is easy to read and write without a full YAML
library. It is also stricter than people expect: `pinned: true` is read as the text `true`, and
times are written in quotes.

*Draft:* writers write only the subset; readers accept it. *Question:* allow full YAML for readers,
or publish a reference parser?

## Q5. Does the memory have to be in git?

Lodestone keeps the memory in git, and a few things depend on it: export is a git bundle, history
is how "nothing is deleted" stays honest, and a publication's release is a commit.

*Draft:* storage is the provider's choice, history is a SHOULD, and only export (Moving) requires a
git bundle. *Question:* should Core require that the history of every change is kept, in some
form?

## Q6. What `context` must contain

`context` is the most important tool, and also the hardest to pin down without taking away the
provider's freedom to rank. The draft fixes the order (pinned note, latest thread, recent notes)
and suggests about 2,000 tokens. Our server also adds the latest digest and a few notes from `me`.

*Question:* is the order right? Should notes from `me` be part of every namespace's context?

## Q7. How apps register for sign-in

The draft requires dynamic client registration (RFC 7591), which is what clients such as claude.ai
use today. Newer versions of MCP prefer Client ID Metadata Documents.

*Question:* require either one, and move to metadata documents when clients do?

## Q8. Moving credentials for peers the owner reads from

When the owner moves, the credentials *they* hold for other people's servers are secrets, so the
draft keeps them out of the connections file, and the owner has to ask each peer for a new invite.

*Question:* add an encrypted part to the connections file (with a passphrase only the owner knows),
so peers carry on without new invites?

## Q9. Connected apps after a move

OAuth grants don't move, so after a move to a new address the owner signs in again in every app.
With their own domain, the address stays the same but the sign-in is still needed.

*Question:* is signing in again acceptable for 1.0? Carrying grants across providers would need the
two providers to trust each other.

## Q10. Signing keys for the moved record

The draft signs the moved record with a key per owner that the old server publishes in its
discovery document. Followers who never fetched the key have to rely on the new server confirming
the move (`moved_from`).

*Question:* is the confirmation enough on its own? Should the key belong to the owner rather than
the provider, and how is it rotated?

## Q11. The other tools

`search_archive`, `source`, `about` and `stats` are in our server but not in Core.

*Question:* should they become an optional "Archive" level, so that agents can rely on them where
they exist?

## Q12. A discovery document for every server

Today the discovery document (`/.well-known/lodestone`) belongs to Federation, so a Core-only
server has no standard way to say which levels it supports.

*Question:* require a minimal discovery document (`protocol`, `base_url`, `levels`) in Core?

## Q13. Small inconsistencies in Federation

- The discovery document has `"owner": {"display_name": "Alex"}`, while federation responses have
  `"owner": "Alex"`.
- Search hits carry `created`, while notes and changes carry `updated`.

*Draft:* written down as they are. *Question:* tidy them in `lodestone/1` (by adding fields) or
leave them for v2?

## Q14. Prompts

Our server also offers MCP prompts (`catch-up`, `save-chat`, `search-memory`). *Question:* should
their names be standard, so the same slash command works everywhere?

## Q15. Name and trademark

The specification is named "Lodestone Protocol", and "Lodestone" is kept as a trademark (section 1).
A trademark search has not been done yet.
