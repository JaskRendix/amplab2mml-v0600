import pytest
from lxml import etree

from app.models.properties import EquipmentProperty
from app.pipeline import run_pipeline_from_file
from app.transformers.ampla_to_b2mml import AmplaTransformer


@pytest.fixture
def transformer():
    return AmplaTransformer(config_path="config/mapping.toml")


@pytest.fixture
def make_model():
    def _make(xml: str | None = None):
        if xml is None:
            # default: use sample_ampla.xml through the full pipeline
            model = run_pipeline_from_file("tests/data/sample_ampla.xml")
            return model

        root = etree.fromstring(xml.encode("utf-8"))
        transformer = AmplaTransformer("config/mapping.toml")
        model = transformer.transform(root)
        model["config"] = transformer.config
        return model

    return _make


@pytest.fixture
def make_property():
    def _make_property(
        name="X",
        value=None,
        datatype="string",
        unit_of_measure="",
        raw_unit_of_measure=None,
        normalized_unit_of_measure=None,
        uom_warning=None,
        children=None,
        attributes=None,
    ):
        return EquipmentProperty(
            name=name,
            value=value,
            datatype=datatype,
            unit_of_measure=unit_of_measure,
            raw_unit_of_measure=raw_unit_of_measure,
            normalized_unit_of_measure=normalized_unit_of_measure,
            uom_warning=uom_warning,
            children=children or [],
            attributes=attributes or {},
        )

    return _make_property


@pytest.fixture
def make_asset_mapping():
    """
    Creates a dummy asset mapping object compatible with the builder.
    """

    class DummyMapping:
        equipment_id = "EQ1"
        asset_id = "ASSET1"
        start_time = None
        end_time = None

    return lambda: DummyMapping()


@pytest.fixture
def minimal_ampla_xml():
    return """
    <Ampla>
      <Item id="1" name="Mine">
        <ItemClassAssociation classDefinitionId="10"/>
      </Item>

      <ClassDefinitions>
        <ClassDefinition id="10" name="Base">
          <PropertyDefinition name="PropA" type="System.String" unitOfMeasure="">
            ValueA
          </PropertyDefinition>
        </ClassDefinition>
      </ClassDefinitions>
    </Ampla>
    """
