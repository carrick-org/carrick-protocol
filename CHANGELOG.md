# Changelog

## 0.9 (draft), unreleased

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

First public draft of the Lodestone Protocol.

- Core: the memory format and the owner interface (six MCP tools and OAuth sign-in), written down
  from how Lodestone works today.
- Federation: from the `lodestone/1` protocol Lodestone already uses, plus guests, publications,
  follower counting and a `levels` field in the discovery document.
- Moving: export, import, the "moved to" record and your own domain. New; not yet built anywhere.
- Open questions, schemas, an example repository and the conformance suite.
