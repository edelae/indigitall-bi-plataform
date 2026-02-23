"""Email extractor — endpoints not available on am1 with ServerKey auth.

Status: Email endpoints return 404 on am1 for this account.
These endpoints may work on accounts with email campaigns enabled.
Keeping the extractor for future use with graceful handling.
"""

from scripts.extractors.base_extractor import BaseExtractor


class EmailExtractor(BaseExtractor):
    CHANNEL_NAME = "email"
    RAW_TABLE = "raw.raw_email_stats"

    def _extract_for_app(self, app_id: str, app_meta: dict):
        endpoints = [
            {
                "name": "email/stats",
                "path": "/v1/email/stats",
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
                    print(f"    {ep['name']}: not available (likely 404)")
            except Exception as exc:
                print(f"    {ep['name']}: FAILED ({exc})")
