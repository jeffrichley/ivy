from __future__ import annotations

from abc import ABC, abstractmethod

from ivy.domain.models.context import ExecutionContext
from ivy.domain.models.plan import CommandResult


class BaseCommand(ABC):
    """Template base for command handlers."""

    @abstractmethod
    def execute(self, context: ExecutionContext) -> CommandResult:
        """Execute command for the provided context."""
