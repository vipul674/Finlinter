"""
Scanner Dispatch Module

Central dispatcher that routes files to appropriate language scanners
based on file extension or content analysis.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    UNKNOWN = "unknown"


# File extension to language mapping
EXTENSION_MAP: Dict[str, Language] = {
    ".py": Language.PYTHON,
    ".pyw": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.JAVASCRIPT,  # TypeScript uses similar patterns
    ".tsx": Language.JAVASCRIPT,
    ".java": Language.JAVA,
}


@dataclass
class Finding:
    """Represents a single code finding."""
    
    file_path: str
    line_number: int
    line_content: str
    rule_id: str
    rule_name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    category: str  # "database_read", "api_call", etc.
    suggestion: str
    estimated_cost: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content.strip(),
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "description": self.description,
            "severity": self.severity,
            "category": self.category,
            "suggestion": self.suggestion,
            "estimated_cost": self.estimated_cost,
        }


@dataclass
class ScanResult:
    """Result of scanning a file or code snippet."""
    
    file_path: str
    language: Language
    findings: List[Finding] = field(default_factory=list)
    scan_time_ms: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "language": self.language.value,
            "findings": [f.to_dict() for f in self.findings],
            "findings_count": len(self.findings),
            "scan_time_ms": round(self.scan_time_ms, 2),
            "error": self.error,
        }


class ScannerDispatch:
    """
    Central dispatcher for routing code to appropriate language scanners.
    """
    
    def __init__(self):
        # Import scanners lazily to avoid circular imports
        from .python_scanner import PythonScanner
        from .js_scanner import JavaScriptScanner
        from .java_scanner import JavaScanner
        
        self.scanners = {
            Language.PYTHON: PythonScanner(),
            Language.JAVASCRIPT: JavaScriptScanner(),
            Language.JAVA: JavaScanner(),
        }
    
    def detect_language(self, file_path: Optional[str] = None, code: Optional[str] = None) -> Language:
        """
        Detect the programming language from file extension or code content.
        
        Args:
            file_path: Path to the file (uses extension)
            code: Source code content (uses heuristics)
        
        Returns:
            Detected Language enum value
        """
        # Try file extension first
        if file_path:
            ext = Path(file_path).suffix.lower()
            if ext in EXTENSION_MAP:
                return EXTENSION_MAP[ext]
        
        # Fall back to content analysis
        if code:
            return self._detect_from_content(code)
        
        return Language.UNKNOWN
    
    def _detect_from_content(self, code: str) -> Language:
        """
        Detect language from code content using heuristics.
        """
        code_lower = code.lower()
        
        # Python indicators
        python_indicators = [
            "def ", "import ", "from ", "class ", "::", "self.", 
            "elif ", "except:", "with open", "__init__"
        ]
        python_score = sum(1 for ind in python_indicators if ind in code_lower)
        
        # JavaScript indicators
        js_indicators = [
            "const ", "let ", "var ", "function ", "=> ", 
            "require(", "import ", "export ", "async ", "await ",
            "console.log", ".then(", ".catch("
        ]
        js_score = sum(1 for ind in js_indicators if ind in code_lower)
        
        # Java indicators
        java_indicators = [
            "public class", "private ", "protected ", "static void main",
            "system.out", "@override", "@autowired", "new ", 
            "throws ", "implements ", "extends "
        ]
        java_score = sum(1 for ind in java_indicators if ind in code_lower)
        
        # Determine winner
        scores = {
            Language.PYTHON: python_score,
            Language.JAVASCRIPT: js_score,
            Language.JAVA: java_score,
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            return Language.UNKNOWN
        
        for lang, score in scores.items():
            if score == max_score:
                return lang
        
        return Language.UNKNOWN
    
    def scan_code(
        self, 
        code: str, 
        language: Optional[Union[Language, str]] = None,
        file_path: str = "<input>"
    ) -> ScanResult:
        """
        Scan a code snippet for cost-risk patterns.
        
        Args:
            code: Source code to scan
            language: Programming language (auto-detect if None)
            file_path: File path for reporting (default: "<input>")
        
        Returns:
            ScanResult with findings
        """
        import time
        start_time = time.time()
        
        # Normalize language
        if isinstance(language, str):
            try:
                language = Language(language.lower())
            except ValueError:
                language = None
        
        # Detect language if not provided
        if language is None or language == Language.UNKNOWN:
            language = self.detect_language(file_path=file_path, code=code)
        
        if language == Language.UNKNOWN:
            return ScanResult(
                file_path=file_path,
                language=language,
                findings=[],
                error="Could not detect programming language"
            )
        
        # Get appropriate scanner
        scanner = self.scanners.get(language)
        if not scanner:
            return ScanResult(
                file_path=file_path,
                language=language,
                findings=[],
                error=f"No scanner available for {language.value}"
            )
        
        # Perform scan
        try:
            findings = scanner.scan(code, file_path)
            scan_time = (time.time() - start_time) * 1000
            
            return ScanResult(
                file_path=file_path,
                language=language,
                findings=findings,
                scan_time_ms=scan_time,
            )
        except Exception as e:
            return ScanResult(
                file_path=file_path,
                language=language,
                findings=[],
                error=str(e),
            )
    
    def scan_file(self, file_path: str) -> ScanResult:
        """
        Scan a file for cost-risk patterns.
        
        Args:
            file_path: Path to the file to scan
        
        Returns:
            ScanResult with findings
        """
        path = Path(file_path)
        
        if not path.exists():
            return ScanResult(
                file_path=file_path,
                language=Language.UNKNOWN,
                error=f"File not found: {file_path}"
            )
        
        if not path.is_file():
            return ScanResult(
                file_path=file_path,
                language=Language.UNKNOWN,
                error=f"Not a file: {file_path}"
            )
        
        try:
            code = path.read_text(encoding="utf-8")
        except Exception as e:
            return ScanResult(
                file_path=file_path,
                language=Language.UNKNOWN,
                error=f"Could not read file: {e}"
            )
        
        language = self.detect_language(file_path=file_path)
        return self.scan_code(code, language, file_path)
    
    def scan_directory(
        self, 
        directory: str, 
        recursive: bool = True,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[ScanResult]:
        """
        Scan all supported files in a directory.
        
        Args:
            directory: Path to directory to scan
            recursive: Whether to scan subdirectories
            exclude_patterns: Patterns to exclude (e.g., ["node_modules", ".git"])
        
        Returns:
            List of ScanResult objects
        """
        results = []
        exclude_patterns = exclude_patterns or ["node_modules", ".git", "__pycache__", "venv", ".venv"]
        
        dir_path = Path(directory)
        if not dir_path.exists():
            return results
        
        # Get all files
        if recursive:
            files = dir_path.rglob("*")
        else:
            files = dir_path.glob("*")
        
        for file_path in files:
            # Skip directories
            if not file_path.is_file():
                continue
            
            # Check exclusions
            skip = False
            for pattern in exclude_patterns:
                if pattern in str(file_path):
                    skip = True
                    break
            if skip:
                continue
            
            # Check if supported extension
            ext = file_path.suffix.lower()
            if ext not in EXTENSION_MAP:
                continue
            
            # Scan file
            result = self.scan_file(str(file_path))
            results.append(result)
        
        return results
