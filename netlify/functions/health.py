"""
Netlify serverless function for health check.
"""
import json


def handler(event, context):
    """Health check endpoint."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'status': 'healthy',
            'version': '1.0.0'
        })
    }
