"""Unit tests for zotero_bridge.py — isolated temp Zotero library, no user DB access."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT = SCRIPTS / "zotero_bridge.py"
sys.path.insert(0, str(SCRIPTS))

import zotero_bridge as bridge  # noqa: E402


SCHEMA = """
CREATE TABLE items (
  itemID INTEGER PRIMARY KEY, itemTypeID INT NOT NULL,
  dateAdded TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  dateModified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  libraryID INT NOT NULL, key TEXT NOT NULL, version INT NOT NULL DEFAULT 0,
  synced INT NOT NULL DEFAULT 0, UNIQUE (libraryID, key)
);
CREATE TABLE itemTypes (
  itemTypeID INTEGER PRIMARY KEY, typeName TEXT,
  templateItemTypeID INT, display INT DEFAULT 1
);
CREATE TABLE fields (fieldID INTEGER PRIMARY KEY, fieldName TEXT, fieldFormatID INT);
CREATE TABLE itemData (itemID INT, fieldID INT, valueID, PRIMARY KEY (itemID, fieldID));
CREATE TABLE itemDataValues (valueID INTEGER PRIMARY KEY, value UNIQUE, valueNormalized TEXT);
CREATE TABLE creators (
  creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT, fieldMode INT,
  firstNameNormalized TEXT, lastNameNormalized TEXT
);
CREATE TABLE creatorTypes (creatorTypeID INTEGER PRIMARY KEY, creatorType TEXT);
CREATE TABLE itemCreators (
  itemID INT NOT NULL, creatorID INT NOT NULL, creatorTypeID INT NOT NULL DEFAULT 1,
  orderIndex INT NOT NULL DEFAULT 0,
  PRIMARY KEY (itemID, creatorID, creatorTypeID, orderIndex), UNIQUE (itemID, orderIndex)
);
CREATE TABLE itemAttachments (
  itemID INTEGER PRIMARY KEY, parentItemID INT, linkMode INT, contentType TEXT,
  charsetID INT, path TEXT
);
CREATE TABLE itemAnnotations (
  itemID INTEGER PRIMARY KEY, parentItemID INT NOT NULL, type INTEGER NOT NULL,
  authorName TEXT, text TEXT, comment TEXT, color TEXT, pageLabel TEXT,
  sortIndex TEXT NOT NULL, position TEXT NOT NULL, isExternal INT NOT NULL
);
CREATE TABLE collections (
  collectionID INTEGER PRIMARY KEY, collectionName TEXT NOT NULL,
  parentCollectionID INT DEFAULT NULL, libraryID INT NOT NULL, key TEXT NOT NULL,
  version INT NOT NULL DEFAULT 0, synced INT NOT NULL DEFAULT 0
);
CREATE TABLE collectionItems (
  collectionID INT NOT NULL, itemID INT NOT NULL, orderIndex INT NOT NULL DEFAULT 0,
  PRIMARY KEY (collectionID, itemID)
);
CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, nameNormalized TEXT);
CREATE TABLE itemTags (itemID INT NOT NULL, tagID INT NOT NULL, type INT NOT NULL,
  PRIMARY KEY (itemID, tagID));
CREATE TABLE deletedItems (itemID INTEGER PRIMARY KEY, dateDeleted DEFAULT CURRENT_TIMESTAMP NOT NULL);
CREATE TABLE deletedCollections (collectionID INTEGER PRIMARY KEY, dateDeleted DEFAULT CURRENT_TIMESTAMP NOT NULL);
"""


class ZoteroBridgeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._root = tempfile.TemporaryDirectory(prefix="zotero_bridge_tests_")
        cls.zdir = Path(cls._root.name) / "Zotero"
        cls.zdir.mkdir(parents=True)
        (cls.zdir / "storage" / "ATTACH01").mkdir(parents=True)
        (cls.zdir / "storage" / "ATTACH02").mkdir(parents=True)
        (cls.zdir / "storage" / "ATTACH01" / "paper.pdf").write_bytes(b"%PDF-1.4 fake")
        (cls.zdir / "storage" / "ATTACH02" / "paper2.pdf").write_bytes(b"%PDF-1.4 fake")

        cls.con = sqlite3.connect(cls.zdir / "zotero.sqlite")
        cls.con.executescript(SCHEMA)
        cls.con.execute("PRAGMA journal_mode=WAL")
        cls._seed(cls.con)
        cls.con.commit()
        # Keep this connection open so the -wal file stays live (WAL-safe test).

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls._root.cleanup()

    @staticmethod
    def _seed(con):
        types = [(1, "annotation"), (3, "attachment"), (7, "book"),
                 (11, "conferencePaper"), (22, "journalArticle"), (28, "note"),
                 (31, "preprint")]
        con.executemany("INSERT INTO itemTypes (itemTypeID,typeName) VALUES (?,?)", types)
        con.execute("INSERT INTO creatorTypes (creatorTypeID,creatorType) VALUES (1,'author')")
        con.executemany("INSERT INTO fields (fieldID,fieldName) VALUES (?,?)",
                        [(1, "title"), (2, "abstractNote"), (3, "date")])

        items = [
            (10, 11, "2026-01-10 10:00:00", "PAPER001"),
            (11, 3, "2026-01-10 10:01:00", "ATTACH01"),
            (12, 1, "2026-01-10 10:02:00", "ANN001"),
            (13, 1, "2026-01-10 10:03:00", "ANN002"),
            (14, 1, "2026-01-10 10:04:00", "ANN003"),
            (15, 1, "2026-01-10 10:05:00", "ANNDEL"),
            (20, 22, "2026-01-15 12:00:00", "PAPER002"),
            (21, 3, "2026-01-15 12:01:00", "ATTACH02"),
            (30, 31, "2026-01-20 09:00:00", "DELETED01"),
            (40, 28, "2026-01-21 09:00:00", "NOTE001"),
        ]
        con.executemany(
            "INSERT INTO items (itemID,itemTypeID,dateAdded,libraryID,key) VALUES (?,?,?,1,?)", items)

        values = [
            (1, "Attention Is All You Need"), (2, "We propose a transformer architecture."),
            (3, "2017"), (4, "Feature-Focused Test Generation"), (5, "2026-01"),
            (6, "Deleted Paper"), (7, "My private note"),
            (8, "first highlight"), (9, ""), (10, "Eq. 4 scaling factor"),
            (11, "margin question"), (12, "deleted highlight"),
        ]
        con.executemany("INSERT INTO itemDataValues (valueID,value) VALUES (?,?)", values)
        data = [
            (10, 1, 1), (10, 2, 2), (10, 3, 3),
            (20, 1, 4), (20, 3, 5),
            (30, 1, 6), (40, 1, 7),
            (12, 1, 8), (13, 2, 11), (14, 1, 10), (15, 1, 12),
        ]
        con.executemany("INSERT INTO itemData (itemID,fieldID,valueID) VALUES (?,?,?)", data)

        con.executemany("INSERT INTO creators (creatorID,firstName,lastName,fieldMode) VALUES (?,?,?,0)",
                        [(1, "Ashish", "Vaswani"), (2, "Noam", "Shazeer"), (3, "Juan", "Zamudio")])
        con.executemany("INSERT INTO itemCreators (itemID,creatorID,creatorTypeID,orderIndex) VALUES (?,?,1,?)",
                        [(10, 1, 0), (10, 2, 1), (20, 3, 0)])

        con.executemany(
            "INSERT INTO itemAttachments (itemID,parentItemID,linkMode,contentType,path) VALUES (?,?,?,?,?)",
            [(11, 10, 0, "application/pdf", "storage:paper.pdf"),
             (21, 20, 0, "application/pdf", "storage:paper2.pdf")])

        annotations = [
            # (itemID, parentItemID, type, color, pageLabel, sortIndex, text, comment)
            (12, 11, 1, "#ffd400", "1", "00000|000100|00010", "first highlight", None),
            (13, 11, 2, "#5fb236", "2", "00001|000100|00010", None, "margin question"),
            (14, 11, 1, "#ff6666", "4", "00003|000200|00010", "Eq. 4 scaling factor", "Why sqrt(d_k)?"),
            (15, 11, 1, "#2ea8e5", "9", "00009|000100|00010", "deleted highlight", None),
        ]
        con.executemany(
            "INSERT INTO itemAnnotations (itemID,parentItemID,type,color,pageLabel,sortIndex,position,isExternal,text,comment) "
            "VALUES (?,?,?,?,?,?,'{}',0,?,?)", annotations)

        con.executemany("INSERT INTO collections (collectionID,collectionName,libraryID,key) VALUES (?,?,1,?)",
                        [(1, "Attention", "COL001"), (2, "Thesis", "COL002"),
                         (3, "Nested", "COL003")])
        con.execute("UPDATE collections SET parentCollectionID=1 WHERE collectionID=3")
        con.executemany("INSERT INTO collectionItems (collectionID,itemID) VALUES (?,?)",
                        [(1, 10), (2, 10), (2, 20), (2, 30), (3, 30)])
        con.executemany("INSERT INTO tags (tagID,name) VALUES (?,?)",
                        [(1, "transformers"), (2, "nlp"), (3, "testing")])
        con.executemany("INSERT INTO itemTags (itemID,tagID,type) VALUES (?,?,0)",
                        [(10, 1), (10, 2), (20, 3), (30, 3)])
        con.execute("INSERT INTO deletedItems (itemID) VALUES (30)")
        con.execute("INSERT INTO deletedItems (itemID) VALUES (15)")
        con.execute("INSERT INTO deletedCollections (collectionID) VALUES (3)")

    def run_cli(self, *args, pretty=False):
        cmd = [sys.executable, str(SCRIPT), "--sqlite-only", "--zotero-dir", str(self.zdir)]
        if pretty:
            cmd.append("--pretty")
        cmd.extend(args)
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return proc.stdout

    def cli_json(self, *args):
        return json.loads(self.run_cli(*args))

    # ------------------------------------------------------------------ #

    def test_wal_snapshot_leaves_source_untouched(self):
        files = [self.zdir / "zotero.sqlite", self.zdir / "zotero.sqlite-wal",
                 self.zdir / "zotero.sqlite-shm"]
        before = {f: (f.stat().st_mtime_ns, f.read_bytes()) for f in files if f.exists()}
        self.assertIn(self.zdir / "zotero.sqlite-wal", before)

        payload = self.cli_json("search", "attention")
        self.assertTrue(any(r["itemKey"] == "PAPER001" for r in payload["results"]))

        after = {f: (f.stat().st_mtime_ns, f.read_bytes()) for f in files if f.exists()}
        self.assertEqual(before, after, "source Zotero DB/WAL/SHM were modified")

        con, tmp = bridge.open_zotero_snapshot(self.zdir)
        try:
            self.assertEqual(con.execute("PRAGMA query_only").fetchone()[0], 0)
            count = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            self.assertEqual(count, 10)
        finally:
            con.close()
            tmp.cleanup()
        self.assertFalse(Path(tmp.name).exists(), "temp snapshot not cleaned up")

    def test_search_collection_filter_and_exclusions(self):
        payload = self.cli_json("search", "attention")
        keys = [r["itemKey"] for r in payload["results"]]
        self.assertEqual(keys, ["PAPER001"])
        self.assertEqual(payload["backend"], "sqlite")
        self.assertEqual(set(payload["results"][0]), {
            "backend", "itemKey", "slug", "title", "authors", "year", "itemType",
            "abstract", "tags", "collections", "attachmentKey", "pdfPath",
            "zoteroSelectUri", "zoteroPdfUri",
        })

        thesis = self.cli_json("search", "", "--collection", "Thesis", "--limit", "50")
        self.assertEqual({r["itemKey"] for r in thesis["results"]}, {"PAPER001", "PAPER002"})

        by_key = self.cli_json("search", "", "--collection", "COL001")
        self.assertEqual([r["itemKey"] for r in by_key["results"]], ["PAPER001"])

        all_items = self.cli_json("search", "", "--limit", "100")
        keys = {r["itemKey"] for r in all_items["results"]}
        self.assertNotIn("DELETED01", keys)
        self.assertNotIn("NOTE001", keys)
        self.assertNotIn("ATTACH01", keys)

    def test_recent_sorted_by_date_added(self):
        payload = self.cli_json("recent", "--limit", "2")
        self.assertEqual([r["itemKey"] for r in payload["results"]], ["PAPER002", "PAPER001"])
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["limit"], 2)

    def test_item_pdf_path_and_zotero_uris(self):
        item = self.cli_json("item", "PAPER001")
        self.assertEqual(item["itemKey"], "PAPER001")
        self.assertEqual(item["authors"], ["Ashish Vaswani", "Noam Shazeer"])
        self.assertEqual(item["year"], "2017")
        self.assertTrue(item["slug"].startswith("vaswani-2017-attention"))
        self.assertEqual(item["attachmentKey"], "ATTACH01")
        self.assertEqual(item["pdfPath"], str(self.zdir / "storage" / "ATTACH01" / "paper.pdf"))
        self.assertEqual(item["zoteroSelectUri"], "zotero://select/library/items/PAPER001")
        self.assertEqual(item["zoteroPdfUri"], "zotero://open-pdf/library/items/ATTACH01")
        self.assertEqual(item["collections"], ["Attention", "Thesis"])
        self.assertEqual(item["tags"], ["nlp", "transformers"])

    def test_annotations_order_types_colors_and_deep_links(self):
        payload = self.cli_json("annotations", "PAPER001")
        anns = payload["annotations"]
        self.assertEqual([a["annotationKey"] for a in anns], ["ANN001", "ANN002", "ANN003"])
        self.assertEqual([a["type"] for a in anns], ["highlight", "note", "highlight"])
        self.assertEqual([a["color"] for a in anns], ["#ffd400", "#5fb236", "#ff6666"])
        self.assertEqual(anns[2]["comment"], "Why sqrt(d_k)?")
        self.assertEqual(anns[2]["pageLabel"], "4")
        self.assertEqual(anns[2]["zoteroPdfUri"],
                         "zotero://open-pdf/library/items/ATTACH01?page=4")
        self.assertEqual(set(anns[0]), {
            "annotationKey", "attachmentKey", "type", "color", "pageLabel",
            "sortIndex", "text", "comment", "zoteroPdfUri",
        })

    def test_collections_counts_and_parent(self):
        payload = self.cli_json("collections")
        cols = {c["key"]: c for c in payload["collections"]}
        self.assertEqual(set(payload["collections"][0]), {"key", "name", "parentKey", "itemCount"})
        self.assertEqual(cols["COL001"]["name"], "Attention")
        self.assertEqual(cols["COL001"]["itemCount"], 1)
        # Deleted paper excluded from the count; deleted collection omitted entirely.
        self.assertEqual(cols["COL002"]["itemCount"], 2)
        self.assertNotIn("COL003", cols)

    def test_bibtex_offline_fallback_and_key_extraction(self):
        payload = self.cli_json("bibtex", "PAPER001")
        self.assertEqual(payload["backend"], "sqlite")
        self.assertEqual(payload["itemKey"], "PAPER001")
        self.assertTrue(payload["bibtex"].startswith("@article{"))
        self.assertIn("{" + payload["bibtexKey"] + ",", payload["bibtex"])
        self.assertIn("Attention Is All You Need", payload["bibtex"])
        self.assertIn("Vaswani", payload["bibtex"])
        self.assertIn("2017", payload["bibtex"])

    def test_api_and_sqlite_payloads_share_exact_shape(self):
        api_item = {
            "key": "PAPER001",
            "data": {
                "key": "PAPER001", "itemType": "conferencePaper",
                "title": "Attention Is All You Need", "date": "2017",
                "abstractNote": "We propose a transformer architecture.",
                "creators": [{"firstName": "Ashish", "lastName": "Vaswani", "creatorType": "author"}],
                "tags": [{"tag": "transformers"}], "collections": ["COL001"],
                "dateAdded": "2026-01-10 10:00:00",
            },
            "meta": {"parsedDate": "2017"},
        }
        api = bridge.APIBackend("http://localhost:23119/api/users/0", self.zdir)
        api._raw = [api_item, {
            "key": "ATTACH01",
            "data": {"itemType": "attachment", "parentItem": "PAPER001",
                     "contentType": "application/pdf", "linkMode": "imported_file",
                     "filename": "paper.pdf"},
        }]
        from_api = bridge.item_payload(api._canonical(api_item), api.name)
        from_sql = self.cli_json("item", "PAPER001")
        self.assertEqual(set(from_api), set(from_sql))
        self.assertEqual(from_api["slug"], from_sql["slug"])
        self.assertEqual(from_api["title"], from_sql["title"])
        self.assertEqual(from_api["pdfPath"], from_sql["pdfPath"])

        api_ann = bridge.annotation_payload("PAPER001", [{
            "annotationKey": "ANN001", "attachmentKey": "ATTACH01",
            "type": "highlight", "color": "#ffd400", "pageLabel": "1",
            "sortIndex": "00000|000100|00010", "text": "first highlight", "comment": "",
        }], api.name)
        sql_ann = self.cli_json("annotations", "PAPER001")
        self.assertEqual(set(api_ann), set(sql_ann))
        self.assertEqual(set(api_ann["annotations"][0]), set(sql_ann["annotations"][0]))

    def test_pretty_prints_human_summary(self):
        out = self.run_cli("recent", "--limit", "1", pretty=True)
        self.assertIn("[sqlite] recent:", out)
        self.assertNotIn('"itemKey"', out)

    def test_global_flags_accepted_after_subcommand(self):
        cmd = [
            sys.executable, str(SCRIPT),
            "item", "PAPER001",
            "--sqlite-only", "--zotero-dir", str(self.zdir), "--pretty",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        self.assertIn("[sqlite] Attention Is All You Need (2017)", proc.stdout)
        self.assertNotIn('"itemKey"', proc.stdout)

        # Flags before subcommand must not be clobbered by subparser defaults.
        args = bridge.build_parser().parse_args(
            ["--pretty", "--sqlite-only", "item", "PAPER001"]
        )
        self.assertTrue(args.pretty)
        self.assertTrue(args.sqlite_only)

    def test_text_subcommand_truncation_and_pretty_output(self):
        args = bridge.build_parser().parse_args(
            ["text", "PAPER001", "--first-page", "1", "--last-page", "2",
             "--max-chars", "10", "--sqlite-only", "--zotero-dir", str(self.zdir)]
        )
        with bridge.SQLiteBackend(self.zdir) as backend, \
             mock.patch.object(bridge, "extract_pdf_text",
                               return_value=("pdftotext", "Attention Is All You Need")) as mocked:
            payload = bridge.run_command(backend, args)
            mocked.assert_called_once_with(
                str(self.zdir / "storage" / "ATTACH01" / "paper.pdf"),
                first_page=1,
                last_page=2,
            )
        self.assertEqual(payload["backend"], "sqlite")
        self.assertEqual(payload["itemKey"], "PAPER001")
        self.assertEqual(payload["attachmentKey"], "ATTACH01")
        self.assertEqual(payload["extractor"], "pdftotext")
        self.assertEqual(payload["text"], "Attention ")
        self.assertEqual(payload["charCount"], 10)
        self.assertTrue(payload["truncated"])


class SlugTestCase(unittest.TestCase):
    def test_standard_author_year_title(self):
        slug = bridge.make_paper_slug([{"lastName": "Vaswani"}], "2017",
                                      "Attention Is All You Need", "ABC123")
        self.assertEqual(slug, "vaswani-2017-attention")
        self.assertLessEqual(len(slug), 50)

    def test_unicode_and_punctuation(self):
        slug = bridge.make_paper_slug(["Müller"], "2024", "Café — Réseaux: Énergie!", "KEY")
        self.assertEqual(slug, "muller-2024-cafe-reseaux-energie")
        self.assertRegex(slug, r"^[a-z0-9-]+$")
        self.assertNotIn(":", slug)
        self.assertNotIn("/", slug)

    def test_missing_author_and_year_falls_back_to_title_and_key(self):
        slug = bridge.make_paper_slug([], None, "Some Weird / Title: Part 2", "AbC123")
        self.assertEqual(slug, "some-weird-title-abc123")
        self.assertRegex(slug, r"^[a-z0-9-]+$")

    def test_missing_everything_and_length_cap(self):
        self.assertEqual(bridge.make_paper_slug([], "", "", "ABC123"), "abc123")
        long_title = " ".join(["very"] * 40) + " end"
        slug = bridge.make_paper_slug(["Author"], "2020", long_title, "K")
        self.assertLessEqual(len(slug), 50)
        self.assertRegex(slug, r"^[a-z0-9-]+$")

    def test_string_author_last_comma_form(self):
        slug = bridge.make_paper_slug(["Zamudio Amaya, Juan"], "2026",
                                      "Feature-Focused Test Generation", "K")
        self.assertEqual(slug, "amaya-2026-feature-focused-test")


if __name__ == "__main__":
    unittest.main()
