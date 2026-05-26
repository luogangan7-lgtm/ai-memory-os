"""Code Parser: Parse python, javascript, and typescript source files to extract functions, classes, imports using Tree-sitter with Regex fallbacks."""
from __future__ import annotations
import re
import os
import structlog
from typing import List, Dict, Any

logger = structlog.get_logger()

# Try importing tree_sitter
HAS_TREESITTER = False
try:
    import tree_sitter
    import tree_sitter_language_pack as tslp
    if "python" in tslp.available_languages():
        HAS_TREESITTER = True
except Exception as e:
    logger.warning("Tree-sitter loading failed, falling back to regex parser", error=str(e))

def parse_file(file_path: str, content: str) -> List[Dict[str, Any]]:
    """Parse a code file and extract structure entities (classes, functions, imports)."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".py":
        if HAS_TREESITTER:
            try:
                return parse_python_treesitter(file_path, content)
            except Exception as e:
                logger.error("Tree-sitter parse failed, using regex fallback", file_path=file_path, error=str(e))
                return parse_python_regex(file_path, content)
        else:
            return parse_python_regex(file_path, content)
    elif ext in (".js", ".ts", ".tsx", ".jsx"):
        return parse_js_ts_regex(file_path, content)
    else:
        return []

def parse_python_treesitter(file_path: str, content: str) -> List[Dict[str, Any]]:
    """Parse python code using Tree-sitter."""
    import tree_sitter_language_pack as tslp
    parser = tslp.get_parser("python")
    tree = parser.parse(content)
    
    entities: List[Dict[str, Any]] = []
    
    # We can perform simple traversal of the AST
    def traverse(node, parent_class: str | None = None):
        # Line numbers in tree-sitter are 0-indexed, we want 1-indexed
        start_line = node.start_position().row + 1
        end_line = node.end_position().row + 1
        node_kind = node.kind()
        
        if node_kind == "class_definition":
            # Extract class name node
            name_node = node.child_by_field_name("name")
            class_name = content[name_node.start_byte():name_node.end_byte()] if name_node else "Unknown"
            
            # Find docstring
            doc = ""
            body_node = node.child_by_field_name("body")
            if body_node and body_node.child_count() > 0:
                first_expr = body_node.child(0)
                if first_expr.kind() == "expression_statement" and first_expr.child_count() > 0:
                    val = first_expr.child(0)
                    if val.kind() == "string":
                        doc = content[val.start_byte():val.end_byte()].strip("\"'")
            
            entities.append({
                "entity_type": "class",
                "name": class_name,
                "qualified_name": class_name,
                "signature": f"class {class_name}",
                "description": doc,
                "start_line": start_line,
                "end_line": end_line
            })
            
            # Recurse inside body
            if body_node:
                for i in range(body_node.child_count()):
                    traverse(body_node.child(i), parent_class=class_name)
                    
        elif node_kind == "function_definition":
            name_node = node.child_by_field_name("name")
            func_name = content[name_node.start_byte():name_node.end_byte()] if name_node else "unknown"
            
            # Reconstruct signature from parameters
            params_node = node.child_by_field_name("parameters")
            params = content[params_node.start_byte():params_node.end_byte()] if params_node else "()"
            
            return_type = ""
            return_node = node.child_by_field_name("return_type")
            if return_node:
                return_type = f" -> {content[return_node.start_byte():return_node.end_byte()]}"
                
            sig = f"def {func_name}{params}{return_type}"
            qual_name = f"{parent_class}.{func_name}" if parent_class else func_name
            
            doc = ""
            body_node = node.child_by_field_name("body")
            if body_node and body_node.child_count() > 0:
                first_expr = body_node.child(0)
                if first_expr.kind() == "expression_statement" and first_expr.child_count() > 0:
                    val = first_expr.child(0)
                    if val.kind() == "string":
                        doc = content[val.start_byte():val.end_byte()].strip("\"'")
                        
            entities.append({
                "entity_type": "function",
                "name": func_name,
                "qualified_name": qual_name,
                "signature": sig,
                "description": doc,
                "start_line": start_line,
                "end_line": end_line
            })
            
        elif node_kind in ("import_statement", "import_from_statement"):
            module_name = content[node.start_byte():node.end_byte()].strip()
            entities.append({
                "entity_type": "import",
                "name": module_name,
                "qualified_name": module_name,
                "signature": module_name,
                "description": "",
                "start_line": start_line,
                "end_line": end_line
            })
            
        else:
            for i in range(node.child_count()):
                traverse(node.child(i), parent_class)
                
    traverse(tree.root_node())
    return entities


def parse_python_regex(file_path: str, content: str) -> List[Dict[str, Any]]:
    """Fallback regex parser for Python."""
    lines = content.splitlines()
    entities = []
    
    # Class pattern: class ClassName(...)
    class_pattern = re.compile(r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\b")
    # Function pattern: def func_name(...)
    func_pattern = re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*(->\s*[^:]+)?\s*:")
    # Import pattern
    import_pattern = re.compile(r"^\s*(import\s+.+|from\s+.+\s+import\s+.+)")
    
    current_class = None
    
    for idx, line in enumerate(lines):
        line_num = idx + 1
        
        # 1. Imports
        if import_match := import_pattern.match(line):
            entities.append({
                "entity_type": "import",
                "name": line.strip(),
                "qualified_name": line.strip(),
                "signature": line.strip(),
                "description": "",
                "start_line": line_num,
                "end_line": line_num
            })
            continue
            
        # 2. Classes
        if class_match := class_pattern.match(line):
            class_name = class_match.group(1)
            current_class = class_name
            entities.append({
                "entity_type": "class",
                "name": class_name,
                "qualified_name": class_name,
                "signature": line.strip(),
                "description": "",
                "start_line": line_num,
                "end_line": line_num + 3  # rough estimate
            })
            continue
            
        # 3. Functions
        if func_match := func_pattern.match(line):
            func_name = func_match.group(1)
            qual_name = f"{current_class}.{func_name}" if current_class else func_name
            entities.append({
                "entity_type": "function",
                "name": func_name,
                "qualified_name": qual_name,
                "signature": line.strip(),
                "description": "",
                "start_line": line_num,
                "end_line": line_num + 5  # rough estimate
            })
            
    return entities

def parse_js_ts_regex(file_path: str, content: str) -> List[Dict[str, Any]]:
    """Regex parser for JavaScript & TypeScript."""
    lines = content.splitlines()
    entities = []
    
    class_pattern = re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+([a-zA-Z_][a-zA-Z0-9_]*)")
    func_pattern = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)")
    import_pattern = re.compile(r"^\s*(import\s+.+|const\s+.+=\s*require\(.+)")
    
    current_class = None
    
    for idx, line in enumerate(lines):
        line_num = idx + 1
        
        # 1. Imports
        if import_match := import_pattern.match(line):
            entities.append({
                "entity_type": "import",
                "name": line.strip(),
                "qualified_name": line.strip(),
                "signature": line.strip(),
                "description": "",
                "start_line": line_num,
                "end_line": line_num
            })
            continue
            
        # 2. Classes
        if class_match := class_pattern.match(line):
            class_name = class_match.group(1)
            current_class = class_name
            entities.append({
                "entity_type": "class",
                "name": class_name,
                "qualified_name": class_name,
                "signature": line.strip(),
                "description": "",
                "start_line": line_num,
                "end_line": line_num + 3
            })
            continue
            
        # 3. Functions
        if func_match := func_pattern.match(line):
            func_name = func_match.group(1)
            qual_name = f"{current_class}.{func_name}" if current_class else func_name
            entities.append({
                "entity_type": "function",
                "name": func_name,
                "qualified_name": qual_name,
                "signature": line.strip(),
                "description": "",
                "start_line": line_num,
                "end_line": line_num + 5
            })
            
    return entities
