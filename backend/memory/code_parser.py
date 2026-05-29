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
    
    def traverse(node, parent_class: str | None = None):
        start_line = node.start_position().row + 1
        end_line = node.end_position().row + 1
        node_kind = node.kind()
        
        if node_kind == "class_definition":
            name_node = node.child_by_field_name("name")
            class_name = content[name_node.start_byte():name_node.end_byte()] if name_node else "Unknown"
            
            doc = ""
            body_node = node.child_by_field_name("body")
            if body_node and body_node.child_count() > 0:
                first_expr = body_node.child(0)
                if first_expr.kind() == "expression_statement" and first_expr.child_count() > 0:
                    val = first_expr.child(0)
                    if val.kind() == "string":
                        doc = content[val.start_byte():val.end_byte()].strip("\"'")
            
            # Extract base classes → INHERITS relations
            # tree-sitter Python uses 'argument_list' for base class list
            relations = []
            for i in range(node.child_count()):
                ch = node.child(i)
                if ch.kind() == "argument_list":
                    bases_text = content[ch.start_byte():ch.end_byte()].strip("()")
                    for base in bases_text.split(","):
                        base = base.strip()
                        if base and base != "object":
                            relations.append({"target_name": base, "rel_type": "INHERITS"})
                    break
            
            entities.append({
                "entity_type": "class",
                "name": class_name,
                "qualified_name": class_name,
                "signature": f"class {class_name}",
                "description": doc,
                "start_line": start_line,
                "end_line": end_line,
                "relations": relations,
            })
            
            if body_node:
                for i in range(body_node.child_count()):
                    traverse(body_node.child(i), parent_class=class_name)
                    
        elif node_kind == "function_definition":
            name_node = node.child_by_field_name("name")
            func_name = content[name_node.start_byte():name_node.end_byte()] if name_node else "unknown"
            
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

            # Extract function calls → CALLS relations
            call_re = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
            func_text = content[node.start_byte():node.end_byte()]
            calls_found = set(call_re.findall(func_text))
            _builtins = {"print","len","range","str","int","float","list","dict","set","tuple","bool","type","super","isinstance","hasattr","getattr","setattr","open","zip","map","filter","enumerate","sorted","reversed","any","all","min","max","sum","round","abs","id","repr","format","vars","dir","next","iter","callable","def","class","async","await"}
            relations = [
                {"target_name": c, "rel_type": "CALLS"}
                for c in calls_found
                if c not in _builtins and c != func_name and c != (parent_class or "")
            ]

            entities.append({
                "entity_type": "function",
                "name": func_name,
                "qualified_name": qual_name,
                "signature": sig,
                "description": doc,
                "start_line": start_line,
                "end_line": end_line,
                "relations": relations,
            })
            
        elif node_kind in ("import_statement", "import_from_statement"):
            module_name = content[node.start_byte():node.end_byte()].strip()
            # Extract module target for IMPORTS relation
            target = ""
            if node_kind == "import_from_statement":
                mod_node = node.child_by_field_name("module_name")
                if mod_node:
                    target = content[mod_node.start_byte():mod_node.end_byte()].strip()
            elif node_kind == "import_statement":
                # first name child
                for i in range(node.child_count()):
                    ch = node.child(i)
                    if ch.kind() in ("dotted_name", "aliased_import"):
                        target = content[ch.start_byte():ch.end_byte()].strip().split(" ")[0]
                        break
            relations = [{"target_name": target, "rel_type": "IMPORTS"}] if target else []
            entities.append({
                "entity_type": "import",
                "name": module_name,
                "qualified_name": module_name,
                "signature": module_name,
                "description": "",
                "start_line": start_line,
                "end_line": end_line,
                "relations": relations,
            })
            
        else:
            for i in range(node.child_count()):
                traverse(node.child(i), parent_class)
                
    traverse(tree.root_node())
    return entities



def parse_python_regex(file_path: str, content: str) -> List[Dict[str, Any]]:
    """Fallback regex parser for Python with relationship extraction (CALLS, INHERITS, IMPORTS)."""
    lines = content.splitlines()
    entities = []
    
    class_pattern = re.compile(r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s*\(([^)]+)\))?\s*:")
    func_pattern = re.compile(r"^(\s*)(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*(->\s*[^:]+)?\s*:")
    import_pattern = re.compile(r"^\s*(import\s+(.+)|from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import\s+(.+))")
    
    current_class = None
    _builtins = {"print","len","range","str","int","float","list","dict","set","tuple","bool","type","super","isinstance","hasattr","getattr","setattr","open","zip","map","filter","enumerate","sorted","reversed","any","all","min","max","sum","round","abs","id","repr","format","vars","dir","next","iter","callable","def","class","async","await"}
    
    for idx, line in enumerate(lines):
        line_num = idx + 1
        
        # 1. Imports
        if import_match := import_pattern.match(line):
            module_name = line.strip()
            target = ""
            if import_match.group(3):
                target = import_match.group(3).strip()
            elif import_match.group(2):
                target = import_match.group(2).strip().split(" ")[0].split(",")[0]
            
            relations = [{"target_name": target, "rel_type": "IMPORTS"}] if target else []
            entities.append({
                "entity_type": "import",
                "name": module_name,
                "qualified_name": module_name,
                "signature": module_name,
                "description": "",
                "start_line": line_num,
                "end_line": line_num,
                "relations": relations
            })
            continue
            
        # 2. Classes
        if class_match := class_pattern.match(line):
            class_name = class_match.group(1)
            current_class = class_name
            bases_text = class_match.group(2)
            relations = []
            if bases_text:
                for base in bases_text.split(","):
                    base = base.strip()
                    if base and base != "object":
                        relations.append({"target_name": base, "rel_type": "INHERITS"})
            
            entities.append({
                "entity_type": "class",
                "name": class_name,
                "qualified_name": class_name,
                "signature": line.strip(),
                "description": "",
                "start_line": line_num,
                "end_line": line_num + 3,  # rough estimate
                "relations": relations
            })
            continue
            
        # 3. Functions
        if func_match := func_pattern.match(line):
            indent_str = func_match.group(1)
            func_name = func_match.group(2)
            qual_name = f"{current_class}.{func_name}" if current_class else func_name
            
            func_body_lines = []
            base_indent = len(indent_str)
            for next_idx in range(idx + 1, len(lines)):
                next_line = lines[next_idx]
                if not next_line.strip():
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= base_indent:
                    break
                func_body_lines.append(next_line)
            
            func_text = "\n".join(func_body_lines)
            call_re = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
            calls_found = set(call_re.findall(func_text))
            relations = [
                {"target_name": c, "rel_type": "CALLS"}
                for c in calls_found
                if c not in _builtins and c != func_name and c != (current_class or "")
            ]
            
            entities.append({
                "entity_type": "function",
                "name": func_name,
                "qualified_name": qual_name,
                "signature": line.strip(),
                "description": "",
                "start_line": line_num,
                "end_line": line_num + len(func_body_lines),
                "relations": relations
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
