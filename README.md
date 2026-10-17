# Lodestone Protocol

**Version 0.9 (draft).** An open specification for AI memory you can take with you.

A Lodestone server keeps one person's long-term memory for their AI agents: short notes about
facts, decisions, preferences, people and ongoing work, and optionally an archive of past
conversations. Agents read and write it over [MCP](https://modelcontextprotocol.io).

This specification lets anyone build a compatible server, self-hosted or in the cloud, so that:

- **any agent works with any server**, with the same tools and the same meaning everywhere; and
- **people can leave a provider** without losing their memory, their connected apps or the people
  who follow them.

It is deliberately small. Like RSS, it fixes only what has to be the same everywhere. Providers
compete on everything else: search, distillation, the interface, storage, backups, security, cost
and extras.

## The specification

1. [Introduction](spec/1-introduction.md): goals, levels, terms, versioning, name and governance
2. [Memory format](spec/2-memory-format.md) (Core): notes as Markdown files with frontmatter
3. [Owner interface](spec/3-owner-interface.md) (Core): six MCP tools and OAuth sign-in
4. [Federation](spec/4-federation.md) (optional): sharing with people, other servers and everyone
5. [Moving](spec/5-moving.md) (optional): export, import, the "moved to" record, your own domain
6. [Open questions](spec/6-open-questions.md)

## Levels

| Level | Required? | In short |
| --- | --- | --- |
| **Core** | Yes | The memory format, plus `context`, `recall`, `get`, `remember`, `checkpoint` and `forget` over MCP, OAuth sign-in, and a small discovery file |
| **Federation** | No | `/.well-known/lodestone`, peers, guests, publications, the read-only shared tools |
| **Moving** | No | "Download my memory" as a git bundle, import that keeps ids, a signed "moved to" record kept for 12 months, your own domain |

A server may call itself **Lodestone compatible** only if it passes the conformance suite at Core
level.

## Conformance suite

```sh
export LODESTONE_TOKEN=...    # an owner token
python3 conformance/lodestone_conformance.py server https://lodestone.example.com --write
python3 conformance/lodestone_conformance.py repo path/to/memory-repo
```

See [conformance/README.md](conformance/README.md).

Results for the Lodestone server (version 0.29.2), run locally on 17 October 2026, with `--write`:

| Level | Result |
| --- | --- |
| Core | Pass, no warnings |
| Federation | Pass, peers and publications included, no warnings |
| Moving | Not supported yet |

## In this repository

| Folder | What it holds |
| --- | --- |
| [`spec/`](spec/) | The specification |
| [`schemas/`](schemas/) | JSON Schemas: note frontmatter, tool inputs, the discovery file, the moved record, the connections file |
| [`conformance/`](conformance/) | The conformance suite |
| [`examples/`](examples/) | An example memory repository and example documents |
| [`tests/`](tests/) | Tests for the suite and the schemas |

## Taking part

The editor (Nick) decides for now. Please open an issue for questions, problems and proposals, or a
pull request for a change to the text. The [open questions](spec/6-open-questions.md) are the
best place to start.

## Licences

The specification text is under [CC BY 4.0](LICENSES/CC-BY-4.0.txt). The schemas, the conformance
suite, the tests and the examples are under [Apache 2.0](LICENSES/Apache-2.0.txt). "Lodestone" is a
trademark. See [LICENSE.md](LICENSE.md).
