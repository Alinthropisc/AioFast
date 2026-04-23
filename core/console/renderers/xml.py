from typing import Any
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring

from .base import Renderer


class XmlRenderer(Renderer):
    def render(self, headers: list[str], rows: list[list[Any]], title: str = "") -> str:
        root = Element("data")
        if title:
            root.set("title", title)
        for row in rows:
            item = SubElement(root, "item")
            for h, v in zip(headers, row, strict=False):
                child = SubElement(item, h.lower().replace(" ", "_"))
                child.text = str(v)
        raw = tostring(root, encoding="unicode")
        return parseString(raw).toprettyxml(indent="  ")
