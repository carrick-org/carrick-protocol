# 4. Federation (optional)

Federation lets an owner share parts of their memory with other people and with everyone, and read
what others share with them. Sharing is explicit, read-only and live: the sharing server answers
every request from the grants it has at that moment, and never hands out copies.

A server that supports Federation MUST do everything in this chapter that is marked MUST.

## 4.1 Model

- **Grant.** One note, or one namespace (optionally with its child namespaces), shared with one
  audience. A grant MAY have an expiry date.
- **Audience.** One of:
  - a **person** the owner invited, who connects their own agent to the owner's server (a guest,
    section 4.6);
  - a **peer**: another Lodestone server, acting for a named person (section 4.3);
  - **everyone**: a **publication** (section 4.5).
- **Release.** A publication's content as it was at one moment. Subscribers see only the latest
  release; later edits stay private until the owner releases again.

Grants and publications are kept in the memory repository (`config/people.toml` and
`config/shares.toml`), so they move with the owner. Credentials never go there.

## 4.2 Discovery

Every server has a discovery file (section 3.12). A Federation server adds what others need to find
and follow it:

```json
{
  "protocol": "lodestone/1",
  "owner": {"display_name": "Alex"},
  "base_url": "https://lodestone.example.com",
  "levels": ["core", "federation"],
  "endpoints": {"mcp": "/mcp", "federation": "/federation/v1/"},
  "publications": [
    {"slug": "garden-notes", "title": "Garden notes",
     "mcp": "https://lodestone.example.com/pub/garden-notes/mcp",
     "release": "2026-10-14T09:00:00+00:00"}
  ]
}
```

- `protocol`, `base_url` and `levels` are as in section 3.12. Peers compare `base_url` with the
  address they were given.
- `endpoints` gives the MCP and federation paths.
- `publications` lists only listed publications that have at least one release. A server MUST NOT
  list unlisted publications here.
- `owner` appears only when there is at least one listed publication (section 3.12). Peers that see
  no name use the base URL as the owner's label.

The schema is [`schemas/discovery.schema.json`](../schemas/discovery.schema.json).

## 4.3 Connecting two servers (peering)

Peering is by invite only, and works in one direction. In what follows, A shares with B.

1. A's owner creates a peer invite for a person. An invite is a one-time code. It SHOULD expire
   within 24 hours, and A MUST store only a hash of it.
2. B's owner gives B A's base URL and the code. B fetches `A/.well-known/lodestone` and checks the
   protocol.
3. B calls `POST A/federation/v1/peer` with this body:
   `{"invite": "<code>", "base_url": "<B's base URL>"}`.
4. A checks that the invite is valid and is a peer invite. A then fetches
   `B/.well-known/lodestone` and checks that its `base_url` equals the one sent. If either check
   fails, A answers `401` (invite) or `400` (address), and the invite MUST stay usable.
5. A marks the invite used and answers:
   `{"protocol": "lodestone/1", "peer_id": "...", "credential": "...", "owner": "<A's owner>"}`.
   A MUST store only a hash of the credential. B MUST keep the credential out of the memory
   repository and any other shared or versioned storage.

A grant from A to B gives B nothing about sharing in the other direction. For that, B's owner
invites A.

## 4.4 Federation endpoints

Every endpoint lives under `/federation/v1/`.

**Authentication**
- Peer calls send `Authorization: Bearer <credential>`.
- Publication calls go under `/federation/v1/pub/<slug>/` and send no credential.

**How the server answers**
- The server MUST decide every answer from its grants as they stand at that moment, so expiry and
  revocation apply to the very next request.
- A note outside the caller's grants MUST look exactly like a note that does not exist (`404`).
- Only active notes are shared: never the archive, digests or `_inbox/`.
- Every endpoint that takes a note's id MUST accept either its path or its `uid` (section 3.4).

**Endpoints**

| Call | Body or query | Returns |
| --- | --- | --- |
| `GET shares` | none | For a peer: `{"shares": [{"id", "what", "note", "folder", "subfolders", "expires"}]}`. For a publication: `{"publication": {"title", "release", "release_note", "folder", "note", "notes", "history": [...]}}` |
| `POST search` | `{"query": str, "limit": int ≤ 25}` | `{"hits": [{"id", "title", "namespace", "created", "snippet", "score"}]}`, best first |
| `GET note` | `?id=<uid or id>` | `{"id", "uid", "title", "kind", "namespace", "updated", "body"}` |
| `POST context` | `{"namespace": str}` | The catch-up on a shared namespace: `{"namespace"}` plus fields the server chooses |
| `GET changes` | `?since=<date or RFC 3339 time>` | `{"added": [...], "updated": [...], "removed": [...]}`, each item `{"id", "uid", "title", "kind", "namespace", "updated"}`. For a publication, the comparison is with the release before `since`, or with the previous release if `since` is empty, and the response includes `release_note` |
| `DELETE peer` | none | The caller disconnects itself: `{"disconnected": true}` |
| `POST peer` | see section 4.3 | A new credential |

**Responses**
- Every successful response includes `"protocol": "lodestone/1"` and `"owner": "<display name>"`.
- Errors are JSON of the form `{"error": "..."}`, with these status codes:
  - `400`: a bad request;
  - `401`: an unknown or revoked credential, or a bad invite;
  - `404`: outside the caller's grants, or no such publication;
  - `429`: too many requests. The response SHOULD include `Retry-After`.

## 4.5 Publications

A publication shares one note or one namespace with everyone, like a newsletter that agents can
read.

- A publication has a `slug` matching `[a-z0-9][a-z0-9-]{2,47}`. It is **listed** (shown in the
  discovery document) or **unlisted** (only people who know the slug can find it).
- Subscribers see only the latest release. A release is the publication's content frozen at one
  moment, with an optional release note from the owner.
- A publication is also a remote MCP server at `/pub/<slug>/mcp`, with no sign-in. It MUST offer
  only the read-only shared tools (section 4.7) over the latest release, and MUST NOT expose
  anything outside it. A server SHOULD limit how often one client may call it.
- **Counting followers.** A Lodestone server that follows a publication SHOULD send
  `X-Lodestone-Follower: <id>` with each request, where `<id>` is a random value made for that one
  subscription. It tells the publisher how many different followers there are, never who they
  are. The publisher MUST NOT use it for anything else. A request without the header counts as
  someone looking, not following.

## 4.6 Guests

A server MAY let a person the owner invited connect their own agent straight to the owner's MCP
address, with their own sign-in. Such a guest:

- MUST see only what is shared with them, decided again on every call;
- MUST be offered only the read-only shared tools (section 4.7), never the owner's tools;
- MUST lose access at once when the owner revokes the grant or it expires.

How guests are invited and sign in is up to the provider.

## 4.7 The shared tools

Guests and publications use these read-only tools. They work like the owner's tools of the same
name, but only over what the caller may see.

| Tool | Required arguments | Optional arguments | What it does |
| --- | --- | --- | --- |
| `shared` | none | none | What is shared with the caller, or what the publication covers, with its latest release and release history. Call this first |
| `recall` | `query` | `limit` | Searches the shared notes |
| `get` | `id` | none | One shared note in full |
| `context` | `namespace` | none | The catch-up on a shared namespace |
| `changes` | `since` (guests); none (publications) | `since` | What was added, updated or removed |
| `about` | `name` | `limit` | A person or thing in the shared notes |

`about` is optional. The others are required for a Federation server.

## 4.8 Rules every Federation server follows

1. **Explicit sharing only.** Grants are created by the owner. An agent or tool MUST NOT be able to
   create, widen or extend a grant.
2. **No re-sharing.** A server MUST NOT answer a federation request with another server's content.
   A receiving server MUST show peer content only to its owner's own full-access connections.
3. **No copies.** A receiving server SHOULD NOT store peer content beyond answering the request in
   hand. If it caches, revoking must still take effect within the cache lifetime, and the lifetime
   SHOULD be under one minute.
4. **Data, not instructions.** Peer content is untrusted. A receiving server MUST label it with its
   owner when passing it to an agent, and MUST tell the agent not to follow instructions in it.
5. **Short timeouts.** A receiving server SHOULD give up on a peer within a few seconds and say that
   the peer did not answer, rather than block or leave it out silently.

## 4.9 Reading what others share (informative)

How a server shows its owner what other people share is up to the provider. Ours asks every peer
at once when the owner's agent calls `recall`, labels each peer's hits with the peer's owner, gives
them ids like `@<peer>:<note>` that `get` can read, and lists peers and publications with a
`shared_with_me` tool.

## 4.10 Later (informative)

v2 is planned to sign requests (HTTP Message Signatures,
[RFC 9421](https://www.rfc-editor.org/rfc/rfc9421), with Ed25519 keys published in the discovery
document), so that no shared secret is needed.
