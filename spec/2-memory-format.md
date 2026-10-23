# 2. Memory format (Core)

The memory format is what moves between providers. It is a tree of plain files that a person can
read without any special software.

## 2.1 The memory repository

The memory repository has these top-level folders:

| Folder | What it holds | Required |
| --- | --- | --- |
| `memory/` | Notes, by namespace (section 2.2) | Yes |
| `digests/` | Daily summaries, by namespace (section 2.9) | No |
| `archive/` | Raw material: conversation transcripts, artifacts, documents (section 2.10) | No |
| `config/` | The owner's settings that travel with the memory (section 2.11) | No |

- A server MUST be able to read and write notes laid out as described in this chapter. How it
  stores them internally (files, a database, object storage) is up to the provider.
- A server SHOULD keep the history of every change, so that nothing is lost when a note is
  replaced or retracted. Our own implementation keeps the repository in git and makes one commit
  per change.
- A server MUST NOT write secrets (tokens, passwords, keys, credentials) into the memory
  repository.
- Text files MUST be UTF-8 with `\n` line endings. Paths use `/` and are case-sensitive.

## 2.2 Namespaces

A namespace is a path of one to five segments, such as `me`, `work` or `proj/garden/2026`.

- Each segment MUST match `[a-z0-9][a-z0-9._-]{0,63}`: lowercase, starting with a letter or digit,
  at most 64 characters.
- A segment MUST NOT start with `_`. Names starting with `_` are reserved for folders inside a
  namespace (such as `_inbox`).
- The namespace `me` is the owner's own: their preferences and facts about them.
- A namespace's notes live in `memory/<namespace>/<kind folder>/`. A child namespace, such as
  `proj/garden/2026` under `proj/garden`, is a separate namespace: its notes are not part of the
  parent's.
- A segment MUST NOT be a kind folder's name: `facts`, `decisions`, `preferences`, `people`,
  `threads`, `entities` or `_inbox`. Otherwise `memory/proj/facts/` would hold both the facts of
  `proj` and the folders of a namespace `proj/facts`. A server MUST refuse to create such a
  namespace, and SHOULD suggest another word (for example `work/contacts` for `work/people`).
- Any kind added in a later version gets a folder starting with `_`. Segments can't start with `_`,
  so a new kind can never clash with an existing namespace.

## 2.3 Kinds and where notes go

Every note has one kind. The kind decides the folder:

| Kind | Folder | What it is |
| --- | --- | --- |
| `fact` | `facts/` | Something true and worth keeping |
| `decision` | `decisions/` | A choice that was made, with the reason |
| `preference` | `preferences/` | How the owner likes things done |
| `person` | `people/` | A person, for the knowledge graph |
| `entity` | `entities/` | An organisation, place, project, event or thing, for the knowledge graph |
| `thread` | `threads/` | The rolling state of a long-running piece of work (section 2.7) |

Kind folders hold notes only, never other folders.

Proposals that are not yet accepted (for example, from automatic distillation) MAY be kept in
`memory/<namespace>/_inbox/`, with status `proposed`.

File names:

- A note's file name MUST end in `.md`.
- Writers SHOULD name a file after its title in lowercase, with runs of other characters replaced
  by `-`, at most 60 characters (a "slug"). Decisions SHOULD start with the date:
  `2026-10-16-use-a-git-bundle-for-export.md`. A thread's file name SHOULD be the slug of its
  thread name, so that the same thread name always finds the same file.
- If a name is taken, writers SHOULD add `-2`, `-3` and so on.
- Readers MUST NOT depend on file names for meaning. The frontmatter is what counts.

## 2.4 A note

A note is a Markdown file that starts with frontmatter between two `---` lines:

```markdown
---
id: 01M51FNNT2A1564RGBVW8YPKQF
namespace: proj/garden
kind: decision
title: "Plant the beans after the last frost, not by the calendar"
status: active
tags: [planting, beans]
created: "2026-10-16T04:31:37+00:00"
updated: "2026-10-16T04:31:37+00:00"
author: {agent: claude-desktop, account: home, machine: laptop}
---
We lost the first sowing to a late frost in 2025. From now on, wait for two weeks of nights above
8 °C, whatever the date.
```

### Fields

Writers MUST write these fields:

| Field | Meaning |
| --- | --- |
| `id` | The note's permanent identifier. It never changes, even when the file is moved or renamed. Writers SHOULD use a [ULID](https://github.com/ulid/spec) (26 characters, Crockford base32). It MUST be unique within the repository. |
| `namespace` | The namespace (section 2.2). Writers MUST put the note in that namespace's folder. If the folder and this line ever disagree, readers MUST go by this line. |
| `kind` | One of the kinds in section 2.3. It MUST match the folder the note is in. |
| `title` | A short, specific title, at most 200 characters, on one line. |
| `status` | `active`, `superseded`, `retracted` or `proposed` (section 2.5). |
| `created` | When the note was created: an [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339) time with an offset, for example `2026-10-16T04:31:37+00:00`. |
| `updated` | When the note last changed, in the same format. |

These fields are optional:

| Field | Meaning |
| --- | --- |
| `pinned` | `true` if this is the namespace's pinned note (section 2.6). Leave it out otherwise. |
| `tags` | A list of short lowercase tags. |
| `author` | Who last wrote the note: a map with any of `agent` (the client's name), `account` and `machine`. |
| `type` | For an `entity`: `organisation`, `place`, `project`, `event` or `thing`. Other values are allowed. |
| `aliases` | For a `person` or `entity`: other names it goes by. On a pinned note: other names for the namespace (section 2.6). |
| `sources` | Where the note came from: ids of archive documents or other notes. |
| `links` | Typed links to people and things (section 2.8). |
| `supersedes` | The `id`s of notes this one replaces. |
| `superseded_by` | The `id` of the note that replaced this one. |
| `reason` | Why the note was retracted or superseded. |
| `removed_with` | The namespace whose removal retracted this note (section 2.12). |

- Readers MUST ignore fields they don't recognise. Writers MUST keep fields they don't recognise
  when they rewrite a note, so that one provider's extras survive a visit to another.
- The body is Markdown ([CommonMark](https://commonmark.org)). It MUST NOT be empty.

### Frontmatter syntax

Frontmatter is YAML, but only a small part of it, so that it is easy to read and write without a
full YAML library. Writers MUST write only these forms, one field per line:

- a plain value: `status: active`;
- a double-quoted string, using JSON escapes, for any value that contains `:`, `#`, `[`, `]`, `{`,
  `}`, `,`, `&`, `*`, `!`, `|`, `>`, `'`, `"`, `%`, `@` or a backtick, that starts with `-` or a
  space, ends with a space, or is empty: `title: "Beans: after the frost"`;
- a list on one line: `tags: [planting, beans]`;
- a map on one line: `author: {agent: claude-desktop, machine: laptop}`;
- a list over several lines, one item per line, indented and starting with `- `. Writers SHOULD use
  this form for `sources` and `links`:

  ```yaml
  links:
    - "[[Sam]] works_at [[Green Fingers Ltd]] (since: 2025-02)"
  ```

Readers MUST accept all of these forms. Readers SHOULD also accept single-quoted strings, comment
lines starting with `#`, and blank lines.

### Reading hand-written notes (informative)

People sometimes write notes by hand. A lenient reader can fill in what is missing: the title from
the first `# ` heading or the file name, the kind from its folder, the namespace from the folders
between `memory/` and the kind folder (`memory/proj/x/facts/a.md` is in `proj/x`), `status: active`
(or `proposed` in `_inbox/`), and the path as the `id`. Writers that later save such a note should
then add the missing fields.

## 2.5 Status: nothing is deleted

Notes are not deleted. A note that is wrong or out of date changes status, and stays in the
repository:

| Status | Meaning | Shown by `recall` and `context` |
| --- | --- | --- |
| `active` | Current | Yes |
| `proposed` | Suggested, not yet accepted (usually in `_inbox/`) | No |
| `superseded` | Replaced by a newer note (`superseded_by`) | No |
| `retracted` | Wrong or no longer relevant (`reason`) | No |

- A server MUST NOT delete a note's file because of an agent's request. Retracting (`forget`,
  section 3.6) sets `status: retracted` and a `reason`.
- When a note replaces others, the new note SHOULD list them in `supersedes`, and each old note
  SHOULD get `status: superseded` and `superseded_by`.
- A retracted or superseded note MAY be restored to `active` by the owner.

## 2.6 The pinned note

Each namespace MAY have one pinned note: its brief, which every session on the namespace reads
first.

- A pinned note has `pinned: true`. It MUST be `active` and MUST NOT be a `thread`.
- There is at most one per namespace. Pinning a note MUST unpin the namespace's previous pinned
  note, which stays as an ordinary note. If a hand edit leaves two notes pinned, readers MUST use
  the one with the latest `updated`.
- A pinned note's body SHOULD be at most 6,000 characters (about 1,500 tokens), because every
  session reads all of it. Servers SHOULD refuse to pin a longer note through the owner interface.
- A pinned note's `aliases` are other names for the namespace. For example, a pinned note in
  `proj/garden` with `aliases: [Allotment]` lets an agent find the namespace by asking for
  "Allotment" (section 3.4).

## 2.7 Threads

A thread is the rolling state of a long-running piece of work: the goal, where things stand, what
is next, open questions.

- A thread lives at `memory/<namespace>/threads/<slug of the thread name>.md`, with `kind: thread`.
- Saving a thread (`checkpoint`, section 3.7) replaces its body and `updated` time. The previous
  state is kept in the repository's history, not in the note.

## 2.8 Links and the knowledge graph

Notes mention people and things as wiki links: `[[Sam]]`. A link may show different text with
`[[Sam|my neighbour]]`.

Typed links go in the `links` field, one per item:

```
[[Subject]] relation [[Object]]
[[Subject]] relation [[Object 1]], [[Object 2]] (role: brother, since: 2024-05, until: 2025-01)
```

- `relation` is a word or words with `_`, such as `works_at`. The optional part in brackets holds
  `key: value` details. `since` and `until` are dates (`YYYY`, `YYYY-MM` or `YYYY-MM-DD`).
- A name resolves to the `person` or `entity` note whose `title` or one of whose `aliases` matches
  it, ignoring case and extra spaces. A name with no such note is still a valid link.
- Relation types MAY be defined in `config/relations.toml` (section 2.11). The starter set is:
  `sibling_of`, `parent_of`, `spouse_of`, `relative_of`, `knows`, `works_at`, `member_of`,
  `part_of`, `owns`, `located_in`, `depends_on`, `decided_in`, `attended`, `about` and
  `related_to`.
- Writers MUST keep links exactly as written, including relations they don't know.

Building a graph from links, and any tool that answers questions about it, is up to each provider.

## 2.9 Digests

A digest is a short daily summary of what happened in a namespace. Digests are optional.

- If a server writes digests, it MUST put them at `digests/<namespace>/<YYYY-MM-DD>.md`, as
  Markdown with no frontmatter.
- How a digest is written is up to the provider.

## 2.10 The archive

`archive/` holds raw material that notes are distilled from: conversation transcripts, artifacts
and documents.

- Its layout depends on the capture tools, and is up to the provider. Servers MUST NOT require any
  particular layout inside `archive/`.
- When a server exports or imports a repository, it MUST carry `archive/` across unchanged.
- Transcripts SHOULD have secrets removed before they are archived.

How our own implementation lays out the archive (informative):

```
archive/claude-ai/<account>/<yyyy>/<mm>/<conversation-uuid>/conversation.json
archive/claude-ai/<account>/<yyyy>/<mm>/<conversation-uuid>/conversation.md
archive/claude-ai/<account>/<yyyy>/<mm>/<conversation-uuid>/artifacts/<id>-v<n>.<ext>
archive/claude-ai/<account>/projects/<project-uuid>/project.json
archive/claude-code/<machine>/<yyyy>/<mm>/<session-id>.jsonl
```

## 2.11 Settings that travel

`config/` holds settings that belong to the owner rather than to a provider. All of these files are
optional, and all are [TOML](https://toml.io):

| File | What it holds | Level |
| --- | --- | --- |
| `config/relations.toml` | Relation types for links (section 2.8) | Core |
| `config/people.toml` | The people the owner shares with | Federation |
| `config/shares.toml` | What is shared with whom, and publications | Federation |

A server MUST carry every file in `config/` across on export and import, including files it does
not understand. Files for capture tools are allowed and are not part of this specification. Ours is
`config/namespaces.toml`, which maps folders and projects to namespaces; only its `[renamed]` table
is defined here (section 2.12).

A relation type in `config/relations.toml` looks like this (informative):

```toml
[works_at]
inverse = "employs"           # the name of the other direction
cardinality = "many-to-one"   # many-to-many | one-to-one | many-to-one | one-to-many
roles = ["employee", "founder"]
words = ["works at", "works for"]

[sibling_of]
symmetric = true
```

## 2.12 Renaming, merging and removing a namespace

A server MAY let the owner rename, merge or remove a namespace. If it does, it does it as described
here, so that the result reads the same everywhere.

**Renaming.** Renaming `proj/old` to `proj/new`:

- moves every note in `memory/proj/old/` to `memory/proj/new/`, child namespaces included
  (`proj/old/x` becomes `proj/new/x`), and rewrites each note's `namespace:` line;
- moves `digests/proj/old/` to `digests/proj/new/`;
- never changes a note's `uid`. Its path, and so its tool `id`, does change. Because every tool also
  accepts the `uid` (section 3.4), references kept by `uid` keep working;
- records the rename in `config/namespaces.toml`, so that old names still reach the new namespace:

  ```toml
  [renamed]
  "proj/old" = "proj/new"
  ```

**The `[renamed]` table.**

- A key matches a namespace and all its children, by prefix: `proj/old/x` resolves to `proj/new/x`.
  When several keys match, the longest wins.
- The table is flat: renaming again rewrites the existing values rather than adding a chain.
- An entry whose key is again the name of a namespace with notes is dropped.
- A server that writes notes SHOULD resolve a namespace name through `[renamed]` before writing, so
  that it doesn't recreate a renamed namespace under its old name. Readers that don't know the table
  ignore it.

**Merging.** Renaming onto a namespace that already has notes merges the two. Notes are moved as
above, and a merge MUST NOT overwrite or drop a note. It also MUST NOT widen what is
shared: if the namespace being merged away is shared as a folder or published (chapter 4), the
server MUST refuse the merge until that share or publication is removed.

**Removing.** Removing a namespace retracts every note in it and its children (section 2.5), and
adds `removed_with: <namespace>` to each one. Restoring the namespace brings back exactly the notes
with that key, not notes that were retracted one by one, and drops the key. Restoring a single note
also drops it.

A complete example repository is in [`examples/memory-repo/`](../examples/memory-repo/). The
frontmatter is described as JSON Schema in
[`schemas/note-frontmatter.schema.json`](../schemas/note-frontmatter.schema.json).
