"""
Centralized logging configuration for the procurement system.
Uses Loguru for structured logging with rotation and retention.
"""
import sys
import json
from pathlib import Path
from loguru import logger
from datetime import datetime
from typing import Any, Dict
import os

# Remove default handler
logger.remove()

# Create logs directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Format for structured logging
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# Console handler
logger.add(
    sys.stdout,
    format=LOG_FORMAT,
    level=os.getenv("LOG_LEVEL", "INFO"),
    colorize=True,
    backtrace=True,
    diagnose=True
)

# File handler with rotation
logger.add(
    log_dir / "procurement_{time:YYYY-MM-DD}.log",
    rotation="500 MB",
    retention="30 days",
    compression="zip",
    format=LOG_FORMAT,
    level="DEBUG",
    encoding="utf-8"
)

# JSON structured log for analysis
logger.add(
    log_dir / "events.json",
    serialize=True,
    rotation="100 MB",
    retention="30 days",
    level="INFO"
)


class AgentLogger:
    """Context-aware logger for agents."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.context: Dict[str, Any] = {}
    
    def bind(self, **kwargs):
        """Add context to all subsequent logs."""
        self.context.update(kwargs)
        return self
    
    def _log(self, level: str, message: str, **kwargs):
        extra = {**self.context, **kwargs, "agent": self.agent_name}
        logger.bind(**extra).log(level, message)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("CRITICAL", message, **kwargs)


def get_logger(agent_name: str = "system") -> AgentLogger:
    """Factory function to get agent-specific logger."""
    return AgentLogger(agent_name)


__all__ = ['logger', 'get_logger', 'AgentLogger']
