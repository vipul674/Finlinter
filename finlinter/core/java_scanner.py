"""
Java Scanner Module

Regex and pattern-based scanner for detecting cost-risk patterns in Java code.
Detects Spring Data repository calls, RestTemplate, ObjectMapper, and JDBC operations in loops.
"""

import re
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class JavaFinding:
    """Internal finding representation."""
    line_number: int
    line_content: str
    rule_id: str
    rule_name: str
    description: str
    severity: str
    category: str
    suggestion: str


# Loop patterns in Java
LOOP_PATTERNS = [
    r'\bfor\s*\(',
    r'\bwhile\s*\(',
    r'\bdo\s*\{',
    r'\.forEach\s*\(',
    r'\.stream\s*\(\s*\)\s*\.',
    r'\.parallelStream\s*\(\s*\)\s*\.',
]

# Spring Data Repository patterns
SPRING_DATA_PATTERNS = [
    (r'repository\s*\.\s*find', "Spring Data Repository find"),
    (r'repository\s*\.\s*findById', "Spring Data findById()"),
    (r'repository\s*\.\s*findAll', "Spring Data findAll()"),
    (r'repository\s*\.\s*findBy\w+', "Spring Data findBy*()"),
    (r'repository\s*\.\s*get', "Spring Data Repository get"),
    (r'repository\s*\.\s*save', "Spring Data Repository save"),
    (r'repository\s*\.\s*delete', "Spring Data Repository delete"),
    (r'Repo\s*\.\s*find', "Repository find"),
    (r'Dao\s*\.\s*find', "DAO find"),
    (r'Dao\s*\.\s*get', "DAO get"),
    (r'entityManager\s*\.\s*find', "JPA EntityManager find"),
    (r'entityManager\s*\.\s*createQuery', "JPA EntityManager createQuery"),
    (r'session\s*\.\s*get', "Hibernate Session get"),
    (r'session\s*\.\s*load', "Hibernate Session load"),
    (r'session\s*\.\s*createQuery', "Hibernate Session createQuery"),
]

# RestTemplate patterns
REST_TEMPLATE_PATTERNS = [
    (r'restTemplate\s*\.\s*getForObject', "RestTemplate getForObject()"),
    (r'restTemplate\s*\.\s*getForEntity', "RestTemplate getForEntity()"),
    (r'restTemplate\s*\.\s*postForObject', "RestTemplate postForObject()"),
    (r'restTemplate\s*\.\s*postForEntity', "RestTemplate postForEntity()"),
    (r'restTemplate\s*\.\s*exchange', "RestTemplate exchange()"),
    (r'restTemplate\s*\.\s*execute', "RestTemplate execute()"),
    (r'restTemplate\s*\.\s*delete', "RestTemplate delete()"),
    (r'restTemplate\s*\.\s*put', "RestTemplate put()"),
    (r'webClient\s*\.\s*get', "WebClient GET"),
    (r'webClient\s*\.\s*post', "WebClient POST"),
    (r'httpClient\s*\.\s*execute', "HttpClient execute"),
    (r'HttpURLConnection', "HttpURLConnection"),
    (r'\.openConnection\s*\(', "URL openConnection()"),
]

# ObjectMapper patterns
OBJECT_MAPPER_PATTERNS = [
    (r'objectMapper\s*\.\s*writeValueAsString', "ObjectMapper writeValueAsString()"),
    (r'objectMapper\s*\.\s*writeValueAsBytes', "ObjectMapper writeValueAsBytes()"),
    (r'objectMapper\s*\.\s*readValue', "ObjectMapper readValue()"),
    (r'objectMapper\s*\.\s*readTree', "ObjectMapper readTree()"),
    (r'mapper\s*\.\s*writeValueAsString', "ObjectMapper writeValueAsString()"),
    (r'mapper\s*\.\s*readValue', "ObjectMapper readValue()"),
    (r'gson\s*\.\s*toJson', "Gson toJson()"),
    (r'gson\s*\.\s*fromJson', "Gson fromJson()"),
    (r'Gson\s*\(\s*\)\s*\.\s*toJson', "Gson toJson()"),
]

# JDBC patterns
JDBC_PATTERNS = [
    (r'jdbcTemplate\s*\.\s*query', "JdbcTemplate query()"),
    (r'jdbcTemplate\s*\.\s*queryForObject', "JdbcTemplate queryForObject()"),
    (r'jdbcTemplate\s*\.\s*queryForList', "JdbcTemplate queryForList()"),
    (r'jdbcTemplate\s*\.\s*update', "JdbcTemplate update()"),
    (r'jdbcTemplate\s*\.\s*execute', "JdbcTemplate execute()"),
    (r'statement\s*\.\s*executeQuery', "Statement executeQuery()"),
    (r'statement\s*\.\s*execute', "Statement execute()"),
    (r'preparedStatement\s*\.\s*executeQuery', "PreparedStatement executeQuery()"),
    (r'preparedStatement\s*\.\s*execute', "PreparedStatement execute()"),
    (r'connection\s*\.\s*prepareStatement', "Connection prepareStatement()"),
    (r'resultSet\s*\.\s*next', "ResultSet iteration"),
]

# AWS SDK patterns
AWS_PATTERNS = [
    (r'dynamoDb\s*\.\s*getItem', "DynamoDB getItem()"),
    (r'dynamoDb\s*\.\s*putItem', "DynamoDB putItem()"),
    (r'dynamoDb\s*\.\s*query', "DynamoDB query()"),
    (r'dynamoDb\s*\.\s*scan', "DynamoDB scan()"),
    (r's3Client\s*\.\s*getObject', "S3 getObject()"),
    (r's3Client\s*\.\s*putObject', "S3 putObject()"),
    (r'snsClient\s*\.\s*publish', "SNS publish()"),
    (r'sqsClient\s*\.\s*sendMessage', "SQS sendMessage()"),
    (r'lambdaClient\s*\.\s*invoke', "Lambda invoke()"),
]

# Hot path indicators
HOT_PATH_PATTERNS = [
    r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)',
    r'@(Controller|RestController|Service|Component)',
    r'(handle|process|execute|run|invoke|dispatch)\w*\s*\(',
    r'public\s+\w+\s+(handle|process|execute|controller|endpoint)',
    r'@Scheduled',
    r'@EventListener',
    r'@KafkaListener',
    r'@RabbitListener',
]


class JavaScanner:
    """
    Regex and pattern-based scanner for Java code.
    
    Detects:
    - Spring Data repository calls inside loops
    - RestTemplate/WebClient calls inside loops
    - ObjectMapper serialization inside loops
    - JDBC/JdbcTemplate operations inside loops
    - AWS SDK operations inside loops
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
        self.spring_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in SPRING_DATA_PATTERNS]
        self.rest_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in REST_TEMPLATE_PATTERNS]
        self.mapper_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in OBJECT_MAPPER_PATTERNS]
        self.jdbc_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in JDBC_PATTERNS]
        self.aws_regexes = [(re.compile(p, re.IGNORECASE), desc) for p, desc in AWS_PATTERNS]
        self.hot_path_regexes = [re.compile(p, re.IGNORECASE) for p in HOT_PATH_PATTERNS]
    
    def _is_loop_start(self, line: str) -> bool:
        """Check if a line starts a loop construct."""
        for regex in self.loop_regexes:
            if regex.search(line):
                return True
        return False
    
    def _is_hot_path(self, lines: List[str], current_line: int) -> bool:
        """Check if we're in a hot code path."""
        # Look back up to 30 lines for annotations and method signatures
        start = max(0, current_line - 30)
        context = '\n'.join(lines[start:current_line])
        
        for regex in self.hot_path_regexes:
            if regex.search(context):
                return True
        return False
    
    def _find_loops(self, lines: List[str]) -> Set[int]:
        """
        Find all line numbers that are inside loops.
        Uses brace counting to track loop scope.
        """
        in_loop_lines: Set[int] = set()
        loop_depth = 0
        brace_depth = 0
        loop_start_depths: List[int] = []
        
        for i, line in enumerate(lines):
            # Check if this line starts a loop
            if self._is_loop_start(line):
                loop_depth += 1
                # Record the brace depth when entering the loop
                loop_start_depths.append(brace_depth)
            
            # Count braces
            for char in line:
                if char == '{':
                    brace_depth += 1
                    # If we just entered a loop, this is the loop's opening brace
                elif char == '}':
                    brace_depth -= 1
                    # Check if we've exited a loop
                    while loop_start_depths and brace_depth < loop_start_depths[-1]:
                        loop_start_depths.pop()
                        loop_depth = max(0, loop_depth - 1)
            
            # Mark this line as being in a loop
            if loop_depth > 0:
                in_loop_lines.add(i)
        
        return in_loop_lines
    
    def scan(self, code: str, file_path: str = "<input>") -> List:
        """
        Scan Java code for cost-risk patterns.
        
        Args:
            code: Java source code
            file_path: File path for error reporting
        
        Returns:
            List of Finding objects
        """
        from .scanner_dispatch import Finding
        
        lines = code.splitlines()
        findings: List[JavaFinding] = []
        
        # Find all lines inside loops
        in_loop_lines = self._find_loops(lines)
        
        # Scan each line for patterns
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Skip if not in a loop
            if i not in in_loop_lines:
                continue
            
            is_hot_path = self._is_hot_path(lines, i)
            base_severity = "high" if is_hot_path else "high"
            
            # Check Spring Data patterns
            for regex, desc in self.spring_regexes:
                if regex.search(line):
                    findings.append(JavaFinding(
                        line_number=line_num,
                        line_content=line,
                        rule_id="JAVA001",
                        rule_name="Spring Data Call in Loop",
                        description=f"{desc} detected inside a loop. Each iteration queries the database.",
                        severity=base_severity,
                        category="database_read",
                        suggestion="Use batch operations like findAllById() or custom batch queries instead."
                    ))
                    break
            
            # Check RestTemplate patterns
            for regex, desc in self.rest_regexes:
                if regex.search(line):
                    findings.append(JavaFinding(
                        line_number=line_num,
                        line_content=line,
                        rule_id="JAVA002",
                        rule_name="HTTP Call in Loop",
                        description=f"{desc} detected inside a loop. Each iteration makes an HTTP request.",
                        severity=base_severity,
                        category="api_call",
                        suggestion="Batch API calls or use async/parallel execution with WebClient."
                    ))
                    break
            
            # Check ObjectMapper patterns
            for regex, desc in self.mapper_regexes:
                if regex.search(line):
                    findings.append(JavaFinding(
                        line_number=line_num,
                        line_content=line,
                        rule_id="JAVA003",
                        rule_name="Serialization in Loop",
                        description=f"{desc} detected inside a loop. Repeated JSON serialization is CPU-intensive.",
                        severity="medium",
                        category="serialization",
                        suggestion="Batch serialize by collecting objects into a list and serializing once."
                    ))
                    break
            
            # Check JDBC patterns
            for regex, desc in self.jdbc_regexes:
                if regex.search(line):
                    # ResultSet.next() is expected in loops, so lower severity
                    if "ResultSet" in desc:
                        continue
                    
                    findings.append(JavaFinding(
                        line_number=line_num,
                        line_content=line,
                        rule_id="JAVA004",
                        rule_name="JDBC Call in Loop",
                        description=f"{desc} detected inside a loop. Each iteration executes a database query.",
                        severity=base_severity,
                        category="database_read",
                        suggestion="Use batch operations or prepare the query once outside the loop."
                    ))
                    break
            
            # Check AWS SDK patterns
            for regex, desc in self.aws_regexes:
                if regex.search(line):
                    category = "api_call"
                    if "DynamoDB" in desc:
                        category = "database_read"
                    
                    findings.append(JavaFinding(
                        line_number=line_num,
                        line_content=line,
                        rule_id="JAVA005",
                        rule_name="AWS SDK Call in Loop",
                        description=f"{desc} detected inside a loop. Each iteration makes an AWS API call.",
                        severity=base_severity,
                        category=category,
                        suggestion="Use batch operations like BatchGetItem or batch write for DynamoDB."
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
