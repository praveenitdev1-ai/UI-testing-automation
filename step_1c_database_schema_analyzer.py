"""
SQL Schema to JSON Converter
============================

This program converts SQL DDL (Data Definition Language) files into structured JSON schema format.
It parses CREATE TABLE, ALTER TABLE, CREATE INDEX, and other SQL statements to extract:
- Table definitions with columns and their properties
- Primary keys, foreign keys, and indexes
- Data types, constraints, and defaults

The program is designed to be generic and work with various SQL dialects.
"""

import re
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class SQLSchemaParser:
    """
    Parses SQL DDL statements and converts them to structured JSON schema format.
    """
    
    def __init__(self):
        """Initialize the parser with data type mappings and patterns."""
        # Common SQL data type patterns
        self.data_type_patterns = {
            # Numeric types
            r'(?i)serial': 'SERIAL',
            r'(?i)integer|int\b': 'INTEGER',
            r'(?i)decimal\s*\(\s*(\d+)\s*,?\s*(\d*)\s*\)': 'DECIMAL',
            r'(?i)numeric\s*\(\s*(\d+)\s*,?\s*(\d*)\s*\)': 'NUMERIC',
            r'(?i)float|real': 'FLOAT',
            r'(?i)double': 'DOUBLE',
            r'(?i)bigint': 'BIGINT',
            r'(?i)smallint': 'SMALLINT',
            
            # String types
            r'(?i)varchar\s*\(\s*(\d+)\s*\)': 'VARCHAR',
            r'(?i)char\s*\(\s*(\d+)\s*\)': 'CHAR',
            r'(?i)text': 'TEXT',
            r'(?i)clob': 'CLOB',
            
            # Date/Time types
            r'(?i)timestamp': 'TIMESTAMP',
            r'(?i)datetime': 'DATETIME',
            r'(?i)date': 'DATE',
            r'(?i)time': 'TIME',
            
            # Other types
            r'(?i)boolean|bool': 'BOOLEAN',
            r'(?i)uuid': 'UUID',
            r'(?i)jsonb': 'JSONB',
            r'(?i)json': 'JSON',
            r'(?i)blob': 'BLOB',
            r'(?i)binary': 'BINARY'
        }
    
    def clean_sql_content(self, content: str) -> str:
        """Clean SQL content by removing comments and normalizing whitespace."""
        # Remove single-line comments (-- comments)
        content = re.sub(r'--.*?$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments (/* comments */)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        return content.strip()
    
    def parse_data_type(self, data_type_str: str) -> Dict[str, Any]:
        """Parse SQL data type string and extract type, length, scale, etc."""
        data_type_str = data_type_str.strip()
        
        result = {
            "data_type": "VARCHAR",  # Default
            "nullable": True,
            "primary_key": False,
            "auto_increment": False
        }
        
        # Check each pattern
        for pattern, sql_type in self.data_type_patterns.items():
            match = re.search(pattern, data_type_str)
            if match:
                result["data_type"] = sql_type
                
                # Extract length/precision for types that have them
                if sql_type in ['VARCHAR', 'CHAR'] and match.groups():
                    result["length"] = int(match.group(1))
                elif sql_type in ['DECIMAL', 'NUMERIC'] and match.groups():
                    result["length"] = int(match.group(1))
                    if len(match.groups()) > 1 and match.group(2):
                        result["scale"] = int(match.group(2))
                
                # SERIAL types are auto-increment
                if sql_type == 'SERIAL':
                    result["auto_increment"] = True
                
                break
        
        return result
    
    def parse_column_definition(self, column_def: str) -> Dict[str, Any]:
        """Parse a single column definition."""
        column_def = column_def.strip().rstrip(',')
        
        # Split column name and definition
        parts = column_def.split(None, 1)
        if len(parts) < 2:
            return None
        
        column_name = parts[0].strip()
        definition = parts[1].strip()
        
        # Parse data type
        type_match = re.search(r'^(\w+(?:\s*\([^)]+\))?)', definition)
        if not type_match:
            return None
        
        data_type_str = type_match.group(1)
        column_info = self.parse_data_type(data_type_str)
        column_info["name"] = column_name
        
        # Check for constraints
        definition_upper = definition.upper()
        
        # Check for NOT NULL
        if 'NOT NULL' in definition_upper:
            column_info["nullable"] = False
        
        # Check for PRIMARY KEY
        if 'PRIMARY KEY' in definition_upper:
            column_info["primary_key"] = True
            column_info["nullable"] = False
        
        # Check for DEFAULT value
        default_match = re.search(r'DEFAULT\s+([^,\s]+(?:\([^)]*\))?)', definition, re.IGNORECASE)
        if default_match:
            default_value = default_match.group(1).strip()
            # Remove quotes if present
            if default_value.startswith("'") and default_value.endswith("'"):
                default_value = default_value[1:-1]
            column_info["default"] = default_value
        
        return column_info
    
    def split_table_parts(self, content: str) -> List[str]:
        """Split table content by commas, respecting nested parentheses."""
        parts = []
        current_part = ""
        paren_count = 0
        
        for char in content:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                parts.append(current_part.strip())
                current_part = ""
                continue
            
            current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    def parse_create_table(self, sql_statement: str) -> Optional[Dict[str, Any]]:
        """Parse CREATE TABLE statement."""
        # Extract table name
        table_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(', sql_statement, re.IGNORECASE)
        if not table_match:
            return None
        
        table_name = table_match.group(1).lower()
        
        # Extract table content (everything between parentheses)
        # Find the opening parenthesis and match it with the closing one
        start_paren = sql_statement.find('(')
        if start_paren == -1:
            return None
        
        paren_count = 0
        end_paren = -1
        
        for i in range(start_paren, len(sql_statement)):
            if sql_statement[i] == '(':
                paren_count += 1
            elif sql_statement[i] == ')':
                paren_count -= 1
                if paren_count == 0:
                    end_paren = i
                    break
        
        if end_paren == -1:
            return None
        
        table_content = sql_statement[start_paren + 1:end_paren]
        
        # Parse columns and constraints
        columns = []
        primary_keys = []
        foreign_keys = []
        
        # Split by commas, but be careful with nested parentheses
        parts = self.split_table_parts(table_content)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            part_upper = part.upper()
            
            # Check if it's a constraint
            if part_upper.startswith('PRIMARY KEY'):
                # Extract primary key columns
                pk_match = re.search(r'PRIMARY\s+KEY\s*\(\s*([^)]+)\s*\)', part, re.IGNORECASE)
                if pk_match:
                    pk_columns = [col.strip() for col in pk_match.group(1).split(',')]
                    primary_keys.extend(pk_columns)
            
            elif part_upper.startswith('FOREIGN KEY'):
                # Extract foreign key information
                fk_match = re.search(
                    r'FOREIGN\s+KEY\s*\(\s*([^)]+)\s*\)\s+REFERENCES\s+(\w+)\s*\(\s*([^)]+)\s*\)',
                    part, re.IGNORECASE
                )
                if fk_match:
                    fk_columns = [col.strip() for col in fk_match.group(1).split(',')]
                    ref_table = fk_match.group(2)
                    ref_columns = [col.strip() for col in fk_match.group(3).split(',')]
                    
                    foreign_keys.append({
                        "columns": fk_columns,
                        "reference_table": ref_table,
                        "reference_columns": ref_columns
                    })
            
            elif not any(part_upper.startswith(constraint) for constraint in ['PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK']):
                # It's a column definition
                column_info = self.parse_column_definition(part)
                if column_info:
                    columns.append(column_info)
                    
                    # If column is marked as primary key, add to primary_keys list
                    if column_info.get("primary_key"):
                        primary_keys.append(column_info["name"])
        
        return {
            "name": table_name,
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": []  # Will be populated when parsing CREATE INDEX statements
        }
    
    def parse_create_index(self, sql_statement: str) -> Optional[Dict[str, Any]]:
        """Parse CREATE INDEX statement."""
        # Match CREATE INDEX pattern
        index_match = re.search(
            r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(\s*([^)]+)\s*\)',
            sql_statement, re.IGNORECASE
        )
        
        if not index_match:
            return None
        
        index_name = index_match.group(1)
        table_name = index_match.group(2).lower()
        columns_str = index_match.group(3)
        
        # Check if it's a unique index
        is_unique = 'UNIQUE' in sql_statement.upper()
        
        # Parse columns
        columns = [col.strip() for col in columns_str.split(',')]
        
        return {
            "table_name": table_name,
            "index": {
                "name": index_name,
                "columns": columns,
                "unique": is_unique
            }
        }
    
    def parse_alter_table(self, sql_statement: str) -> Optional[Dict[str, Any]]:
        """Parse ALTER TABLE statement (for ADD COLUMN)."""
        # Match ALTER TABLE ADD COLUMN pattern
        alter_match = re.search(
            r'ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(.+?)(?:\s*;|$)',
            sql_statement, re.IGNORECASE | re.DOTALL
        )
        
        if not alter_match:
            return None
        
        table_name = alter_match.group(1).lower()
        column_def = alter_match.group(2).strip()
        
        # Parse the column definition
        column_info = self.parse_column_definition(column_def)
        if not column_info:
            return None
        
        return {
            "table_name": table_name,
            "operation": "ADD_COLUMN",
            "column": column_info
        }
    
    def split_sql_statements(self, content: str) -> List[str]:
        """Split SQL content into individual statements, handling semicolons properly."""
        statements = []
        current_statement = ""
        in_string = False
        string_char = None
        
        i = 0
        while i < len(content):
            char = content[i]
            
            # Handle string literals
            if char in ("'", '"') and not in_string:
                in_string = True
                string_char = char
                current_statement += char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                current_statement += char
            elif char == ';' and not in_string:
                # End of statement
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
            else:
                current_statement += char
            
            i += 1
        
        # Add the last statement if it doesn't end with semicolon
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    def parse_sql_file(self, file_path: str) -> Dict[str, Any]:
        """Parse SQL file and return structured schema."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"SQL file not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading SQL file {file_path}: {str(e)}")
        
        # Clean the content
        content = self.clean_sql_content(content)
        
        # Split into individual statements
        statements = self.split_sql_statements(content)
        
        # Parse statements
        tables = {}
        indexes_by_table = {}
        
        for statement in statements:
            statement = statement.strip()
            if not statement:
                continue
            
            statement_upper = statement.upper()
            
            # Parse CREATE TABLE
            if statement_upper.startswith('CREATE TABLE'):
                table_info = self.parse_create_table(statement)
                if table_info:
                    tables[table_info["name"]] = table_info
            
            # Parse CREATE INDEX
            elif statement_upper.startswith('CREATE') and 'INDEX' in statement_upper:
                index_info = self.parse_create_index(statement)
                if index_info:
                    table_name = index_info["table_name"]
                    if table_name not in indexes_by_table:
                        indexes_by_table[table_name] = []
                    indexes_by_table[table_name].append(index_info["index"])
            
            # Parse ALTER TABLE
            elif statement_upper.startswith('ALTER TABLE'):
                alter_info = self.parse_alter_table(statement)
                if alter_info and alter_info["operation"] == "ADD_COLUMN":
                    table_name = alter_info["table_name"]
                    if table_name in tables:
                        # Add the new column to existing table
                        tables[table_name]["columns"].append(alter_info["column"])
        
        # Add indexes to tables
        for table_name, indexes in indexes_by_table.items():
            if table_name in tables:
                tables[table_name]["indexes"] = indexes
        
        # Create final schema structure
        schema = {
            "schema_version": "1.0",
            "tables": list(tables.values()),
            "total_tables": len(tables),
            "total_indexes": sum(len(table.get("indexes", [])) for table in tables.values())
        }
        
        return schema
    
    def save_schema_json(self, schema: Dict[str, Any], output_file: str):
        """Save schema to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as file:
                json.dump(schema, file, indent=2, ensure_ascii=False)
            print(f" Schema JSON saved to: {output_file}")
        except Exception as e:
            raise Exception(f"Error saving schema file: {str(e)}")


def main():
    """Main function to run the SQL to JSON schema converter."""
    
    # Set up CLI argument parsing
    parser = argparse.ArgumentParser(
        description="Convert SQL DDL file to structured JSON schema format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python step_1c_database_schema_analyzer.py -i Inputs/db_schema.txt -o JSON/database_schema.json
  python step_1c_database_schema_analyzer.py -i Inputs/db_schema.txt -o JSON/schema.json
  python step_1c_database_schema_analyzer.py --input path/to/database.sql --output JSON/db_schema.json
        
Note: -i (input) argument is required when calling from pipeline.
Default output: JSON/database_schema.json
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        help='Path to the input SQL DDL file'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Path for the output JSON schema file (default: JSON/database_schema.json)'
    )
    
    args = parser.parse_args()
    
    # Configuration - use CLI args or defaults
    current_dir = Path(__file__).parent
    inputs_dir = current_dir / "Inputs"
    json_output_dir = current_dir / "JSON"
    
    # Create directories if they don't exist
    inputs_dir.mkdir(exist_ok=True)
    json_output_dir.mkdir(exist_ok=True)
    
    if not args.input:
        print("Error: --input/-i argument is required. No hardcoded input file names allowed.")
        print("Please specify the input file using -i <input_file> or --input <input_file>")
        print("Example: python step_1c_database_schema_analyzer.py -i Inputs/db_schema.txt")
        return 1
        
    input_file = Path(args.input)
    if not input_file.is_absolute():
        input_file = current_dir / input_file
    
    if args.output:
        output_file = Path(args.output)
        if not output_file.is_absolute():
            output_file = current_dir / output_file
    else:
        output_file = json_output_dir / "database_schema.json"
    
    try:
        # Initialize parser
        print(" Initializing SQL Schema Parser...")
        print(f" Input SQL File: {input_file}")
        print(f" Output JSON File: {output_file}")
        
        sql_parser = SQLSchemaParser()
        
        # Check if input file exists
        if not input_file.exists():
            print(f" Error: SQL file not found: {input_file}")
            return 1
        
        # Parse SQL file
        print(" Parsing SQL DDL statements...")
        schema = sql_parser.parse_sql_file(str(input_file))
        
        print(f" Successfully parsed {schema['total_tables']} tables with {schema['total_indexes']} indexes")
        
        # Print summary
        print("\n Schema Summary:")
        for table in schema["tables"]:
            columns_count = len(table["columns"])
            indexes_count = len(table.get("indexes", []))
            fk_count = len(table.get("foreign_keys", []))
            print(f"   {table['name']}: {columns_count} columns, {indexes_count} indexes, {fk_count} foreign keys")
        
        # Save JSON schema
        print(f"\n Saving JSON schema...")
        sql_parser.save_schema_json(schema, str(output_file))
        
        print(f"\n Successfully converted SQL schema to JSON!")
        print(f" Output file: {output_file}")
        
    except Exception as e:
        print(f" Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
