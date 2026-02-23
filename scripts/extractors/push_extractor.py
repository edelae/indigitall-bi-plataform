"""Push notifications extractor — verified endpoints from am1 API.

Verified endpoints:
  - /v1/application/{id}/dateStats  (daily stats by platform: android/ios/web)
  - /v1/application/{id}/pushHeatmap  (engagement heatmap by hour/weekday)
  - /v1/application/{id}/stats/device  (device stats, max 7-day range)
  - /v1/application/stats  (account-level summary: campaigns/devices/impacts)
"""

from datetime import timedelta

from scripts.extractors.base_extractor import BaseExtractor


class PushExtractor(BaseExtractor):
    CHANNEL_NAME = "push"
    RAW_TABLE = "raw.raw_push_stats"

    def _extract_for_app(self, app_id: str, app_meta: dict):
        # Device stats endpoint is limited to 7-day range
        device_date_from = max(
            self.date_from,
            self.date_to - timedelta(days=7),
        )

        endpoints = [
            {
                "name": "dateStats (daily)",
                "path": f"/v1/application/{app_id}/dateStats",
                "params": {
                    "dateFrom": self.date_from_str,
                    "dateTo": self.date_to_str,
                    "periodicity": "daily",
                },
            },
            {
                "name": "pushHeatmap",
                "path": f"/v1/application/{app_id}/pushHeatmap",
                "params": {
                    "dateFrom": self.date_from_str,
                    "dateTo": self.date_to_str,
                },
            },
            {
                "name": "stats/device (7d)",
                "path": f"/v1/application/{app_id}/stats/device",
                "params": {
                    "dateFrom": device_date_from.isoformat(),
                    "dateTo": self.date_to_str,
                },
            },
            {
                "name": "application/stats",
                "path": "/v1/application/stats",
                "params": {
                    "applicationId": app_id,
                    "limit": 50,
                    "page": 0,
                },
            },
        ]

        for ep in endpoints:
            try:
                data = self.client.get(ep["path"], params=ep["params"], application_id=app_id)
                if data is not None:
                    self._store_raw(app_id, ep["path"], data)
                    print(f"    {ep['name']}: OK")
                else:
                    print(f"    {ep['name']}: empty response")
            except Exception as exc:
                print(f"    {ep['name']}: FAILED ({exc})")
