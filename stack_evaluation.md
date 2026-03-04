# Auditoría y Evaluación del Stack Tecnológico — inDigitall BI Platform

**Fecha**: Marzo 2026
**Alcance**: Evaluación del stack actual (Plotly Dash) vs. alternativas modernas (React + TypeScript + FastAPI)
**Objetivo**: Determinar si el stack actual es adecuado para la visión del producto o si se debe migrar

---

## 1. Estado Actual del Proyecto

### Métricas del Codebase

| Métrica | Valor |
|---------|-------|
| Líneas de Python (app/) | ~13,300 |
| Archivos de callback | 27 |
| Archivos de layout (páginas) | 13 |
| Archivos de servicio | 12 |
| JavaScript/TypeScript custom | **0 líneas** |
| CSS personalizado | 546 líneas |
| Dependencias Python | 14 paquetes |
| Servicios Docker | 6 (DB, PostgREST, Studio, Kong, App, n8n) |

### Stack Actual

| Capa | Tecnología |
|------|-----------|
| Frontend + Backend | Plotly Dash 2.18.2 (monolito Python) |
| Componentes UI | Dash Bootstrap Components 1.6.0 |
| Gráficas | Plotly.py 5.24+ |
| Estilos | Bootstrap 5 + CSS variables custom |
| Servidor | Flask + Gunicorn (sync, 2 workers) |
| Base de datos | PostgreSQL 15 (Supabase Self-Hosted) |
| ORM | SQLAlchemy Core |
| IA | Anthropic Claude + OpenAI GPT-4o-mini |
| ETL | dbt + extractores Python |
| Deploy | Docker Compose + GCP VM + Caddy |

---

## 2. Funcionalidades Deseadas vs. Capacidades de Dash

### Visión del Producto

La plataforma requiere **interactividad bidireccional** entre consultas y tableros:

1. Chat IA → genera SQL → resultado + gráfica → guardar como query
2. Query guardada → agregar como widget a tablero personalizado
3. Click en gráfica del tablero → navega al query original
4. Constructor de dashboards con panel lateral, drag-and-drop, resize
5. Asistente IA contextual en el constructor
6. Filtros cruzados (cross-filtering) entre widgets
7. Explorador de datos interactivo
8. Multi-tenant con autenticación JWT

### Evaluación por Funcionalidad

| Funcionalidad | Dash | React + TS | Veredicto |
|---------------|------|-----------|-----------|
| Gráficas interactivas (hover, click, zoom) | ★★★★★ Nativo con Plotly | ★★★★★ Plotly.js / Recharts / D3 | **Empate** |
| Chat IA con streaming | ★★☆☆☆ No hay streaming nativo, se simula con intervalos | ★★★★★ SSE/WebSocket nativos, streaming token-by-token | **React gana** |
| Drag-and-drop grid | ★★☆☆☆ `dash-draggable` inestable, sin mantenimiento activo | ★★★★★ react-grid-layout, dnd-kit, pragmatic-drag-and-drop | **React gana** |
| Resize de widgets | ★★☆☆☆ Requiere callbacks complejos | ★★★★★ Nativo con react-grid-layout | **React gana** |
| Cross-filtering entre charts | ★★★☆☆ Posible pero verboso (callback chains) | ★★★★★ Estado global + re-render selectivo | **React gana** |
| Navegación SPA | ★★★☆☆ `use_pages` funcional pero limitado | ★★★★★ React Router / TanStack Router | **React gana** |
| Estado complejo (undo/redo, multi-store) | ★★☆☆☆ `dcc.Store` es básico, sin middleware | ★★★★★ Zustand / Jotai / Redux Toolkit | **React gana** |
| Formularios complejos | ★★☆☆☆ Sin validación integrada | ★★★★★ React Hook Form + Zod | **React gana** |
| Tablas con edición inline | ★★★☆☆ `dash_table` funcional pero limitado | ★★★★★ TanStack Table, AG Grid | **React gana** |
| Renderizado condicional | ★★★☆☆ Via callbacks (round-trip al server) | ★★★★★ Instantáneo (client-side) | **React gana** |
| Performance con muchos widgets | ★★☆☆☆ Cada interacción = HTTP round-trip | ★★★★★ Client-side rendering, lazy loading | **React gana** |
| Velocidad de desarrollo (MVP) | ★★★★★ Todo en Python, sin build step | ★★★☆☆ Requiere setup, build pipeline | **Dash gana** |
| Curva de aprendizaje (equipo Python) | ★★★★★ Solo Python | ★★☆☆☆ Requiere TS + React + build tools | **Dash gana** |

**Score**: Dash 3/13, React 10/13

---

## 3. Limitaciones Críticas de Dash para Este Proyecto

### 3.1 Arquitectura de Callbacks (Round-Trip Obligatorio)

Cada interacción del usuario genera un HTTP request al servidor:

```
[Usuario hace click] → HTTP POST → Flask procesa → HTTP Response → Browser actualiza
```

**Impacto real en la app**:
- Click en gráfica para filtrar: ~200-500ms de latencia
- Typing en chat IA: cada keystroke puede disparar callbacks
- Cambiar de tab: round-trip completo para renderizar contenido
- 27 archivos de callbacks = ~3,500 líneas de boilerplate reactivo

En React, la mayoría de estas interacciones serían **instantáneas** (client-side) sin tocar el servidor.

### 3.2 No Hay Streaming Real

El chat con IA actualmente muestra la respuesta completa de golpe. No puede hacer streaming token-by-token como ChatGPT porque:
- Dash no soporta Server-Sent Events (SSE) nativamente
- Workaround con `dcc.Interval` + polling es ineficiente y genera flicker
- La UX del chat se siente estática comparada con productos modernos de IA

### 3.3 Drag-and-Drop Inviable

El constructor de dashboards necesita:
- Arrastrar widgets desde un panel lateral al canvas
- Reorganizar widgets en una grilla
- Resize libre (no solo ciclar 4→6→12)
- Preview del drop zone

En Dash:
- `dash-draggable` (wrapper de react-grid-layout) está sin mantenimiento desde 2023
- Cualquier interacción drag requiere round-trip al server = latencia inaceptable
- **Se tuvo que implementar con botones estáticos** en vez de drag-drop real

### 3.4 Estado Global Limitado

`dcc.Store` solo soporta:
- `memory` (se pierde al refrescar)
- `session` (se pierde al cerrar tab)
- `local` (persiste pero sin estructura)

No hay: middleware, selectors, computed values, undo/redo, optimistic updates, state machines.

**Impacto**: El constructor de dashboards requiere estado complejo (lista de widgets, posiciones, tamaños, historial de cambios) que `dcc.Store` maneja pobremente.

### 3.5 Escalabilidad de Callbacks

Con 27 archivos de callbacks y creciendo:
- No hay forma de componer callbacks (no hay hooks)
- Los pattern-matching callbacks (`{"type": "xxx", "index": ALL}`) son frágiles
- Debugging es difícil (no hay DevTools como React DevTools)
- Testing de callbacks requiere selenium/playwright (no unit tests simples)

### 3.6 Ecosistema de Componentes Limitado

| Necesidad | Dash | React |
|-----------|------|-------|
| Date range picker avanzado | `dcc.DatePickerRange` (básico) | react-datepicker, shadcn/ui (completo) |
| Rich text editor | No existe | TipTap, Lexical, Plate |
| Markdown rendering | `dcc.Markdown` (básico) | react-markdown + rehype (completo) |
| Skeleton loading | No existe | Nativo en cualquier UI kit |
| Toast/notifications | Manual con `dbc.Alert` | Sonner, react-hot-toast |
| Command palette (Cmd+K) | No existe | cmdk (shadcn), kbar |
| Multi-select con search | `dcc.Dropdown` (limitado) | react-select, cmdk |
| Virtualized lists | No existe | TanStack Virtual, react-window |
| Animated transitions | No existe | Framer Motion, React Spring |

---

## 4. Propuesta: React + TypeScript + FastAPI

### Arquitectura Propuesta

```
┌─────────────────────────────────────────────────┐
│                    Frontend                      │
│  React 19 + TypeScript + Vite                   │
│  ├── UI: shadcn/ui + Tailwind CSS               │
│  ├── Charts: Plotly.js (o Recharts/Tremor)      │
│  ├── State: Zustand + TanStack Query            │
│  ├── Router: TanStack Router                    │
│  ├── Grid: react-grid-layout                    │
│  ├── Chat: Vercel AI SDK (streaming)            │
│  └── Build: Vite + pnpm                         │
├─────────────────────────────────────────────────┤
│                     API                          │
│  FastAPI + Python 3.12                          │
│  ├── Auth: JWT (fastapi-users)                  │
│  ├── AI: Anthropic + OpenAI (streaming SSE)     │
│  ├── ORM: SQLAlchemy 2.x (async)               │
│  ├── Validation: Pydantic v2                    │
│  ├── Tasks: Celery / ARQ (background jobs)      │
│  └── Docs: Auto-generated OpenAPI/Swagger       │
├─────────────────────────────────────────────────┤
│               Base de Datos                      │
│  PostgreSQL 15 (sin cambios)                    │
│  ├── dbt (sin cambios)                          │
│  ├── Star schema (sin cambios)                  │
│  └── Extractores Python (sin cambios)           │
└─────────────────────────────────────────────────┘
```

### Beneficios Concretos

#### 4.1 Constructor de Dashboards Real

```typescript
// Con react-grid-layout — drag, drop, resize nativo
<ResponsiveGridLayout
  layouts={layouts}
  onLayoutChange={handleLayoutChange}
  draggableHandle=".widget-header"
  isResizable={true}
>
  {widgets.map(w => (
    <div key={w.id} data-grid={w.grid}>
      <WidgetCard widget={w} onRemove={remove} onInfo={showInfo} />
    </div>
  ))}
</ResponsiveGridLayout>
```

**Resultado**: Drag-and-drop real, resize libre, snap-to-grid, todo client-side sin latencia.

#### 4.2 Chat IA con Streaming

```typescript
// Con Vercel AI SDK — streaming token-by-token
const { messages, input, handleSubmit, isLoading } = useChat({
  api: '/api/chat',
  onFinish: (message) => {
    if (message.toolInvocations) {
      // Auto-render chart from SQL result
      addWidgetToCanvas(message.toolInvocations[0].result);
    }
  }
});
```

**Resultado**: Respuestas de IA aparecen token por token como ChatGPT, no de golpe.

#### 4.3 Cross-Filtering Instantáneo

```typescript
// Estado global con Zustand — sin round-trip
const useFilterStore = create((set) => ({
  activeFilter: null,
  setFilter: (filter) => set({ activeFilter: filter }),
  clearFilter: () => set({ activeFilter: null }),
}));

// Cada widget se suscribe y re-renderiza instantáneamente
function WidgetChart({ data, columns }) {
  const filter = useFilterStore(s => s.activeFilter);
  const filtered = filter ? data.filter(row => row[filter.col] === filter.val) : data;
  return <Plot data={filtered} ... />;
}
```

#### 4.4 API Tipada y Documentada

```python
# FastAPI — auto-genera OpenAPI docs, validación con Pydantic
@router.post("/api/queries/{query_id}/execute")
async def execute_query(
    query_id: int,
    params: QueryParams,
    user: User = Depends(get_current_user),
) -> QueryResult:
    result = await ai_agent.process(params.question, user.tenant_id)
    return QueryResult(data=result.data, chart_type=result.chart_type, sql=result.sql)
```

**Resultado**: Documentación automática en `/docs`, validación de tipos en request/response, async nativo.

---

## 5. Estrategia de Migración

### Opción A: Migración Incremental (Recomendada)

Mantener el backend Python pero separar frontend gradualmente.

```
Fase 1 (2-3 semanas): FastAPI wrapper
├── Crear FastAPI app que sirve como API
├── Mover lógica de services/ a endpoints REST
├── Dash sigue funcionando en paralelo
└── Entregable: /api/v1/* endpoints funcionando

Fase 2 (3-4 semanas): React shell + Dashboard Builder
├── Crear app React con Vite + shadcn/ui
├── Implementar Dashboard Builder con react-grid-layout
├── Conectar a FastAPI endpoints
├── Chat IA con streaming (SSE)
└── Entregable: Constructor de dashboards funcional en React

Fase 3 (2-3 semanas): Migrar páginas restantes
├── Home, Query List, Query Chat, Data Explorer
├── Dashboard Unificado (Visionamos) con tabs
├── Autenticación JWT completa
└── Entregable: App React completa, Dash deprecado

Fase 4 (1-2 semanas): Polish + Deploy
├── Testing E2E con Playwright
├── Performance optimization (lazy loading, code splitting)
├── Docker multi-stage build
├── CI/CD pipeline
└── Entregable: Deploy producción
```

**Tiempo total estimado: 8-12 semanas** (1 desarrollador full-stack)

### Opción B: Reescritura Completa

Reconstruir todo desde cero con React + FastAPI.

- **Ventaja**: Arquitectura limpia sin deuda técnica
- **Desventaja**: 10-16 semanas, la app actual queda sin updates durante ese periodo
- **Riesgo**: Alto — features existentes pueden perderse o regresionar

### Opción C: Mejoras dentro de Dash (No Recomendada)

Seguir con Dash pero agregar workarounds:
- `dash-draggable` para drag-drop (sin mantenimiento)
- `dcc.Interval` para simular streaming (flicker)
- Más callbacks para features complejas (deuda técnica)

**Problema**: Cada feature nueva requiere más workarounds, la complejidad crece exponencialmente.

---

## 6. Comparación de Esfuerzo

### Implementar Features Faltantes en Dash vs React

| Feature | Esfuerzo en Dash | Esfuerzo en React | Calidad en Dash | Calidad en React |
|---------|-----------------|-------------------|-----------------|------------------|
| Drag-drop dashboard builder | 3-4 semanas | 1 semana | Baja (workaround) | Alta (nativo) |
| Chat IA con streaming | 2-3 semanas | 3 días | Media (polling) | Alta (SSE nativo) |
| Cross-filter instantáneo | 1-2 semanas | 2-3 días | Media (round-trip) | Alta (client-side) |
| Undo/redo en builder | 2 semanas | 2 días | Baja (manual) | Alta (zustand middleware) |
| Skeleton loading | 1 semana | 2 horas | Baja (hack) | Alta (nativo) |
| Animated transitions | No viable | 1-2 días | N/A | Alta (Framer Motion) |
| Multi-tenant auth | Ya existe | 3-4 días | Funcional | Funcional |
| Exportar dashboard a PDF | 1 semana | 3 días | Media | Alta |

**Total para features faltantes**:
- **En Dash**: ~10-14 semanas, calidad comprometida
- **En React**: ~3-4 semanas (después de setup inicial de 2-3 semanas)

---

## 7. Qué se Reutiliza del Proyecto Actual

### Se Reutiliza Completamente (sin cambios)

| Componente | Razón |
|-----------|-------|
| PostgreSQL + esquema completo | Idéntico — React consume misma DB |
| dbt models + star schema | Idéntico — transformaciones no cambian |
| Extractores Python (scripts/) | Idéntico — pipeline ETL independiente |
| n8n workflows | Idéntico — orquestación independiente |
| Docker infrastructure | Se adapta, no se reescribe |
| CSS variables / design tokens | Se migran a Tailwind config |

### Se Adapta (misma lógica, nuevo formato)

| Componente | Cambio |
|-----------|--------|
| `ai_agent.py` (676 líneas) | → FastAPI endpoint con SSE streaming |
| `data_service.py` (1,052 líneas) | → FastAPI endpoints async |
| `chart_service.py` (781 líneas) | → Plotly.js configs en frontend |
| `storage_service.py` | → FastAPI CRUD endpoints |
| `label_service.py` | → i18n dict en frontend |
| Lógica de callbacks | → React hooks + API calls |

### Se Descarta

| Componente | Razón |
|-----------|-------|
| Archivos de layout Dash (13) | Reemplazados por componentes React |
| Archivos de callback (27) | Reemplazados por hooks + API calls |
| `main.py` (Dash app + navbar) | Reemplazado por React app + FastAPI |
| `dash_table` usage | Reemplazado por TanStack Table |

---

## 8. Stack Propuesto Detallado

### Frontend

| Categoría | Tecnología | Justificación |
|-----------|-----------|---------------|
| Framework | **React 19** | Ecosystem más grande, comunidad activa |
| Lenguaje | **TypeScript 5.x** | Type safety, mejor DX, refactoring seguro |
| Build | **Vite 6** | Build rápido, HMR instantáneo |
| UI Kit | **shadcn/ui + Tailwind CSS** | Componentes copiables, diseño limpio, altamente personalizable |
| Charts | **Plotly.js** (o Tremor para dashboards) | Compatibilidad con charts existentes |
| State | **Zustand** (global) + **TanStack Query** (server) | Simple, performante, sin boilerplate |
| Router | **TanStack Router** | Type-safe, file-based routing |
| Grid | **react-grid-layout** | Standard para dashboards, mantenido activamente |
| Chat IA | **Vercel AI SDK** | Streaming nativo, tool calling, multi-provider |
| Tables | **TanStack Table** | Sorting, filtering, pagination, virtualización |
| Forms | **React Hook Form + Zod** | Validación type-safe |
| Package Mgr | **pnpm** | Rápido, ahorra espacio en disco |

### Backend

| Categoría | Tecnología | Justificación |
|-----------|-----------|---------------|
| Framework | **FastAPI 0.115+** | Async nativo, auto-docs, Pydantic v2 |
| Auth | **fastapi-users** + JWT | Multi-tenant, roles, refresh tokens |
| ORM | **SQLAlchemy 2.x (async)** | Ya existe, solo agregar async adapter |
| AI | **Anthropic + OpenAI** SDKs | Sin cambios, agregar SSE streaming |
| Validation | **Pydantic v2** | Ya se usa en config, extender a todo |
| Background | **ARQ** (o Celery) | Pipeline ETL, AI tasks pesadas |
| CORS | **fastapi-cors** | Para separar frontend/backend |
| Docs | **Auto-generados** | OpenAPI 3.1 gratis con FastAPI |

---

## 9. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|-----------|
| Curva de aprendizaje TypeScript/React | Alto | Fase incremental, un módulo a la vez |
| Pérdida de features durante migración | Alto | Migración paralela, Dash sigue vivo hasta Fase 3 |
| Complejidad de deployment (2 apps) | Medio | Docker multi-stage, nginx para routing |
| Tiempo de entrega > estimado | Medio | Priorizar constructor + chat IA (mayor valor) |
| Compatibilidad de charts Plotly.py → Plotly.js | Bajo | Plotly.js es la base de Plotly.py, misma API |

---

## 10. Recomendación Final

### Veredicto: **Migrar a React + TypeScript + FastAPI**

**Razón principal**: Las 3 funcionalidades core que definen el valor del producto (constructor de dashboards con drag-drop, chat IA con streaming, interactividad bidireccional consultas↔tableros) son **significativamente más difíciles y de menor calidad** en Dash que en React.

**Dash es excelente para**:
- Prototipos rápidos de dashboards
- Equipos 100% Python que no van a tocar JavaScript
- Apps de visualización read-only (sin mucha interacción del usuario)

**Dash NO es adecuado para**:
- Aplicaciones interactivas tipo SaaS
- Constructores drag-and-drop
- Chat en tiempo real con streaming
- Estado complejo (multi-widget, undo/redo, cross-filtering)
- Apps que necesitan crecer en features de UI

### Plan de Acción Sugerido

1. **Semana 1-2**: Setup React + FastAPI, migrar auth + endpoints principales
2. **Semana 3-5**: Dashboard Builder con react-grid-layout + chat IA con streaming
3. **Semana 6-8**: Migrar Query page, Query List, Home, Data Explorer
4. **Semana 9-10**: Dashboard Unificado (Visionamos) + tabs por canal
5. **Semana 11-12**: Testing, polish, deploy production

### Inversión Justificada

| Métrica | Dash (seguir) | React (migrar) |
|---------|--------------|-----------------|
| Tiempo para features completas | 10-14 semanas de workarounds | 8-12 semanas de desarrollo limpio |
| Calidad UX resultante | 5/10 (limitaciones de framework) | 9/10 (estándar SaaS moderno) |
| Mantenibilidad a 12 meses | Decreciente (más workarounds) | Creciente (ecosystem maduro) |
| Capacidad de agregar features nuevas | Cada vez más lenta | Constante |
| Atracción de talento | Limitado (nicho Dash) | Amplio (React es el estándar) |

**La migración se paga sola**: el tiempo que se ahorraría implementando futuras features en React vs Dash justifica la inversión inicial de migración.

---

## Anexo A: Librerías Clave del Nuevo Stack

```json
{
  "dependencies": {
    "react": "^19.0",
    "react-dom": "^19.0",
    "typescript": "^5.7",
    "@tanstack/react-query": "^5.0",
    "@tanstack/react-router": "^1.0",
    "@tanstack/react-table": "^8.0",
    "zustand": "^5.0",
    "plotly.js": "^2.35",
    "react-plotly.js": "^2.6",
    "react-grid-layout": "^1.5",
    "ai": "^4.0",
    "tailwindcss": "^4.0",
    "zod": "^3.23",
    "react-hook-form": "^7.54",
    "@hookform/resolvers": "^3.0"
  }
}
```

## Anexo B: Estructura de Carpetas Propuesta (React)

```
indigitall-bi-frontend/
├── src/
│   ├── app/                    # Rutas (file-based routing)
│   │   ├── index.tsx           # / — Home
│   │   ├── queries/
│   │   │   ├── index.tsx       # /queries — Lista
│   │   │   └── new.tsx         # /queries/new — Chat IA
│   │   ├── dashboards/
│   │   │   ├── index.tsx       # /dashboards — Galería
│   │   │   ├── builder.tsx     # /dashboards/builder
│   │   │   └── [id].tsx        # /dashboards/:id — Vista
│   │   └── data/
│   │       └── index.tsx       # /data — Explorador
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── charts/             # Plotly wrappers
│   │   ├── dashboard/          # Grid, Widget, WidgetCard
│   │   ├── chat/               # ChatMessage, ChatInput
│   │   └── layout/             # Navbar, Sidebar, Container
│   ├── hooks/
│   │   ├── useChat.ts          # AI chat hook
│   │   ├── useDashboard.ts     # Dashboard state
│   │   └── useQueries.ts       # Query CRUD
│   ├── stores/
│   │   ├── filterStore.ts      # Cross-filtering state
│   │   ├── dashboardStore.ts   # Builder state
│   │   └── authStore.ts        # Auth + tenant
│   ├── services/
│   │   └── api.ts              # FastAPI client (fetch wrapper)
│   ├── lib/
│   │   ├── chart-config.ts     # Plotly defaults + InDigitall theme
│   │   └── labels.ts           # i18n labels (Spanish)
│   └── types/
│       ├── query.ts            # SavedQuery, QueryResult
│       ├── dashboard.ts        # Dashboard, Widget, GridLayout
│       └── api.ts              # API response types
├── tailwind.config.ts          # InDigitall design tokens
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## Anexo C: Estructura Backend (FastAPI)

```
indigitall-bi-api/
├── app/
│   ├── main.py                 # FastAPI app, CORS, lifespan
│   ├── config.py               # Pydantic settings (reutilizado)
│   ├── auth/
│   │   ├── jwt.py              # JWT encode/decode
│   │   └── dependencies.py     # get_current_user, require_tenant
│   ├── routers/
│   │   ├── queries.py          # /api/queries/* — CRUD + execute
│   │   ├── dashboards.py       # /api/dashboards/* — CRUD
│   │   ├── chat.py             # /api/chat — SSE streaming AI
│   │   ├── data.py             # /api/data — Schema explorer
│   │   ├── kpis.py             # /api/kpis/* — Dashboard data
│   │   └── pipeline.py         # /api/pipeline — ETL trigger
│   ├── services/               # Reutilizados de app actual
│   │   ├── ai_agent.py         # → Agregar streaming
│   │   ├── data_service.py     # → Agregar async
│   │   ├── storage_service.py  # → Sin cambios grandes
│   │   └── ...
│   └── models/
│       ├── database.py         # SQLAlchemy async engine
│       └── schemas.py          # ORM models (reutilizados)
├── requirements.txt
└── Dockerfile
```
