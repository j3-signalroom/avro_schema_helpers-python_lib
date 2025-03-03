import logging
import json
from typing import Dict, List
from ccaf_avro_schema_helpers_python_lib.generate_flink_sql_statements_for_fully_flatten_root_record import GenerateFlinkSqlStatementsForFullyFlattenRootRecord, ROOT_COLUMN_METADATA
 

__copyright__  = "Copyright (c) 2025 Jeffrey Jonathan Jennings"
__credits__    = ["Jeffrey Jonathan Jennings (J3)"]
__maintainer__ = "Jeffrey Jonathan Jennings (J3)"
__email__      = "j3@thej3.com"
__status__     = "dev"


# Configure the logger
logger = logging.getLogger(__name__)
 
def test_generate_all_flink_statement_files():
    avro_schema = _read_avro_schema("tests/data/schema-example-value-v1.avsc")
 
    data = ["load_created_by", "load_created_at", "load_event_type", "load_last_updated_by", "load_last_updated_at", "load_id", "load_number", "kafka_event_time", "kafka_partition", "kafka_offset", "order", "routes", "stops"]
 
    base_objects = _define_root_metadata_columns()
   
    for base_object in base_objects:
        sink = GenerateFlinkSqlStatementsForFullyFlattenRootRecord(avro_schema,
                                                                   base_object,
                                                                   data,
                                                                   [{"name": "load_id", "type": "string"},
                                                                    {"name": "load_created_at", "type": "double"},
                                                                    {"name": "load_event_type", "type": "string"},
                                                                    {"name": "load_last_updated_by", "type": "string"},
                                                                    {"name": "load_last_updated_at", "type": "double"},
                                                                    {"name": "load_created_by", "type": "string"},
                                                                    {"name": "load_number", "type": "string"}],
                                                                    "load_id",
                                                                    "example_value",
                                                                    "catalog.database.`example_table`",
                                                                    f"catalog.database.`example.{base_object[ROOT_COLUMN_METADATA['alt_name']]}`")
 
        statement = sink.get_select_statement()
        _to_file(f"select_{base_object[ROOT_COLUMN_METADATA['alt_name']]}", statement)
        statement = sink.get_insert_statement()
        _to_file(f"insert_{base_object[ROOT_COLUMN_METADATA['alt_name']]}", statement)
        statement = sink.get_create_table_statement()
        _to_file(f"create_{base_object[ROOT_COLUMN_METADATA['alt_name']]}", statement)
 
        logger.info("Generated all Flink SQL statements for %s", base_object[ROOT_COLUMN_METADATA['name']])
        logger.info("Column count: %d", sink.get_select_project_column_count())
        logger.info("")
 

def _to_file(file_name: str, file_content: str) -> None:
    """Writes the SELECT statement to a file."""
    with open(f"tests/statements/{file_name}.fql", "w") as f:
        f.write(file_content)
 

def _define_root_metadata_columns() -> List[Dict]:
    """Define the nested root columns."""
    return [
        {ROOT_COLUMN_METADATA["name"]: "order",
        ROOT_COLUMN_METADATA["type"]: "string",
        ROOT_COLUMN_METADATA["is_array"]: False,
        ROOT_COLUMN_METADATA["primary_key_names"]: ["number"],
        ROOT_COLUMN_METADATA["primary_key_types"]: ["string"],
        ROOT_COLUMN_METADATA["alt_name"]: "order"},
        {ROOT_COLUMN_METADATA["name"]: "routes",
        ROOT_COLUMN_METADATA["type"]: "string",
        ROOT_COLUMN_METADATA["is_array"]: True,
        ROOT_COLUMN_METADATA["primary_key_names"]: ["number"],
        ROOT_COLUMN_METADATA["primary_key_types"]: ["string"],
        ROOT_COLUMN_METADATA["alt_name"]: "order_routes"},
        {ROOT_COLUMN_METADATA["name"]: "stops",
        ROOT_COLUMN_METADATA["type"]: "string",
        ROOT_COLUMN_METADATA["is_array"]: True,
        ROOT_COLUMN_METADATA["primary_key_names"]: ["id"],
        ROOT_COLUMN_METADATA["primary_key_types"]: ["string"],
        ROOT_COLUMN_METADATA["alt_name"]: "order_stops"}]
 

def _read_avro_schema(file_name: str) -> Dict:
    """This method reads in an Avro schema file and returns the schema.
 
    Arg(s):
        file_name (str):  The name of the Avro schema file.
 
    Returns:
        Dict:  The Avro schema.
    """
    with open(file_name, 'r') as file:
        return json.load(file)
 