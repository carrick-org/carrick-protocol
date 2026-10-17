#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Conformance suite for the Lodestone Protocol, version 0.9 (draft).

Check a running server:

    export LODESTONE_TOKEN=...          # an owner token that can read and write everything
    python3 lodestone_conformance.py server https://lodestone.example.com --write

Check a memory repository on disk:

    python3 lodestone_conformance.py repo path/to/memory-repo

Standard library only, Python 3.11 or later. Tokens are read from the environment, never from the
command line, so they don't end up in shell history or CI logs.

`server` without --write only reads (apart from registering one OAuth test client, which is what
any app does when it first connects). With --write it saves a few notes in a new namespace,
`conformance/<run id>`, and retracts them all at the end. Use a test account if you can.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode, urlsplit

SPEC_VERSION = "0.9"
PROTOCOL = "lodestone/1"
MCP_VERSION = "2025-06-18"

# The six Core tools: required arguments, then optional ones (spec/3-owner-interface.md, section 3.4).
CORE_TOOLS = {
    "context": ([], ["namespace"]),
    "recall": (["query"], ["namespace", "kinds", "limit"]),
    "get": (["id"], ["max_chars"]),
    "remember": (["namespace", "kind", "title", "body"], ["tags", "links", "aliases", "entity_type", "pinned"]),
    "checkpoint": (["namespace", "thread", "state"], []),
    "forget": (["id", "reason"], []),
}
WRITE_TOOLS = ("remember", "checkpoint", "forget")
SHARED_TOOLS = ("shared", "recall", "get", "context", "changes")
SUMMARY_FIELDS = ("id", "uid", "namespace", "kind", "title", "status", "created", "updated", "pinned")
HIT_FIELDS = ("id", "title", "kind", "namespace", "created", "snippet", "score")
MAP_FIELDS = ("namespace", "notes", "updated", "pinned", "aliases")

KIND_DIRS = {"fact": "facts", "decision": "decisions", "preference": "preferences", "person": "people",
             "thread": "threads", "entity": "entities"}
STATUSES = ("active", "superseded", "retracted", "proposed")
SEGMENT = r"[a-z0-9][a-z0-9._-]{0,63}"
NAMESPACE_RE = re.compile(rf"^{SEGMENT}(/{SEGMENT}){{0,4}}$")
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
SECRET_RE = re.compile(r"(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9-]{30,}|"
                       r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16})")
PIN_MAX_CHARS = 6000
INDEX_WAIT = 15          # seconds a new note may take to show up in recall and context


# --------------------------------------------------------------------------- results

@dataclass
class Check:
    level: str           # core | federation | moving
    name: str
    outcome: str         # pass | fail | warn | skip | unsupported
    detail: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, level: str, name: str, ok: bool, detail: str = "", *, should: bool = False) -> bool:
        outcome = "pass" if ok else ("warn" if should else "fail")
        self.checks.append(Check(level, name, outcome, "" if ok else detail))
        return ok

    def skip(self, level: str, name: str, why: str) -> None:
        self.checks.append(Check(level, name, "skip", why))

    def unsupported(self, level: str, why: str) -> None:
        self.checks.append(Check(level, "level supported", "unsupported", why))

    def verdict(self, level: str) -> str:
        mine = [c for c in self.checks if c.level == level]
        if not mine:
            return "not checked"
        if any(c.outcome == "unsupported" for c in mine):
            return "not supported"
        if any(c.outcome == "fail" for c in mine):
            return "FAIL"
        if any(c.outcome == "skip" for c in mine):
            return "not proven (some checks were skipped)"
        return "pass"

    def print(self, out=sys.stdout) -> None:
        mark = {"pass": "pass", "fail": "FAIL", "warn": "warn", "skip": "skip", "unsupported": "n/a "}
        for level in ("core", "federation", "moving", "repo"):
            mine = [c for c in self.checks if c.level == level]
            if not mine:
                continue
            print(f"\n{level.capitalize()}", file=out)
            for c in mine:
                print(f"  [{mark[c.outcome]}] {c.name}" + (f": {c.detail}" if c.detail else ""), file=out)
        print("\nSummary", file=out)
        for level in ("core", "federation", "moving", "repo"):
            if any(c.level == level for c in self.checks):
                print(f"  {level.capitalize()}: {self.verdict(level)}", file=out)

    @property
    def failed(self) -> bool:
        return any(c.outcome == "fail" for c in self.checks)


# --------------------------------------------------------------------------- HTTP

@dataclass
class Response:
    status: int
    headers: dict
    body: object        # parsed JSON, or text, or bytes for binary
    raw: bytes = b""


def http(method: str, url: str, body: object = None, *, token: str = "", headers: dict | None = None,
         form: dict | None = None, timeout: float = 20) -> Response:
    h = {"Accept": "application/json", "User-Agent": f"lodestone-conformance/{SPEC_VERSION}", **(headers or {})}
    data = None
    if form is not None:
        data, h["Content-Type"] = urlencode(form).encode(), "application/x-www-form-urlencoded"
    elif body is not None:
        data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
    if token:
        h["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data, h, method=method), timeout=timeout) as r:
            status, hdrs, raw = r.status, dict(r.headers), r.read(64 * 1024 * 1024)
    except urllib.error.HTTPError as e:
        status, hdrs, raw = e.code, dict(e.headers), e.read(1024 * 1024)
    except (urllib.error.URLError, OSError) as e:
        return Response(0, {}, f"unreachable: {getattr(e, 'reason', e)}")
    ctype = next((v for k, v in hdrs.items() if k.lower() == "content-type"), "")
    if "json" in ctype or raw[:1] in (b"{", b"["):
        try:
            return Response(status, hdrs, json.loads(raw or b"null"), raw)
        except ValueError:
            pass
    if "text/event-stream" in ctype:          # a server may answer a POST with a one-event stream
        for line in raw.decode(errors="replace").splitlines():
            if line.startswith("data:"):
                try:
                    return Response(status, hdrs, json.loads(line[5:]), raw)
                except ValueError:
                    break
    if ctype.startswith("text/"):
        return Response(status, hdrs, raw[:2000].decode(errors="replace"), raw)
    return Response(status, hdrs, raw, raw)


def header(resp: Response, name: str) -> str:
    return next((v for k, v in resp.headers.items() if k.lower() == name.lower()), "")


def short(value: object, n: int = 200) -> str:
    s = value if isinstance(value, str) else json.dumps(value, default=str)
    return s if len(s) <= n else s[:n] + "…"


class Mcp:
    """A minimal MCP client over Streamable HTTP."""

    def __init__(self, url: str, token: str):
        self.url, self.token, self.session, self.n = url, token, "", 0

    def rpc(self, method: str, params: dict | None = None) -> Response:
        self.n += 1
        h = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": MCP_VERSION}
        if self.session:
            h["Mcp-Session-Id"] = self.session
        resp = http("POST", self.url, {"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}},
                    token=self.token, headers=h)
        self.session = header(resp, "Mcp-Session-Id") or self.session
        return resp

    def notify(self, method: str) -> None:
        h = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": MCP_VERSION}
        if self.session:
            h["Mcp-Session-Id"] = self.session
        http("POST", self.url, {"jsonrpc": "2.0", "method": method}, token=self.token, headers=h)

    def call(self, tool: str, **args) -> dict:
        """The tool result, or {"_rpc_error": ...} / {"_http": status} when there is none."""
        resp = self.rpc("tools/call", {"name": tool, "arguments": args})
        if not isinstance(resp.body, dict):
            return {"_http": resp.status, "_body": short(resp.body)}
        if "error" in resp.body:
            return {"_rpc_error": resp.body["error"]}
        return resp.body.get("result") or {}


def text_of(result: dict) -> str:
    return "\n".join(c.get("text", "") for c in result.get("content") or [] if isinstance(c, dict))


def structured(result: dict) -> dict:
    s = result.get("structuredContent")
    return s if isinstance(s, dict) else {}


# --------------------------------------------------------------------------- Core: sign-in

def check_signin(r: Report, base: str, mcp_url: str) -> None:
    L = "core"
    resp = http("POST", mcp_url, {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                headers={"Accept": "application/json, text/event-stream"})
    if resp.status == 0:
        r.add(L, "server answers", False, str(resp.body))
        return
    www = header(resp, "WWW-Authenticate")
    r.add(L, "MCP without a token is refused (401)", resp.status == 401, f"HTTP {resp.status}")
    m = re.search(r'resource_metadata="([^"]+)"', www)
    r.add(L, "401 names the protected resource metadata (WWW-Authenticate)", bool(m), f"got {www!r}")
    meta_url = m.group(1) if m else base + "/.well-known/oauth-protected-resource"
    resp = http("GET", meta_url)
    prm = resp.body if isinstance(resp.body, dict) else {}
    ok = r.add(L, "protected resource metadata (RFC 9728)", resp.status == 200 and bool(prm.get("resource"))
               and isinstance(prm.get("authorization_servers"), list) and bool(prm.get("authorization_servers")),
               f"HTTP {resp.status}: {short(resp.body)}")
    if not ok:
        return
    issuer = str(prm["authorization_servers"][0]).rstrip("/")
    parts = urlsplit(issuer)
    as_url = f"{parts.scheme}://{parts.netloc}/.well-known/oauth-authorization-server{parts.path}"
    resp = http("GET", as_url)
    asm = resp.body if isinstance(resp.body, dict) else {}
    r.add(L, "authorization server metadata (RFC 8414)", resp.status == 200 and bool(asm.get("authorization_endpoint"))
          and bool(asm.get("token_endpoint")), f"HTTP {resp.status} at {as_url}: {short(resp.body)}")
    r.add(L, "authorization code grant with PKCE S256", "S256" in (asm.get("code_challenge_methods_supported") or [])
          and "code" in (asm.get("response_types_supported") or ["code"]),
          f"code_challenge_methods_supported: {asm.get('code_challenge_methods_supported')!r}")
    r.add(L, "refresh tokens", "refresh_token" in (asm.get("grant_types_supported") or []),
          f"grant_types_supported: {asm.get('grant_types_supported')!r}", should=True)
    reg = asm.get("registration_endpoint")
    if not r.add(L, "dynamic client registration offered (RFC 7591)", bool(reg), "no registration_endpoint"):
        return
    resp = http("POST", reg, {"client_name": "Lodestone conformance suite",
                              "redirect_uris": ["http://127.0.0.1:8976/callback"],
                              "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
                              "token_endpoint_auth_method": "none"})
    r.add(L, "dynamic client registration accepts a loopback app", resp.status in (200, 201)
          and isinstance(resp.body, dict) and bool(resp.body.get("client_id")), f"HTTP {resp.status}: {short(resp.body)}")


# --------------------------------------------------------------------------- Core: tools

def check_session(r: Report, mcp: Mcp) -> dict | None:
    L = "core"
    resp = mcp.rpc("initialize", {"protocolVersion": MCP_VERSION, "capabilities": {},
                                  "clientInfo": {"name": "lodestone-conformance", "version": SPEC_VERSION}})
    res = resp.body.get("result") if isinstance(resp.body, dict) else None
    if not r.add(L, "initialize with the token", resp.status == 200 and isinstance(res, dict)
                 and bool(res.get("protocolVersion")), f"HTTP {resp.status}: {short(resp.body)}"):
        return None
    r.add(L, f"MCP version {MCP_VERSION} or later", str(res.get("protocolVersion")) >= MCP_VERSION,
          f"server chose {res.get('protocolVersion')!r}")
    r.add(L, "initialize includes instructions for agents", bool(res.get("instructions")), "no instructions",
          should=True)
    mcp.notify("notifications/initialized")
    resp = mcp.rpc("tools/list")
    tools = (resp.body.get("result") or {}).get("tools") if isinstance(resp.body, dict) else None
    if not r.add(L, "tools/list", isinstance(tools, list), f"HTTP {resp.status}: {short(resp.body)}"):
        return None
    by_name = {t.get("name"): t for t in tools if isinstance(t, dict)}
    for name, (required, optional) in CORE_TOOLS.items():
        tool = by_name.get(name)
        if not r.add(L, f"tool `{name}` is offered", tool is not None, f"tools: {sorted(by_name)}"):
            continue
        schema = tool.get("inputSchema") or {}
        props, req = set((schema.get("properties") or {})), set(schema.get("required") or [])
        missing = [a for a in required + optional if a not in props]
        r.add(L, f"`{name}` takes the arguments in the spec", not missing, f"missing: {missing}")
        r.add(L, f"`{name}` requires exactly {required or 'no arguments'}", req == set(required),
              f"requires {sorted(req)}")
    return by_name


def check_reads(r: Report, mcp: Mcp) -> None:
    L = "core"
    res = mcp.call("context")
    s = structured(res)
    rows = s.get("namespaces")
    ok = r.add(L, "`context` without a namespace returns the namespace map", not res.get("isError")
               and bool(text_of(res)) and isinstance(rows, list), short(res))
    if ok and rows:
        bad = [row for row in rows if not all(k in row for k in MAP_FIELDS)]
        r.add(L, "namespace map rows have namespace, notes, updated, pinned, aliases", not bad, short(bad))
    res = mcp.call("recall", query="the")
    hits = structured(res).get("hits")
    ok = r.add(L, "`recall` returns structured hits", not res.get("isError") and isinstance(hits, list)
               and bool(text_of(res)), short(res))
    if ok and hits:
        bad = [h for h in hits if not all(k in h for k in HIT_FIELDS)]
        r.add(L, f"hits have {', '.join(HIT_FIELDS)}", not bad, short(bad))
    res = mcp.call("get", id="memory/no-such-namespace-x9/facts/no-such-note.md")
    r.add(L, "`get` with an unknown id is a tool error", res.get("isError") is True, short(res))
    res = mcp.call("no_such_tool_x9")
    r.add(L, "an unknown tool is a JSON-RPC error", "_rpc_error" in res, short(res))
    res = mcp.rpc("tools/call", {"name": "recall", "arguments": {"query": "the"}})
    r.add(L, "results carry their text in structuredContent too", isinstance(resp_struct(res), dict)
          and "text" in resp_struct(res), "structuredContent has no `text`", should=True)


def resp_struct(resp: Response) -> dict | None:
    if isinstance(resp.body, dict):
        return (resp.body.get("result") or {}).get("structuredContent")
    return None


def wait_for(fn, seconds: float = INDEX_WAIT) -> bool:
    end = time.monotonic() + seconds
    while True:
        if fn():
            return True
        if time.monotonic() > end:
            return False
        time.sleep(1)


def check_writes(r: Report, mcp: Mcp) -> None:
    L = "core"
    run = secrets.token_hex(3)
    ns = f"conformance/run-{run}"
    marker = f"marker{secrets.token_hex(6)}"
    created: list[str] = []

    def summary_ok(res: dict) -> bool:
        s = structured(res)
        return not res.get("isError") and all(k in s for k in SUMMARY_FIELDS)

    try:
        # remember, get, recall, context
        res = mcp.call("remember", namespace=ns, kind="fact", title=f"Conformance fact {run}",
                       body=f"This note was written by the conformance suite. The marker is {marker}.",
                       tags=["conformance"])
        if not r.add(L, "`remember` saves a note and returns a note summary", summary_ok(res), short(res)):
            return
        note = structured(res)
        created.append(note["id"])
        r.add(L, "the new note is active, with the namespace and kind asked for", note["status"] == "active"
              and note["namespace"] == ns and note["kind"] == "fact", short(note))
        r.add(L, "times are RFC 3339 with an offset", bool(TIME_RE.match(str(note["created"])))
              and bool(TIME_RE.match(str(note["updated"]))), f"{note['created']!r}, {note['updated']!r}")
        res = mcp.call("get", id=note["id"])
        r.add(L, "`get` reads the new note at once", not res.get("isError") and marker in text_of(res)
              and structured(res).get("id") == note["id"] and "text" in structured(res), short(res))
        res = mcp.call("get", id=note["uid"])
        r.add(L, "`get` reads a note by its uid too", not res.get("isError") and marker in text_of(res)
              and structured(res).get("id") == note["id"], short(res))
        found = wait_for(lambda: note["id"] in [h.get("id") for h in
                                                 structured(mcp.call("recall", query=marker)).get("hits") or []])
        r.add(L, f"`recall` finds the new note (within {INDEX_WAIT}s)", found, f"searched for {marker}", should=True)
        r.add(L, "`recall` with namespace finds it too",
              note["id"] in [h.get("id") for h in structured(mcp.call("recall", query=marker, namespace=ns)).get("hits") or []],
              "not found", should=True)
        r.add(L, "`context` on the namespace lists the note with its id",
              wait_for(lambda: note["id"] in text_of(mcp.call("context", namespace=ns))),
              short(text_of(mcp.call("context", namespace=ns))))

        # threads
        res = mcp.call("checkpoint", namespace=ns, thread=f"Conformance thread {run}",
                       state=f"Goal: test checkpoint. State one {marker}.")
        r.add(L, "`checkpoint` saves a thread and returns a note summary", summary_ok(res)
              and structured(res).get("kind") == "thread", short(res))
        first = structured(res)
        if first.get("id"):
            created.append(first["id"])
        res = mcp.call("checkpoint", namespace=ns, thread=f"Conformance thread {run}",
                       state=f"Goal: test checkpoint. State two {marker}.")
        second = structured(res)
        r.add(L, "checkpointing the same thread again keeps its uid", bool(first.get("uid"))
              and first.get("uid") == second.get("uid"), f"{first.get('uid')!r} then {second.get('uid')!r}")
        ctx = text_of(mcp.call("context", namespace=ns))
        r.add(L, "`context` shows the thread's latest state, not the old one", "State two" in ctx
              and "State one" not in ctx, short(ctx))

        # pinned notes
        res = mcp.call("remember", namespace=ns, kind="fact", title=f"Conformance brief A {run}",
                       body=f"Brief A for this namespace. pinA{marker}", pinned=True)
        pin_a = structured(res)
        if pin_a.get("id"):
            created.append(pin_a["id"])
        r.add(L, "`remember` with pinned: true pins the note", summary_ok(res) and pin_a.get("pinned") is True,
              short(res))
        ctx = text_of(mcp.call("context", namespace=ns))
        r.add(L, "`context` shows the pinned note first, then the thread",
              f"pinA{marker}" in ctx and "State two" in ctx and ctx.index(f"pinA{marker}") < ctx.index("State two"),
              short(ctx, 400))
        res = mcp.call("remember", namespace=ns, kind="fact", title=f"Conformance brief B {run}",
                       body=f"Brief B for this namespace. pinB{marker}", pinned=True,
                       aliases=[f"Conformance alias {run}"])
        pin_b = structured(res)
        if pin_b.get("id"):
            created.append(pin_b["id"])
        rows = structured(mcp.call("context")).get("namespaces") or []
        row = next((x for x in rows if x.get("namespace") == ns), {})
        r.add(L, "pinning another note unpins the first (namespace map shows the new one)",
              (row.get("pinned") or {}).get("id") == pin_b.get("id"), short(row))
        res = mcp.call("get", id=pin_a.get("id", ""))
        r.add(L, "the previously pinned note is still there, as an ordinary note", not res.get("isError")
              and f"pinA{marker}" in text_of(res), short(res))
        res = mcp.call("remember", namespace=ns, kind="fact", title=f"Conformance long brief {run}",
                       body="x" * (PIN_MAX_CHARS + 500), pinned=True)
        if not res.get("isError") and structured(res).get("id"):
            created.append(structured(res)["id"])
        r.add(L, f"pinning a note over {PIN_MAX_CHARS} characters is refused", res.get("isError") is True,
              "it was pinned", should=True)

        # finding a namespace by name
        res = mcp.call("context", namespace=f"run-{run}")
        r.add(L, "`context` finds a namespace by its last segment", structured(res).get("namespace") == ns,
              short(structured(res)))
        res = mcp.call("context", namespace=f"Conformance alias {run}")
        r.add(L, "`context` finds a namespace by its pinned note's alias", structured(res).get("namespace") == ns,
              short(structured(res)))

        # bad input
        for label, args in (("a bad namespace", {"namespace": "Not A Namespace!", "kind": "fact"}),
                            ("a namespace named like a kind folder", {"namespace": f"{ns}/people", "kind": "fact"}),
                            ("kind thread", {"namespace": ns, "kind": "thread"}),
                            ("an unknown kind", {"namespace": ns, "kind": "rumour"}),
                            ("an empty body", {"namespace": ns, "kind": "fact", "body": ""})):
            args = {"title": f"Should be refused {run}", "body": "refused", **args}
            res = mcp.call("remember", **args)
            if not res.get("isError") and structured(res).get("id"):
                created.append(structured(res)["id"])
            r.add(L, f"`remember` with {label} is a tool error", res.get("isError") is True, short(res))

        # forget, by uid
        res = mcp.call("forget", id=note["uid"], reason="conformance test")
        r.add(L, "`forget` retracts the note, given its uid", summary_ok(res)
              and structured(res).get("status") == "retracted" and structured(res).get("id") == note["id"], short(res))
        if not res.get("isError"):
            created.remove(note["id"])
        r.add(L, "`recall` no longer finds a retracted note",
              wait_for(lambda: note["id"] not in [h.get("id") for h in
                                                   structured(mcp.call("recall", query=marker)).get("hits") or []]),
              "still found")
        r.add(L, "`context` no longer lists a retracted note",
              note["id"] not in text_of(mcp.call("context", namespace=ns)), "still listed")
        res = mcp.call("get", id=note["id"])
        r.add(L, "`get` still reads a retracted note", not res.get("isError") and marker in text_of(res), short(res))
        r.add(L, "`get` shows that the note is retracted", "retracted" in text_of(res), short(res), should=True)
    finally:
        left = []
        for ref in created:
            res = mcp.call("forget", id=ref, reason="conformance test cleanup")
            if res.get("isError") or "_rpc_error" in res:
                left.append(ref)
        r.add(L, f"clean-up: every test note in {ns} retracted", not left, f"could not retract: {left}", should=True)


# --------------------------------------------------------------------------- Federation

def check_discovery(r: Report, base: str) -> dict | None:
    """The discovery file every server has (section 3.12)."""
    L = "core"
    resp = http("GET", base + "/.well-known/lodestone")
    doc = resp.body if isinstance(resp.body, dict) else None
    if not r.add(L, "discovery file (/.well-known/lodestone) without sign-in", resp.status == 200 and doc is not None,
                 f"HTTP {resp.status}: {short(resp.body)}"):
        return None
    r.add(L, "discovery: protocol is lodestone/1", doc.get("protocol") == PROTOCOL, f"got {doc.get('protocol')!r}")
    r.add(L, "discovery: base_url is the address used", str(doc.get("base_url", "")).rstrip("/") == base,
          f"got {doc.get('base_url')!r}, expected {base!r}")
    levels = doc.get("levels")
    r.add(L, "discovery: levels lists core", isinstance(levels, list) and "core" in levels
          and set(levels) <= {"core", "federation", "moving"}, f"got {levels!r}")
    if not doc.get("publications"):
        r.add(L, "discovery: no owner name without a listed publication", "owner" not in doc,
              f"got owner {doc.get('owner')!r}")
    return doc


def check_federation(r: Report, base: str, doc: dict | None, publication: str, credential: str) -> None:
    L = "federation"
    if doc is None:
        resp = http("GET", base + "/.well-known/lodestone")
        doc = resp.body if isinstance(resp.body, dict) else None
    if doc is None or ("federation" not in (doc.get("levels") or [])
                       and not (doc.get("endpoints") or {}).get("federation")):
        r.unsupported(L, "the discovery file lists no `federation` level and no federation endpoint")
        return
    r.add(L, "discovery lists federation in levels", "federation" in (doc.get("levels") or []),
          f"got {doc.get('levels')!r}")
    pubs = doc.get("publications")
    r.add(L, "publications is a list", isinstance(pubs, list), f"got {type(pubs).__name__}")
    for p in pubs or []:
        r.add(L, f"listed publication {p.get('slug')!r} has slug, title, mcp and release",
              all(p.get(k) for k in ("slug", "title", "mcp", "release")), short(p))
    if pubs:
        r.add(L, "owner.display_name (there is a listed publication)", isinstance(doc.get("owner"), dict)
              and bool(doc["owner"].get("display_name")), f"got {doc.get('owner')!r}")

    fed = base + "/federation/v1"
    for method, path, body in (("GET", "shares", None), ("POST", "search", {"query": "test"})):
        resp = http(method, f"{fed}/{path}", body)
        r.add(L, f"{method} {path} without a credential is refused (401)", resp.status == 401, f"HTTP {resp.status}")
    resp = http("GET", f"{fed}/shares", token="not-a-real-credential-x9")
    r.add(L, "an unknown credential is refused (401)", resp.status == 401, f"HTTP {resp.status}")
    resp = http("GET", f"{fed}/pub/no-such-publication-x9/shares")
    r.add(L, "an unknown publication is 404", resp.status == 404, f"HTTP {resp.status}")
    resp = http("POST", base + "/pub/no-such-publication-x9/mcp", {"jsonrpc": "2.0", "id": 1, "method": "ping"})
    r.add(L, "an unknown publication's MCP address is 404", resp.status == 404, f"HTTP {resp.status}")
    resp = http("POST", f"{fed}/peer", {"invite": "not-a-real-invite-x9", "base_url": base})
    r.add(L, "a bad invite is refused (401)", resp.status == 401, f"HTTP {resp.status}")
    for res in (http("GET", f"{fed}/shares"),):
        r.add(L, "errors are JSON with an `error` field", isinstance(res.body, dict) and "error" in res.body,
              short(res.body))

    slug = publication or next((p.get("slug") for p in pubs or [] if p.get("slug")), "")
    if slug:
        _federation_endpoints(r, f"{fed}/pub/{slug}", "", f"publication {slug!r}")
        mcp = Mcp(f"{base}/pub/{slug}/mcp", "")
        resp = mcp.rpc("initialize", {"protocolVersion": MCP_VERSION, "capabilities": {},
                                      "clientInfo": {"name": "lodestone-conformance", "version": SPEC_VERSION}})
        r.add(L, f"publication {slug!r}: MCP needs no sign-in", resp.status == 200, f"HTTP {resp.status}")
        resp = mcp.rpc("tools/list")
        tools = {t.get("name") for t in ((resp.body or {}).get("result") or {}).get("tools", [])} \
            if isinstance(resp.body, dict) else set()
        r.add(L, f"publication {slug!r}: MCP offers the shared tools", set(SHARED_TOOLS) <= tools,
              f"tools: {sorted(tools)}")
        r.add(L, f"publication {slug!r}: MCP offers no write tools", not tools & {*WRITE_TOOLS, "shared_with_me"},
              f"tools: {sorted(tools)}")
    else:
        r.skip(L, "publication endpoints", "no listed publication; pass --publication <slug> to check one")
    if credential:
        _federation_endpoints(r, fed, credential, "peer")
    else:
        r.skip(L, "peer endpoints", "set LODESTONE_PEER_CREDENTIAL to check them as a peer")


def _federation_endpoints(r: Report, root: str, credential: str, who: str) -> None:
    L = "federation"
    resp = http("GET", f"{root}/shares", token=credential)
    res = resp.body if isinstance(resp.body, dict) else {}
    r.add(L, f"{who}: GET shares", resp.status == 200 and res.get("protocol") == PROTOCOL and "owner" in res
          and ("shares" in res or "publication" in res), f"HTTP {resp.status}: {short(resp.body)}")
    resp = http("POST", f"{root}/search", {"query": "the", "limit": 3}, token=credential)
    hits = resp.body.get("hits") if isinstance(resp.body, dict) else None
    r.add(L, f"{who}: POST search returns hits", resp.status == 200 and isinstance(hits, list)
          and all({"id", "title"} <= set(h) for h in hits), f"HTTP {resp.status}: {short(resp.body)}")
    if hits:
        resp = http("GET", f"{root}/note?" + urlencode({"id": hits[0]["id"]}), token=credential)
        note = resp.body if isinstance(resp.body, dict) else {}
        r.add(L, f"{who}: GET note returns the hit", resp.status == 200
              and all(k in note for k in ("id", "uid", "title", "kind", "namespace", "updated", "body")),
              f"HTTP {resp.status}: {short(resp.body)}")
    resp = http("GET", f"{root}/note?" + urlencode({"id": "memory/no/such/note-x9.md"}), token=credential)
    r.add(L, f"{who}: GET note outside the grant is 404", resp.status == 404, f"HTTP {resp.status}")
    resp = http("GET", f"{root}/changes?" + urlencode({"since": "2000-01-01"}), token=credential)
    res = resp.body if isinstance(resp.body, dict) else {}
    r.add(L, f"{who}: GET changes", resp.status == 200
          and all(isinstance(res.get(k), list) for k in ("added", "updated", "removed")),
          f"HTTP {resp.status}: {short(resp.body)}")


# --------------------------------------------------------------------------- Moving

def check_moving(r: Report, base: str, doc: dict | None, token: str) -> None:
    L = "moving"
    if doc is None:
        resp = http("GET", base + "/.well-known/lodestone")
        doc = resp.body if isinstance(resp.body, dict) else None
    if doc is None:
        r.unsupported(L, "no discovery file, so no way to announce a move")
        return
    export = (doc.get("endpoints") or {}).get("export")
    if not export and "moving" not in (doc.get("levels") or []):
        r.unsupported(L, "the discovery file neither lists `moving` in levels nor has endpoints.export")
        return
    if not r.add(L, "discovery lists endpoints.export", bool(export), "no export endpoint"):
        return
    url = export if export.startswith("http") else base + export
    resp = http("GET", url, headers={"Accept": "application/x-git-bundle"})
    r.add(L, "export without a token is refused (401 or 403)", resp.status in (401, 403), f"HTTP {resp.status}")
    if token:
        resp = http("GET", url, token=token, headers={"Accept": "application/x-git-bundle"}, timeout=300)
        raw = resp.raw or b""
        r.add(L, "export returns a git bundle", resp.status == 200
              and (raw.startswith(b"# v2 git bundle") or raw.startswith(b"# v3 git bundle")),
              f"HTTP {resp.status}, starts {raw[:30]!r}")
        r.add(L, "export is application/x-git-bundle", "x-git-bundle" in header(resp, "Content-Type"),
              header(resp, "Content-Type"), should=True)
    else:
        r.skip(L, "export with the owner token", "set LODESTONE_TOKEN")
    keys = doc.get("keys")
    r.add(L, "discovery publishes an Ed25519 key for the moved record", isinstance(keys, list) and any(
        isinstance(k, dict) and k.get("kty") == "OKP" and k.get("crv") == "Ed25519" and k.get("x") for k in keys),
        f"keys: {short(keys)}")
    if doc.get("moved"):
        mv = doc["moved"]
        r.add(L, "moved record has from, to, at and a signature", isinstance(mv, dict)
              and all(mv.get(k) for k in ("from", "to", "at")) and bool(doc.get("signature")), short(doc))


# --------------------------------------------------------------------------- repository

def parse_frontmatter(text: str) -> tuple[dict | None, str]:
    """The frontmatter subset in spec/2-memory-format.md. Returns (None, text) without frontmatter."""
    m = re.match(r"\A---\n(.*?)\n---\n?", text, re.DOTALL)
    if not m:
        return None, text
    meta: dict = {}
    key = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s*(.*)$", line)
        if item and key is not None:
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(_unquote(item.group(1)))
            continue
        k, sep, v = line.partition(":")
        if not sep or line[0].isspace():
            raise ValueError(f"not a `key: value` line: {line!r}")
        key = k.strip()
        meta[key] = _value(v) if v.strip() else []
    return meta, text[m.end():]


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return json.loads(s)
    if len(s) >= 2 and s[0] == s[-1] == "'":
        return s[1:-1].replace("''", "'")
    return s


def _split(inner: str) -> list[str]:
    out, buf, quote = [], "", ""
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote and not buf.endswith("\\" + quote):
                quote = ""
        elif ch in "\"'":
            quote, buf = ch, buf + ch
        elif ch == ",":
            out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())
    return out


def _value(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [_unquote(x) for x in _split(raw[1:-1])]
    if raw.startswith("{") and raw.endswith("}"):
        return {k.strip(): _unquote(v) for k, _, v in (item.partition(":") for item in _split(raw[1:-1]))}
    return _unquote(raw)


def check_repo(r: Report, root: Path) -> None:
    L = "repo"
    if not r.add(L, "memory/ exists", (root / "memory").is_dir(), f"no memory/ in {root}"):
        return
    dir_kinds = {v: k for k, v in KIND_DIRS.items()}
    ids: dict[str, str] = {}
    pinned: dict[str, list[str]] = {}
    problems: list[str] = []
    count = 0
    for path in sorted((root / "memory").rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        parts = PurePosixPath(rel).parts
        folder = parts[-2] if len(parts) >= 3 else ""
        inbox = folder == "_inbox"
        if folder not in dir_kinds and not inbox:
            problems.append(f"{rel}: not in a kind folder ({', '.join(KIND_DIRS.values())}) or _inbox")
            continue
        count += 1
        text = path.read_text(encoding="utf-8")
        try:
            meta, body = parse_frontmatter(text)
        except (ValueError, json.JSONDecodeError) as exc:
            problems.append(f"{rel}: frontmatter: {exc}")
            continue
        if meta is None:
            problems.append(f"{rel}: no frontmatter")
            continue
        missing = [k for k in ("id", "namespace", "kind", "title", "status", "created", "updated") if not meta.get(k)]
        if missing:
            problems.append(f"{rel}: missing {', '.join(missing)}")
            continue
        ns = "/".join(parts[1:-2])
        if meta["namespace"] != ns:
            problems.append(f"{rel}: namespace {meta['namespace']!r} does not match its folder {ns!r}")
        if not NAMESPACE_RE.match(str(meta["namespace"])) or any(s.startswith("_") for s in ns.split("/")):
            problems.append(f"{rel}: invalid namespace {meta['namespace']!r}")
        elif any(s in KIND_DIRS.values() for s in str(meta["namespace"]).split("/")):
            problems.append(f"{rel}: namespace {meta['namespace']!r} is named like a kind folder")
        if meta["kind"] not in KIND_DIRS:
            problems.append(f"{rel}: unknown kind {meta['kind']!r}")
        elif not inbox and dir_kinds[folder] != meta["kind"]:
            problems.append(f"{rel}: kind {meta['kind']!r} is in the {folder}/ folder")
        if meta["status"] not in STATUSES:
            problems.append(f"{rel}: unknown status {meta['status']!r}")
        for k in ("created", "updated"):
            if not TIME_RE.match(str(meta[k])):
                problems.append(f"{rel}: {k} {meta[k]!r} is not an RFC 3339 time with an offset")
        if "\n" in str(meta["title"]) or len(str(meta["title"])) > 200:
            problems.append(f"{rel}: title must be one line of at most 200 characters")
        if not body.strip():
            problems.append(f"{rel}: empty body")
        if meta["id"] in ids:
            problems.append(f"{rel}: id {meta['id']!r} is also used by {ids[meta['id']]}")
        ids[meta["id"]] = rel
        if str(meta.get("pinned", "")).lower() == "true":
            if meta["kind"] == "thread" or meta["status"] != "active":
                problems.append(f"{rel}: a pinned note must be active and not a thread")
            elif len(body.strip()) > PIN_MAX_CHARS:
                problems.append(f"{rel}: pinned note is over {PIN_MAX_CHARS} characters (SHOULD)")
            pinned.setdefault(meta["namespace"], []).append(rel)
        if meta["status"] == "retracted" and not meta.get("reason"):
            problems.append(f"{rel}: retracted without a reason")
    r.add(L, f"{count} notes are in kind folders with valid frontmatter", not problems, "\n      " +
          "\n      ".join(problems[:50]) + (f"\n      … and {len(problems) - 50} more" if len(problems) > 50 else ""))
    two = {ns: rels for ns, rels in pinned.items() if len(rels) > 1}
    r.add(L, "at most one pinned note per namespace", not two, short(two), should=True)
    digests = root / "digests"
    bad = [p.relative_to(root).as_posix() for p in digests.rglob("*") if p.is_file()
           and not re.match(r"^\d{4}-\d{2}-\d{2}\.md$", p.name)] if digests.is_dir() else []
    r.add(L, "digests are digests/<namespace>/<YYYY-MM-DD>.md", not bad, short(bad))
    leaked = []
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts and p.stat().st_size < 5_000_000:
            try:
                if SECRET_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
                    leaked.append(p.relative_to(root).as_posix())
            except OSError:
                pass
    r.add(L, "no secrets in the repository (a few common token shapes)", not leaked, short(leaked))


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=f"Lodestone Protocol {SPEC_VERSION} conformance suite")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sv = sub.add_parser("server", help="check a running server")
    sv.add_argument("url", help="the server's base URL, e.g. https://lodestone.example.com")
    sv.add_argument("--mcp", default="", help="the MCP address, if not <url>/mcp")
    sv.add_argument("--write", action="store_true",
                    help="also check the write tools, in a new namespace conformance/run-<id> (cleaned up after)")
    sv.add_argument("--levels", default="core,federation,moving", help="which levels to check (comma-separated)")
    sv.add_argument("--publication", default="", help="a publication slug to check (default: the first listed)")
    sv.add_argument("--json", action="store_true", help="print the results as JSON")
    rp = sub.add_parser("repo", help="check a memory repository on disk")
    rp.add_argument("path")
    rp.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    report = Report()
    if args.cmd == "repo":
        check_repo(report, Path(args.path))
    else:
        base = args.url.rstrip("/")
        levels = {x.strip() for x in args.levels.split(",") if x.strip()}
        token = os.environ.get("LODESTONE_TOKEN", "").strip()
        doc = None
        if "core" in levels:
            mcp_url = args.mcp or base + "/mcp"
            doc = check_discovery(report, base)
            check_signin(report, base, mcp_url)
            if not token:
                report.skip("core", "the six tools", "set LODESTONE_TOKEN to an owner token")
            else:
                mcp = Mcp(mcp_url, token)
                if check_session(report, mcp) is not None:
                    check_reads(report, mcp)
                    if args.write:
                        check_writes(report, mcp)
                    else:
                        report.skip("core", "the write tools", "run with --write to check them")
        if "federation" in levels:
            check_federation(report, base, doc, args.publication,
                             os.environ.get("LODESTONE_PEER_CREDENTIAL", "").strip())
        if "moving" in levels:
            check_moving(report, base, doc, token)
    if args.json:
        print(json.dumps({"spec": SPEC_VERSION, "checks": [c.__dict__ for c in report.checks],
                          "levels": {lv: report.verdict(lv) for lv in ("core", "federation", "moving", "repo")
                                     if any(c.level == lv for c in report.checks)}}, indent=2))
    else:
        report.print()
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
