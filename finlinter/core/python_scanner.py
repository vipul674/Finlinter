"""
Python Scanner Module

AST-based scanner for detecting cost-risk patterns in Python code.
Detects database calls, API calls, and serialization operations inside loops.
"""

import ast
import re
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass


# Import from scanner_dispatch to avoid circular import issues
# We define Finding locally and convert at the boundary
@dataclass
class PythonFinding:
    """Internal finding representation."""
    line_number: int
    line_content: str
    rule_id: str
    rule_name: str
    description: str
    severity: str
    category: str
    suggestion: str


# Patterns that indicate expensive database operations
DB_PATTERNS = {
    # DynamoDB
    ("dynamodb", "get_item"): "DynamoDB get_item",
    ("dynamodb", "query"): "DynamoDB query",
    ("dynamodb", "scan"): "DynamoDB scan",
    ("dynamodb", "put_item"): "DynamoDB put_item",
    ("table", "get_item"): "DynamoDB get_item",
    ("table", "query"): "DynamoDB query",
    ("table", "scan"): "DynamoDB scan",
    
    # SQLAlchemy / Generic ORM
    ("session", "query"): "SQLAlchemy query",
    ("session", "execute"): "SQLAlchemy execute",
    ("session", "get"): "SQLAlchemy get",
    ("db", "get"): "Database get",
    ("db", "query"): "Database query",
    ("db", "execute"): "Database execute",
    ("db", "find"): "Database find",
    ("db", "find_one"): "Database find_one",
    
    # MongoDB / PyMongo
    ("collection", "find"): "MongoDB find",
    ("collection", "find_one"): "MongoDB find_one",
    ("collection", "aggregate"): "MongoDB aggregate",
    
    # Redis
    ("redis", "get"): "Redis get",
    ("redis", "hget"): "Redis hget",
    ("redis", "hgetall"): "Redis hgetall",
    
    # Cursor operations
    ("cursor", "execute"): "SQL cursor execute",
    ("cursor", "fetchone"): "SQL cursor fetchone",
    ("cursor", "fetchall"): "SQL cursor fetchall",
}

# Patterns that indicate expensive API calls
API_PATTERNS = {
    # requests library
    ("requests", "get"): "HTTP GET request",
    ("requests", "post"): "HTTP POST request",
    ("requests", "put"): "HTTP PUT request",
    ("requests", "delete"): "HTTP DELETE request",
    ("requests", "patch"): "HTTP PATCH request",
    
    # httpx
    ("httpx", "get"): "HTTPX GET request",
    ("httpx", "post"): "HTTPX POST request",
    ("client", "get"): "HTTP client GET",
    ("client", "post"): "HTTP client POST",
    
    # aiohttp
    ("session", "get"): "aiohttp GET",
    ("session", "post"): "aiohttp POST",
    
    # urllib
    ("urllib", "urlopen"): "urllib request",
    ("request", "urlopen"): "urllib request",
    
    # boto3 API calls
    ("client", "invoke"): "AWS Lambda invoke",
    ("sns", "publish"): "AWS SNS publish",
    ("sqs", "send_message"): "AWS SQS send",
}

# Patterns for serialization operations
SERIALIZATION_PATTERNS = {
    ("json", "dumps"): "JSON serialization",
    ("json", "loads"): "JSON deserialization",
    ("pickle", "dumps"): "Pickle serialization",
    ("pickle", "loads"): "Pickle deserialization",
    ("yaml", "dump"): "YAML serialization",
    ("yaml", "load"): "YAML deserialization",
}

# Patterns for unbounded queries (queries that might return large result sets)
UNBOUNDED_QUERY_PATTERNS = {
    ("cursor", "execute"): "SQL query",
    ("cursor", "fetchall"): "SQL fetchall",
    ("session", "query"): "ORM query",
    ("session", "execute"): "SQLAlchemy execute",
    ("collection", "find"): "MongoDB find",
    ("db", "query"): "Database query",
    ("db", "execute"): "Database execute",
    ("db", "find"): "Database find",
    ("table", "scan"): "DynamoDB scan",
}

# Keywords that indicate bounded/paginated queries
PAGINATION_KEYWORDS = {
    "limit", "offset", "top", "fetch", "first", "take",
    "page", "paginate", "pagination", "slice", "[:"  # Python slicing
}

# Function names that indicate hot code paths
HOT_PATH_KEYWORDS = {
    "handle", "handler", "process", "controller", "endpoint",
    "route", "view", "api", "webhook", "lambda_handler",
    "main", "run", "execute", "dispatch", "serve"
}


class LoopVisitor(ast.NodeVisitor):
    """
    AST visitor that tracks loop contexts and finds expensive operations.
    """
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.findings: List[PythonFinding] = []
        self.loop_stack: List[ast.AST] = []
        self.in_hot_path = False
        self.current_function: Optional[str] = None
    
    def _get_line_content(self, lineno: int) -> str:
        """Get the source line content (1-indexed)."""
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1]
        return ""
    
    def _is_in_loop(self) -> bool:
        """Check if currently inside a loop."""
        return len(self.loop_stack) > 0
    
    def _add_finding(
        self,
        node: ast.AST,
        rule_id: str,
        rule_name: str,
        description: str,
        category: str,
        severity: str = "medium",
        suggestion: str = ""
    ):
        """Add a finding for the given node."""
        line_content = self._get_line_content(node.lineno)
        
        # Increase severity if in hot path
        if self.in_hot_path and severity == "medium":
            severity = "high"
        
        self.findings.append(PythonFinding(
            line_number=node.lineno,
            line_content=line_content,
            rule_id=rule_id,
            rule_name=rule_name,
            description=description,
            severity=severity,
            category=category,
            suggestion=suggestion,
        ))
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function definitions for hot path detection."""
        old_function = self.current_function
        old_hot_path = self.in_hot_path
        
        self.current_function = node.name
        self.in_hot_path = any(kw in node.name.lower() for kw in HOT_PATH_KEYWORDS)
        
        self.generic_visit(node)
        
        self.current_function = old_function
        self.in_hot_path = old_hot_path
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track async function definitions."""
        self.visit_FunctionDef(node)  # type: ignore
    
    def visit_For(self, node: ast.For):
        """Track for loop context."""
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()
    
    def visit_While(self, node: ast.While):
        """Track while loop context."""
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()
    
    def visit_ListComp(self, node: ast.ListComp):
        """Track list comprehension as loop context."""
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()
    
    def visit_DictComp(self, node: ast.DictComp):
        """Track dict comprehension as loop context."""
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()
    
    def visit_SetComp(self, node: ast.SetComp):
        """Track set comprehension as loop context."""
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()
    
    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        """Track generator expression as loop context."""
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()
    
    def visit_Call(self, node: ast.Call):
        """Check function calls for expensive operations."""
        # Get the call pattern (obj.method or just function)
        pattern = self._extract_call_pattern(node)
        
        # Check for unbounded queries (not loop-dependent)
        if pattern:
            obj_name, method_name = pattern
            self._check_unbounded_query(node, obj_name, method_name)
        
        # Loop-dependent checks
        if not self._is_in_loop():
            self.generic_visit(node)
            return
        
        if pattern:
            obj_name, method_name = pattern
            
            # Check database patterns
            for (obj_pat, method_pat), desc in DB_PATTERNS.items():
                if self._matches_pattern(obj_name, method_name, obj_pat, method_pat):
                    self._add_finding(
                        node,
                        rule_id="PY001",
                        rule_name="Database Call in Loop",
                        description=f"{desc} called inside a loop. Each iteration triggers a database operation.",
                        category="database_read",
                        severity="high",
                        suggestion="Use JOIN or IN query to batch database operations, or use batch APIs like batch_get_item."
                    )
                    break
            
            # Check API patterns
            for (obj_pat, method_pat), desc in API_PATTERNS.items():
                if self._matches_pattern(obj_name, method_name, obj_pat, method_pat):
                    self._add_finding(
                        node,
                        rule_id="PY002",
                        rule_name="API Call in Loop",
                        description=f"{desc} called inside a loop. Each iteration makes an external API call.",
                        category="api_call",
                        severity="high",
                        suggestion="Use a bulk or batch API endpoint to reduce call count."
                    )
                    break
            
            # Check serialization patterns
            for (obj_pat, method_pat), desc in SERIALIZATION_PATTERNS.items():
                if self._matches_pattern(obj_name, method_name, obj_pat, method_pat):
                    self._add_finding(
                        node,
                        rule_id="PY003",
                        rule_name="Serialization in Loop",
                        description=f"{desc} called inside a loop. Repeated serialization is CPU-intensive.",
                        category="serialization",
                        severity="medium",
                        suggestion="Move serialization outside the loop if possible, or serialize a batch at once."
                    )
                    break
        
        self.generic_visit(node)
    
    def _check_unbounded_query(self, node: ast.Call, obj_name: str, method_name: str):
        """Check if a query is unbounded (missing LIMIT/pagination)."""
        for (obj_pat, method_pat), desc in UNBOUNDED_QUERY_PATTERNS.items():
            if self._matches_pattern(obj_name, method_name, obj_pat, method_pat):
                # Check if query contains pagination keywords
                query_str = self._extract_query_string(node)
                if query_str and not self._has_pagination(query_str):
                    self._add_finding(
                        node,
                        rule_id="PY004",
                        rule_name="Unbounded Query",
                        description=f"{desc} without LIMIT or pagination. May return excessive data and incur high costs.",
                        category="database_read",
                        severity="medium",
                        suggestion="Add LIMIT or implement pagination to prevent full table scans."
                    )
                break
    
    def _extract_query_string(self, node: ast.Call) -> Optional[str]:
        """Extract SQL query string from a call if present."""
        # Check first positional argument for string
        if node.args and isinstance(node.args[0], ast.Constant):
            if isinstance(node.args[0].value, str):
                return node.args[0].value.lower()
        # Check for f-string or concatenated string (simplified)
        if node.args and isinstance(node.args[0], ast.JoinedStr):
            # Extract parts of f-string
            parts = []
            for value in node.args[0].values:
                if isinstance(value, ast.Constant):
                    parts.append(str(value.value))
            return "".join(parts).lower()
        return None
    
    def _has_pagination(self, query_str: str) -> bool:
        """Check if query string contains pagination keywords."""
        query_lower = query_str.lower()
        return any(kw in query_lower for kw in PAGINATION_KEYWORDS)
    
    def _extract_call_pattern(self, node: ast.Call) -> Optional[Tuple[str, str]]:
        """Extract the object.method pattern from a call node."""
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            
            # Get the object name
            if isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
            elif isinstance(node.func.value, ast.Attribute):
                obj_name = node.func.value.attr
            elif isinstance(node.func.value, ast.Call):
                # Handle chained calls like db.collection("x").find()
                if isinstance(node.func.value.func, ast.Attribute):
                    obj_name = node.func.value.func.attr
                else:
                    return None
            else:
                return None
            
            return (obj_name.lower(), method_name.lower())
        
        elif isinstance(node.func, ast.Name):
            # Simple function call like json.dumps() after "from json import dumps"
            return ("", node.func.id.lower())
        
        return None
    
    def _matches_pattern(
        self, 
        obj_name: str, 
        method_name: str, 
        obj_pattern: str, 
        method_pattern: str
    ) -> bool:
        """Check if the call matches a pattern."""
        return (
            (obj_pattern in obj_name or obj_name in obj_pattern or obj_pattern == "") and
            (method_pattern in method_name or method_name in method_pattern)
        )


class PythonScanner:
    """
    AST-based scanner for Python code.
    
    Detects:
    - Database operations inside loops (DynamoDB, SQLAlchemy, PyMongo, etc.)
    - HTTP requests inside loops (requests, httpx, aiohttp)
    - JSON/serialization operations inside loops
    """
    
    def __init__(self):
        from ..cost.estimator import CostEstimator, CostCategory
        self.cost_estimator = CostEstimator()
        self.cost_category_map = {
            "database_read": CostCategory.DATABASE_READ,
            "database_write": CostCategory.DATABASE_WRITE,
            "api_call": CostCategory.API_CALL,
            "serialization": CostCategory.SERIALIZATION,
        }
    
    def scan(self, code: str, file_path: str = "<input>") -> List:
        """
        Scan Python code for cost-risk patterns.
        
        Args:
            code: Python source code
            file_path: File path for error reporting
        
        Returns:
            List of Finding objects
        """
        from .scanner_dispatch import Finding
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Return empty findings for syntax errors
            return []
        
        source_lines = code.splitlines()
        visitor = LoopVisitor(source_lines)
        visitor.visit(tree)
        
        # Convert internal findings to scanner_dispatch.Finding
        findings = []
        for pf in visitor.findings:
            # Calculate cost estimate
            cost_category = self.cost_category_map.get(pf.category)
            cost_estimate = None
            if cost_category:
                estimate = self.cost_estimator.estimate(cost_category)
                cost_estimate = estimate.to_dict()
                # Update severity based on cost
                if estimate.severity in ("high", "critical"):
                    pf.severity = estimate.severity
            
            findings.append(Finding(
                file_path=file_path,
                line_number=pf.line_number,
                line_content=pf.line_content,
                rule_id=pf.rule_id,
                rule_name=pf.rule_name,
                description=pf.description,
                severity=pf.severity,
                category=pf.category,
                suggestion=pf.suggestion,
                estimated_cost=cost_estimate,
            ))
        
        return findings
