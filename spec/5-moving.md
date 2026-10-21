# 5. Moving (optional)

Moving lets an owner leave a provider and take everything with them: their memory, their connected
apps and the people who follow them.

**Status: new in 0.9.** No server implements this chapter yet, including ours. It is written down
first so that providers can build towards the same thing. Expect changes before 1.0; see
[chapter 6](6-open-questions.md).

A move has four parts:

1. **Export** the memory repository from the old server (section 5.1).
2. **Import** it into the new server (section 5.2).
3. The old server publishes a **"moved to" record**, and keeps it up for 12 months (section 5.3).
4. Peers and followers **re-point** to the new address on their own (section 5.4).

The simplest move of all is when the owner uses **their own domain** (section 5.5): nothing outside
the two providers has to change.

## 5.1 Export: "Download my memory"

- A server MUST let the owner download their whole memory repository, with its full history, as a
  [git bundle](https://git-scm.com/docs/git-bundle) that holds every branch.
- It MUST offer this in its user interface, and at an HTTP address listed in the discovery document
  as `endpoints.export` (for example `"/export/memory.bundle"`). A `GET` on that address with an
  owner token that can read everything returns the bundle as `application/x-git-bundle`. Any other
  caller gets `401` or `403`.
- The bundle MUST contain everything in chapter 2: `memory/`, `digests/`, `archive/` and `config/`,
  including files the server does not understand.
- The bundle MUST NOT contain secrets: no tokens, passwords, keys or credentials.
- Separately, the server MUST let the owner download a **connections file** (section 5.6), in its
  user interface and at an address listed in the discovery file as `endpoints.connections` (for
  example `"/export/connections.json"`), with the same access rules as the bundle.

## 5.2 Import

- A server MUST let the owner import a memory repository from a git bundle, or from a git
  repository the owner points it to.
- Import MUST keep every file and path as it is, every note's `id` (uid), and SHOULD keep the
  history.
- Import MUST NOT rewrite, merge or drop notes. If the new server already holds notes, it MUST
  either refuse the import or keep both sets intact and tell the owner what it did.
- After an import, every Core tool MUST work on the imported notes, with the same `id`s as before
  where the paths are the same.
- How the owner starts an import (a form, a command, an API) is up to the provider.

## 5.3 The "moved to" record

When the owner has moved, the old server tells everyone where they went.

```json
{
  "protocol": "carrick/1",
  "moved": {
    "from": "https://alex.old-provider.example",
    "to": "https://alex.new-provider.example",
    "at": "2026-11-02T10:00:00+00:00"
  },
  "signature": "eyJhbGciOiJFZERTQSIsImtpZCI6ImsxIn0..c2lnbmF0dXJl"
}
```

- `moved.from` is the old base URL, `moved.to` the new one, and `moved.at` when the move took
  effect.
- `signature` is a JWS ([RFC 7515](https://www.rfc-editor.org/rfc/rfc7515)) with a detached
  payload, using `EdDSA` (Ed25519). The payload is the `moved` object, serialised with the JSON
  Canonicalization Scheme ([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)). The key is one the
  old server published for this owner in its discovery document before the move:

  ```json
  "keys": [{"kid": "k1", "kty": "OKP", "crv": "Ed25519", "x": "<public key, base64url>"}]
  ```

  A server that supports Moving MUST publish this key in its discovery document from the start, so
  that followers already have it on file when a move happens.

**Where the old server serves it**

- `GET /.well-known/carrick` MUST return `200` with the discovery document, including `moved` and
  `signature` as above.
- Every request to the old MCP address, the federation endpoints and publication addresses MUST be
  answered with `410 Gone` and the record as a JSON body, with `"error": "moved"` added. The
  response SHOULD also carry a readable message, such as "This memory has moved to
  https://alex.new-provider.example. Connect there instead."
- The old server MUST keep serving the record for at least 12 months after `moved.at`, even if the
  owner's account is closed. During that time it MUST NOT give the old address to anyone else.
- The old server MUST NOT serve any of the owner's notes after the move.

**How the new server confirms it**

- The new server's discovery document MUST list the old address in `moved_from`:
  `"moved_from": ["https://alex.old-provider.example"]`. This is how the new server says "yes, the
  same owner lives here now". Without it, a record is not trusted.

The schema is [`schemas/moved.schema.json`](../schemas/moved.schema.json).

## 5.4 What peers and followers do

A server that follows a publication, or is connected to a peer, and receives a moved record for it
(from a `410`, or from the discovery document):

1. MUST check that `moved.from` is the address it was using.
2. MUST fetch `moved.to` + `/.well-known/carrick` and check that `moved_from` lists the old
   address.
3. MUST check the signature if it has the old server's key on file, and SHOULD keep keys on file
   for every peer and publication it follows.
4. If every check passes:
   - for a publication, SHOULD switch to the new address and carry on, keeping its follower id;
   - for a peer, MUST switch to the new address but MUST NOT expect its old credential to work there.
     Credentials never move (section 5.6), so it shows its owner that it is waiting for a new invite
     from the person who moved.
5. MUST tell its owner what happened, whether it switched or not. It MUST NOT drop a peer or a
   publication silently.

If a check fails, it MUST keep the old address and tell its owner.

## 5.5 Your own domain

- A server SHOULD let the owner use their own domain (such as `memory.alex.example`) as their base
  URL.
- When the owner's base URL is their own domain, moving is a matter of export, import and pointing
  the domain at the new provider. Connected apps and followers keep the same address. A moved record
  is not needed.
- A server that offers this MUST serve the owner's domain over HTTPS, and MUST stop answering for it
  as soon as the owner points it elsewhere.

## 5.6 The connections file

**No credential of any kind moves between providers.** What moves is the memory, its history, and
the *list* of the owner's connections. Access is always granted again on the new server: someone
who shared with the owner on one server has not agreed to share with them on another.

The connections file is that list, with addresses, names and kinds only:

```json
{
  "protocol": "carrick/1",
  "owner": "https://alex.old-provider.example",
  "peers_in": [
    {"url": "https://sam.example", "owner": "Sam", "person": "sam"}
  ],
  "peers_out": [
    {"url": "https://jo.example", "kind": "peer", "owner": "Jo"},
    {"url": "https://news.example", "kind": "publication", "slug": "garden-notes", "owner": "News"}
  ],
  "apps": [
    {"name": "Claude"},
    {"name": "VS Code"}
  ]
}
```

- The file MUST NOT hold any credential, token, key, or hash or fingerprint of one.
- **`peers_in`: people who read from the owner.** After a move, the new server MUST show the owner
  this list and let them invite each one again (one action per person). Their servers learn the new
  address from the moved record and wait for that invite (section 5.4).
- **`peers_out`: what the owner reads from others.**
  - For each `peer`, the new server MUST show it and SHOULD offer a ready-to-send request asking that
    person to share again.
  - Publications need no credential, so the new server SHOULD subscribe to each `publication` again
    on its own.
- **`apps`: apps the owner had connected.** OAuth grants don't move. The new server SHOULD show
  these as a checklist so the owner can sign in again in each one.
- Followers of the owner's own publications need nothing: they follow the moved record (section 5.4).

The schema is [`schemas/connections.schema.json`](../schemas/connections.schema.json).
