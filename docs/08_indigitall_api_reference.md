# Indigitall API — Referencia de Integración

> Documentación basada en pruebas reales contra la API de Indigitall (región AM1).
> Última actualización: 2026-02-23

---

## 1. Autenticación

### ServerKey (Server-to-Server) — Modo Preferido

La API usa un único header `Authorization` con prefijo `ServerKey`:

```
Authorization: ServerKey <UUID>
Accept: application/json
Content-Type: application/json
```

**No se requiere** header `AppToken`. El AppToken (publicKey de la app) se usa como
`applicationId` en los query params, no como header de autenticación.

### JWT (Email/Password) — Modo Alternativo

Para endpoints que requieren sesión de usuario (ej. mensajes de chat):

```
POST /v1/auth
Body: {"mail": "user@example.com", "password": "..."}
→ Respuesta: {"token": "<JWT>"}

Authorization: Bearer <JWT>
```

### Obtener credenciales

- **ServerKey**: Indigitall Console → Settings → Server Keys
- **AppToken (publicKey)**: visible en la respuesta de `/v1/application` como campo `publicKey`

---

## 2. URL Base — Regiones

La API es **regional**. Cada cuenta está asociada a una región específica:

| Región | URL | Uso |
|--------|-----|-----|
| `am1` | `https://am1.api.indigitall.com` | **Americas / Latinoamérica** |
| `eu1` | `https://eu1.api.indigitall.com` | Europa (pre-2021) |
| `eu2` | `https://eu2.api.indigitall.com` | Europa / mundial (post-2021) |
| `eu3` | `https://eu3.api.indigitall.com` | Post-septiembre 2024 |

> **Importante**: El genérico `https://api.indigitall.com` NO funciona con ServerKey
> de la región AM1. Siempre usar la URL regional correcta.

Para la cuenta de Visionamos: **`https://am1.api.indigitall.com`**

---

## 3. Formato de Respuesta Estándar

Todas las respuestas siguen este formato:

```json
{
  "statusCode": 200,
  "message": "OK",
  "count": 1,
  "data": [...]
}
```

- `statusCode`: código HTTP
- `message`: descripción del resultado
- `count`: total de registros (para endpoints paginados)
- `data`: array de objetos o objeto con los datos

---

## 4. Paginación

La API usa **dos esquemas** de paginación dependiendo del endpoint:

### Esquema A: `limit` + `page` (mayoría de endpoints)
```
GET /v1/application?limit=50&page=0
GET /v1/campaign?applicationId=100274&limit=20&page=0
```
- `page` empieza en 0

### Esquema B: `limit` + `offset` (endpoints de chat)
```
GET /v1/chat/contacts?applicationId=100274&limit=20&offset=0
```
- `offset` = número de registros a saltar

---

## 5. Endpoints Verificados

### 5.1 Aplicaciones

#### `GET /v1/application`
Lista todas las aplicaciones de la cuenta.

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `limit` | int | Sí | Máximo de resultados |
| `page` | int | Sí | Página (base 0) |

**Respuesta:**
```json
{
  "statusCode": 200,
  "message": "OK",
  "count": 1,
  "data": [
    {
      "id": 100274,
      "createdAt": "2025-04-14T17:07:22.876Z",
      "name": "VISIONAMOS PROD",
      "publicKey": "ec3521b6-49c6-41dc-8f54-a7be791ad95a",
      "androidEnabled": false,
      "iosEnabled": false,
      "webpushEnabled": false,
      "chatEnabled": true,
      "pushLocationEnabled": false,
      "deleteDevicesConfiguration": {}
    }
  ]
}
```

#### `GET /v1/application/stats`
Resumen de estadísticas a nivel de cuenta.

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `applicationId` | int | Sí | ID de la aplicación |
| `limit` | int | Sí | Máximo de resultados |
| `page` | int | Sí | Página (base 0) |

**Respuesta:**
```json
{
  "data": [
    {
      "id": 100274,
      "name": "VISIONAMOS PROD",
      "campaigns": {"sent": 0, "scheduled": 0, "welcome": 0, "fidelity": 0, "goefencing": 0, "network": 0},
      "devices": {"android": 0, "ios": 0, "webpush": 0, "safari": 0},
      "impacts": {"total": 0, "today": 0, "lastWeek": 0, "lastMonth": 0}
    }
  ]
}
```

---

### 5.2 Estadísticas Push

#### `GET /v1/application/{appId}/dateStats`
Estadísticas diarias de push por plataforma.

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `dateFrom` | string (YYYY-MM-DD) | Sí | Fecha inicio |
| `dateTo` | string (YYYY-MM-DD) | Sí | Fecha fin |
| `periodicity` | string | Sí | `"daily"` o `"hourly"` |

**Respuesta:**
```json
{
  "data": [
    {
      "platformGroup": "android",
      "statsDate": "2026-02-16",
      "numDevicesSent": 0,
      "numDevicesSuccess": 0,
      "numDevicesReceived": 0,
      "numDevicesClicked": 0
    }
  ]
}
```
> Se retorna un registro por plataforma (android, ios, web) por fecha.

#### `GET /v1/application/{appId}/pushHeatmap`
Mapa de calor de engagement por hora y día de la semana.

| Param | Tipo | Requerido |
|-------|------|-----------|
| `dateFrom` | string | Sí |
| `dateTo` | string | Sí |

**Respuesta:**
```json
{
  "data": {
    "heatmap": "general",
    "hour": {"8": 0.0225, "9": 0.0261, "10": 0.0278, ...},
    "weekday": {"monday": 0.0273, "tuesday": 0.0558, ...},
    "weekday-hour": {
      "monday": {"8": 0.0204, "9": 0.0281, ...},
      "tuesday": {"8": 0.0185, ...},
      ...
    }
  }
}
```
> Los valores representan tasas de interacción (0.0 a 1.0).

#### `GET /v1/application/{appId}/stats/device`
Estadísticas de dispositivos.

| Param | Tipo | Requerido | Nota |
|-------|------|-----------|------|
| `dateFrom` | string | Sí | **Máximo 7 días de rango** |
| `dateTo` | string | Sí | Si excede 7 días → 403 |

#### `GET /v1/application/{appId}/stats/dashboard`
Resumen de dashboard. No requiere parámetros adicionales.

---

### 5.3 Campañas

#### `GET /v1/campaign`
Lista de campañas de la aplicación.

| Param | Tipo | Requerido |
|-------|------|-----------|
| `applicationId` | int | Sí |
| `limit` | int | Sí |
| `page` | int | Sí |

#### `GET /v1/campaign/stats`
Estadísticas de campañas.

| Param | Tipo | Requerido |
|-------|------|-----------|
| `applicationId` | int | Sí |
| `dateFrom` | string | Sí |
| `dateTo` | string | Sí |
| `limit` | int | Sí |
| `page` | int | Sí |

---

### 5.4 Chat / WhatsApp

#### `GET /v1/chat/contacts`
Lista de contactos de chat (WhatsApp).

| Param | Tipo | Requerido |
|-------|------|-----------|
| `applicationId` | int | Sí |
| `limit` | int | Sí |
| `offset` | int | Sí |

**Respuesta:**
```json
{
  "data": [
    {
      "contactId": "573167738125",
      "externalCode": "",
      "createdAt": "2025-05-29T02:01:19.632Z",
      "updatedAt": "2025-09-24T16:19:04.421Z",
      "channel": "cloudapi",
      "language": null,
      "profileName": "Albenis Yenith",
      "externalId": null,
      "instanceId": 391,
      "chatAllowed": false,
      "agentId": null,
      "id": 8905634,
      "lastInputMessage": "2025-09-24T16:19:03.942Z"
    }
  ]
}
```

> - `contactId`: número de teléfono con código de país (ej. 573... = Colombia)
> - `channel`: siempre "cloudapi" (WhatsApp Cloud API)
> - `instanceId`: ID de la instancia de WhatsApp (391 para Visionamos)
> - `lastInputMessage`: timestamp del último mensaje recibido

#### `GET /v1/chat/agent/status`
Estado de los agentes de chat.

| Param | Tipo | Requerido |
|-------|------|-----------|
| `applicationId` | int | Sí |

**Respuesta:**
```json
{
  "data": {
    "activeAgents": 4
  }
}
```

---

### 5.5 Endpoints No Disponibles (ServerKey Auth)

Los siguientes endpoints retornan **404** con autenticación ServerKey.
Requieren autenticación JWT (email/password):

| Endpoint | Descripción |
|----------|-------------|
| `/v1/chat/message` | Mensajes de conversación |
| `/v1/chat/instance` | Instancias de WhatsApp |
| `/v1/chat/agent` | Lista de agentes |
| `/v1/chat/stats` | Estadísticas de chat |
| `/v1/chat/template` | Templates de WhatsApp |
| `/v1/chat/tag` | Etiquetas de chat |
| `/v1/chat/group` | Grupos de chat |
| `/v1/sms/*` | Todos los endpoints SMS |
| `/v1/email/*` | Todos los endpoints Email |

El endpoint `/v1/inApp/stats` retorna **500** (error del servidor).

---

## 6. Códigos de Error Comunes

| Código | Mensaje | Causa |
|--------|---------|-------|
| 400 | `request/query must have required property 'limit'` | Falta parámetro obligatorio |
| 400 | `periodicity should be equal to one of: hourly, daily` | Valor inválido de periodicity |
| 401 | `Access token is not valid` | ServerKey inválido o región incorrecta |
| 403 | `Operation forbidden, more 7 days` | Rango de fechas excede límite |
| 404 | `Route GET:/v1/... not found` | Endpoint no existe o no disponible para auth mode |
| 500 | `Internal server error` | Error del lado del servidor |

---

## 7. Pipeline de Extracción

### Arquitectura

```
Indigitall API (am1)
       │
       ▼
  ServerKey Auth
       │
       ▼
  ┌─────────────────────────────────────────────┐
  │  Orchestrator (orchestrator.py)              │
  │  1. Authenticate                             │
  │  2. Discover applications                    │
  │  3. Run 7 extractors per app                 │
  │  4. Report summary                           │
  └──────────────┬──────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
  Push      Chat/WA     Campaigns    SMS  Email  InApp  Contacts
  Extractor  Extractor  Extractor   (N/A) (N/A)  (N/A)  Extractor
    │            │            │                              │
    ▼            ▼            ▼                              ▼
  raw.raw_   raw.raw_    raw.raw_                      raw.raw_
  push_stats chat_stats  campaigns_api                 contacts_api
```

### Extractores y Endpoints

| Extractor | Endpoints | Estado |
|-----------|-----------|--------|
| **PushExtractor** | dateStats, pushHeatmap, stats/device, application/stats | Activo — datos de heatmap disponibles |
| **ChatExtractor** | chat/contacts (paginado), chat/agent/status | Activo — 20+ contactos WhatsApp |
| **CampaignsExtractor** | campaign (paginado), campaign/stats | Activo — 0 campañas actuales |
| **ContactsExtractor** | chat/contacts (paginado), chat/agent/status | Activo — mismo dato, tabla diferente |
| **SMSExtractor** | sms/stats | Inactivo — 404 (no habilitado) |
| **EmailExtractor** | email/stats | Inactivo — 404 (no habilitado) |
| **InAppExtractor** | inApp/stats | Inactivo — 500 (error servidor) |

### Ejecución

```bash
# Crear esquema raw (primera vez)
docker compose exec app python scripts/create_raw_schema.py

# Ejecutar pipeline completo
docker compose exec app python -m scripts.extractors.orchestrator

# Test standalone (sin Docker)
python scripts/test_api_connection.py
```

---

## 8. Datos de la Cuenta Visionamos

| Campo | Valor |
|-------|-------|
| **App ID** | 100274 |
| **Nombre** | VISIONAMOS PROD |
| **Región** | AM1 (Americas) |
| **Canal principal** | Chat / WhatsApp |
| **Agentes activos** | 4 |
| **Contactos** | 20+ (números colombianos 573...) |
| **WhatsApp Instance** | 391 |
| **Push/SMS/Email** | No habilitados |
| **Campañas** | 0 activas |
