"""Selenium-based Reddit scroll scraper for Instamart communities."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from instamart_analyser.common.models import ConnectorResult, FeedbackRecord
from instamart_analyser.phases.phase_1.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = ["swiggyinstamart"]
DEFAULT_SORTS = ("new", "hot", "top", "rising")


class RedditSeleniumConnector(BaseConnector):
    """Use a real Chrome browser to collect Reddit posts when HTTP APIs are blocked."""

    source = "reddit"

    def __init__(
        self,
        batch_id: str,
        max_records: int = 500,
        lookback_days: int = 3650,
        *,
        subreddits: list[str] | None = None,
        max_scrolls: int = 40,
        headless: bool = True,
        pause_seconds: float = 1.2,
        include_comments: bool = True,
        sorts: list[str] | None = None,
        max_pages_per_sort: int = 50,
        comment_limit: int = 500,
    ) -> None:
        super().__init__(batch_id=batch_id, max_records=max_records, lookback_days=lookback_days)
        self.subreddits = subreddits or DEFAULT_SUBREDDITS
        self.max_scrolls = max_scrolls
        self.headless = headless
        self.pause_seconds = pause_seconds
        self.include_comments = include_comments
        self.sorts = sorts or list(DEFAULT_SORTS)
        self.max_pages_per_sort = max_pages_per_sort
        self.comment_limit = comment_limit

    def collect(self) -> ConnectorResult:
        records: list[FeedbackRecord] = []
        errors: list[str] = []
        seen_ids: set[str] = set()
        fetched_count = 0

        try:
            driver = self._build_driver()
        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(
                source=self.source,
                records=[],
                fetched_count=0,
                filtered_count=0,
                errors=[f"Selenium driver failed: {exc}"],
                retries=0,
            )

        try:
            for subreddit in self.subreddits:
                if self.max_records and len(records) >= self.max_records:
                    break
                try:
                    items = self._collect_subreddit(driver, subreddit)
                    fetched_count += len(items)
                    for item in items:
                        if self.max_records and len(records) >= self.max_records:
                            break
                        item_id = str(item.get("id") or "")
                        if not item_id or item_id in seen_ids:
                            continue
                        seen_ids.add(item_id)
                        record = self._to_record(item, subreddit)
                        if record:
                            records.append(record)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"r/{subreddit}: {exc}")
                    logger.exception("Selenium scrape failed for r/%s", subreddit)
        finally:
            try:
                driver.quit()
            except Exception:  # noqa: BLE001
                pass

        logger.info(
            "Reddit Selenium: scanned %d items, kept %d from %s",
            fetched_count,
            len(records),
            ", ".join(self.subreddits),
        )
        return ConnectorResult(
            source=self.source,
            records=records,
            fetched_count=fetched_count,
            filtered_count=len(records),
            errors=errors,
            retries=0,
        )

    def _build_driver(self) -> Any:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1400,2200")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            },
        )
        return driver

    def _collect_subreddit(self, driver: Any, subreddit: str) -> list[dict[str, Any]]:
        driver.set_page_load_timeout(90)
        driver.set_script_timeout(30)

        # Warm HTML feed so Reddit JS challenge / cookies settle.
        page_url = f"https://www.reddit.com/r/{subreddit}/new/"
        logger.info("Opening HTML feed %s", page_url)
        driver.get(page_url)
        time.sleep(4)
        logger.info("Page title after load: %s", (driver.title or "")[:120])
        self._dismiss_consent_if_present(driver)

        posts_by_id: dict[str, dict[str, Any]] = {}
        for sort in self.sorts:
            listing = self._fetch_listing_by_navigation(driver, subreddit, sort=sort)
            for post in listing:
                posts_by_id[post["id"]] = post
            logger.info(
                "After sort=%s unique posts=%d for r/%s",
                sort,
                len(posts_by_id),
                subreddit,
            )

        if not posts_by_id:
            logger.info("JSON listings empty; falling back to DOM scroll for r/%s", subreddit)
            driver.get(page_url)
            time.sleep(3)
            self._dismiss_consent_if_present(driver)
            for post in self._scroll_dom_posts(driver, subreddit):
                posts_by_id[post["id"]] = post

        posts = list(posts_by_id.values())
        logger.info("Listing complete: %d unique posts for r/%s", len(posts), subreddit)

        if not self.include_comments:
            return posts

        items: list[dict[str, Any]] = []
        for idx, post in enumerate(posts, start=1):
            logger.info(
                "Expanding thread %d/%d id=%s title=%s",
                idx,
                len(posts),
                post.get("id"),
                (post.get("title") or "")[:80],
            )
            thread_items = self._expand_thread(driver, subreddit, post)
            items.extend(thread_items)
            time.sleep(0.7)
            if self.max_records and len(items) >= self.max_records:
                break
        return items

    def _fetch_listing_by_navigation(
        self,
        driver: Any,
        subreddit: str,
        *,
        sort: str,
    ) -> list[dict[str, Any]]:
        posts: list[dict[str, Any]] = []
        after: str | None = None
        limit = 100
        seen_page_tokens: set[str] = set()

        for page_idx in range(self.max_pages_per_sort):
            path = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}&raw_json=1"
            if sort == "top":
                path += "&t=all"
            if after:
                path += f"&after={after}"
            logger.info("Navigating %s page %d: %s", sort, page_idx + 1, path)
            payload = self._load_json_page(driver, path)
            if not payload:
                break

            children = payload.get("data", {}).get("children", [])
            after = payload.get("data", {}).get("after")
            if after and after in seen_page_tokens:
                logger.info("Pagination loop detected for sort=%s; stopping", sort)
                break
            if after:
                seen_page_tokens.add(after)

            for child in children:
                parsed = self._from_api_post(child.get("data", {}), subreddit)
                if parsed:
                    posts.append(parsed)

            logger.info(
                "%s page %d — cumulative listing posts=%d after=%s",
                sort,
                page_idx + 1,
                len(posts),
                after,
            )
            if not after:
                break
            if self.max_records and len(posts) >= self.max_records:
                break
            time.sleep(0.8)
        return posts

    def _expand_thread(
        self,
        driver: Any,
        subreddit: str,
        post: dict[str, Any],
    ) -> list[dict[str, Any]]:
        post_id = post.get("id")
        if not post_id:
            return []

        path = (
            f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
            f"?limit={self.comment_limit}&depth=10&raw_json=1"
        )
        payload = self._load_json_page(driver, path)
        if not payload or not isinstance(payload, list) or len(payload) < 1:
            logger.warning("Thread JSON missing for %s; keeping listing post only", post_id)
            return [{**post, "kind": "post"}]

        listing = payload[0].get("data", {}).get("children", [])
        items: list[dict[str, Any]] = []
        if listing:
            enriched = self._from_api_post(listing[0].get("data", {}), subreddit)
            if enriched:
                enriched["kind"] = "post"
                items.append(enriched)
            else:
                items.append({**post, "kind": "post"})
        else:
            items.append({**post, "kind": "post"})

        if len(payload) >= 2:
            comments_root = payload[1].get("data", {}).get("children", [])
            self._flatten_comments(
                comments_root,
                subreddit=subreddit,
                post_id=str(post_id),
                post_title=post.get("title") or "",
                post_url=post.get("url") or "",
                out=items,
            )

        # Follow "more" comment IDs via Reddit morechildren when present.
        more_ids = [c for c in items if c.get("_more_ids")]
        for more in more_ids:
            ids = more.pop("_more_ids", []) or []
            for chunk_start in range(0, min(len(ids), 100), 100):
                chunk = ids[chunk_start : chunk_start + 100]
                more_items = self._fetch_more_children(
                    driver,
                    subreddit=subreddit,
                    post_fullname=f"t3_{post_id}",
                    children=chunk,
                    post_title=post.get("title") or "",
                    post_url=post.get("url") or "",
                )
                items.extend(more_items)

        items = [i for i in items if not i.get("_more_ids")]
        logger.info(
            "Thread %s expanded to %d items (post+comments)",
            post_id,
            len(items),
        )
        return items

    def _fetch_more_children(
        self,
        driver: Any,
        *,
        subreddit: str,
        post_fullname: str,
        children: list[str],
        post_title: str,
        post_url: str,
    ) -> list[dict[str, Any]]:
        if not children:
            return []
        # Reddit morechildren is POST; use browser fetch in-page after warm session.
        script = """
            const done = arguments[arguments.length - 1];
            const linkId = arguments[0];
            const children = arguments[1];
            const body = new URLSearchParams();
            body.set('api_type', 'json');
            body.set('link_id', linkId);
            body.set('children', children.join(','));
            body.set('limit_children', 'False');
            fetch('https://www.reddit.com/api/morechildren.json', {
              method: 'POST',
              credentials: 'include',
              headers: {'Content-Type': 'application/x-www-form-urlencoded'},
              body: body.toString()
            })
              .then(r => r.json().then(j => done({ok: r.ok, status: r.status, json: j})))
              .catch(e => done({ok: false, status: 0, error: String(e)}));
        """
        try:
            driver.set_script_timeout(40)
            result = driver.execute_async_script(script, post_fullname, children)
        except Exception as exc:  # noqa: BLE001
            logger.warning("morechildren fetch failed: %s", exc)
            return []
        if not result or not result.get("ok"):
            logger.warning(
                "morechildren failed status=%s error=%s",
                (result or {}).get("status"),
                (result or {}).get("error"),
            )
            return []

        things = (
            result.get("json", {})
            .get("json", {})
            .get("data", {})
            .get("things", [])
        )
        out: list[dict[str, Any]] = []
        for thing in things:
            if thing.get("kind") != "t1":
                continue
            parsed = self._from_api_comment(
                thing.get("data", {}),
                subreddit=subreddit,
                post_id=post_fullname.replace("t3_", ""),
                post_title=post_title,
                post_url=post_url,
            )
            if parsed:
                out.append(parsed)
        return out

    def _flatten_comments(
        self,
        children: list[dict[str, Any]],
        *,
        subreddit: str,
        post_id: str,
        post_title: str,
        post_url: str,
        out: list[dict[str, Any]],
    ) -> None:
        for child in children or []:
            kind = child.get("kind")
            data = child.get("data", {}) or {}
            if kind == "more":
                ids = data.get("children") or []
                if ids:
                    out.append({"_more_ids": ids, "id": f"more_{post_id}_{len(out)}"})
                continue
            if kind != "t1":
                continue
            parsed = self._from_api_comment(
                data,
                subreddit=subreddit,
                post_id=post_id,
                post_title=post_title,
                post_url=post_url,
            )
            if parsed:
                out.append(parsed)
            replies = data.get("replies")
            if isinstance(replies, dict):
                nested = replies.get("data", {}).get("children", [])
                self._flatten_comments(
                    nested,
                    subreddit=subreddit,
                    post_id=post_id,
                    post_title=post_title,
                    post_url=post_url,
                    out=out,
                )

    def _load_json_page(self, driver: Any, path: str) -> Any | None:
        try:
            driver.get(path)
            time.sleep(2.2)
            body = ""
            try:
                pre = driver.find_elements("css selector", "pre")
                if pre:
                    body = pre[0].text.strip()
            except Exception:  # noqa: BLE001
                body = ""
            if not body:
                body = driver.find_element("tag name", "body").text.strip()
            if not (body.startswith("{") or body.startswith("[")):
                src = driver.page_source or ""
                start_obj = src.find("{")
                start_arr = src.find("[")
                candidates = [i for i in (start_obj, start_arr) if i >= 0]
                if not candidates:
                    logger.warning("JSON page did not return JSON (title=%s)", driver.title)
                    return None
                start = min(candidates)
                end = max(src.rfind("}"), src.rfind("]"))
                if end <= start:
                    logger.warning("JSON page malformed (title=%s)", driver.title)
                    return None
                body = src[start : end + 1]
            return json.loads(body)
        except Exception as exc:  # noqa: BLE001
            logger.warning("JSON navigation failed for %s: %s", path, exc)
            return None

    def _dismiss_consent_if_present(self, driver: Any) -> None:
        from selenium.webdriver.common.by import By

        candidates = [
            "button[button-name='Accept']",
            "button.accept-all",
            "#accept-all-cookies-button",
            "button[aria-label*='Accept']",
        ]
        for selector in candidates:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons:
                    buttons[0].click()
                    time.sleep(1)
                    return
            except Exception:  # noqa: BLE001
                continue

    def _scroll_dom_posts(self, driver: Any, subreddit: str) -> list[dict[str, Any]]:
        from selenium.webdriver.common.by import By

        posts_by_id: dict[str, dict[str, Any]] = {}
        stagnant = 0
        for scroll_idx in range(self.max_scrolls):
            before = len(posts_by_id)

            for el in driver.find_elements(By.CSS_SELECTOR, "shreddit-post"):
                parsed = self._from_shreddit_el(el, subreddit)
                if parsed:
                    posts_by_id[parsed["id"]] = parsed

            for el in driver.find_elements(By.CSS_SELECTOR, "div.thing.link"):
                parsed = self._from_old_thing(el, subreddit)
                if parsed:
                    posts_by_id[parsed["id"]] = parsed

            after = len(posts_by_id)
            logger.info(
                "DOM scroll %d/%d — posts: %d title=%s",
                scroll_idx + 1,
                self.max_scrolls,
                after,
                (driver.title or "")[:60],
            )
            if self.max_records and after >= self.max_records:
                break
            if after == before:
                stagnant += 1
                if stagnant >= 4:
                    break
            else:
                stagnant = 0

            self._click_load_more(driver)
            driver.execute_script(
                """
                const posts = document.querySelectorAll('shreddit-post, div.thing.link');
                if (posts.length) {
                  posts[posts.length - 1].scrollIntoView({block: 'end'});
                }
                window.scrollBy(0, Math.max(900, window.innerHeight));
                """
            )
            time.sleep(self.pause_seconds + 0.6)
        return list(posts_by_id.values())

    def _click_load_more(self, driver: Any) -> None:
        from selenium.webdriver.common.by import By

        try:
            for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
                label = ((btn.text or "") + " " + (btn.get_attribute("aria-label") or "")).lower()
                if "view more" in label or "load more" in label or "more posts" in label:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1.2)
                        return
                    except Exception:  # noqa: BLE001
                        continue
        except Exception:  # noqa: BLE001
            pass

    def _from_api_post(self, data: dict[str, Any], subreddit: str) -> dict[str, Any] | None:
        post_id = data.get("id")
        if not post_id:
            return None
        title = data.get("title") or ""
        body = data.get("selftext") or ""
        created = data.get("created_utc")
        timestamp = None
        if created:
            timestamp = datetime.fromtimestamp(created, tz=timezone.utc).replace(microsecond=0).isoformat()
        permalink = data.get("permalink") or ""
        url = permalink if str(permalink).startswith("http") else f"https://www.reddit.com{permalink}"
        return {
            "id": post_id,
            "kind": "post",
            "title": title,
            "body": body,
            "author": data.get("author"),
            "score": data.get("score"),
            "num_comments": data.get("num_comments"),
            "timestamp": timestamp,
            "url": url,
            "subreddit": subreddit,
        }

    def _from_api_comment(
        self,
        data: dict[str, Any],
        *,
        subreddit: str,
        post_id: str,
        post_title: str,
        post_url: str,
    ) -> dict[str, Any] | None:
        comment_id = data.get("id")
        body = (data.get("body") or "").strip()
        if not comment_id or not body or body in {"[deleted]", "[removed]"}:
            return None
        created = data.get("created_utc")
        timestamp = None
        if created:
            timestamp = datetime.fromtimestamp(created, tz=timezone.utc).replace(microsecond=0).isoformat()
        permalink = data.get("permalink") or ""
        url = permalink if str(permalink).startswith("http") else f"https://www.reddit.com{permalink}"
        return {
            "id": f"c_{comment_id}",
            "kind": "comment",
            "title": f"Comment on: {post_title}" if post_title else "Comment",
            "body": body,
            "author": data.get("author"),
            "score": data.get("score"),
            "num_comments": None,
            "timestamp": timestamp,
            "url": url or post_url,
            "subreddit": subreddit,
            "parent_post_id": post_id,
        }

    def _from_shreddit_el(self, el: Any, subreddit: str) -> dict[str, Any] | None:
        try:
            post_id = (el.get_attribute("id") or "").replace("t3_", "").strip()
            if not post_id:
                return None
            title = el.get_attribute("post-title") or ""
            author = el.get_attribute("author")
            permalink = el.get_attribute("permalink") or ""
            score = el.get_attribute("score") or "0"
            comments = el.get_attribute("comment-count") or "0"
            created = el.get_attribute("created-timestamp")
            timestamp = None
            if created:
                try:
                    if created.isdigit():
                        timestamp = datetime.fromtimestamp(int(created), tz=timezone.utc).replace(
                            microsecond=0
                        ).isoformat()
                    else:
                        timestamp = created
                except Exception:  # noqa: BLE001
                    timestamp = created
            body = ""
            try:
                body_els = el.find_elements(
                    "css selector",
                    "[slot='text-body'], div[data-post-click-location='text-body']",
                )
                if body_els:
                    body = body_els[0].text.strip()
            except Exception:  # noqa: BLE001
                body = ""
            url = permalink if permalink.startswith("http") else f"https://www.reddit.com{permalink}"
            return {
                "id": post_id,
                "kind": "post",
                "title": title.strip(),
                "body": body,
                "author": author,
                "score": int(score) if str(score).isdigit() else 0,
                "num_comments": int(comments) if str(comments).isdigit() else 0,
                "timestamp": timestamp,
                "url": url,
                "subreddit": subreddit,
            }
        except Exception:  # noqa: BLE001
            return None

    def _from_old_thing(self, el: Any, subreddit: str) -> dict[str, Any] | None:
        import re
        from urllib.parse import urljoin

        try:
            fullname = (el.get_attribute("data-fullname") or "").strip()
            match = re.search(r"t3_([a-z0-9]+)", fullname, re.I)
            post_id = match.group(1) if match else ""
            if not post_id:
                return None
            title_el = el.find_elements("css selector", "a.title")
            title = title_el[0].text.strip() if title_el else ""
            body = ""
            body_els = el.find_elements("css selector", "div.usertext-body .md")
            if body_els:
                body = body_els[0].text.strip()
            author_els = el.find_elements("css selector", "a.author")
            author = author_els[0].text.strip() if author_els else None
            permalink = el.get_attribute("data-permalink") or ""
            if permalink.startswith("/"):
                permalink = urljoin("https://www.reddit.com", permalink)
            ts_raw = el.get_attribute("data-timestamp")
            timestamp = None
            if ts_raw and ts_raw.isdigit():
                timestamp = datetime.fromtimestamp(int(ts_raw) / 1000, tz=timezone.utc).replace(
                    microsecond=0
                ).isoformat()
            return {
                "id": post_id,
                "kind": "post",
                "title": title,
                "body": body,
                "author": author,
                "score": int(el.get_attribute("data-score") or 0),
                "num_comments": int(el.get_attribute("data-comments-count") or 0),
                "timestamp": timestamp,
                "url": permalink,
                "subreddit": subreddit,
            }
        except Exception:  # noqa: BLE001
            return None

    def _to_record(self, item: dict[str, Any], subreddit: str) -> FeedbackRecord | None:
        title = item.get("title") or ""
        body = item.get("body") or ""
        kind = item.get("kind") or "post"
        if kind == "comment":
            combined = f"{title}\n{body}".strip()
        else:
            combined = f"{title}\n{body}".strip()
        if len(combined.split()) < 3:
            return None
        if not self.matches_instamart_keywords(combined):
            combined = f"Instamart discussion from r/{subreddit}: {combined}"
        return FeedbackRecord(
            source=self.source,
            source_record_id=str(item["id"]),
            body_text=combined,
            language=self.detect_language(combined),
            collection_batch_id=self.batch_id,
            url=item.get("url"),
            author=item.get("author"),
            timestamp=item.get("timestamp"),
            title=title,
            metadata={
                "subreddit": subreddit,
                "score": item.get("score"),
                "num_comments": item.get("num_comments"),
                "fetch_source": "selenium_browser_full",
                "instamart_focused_subreddit": True,
                "kind": kind,
                "parent_post_id": item.get("parent_post_id"),
            },
        )
