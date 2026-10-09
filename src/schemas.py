"""Value contracts. Validates what the extractor is allowed to return."""
from dataclasses import dataclass, field

CATEGORIES = {"dev_tools", "ai_infra", "data_infra", "horizontal_saas",
              "vertical_saas", "fintech", "security", "other", "unknown"}
SELLS_TO = {"businesses", "consumers", "both", "unknown"}
QUALITY = {"usable", "missing", "failed"}


@dataclass
class ExtractedCompany:
    name: str
    what_they_do: str = ""
    category: str = "unknown"
    sells_to: str = "unknown"
    tech_signals: list = field(default_factory=list)

    def validate(self):
        """Return a list of problems; empty means valid."""
        problems = []
        if self.category not in CATEGORIES:
            problems.append(f"bad category: {self.category!r}")
        if self.sells_to not in SELLS_TO:
            problems.append(f"bad sells_to: {self.sells_to!r}")
        return problems
