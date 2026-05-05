from lxml import etree

from app.builders.b2mml_builder import build_b2mml_xml
from app.pipeline import run_pipeline_from_file

NS = "http://www.mesa.org/xml/B2MML-V0600"


def _normalise(root):
    # Remove timestamps that vary
    for tag in ["CreationDateTime", "PublishedDate"]:
        for el in root.findall(f".//{{{NS}}}{tag}"):
            el.text = ""

    # Strip whitespace
    for el in root.iter():
        if el.text:
            el.text = el.text.strip()
        if el.tail:
            el.tail = el.tail.strip()

    # Remove comments
    for comment in root.xpath("//comment()"):
        comment.getparent().remove(comment)


def _canonicalise(root):
    from io import BytesIO

    buf = BytesIO()
    root.getroottree().write_c14n(buf)
    return buf.getvalue()


def test_output_matches_xslt_ground_truth():
    # Load model
    model = run_pipeline_from_file("tests/data/sample_ampla.xml")

    # Build v0600 XML
    actual_xml = build_b2mml_xml(model, config=model["config"])
    actual = etree.fromstring(actual_xml.encode())

    # Load expected v0600 XML fixture
    expected = etree.parse("tests/data/sample_b2mml_expected.xml").getroot()

    # Normalize both
    _normalise(actual)
    _normalise(expected)

    # Compare canonical XML
    assert _canonicalise(actual) == _canonicalise(expected)
