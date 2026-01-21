"""
CLI Scan Command

Implements the `finlinter scan <path>` command.
Scans files/directories for cost-risk patterns with color-coded output.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import click

from ..core import ScannerDispatch
from ..cost import CostEstimator


# ANSI color codes for terminal output
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def severity_color(severity: str) -> str:
    """Get color for severity level."""
    colors = {
        "critical": Colors.RED + Colors.BOLD,
        "high": Colors.RED,
        "medium": Colors.YELLOW,
        "low": Colors.GREEN,
    }
    return colors.get(severity, Colors.WHITE)


def format_cost(amount: float) -> str:
    """Format a cost amount for display in ₹."""
    if amount >= 1000:
        return f"₹{amount:,.2f}"
    elif amount >= 1:
        return f"₹{amount:.2f}"
    elif amount >= 0.01:
        return f"₹{amount:.2f}"
    else:
        return f"₹{amount:.4f}"


def print_finding(finding, show_cost: bool = True):
    """Print a single finding with color formatting."""
    severity = finding.severity
    color = severity_color(severity)
    
    # Header line - Financial Bug format
    print(f"\n{Colors.YELLOW}⚠️  Financial Bug Detected{Colors.RESET}")
    print(f"{color}[{severity.upper()}]{Colors.RESET} {Colors.BOLD}{finding.rule_name}{Colors.RESET}")
    print(f"  {Colors.DIM}Rule: {finding.rule_id}{Colors.RESET}")
    
    # Location
    print(f"  {Colors.CYAN}📍 {finding.file_path}:{finding.line_number}{Colors.RESET}")
    
    # Code snippet
    line_content = finding.line_content.strip()
    if len(line_content) > 80:
        line_content = line_content[:77] + "..."
    print(f"  {Colors.DIM}│{Colors.RESET} {line_content}")
    
    # Description (Why this matters)
    print(f"  {Colors.WHITE}⚠️  {finding.description}{Colors.RESET}")
    
    # Cost estimate
    if show_cost and finding.estimated_cost:
        cost = finding.estimated_cost
        per_exec = format_cost(cost['per_execution_cost'])
        monthly = format_cost(cost['monthly_cost'])
        print(f"  {Colors.YELLOW}💰 Estimated: {per_exec}/execution → {monthly}/month{Colors.RESET}")
    
    # Suggestion (Recommended Fix)
    if finding.suggestion:
        print(f"  {Colors.GREEN}💡 Recommended Fix: {finding.suggestion}{Colors.RESET}")


def print_summary(results, estimator):
    """Print a summary of all findings."""
    all_findings = []
    for result in results:
        all_findings.extend(result.findings)
    
    if not all_findings:
        print(f"\n{Colors.GREEN}✓ No financial bugs detected!{Colors.RESET}")
        return
    
    # Collect cost estimates
    estimates = []
    for f in all_findings:
        if f.estimated_cost:
            from ..cost.estimator import CostEstimate, CostCategory
            estimates.append(CostEstimate(
                category=CostCategory(f.estimated_cost['category']),
                unit_cost=f.estimated_cost['unit_cost'],
                iterations=f.estimated_cost['iterations'],
                per_execution_cost=f.estimated_cost['per_execution_cost'],
                monthly_cost=f.estimated_cost['monthly_cost'],
                severity=f.estimated_cost['severity'],
            ))
    
    summary = estimator.get_summary(estimates)
    
    # Print summary header
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}COST REPORT SUMMARY{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    # File summary
    files_with_issues = sum(1 for r in results if r.findings)
    total_files = len(results)
    print(f"\n📁 Files scanned: {total_files}")
    print(f"⚠️  Files with financial bugs: {files_with_issues}")
    print(f"🔍 Total findings: {summary['findings_count']}")
    
    # Severity breakdown
    print(f"\n{Colors.BOLD}Severity Breakdown:{Colors.RESET}")
    sc = summary['severity_counts']
    if sc['high'] > 0:
        print(f"  {Colors.RED}● High: {sc['high']}{Colors.RESET}")
    if sc['medium'] > 0:
        print(f"  {Colors.YELLOW}● Medium: {sc['medium']}{Colors.RESET}")
    if sc['low'] > 0:
        print(f"  {Colors.GREEN}● Low: {sc['low']}{Colors.RESET}")
    
    # Cost summary
    print(f"\n{Colors.BOLD}💰 Estimated Cost Impact:{Colors.RESET}")
    print(f"  Per Execution: {format_cost(summary['total_per_execution'])}")
    print(f"  Monthly:       {Colors.RED}{Colors.BOLD}{format_cost(summary['total_monthly'])}{Colors.RESET}")
    
    print(f"\n{Colors.DIM}⚠️  {summary.get('disclaimer', 'Approximate estimate for awareness, not exact billing.')}{Colors.RESET}")


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive/--no-recursive', '-r/-R', default=True,
              help='Recursively scan directories')
@click.option('--json', 'output_json', is_flag=True,
              help='Output results as JSON')
@click.option('--verbose', '-v', is_flag=True,
              help='Show detailed output')
@click.option('--no-color', is_flag=True,
              help='Disable colored output')
def scan(path: str, recursive: bool, output_json: bool, verbose: bool, no_color: bool):
    """
    Scan files or directories for cost-risk patterns.
    
    Examples:
    
        finlinter scan myproject/
        
        finlinter scan api.py
        
        finlinter scan . --json
    """
    # Disable colors if requested or not a TTY
    if no_color or not sys.stdout.isatty():
        Colors.RED = ''
        Colors.YELLOW = ''
        Colors.GREEN = ''
        Colors.BLUE = ''
        Colors.CYAN = ''
        Colors.WHITE = ''
        Colors.BOLD = ''
        Colors.DIM = ''
        Colors.RESET = ''
    
    scanner = ScannerDispatch()
    estimator = CostEstimator()
    
    path_obj = Path(path)
    
    # Scan based on path type
    if path_obj.is_file():
        results = [scanner.scan_file(str(path_obj))]
    else:
        results = scanner.scan_directory(str(path_obj), recursive=recursive)
    
    # Handle JSON output
    if output_json:
        import json
        output = {
            "results": [r.to_dict() for r in results],
            "summary": {
                "total_files": len(results),
                "files_with_issues": sum(1 for r in results if r.findings),
                "total_findings": sum(len(r.findings) for r in results),
            }
        }
        print(json.dumps(output, indent=2))
        return
    
    # Print header
    print(f"\n{Colors.BOLD}╔══════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}║  💰 Financial Code Validator                           ║{Colors.RESET}")
    print(f"{Colors.BOLD}╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    print(f"\n{Colors.DIM}Scanning: {path}{Colors.RESET}")
    
    # Print findings grouped by file
    current_file = None
    findings_count = 0
    
    for result in results:
        if result.error:
            print(f"\n{Colors.RED}Error scanning {result.file_path}: {result.error}{Colors.RESET}")
            continue
        
        if not result.findings:
            if verbose:
                print(f"\n{Colors.GREEN}✓ {result.file_path}: No issues{Colors.RESET}")
            continue
        
        # Print file header
        if result.file_path != current_file:
            current_file = result.file_path
            print(f"\n{Colors.BOLD}{'─'*60}{Colors.RESET}")
            print(f"{Colors.BOLD}📄 {result.file_path}{Colors.RESET}")
            print(f"   {Colors.DIM}Language: {result.language.value} | "
                  f"Scan time: {result.scan_time_ms:.1f}ms{Colors.RESET}")
        
        # Print each finding
        for finding in result.findings:
            print_finding(finding)
            findings_count += 1
    
    # Print summary
    print_summary(results, estimator)
    
    # Exit with error code if issues found
    if findings_count > 0:
        sys.exit(1)
