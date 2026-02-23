"""InApp extractor — endpoint returns 500 on am1 for this account.

Status: /v1/inApp/stats returns Internal Server Error (500).
This may be a temporary issue or the feature may not be enabled.
Keeping the extractor for future use with graceful handling.
"""

from scripts.extractors.base_extractor import BaseExtractor


class InAppExtractor(BaseExtractor):
    CHANNEL_NAME = "inapp"
    RAW_TABLE = "raw.raw_inapp_stats"

    def _extract_for_app(self, app_id: str, app_meta: dict):
        endpoints = [
            {
                "name": "inApp/stats",
                "path": "/v1/inApp/stats",
                "params": {
                    "applicationId": app_id,
                    "dateFrom": self.date_from_str,
                    "dateTo": self.date_to_str,
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
                    print(f"    {ep['name']}: not available")
            except Exception as exc:
                print(f"    {ep['name']}: FAILED ({exc})")
