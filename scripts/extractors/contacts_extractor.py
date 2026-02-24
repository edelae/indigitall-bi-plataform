"""Contacts extractor — verified endpoints from am1 API.

Verified endpoints:
  - /v1/chat/contacts  (paginated — limit+offset, returns contactId, channel, profileName, etc.)
  - /v1/chat/agent/status  (active agent count)

Note: This extractor focuses on persisting contacts as a standalone entity.
The ChatExtractor also fetches contacts — this is intentional for the
raw_contacts_api table which may have different dbt transforms.
"""

from scripts.extractors.base_extractor import BaseExtractor
from scripts.extractors.config import extraction_settings as cfg


class ContactsExtractor(BaseExtractor):
    CHANNEL_NAME = "contacts"
    RAW_TABLE = "raw.raw_contacts_api"

    MAX_PAGES = 50

    def _extract_for_app(self, app_id: str, app_meta: dict):
        page_size = min(cfg.EXTRACTION_MAX_RECORDS, 100)

        # 1. Chat contacts (paginated — uses limit+page, NOT offset)
        #    The Indigitall API ignores the offset parameter for /v1/chat/contacts.
        #    Page numbers are 0-indexed.
        total = 0
        for page_num in range(self.MAX_PAGES):
            try:
                data = self.client.get(
                    "/v1/chat/contacts",
                    params={
                        "applicationId": app_id,
                        "limit": page_size,
                        "page": page_num,
                    },
                    application_id=app_id,
                )
                if data is None:
                    break

                contacts = data.get("data", []) if isinstance(data, dict) else data
                if not contacts:
                    break

                self._store_raw(app_id, "/v1/chat/contacts", data)
                total += len(contacts)

                if len(contacts) < page_size:
                    break

            except Exception as exc:
                print(f"    contacts page {page_num}: FAILED ({exc})")
                break

        print(f"    contacts: {total} records across {page_num + 1} page(s)")

        # 2. Agent status
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
