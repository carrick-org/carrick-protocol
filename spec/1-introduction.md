# 1. Introduction

**Lodestone Protocol, version 0.9 (draft).** The text of this specification is licensed under
[CC BY 4.0](../LICENSES/CC-BY-4.0.txt).

## What this is for

A Lodestone server holds one person's long-term memory for their AI agents: short notes (facts,
decisions, preferences, people, the state of ongoing work) and, optionally, an archive of past
conversations. Agents read and write that memory over [MCP](https://modelcontextprotocol.io).

This specification lets anyone build a compatible server, self-hosted or in the cloud. It has two
goals:

1. **Any agent works with any server.** The same tools, with the same names and the same meaning,
   wherever the memory is kept.
2. **People can leave.** Someone can move to another provider without losing their memory, the
   apps they have connected, or the people who follow what they share.

It defines only what has to be the same everywhere for those two goals. Everything else is left to
each provider, and providers compete on it:

- search ranking (including any decay of old notes);
- distillation (how notes get written from conversations);
- the web interface;
- storage, backups and encryption;
- capture tools;
- cost, billing and other commercial terms, such as what happens when a payment is missed;
- any extra features.

## Levels

A server says which levels it supports. Core is required; the others are optional.

| Level | What it covers | Chapter |
| --- | --- | --- |
| **Core** (required) | The memory format and the owner interface (the MCP tools and sign-in) | [2](2-memory-format.md), [3](3-owner-interface.md) |
| **Federation** (optional) | Discovery, sharing with other servers, publications | [4](4-federation.md) |
| **Moving** (optional) | Export and import, the "moved to" record, your own domain | [5](5-moving.md) |

A server may call itself **Lodestone compatible** only if it passes the
[conformance suite](../conformance/) at Core level. It may name each optional level it passes, for
example "Lodestone compatible (Core, Federation)".

## Words used in this specification

The keywords MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are used as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174),
when they appear in capitals.

- **Owner.** The one person whose memory a server holds. Each server, or each account on a shared
  service, belongs to one owner.
- **Provider.** Whoever runs the server: the owner themselves, or a company.
- **Server.** One owner's Lodestone, reached at one base URL such as `https://lodestone.example.com`.
- **Memory repository.** The owner's memory as a tree of files (chapter 2). It is the thing that
  moves when the owner moves.
- **Note.** One Markdown file with frontmatter: a fact, decision, preference, person, entity or
  thread.
- **Namespace.** A folder of notes, such as `me` or `proj/garden`.
- **Agent.** An AI client (Claude, an IDE, a script) that uses the owner interface.
- **Client.** Anything that calls the server: an agent, another server, or the conformance suite.

Sections marked **(informative)** explain or give examples. Everything else is normative.

## Versioning

- The specification's version is `0.9`. The wire identifier the protocol already uses is
  `lodestone/1`, and it stays `lodestone/1` for every 0.x and 1.x version of this document.
- Within `lodestone/1`, changes are additive: new optional fields, new optional tools, new
  endpoints. Clients MUST ignore fields they don't recognise.
- A breaking change gets a new wire identifier (`lodestone/2`) and new paths. A server MAY serve
  both.
- 0.9 is a draft. Things marked as open in [chapter 6](6-open-questions.md) may still change before
  1.0.

## Name and trademark

"Lodestone" is a trademark of the specification's editor. Anyone may implement this specification,
copy it and build on it under CC BY 4.0. Only servers that pass the conformance suite at Core level
may describe themselves as "Lodestone compatible".

## Governance

For now the editor (Nick) decides what goes into the specification. Changes are proposed as issues
or pull requests on this repository. This will be revisited once there are other providers.
