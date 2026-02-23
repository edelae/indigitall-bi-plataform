"""SMS extractor — endpoints not available on am1 with ServerKey auth.

Status: All SMS endpoints return 404 on am1 for this account.
These endpoints may work on other accounts that have SMS enabled.
Keeping the extractor for future use with graceful handling.
"""

from scripts.extractors.base_extractor import BaseExtractor


class SMSExtractor(BaseExtractor):
    CHANNEL_NAME = "sms"
    RAW_TABLE = "raw.raw_sms_stats"

    def _extract_for_app(self, app_id: str, app_meta: dict):
        endpoints = [
            {
                "name": "sms/stats",
                "path": "/v1/sms/stats",
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
