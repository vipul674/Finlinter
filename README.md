# Financial Code Validator

> We treat cloud cost as a code bug and catch it before deployment using static analysis.

A local tool that detects cost-heavy code patterns in **Python, JavaScript, and Java**, estimates cloud cost in ₹ (Indian Rupees), and suggests fixes before code is deployed.

## What It Does

**Cloud cost is treated as a code bug.** Just like syntax bugs, logic bugs, and security bugs — this tool introduces **financial bugs**.

1. **Paste code** into the web interface (Python, JavaScript, or Java)
2. Click **"Analyze"**
3. Receive a **structured cost report** with fixes

## Features

- 🔍 **Static Pattern Detection**: Uses AST/regex to detect cost-heavy patterns
- 💰 **Cost Estimation**: Estimates costs in ₹ per execution and monthly
- 💡 **Fix Recommendations**: Every issue includes a recommended fix
- 🖥️ **100% Local**: Runs entirely offline, no cloud dependencies
- 🌐 **Multi-Language**: Python, JavaScript, and Java support

## Detected Patterns

| Language | Patterns Detected |
|----------|-------------------|
| Python | API/DB calls in loops, N+1 queries, unbounded queries |
| JavaScript | fetch/axios in loops, MongoDB ops in loops, async fan-out |
| Java | Spring Data repos in loops, RestTemplate, JDBC, ObjectMapper |

## Cost Model

| Operation | Unit Cost |
|-----------|-----------|
| API Call | ₹0.01 |
| DB Query | ₹0.002 |

Formula: `per_execution_cost = unit_cost × iterations (default: 100)`

> ⚠️ Approximate estimate for awareness, not exact billing.

## Installation

```bash
cd FinOPS\ code-linter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install
pip install -e .
```

## Usage

### Web Interface (Recommended)

```bash
finlinter serve
```

Open http://127.0.0.1:5000 in your browser, paste Python code, and click "Analyze".

### CLI

```bash
# Scan a file
finlinter scan mycode.py

# Scan a directory
finlinter scan ./src

# JSON output
finlinter scan ./src --json
```

## Example Output

```
⚠ Financial Bug Detected

Pattern: API call inside loop
Line: 14
Severity: High

Estimated Cost:
₹1.00 per execution
≈ ₹30.00 per month (daily runs)

Why this matters:
Each loop iteration triggers a paid API request.

Recommended Fix:
Use a bulk or batch API endpoint to reduce call count.
```

## Development

```bash
# Run tests
pytest tests/ -v

# Scan example files
finlinter scan examples/
```

## License

MIT License
