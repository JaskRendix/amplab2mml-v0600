def test_end_to_end_transformer(make_model):
    xml = """
    <Ampla>
      <Item id="1" name="Mine" type="Citect.Ampla.Isa95.EnterpriseFolder">
        <ItemClassAssociation classDefinitionId="10"/>
      </Item>

      <ClassDefinitions>
        <ClassDefinition id="10" name="Base">
          <PropertyDefinition name="PropA" type="System.String">ValueA</PropertyDefinition>
        </ClassDefinition>
      </ClassDefinitions>
    </Ampla>
    """

    model = make_model(xml)
    eq = model["equipment"][0]

    assert eq.full_name == "Mine"
    assert eq.class_ids == ["Base"]

    # No inheritance from the class itself anymore
    assert len(eq.properties) == 0


def test_transformer_returns_warnings(make_model):
    xml = """
    <Ampla>
      <Item id="1" name="Mine" type="Citect.Ampla.Isa95.EnterpriseFolder">
        <ItemClassAssociation classDefinitionId="999"/>
      </Item>
    </Ampla>
    """
    model = make_model(xml)
    assert "warnings" in model
    assert isinstance(model["warnings"], list)
    assert model["warnings"]
