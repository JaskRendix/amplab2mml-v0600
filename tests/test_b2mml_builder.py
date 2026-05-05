from lxml import etree

from app.builders.b2mml_builder import build_b2mml_xml

NS = {"b2mml": "http://www.mesa.org/xml/B2MML-V0600"}


def test_b2mml_xml_structure(make_model, minimal_ampla_xml):
    model = make_model(minimal_ampla_xml)
    xml = build_b2mml_xml(model, config=model["config"])

    doc = etree.fromstring(xml.encode())

    # Root element
    assert etree.QName(doc).localname == "ShowEquipmentInformation"

    # ApplicationArea
    app_area = doc.find(".//b2mml:ApplicationArea", namespaces=NS)
    assert app_area is not None

    # DataArea
    data_area = doc.find(".//b2mml:DataArea", namespaces=NS)
    assert data_area is not None

    show = data_area.find("b2mml:Show", namespaces=NS)
    assert show is not None

    eq_info = data_area.find("b2mml:EquipmentInformation", namespaces=NS)
    assert eq_info is not None

    # Equipment
    eq = eq_info.find("b2mml:Equipment", namespaces=NS)
    assert eq is not None

    # v0600: ID is the full_name
    assert eq.find("b2mml:ID", namespaces=NS).text == "Mine"

    # EquipmentClass
    cls = eq_info.find("b2mml:EquipmentClass", namespaces=NS)
    assert cls is not None
    assert cls.find("b2mml:ID", namespaces=NS).text == "Base"
