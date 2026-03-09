"""SMS extractor — uses ALL discovered v2 API endpoints for SMS data.

Confirmed v2 endpoints (10):
  GET /v2/sms/campaign?applicationId=X                              → list campaigns
  GET /v2/sms/campaign/{id}                                         → campaign detail
  GET /v2/sms/send?applicationId=X&limit=N&page=P                  → list sendings (8.6M)
  GET /v2/sms/send/{id}                                             → sending detail + campaignSnapshot
  GET /v2/sms/stats/campaign?applicationId=X&dateFrom=Y&dateTo=Z   → daily stats per campaign (max 99d)
  GET /v2/sms/stats/campaign/{campaignId}?applicationId=X           → full history per campaign (no date limit)
  GET /v2/sms/stats/application?applicationId=X&dateFrom=Y&dateTo=Z → daily aggregate stats (max 99d)
  GET /v2/sms/contact?applicationId=X&limit=N&page=P               → SMS contacts (413K)
  GET /v2/sms/contact/{id}                                          → contact detail
  GET /v2/sms/topic?applicationId=X                                 → subscription topics

Incremental mode:
  - sms_sendings cursor: ISO date of last extraction → only fetch page 1..N until
    we hit records older than cursor (API returns newest first)
  - stats: re-extract last 7 days only (overlap for late data)
  - contacts: always full (small, ~4 min)
  - campaigns: always full (tiny)
"""

from datetime import date, timedelta

from scripts.extractors.base_extractor import BaseExtractor

MAX_STATS_WINDOW_DAYS = 99
INCREMENTAL_STATS_DAYS = 7  # Only re-extract last 7 days of stats in incremental mode


class SMSExtractor(BaseExtractor):
    CHANNEL_NAME = "sms"
    RAW_TABLE = "raw.raw_sms_stats"

    def _extract_for_app(self, app_id: str, app_meta: dict):
        campaign_ids = self._extract_campaigns(app_id)
        self._extract_app_stats(app_id)
        self._extract_campaign_stats_list(app_id)
        self._extract_campaign_stats_detail(app_id, campaign_ids)
        self._extract_sendings(app_id)
        self._extract_contacts(app_id)
        self._extract_topics(app_id)

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    def _extract_campaigns(self, app_id: str) -> list[int]:
        """GET /v2/sms/campaign — list all SMS campaigns. Returns campaign IDs."""
        data = self.client.get(
            "/v2/sms/campaign",
            params={"applicationId": app_id},
            application_id=app_id,
        )
        if data is None:
            print("    sms/campaign: not available")
            return []

        self._store_raw(app_id, "/v2/sms/campaign", data)
        campaigns = data.get("data", {}).get("campaigns", [])
        count = data.get("count", len(campaigns))
        print(f"    sms/campaign: {count} campaigns")
        return [c["id"] for c in campaigns if "id" in c]

    # ------------------------------------------------------------------
    # Stats — aggregated
    # ------------------------------------------------------------------

    def _extract_campaign_stats_list(self, app_id: str):
        """GET /v2/sms/stats/campaign — daily stats per campaign (date-ranged, max 99d)."""
        for start, end in self._date_windows():
            data = self.client.get(
                "/v2/sms/stats/campaign",
                params={
                    "applicationId": app_id,
                    "dateFrom": start.isoformat(),
                    "dateTo": end.isoformat(),
                },
                application_id=app_id,
            )
            if data is None:
                print("    sms/stats/campaign: not available")
                return
            self._store_raw(app_id, "/v2/sms/stats/campaign", data)

        rows = data.get("data", []) if data else []
        print(f"    sms/stats/campaign: {len(rows)} rows (last window)")

    def _extract_campaign_stats_detail(self, app_id: str, campaign_ids: list[int]):
        """GET /v2/sms/stats/campaign/{id} — full history per campaign (no date limit)."""
        total_rows = 0
        for cid in campaign_ids:
            data = self.client.get(
                f"/v2/sms/stats/campaign/{cid}",
                params={"applicationId": app_id},
                application_id=app_id,
            )
            if data is None:
                continue
            rows = data.get("data", [])
            total_rows += len(rows)
            self._store_raw(app_id, f"/v2/sms/stats/campaign/{cid}", data)

        print(f"    sms/stats/campaign/{{id}}: {total_rows} rows across {len(campaign_ids)} campaigns")

    def _extract_app_stats(self, app_id: str):
        """GET /v2/sms/stats/application — daily aggregate stats.

        Incremental: only re-extract last 7 days of stats.
        """
        # Incremental: narrow the date range for stats
        stats_from = self.date_from
        cursor = self._get_cursor("sms_stats")
        if cursor and not self.full_refresh:
            try:
                cursor_date = date.fromisoformat(cursor)
                stats_from = cursor_date - timedelta(days=INCREMENTAL_STATS_DAYS)
                if stats_from < self.date_from:
                    stats_from = self.date_from
                print(f"    sms/stats: incremental from {stats_from}")
            except ValueError:
                pass

        total_rows = 0
        for start, end in self._date_windows(override_from=stats_from):
            data = self.client.get(
                "/v2/sms/stats/application",
                params={
                    "applicationId": app_id,
                    "dateFrom": start.isoformat(),
                    "dateTo": end.isoformat(),
                },
                application_id=app_id,
            )
            if data is None:
                print("    sms/stats/application: not available")
                return
            rows = data.get("data", [])
            total_rows += len(rows)
            self._store_raw(app_id, "/v2/sms/stats/application", data)

        self._update_cursor("sms_stats", self.date_to.isoformat())
        print(f"    sms/stats/application: {total_rows} daily rows")

    # ------------------------------------------------------------------
    # Sendings (messages dispatched) — FULL extraction, no cap
    # ------------------------------------------------------------------

    def _extract_sendings(self, app_id: str):
        """GET /v2/sms/send — paginated sendings.

        Full mode: fetches ALL sendings (page_size=1000).
        Incremental mode: fetches newest pages until we hit records older than cursor.
        The API returns newest sendings first (sorted by sentAt DESC).
        """
        page = 1
        page_size = 1000  # v2 API accepts up to 1000
        total_fetched = 0
        api_total = 0

        # Incremental: stop when we hit old records
        cutoff_date = None
        cursor = self._get_cursor("sms_sendings")
        if cursor and not self.full_refresh:
            try:
                cutoff_date = date.fromisoformat(cursor)
                # 1-day overlap for late-arriving records
                cutoff_date = cutoff_date - timedelta(days=1)
                print(f"    sms/send: incremental, cutoff={cutoff_date}")
            except ValueError:
                pass

        while True:
            data = self.client.get(
                "/v2/sms/send",
                params={
                    "applicationId": app_id,
                    "limit": page_size,
                    "page": page,
                },
                application_id=app_id,
            )
            if data is None:
                print("    sms/send: not available")
                return

            sendings = data.get("data", {}).get("sendings", [])
            if not sendings:
                break

            api_total = data.get("count", api_total)
            self._store_raw(app_id, "/v2/sms/send", data)
            total_fetched += len(sendings)
            page += 1

            if total_fetched % 50000 == 0:
                print(f"    sms/send: {total_fetched:,} / {api_total:,} fetched...")

            # Incremental: check if oldest record in this page is before cutoff
            if cutoff_date:
                oldest_sent = sendings[-1].get("sentAt", "")
                if oldest_sent:
                    try:
                        oldest_date = date.fromisoformat(oldest_sent[:10])
                        if oldest_date < cutoff_date:
                            print(f"    sms/send: reached cutoff ({oldest_date} < {cutoff_date})")
                            break
                    except ValueError:
                        pass

            if len(sendings) < page_size:
                break

        # Save cursor for next incremental run
        self._update_cursor("sms_sendings", self.date_to.isoformat())
        print(f"    sms/send: {total_fetched:,} fetched (API total: {api_total:,})")

    # ------------------------------------------------------------------
    # Contacts — FULL extraction, no cap
    # ------------------------------------------------------------------

    def _extract_contacts(self, app_id: str):
        """GET /v2/sms/contact — paginated SMS contacts.

        In incremental mode, only fetches first few pages (new contacts appear first).
        In full mode, fetches ALL contacts.
        """
        page = 1
        page_size = 1000
        total_fetched = 0
        api_total = 0

        # Incremental: limit to first 10 pages (~10K newest contacts)
        max_pages = None
        cursor = self._get_cursor("sms_contacts")
        if cursor and not self.full_refresh:
            max_pages = 10
            print(f"    sms/contact: incremental (max {max_pages} pages of new contacts)")

        while True:
            if max_pages and page > max_pages:
                break

            data = self.client.get(
                "/v2/sms/contact",
                params={
                    "applicationId": app_id,
                    "limit": page_size,
                    "page": page,
                },
                application_id=app_id,
            )
            if data is None:
                print("    sms/contact: not available")
                return

            contacts = data.get("data", {}).get("contacts", [])
            if not contacts:
                break

            api_total = data.get("count", api_total)
            self._store_raw(app_id, "/v2/sms/contact", data)
            total_fetched += len(contacts)
            page += 1

            if total_fetched % 10000 == 0:
                print(f"    sms/contact: {total_fetched:,} / {api_total:,} fetched...")

            if len(contacts) < page_size:
                break

        self._update_cursor("sms_contacts", self.date_to.isoformat())
        print(f"    sms/contact: {total_fetched:,} fetched (API total: {api_total:,})")

    # ------------------------------------------------------------------
    # Topics
    # ------------------------------------------------------------------

    def _extract_topics(self, app_id: str):
        """GET /v2/sms/topic — subscription topics/categories."""
        data = self.client.get(
            "/v2/sms/topic",
            params={"applicationId": app_id},
            application_id=app_id,
        )
        if data is not None:
            self._store_raw(app_id, "/v2/sms/topic", data)
            count = data.get("count", 0)
            print(f"    sms/topic: {count} topics")
        else:
            print("    sms/topic: not available")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _date_windows(self, override_from: date | None = None):
        """Yield (start, end) date tuples in <=99-day windows covering the extraction range."""
        current = override_from or self.date_from
        while current < self.date_to:
            window_end = min(current + timedelta(days=MAX_STATS_WINDOW_DAYS - 1), self.date_to)
            yield current, window_end
            current = window_end + timedelta(days=1)
