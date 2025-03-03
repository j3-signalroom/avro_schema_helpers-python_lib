from typing import Tuple, List, Dict
 

__copyright__  = "Copyright (c) 2025 Jeffrey Jonathan Jennings"
__credits__    = ["Jeffrey Jonathan Jennings (J3)"]
__maintainer__ = "Jeffrey Jonathan Jennings (J3)"
__email__      = "j3@thej3.com"
__status__     = "dev"


# Reserved words that cannot be used as column names in SQL statements.
RESERVED_WORDS = ["order", "number", "count", "value", "references", "model", "year"]

ARRAY_WITHIN_INDICATOR = "array-"
TABLE_ALIAS_NAME = "tbl"
 
# Root Column metadata.
ROOT_COLUMN_METADATA = {
    "name": "name",
    "type": "type",
    "is_array": "is_array",
    "primary_key_names": "primary_key_names",
    "primary_key_types": "primary_key_types",
    "alt_name": "alt_name"
}
 
# SELECT clause metadata.
SELECT_METADATA = {
    "name": "name",
    "type": "type",
    "alias": "name_alias",
    "path": "path",
    "nested_indices": "nested_indices",
    "nested_level": "nested_level",
    "nested_family": "nested_family",
    "segments": "segments"
}
 
# FROM clause metadata.
FROM_METADATA = {
    "nested_name": "nested_name",
    "nested_expression": "nested_expression",
    "nested_level": "nested_level",
    "nested_alias": "nested_alias"
}
 
class GenerateFlinkSqlStatementsForFullyFlattenRootRecord:
    """This class constructs a pair of Flink SQL statements from the Avro schema based on
    the provided outermost JSON object or JSON array column. These Flink SQL statements
    include the CREATE TABLE and INSERT INTO SELECT FROM statements. The CREATE TABLE
    statement creates the Sink Table, which subsequently establishes the backing sink
    Kafka topic. The INSERT INTO SELECT FROM statement generates a continuous unbounded
    data stream that populates the sink table.
    """
    def __init__(self, avro_schema: Dict, working_root_column: Dict, root_column_names: List[str], common_root_columns: List[Dict], primary_key: str, source_kafka_topic_subject_schema_name: str, source_table_name: str, sink_table_name: str) -> None:
        """This constructor constructs the pair of sink Flink SQL statements.
 
        Args:
            avro_schema (Dict):                             The Avro schema.
            working_root_column (Dict):                     The working root column metadata.
            root_column_names (List[str]):                  The list of all the root column names.
            common_root_columns (List[Dict]):               The parent columns.
            primary_key (str):                              The primary key.
            source_kafka_topic_subject_schema_name (str):   The source Kafka topic name.
            source_table_name (str):                        The source table name.
            sink_table_name (str):                          The sink table name.
        """
        # Initialize the class variables.
        self.source_kafka_topic_subject_schema_name = source_kafka_topic_subject_schema_name
        self._common_root_columns = common_root_columns        
        self._root_column_name = working_root_column[ROOT_COLUMN_METADATA['name']]
        self._root_column_is_array = working_root_column[ROOT_COLUMN_METADATA['is_array']]
        self._root_primary_key_names = working_root_column[ROOT_COLUMN_METADATA['primary_key_names']]
        self._root_primary_key_types = working_root_column[ROOT_COLUMN_METADATA['primary_key_types']]
        self._track_record_columns = False
        self._column_count = 0
        self.primary_key = primary_key
        self._source_table_name = source_table_name
        self._sink_table_name = sink_table_name
        self._metadata = []
        self._reserved_words = set(self._get_reserved_words())
 
        # Remove the base column from list of non target columns, so the class knows when to stop
        # collecting column metadata.
        root_column_names.remove(self._root_column_name)
        self._non_target_columns = set(root_column_names)
 
        #
        target_schema = self._find_target_schema(self._root_column_name, avro_schema)
        if target_schema == {}:
            return
 
        # Parse schema.
        self._traverse_schema(target_schema, self._root_column_name, self._root_column_is_array)
 
        # Generate the SELECT projection.
        self._generate_select_projection()
   
    def _traverse_schema(self, schema: Dict, record_name: str, within_an_array: bool) -> None:
        """This function moves from a parent element (record or type) down through its subordinate
        elements, performing essentially a tree traversal.  This is called a "Depth-First Traversal
        (or Recursive Descent)", meaning that it goes as deep as possible before backtracking.  This
        is common when using recursion to explore each child node.  With the aim of collecting the
        record names and its associated field names, and if they belong to an array or not.
 
        Arg(s):
            schema (dict):            The schema to update.
            record_name (str):        The record name.
            within_an_array (bool):   A flag indicating if the record is within an array.
        """
        schema_type = schema.get("type")
        if schema_type == "record":
            if "name" in schema:
                prefix = f"{self._root_column_name}_"
                if schema.get("name") == record_name:
                    # Set the flag to track the record columns.
                    self._track_record_columns = True
 
                    record_name = schema["name"].removeprefix(prefix)
 
                    # Check if the record name is a reserved word.
                    record_name = f"`{record_name}`" if record_name in self._reserved_words else record_name
 
                    # Check if the record name is an array.
                    if within_an_array:
                        record_name = f"{ARRAY_WITHIN_INDICATOR}{record_name}"
                elif (schema.get("name") not in self._non_target_columns) and self._track_record_columns:
                    # Check if the record name is an array.
                    if within_an_array:
                        record_name += f".{ARRAY_WITHIN_INDICATOR}{schema['name'].removeprefix(prefix)}"
                    else:
                        record_name += f".{schema['name'].removeprefix(prefix)}"
                elif schema.get("name") in self._non_target_columns:
                    # Stop tracking the record columns.
                    self._track_record_columns = False
 
            # Iterate through all the fields.
            fields = schema.get("fields", [])
            for field in fields:
                if self._track_record_columns:
                    if not self._find_type_record(field['type']):
                        # Check if the record name is a reserved word.
                        if field[SELECT_METADATA['name']] in self._reserved_words:
                            # Escape the record name with backticks when the word is reserverd.
                            field_name = f"`{field[SELECT_METADATA['name']]}`"
                        else:
                            # Leave the record name as is.
                            field_name = field[SELECT_METADATA['name']]
 
                        # Prefix the NESTED name to the column name.
                        column_name = f"{record_name}.{field_name}"
 
                        # Increment the column count.
                        self._column_count += 1
 
                        # Check if the column is within an array.
                        column_segments = column_name.split(".")
                        column_segment_indices = []
                        index = 0
                        for segment in column_segments:
                            if segment.startswith(ARRAY_WITHIN_INDICATOR):
                                column_segment_indices.append(index)
                            index += 1
                       
                        # Remove the ARRAY_WITHIN_INDICATOR from the column name and column segments.
                        column_name = self._remove_repetitive_substring_from_record_names(column_name.replace(ARRAY_WITHIN_INDICATOR, ''))
                        column_segments = column_name.split(".")
 
                        # Set column metadata.
                        self._metadata.append({
                            SELECT_METADATA['name']: column_name,
                            SELECT_METADATA['alias']: column_name.replace('.', '_').replace('`', ''),
                            SELECT_METADATA['type']: field["type"],
                            SELECT_METADATA['nested_indices']: column_segment_indices,
                            SELECT_METADATA['nested_level']: len(column_segment_indices),
                            SELECT_METADATA['path']: column_name[0:column_name.rfind('.')],
                            SELECT_METADATA['segments']: column_segments,
                            SELECT_METADATA['nested_family']: '' if column_segment_indices == [] else column_segments[column_segment_indices[len(column_segment_indices)-1]]
                        })
                """
                The field type can be:
                    - simple primitive type (e.g., string, int, float, boolean, etc.)
                    - dict (nested record, enum, fixed, etc.)
                    - list (union of multiple types)
                    - or a complex combination
                """
                field_type = field["type"]
                self._traverse_type(field_type, record_name, False)
        elif schema_type == "array":
            items = schema.get("items")
            self._traverse_type(items, record_name, True)
 
    def _remove_repetitive_substring_from_record_names(self, column_name) -> str:
        """This function removes a repetitive substring prefixed in the record names of a column name."""
        original_segments = column_name.split('.')
        segments = []
        segments.append(original_segments[0])
        for index in range(1, len(original_segments)):
            prefix = f"{original_segments[index - 1]}_"
            if original_segments[index].startswith(prefix):
                segments.append(original_segments[index].removeprefix(prefix))
            else:
                segments.append(original_segments[index])
 
        return '.'.join(segments)
 
    def _traverse_type(self, type_obj, record_name: str, within_an_array: bool) -> None:
        """This helper function routes fields with an embedded schema to the _traverse_schema()
        function.
 
        Arg(s):
            type_obj:                The type object to traverse.
            record_name (str):       The record name.
            within_an_array (bool):  A flag indicating if the record is within an array.
        """
        if isinstance(type_obj, dict):
            # We have a nested schema.
            self._traverse_schema(type_obj, record_name, within_an_array)
        elif isinstance(type_obj, list):
            # We have a union; check for a nested schema.
            for t in type_obj:
                if isinstance(t, dict):
                    self._traverse_schema(t, record_name, within_an_array)
        # If it's a simple primitive, then we do nothing.
 
    def _set_data_type(self, type_obj) -> str:
        """Sets the CREATE TABLE statement data type.
 
        Args:
            type_obj: The type object.
 
        Returns:
            str: The CREATE TABLE statement data type.
        """
        if isinstance(type_obj, list):
            if isinstance(type_obj[1], dict):
                return f"ARRAY<ROW<`name` ARRAY<{(type_obj[1])['items'].upper() if (type_obj[1])['items'].upper() != 'LONG' else 'BIGINT'}>>>" # In Avro a LONG data type is a BIGINT in Flink.
            else:   # class type is str
                return type_obj[1].upper() if type_obj[1].upper() != 'LONG' else 'BIGINT'
        elif isinstance(type_obj, dict):
            return f"ARRAY<ROW<`name` ARRAY<{type_obj['items'].upper() if type_obj['items'].upper() != 'LONG' else 'BIGINT'}>>>"
        else:
            return type_obj.upper() if type_obj.upper() != 'LONG' else 'BIGINT'
   
    def _generate_select_projection(self) -> Tuple[List, List]:
        """This function performs a "Breadth-First Traversal" of the metadata.  This means that
        the code will visit all nodes at one level before moving to the next level down.  With the
        purpose to generate the SELECT projection and the FROM clause.
 
        Returns:
            Tuple[List, List]: The SELECT projection and the FROM clause as list.
        """
        # Sort the metadata by nesting level.
        self._metadata.sort(key=lambda x: x[SELECT_METADATA['nested_level']])
 
        # Initialize the variables.
        column_index = 0
        cca_count = 0
        cca_parent_count = 0
        cca_child_count = 0
        cte_count = 0
        continuation_from_previous_level = False
        column_array_alias = ""
        current_column_array_name = ""
        nested_child_alias = ""
        base_array_alias = ""
        select_ctes = []
        select_projection = []
        select_from = []
        select_from.append({
            FROM_METADATA["nested_name"]: f"{self._source_table_name}",
            FROM_METADATA["nested_expression"]: f"{self._source_table_name} {TABLE_ALIAS_NAME}",
            FROM_METADATA["nested_level"]: 0,
            FROM_METADATA["nested_alias"]: f"{TABLE_ALIAS_NAME}"
        })
 
        # Iterate through the SELECT clause projection metadata.
        while column_index < self._column_count:
            column = self._metadata[column_index]
            level = column[SELECT_METADATA['nested_level']]
 
            match level:
                case 0:
                    current_nested_family = column[SELECT_METADATA['nested_family']]
                    try:
                        while current_nested_family == self._metadata[column_index].get(SELECT_METADATA['nested_family']) and (column_index < self._column_count):
                            current_column_path = self._metadata[column_index].get(SELECT_METADATA['path'])
                            try:
                                while current_column_path == self._metadata[column_index].get(SELECT_METADATA['path']) and (column_index < self._column_count):
                                    # Get the column metadata.
                                    column = self._metadata[column_index]
 
                                    if self._is_an_array(column):
                                        select_projection.append(f"ARRAY[ROW({column[SELECT_METADATA['name']]})] AS {column[SELECT_METADATA['alias']]}")
                                    else:
                                        select_projection.append(f"{column[SELECT_METADATA['name']]} AS {column[SELECT_METADATA['alias']]}")
 
                                    # Increment the column index.
                                    column_index += 1
                            except IndexError:
                                pass
                    except IndexError:
                        pass
 
                    # Indicate that the traversal is a continuation from the previous level.
                    if column_index < self._column_count:
                        continuation_from_previous_level = True
 
                case 1:
                    level_index = (column[SELECT_METADATA['nested_indices']])[level - 1]
                    cca_count += 1
                    column_array_alias = f"cca_{cca_count}"
                    nested_column = ".".join([column for column in (column[SELECT_METADATA['segments']])[0:level_index + 1]])
                    sanitized_nested_column = ".".join([f"`{column}`" if column in self._reserved_words else column for column in (column[SELECT_METADATA['segments']])[0:level_index + 1]])
 
                    if not continuation_from_previous_level:
                        base_array_alias = column_array_alias
                        from_item = f"CROSS JOIN UNNEST({f'{TABLE_ALIAS_NAME}.`{nested_column}`' if nested_column in self._reserved_words else nested_column}) AS {base_array_alias}"
                        select_from.append({
                                FROM_METADATA["nested_name"]: nested_column,
                                FROM_METADATA["nested_expression"]: from_item,
                                FROM_METADATA["nested_level"]: level,
                                FROM_METADATA["nested_alias"]: base_array_alias
                            })
                       
                        current_nested_family = column[SELECT_METADATA['nested_family']]
                        try:
                            while current_nested_family == self._metadata[column_index].get(SELECT_METADATA['nested_family']) and (column_index < self._column_count):
                                current_column_path = self._metadata[column_index].get(SELECT_METADATA['path'])
                                try:
                                    while current_column_path == self._metadata[column_index].get(SELECT_METADATA['path']) and (column_index < self._column_count):
                                        # Get the column metadata.
                                        column = self._metadata[column_index]
 
                                        # Get the column array column name.
                                        column_array_column_segments = [column_segment for column_segment in column[SELECT_METADATA['segments']][(column[SELECT_METADATA['nested_indices']])[0] + 1:len(column[SELECT_METADATA['segments']])]]
                                        column_array_column_name = ".".join(column_array_column_segments)
 
                                        # Append the column array column name to the CROSS JOIN UNNEST clause.
                                        if self._is_an_array(column):
                                            select_projection.append(f"ARRAY[ROW({base_array_alias}.{column_array_column_name})] AS {column[SELECT_METADATA['alias']]}")
                                        else:
                                            select_projection.append(f"{base_array_alias}.{column_array_column_name} AS {column[SELECT_METADATA['alias']]}")
 
                                        # Increment the column index.
                                        column_index += 1
                                except IndexError:
                                    pass
                        except IndexError:
                            pass
                    else:
                        if current_column_array_name != self._get_current_column_array_name(column):
                            cte_count += 1
                            cte_alias = f"cte_{cte_count}"
                            nested_column_cte = f"{nested_column.replace('.','_').replace('`','')}_cte"
 
                            cte_query_item = f"{nested_column_cte} AS (\n"
                            cte_query_item += "    SELECT\n"
                            cte_query_item += f"        {TABLE_ALIAS_NAME}.{self.primary_key},\n"
                            base_column_name = self._root_column_name if self._root_column_name not in self._reserved_words else f"`{self._root_column_name}`"
                            cte_query_item += ",\n".join([f"        {TABLE_ALIAS_NAME}.{base_column_name}.`{primary_key}` AS {self._root_column_name}_{primary_key}" for primary_key in self._root_primary_key_names])
                            cte_query_item += ",\n"
 
                            # Set the base column expression.
                            base_column_expression = "    AND ".join([f"{TABLE_ALIAS_NAME}.{base_column_name}.`{primary_key}` = cte_{cte_count}.{self._root_column_name}_{primary_key}" for primary_key in self._root_primary_key_names])
                           
                            # Set the LEFT JOIN ON clause.
                            cte_from_item = f"LEFT JOIN\n        {nested_column_cte} AS {cte_alias}\n        ON {TABLE_ALIAS_NAME}.{self.primary_key} = cte_{cte_count}.{self.primary_key} AND {base_column_expression}"
                           
                            select_from.append({
                                FROM_METADATA["nested_name"]: nested_column,
                                FROM_METADATA["nested_expression"]: cte_from_item,
                                FROM_METADATA["nested_level"]: level,
                                FROM_METADATA["nested_alias"]: cte_alias
                            })
 
                        current_nested_family = column[SELECT_METADATA['nested_family']]
                        try:
                            while current_nested_family == self._metadata[column_index].get(SELECT_METADATA['nested_family']) and (column_index < self._column_count):
                                current_column_path = self._metadata[column_index].get(SELECT_METADATA['path'])
                                try:
                                    while current_column_path == self._metadata[column_index].get(SELECT_METADATA['path']) and (column_index < self._column_count):
                                        # Get the column metadata.
                                        column = self._metadata[column_index]
 
                                        # Get the column array column name.
                                        column_array_column_segments = [column_segment for column_segment in column[SELECT_METADATA['segments']][(column[SELECT_METADATA['nested_indices']])[0] + 1:len(column[SELECT_METADATA['segments']])]]
                                        column_array_column_name = ".".join(column_array_column_segments)
 
                                        cte_query_item += f"        {column_array_alias}.{column_array_column_name} AS {column[SELECT_METADATA['alias']]},\n"
 
                                        # Append the column array column name to the CROSS JOIN UNNEST clause.
                                        if self._is_an_array(column):
                                            select_projection.append(f"ARRAY[ROW({cte_alias}.{column[SELECT_METADATA['alias']]})] AS {column[SELECT_METADATA['alias']]}")
                                        else:
                                            select_projection.append(f"{cte_alias}.{column[SELECT_METADATA['alias']]} AS {column[SELECT_METADATA['alias']]}")
 
                                        # Increment the column index.
                                        column_index += 1
                                except IndexError:
                                    pass
                        except IndexError:
                            pass
                       
                        # Close the CTE Query with the FROM clause.
                        cte_query_item = cte_query_item.rstrip(",\n")
                        cte_query_item += "\n    FROM\n"
                        cte_query_item += f"        {self._source_table_name} {TABLE_ALIAS_NAME}\n"
                        cte_query_item += f"        CROSS JOIN UNNEST({TABLE_ALIAS_NAME}.{sanitized_nested_column}) AS {column_array_alias}\n"
                        cte_query_item += ")"
                        select_ctes.append(cte_query_item)
 
                    current_column_array_name = self._get_current_column_array_name(column)
 
                    # Indicate that the traversal is a continuation from the previous level.
                    if column_index < self._column_count:
                        continuation_from_previous_level = True
 
                case _: # Handle nested levels greater than 1.
                    parent_level_index = (column[SELECT_METADATA['nested_indices']])[level - 2]
                    child_level_index = (column[SELECT_METADATA['nested_indices']])[level - 1]
                    nested_parent_column = (column[SELECT_METADATA['segments']])[parent_level_index]
                    nested_child_column = (column[SELECT_METADATA['segments']])[child_level_index]
                    nested_child_column = f"`{nested_child_column}`" if nested_child_column in self._reserved_words else nested_child_column
                    cte_query_item = ""
                    cte_alias = ""
 
                    if not continuation_from_previous_level:
                        # Create the Parent CROSS JOIN UNNEST clause.
                        cca_parent_count += 1
                        nested_parent_alias = f"cca_p_{cca_parent_count}"
                        nested_parent = f"CROSS JOIN UNNEST({nested_parent_column}) AS {nested_parent_alias} ({nested_child_column})"
 
                        # Append the CROSS JOIN UNNEST clause to the FROM clause list.
                        select_from.append({
                            FROM_METADATA["nested_name"]: nested_parent_column,
                            FROM_METADATA["nested_expression"]: nested_parent,
                            FROM_METADATA["nested_level"]: level,
                            FROM_METADATA["nested_alias"]: nested_parent_alias
                        })
 
                        cca_child_count += 1
                        nested_child_alias = f"cca_c_{cca_child_count}"
                        nested_child = f"CROSS JOIN UNNEST({nested_parent_alias}.{nested_child_column}) AS {nested_child_alias}"
                        select_from.append({
                            FROM_METADATA["nested_name"]: nested_child_column,
                            FROM_METADATA["nested_expression"]: nested_child,
                            FROM_METADATA["nested_level"]: level,
                            FROM_METADATA["nested_alias"]: nested_child_alias
                        })
                    else:
                        nested_parent_alias = f"cca_p_{cca_parent_count}"
                        if current_column_array_name != self._get_current_column_array_name(column):
                            cca_count += 1
                            nested_child_alias = f"cca_{cca_count}"
                            cte_count += 1
                            cte_alias = f"cte_{cte_count}"
                            parent_nested_alias = self._get_parent_alias(level - 1, nested_parent_column, select_from)
                            if parent_nested_alias == "":
                                parent_nested_alias = column_array_alias
 
                            base_column_name = self._root_column_name if self._root_column_name not in self._reserved_words else f"`{self._root_column_name}`"
 
                            cte_query_item = f"{nested_child_column.replace('`','')}_cte AS (\n"
                            cte_query_item += "    SELECT\n"
                            cte_query_item += f"        {TABLE_ALIAS_NAME}.{self.primary_key},\n"
                            if base_array_alias == "":
                                if continuation_from_previous_level:
                                    cte_query_item += ",\n".join([f"        {TABLE_ALIAS_NAME}.{base_column_name}.`{primary_key}` AS {self._root_column_name}_{primary_key}" for primary_key in self._root_primary_key_names])
                                else:
                                    cte_query_item += ",\n".join([f"        {parent_nested_alias}.`{primary_key}` AS {self._root_column_name}_{primary_key}" for primary_key in self._root_primary_key_names])
                            else:
                                cte_query_item += ",\n".join([f"        {nested_parent_alias}.`{primary_key}` AS {self._root_column_name}_{primary_key}" for primary_key in self._root_primary_key_names])
                            cte_query_item += ",\n"
 
                            # Get the base column expression.
                            if base_array_alias == "":
                                base_column_expression = "    AND ".join([f"{TABLE_ALIAS_NAME}.{base_column_name}.`{primary_key}` = cte_{cte_count}.{self._root_column_name}_{primary_key}" for primary_key in self._root_primary_key_names])
                            else:
                                base_column_expression = "    AND ".join([f"{base_array_alias}.`{primary_key}` = cte_{cte_count}.{self._root_column_name}_{primary_key}" for primary_key in self._root_primary_key_names])
 
                            # Set the LEFT JOIN ON clause.
                            cte_from_item = f"LEFT JOIN\n        {nested_child_column.replace('`','')}_cte AS {cte_alias}\n        ON {TABLE_ALIAS_NAME}.{self.primary_key} = cte_{cte_count}.{self.primary_key} AND {base_column_expression}"
 
                            select_from.append({
                                FROM_METADATA["nested_name"]: nested_child_column,
                                FROM_METADATA["nested_expression"]: cte_from_item,
                                FROM_METADATA["nested_level"]: level,
                                FROM_METADATA["nested_alias"]: cte_alias
                            })
 
                    # Get the current column path.
                    column_path_name = ".".join(column[SELECT_METADATA['segments']][0:child_level_index + 1])
                    current_column_path = column_path_name
                    try:
                        # Iterate through the columns at the current level.
                        while current_column_path == ".".join(self._metadata[column_index].get(SELECT_METADATA['segments'])[0:child_level_index + 1]) and (column_index < self._column_count):
                            # Get the column metadata.
                            column = self._metadata[column_index]
 
                            # Get the column array column name.
                            column_array_column_segments = [column_segment for column_segment in column[SELECT_METADATA['segments']][child_level_index + 1:len(column[SELECT_METADATA['segments']])]]
                            column_array_column_name = ".".join(column_array_column_segments)
                            if cte_query_item != "":
                                cte_query_item += f"        {nested_child_alias}.{column_array_column_name} AS {column[SELECT_METADATA['alias']]},\n"
 
                                if self._is_an_array(column):
                                    select_projection.append(f"ARRAY[ROW({cte_alias}.{column[SELECT_METADATA['alias']]})] AS {column[SELECT_METADATA['alias']]}")
                                else:
                                    select_projection.append(f"{cte_alias}.{column[SELECT_METADATA['alias']]} AS {column[SELECT_METADATA['alias']]}")
                            else:
                                if self._is_an_array(column):
                                    select_projection.append(f"ARRAY[ROW({nested_child_alias}.{column_array_column_name})] AS {column[SELECT_METADATA['alias']]}")
                                else:
                                    select_projection.append(f"{nested_child_alias}.{column_array_column_name} AS {column[SELECT_METADATA['alias']]}")
 
                            # Increment the column index.
                            column_index += 1
                    except IndexError:
                        pass
                   
                    # Close the CTE Query with the FROM clause.
                    if cte_query_item != "":
                        cte_query_item = cte_query_item.rstrip(",\n")
                        cte_query_item += "\n    FROM\n"
                        cte_query_item += f"        {self._source_table_name} {TABLE_ALIAS_NAME}\n"
                        cte_query_item += f"        CROSS JOIN UNNEST({TABLE_ALIAS_NAME}.{nested_parent_column}) AS {nested_parent_alias}\n"
                        cte_query_item += f"        CROSS JOIN UNNEST({nested_parent_alias}.{nested_child_column}) AS {nested_child_alias}\n"
                        cte_query_item += ")"
                        select_ctes.append(cte_query_item)
 
                    # Reset the current column array name.
                    current_column_array_name = self._get_current_column_array_name(column)
       
        return select_ctes, select_projection, select_from
 
    def _is_an_array(self, select_meta: Dict) -> bool:
        """Checks if the column is an array.
 
        Args:
            select_meta (Dict): The SELECT projection column metadata.
 
        Returns:
            bool: A flag indicating if the column metadata indicates the column
                  is an array of some type.
        """
        type_obj = select_meta[SELECT_METADATA['type']]
        if isinstance(type_obj, list):
            return isinstance(type_obj[1], dict)
        else:
            return isinstance(type_obj, dict)
   
    def _get_current_column_array_name(self, column: Dict) -> str:
        """Gets the current column array name."""
        if column[SELECT_METADATA['nested_level']] == 1:
            return column[SELECT_METADATA['segments']][(column[SELECT_METADATA['nested_indices']])[0]]
        else:
            return ".".join((column[SELECT_METADATA['segments']])[0:len(column[SELECT_METADATA['nested_indices']])])
 
    def _get_parent_alias(self, parent_level: int, parent_level_name: str, select_from: Dict) -> str:
        """Gets the parent alias.
 
        Args:
            parent_level (int):       The parent level.
            parent_level_name (str):  The parent level name.
            select_from (Dict):       The SELECT FROM clause.
 
        Returns:
            str: The parent alias.
        """
        for from_clause in select_from:
            if from_clause[FROM_METADATA['nested_level']] == parent_level and from_clause[FROM_METADATA['nested_name']] == parent_level_name:
                return from_clause[FROM_METADATA['nested_alias']]
        return ""
    

    def _find_target_schema(self, target_name: str, original_schema: Dict) -> Dict:
        schema_type = original_schema.get("type")
    
        if schema_type == "record":
            fields = original_schema.get("fields", [])
            for field in fields:
                if field['name'] == target_name:
                    target_schema = {
                        "type": "record",
                        "name": self.source_kafka_topic_subject_schema_name,
                        "namespace": "org.apache.flink.avro.generated.record",
                        "fields": []
                    }
                    target_schema["fields"].append(field)
                    return target_schema
    
        return {}
    
    def _get_reserved_words(self) -> List[str]:
        """This function returns the reserved words list.
    
        Returns:
            List: The reserved words list.
        """
        return RESERVED_WORDS

    def _find_type_array(self, data):
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
                result = self._find_type_array(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_type_array(item)
                if result:
                    return result
        return None

    def _find_type_record(self, data):
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
                result = self._find_type_record(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_type_record(item)
                if result:
                    return result
        return None

   
    def get_select_statement(self) -> str:
        """Generates the SELECT statement."""
        select_ctes, select_projections, select_froms = self._generate_select_projection()
       
        if len(select_ctes) > 0:
            select_statement = "WITH " + ",\n".join([f"{select_cte}" for select_cte in select_ctes]) + "\n"
        else:
            select_statement = ""
        select_statement += "SELECT\n"
        select_statement += ",\n".join([f"    {TABLE_ALIAS_NAME}.{column[SELECT_METADATA['name']]} AS {column[SELECT_METADATA['name']].replace('`','')}" for column in self._common_root_columns])
        select_statement += ",\n"
        select_statement += ",\n".join([f'    {column}' for column in select_projections])
        select_statement += "\nFROM\n"
        select_statement += "\n".join([f"    {from_clause.get(FROM_METADATA['nested_expression'])}" for from_clause in select_froms])
        select_statement += ";"
 
        return select_statement
   
    def get_select_project_column_count(self) -> int:
        """Return the SELECT projection column count."""
        return self._column_count
   
    def get_insert_statement(self) -> str:
        """Generates the INSERT INTO SELECT FROM statement."""
        insert_statement = f"INSERT INTO {self._sink_table_name}(\n"
        insert_statement += ",\n".join([f"    {column[SELECT_METADATA['name']].replace('`','')}" for column in self._common_root_columns]) + ",\n"
        insert_statement += ",\n".join([f"    {column[SELECT_METADATA['alias']]}" for column in self._metadata]) + ")\n"
        insert_statement += self.get_select_statement()
        return insert_statement
   
    def get_create_table_statement(self) -> str:
        """Generates the CREATE TABLE statement."""
        create_statement = f"CREATE TABLE {self._sink_table_name} (\n"
        create_statement += ",\n".join([f"    `{column[SELECT_METADATA['name']].replace('`', '')}` {self._set_data_type(column[SELECT_METADATA['type']])}" for column in self._common_root_columns]) + ",\n"
        create_statement += ",\n".join([f"    `{column[SELECT_METADATA['alias']].replace('`', '')}` {self._set_data_type(column[SELECT_METADATA['type']])}" for column in self._metadata]) + ",\n"
        create_statement += f"    CONSTRAINT `PRIMARY` PRIMARY KEY (`{self.primary_key}`) NOT ENFORCED\n"
        create_statement += ")\n"
        create_statement += f"DISTRIBUTED BY HASH(`{self.primary_key}`) INTO 1 BUCKETS\n"
        create_statement += "WITH ("
        create_statement += "\n    'changelog.mode' = 'retract',"
        create_statement += "\n    'connector' = 'confluent',"
        create_statement += "\n    'kafka.retention.size' = '0',"
        create_statement += "\n    'kafka.retention.time' = '0',"
        create_statement += "\n    'key.format' = 'avro-registry',"
        create_statement += "\n    'scan.bounded.mode' = 'unbounded',"
        create_statement += "\n    'scan.startup.mode' = 'earliest-offset',"
        create_statement += "\n    'key.format' = 'avro-registry',"
        create_statement += "\n    'value.format' = 'avro-registry',"
        create_statement += "\n    'value.fields-include' = 'ALL'"
        create_statement += "\n);"
        return create_statement
   
 