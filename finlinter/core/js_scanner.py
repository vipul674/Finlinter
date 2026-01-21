"""
JavaScript Scanner Module

Token/regex-based scanner for detecting cost-risk patterns in JavaScript code.
Detects fetch/axios calls, MongoDB operations, and Promise fan-out inside loops.
"""

import re
from typing import List, Optional, Tuple, Set
from dataclasses import dataclass


@dataclass
class JSFinding:
    """Internal finding representation."""
    line_number: int
    line_content: str
    rule_id: str
    rule_name: str
    description: str
    severity: str
    category: str
    suggestion: str


# Regex patterns for loop detection
LOOP_PATTERNS = [
    r'\bfor\s*\(',
    r'\bwhile\s*\(',
    r'\bdo\s*\{',
    r'\.forEach\s*\(',
    r'\.map\s*\(',
    r'\.filter\s*\(',
    r'\.reduce\s*\(',
    r'\.some\s*\(',
    r'\.every\s*\(',
    r'\.find\s*\(',
    r'\.findIndex\s*\(',
    r'\bfor\s+\w+\s+of\b',
    r'\bfor\s+\w+\s+in\b',
]

# API call patterns
API_CALL_PATTERNS = [
    (r'\bfetch\s*\(', "fetch() call"),
    (r'\baxios\s*\.\s*(get|post|put|delete|patch|request)\s*\(', "axios HTTP call"),
    (r'\baxios\s*\(', "axios HTTP call"),
    (r'\bhttp\s*\.\s*(get|post|put|delete|patch)\s*\(', "HTTP library call"),
    (r'\brequest\s*\(', "request() call"),
    (r'\bgot\s*\(', "got() HTTP call"),
    (r'\bsuperagent\s*\.', "superagent HTTP call"),
    (r'\$\.ajax\s*\(', "jQuery AJAX call"),
    (r'\$\.(get|post)\s*\(', "jQuery HTTP call"),
]

# Database patterns
DB_PATTERNS = [
    (r'\.find\s*\(', "MongoDB find()"),
    (r'\.findOne\s*\(', "MongoDB findOne()"),
    (r'\.findById\s*\(', "MongoDB findById()"),
    (r'\.findMany\s*\(', "Database findMany()"),
    (r'\.aggregate\s*\(', "MongoDB aggregate()"),
    (r'\.updateOne\s*\(', "MongoDB updateOne()"),
    (r'\.updateMany\s*\(', "MongoDB updateMany()"),
    (r'\.deleteOne\s*\(', "MongoDB deleteOne()"),
    (r'\.collection\s*\([^)]*\)\s*\.', "MongoDB collection operation"),
    (r'\bquery\s*\(', "Database query()"),
    (r'\.execute\s*\(', "Database execute()"),
    (r'DynamoDB\s*\.\s*(get|put|query|scan)', "DynamoDB operation"),
    (r'dynamodb\s*\.\s*(get|put|query|scan)', "DynamoDB operation"),
    (r'\.getItem\s*\(', "DynamoDB getItem()"),
    (r'\.putItem\s*\(', "DynamoDB putItem()"),
    (r'redis\s*\.\s*(get|set|hget|hset)', "Redis operation"),
]

# Promise/async fan-out patterns
PROMISE_PATTERNS = [
    (r'new\s+Promise\s*\(', "Promise creation"),
    (r'Promise\s*\.\s*all\s*\(', "Promise.all()"),
    (r'Promise\s*\.\s*race\s*\(', "Promise.race()"),
    (r'\basync\s+\(', "async arrow function"),
    (r'\bawait\s+', "await expression"),
]

# Serialization patterns
SERIALIZATION_PATTERNS = [
    (r'JSON\s*\.\s*parse\s*\(', "JSON.parse()"),
    (r'JSON\s*\.\s*stringify\s*\(', "JSON.stringify()"),
]

# Hot path function names
HOT_PATH_PATTERNS = [
    r'(handle|handler|process|controller|endpoint|route|api|webhook|middleware)',
    r'(get|post|put|delete|patch)[A-Z]',
    r'on(Request|Response|Message|Event)',
]


class BlockTracker:
    """
    Tracks brace-delimited blocks to determine loop scope.
    Simple state machine that counts braces.
    """
    
    def __init__(self):
        self.brace_depth = 0
        self.in_loop = False
        self.loop_start_depth = -1
        self.paren_depth = 0
    
    def process_line(self, line: str) -> bool:
        """
        Process a line and return whether we're inside a loop.
        
        Returns:
            True if currently inside a loop body
        """
        # Count braces and parentheses
        for char in line:
            if char == '{':
                self.brace_depth += 1
            elif char == '}':
                self.brace_depth -= 1
                # Check if we've exited the loop
                if self.in_loop and self.brace_depth < self.loop_start_depth:
                    self.in_loop = False
                    self.loop_start_depth = -1
            elif char == '(':
                self.paren_depth += 1
            elif char == ')':
                self.paren_depth -= 1
        
        return self.in_loop
    
    def enter_loop(self):
        """Mark that we're entering a loop."""
        self.in_loop = True
        self.loop_start_depth = self.brace_depth


class JavaScriptScanner:
    """
    Token/regex-based scanner for JavaScript code.
    
    Detects:
    - fetch/axios/HTTP calls inside loops
    - MongoDB/database operations inside loops
    - Promise creation inside loops (async fan-out)
    - JSON.parse/stringify inside loops
    """
    
    def __init__(self):
        from ..cost.estimator import CostEstimator, CostCategory
        self.cost_estimator = CostEstimator()
        self.cost_category_map = {
            "database_read": CostCategory.DATABASE_READ,
            "api_call": CostCategory.API_CALL,
            "serialization": CostCategory.SERIALIZATION,
        }
        
        # Compile regex patterns
        self.loop_regexes = [re.compile(p, re.IGNORECASE) for p in LOOP_PATTERNS]
        self.api_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in API_CALL_PATTERNS]
        self.db_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in DB_PATTERNS]
        self.promise_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in PROMISE_PATTERNS]
        self.serial_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in SERIALIZATION_PATTERNS]
        self.hot_path_regexes = [re.compile(p, re.IGNORECASE) for p in HOT_PATH_PATTERNS]
    
    def _is_loop_start(self, line: str) -> bool:
        """Check if a line starts a loop construct."""
        for regex in self.loop_regexes:
            if regex.search(line):
                return True
        return False
    
    def _is_hot_path(self, lines: List[str], current_line: int) -> bool:
        """Check if we're in a hot code path by looking at surrounding context."""
        # Look back up to 20 lines for function definition
        start = max(0, current_line - 20)
        context = '\n'.join(lines[start:current_line])
        
        for regex in self.hot_path_regexes:
            if regex.search(context):
                return True
        return False
    
    def scan(self, code: str, file_path: str = "<input>") -> List:
        """
        Scan JavaScript code for cost-risk patterns.
        
        Args:
            code: JavaScript source code
            file_path: File path for error reporting
        
        Returns:
            List of Finding objects
        """
        from .scanner_dispatch import Finding
        
        lines = code.splitlines()
        findings: List[JSFinding] = []
        
        # Track loop state using a simple approach
        # We'll look for loop patterns and then scan for issues in the lines that follow
        loop_depth = 0
        brace_stack = []
        in_loop_lines: Set[int] = set()
        
        # First pass: identify which lines are inside loops
        for i, line in enumerate(lines):
            # Count braces
            open_braces = line.count('{')
            close_braces = line.count('}')
            
            # Check if this line starts a loop
            if self._is_loop_start(line):
                loop_depth += 1
                brace_stack.append(loop_depth)
            
            # Mark this line as being in a loop
            if loop_depth > 0:
                in_loop_lines.add(i)
            
            # Update brace tracking
            for _ in range(close_braces):
                if brace_stack and loop_depth > 0:
                    brace_stack.pop()
                    if not brace_stack:
                        loop_depth = 0
                    else:
                        loop_depth = brace_stack[-1] if brace_stack else 0
        
        # Second pass: find issues in loop lines
        for i, line in enumerate(lines):
            line_num = i + 1
            in_loop = i in in_loop_lines
            is_hot_path = self._is_hot_path(lines, i)
            
            if not in_loop:
                continue
            
            # Check API calls
            for regex, desc in self.api_regexes:
                if regex.search(line):
                    severity = "high" if is_hot_path else "high"
                    findings.append(JSFinding(
                        line_number=line_num,
                        line_content=line,
                        rule_id="JS001",
                        rule_name="API Call in Loop",
                        description=f"{desc} detected inside a loop. Each iteration makes a network request.",
                        severity=severity,
                        category="api_call",
                        suggestion="Move the API call outside the loop, or use Promise.all() after collecting all requests."
                    ))
                    break
            
            # Check database calls
            for regex, desc in self.db_regexes:
                if regex.search(line):
                    severity = "high" if is_hot_path else "high"
                    findings.append(JSFinding(
                        line_number=line_num,
                        line_content=line,
                        rule_id="JS002",
                        rule_name="Database Call in Loop",
                        description=f"{desc} detected inside a loop. Each iteration queries the database.",
                        severity=severity,
                        category="database_read",
                        suggestion="Use batch operations or aggregate queries instead of individual calls per iteration."
                    ))
                    break
            
            # Check Promise fan-out (but not await which is often fine)
            for regex, desc in self.promise_regexes:
                if regex.search(line) and "await" not in desc:
                    # Promise creation in loop is concerning
                    if "creation" in desc or "async" in desc.lower():
                        findings.append(JSFinding(
                            line_number=line_num,
                            line_content=line,
                            rule_id="JS003",
                            rule_name="Async Fan-out in Loop",
                            description=f"{desc} inside a loop creates unbounded concurrent operations.",
                            severity="medium",
                            category="api_call",
                            suggestion="Collect promises and use Promise.all() with concurrency limits, or use for...of with await."
                        ))
                        break
            
            # Check serialization
            for regex, desc in self.serial_regexes:
                if regex.search(line):
                    findings.append(JSFinding(
                        line_number=line_num,
                        line_content=line,
                        rule_id="JS004",
                        rule_name="Serialization in Loop",
                        description=f"{desc} inside a loop. Repeated serialization is CPU-intensive.",
                        severity="medium",
                        category="serialization",
                        suggestion="Move serialization outside the loop if possible, or batch serialize."
                    ))
                    break
        
        # Convert to Finding objects with cost estimates
        result = []
        for jf in findings:
            cost_category = self.cost_category_map.get(jf.category)
            cost_estimate = None
            if cost_category:
                estimate = self.cost_estimator.estimate(cost_category)
                cost_estimate = estimate.to_dict()
            
            result.append(Finding(
                file_path=file_path,
                line_number=jf.line_number,
                line_content=jf.line_content,
                rule_id=jf.rule_id,
                rule_name=jf.rule_name,
                description=jf.description,
                severity=jf.severity,
                category=jf.category,
                suggestion=jf.suggestion,
                estimated_cost=cost_estimate,
            ))
        
        return result
