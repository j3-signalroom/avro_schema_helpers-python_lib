from ccaf_avro_schema_helpers_python_lib.utility import to_snake_case


__copyright__  = "Copyright (c) 2025 Jeffrey Jonathan Jennings"
__credits__    = ["Jeffrey Jonathan Jennings (J3)"]
__maintainer__ = "Jeffrey Jonathan Jennings (J3)"
__email__      = "j3@thej3.com"
__status__     = "dev"
 

class SwapCamelcaseWithSnakecase:
    """This class converts a camelCase record or field name to a snake_case record or field name
    This is useful for converting Avro schema field names to Flink SQL field names.
    """
    def __init__(self, original_schema: dict, topic_name: str, reverse_name_with_alias: bool) :
        """Constructor adds the aliases to the schema.
 
        Arg(s):
            original_schema (dict):  The original schema.
            topic_name (str):        The Kafka topic name that own's the Avro schema.
            reverse_name_with_alias (bool):  True, the name is in snake_case, and the alias is
                                             in camelCase.  Otherwise, it is the reverse.
        """
        self._prefix = (f"{topic_name}_value_").replace(".", "_")
        self._reverse_name_with_alias = reverse_name_with_alias
        self._traverse_schema(original_schema)
 
    def get_updated_schema(self) -> dict:
        """The function gets the updated schema.
 
        Returns:
            dict: The updated schema.
        """
        return self._updated_schema
 
    def _traverse_schema(self, schema: dict) -> None:
        """Recursively traverse the Avro schema, adding snake_case aliases
        to each record and each field.
 
        Arg(s):
            schema (dict): The schema to update.
        """
        schema_type = schema.get("type")
 
        if schema_type == "record":
            self._add_alias_to_record(schema)
 
            # Iterate through all the fields.
            fields = schema.get("fields", [])
            for field in fields:
                self._add_alias_to_field(field)
 
                """
                The field type can be:
                    - simple primitive type (e.g., string, int, float, boolean, etc.)
                    - dict (nested record, enum, fixed, etc.)
                    - list (union of multiple types)
                    - or a complex combination
                """
                field_type = field["type"]
                self._traverse_type(field_type)
        elif schema_type == "array":
            items = schema.get("items")
            self._traverse_type(items)
 
        self._updated_schema = schema
 
    def _add_alias_to_record(self, schema: dict) -> None:
        """If the schema is a record, has a 'name' and _reverse_name_with_alias == False, then add
        an aliases array containing the snake_case version of that name.  Otherwise, if
        reverse_name_with_alias == True, then add an aliases array containing the camel case of
        that name and use a snake case naming style for the name instead.
 
        Arg(s):
            schema (dict): The schema to update.
        """
        # Only do this if 'name' exists in the record definition
        if "name" in schema:
            if not self._reverse_name_with_alias:
                snake_case_name = to_snake_case(schema["name"].removeprefix(self._prefix))
               
                # If 'aliases' already present, just append (or ignore if you want strict one-value aliases).
                if "aliases" in schema:
                    schema["aliases"].append(snake_case_name)
                else:
                    schema["aliases"] = [snake_case_name]
            else:
                original_name = schema["name"].removeprefix(self._prefix)
 
                schema["name"] = to_snake_case(schema["name"].removeprefix(self._prefix))
 
                # If 'aliases' already present, just append (or ignore if you want strict one-value aliases).
                if "aliases" in schema:
                    schema["aliases"].append(original_name)
                else:
                    schema["aliases"] = [original_name]
 
        self._updated_schema = schema
 
    def _add_alias_to_field(self, field: dict) -> None:
        """Add an aliases array if _reverse_name_with_alias == False, to the field containing the snake_case
        version of that field name.  Otherwise, if reverse_name_with_alias == True, then add an aliases array
        containing the camel case of that field name and use a snake case naming style for the field name instead.
 
        Arg(s):
            field (dict): The field to update.
        """
        if not self._reverse_name_with_alias:
            snake_case_name = to_snake_case(field["name"])
            if "aliases" in field:
                field["aliases"].append(snake_case_name)
            else:
                field["aliases"] = [snake_case_name]
        else:
            original_name = field["name"]
 
            field["name"] = to_snake_case(field["name"].removeprefix(self._prefix))
            if "aliases" in field:
                field["aliases"].append(original_name)
            else:
                field["aliases"] = [original_name]
 
    def _traverse_type(self, type_obj) -> None:
        """Helper to handle different Avro `type` variants (e.g. dict, list, string).
 
        Arg(s):
            type_obj: The type object to traverse.
        """
        if isinstance(type_obj, dict):
            # We have a nested schema.
            self._traverse_schema(type_obj)
        elif isinstance(type_obj, list):
            # We have a union; each element can be a simple type or a dict.
            for t in type_obj:
                if isinstance(t, dict):
                    self._traverse_schema(t)
        # If it's a simple primitive, then we do nothing.
 