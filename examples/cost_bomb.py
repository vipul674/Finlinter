"""
Python Cost Bomb Example

This file demonstrates patterns that FinLinter should detect.
These are common anti-patterns that cause excessive cloud costs.
"""

import json
import requests

# Simulated imports for demonstration
class dynamodb:
    @staticmethod
    def get_item(TableName, Key):
        pass

class session:
    @staticmethod
    def query(model):
        pass

class db:
    @staticmethod
    def get(key):
        pass


def process_users(user_ids: list):
    """
    BAD: Multiple database and API calls inside a loop.
    This will trigger FinLinter warnings.
    """
    results = []
    
    for user_id in user_ids:
        # BAD: Database call in loop
        user_data = dynamodb.get_item(
            TableName='users',
            Key={'id': user_id}
        )
        
        # BAD: HTTP request in loop
        response = requests.get(
            f'https://api.example.com/enrichment/{user_id}'
        )
        
        # BAD: JSON serialization in loop
        serialized = json.dumps(user_data)
        
        results.append({
            'user': user_data,
            'enrichment': response.json(),
            'serialized': serialized
        })
    
    return results


def handle_batch_request(items: list):
    """
    BAD: ORM query inside a list comprehension (hidden loop).
    """
    # BAD: Database query in list comprehension
    enriched = [session.query(item) for item in items]
    
    # BAD: API calls in generator expression
    responses = (requests.post('https://api.example.com/process', json=item) 
                 for item in items)
    
    return list(responses)


def controller_endpoint(request_data: dict):
    """
    BAD: This is in a hot code path (controller name).
    """
    ids = request_data.get('ids', [])
    
    for id in ids:
        # BAD: Database get in loop in hot path
        data = db.get(id)
        
        # BAD: JSON loads in loop
        parsed = json.loads(data)
    
    return {'status': 'done'}


# ============================================================
# GOOD PATTERNS (for comparison - should NOT trigger warnings)
# ============================================================

def process_users_correctly(user_ids: list):
    """
    GOOD: Batch operations outside the loop.
    """
    # GOOD: Single batch call
    all_users = dynamodb.batch_get_item(user_ids)
    
    # GOOD: Single API call for batch
    enrichment = requests.post(
        'https://api.example.com/batch-enrichment',
        json={'user_ids': user_ids}
    )
    
    results = []
    for user_id in user_ids:
        # Processing without I/O is fine
        user = all_users.get(user_id)
        results.append(user)
    
    # GOOD: Single serialization at the end
    return json.dumps(results)
