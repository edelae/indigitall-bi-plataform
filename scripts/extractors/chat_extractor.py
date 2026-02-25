"""Chat / WhatsApp extractor — verified endpoints from am1 API.

Verified endpoints (ServerKey auth):
  - /v1/chat/contacts         (paginated contact list)
  - /v1/chat/agent/status     (active agent count)
  - /v1/chat/history/csv      (message history — CSV, max 7 days per request)
  - /v1/chat/agent/conversations  (agent sessions — JSON, all at once)
  - /v1/chat/channel          (WhatsApp + webchat channels)
  - /v1/chat/configuration    (chat config)
  - /v1/chat/topic            (conversation topics)
  - /v1/chat/integration      (agent + Dialogflow integrations)
"""

import csv
import io
import json
from datetime import timedelta

from scripts.extractors.base_extractor import BaseExtractor
from scripts.extractors.config import extraction_settings as cfg


class ChatExtractor(BaseExtractor):
    CHANNEL_NAME = "chat"
    RAW_TABLE = "raw.raw_chat_stats"

    MAX_PAGES = 50  # Safety limit for pagination
    HISTORY_MAX_DAYS = 7  # API limit per request for chat/history/csv
    HISTORY_PAGE_SIZE = 500  # rows per CSV page

    def _extract_for_app(self, app_id: str, app_meta: dict):
        # 1. Chat agent status
        self._extract_agent_status(app_id)

        # 2. Chat contacts (paginated)
        self._extract_contacts(app_id)

        # 3. Chat message history (CSV, 7-day windows)
        self._extract_message_history(app_id)

        # 4. Agent conversations (all sessions)
        self._extract_agent_conversations(app_id)

        # 5. Chat channels
        self._extract_channels(app_id)

        # 6. Chat configuration
        self._extract_configuration(app_id)

        # 7. Topics
        self._extract_topics(app_id)

        # 8. Integrations
        self._extract_integrations(app_id)

    # ------------------------------------------------------------------
    # 1. Agent status
    # ------------------------------------------------------------------

    def _extract_agent_status(self, app_id: str):
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

    # ------------------------------------------------------------------
    # 2. Contacts (paginated)
    # ------------------------------------------------------------------

    def _extract_contacts(self, app_id: str):
        page_size = min(cfg.EXTRACTION_MAX_RECORDS, 100)
        total_contacts = 0

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
                total_contacts += len(contacts)

                if len(contacts) < page_size:
                    break

            except Exception as exc:
                print(f"    contacts page {page_num}: FAILED ({exc})")
                break

        print(f"    contacts: {total_contacts} records across {page_num + 1} page(s)")

    # ------------------------------------------------------------------
    # 3. Message history (CSV, 7-day sliding windows)
    # ------------------------------------------------------------------

    def _extract_message_history(self, app_id: str):
        """Extract chat messages via /v1/chat/history/csv.

        The API enforces a max 7-day window, so we slide through the
        full date range in 7-day chunks, paginating each chunk.
        """
        total_messages = 0
        window_start = self.date_from

        while window_start < self.date_to:
            window_end = min(window_start + timedelta(days=self.HISTORY_MAX_DAYS),
                             self.date_to)

            page_messages = self._extract_history_window(
                app_id, window_start.isoformat(), window_end.isoformat()
            )
            total_messages += page_messages
            window_start = window_end

        print(f"    message-history: {total_messages} messages")

    def _extract_history_window(self, app_id: str, date_from: str, date_to: str) -> int:
        """Extract all pages for one 7-day window. Returns message count."""
        window_total = 0

        for page_num in range(self.MAX_PAGES):
            try:
                csv_text = self.client.get_text(
                    "/v1/chat/history/csv",
                    params={
                        "applicationId": app_id,
                        "limit": self.HISTORY_PAGE_SIZE,
                        "page": page_num,
                        "dateFrom": date_from,
                        "dateTo": date_to,
                    },
                    application_id=app_id,
                )
                if csv_text is None:
                    break

                # Parse CSV to list of dicts for JSONB storage
                reader = csv.DictReader(io.StringIO(csv_text))
                rows = list(reader)
                if not rows:
                    break

                payload = {
                    "dateFrom": date_from,
                    "dateTo": date_to,
                    "page": page_num,
                    "count": len(rows),
                    "data": rows,
                }
                self._store_raw(app_id, "/v1/chat/history/csv", payload)
                window_total += len(rows)

                if len(rows) < self.HISTORY_PAGE_SIZE:
                    break

            except Exception as exc:
                print(f"    history {date_from}/{date_to} p{page_num}: FAILED ({exc})")
                break

        return window_total

    # ------------------------------------------------------------------
    # 4. Agent conversations
    # ------------------------------------------------------------------

    def _extract_agent_conversations(self, app_id: str):
        """Extract all agent conversation sessions via /v1/chat/agent/conversations.

        Using email="" returns all conversations across all agents.
        """
        try:
            data = self.client.get(
                "/v1/chat/agent/conversations",
                params={
                    "applicationId": app_id,
                    "email": "",
                    "limit": 50000,
                },
                application_id=app_id,
            )
            if data is None:
                print(f"    agent/conversations: empty response")
                return

            convs = data.get("data", []) if isinstance(data, dict) else []
            self._store_raw(app_id, "/v1/chat/agent/conversations", data)
            print(f"    agent/conversations: {len(convs)} sessions")
        except Exception as exc:
            print(f"    agent/conversations: FAILED ({exc})")

    # ------------------------------------------------------------------
    # 5. Channels
    # ------------------------------------------------------------------

    def _extract_channels(self, app_id: str):
        try:
            data = self.client.get(
                "/v1/chat/channel",
                params={"applicationId": app_id},
                application_id=app_id,
            )
            if data is not None:
                self._store_raw(app_id, "/v1/chat/channel", data)
                count = data.get("count", 0) if isinstance(data, dict) else 0
                print(f"    channels: {count}")
            else:
                print(f"    channels: empty response")
        except Exception as exc:
            print(f"    channels: FAILED ({exc})")

    # ------------------------------------------------------------------
    # 6. Configuration
    # ------------------------------------------------------------------

    def _extract_configuration(self, app_id: str):
        try:
            data = self.client.get(
                "/v1/chat/configuration",
                params={"applicationId": app_id},
                application_id=app_id,
            )
            if data is not None:
                self._store_raw(app_id, "/v1/chat/configuration", data)
                print(f"    configuration: OK")
        except Exception as exc:
            print(f"    configuration: FAILED ({exc})")

    # ------------------------------------------------------------------
    # 7. Topics
    # ------------------------------------------------------------------

    def _extract_topics(self, app_id: str):
        try:
            data = self.client.get(
                "/v1/chat/topic",
                params={"applicationId": app_id},
                application_id=app_id,
            )
            if data is not None:
                self._store_raw(app_id, "/v1/chat/topic", data)
                count = data.get("count", 0) if isinstance(data, dict) else 0
                print(f"    topics: {count}")
        except Exception as exc:
            print(f"    topics: FAILED ({exc})")

    # ------------------------------------------------------------------
    # 8. Integrations
    # ------------------------------------------------------------------

    def _extract_integrations(self, app_id: str):
        try:
            data = self.client.get(
                "/v1/chat/integration",
                params={"applicationId": app_id},
                application_id=app_id,
            )
            if data is not None:
                self._store_raw(app_id, "/v1/chat/integration", data)
                count = data.get("count", 0) if isinstance(data, dict) else 0
                print(f"    integrations: {count}")
        except Exception as exc:
            print(f"    integrations: FAILED ({exc})")
