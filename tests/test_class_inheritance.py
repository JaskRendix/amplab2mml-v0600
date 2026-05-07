def test_class_inheritance_chain(make_model):
    """
    v0600 rule:
    - Top-level ClassDefinition is a container
    - Real classes begin at depth ≥ 2
    - Names are joined with dots
    - Parent is the immediate ancestor class
    """
    xml = """
    <Ampla>
      <ClassDefinitions>
        <ClassDefinition id="1" name="Base">
          <ClassDefinition id="2" name="Child">
            <ClassDefinition id="3" name="Grandchild"/>
          </ClassDefinition>
        </ClassDefinition>
      </ClassDefinitions>
    </Ampla>
    """

    model = make_model(xml)
    classes = {cls.name: cls for cls in model["classes"]}

    # v0600: "Base" is a container → skipped
    assert set(classes) == {"Child", "Child.Grandchild"}

    # inheritance_chain is ordered from root → leaf
    assert [c.name for c in classes["Child"].inheritance_chain] == []
    assert [c.name for c in classes["Child.Grandchild"].inheritance_chain] == ["Child"]


def test_flat_class_is_real_class(make_model):
    """
    v0600 rule:
    - A top-level ClassDefinition with no children IS a real class.
    - It has no parent.
    """
    xml = """
    <Ampla>
      <ClassDefinitions>
        <ClassDefinition id="10" name="Base">
          <PropertyDefinition name="PropA" type="System.String">ValueA</PropertyDefinition>
        </ClassDefinition>
      </ClassDefinitions>
    </Ampla>
    """

    model = make_model(xml)
    classes = {cls.name: cls for cls in model["classes"]}

    assert set(classes) == {"Base"}
    assert classes["Base"].parent is None
    assert classes["Base"].properties[0].name == "PropA"
