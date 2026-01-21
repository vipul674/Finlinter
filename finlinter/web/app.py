"""
Flask Web Application

Provides the web interface for FinLinter.
Runs entirely locally with no external dependencies.
"""

import os
from flask import Flask, render_template, request, jsonify

from ..core import ScannerDispatch
from ..cost import CostEstimator


def create_app():
    """Create and configure the Flask application."""
    
    # Get the directory where this file is located
    app_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(app_dir, 'templates')
    static_dir = os.path.join(app_dir, 'static')
    
    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )
    
    # Initialize scanner and estimator
    scanner = ScannerDispatch()
    estimator = CostEstimator()
    
    @app.route('/')
    def index():
        """Render the main UI."""
        return render_template('index.html')
    
    @app.route('/scan', methods=['POST'])
    def scan():
        """
        Scan code for financial bugs (cost-risk patterns).
        
        Expects JSON body:
        {
            "code": "...",
            "language": "python" | "javascript" | "java" | "auto" (default)
        }
        
        Returns:
        {
            "success": true,
            "result": { ... scan result ... },
            "summary": { ... cost summary ... }
        }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    "success": False,
                    "error": "No data provided"
                }), 400
            
            code = data.get('code', '')
            language = data.get('language', 'auto')
            
            # Map 'auto' to None for auto-detection
            if language == 'auto':
                language = None
            
            if not code.strip():
                return jsonify({
                    "success": False,
                    "error": "No code provided"
                }), 400
            
            # Scan the code with specified language
            result = scanner.scan_code(code, language=language)
            
            # Build cost summary
            from ..cost.estimator import CostEstimate, CostCategory
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
            
            return jsonify({
                "success": True,
                "result": result.to_dict(),
                "summary": summary
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route('/health')
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy", "version": "1.0.0"})
    
    return app
