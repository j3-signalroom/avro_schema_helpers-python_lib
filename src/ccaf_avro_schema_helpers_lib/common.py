import re
import json
from typing import Dict, List
 

__copyright__  = "Copyright (c) 2025 Jeffrey Jonathan Jennings"
__credits__    = ["Jeffrey Jonathan Jennings (J3)"]
__maintainer__ = "Jeffrey Jonathan Jennings (J3)"
__email__      = "j3@thej3.com"
__status__     = "dev"
 

# Reserved words that cannot be used as column names in SQL statements.
RESERVED_WORDS = ["order", "number", "count", "value", "references", "model", "year"]
 

def to_lower_camel_case(name: str) -> str:
    """ Convert a string to lowerCamelCase."""
    words = re.split(r'[\s_-]+|(?<!^)(?=[A-Z])', name)
    if not words:
        return name
   
    # Lowercase the first word; capitalize the rest.
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])
 

def to_snake_case(name: str) -> str:
    """Convert a string (e.g. CamelCase or mixedCase) to snake_case."""
    # Insert an underscore before each capital letter (that isn't at start) and lowercase everything.
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
 
 
def read_avro_schema(file_name: str) -> Dict:
    """This method reads in an Avro schema file and returns the schema.
 
    Arg(s):
        file_name (str):  The name of the Avro schema file.
 
    Returns:
        Dict:  The Avro schema.
    """
    with open(file_name, 'r') as file:
        return json.load(file)
 

def find_type_record(data):
    """This function finds the Avro record type.
   
    Arg(s):
        data: The data to crawl.
 
    Returns:
        The Avro record type.
    """
    if isinstance(data, dict):
        if data.get("type") == "record":
            return data
        for key, value in data.items():
            result = find_type_record(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_type_record(item)
            if result:
                return result
    return None
 

def find_type_array(data):
    """This function finds the Avro array type.
   
    Arg(s):
        data: The data to crawl.
 
    Returns:
        The Avro array type.
    """
    if isinstance(data, dict):
        if data.get("type") == "array":
            return data
        for key, value in data.items():
            result = find_type_array(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_type_array(item)
            if result:
                return result
    return None
 

def get_reserved_words() -> List[str]:
    """This function returns the reserved words list.
   
    Returns:
        List: The reserved words list.
    """
    return RESERVED_WORDS
 

def rename_top_level_schema_record_fields(original_schema: Dict) -> Dict:
    schema_type = original_schema.get("type")
 
    if schema_type == "record":
        fields = original_schema.get("fields", [])
        for field in fields:
            is_simple_primitive = True
            data_types = field['type']
            if isinstance(data_types, dict):
                continue
            else:
                if not isinstance(data_types, str):
                    for data_type in data_types:
                        if isinstance(data_type, dict):
                            is_simple_primitive = False
                            break
                        elif isinstance(data_type, list):
                            # We have a union; check for a nested schema.
                            if isinstance(data_type[1], dict):
                                is_simple_primitive = False
                                break
            if is_simple_primitive:
                field["name"] = to_lower_camel_case(f"load_{field['name']}")
 
    return original_schema
 

def find_target_schema(target_name: str, original_schema: Dict) -> Dict:
    schema_type = original_schema.get("type")
 
    if schema_type == "record":
        fields = original_schema.get("fields", [])
        for field in fields:
            if field['name'] == target_name:
                target_schema = {
                    "type": "record",
                    "name": "dev_mastery_load_raw_avro_value",
                    "namespace": "org.apache.flink.avro.generated.record",
                    "fields": []
                }
                target_schema["fields"].append(field)
                return target_schema
 
    return {}