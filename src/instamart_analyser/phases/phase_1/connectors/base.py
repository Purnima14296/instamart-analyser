"""Base connector interface."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from instamart_analyser.common.config import INSTAMART_REQUIRED_TERMS
from instamart_analyser.common.dates import DEFAULT_LOOKBACK_DAYS

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base for all feedback source connectors."""

    source: str

    def __init__(
        self,
        batch_id: str,
        max_records: int = 0,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> None:
        self.batch_id = batch_id
        self.max_records = max_records  # 0 = no limit on matched Instamart reviews
        self.lookback_days = lookback_days

    @abstractmethod
    def collect(self) -> ConnectorResult:
        """Fetch and return feedback records."""

    def matches_instamart_keywords(self, text: str) -> bool:
        """Return True only if the text explicitly mentions Instamart."""
        lowered = text.lower()
        return any(term in lowered for term in INSTAMART_REQUIRED_TERMS)

    def detect_language(self, text: str) -> str:
        """Simple language detection. Defaults to English."""
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        return "en"
