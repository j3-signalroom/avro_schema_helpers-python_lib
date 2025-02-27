# Confluent Cloud for Apache Flink (CCAF) Avro Schema Helpers Python Library

**Table of Contents**

<!-- toc -->
- [**1.0 Overview**](#10-overview)
<!-- tocstop -->

## 1.0 Overview

### 1.1 `GenerateFlinkSqlStatementsForFullyFlattenRootRecord` class
This class constructs a pair of Flink SQL statements from the Avro schema based on the provided outermost JSON object or JSON array column. These Flink SQL statements include the `CREATE TABLE` and `INSERT INTO SELECT FROM` statements. The `CREATE TABLE` statement creates the Sink Table, which subsequently establishes the backing sink Kafka topic. The `INSERT INTO SELECT FROM` statement generates a continuous, unbounded data stream that populates the sink table

#### 1.2 `SwapCamelcaseWithSnakecase` class
This class converts a camelCase record or field name to a snake_case record or field name. This is useful for converting Avro schema field names to Flink SQL field names.