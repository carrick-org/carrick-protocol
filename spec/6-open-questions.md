# 6. Open questions

These are the parts of 0.9 that we are not yet sure about. Some are awkward things in how
Lodestone, the first server to implement it, works today that we did not want to freeze into the specification. Each one says what
the draft does now. Comments are welcome as issues on this repository.

## Q2. Document kinds in `recall`

`recall`'s `kinds` filter and each hit's `kind` describe the kind of *document* (`memory`,
`digest`, `conversation`, `session`, `artifact`, …), while a note's `kind` is `fact`, `decision`
and so on. The same word means two things, and most document kinds depend on the provider's
archive.

*Draft:* only `memory` and `digest` are defined. *Question:* rename the argument (to `sources`?),
and add a filter by note kind?

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

## Q13. Small inconsistencies in Federation

- The discovery document has `"owner": {"display_name": "Alex"}`, while federation responses have
  `"owner": "Alex"`.
- Search hits carry `created`, while notes and changes carry `updated`.

*Draft:* written down as they are. *Question:* tidy them in `carrick/1` (by adding fields) or
leave them for v2?

## Q14. Prompts

Our server also offers MCP prompts (`catch-up`, `save-chat`, `search-memory`). *Question:* should
their names be standard, so the same slash command works everywhere?

## Q15. Name and trademark

The specification is named "Carrick Protocol", and "Carrick" is kept as a trademark (section 1). It was first
published as the Lodestone Protocol; the earlier wire names stay accepted (section 1, Versioning). A trademark
search for "Carrick" has not been done yet.

## Settled

Decided by the editor on 17 October 2026. The numbers are kept so that earlier references still
work.

- **Q1. Two ids for one note.** Every tool and federation endpoint that takes a note's id accepts
  either its path or its `uid`. Responses keep returning both (`id` is the path, `uid` the permanent
  id). Long-term references should use the `uid`. See sections 3.4, 3.7, 3.10 and 4.4.
- **Q3. Namespace segments that look like kind folders.** Not allowed: a segment can't be `facts`,
  `decisions`, `preferences`, `people`, `threads`, `entities` or `_inbox`. Readers go by a note's
  `namespace:` line when it disagrees with the folder. Kinds added later use folders starting with
  `_`. See sections 2.2–2.4.
- **Q8. Moving credentials for peers the owner reads from.** Credentials never move between
  providers, not even encrypted, and not as a future option. Someone who shared with you on one
  server decides again for the next: the new server lists those shares and offers a ready-to-send
  request to each person. The connections file holds addresses, names and kinds only; the earlier
  draft's hashes of incoming credentials are gone too, and the owner re-invites their readers. See
  section 5.6.
- **Q9. Connected apps after a move.** The owner signs in again in each app; the new server shows a
  checklist of the apps they had connected. See section 5.6.
- **Q12. A discovery file for every server.** Required in Core, with `protocol`, `base_url` and
  `levels`; other fields only when they apply. The owner's name appears only once they have a
  listed publication. See section 3.12.
