"""Chat / WhatsApp extractor — verified endpoints from am1 API.

Verified endpoints:
  - /v1/chat/contacts  (paginated contact list with WhatsApp metadata)
  - /v1/chat/agent/status  (active agent count)

Note: Chat messages, instances, agents list, templates, and stats endpoints
      are NOT available with ServerKey auth (return 404). These require
      JWT/Bearer auth with email+password.
"""

from scripts.extractors.base_extractor import BaseExtractor
from scripts.extractors.config import extraction_settings as cfg


class ChatExtractor(BaseExtractor):
    CHANNEL_NAME = "chat"
    RAW_TABLE = "raw.raw_chat_stats"

    MAX_PAGES = 50  # Safety limit for pagination

    def _extract_for_app(self, app_id: str, app_meta: dict):
        # 1. Chat agent status (single call, no pagination)
        try:
            data = self.client.get(
                "/v1/chat/agent/status",
                params={"applicationId": app_id},
                application_id=app_id,
            )
            if data is not None:
                self._store_raw(app_id, "/v1/chat/agent/status", data)
                print(f"    agent/status: OK")
            else:
                print(f"    agent/status: empty response")
        except Exception as exc:
            print(f"    agent/status: FAILED ({exc})")

        # 2. Chat contacts (paginated — uses limit+offset)
        page_size = min(cfg.EXTRACTION_MAX_RECORDS, 100)
        offset = 0
        total_contacts = 0

        for page_num in range(self.MAX_PAGES):
            try:
                data = self.client.get(
                    "/v1/chat/contacts",
                    params={
                        "applicationId": app_id,
                        "limit": page_size,
                        "offset": offset,
                    },
                    application_id=app_id,
                )
                if data is None:
                    break

                contacts = data.get("data", []) if isinstance(data, dict) else data
                if not contacts:
                    break

                self._store_raw(app_id, "/v1/chat/contacts", data)
                total_contacts += len(contacts)

                # Stop if we got fewer than page_size (last page)
                if len(contacts) < page_size:
                    break

                offset += page_size

            except Exception as exc:
                print(f"    contacts page {page_num}: FAILED ({exc})")
                break

        print(f"    contacts: {total_contacts} records across {page_num + 1} page(s)")
