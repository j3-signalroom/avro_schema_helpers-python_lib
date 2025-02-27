from ccaf_avro_schema_helpers_python_lib.swap_camelcase_with_snakecase import SwapCamelcaseWithSnakecase
from ccaf_avro_schema_helpers_python_lib.utility import to_snake_case


__copyright__  = "Copyright (c) 2025 Jeffrey Jonathan Jennings"
__credits__    = ["Jeffrey Jonathan Jennings (J3)"]
__maintainer__ = "Jeffrey Jonathan Jennings (J3)"
__email__      = "j3@thej3.com"
__status__     = "dev"


def test_record_alias_without_reverse():
    """
    Test that for a simple record (non-reverse mode) the record and each field
    receive an alias that is the snake_case (here, lower-case) version of their names.
    """
    topic_name = "test.topic"  # This will become "test_topic_value_" as prefix.
    schema = {
        "type": "record",
        "name": "test_topic_value_SampleRecord",
        "fields": [
            {"name": "FieldOne", "type": "string"},
            {"name": "FieldTwo", "type": "int"}
        ]
    }
    instance = SwapCamelcaseWithSnakecase(schema, topic_name, reverse_name_with_alias=False)
    updated = instance.get_updated_schema()

    # Check that the record gets an alias (the snake_case of "SampleRecord")
    assert "aliases" in updated, "Record should have an 'aliases' key"
    assert "sample_record" in updated["aliases"]

    # Check each field gets the proper alias (i.e. lower-case version of field name)
    for field in updated["fields"]:
        assert "aliases" in field, "Each field should have an 'aliases' key"
        assert to_snake_case(field["name"]) in field["aliases"]

def test_record_alias_with_reverse():
    """
    Test that when reverse_name_with_alias is True:
      - The record’s name is converted (by removeprefix then snake_case) and its original name (without prefix)
        is placed into the aliases.
      - For each field, the field name is similarly converted and its original name is added as alias.
    """
    topic_name = "test.topic"
    schema = {
        "type": "record",
        "name": "test_topic_value_SampleRecord",
        "fields": [
            {"name": "test_topic_value_FieldOne", "type": "string"},
            {"name": "FieldTwo", "type": "int"}
        ]
    }
    instance = SwapCamelcaseWithSnakecase(schema, topic_name, reverse_name_with_alias=True)
    updated = instance.get_updated_schema()

    # For the record:
    # removeprefix("test_topic_value_SampleRecord") -> "SampleRecord"
    # then to_snake_case -> "samplerecord"
    # And the alias list should include the original ("SampleRecord")
    assert updated["name"] == "sample_record"
    assert "aliases" in updated
    assert "SampleRecord" in updated["aliases"]

    # For the first field:
    # original name "test_topic_value_FieldOne" -> removeprefix -> "FieldOne", then lower-case -> "field_one"
    field1 = updated["fields"][0]
    assert field1["name"] == "field_one"
    assert "aliases" in field1
    assert "test_topic_value_FieldOne" in field1["aliases"]

    # For the second field:
    # "FieldTwo".removeprefix(prefix) returns "FieldTwo", then lower-case -> "field_two"
    field2 = updated["fields"][1]
    assert field2["name"] == "field_two"
    assert "aliases" in field2
    assert "FieldTwo" in field2["aliases"]

def test_nested_union_schema():
    """
    Test that the traversal correctly handles a union type that includes a nested record.
    """
    topic_name = "test.topic"
    schema = {
        "type": "record",
        "name": "test_topic_value_ParentRecord",
        "fields": [
            {
                "name": "child",
                "type": [
                    "null",
                    {
                        "type": "record",
                        "name": "test_topic_value_ChildRecord",
                        "fields": [
                            {"name": "childField", "type": "string"}
                        ]
                    }
                ]
            }
        ]
    }
    instance = SwapCamelcaseWithSnakecase(schema, topic_name, reverse_name_with_alias=False)
    updated = instance.get_updated_schema()

    # Check the parent record alias.
    # removeprefix("test_topic_value_ParentRecord") -> "ParentRecord", then lower-case -> "parent_record"
    assert "aliases" in updated
    assert "parent_record" in updated["aliases"]

    # Check the field "child" alias.
    child_field = updated["fields"][0]
    assert "aliases" in child_field
    assert "child" in child_field["aliases"]

    # Within the union, locate the nested record (ChildRecord)
    union_types = child_field["type"]
    child_record = next(
        (t for t in union_types if isinstance(t, dict) and t.get("type") == "record"),
        None
    )
    assert child_record is not None, "Union should contain a nested record"

    # Check the nested record's alias.
    # removeprefix("test_topic_value_ChildRecord") -> "ChildRecord", then lower-case -> "child_record"
    assert "aliases" in child_record
    assert "child_record" in child_record["aliases"]

    # Check the nested record field alias.
    nested_field = child_record["fields"][0]
    assert "aliases" in nested_field
    assert "child_field" in nested_field["aliases"]

def test_array_schema():
    """
    Test that when the schema is an array, the 'items' (if a record) is processed correctly.
    """
    topic_name = "test.topic"
    schema = {
        "type": "array",
        "items": {
            "type": "record",
            "name": "test_topic_value_ArrayRecord",
            "fields": [
                {"name": "arrayField", "type": "float"}
            ]
        }
    }
    instance = SwapCamelcaseWithSnakecase(schema, topic_name, reverse_name_with_alias=False)
    updated = instance.get_updated_schema()

    # The top-level schema is an array. Its "items" is a record that should be processed.
    items = updated["items"]
    assert items["type"] == "record"

    # Check the record alias:
    # removeprefix("test_topic_value_ArrayRecord") -> "ArrayRecord", then lower-case -> "array_record"
    assert "aliases" in items
    assert "array_record" in items["aliases"]

    # Check the field alias in the record.
    field = items["fields"][0]
    assert "aliases" in field
    assert "array_field" in field["aliases"]

def test_preexisting_aliases():
    """
    Test that if the record or field already has an "aliases" list,
    the new alias is appended rather than replacing the existing one.
    """
    topic_name = "test.topic"
    schema = {
        "type": "record",
        "name": "test_topic_value_SampleRecord",
        "aliases": ["existing_alias"],
        "fields": [
            {"name": "FieldOne", "type": "string", "aliases": ["existing_field_alias"]}
        ]
    }
    instance = SwapCamelcaseWithSnakecase(schema, topic_name, reverse_name_with_alias=False)
    updated = instance.get_updated_schema()

    # For the record, the new alias should be appended.
    # Expected new alias: removeprefix("test_topic_value_SampleRecord") -> "SampleRecord" then lower-case -> "sample_record"
    assert "aliases" in updated
    assert "existing_alias" in updated["aliases"]
    assert "sample_record" in updated["aliases"]

    # For the field, expect the new alias: to_snake_case("FieldOne") -> "field_one"
    field = updated["fields"][0]
    assert "aliases" in field
    assert "existing_field_alias" in field["aliases"]
    assert "field_one" in field["aliases"]
