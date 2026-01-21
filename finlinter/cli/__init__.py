"""CLI entrypoints for FinLinter."""

import click
from .scan import scan
from .serve import serve


@click.group()
@click.version_option(version="1.0.0", prog_name="finlinter")
def main():
    """FinLinter - Detect cost-risk patterns in your code."""
    pass


main.add_command(scan)
main.add_command(serve)

__all__ = ["main", "scan", "serve"]
