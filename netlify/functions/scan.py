"""
Netlify serverless function for scanning code.
"""
import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from finlinter.core import ScannerDispatch
from finlinter.cost import CostEstimator
from finlinter.cost.estimator import CostEstimate, CostCategory


def handler(event, context):
    """
    Netlify function handler for code scanning.
    """
    # Only allow POST requests
    if event['httpMethod'] != 'POST':
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # Parse the request body
        body = json.loads(event['body'])
        code = body.get('code', '')
        language = body.get('language', 'auto')
        
        # Map 'auto' to None for auto-detection
        if language == 'auto':
            language = None
        
        if not code.strip():
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'success': False,
                    'error': 'No code provided'
                })
            }
        
        # Initialize scanner and estimator
        scanner = ScannerDispatch()
        estimator = CostEstimator()
        
        # Scan the code
        result = scanner.scan_code(code, language=language)
        
        # Build cost summary
        estimates = []
        for f in result.findings:
            if f.estimated_cost:
                estimates.append(CostEstimate(
                    category=CostCategory(f.estimated_cost['category']),
                    unit_cost=f.estimated_cost['unit_cost'],
                    iterations=f.estimated_cost['iterations'],
                    per_execution_cost=f.estimated_cost['per_execution_cost'],
                    monthly_cost=f.estimated_cost['monthly_cost'],
                    severity=f.estimated_cost['severity'],
                ))
        
        summary = estimator.get_summary(estimates)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'result': result.to_dict(),
                'summary': summary
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
