"""Dashboard AI Service — AI-powered suggestions for dashboard construction."""

import json
import logging
from typing import Dict, Any, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

SYSTEM_PROMPT = """Eres un asistente experto en Business Intelligence y dashboards.
Tu trabajo es ayudar a los usuarios a construir tableros analiticos efectivos.

El usuario tiene acceso a consultas guardadas que puede agregar como widgets a su tablero.
Cada consulta tiene: nombre, tipo de grafica (bar, line, pie, table), y datos.

=== GRID LAYOUT ===
El tablero usa un grid de 12 columnas con drag-and-drop:
- Ancho (w): 4=tercio, 6=mitad, 8=dos-tercios, 12=completo
- Alto (h): 3=compacto, 4=normal, 5=amplio, 6=grande
- Los widgets se organizan automaticamente verticalmente

=== RECOMENDACIONES DE LAYOUT ===
- KPIs y resumen: ancho 12, alto 3 (barra superior)
- Graficas de tendencia: ancho 6-8, alto 4-5
- Graficas de distribucion (pie): ancho 4-6, alto 4
- Tablas detalladas: ancho 12, alto 5-6
- Agrupa KPIs arriba, tendencias en medio, detalle abajo

Cuando el usuario describe que quiere ver en su tablero, debes:
1. Sugerir cuales de sus consultas disponibles son mas relevantes
2. Recomendar tipos de graficas apropiados
3. Sugerir disposicion con recommended_width y recommended_height
4. Sugerir agrupaciones logicas ("KPIs arriba, tendencias abajo")
5. Si no hay consultas relevantes, sugerir que consultas crear primero

Responde SIEMPRE en JSON valido con este formato:
{
    "response": "Tu explicacion en español con sugerencia de layout",
    "suggestions": [
        {
            "query_id": 123,
            "title": "Nombre de la consulta",
            "description": "Por que es relevante",
            "recommended_width": 6,
            "recommended_height": 4,
            "recommended_chart": "bar"
        }
    ]
}

Si no hay consultas disponibles que coincidan, suggestions puede estar vacio
y en response explica que consultas deberian crear primero.

Responde en español colombiano, profesional pero accesible.
"""


class DashboardAIService:
    """AI service for dashboard building suggestions."""

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None

        if OPENAI_AVAILABLE and settings.has_openai_key:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        if ANTHROPIC_AVAILABLE and settings.has_ai_key:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def suggest_dashboard(
        self,
        message: str,
        available_queries: List[Dict],
        current_widgets: List[Dict],
    ) -> Dict[str, Any]:
        """Generate dashboard suggestions based on user request."""
        queries_desc = "\n".join(
            f"- ID:{q['id']} \"{q['name']}\" ({q.get('ai_function', 'SQL')}, "
            f"{q.get('result_row_count', 0)} filas)"
            for q in available_queries
        ) if available_queries else "No hay consultas guardadas."

        current_desc = ""
        if current_widgets:
            current_desc = "\nWidgets actuales en el tablero:\n" + "\n".join(
                f"- \"{w.get('title', 'Widget')}\" (ancho={w.get('width', 6)})"
                for w in current_widgets
            )

        user_msg = (
            f"Consultas disponibles:\n{queries_desc}\n"
            f"{current_desc}\n\n"
            f"Solicitud del usuario: {message}"
        )

        # Try OpenAI first (preferred — key always configured)
        if self.openai_client:
            result = self._openai_suggest(user_msg)
            if result:
                return result

        # Try Anthropic as fallback
        if self.anthropic_client:
            result = self._anthropic_suggest(user_msg)
            if result:
                return result

        logger.warning(
            "No AI provider available. openai_available=%s, has_openai_key=%s, "
            "anthropic_available=%s, has_ai_key=%s",
            OPENAI_AVAILABLE, settings.has_openai_key,
            ANTHROPIC_AVAILABLE, settings.has_ai_key,
        )
        return {
            "response": (
                "No tengo acceso al servicio de IA en este momento. "
                "Puedes agregar consultas manualmente desde el panel lateral."
            ),
            "suggestions": [],
        }

    def _anthropic_suggest(self, user_msg: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                temperature=0.3,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            return self._parse_response(response.content[0].text)
        except Exception as e:
            logger.warning("Anthropic dashboard AI failed: %s", e)
            return None

    def _openai_suggest(self, user_msg: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=1024,
                temperature=0.3,
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception as e:
            logger.warning("OpenAI dashboard AI failed: %s", e)
            return None

    @staticmethod
    def _parse_response(text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from AI."""
        import re
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def propose_additional_queries(self, message: str) -> Dict[str, Any]:
        """Suggest new queries the user could create for their dashboard."""
        user_msg = (
            f"El usuario quiere crear un tablero con este enfoque: {message}\n\n"
            "Sugiere 3-5 consultas de datos que serian utiles para este tablero. "
            "Para cada consulta sugiere: titulo, descripcion breve, y tipo de grafica ideal. "
            "Responde en JSON: {{\"suggestions\": [{{\"title\": ..., \"description\": ..., "
            "\"chart_type\": ...}}]}}"
        )

        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    max_tokens=512,
                    temperature=0.5,
                )
                result = self._parse_response(response.choices[0].message.content)
                if result:
                    return result
            except Exception as e:
                logger.warning("OpenAI propose queries failed: %s", e)

        return {"suggestions": []}
