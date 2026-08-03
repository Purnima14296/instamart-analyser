"""Reddit discussion connector with PullPush archive fallback."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import requests

from instamart_analyser.common.config import (
    REDDIT_SEARCH_QUERIES,
    REDDIT_SUBREDDITS,
    USER_AGENT,
)
from instamart_analyser.common.models import ConnectorResult, FeedbackRecord
from instamart_analyser.phases.phase_1.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

REDDIT_BASE = "https://old.reddit.com"
REDDIT_OAUTH_BASE = "https://oauth.reddit.com"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
PULLPUSH_URL = "https://api.pullpush.io/reddit/search/submission/"

# Subreddits that are Instamart-focused; posts count even without the keyword.
INSTAMART_FOCUSED_SUBREDDITS = {"swiggyinstamart"}


class RedditBlockedError(Exception):
    """Raised when Reddit blocks unauthenticated API access."""


class RedditConnector(BaseConnector):
    source = "reddit"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._oauth_token: str | None = None

    def collect(self) -> ConnectorResult:
        records: list[FeedbackRecord] = []
        seen_ids: set[str] = set()
        errors: list[str] = []
        fetched_count = 0
        blocked = False

        # Prefer dedicated Instamart community listings first.
        for subreddit in REDDIT_SUBREDDITS:
            if subreddit.lower() not in INSTAMART_FOCUSED_SUBREDDITS:
                continue
            if blocked or self._at_limit(records):
                break
            try:
                posts = self._list_subreddit(subreddit, sort="new")
                fetched_count += len(posts)
                self._append_posts(
                    posts,
                    records,
                    seen_ids,
                    subreddit=subreddit,
                    query="listing:new",
                    allow_subreddit_default=True,
                )
            except RedditBlockedError:
                blocked = True
                break
            except requests.RequestException as exc:
                errors.append(f"r/{subreddit} listing: {exc}")

        for subreddit in REDDIT_SUBREDDITS:
            if blocked or self._at_limit(records):
                break
            for query in REDDIT_SEARCH_QUERIES:
                if blocked or self._at_limit(records):
                    break
                try:
                    posts = self._search_reddit(subreddit, query)
                except RedditBlockedError:
                    blocked = True
                    break
                except requests.RequestException as exc:
                    errors.append(f"r/{subreddit} q={query}: {exc}")
                    continue

                fetched_count += len(posts)
                self._append_posts(
                    posts,
                    records,
                    seen_ids,
                    subreddit,
                    query,
                    allow_subreddit_default=subreddit.lower() in INSTAMART_FOCUSED_SUBREDDITS,
                )

        if blocked or not records:
            logger.info("Fetching Reddit posts via PullPush archive API")
            pullpush_posts, pp_errors = self._search_pullpush()
            errors.extend(pp_errors)
            fetched_count += len(pullpush_posts)
            self._append_posts(pullpush_posts, records, seen_ids, source_label="pullpush")

        if blocked:
            errors.append(
                "Reddit direct API blocked (403). Used PullPush archive as fallback."
            )

        logger.info(
            "Reddit: scanned %d posts, matched %d",
            fetched_count,
            len(records),
        )

        limited = records[: self.max_records] if self.max_records else records
        return ConnectorResult(
            source=self.source,
            records=limited,
            fetched_count=fetched_count,
            filtered_count=len(limited),
            errors=errors,
            retries=0,
        )

    def _at_limit(self, records: list[FeedbackRecord]) -> bool:
        return bool(self.max_records) and len(records) >= self.max_records

    def _append_posts(
        self,
        posts: list[dict[str, Any]],
        records: list[FeedbackRecord],
        seen_ids: set[str],
        subreddit: str = "",
        query: str = "",
        source_label: str = "reddit",
        allow_subreddit_default: bool = False,
    ) -> None:
        for post in posts:
            if self._at_limit(records):
                break
            post_id = post.get("id", "")
            if not post_id or post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            title = post.get("title", "")
            body = post.get("selftext", "") or ""
            combined = f"{title}\n{body}".strip()
            post_sub = (subreddit or post.get("subreddit", "") or "").lower()
            is_focused = allow_subreddit_default or post_sub in INSTAMART_FOCUSED_SUBREDDITS
            if not combined:
                continue
            if not is_focused and not self.matches_instamart_keywords(combined):
                continue
            if is_focused and len(combined.split()) < 3:
                continue

            created = post.get("created_utc")
            timestamp = None
            if created:
                timestamp = (
                    datetime.fromtimestamp(created, tz=timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                )

            permalink = post.get("permalink", "")
            url = None
            if permalink:
                url = permalink if permalink.startswith("http") else f"https://www.reddit.com{permalink}"

            # Keep Instamart mention for downstream filters when post comes from focused subreddit.
            body_text = combined
            if is_focused and not self.matches_instamart_keywords(combined):
                body_text = f"Instamart discussion from r/{post_sub}: {combined}"

            records.append(
                FeedbackRecord(
                    source=self.source,
                    source_record_id=post_id,
                    body_text=body_text,
                    language=self.detect_language(combined),
                    collection_batch_id=self.batch_id,
                    url=url,
                    author=post.get("author"),
                    timestamp=timestamp,
                    title=title,
                    metadata={
                        "subreddit": subreddit or post.get("subreddit", ""),
                        "query": query,
                        "score": post.get("score"),
                        "num_comments": post.get("num_comments"),
                        "fetch_source": source_label,
                        "instamart_focused_subreddit": is_focused,
                    },
                )
            )

    def _auth_headers(self) -> dict[str, str]:
        token = self._get_oauth_token()
        if token:
            return {
                "User-Agent": USER_AGENT,
                "Authorization": f"Bearer {token}",
            }
        return {"User-Agent": USER_AGENT}

    def _get_oauth_token(self) -> str | None:
        if self._oauth_token:
            return self._oauth_token
        client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            return None
        try:
            response = requests.post(
                REDDIT_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            response.raise_for_status()
            self._oauth_token = response.json().get("access_token")
            return self._oauth_token
        except requests.RequestException as exc:
            logger.warning("Reddit OAuth failed: %s", exc)
            return None

    def _list_subreddit(self, subreddit: str, sort: str = "new") -> list[dict[str, Any]]:
        limit = min(100, self.max_records) if self.max_records else 100
        headers = self._auth_headers()
        if "Authorization" in headers:
            url = f"{REDDIT_OAUTH_BASE}/r/{subreddit}/{sort}?limit={limit}"
        else:
            url = f"{REDDIT_BASE}/r/{subreddit}/{sort}.json?limit={limit}"
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 403:
            raise RedditBlockedError("Reddit returned 403")
        response.raise_for_status()
        children = response.json().get("data", {}).get("children", [])
        return [child.get("data", {}) for child in children if child.get("kind") == "t3"]

    def _search_reddit(self, subreddit: str, query: str) -> list[dict[str, Any]]:
        limit = min(50, self.max_records) if self.max_records else 50
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "relevance",
            "limit": limit,
            "t": "year",
        }
        headers = self._auth_headers()
        if "Authorization" in headers:
            url = f"{REDDIT_OAUTH_BASE}/r/{subreddit}/search?{urlencode(params)}"
        else:
            url = f"{REDDIT_BASE}/r/{subreddit}/search.json?{urlencode(params)}"
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 403:
            raise RedditBlockedError("Reddit returned 403")
        response.raise_for_status()
        children = response.json().get("data", {}).get("children", [])
        return [child.get("data", {}) for child in children if child.get("kind") == "t3"]

    def _search_pullpush(self) -> tuple[list[dict[str, Any]], list[str]]:
        posts: list[dict[str, Any]] = []
        errors: list[str] = []
        seen: set[str] = set()

        for subreddit in REDDIT_SUBREDDITS:
            queries = (
                ["*"] + REDDIT_SEARCH_QUERIES
                if subreddit.lower() in INSTAMART_FOCUSED_SUBREDDITS
                else REDDIT_SEARCH_QUERIES
            )
            for query in queries:
                try:
                    params: dict[str, Any] = {
                        "subreddit": subreddit,
                        "size": 100,
                        "sort": "desc",
                        "sort_type": "created_utc",
                    }
                    if query != "*":
                        params["q"] = query
                    response = requests.get(PULLPUSH_URL, params=params, timeout=30)
                    response.raise_for_status()
                    for post in response.json().get("data", []):
                        pid = post.get("id", "")
                        if pid and pid not in seen:
                            seen.add(pid)
                            posts.append(post)
                except requests.RequestException as exc:
                    errors.append(f"PullPush r/{subreddit} q={query}: {exc}")

        return posts, errors
