"""Source connectors for Phase 1 ingestion."""

from instamart_analyser.phases.phase_1.connectors.app_store import AppStoreConnector
from instamart_analyser.phases.phase_1.connectors.base import BaseConnector
from instamart_analyser.phases.phase_1.connectors.mouthshut import MouthShutConnector
from instamart_analyser.phases.phase_1.connectors.play_store import PlayStoreConnector
from instamart_analyser.phases.phase_1.connectors.reddit import RedditConnector
from instamart_analyser.phases.phase_1.connectors.reddit_selenium import RedditSeleniumConnector
from instamart_analyser.phases.phase_1.connectors.seed_category import SeedCategoryConnector

__all__ = [
    "AppStoreConnector",
    "BaseConnector",
    "MouthShutConnector",
    "PlayStoreConnector",
    "RedditConnector",
    "RedditSeleniumConnector",
    "SeedCategoryConnector",
]
