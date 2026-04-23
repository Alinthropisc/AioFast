import json

from core.console.renderers import (
    CsvRenderer,
    JsonRenderer,
    PlainRenderer,
    RendererManager,
    TableRenderer,
    XmlRenderer,
    YamlRenderer,
)

HEADERS = ["Name", "Age"]
ROWS = [["Alice", "30"], ["Bob", "25"]]


class TestJsonRenderer:
    def test_render(self):
        r = JsonRenderer()
        output = r.render(HEADERS, ROWS)
        data = json.loads(output)
        assert len(data) == 2
        assert data[0]["Name"] == "Alice"
        assert data[1]["Age"] == "25"

    def test_indent(self):
        r = JsonRenderer(indent=4)
        output = r.render(HEADERS, ROWS)
        assert "    " in output


class TestCsvRenderer:
    def test_render(self):
        r = CsvRenderer()
        output = r.render(HEADERS, ROWS)
        lines = output.strip().split("\n")
        assert len(lines) == 3
        assert "Name" in lines[0]
        assert "Alice" in lines[1]


class TestPlainRenderer:
    def test_render(self):
        r = PlainRenderer()
        output = r.render(HEADERS, ROWS)
        lines = output.strip().split("\n")
        assert len(lines) == 3
        assert "Alice" in lines[1]

    def test_custom_separator(self):
        r = PlainRenderer(separator=" | ")
        output = r.render(HEADERS, ROWS)
        assert " | " in output


class TestYamlRenderer:
    def test_render(self):
        r = YamlRenderer()
        output = r.render(HEADERS, ROWS)
        assert "Alice" in output
        assert "Bob" in output


class TestXmlRenderer:
    def test_render(self):
        r = XmlRenderer()
        output = r.render(HEADERS, ROWS, title="Test")
        assert "<data" in output
        assert "<item>" in output
        assert "<name>Alice</name>" in output
        assert 'title="Test"' in output


class TestTableRenderer:
    def test_render(self):
        r = TableRenderer()
        output = r.render(HEADERS, ROWS)
        assert "Alice" in output


class TestRendererManager:
    def test_default_renderers(self):
        m = RendererManager()
        assert m.has("table")
        assert m.has("json")
        assert m.has("csv")
        assert m.has("plain")
        assert m.has("yaml")
        assert m.has("xml")

    def test_available(self):
        m = RendererManager()
        avail = m.available()
        assert "json" in avail
        assert "csv" in avail

    def test_get_unknown_returns_default(self):
        m = RendererManager()
        r = m.get("nonexistent")
        assert isinstance(r, TableRenderer)

    def test_register_custom(self):
        m = RendererManager()
        custom = PlainRenderer(separator=",")
        m.register("custom", custom)
        assert m.has("custom")
        assert m.get("custom") is custom

    def test_render(self):
        m = RendererManager()
        output = m.render("json", HEADERS, ROWS)
        data = json.loads(output)
        assert len(data) == 2

    def test_default_property(self):
        m = RendererManager()
        assert m.default == "table"
        m.default = "json"
        assert m.default == "json"

    def test_set_default_invalid_ignored(self):
        m = RendererManager()
        m.default = "nonexistent"
        assert m.default == "table"
