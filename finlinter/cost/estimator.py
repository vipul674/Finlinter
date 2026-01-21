"""
Cost Estimator Module

Provides hardcoded cost calculations for detected patterns.
No external API calls - all pricing is bundled locally.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class CostCategory(Enum):
    """Categories of cost-incurring operations."""
    DATABASE_READ = "database_read"
    DATABASE_WRITE = "database_write"
    API_CALL = "api_call"
    SERIALIZATION = "serialization"


@dataclass
class CostConfig:
    """Cost configuration with hardcoded pricing in ₹ (INR)."""
    
    # Unit costs in ₹ (Indian Rupees)
    UNIT_COSTS: Dict[CostCategory, float] = None
    
    # Default assumptions
    DEFAULT_LOOP_ITERATIONS: int = 100
    DEFAULT_DAILY_EXECUTIONS: int = 1  # For monthly calculation (daily × 30)
    
    # Disclaimer for cost estimates
    DISCLAIMER: str = "Approximate estimate for awareness, not exact billing."
    
    def __post_init__(self):
        if self.UNIT_COSTS is None:
            self.UNIT_COSTS = {
                CostCategory.DATABASE_READ: 0.002,    # ₹0.002 per query
                CostCategory.DATABASE_WRITE: 0.004,   # ₹0.004 per write
                CostCategory.API_CALL: 0.01,          # ₹0.01 per call
                CostCategory.SERIALIZATION: 0.0001,   # Minimal CPU cost
            }


@dataclass
class CostEstimate:
    """Cost estimate for a single finding in ₹."""
    
    category: CostCategory
    unit_cost: float
    iterations: int
    per_execution_cost: float  # Cost per single code execution
    monthly_cost: float        # Extrapolated (daily runs × 30)
    severity: str              # "low", "medium", "high"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "unit_cost": self.unit_cost,
            "iterations": self.iterations,
            "per_execution_cost": round(self.per_execution_cost, 2),
            "monthly_cost": round(self.monthly_cost, 2),
            "severity": self.severity,
        }


class CostEstimator:
    """
    Estimates costs for detected code patterns in ₹ (Indian Rupees).
    
    Formula: per_execution_cost = unit_cost × iterations
    Monthly: per_execution_cost × 30 (daily runs)
    """
    
    def __init__(self, config: Optional[CostConfig] = None):
        self.config = config or CostConfig()
    
    def estimate(
        self,
        category: CostCategory,
        iterations: Optional[int] = None,
    ) -> CostEstimate:
        """
        Calculate cost estimate for a pattern.
        
        Args:
            category: Type of cost-incurring operation
            iterations: Number of loop iterations (default: 100)
        
        Returns:
            CostEstimate with per-execution and monthly projections
        """
        iterations = iterations or self.config.DEFAULT_LOOP_ITERATIONS
        
        unit_cost = self.config.UNIT_COSTS.get(category, 0.0)
        
        # Calculate costs
        per_execution_cost = unit_cost * iterations
        monthly_cost = per_execution_cost * 30  # Daily runs × 30 days
        
        # Determine severity based on monthly cost in ₹
        severity = self._calculate_severity(monthly_cost)
        
        return CostEstimate(
            category=category,
            unit_cost=unit_cost,
            iterations=iterations,
            per_execution_cost=per_execution_cost,
            monthly_cost=monthly_cost,
            severity=severity,
        )
    
    def _calculate_severity(self, monthly_cost: float) -> str:
        """
        Determine severity level based on monthly cost in ₹.
        
        Thresholds:
        - High: > ₹100/month
        - Medium: > ₹10/month
        - Low: <= ₹10/month
        """
        if monthly_cost > 100:
            return "high"
        elif monthly_cost > 10:
            return "medium"
        else:
            return "low"
    
    def format_cost(self, amount: float) -> str:
        """Format a cost amount for display in ₹."""
        if amount >= 1000:
            return f"₹{amount:,.2f}"
        elif amount >= 1:
            return f"₹{amount:.2f}"
        elif amount >= 0.01:
            return f"₹{amount:.4f}"
        else:
            return f"₹{amount:.6f}"
    
    def get_summary(self, estimates: list) -> dict:
        """
        Get a summary of multiple cost estimates.
        
        Args:
            estimates: List of CostEstimate objects
        
        Returns:
            Dictionary with total costs and severity breakdown
        """
        if not estimates:
            return {
                "total_per_execution": 0,
                "total_monthly": 0,
                "severity_counts": {"low": 0, "medium": 0, "high": 0},
                "findings_count": 0,
                "disclaimer": self.config.DISCLAIMER,
            }
        
        total_per_execution = sum(e.per_execution_cost for e in estimates)
        total_monthly = sum(e.monthly_cost for e in estimates)
        
        severity_counts = {"low": 0, "medium": 0, "high": 0}
        for e in estimates:
            severity_counts[e.severity] += 1
        
        return {
            "total_per_execution": round(total_per_execution, 2),
            "total_monthly": round(total_monthly, 2),
            "severity_counts": severity_counts,
            "findings_count": len(estimates),
            "disclaimer": self.config.DISCLAIMER,
        }


# Convenience function for quick estimates
def quick_estimate(category: str, iterations: int = 100) -> dict:
    """
    Quick cost estimation without instantiating the class.
    
    Args:
        category: One of "database_read", "database_write", "api_call", "serialization"
        iterations: Number of loop iterations
    
    Returns:
        Dictionary with cost breakdown in ₹
    """
    estimator = CostEstimator()
    cat = CostCategory(category)
    estimate = estimator.estimate(cat, iterations)
    return estimate.to_dict()

