"""
CLI Serve Command

Implements the `finlinter serve` command.
Launches the Flask web server for the FinLinter UI.
"""

import click


@click.command()
@click.option('--host', '-h', default='127.0.0.1',
              help='Host to bind to (default: 127.0.0.1)')
@click.option('--port', '-p', default=5000, type=int,
              help='Port to listen on (default: 5000)')
@click.option('--debug', '-d', is_flag=True,
              help='Enable debug mode')
def serve(host: str, port: int, debug: bool):
    """
    Start the FinLinter web interface.
    
    Examples:
    
        finlinter serve
        
        finlinter serve --port 8080
        
        finlinter serve --debug
    """
    from ..web import create_app
    
    app = create_app()
    
    # Print startup message
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  🔍 FinLinter Web Interface                                  ║
╠══════════════════════════════════════════════════════════════╣
║  Server running at: http://{host}:{port:<5}                      ║
║  Press Ctrl+C to stop                                        ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Run the Flask app
    app.run(host=host, port=port, debug=debug)
