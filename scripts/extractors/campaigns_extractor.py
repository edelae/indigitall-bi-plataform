"""Campaigns extractor — verified endpoints from am1 API.

Verified endpoints:
  - /v1/campaign  (paginated campaign list — uses limit+page)
  - /v1/campaign/stats  (campaign stats — uses applicationId+dateFrom+dateTo+limit+page)
"""

from scripts.extractors.base_extractor import BaseExtractor
from scripts.extractors.config import extraction_settings as cfg


class CampaignsExtractor(BaseExtractor):
    CHANNEL_NAME = "campaigns"
    RAW_TABLE = "raw.raw_campaigns_api"

    MAX_PAGES = 50

    def _extract_for_app(self, app_id: str, app_meta: dict):
        page_size = min(cfg.EXTRACTION_MAX_RECORDS, 100)

        # 1. Campaign list (paginated — uses limit+page)
        total_campaigns = 0
        for page_num in range(self.MAX_PAGES):
            try:
                data = self.client.get(
                    "/v1/campaign",
                    params={
                        "applicationId": app_id,
                        "limit": page_size,
                        "page": page_num,
                    },
                    application_id=app_id,
                )
                if data is None:
                    break

                campaigns = data.get("data", []) if isinstance(data, dict) else data
                if not campaigns:
                    break

                self._store_raw(app_id, "/v1/campaign", data)
                total_campaigns += len(campaigns)

                if len(campaigns) < page_size:
                    break

            except Exception as exc:
                print(f"    campaign list page {page_num}: FAILED ({exc})")
                break

        print(f"    campaign list: {total_campaigns} records")

        # 2. Campaign stats
        try:
            stats = self.client.get(
                "/v1/campaign/stats",
                params={
                    "applicationId": app_id,
                    "dateFrom": self.date_from_str,
                    "dateTo": self.date_to_str,
                    "limit": page_size,
                    "page": 0,
                },
                application_id=app_id,
            )
            if stats is not None:
                self._store_raw(app_id, "/v1/campaign/stats", stats)
                count = len(stats.get("data", [])) if isinstance(stats, dict) else 0
                print(f"    campaign stats: {count} records")
            else:
                print(f"    campaign stats: empty response")
        except Exception as exc:
            print(f"    campaign stats: FAILED ({exc})")
