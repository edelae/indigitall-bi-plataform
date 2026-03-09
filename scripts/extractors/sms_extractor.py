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
"""

from datetime import timedelta

from scripts.extractors.base_extractor import BaseExtractor

MAX_STATS_WINDOW_DAYS = 99


class SMSExtractor(BaseExtractor):
    CHANNEL_NAME = "sms"
    RAW_TABLE = "raw.raw_sms_stats"

    def _extract_for_app(self, app_id: str, app_meta: dict):
        campaign_ids = self._extract_campaigns(app_id)
        self._extract_campaign_stats_list(app_id)
        self._extract_campaign_stats_detail(app_id, campaign_ids)
        self._extract_app_stats(app_id)
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
        """GET /v2/sms/stats/application — daily aggregate stats (max 99d windows)."""
        total_rows = 0
        for start, end in self._date_windows():
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

        print(f"    sms/stats/application: {total_rows} daily rows")

    # ------------------------------------------------------------------
    # Sendings (messages dispatched) — FULL extraction, no cap
    # ------------------------------------------------------------------

    def _extract_sendings(self, app_id: str):
        """GET /v2/sms/send — paginated list of ALL sendings."""
        page = 1
        page_size = 100
        total_fetched = 0
        api_total = 0

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

            if total_fetched % 10000 == 0:
                print(f"    sms/send: {total_fetched:,} / {api_total:,} fetched...")

            if len(sendings) < page_size:
                break

        print(f"    sms/send: {total_fetched:,} fetched (API total: {api_total:,})")

    # ------------------------------------------------------------------
    # Contacts — FULL extraction, no cap
    # ------------------------------------------------------------------

    def _extract_contacts(self, app_id: str):
        """GET /v2/sms/contact — paginated list of ALL SMS contacts."""
        page = 1
        page_size = 100
        total_fetched = 0
        api_total = 0

        while True:
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

    def _date_windows(self):
        """Yield (start, end) date tuples in <=99-day windows covering the extraction range."""
        current = self.date_from
        while current < self.date_to:
            window_end = min(current + timedelta(days=MAX_STATS_WINDOW_DAYS - 1), self.date_to)
            yield current, window_end
            current = window_end + timedelta(days=1)
