"""
Solidity function parser.
Extracts all functions from a Solidity source file using tree-sitter.
Falls back to regex parsing if tree-sitter is not installed.
"""
import re
from dataclasses import dataclass
from typing import List

try:
    import tree_sitter_solidity as tss
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


@dataclass
class SolidityFunction:
    name: str           # ContractName.functionName
    content: str        # full source code of the function
    contract_name: str  # name of the parent contract
    start_line: int
    end_line: int


def parse_functions(source_code: str) -> List[SolidityFunction]:
    """
    Parse a Solidity source string and return all functions.
    Uses tree-sitter when available, falls back to regex.
    """
    if TREE_SITTER_AVAILABLE:
        return _parse_with_tree_sitter(source_code)
    return _parse_with_regex(source_code)


def _parse_with_tree_sitter(source_code: str) -> List[SolidityFunction]:
    SOL_LANGUAGE = Language(tss.language())
    parser = Parser(SOL_LANGUAGE)
    tree = parser.parse(bytes(source_code, "utf-8"))
    lines = source_code.splitlines()
    functions = []

    def walk(node, current_contract=""):
        if node.type == "contract_declaration":
            for child in node.children:
                if child.type == "identifier":
                    current_contract = child.text.decode("utf-8")
        if node.type in ("function_definition", "modifier_definition", "constructor_definition"):
            start = node.start_point[0]
            end = node.end_point[0]
            content = "\n".join(lines[start:end + 1])
            name = current_contract + ".<constructor>"
            for child in node.children:
                if child.type == "identifier":
                    name = current_contract + "." + child.text.decode("utf-8")
                    break
            functions.append(SolidityFunction(
                name=name,
                content=content,
                contract_name=current_contract,
                start_line=start + 1,
                end_line=end + 1,
            ))
        for child in node.children:
            walk(child, current_contract)

    walk(tree.root_node)
    return functions


def _parse_with_regex(source_code: str) -> List[SolidityFunction]:
    """Fallback parser using regex to extract function blocks."""
    functions = []
    lines = source_code.splitlines()

    current_contract = "Unknown"
    contract_pattern = re.compile(r'^\s*contract\s+(\w+)')
    func_pattern = re.compile(
        r'^\s*(function\s+(\w+)|constructor\s*|modifier\s+(\w+))\s*\('
    )

    i = 0
    while i < len(lines):
        cm = contract_pattern.match(lines[i])
        if cm:
            current_contract = cm.group(1)

        fm = func_pattern.match(lines[i])
        if fm:
            func_name = fm.group(2) or fm.group(3) or "constructor"
            start = i
            brace_count = 0
            j = i
            while j < len(lines):
                brace_count += lines[j].count('{') - lines[j].count('}')
                if brace_count <= 0 and j > i:
                    break
                j += 1
            content = "\n".join(lines[start:j + 1])
            functions.append(SolidityFunction(
                name=f"{current_contract}.{func_name}",
                content=content,
                contract_name=current_contract,
                start_line=start + 1,
                end_line=j + 1,
            ))
            i = j + 1
            continue
        i += 1
    return functions
