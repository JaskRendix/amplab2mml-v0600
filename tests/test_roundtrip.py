from lxml import etree

from app.builders.b2mml_builder import build_b2mml_xml
from app.pipeline import run_pipeline_from_file

NS = {"b": "http://www.mesa.org/xml/B2MML-V0600"}


def roundtrip(make_model, xml: str):
    model = make_model(xml)
    xml_out = build_b2mml_xml(model, config=model["config"])
    return etree.fromstring(xml_out.encode()), model


XML = """
<Ampla>
  <Item id="1" name="Mine">
    <Item id="2" name="Plant">
      <ItemClassAssociation classDefinitionId="20"/>
      <Property name="Class.DriveType">Electric</Property>
    </Item>
  </Item>

  <ClassDefinitions>
    <ClassDefinition id="10" name="Base">
      <ClassDefinition id="20" name="Crusher">
        <PropertyDefinition name="DriveType" type="System.String" unitOfMeasure="">Unknown</PropertyDefinition>
        <PropertyDefinition name="Manufacturer" type="System.String" unitOfMeasure="">ACME</PropertyDefinition>
      </ClassDefinition>
    </ClassDefinition>
  </ClassDefinitions>
</Ampla>
"""


def test_roundtrip_equipment_ids(make_model):
    doc, model = roundtrip(make_model, XML)

    ids = [el.text for el in doc.findall(".//b:Equipment/b:ID", NS)]
    model_fullnames = []

    stack = list(model["equipment"])
    while stack:
        eq = stack.pop(0)
        model_fullnames.append(eq.full_name)
        stack = list(eq.children) + stack

    for name in model_fullnames:
        assert name in ids


def test_roundtrip_equipment_levels(make_model):
    doc, _ = roundtrip(make_model, XML)
    levels = [
        el.text for el in doc.findall(".//b:EquipmentLevel/b:EquipmentElementLevel", NS)
    ]
    assert levels == ["Other", "Other"]


def test_roundtrip_class_ids(make_model):
    doc, model = roundtrip(make_model, XML)

    class_ids = [el.text for el in doc.findall(".//b:EquipmentClass/b:ID", NS)]
    model_class_names = [cls.name for cls in model["classes"]]

    for name in model_class_names:
        assert name in class_ids


def test_roundtrip_property_values(make_model):
    doc, _ = roundtrip(make_model, XML)

    plant = next(
        e
        for e in doc.findall(".//b:Equipment", NS)
        if e.findtext("b:ID", namespaces=NS) == "Mine.Plant"
    )

    props = {
        p.findtext("b:ID", namespaces=NS): p.find("b:Value/*", namespaces=NS).text
        for p in plant.findall("b:EquipmentProperty", NS)
    }

    assert props["DriveType"] == "Electric"

    # Manufacturer is no longer inherited
    assert "Manufacturer" not in props


def test_roundtrip_class_parent(make_model):
    doc, _ = roundtrip(make_model, XML)

    # Real class name is Base.Crusher
    crusher = next(
        e
        for e in doc.findall(".//b:EquipmentClass", NS)
        if e.findtext("b:ID", namespaces=NS) == "Crusher"
    )
    assert crusher is not None

    # v0600: no Ampla.Parent property
    parent_prop = crusher.find("b:EquipmentClassProperty[b:ID='Ampla.Parent']", NS)
    assert parent_prop is None


def test_roundtrip_sample_file():
    model = run_pipeline_from_file("tests/data/sample_ampla.xml")
    xml_out = build_b2mml_xml(model, config=model["config"])
    doc = etree.fromstring(xml_out.encode())

    assert etree.QName(doc).localname == "ShowEquipmentInformation"

    assert len(doc.findall(".//b:Equipment", NS)) > 0
    assert len(doc.findall(".//b:EquipmentClass", NS)) > 0
