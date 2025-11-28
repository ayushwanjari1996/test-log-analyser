"""Custom exceptions for log analyzer."""


class LogAnalyzerError(Exception):
    """Base exception for log analyzer."""
    pass


class ConfigurationError(LogAnalyzerError):
    """Raised when configuration is invalid or missing."""
    pass


class LogFileError(LogAnalyzerError):
    """Raised when log file cannot be read or processed."""
    pass


class LLMError(LogAnalyzerError):
    """Raised when LLM communication fails."""
    pass


class EntityExtractionError(LogAnalyzerError):
    """Raised when entity extraction fails."""
    pass


class ValidationError(LogAnalyzerError):
    """Raised when input validation fails."""
    pass
