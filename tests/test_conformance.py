# SPDX-License-Identifier: Apache-2.0
"""Tests for the conformance suite and the schemas. Run: python3 -m unittest discover -s tests"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "conformance"))

import lodestone_conformance as lc  # noqa: E402

try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:  # the suite itself needs only the standard library
    jsonschema = None

EXAMPLE = ROOT / "examples" / "memory-repo"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FrontmatterTest(unittest.TestCase):
    def test_every_form(self):
        meta, body = lc.parse_frontmatter(
            "---\n"
            "id: 01JB2Y3Z4A5B6C7D8E9F0G1H2J\n"
            'title: "Beans: after the frost"\n'
            "tags: [planting, \"a, b\"]\n"
            "author: {agent: claude-desktop, machine: laptop}\n"
            "# a comment\n"
            "\n"
            "links:\n"
            '  - "[[Sam]] knows [[Alex]] (role: neighbour)"\n'
            "  - '[[Sam]] member_of [[Club]]'\n"
            "---\n"
            "Body text.\n")
        self.assertEqual(meta["title"], "Beans: after the frost")
        self.assertEqual(meta["tags"], ["planting", "a, b"])
        self.assertEqual(meta["author"], {"agent": "claude-desktop", "machine": "laptop"})
        self.assertEqual(meta["links"], ["[[Sam]] knows [[Alex]] (role: neighbour)", "[[Sam]] member_of [[Club]]"])
        self.assertEqual(body, "Body text.\n")

    def test_no_frontmatter(self):
        self.assertEqual(lc.parse_frontmatter("# Just a heading\n"), (None, "# Just a heading\n"))


class RepoCheckTest(unittest.TestCase):
    def run_check(self, root: Path) -> lc.Report:
        report = lc.Report()
        lc.check_repo(report, root)
        return report

    def test_example_passes(self):
        report = self.run_check(EXAMPLE)
        self.assertFalse(report.failed, [c for c in report.checks if c.outcome != "pass"])
        self.assertEqual(report.verdict("repo"), "pass")

    def broken(self, rel: str, text: str) -> lc.Report:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            shutil.copytree(EXAMPLE, root)
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return self.run_check(root)

    def assert_fails(self, rel: str, text: str, words: str):
        report = self.broken(rel, text)
        self.assertTrue(report.failed)
        self.assertIn(words, " ".join(c.detail for c in report.checks))

    NOTE = ("---\nid: {id}\nnamespace: {ns}\nkind: {kind}\ntitle: T\nstatus: {status}\n"
            'created: "{t}"\nupdated: "2026-10-01T10:00:00+00:00"\n{extra}---\n{body}\n')

    def note(self, **kw):
        args = dict(id="01JTEST", ns="proj/garden", kind="fact", status="active", t="2026-10-01T10:00:00+00:00",
                    extra="", body="Body.")
        args.update(kw)
        return self.NOTE.format(**args)

    def test_kind_in_wrong_folder(self):
        self.assert_fails("memory/proj/garden/facts/x.md", self.note(kind="decision"), "is in the facts/ folder")

    def test_namespace_must_match_folder(self):
        self.assert_fails("memory/proj/garden/facts/x.md", self.note(ns="proj/other"), "does not match its folder")

    def test_time_needs_an_offset(self):
        self.assert_fails("memory/proj/garden/facts/x.md", self.note(t="2026-10-01 10:00"), "RFC 3339")

    def test_duplicate_id(self):
        self.assert_fails("memory/proj/garden/facts/x.md", self.note(id="01JB2Y8E5F6G7H8J9K0M1N2P3Q"), "also used by")

    def test_unknown_status(self):
        self.assert_fails("memory/proj/garden/facts/x.md", self.note(status="deleted"), "unknown status")

    def test_pinned_thread(self):
        self.assert_fails("memory/proj/garden/threads/x.md", self.note(kind="thread", extra="pinned: true\n"),
                          "must be active and not a thread")

    def test_empty_body(self):
        self.assert_fails("memory/proj/garden/facts/x.md", self.note(body=""), "empty body")

    def test_not_in_a_kind_folder(self):
        self.assert_fails("memory/proj/garden/x.md", self.note(), "not in a kind folder")

    def test_secret(self):
        self.assert_fails("archive/leak.txt", "token ghp_" + "a" * 36, "archive/leak.txt")

    def test_two_pinned_notes_is_a_warning(self):
        report = self.broken("memory/proj/garden/facts/x.md", self.note(extra="pinned: true\n"))
        self.assertFalse(report.failed)
        self.assertIn("warn", [c.outcome for c in report.checks])


@unittest.skipIf(jsonschema is None, "jsonschema is not installed")
class SchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {p: load(p) for p in sorted((ROOT / "schemas").rglob("*.json"))}
        cls.registry = Registry().with_resources(
            (s["$id"], Resource.from_contents(s)) for s in cls.schemas.values())

    def validator(self, name: str):
        schema = self.schemas[ROOT / "schemas" / name]
        return jsonschema.Draft202012Validator(schema, registry=self.registry,
                                               format_checker=jsonschema.FormatChecker())

    def test_schemas_are_valid(self):
        for path, schema in self.schemas.items():
            with self.subTest(path=path.name):
                jsonschema.Draft202012Validator.check_schema(schema)
                self.assertTrue(schema["$id"].endswith(path.relative_to(ROOT / "schemas").as_posix()))

    def test_example_notes_match_the_frontmatter_schema(self):
        v = self.validator("note-frontmatter.schema.json")
        for path in sorted((EXAMPLE / "memory").rglob("*.md")):
            with self.subTest(note=path.name):
                meta, _ = lc.parse_frontmatter(path.read_text(encoding="utf-8"))
                v.validate(meta)

    def test_examples_match_their_schemas(self):
        for example, schema in (("discovery.json", "discovery.schema.json"), ("moved.json", "moved.schema.json"),
                                ("connections.json", "connections.schema.json")):
            with self.subTest(example=example):
                self.validator(schema).validate(load(ROOT / "examples" / example))

    def test_connections_never_hold_a_credential(self):
        doc = load(ROOT / "examples" / "connections.json")
        doc["peers_out"][0]["credential"] = "x"
        self.assertFalse(self.validator("connections.schema.json").is_valid(doc))

    def test_tool_schemas_match_the_suite(self):
        for name, (required, optional) in lc.CORE_TOOLS.items():
            with self.subTest(tool=name):
                schema = self.schemas[ROOT / "schemas" / "tools" / f"{name}.json"]
                self.assertEqual(set(schema.get("required") or []), set(required))
                self.assertEqual(set(schema["properties"]), set(required + optional))

    def test_remember_example(self):
        v = self.validator("tools/remember.json")
        v.validate({"namespace": "proj/garden", "kind": "decision", "title": "Beans after the frost",
                    "body": "Wait for two weeks of warm nights.", "links": ["[[Sam]] knows [[Alex]]"]})
        self.assertFalse(v.is_valid({"namespace": "proj/garden", "kind": "thread", "title": "t", "body": "b"}))
        self.assertFalse(v.is_valid({"namespace": "Not Valid", "kind": "fact", "title": "t", "body": "b"}))


if __name__ == "__main__":
    unittest.main()
