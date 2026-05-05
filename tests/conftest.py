import pytest
from lxml import etree

from app.transformers.ampla_to_b2mml import AmplaTransformer


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


@pytest.fixture
def transformer():
    """Provides a v0600 AmplaTransformer instance."""
    return AmplaTransformer(config_path="config/mapping.toml")


@pytest.fixture
def make_model(transformer):
    """Parses XML and returns the transformed model."""

    def _make(xml: str):
        root = etree.fromstring(xml.encode("utf-8"))
        model = transformer.transform(root)
        model["config"] = transformer.config  # required for builder + validators
        return model

    return _make
