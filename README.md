# Confluent Cloud for Apache Flink (CCAF) Avro Schema Helpers Python Library

**Table of Contents**

<!-- toc -->
- [**1.0 Overview**](#10-overview)
  * [**1.1 `generate_flink_sql_statements_for_fully_flatten_root_record` module**](#11-generate_flink_sql_statements_for_fully_flatten_root_record-module)
  * [**1.2 `swap_camelcase_with_snakecase` module**](#12-swap_camelcase_with_snakecase-module)
- [**2.0 Resources**](#20-resources)
    * [**2.1 Traversal Method Background**](#21-traversal-method-background)
    * [**2.2 Confluent Cloud for Apache Flink (CCAF) SQL Statements**](#22-confluent-cloud-for-apache-flink-ccaf-sql-statements)
<!-- tocstop -->

## 1.0 Overview

### 1.1 [`generate_flink_sql_statements_for_fully_flatten_root_record` module](./src/ccaf_avro_schema_helpers_python_lib/generate_flink_sql_statements_for_fully_flatten_root_record.py)
This module's class constructs a pair of Flink SQL statements using a _breadth-first traversal method_ from an Avro schema based on the provided outermost JSON object or JSON array column. These Flink SQL statements include the `CREATE TABLE` and `INSERT INTO SELECT FROM` statements. The `CREATE TABLE` statement creates the Sink Table, which subsequently establishes the backing sink Kafka topic. The `INSERT INTO SELECT FROM` statement generates a continuous, unbounded data stream that populates the sink table

![breadth-first traversal](.blog/images/breadth-first-traversal.png)

### 1.2 [`swap_camelcase_with_snakecase` module](./src/ccaf_avro_schema_helpers_python_lib/swap_camelcase_with_snakecase.py)
This module's class uses a _depth-first traversal method_ to traverse an entire Avro schema and converts every `camelCase` record or field name into a `snake_case` record or field name. This is useful for transforming Avro schema field names into Flink SQL style field names.

![depth-first traversal](.blog/images/depth-first-traversal.png)

## 2.0 Resources

### 2.1 Traversal Method Background
- [Breadth First Search Traversal](https://www.w3schools.com/dsa/dsa_algo_graphs_traversal.php#:~:text=Breadth%20First%20Search%20Traversal)
- [Depth First Search Traversal](https://www.w3schools.com/dsa/dsa_algo_graphs_traversal.php#:~:text=Depth%20First%20Search%20Traversal)

### 2.2 Confluent Cloud for Apache Flink (CCAF) SQL Statements
- [CREATE TABLE Statement in Confluent Cloud for Apache Flink](https://docs.confluent.io/cloud/current/flink/reference/statements/create-table.html)
- [SELECT Statement in Confluent Cloud for Apache Flink](https://docs.confluent.io/cloud/current/flink/reference/queries/select.html)
- [WITH Clause in Confluent Cloud for Apache Flink](https://docs.confluent.io/cloud/current/flink/reference/queries/with.html)
- [INSERT INTO FROM SELECT Statement in Confluent Cloud for Apache Flink](https://docs.confluent.io/cloud/current/flink/reference/queries/insert-into-from-select.html)