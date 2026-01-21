"""
Unit Tests for FinLinter Scanners

Tests the Python, JavaScript, and Java scanners for correct detection
of cost-risk patterns.
"""

import pytest
from finlinter.core import ScannerDispatch, PythonScanner, JavaScriptScanner, JavaScanner
from finlinter.core.scanner_dispatch import Language


class TestPythonScanner:
    """Tests for the Python scanner."""
    
    def setup_method(self):
        self.scanner = PythonScanner()
    
    def test_database_call_in_for_loop(self):
        """Detect database call inside a for loop."""
        code = '''
for user_id in user_ids:
    data = dynamodb.get_item(TableName='users', Key={'id': user_id})
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "PY001" for f in findings)
        assert any("Database" in f.rule_name for f in findings)
    
    def test_api_call_in_for_loop(self):
        """Detect API call inside a for loop."""
        code = '''
for item in items:
    response = requests.get(f'https://api.example.com/{item}')
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "PY002" for f in findings)
        assert any("API" in f.rule_name for f in findings)
    
    def test_json_in_for_loop(self):
        """Detect JSON serialization inside a for loop."""
        code = '''
for data in dataset:
    serialized = json.dumps(data)
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "PY003" for f in findings)
        assert any("Serialization" in f.rule_name for f in findings)
    
    def test_database_call_in_list_comprehension(self):
        """Detect database call in list comprehension."""
        code = '''
results = [db.get(id) for id in ids]
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
    
    def test_no_issue_outside_loop(self):
        """No warning for calls outside loops (except unbounded queries)."""
        code = '''
data = dynamodb.get_item(TableName='users', Key={'id': 123})
response = requests.get('https://api.example.com/data')
serialized = json.dumps(data)
'''
        findings = self.scanner.scan(code)
        # Only loop-based patterns should trigger here
        assert all(f.rule_id != 'PY001' for f in findings)
        assert all(f.rule_id != 'PY002' for f in findings)
    
    def test_cost_estimate_included(self):
        """Verify cost estimate is attached to findings."""
        code = '''
for user_id in user_ids:
    data = dynamodb.get_item(TableName='users', Key={'id': user_id})
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert findings[0].estimated_cost is not None
        assert 'per_execution_cost' in findings[0].estimated_cost
        assert 'monthly_cost' in findings[0].estimated_cost
    
    def test_unbounded_query_detection(self):
        """Detect query without LIMIT or pagination."""
        code = '''
cursor.execute("SELECT * FROM users")
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "PY004" for f in findings)
        assert any("Unbounded" in f.rule_name for f in findings)
    
    def test_bounded_query_no_warning(self):
        """No warning for queries with LIMIT."""
        code = '''
cursor.execute("SELECT * FROM users LIMIT 100")
'''
        findings = self.scanner.scan(code)
        # Should not have PY004 for bounded query
        assert not any(f.rule_id == "PY004" for f in findings)


class TestJavaScriptScanner:
    """Tests for the JavaScript scanner."""
    
    def setup_method(self):
        self.scanner = JavaScriptScanner()
    
    def test_fetch_in_for_loop(self):
        """Detect fetch() inside a for loop."""
        code = '''
for (const id of ids) {
    const response = await fetch(`https://api.example.com/${id}`);
}
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "JS001" for f in findings)
    
    def test_axios_in_for_loop(self):
        """Detect axios call inside a for loop."""
        code = '''
for (let i = 0; i < items.length; i++) {
    const data = await axios.get(`/api/items/${items[i]}`);
}
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any("API" in f.rule_name for f in findings)
    
    def test_mongodb_in_foreach(self):
        """Detect MongoDB call inside forEach."""
        code = '''
items.forEach(async (item) => {
    const doc = await db.collection('items').findOne({ id: item.id });
});
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "JS002" for f in findings)
    
    def test_json_parse_in_loop(self):
        """Detect JSON.parse inside a loop."""
        code = '''
for (const str of strings) {
    const obj = JSON.parse(str);
}
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "JS004" for f in findings)
    
    def test_no_issue_outside_loop(self):
        """No warning for calls outside loops."""
        code = '''
const response = await fetch('https://api.example.com/data');
const data = JSON.parse(jsonStr);
'''
        findings = self.scanner.scan(code)
        assert len(findings) == 0


class TestJavaScanner:
    """Tests for the Java scanner."""
    
    def setup_method(self):
        self.scanner = JavaScanner()
    
    def test_repository_in_for_loop(self):
        """Detect Spring Data repository call inside a for loop."""
        code = '''
for (Long id : ids) {
    User user = repository.findById(id).orElse(null);
}
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "JAVA001" for f in findings)
    
    def test_resttemplate_in_for_loop(self):
        """Detect RestTemplate call inside a for loop."""
        code = '''
for (String id : ids) {
    Object result = restTemplate.getForObject("https://api.example.com/" + id, Object.class);
}
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "JAVA002" for f in findings)
    
    def test_objectmapper_in_loop(self):
        """Detect ObjectMapper call inside a loop."""
        code = '''
for (Object obj : objects) {
    String json = objectMapper.writeValueAsString(obj);
}
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "JAVA003" for f in findings)
    
    def test_jdbc_in_loop(self):
        """Detect JdbcTemplate call inside a loop."""
        code = '''
for (String orderId : orderIds) {
    Order order = jdbcTemplate.queryForObject("SELECT * FROM orders WHERE id = ?", Order.class, orderId);
}
'''
        findings = self.scanner.scan(code)
        assert len(findings) >= 1
        assert any(f.rule_id == "JAVA004" for f in findings)
    
    def test_no_issue_outside_loop(self):
        """No warning for calls outside loops."""
        code = '''
User user = repository.findById(123L).orElse(null);
Object result = restTemplate.getForObject("https://api.example.com/data", Object.class);
'''
        findings = self.scanner.scan(code)
        assert len(findings) == 0


class TestScannerDispatch:
    """Tests for the scanner dispatcher."""
    
    def setup_method(self):
        self.dispatch = ScannerDispatch()
    
    def test_detect_python_by_extension(self):
        """Detect Python by .py extension."""
        lang = self.dispatch.detect_language(file_path="test.py")
        assert lang == Language.PYTHON
    
    def test_detect_javascript_by_extension(self):
        """Detect JavaScript by .js extension."""
        lang = self.dispatch.detect_language(file_path="test.js")
        assert lang == Language.JAVASCRIPT
    
    def test_detect_java_by_extension(self):
        """Detect Java by .java extension."""
        lang = self.dispatch.detect_language(file_path="Test.java")
        assert lang == Language.JAVA
    
    def test_detect_python_by_content(self):
        """Detect Python from code content."""
        code = '''
def main():
    print("Hello, world!")
    
if __name__ == "__main__":
    main()
'''
        lang = self.dispatch.detect_language(code=code)
        assert lang == Language.PYTHON
    
    def test_detect_javascript_by_content(self):
        """Detect JavaScript from code content."""
        code = '''
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.send('Hello World!');
});
'''
        lang = self.dispatch.detect_language(code=code)
        assert lang == Language.JAVASCRIPT
    
    def test_detect_java_by_content(self):
        """Detect Java from code content."""
        code = '''
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
'''
        lang = self.dispatch.detect_language(code=code)
        assert lang == Language.JAVA
    
    def test_scan_code_with_auto_detect(self):
        """Scan code with automatic language detection."""
        code = '''
def process_users(user_ids):
    for user_id in user_ids:
        data = dynamodb.get_item(TableName='users', Key={'id': user_id})
    return data
'''
        result = self.dispatch.scan_code(code)
        assert result.language == Language.PYTHON
        assert len(result.findings) >= 1
    
    def test_scan_code_with_explicit_language(self):
        """Scan code with explicitly specified language."""
        code = '''
for user_id in user_ids:
    data = dynamodb.get_item(TableName='users', Key={'id': user_id})
'''
        result = self.dispatch.scan_code(code, language="python")
        assert result.language == Language.PYTHON
        assert len(result.findings) >= 1


class TestCostEstimator:
    """Tests for the cost estimator."""
    
    def test_database_cost_estimate(self):
        """Verify correct cost calculation for database operations in ₹."""
        from finlinter.cost.estimator import CostEstimator, CostCategory
        
        estimator = CostEstimator()
        estimate = estimator.estimate(CostCategory.DATABASE_READ)
        
        # unit_cost=0.002 ₹, iterations=100
        # per_execution = 0.002 * 100 = 0.2 ₹
        assert estimate.per_execution_cost == pytest.approx(0.2, rel=0.01)
        assert estimate.monthly_cost == pytest.approx(0.2 * 30, rel=0.01)
    
    def test_api_cost_estimate(self):
        """Verify correct cost calculation for API calls in ₹."""
        from finlinter.cost.estimator import CostEstimator, CostCategory
        
        estimator = CostEstimator()
        estimate = estimator.estimate(CostCategory.API_CALL)
        
        # unit_cost=0.01 ₹, iterations=100
        # per_execution = 0.01 * 100 = 1 ₹
        # monthly = 1 × 30 = 30 ₹ (> 10, so medium)
        assert estimate.per_execution_cost == pytest.approx(1.0, rel=0.01)
        assert estimate.severity == "medium"  # 30 ₹/month > 10
    
    def test_severity_levels(self):
        """Verify correct severity assignment based on monthly cost in ₹."""
        from finlinter.cost.estimator import CostEstimator, CostCategory
        
        estimator = CostEstimator()
        
        # API calls with 100 iterations: 1₹ per execution, 30₹/month -> medium (>10)
        api_estimate = estimator.estimate(CostCategory.API_CALL)
        assert api_estimate.severity == "medium"
        
        # Database reads: 0.2₹ per execution, 6₹/month -> low
        db_estimate = estimator.estimate(CostCategory.DATABASE_READ)
        assert db_estimate.severity == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
