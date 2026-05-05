from lxml import etree


def parse_ampla_xml(xml_bytes: bytes):
    """
    Parse raw Ampla XML into an lxml ElementTree root.
    - Removes blank text nodes
    - Ensures secure parsing (no external entities)
    - Raises a clean ValueError on invalid XML
    """
    try:
        parser = etree.XMLParser(
            remove_blank_text=True,
            resolve_entities=False,  # security
            no_network=True,  # security
        )
        return etree.fromstring(xml_bytes, parser)
    except Exception as exc:
        raise ValueError("Invalid Ampla XML") from exc
