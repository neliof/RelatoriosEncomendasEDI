# Local Read-Only Dashboard Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local read-only web dashboard served by the existing FastAPI API.

**Architecture:** Add static dashboard assets under `src/integration_app/api/static/` and mount them from `integration_app.api.app.create_app`. The dashboard uses plain HTML/CSS/JavaScript with relative API calls to the existing JSON endpoints, avoiding a JavaScript build step.

**Tech Stack:** Python 3.11+, FastAPI, Starlette static files, plain HTML/CSS/JavaScript, pytest, FastAPI TestClient.

**Spec:** `docs/superpowers/specs/2026-09-16-local-readonly-dashboard-frontend-design.md`

## Global Constraints

- Dashboard is local and read-only.
- Do not add login/authentication in this phase.
- Do not edit `config.yaml`.
- Do not read or expose passwords, `secrets/`, or raw configuration contents.
- Do not alter FTP/SFTP transfer behaviour.
- Do not alter Task Scheduler.
- Do not add a JavaScript build step or npm dependency.
- Use TDD for implementation changes.

---

## File Structure

- Modify `src/integration_app/api/app.py`: serve `GET /` and static dashboard assets.
- Create `src/integration_app/api/static/dashboard.html`: dashboard document.
- Create `src/integration_app/api/static/dashboard.css`: operational dashboard styling.
- Create `src/integration_app/api/static/dashboard.js`: fetch and render API data.
- Modify `tests/test_api_app.py`: route and static asset tests.
- Modify `README.md`: mention the dashboard URL.

---

### Task 1: Serve Dashboard HTML And Static Assets

**Files:**
- Modify: `src/integration_app/api/app.py`
- Create: `src/integration_app/api/static/dashboard.html`
- Create: `src/integration_app/api/static/dashboard.css`
- Create: `src/integration_app/api/static/dashboard.js`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `create_app(db_path: Path, report_dir: Path) -> FastAPI`
- Produces: `GET /` returning dashboard HTML.
- Produces: `/static/dashboard.css` and `/static/dashboard.js`.

- [ ] **Step 1: Write failing tests for dashboard route and static assets**

Append to `tests/test_api_app.py`:

```python
def test_dashboard_root_serves_html_with_static_assets(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Relatorios Encomendas EDI EF" in response.text
    assert "/static/dashboard.css" in response.text
    assert "/static/dashboard.js" in response.text


def test_dashboard_static_assets_are_served(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")
    client = TestClient(app)

    css = client.get("/static/dashboard.css")
    js = client.get("/static/dashboard.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert ".metric-card" in css.text
    assert js.status_code == 200
    assert "text/javascript" in js.headers["content-type"]
    assert "fetchSummary" in js.text
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: FAIL because `/` and `/static/dashboard.*` are not served yet.

- [ ] **Step 3: Create minimal dashboard assets**

Create `src/integration_app/api/static/dashboard.html`:

```html
<!doctype html>
<html lang="pt-PT">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Relatorios Encomendas EDI EF</title>
    <link rel="stylesheet" href="/static/dashboard.css">
  </head>
  <body>
    <main class="shell">
      <header class="topbar">
        <div>
          <h1>Relatorios Encomendas EDI EF</h1>
          <p id="last-updated">A carregar dados...</p>
        </div>
        <button id="refresh-button" type="button">Actualizar</button>
      </header>

      <section class="metrics" aria-label="Resumo operacional">
        <article class="metric-card"><span>Total</span><strong id="metric-total">-</strong></article>
        <article class="metric-card"><span>Enviados</span><strong id="metric-sent">-</strong></article>
        <article class="metric-card"><span>Confirmados</span><strong id="metric-confirmed">-</strong></article>
        <article class="metric-card"><span>Pendentes</span><strong id="metric-pending">-</strong></article>
        <article class="metric-card"><span>Duplicados</span><strong id="metric-duplicate">-</strong></article>
        <article class="metric-card"><span>Falhados</span><strong id="metric-failed">-</strong></article>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2>Eventos recentes</h2>
          <form id="event-filters" class="filters">
            <select id="status-filter" aria-label="Estado">
              <option value="">Todos</option>
              <option value="sent">Enviados</option>
              <option value="confirmed">Confirmados</option>
              <option value="duplicate">Duplicados</option>
              <option value="failed">Falhados</option>
              <option value="detected">Detectados</option>
            </select>
            <input id="connection-filter" type="search" placeholder="Ligacao" aria-label="Ligacao">
            <input id="limit-filter" type="number" min="1" max="500" value="100" aria-label="Limite">
          </form>
        </div>
        <p id="events-error" class="notice" hidden></p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Ligacao</th>
                <th>Protocolo</th>
                <th>Estado</th>
                <th>Confirmacao</th>
                <th>Ficheiro</th>
                <th>Erro</th>
              </tr>
            </thead>
            <tbody id="events-body"></tbody>
          </table>
        </div>
      </section>

      <section class="grid">
        <article class="panel">
          <h2>Fornecedores</h2>
          <p id="suppliers-error" class="notice" hidden></p>
          <div id="suppliers-list" class="list"></div>
        </article>
        <article class="panel">
          <h2>Relatorios</h2>
          <p id="reports-error" class="notice" hidden></p>
          <div id="reports-list" class="list"></div>
        </article>
      </section>
    </main>
    <script src="/static/dashboard.js" defer></script>
  </body>
</html>
```

Create `src/integration_app/api/static/dashboard.css`:

```css
:root {
  color-scheme: light;
  --bg: #f4f6f8;
  --panel: #ffffff;
  --text: #18212f;
  --muted: #697586;
  --line: #d9e1ea;
  --accent: #1f6feb;
  --success: #1f8a5b;
  --warning: #9a6b00;
  --danger: #c0392b;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Arial, Helvetica, sans-serif;
}

.shell {
  width: min(1400px, 100%);
  margin: 0 auto;
  padding: 24px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 26px;
  line-height: 1.2;
}

h2 {
  font-size: 18px;
}

.topbar p,
.notice {
  color: var(--muted);
  margin-top: 6px;
}

button,
select,
input {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #ffffff;
  color: var(--text);
  font: inherit;
  min-height: 36px;
}

button {
  background: var(--accent);
  color: #ffffff;
  border-color: var(--accent);
  padding: 0 14px;
  cursor: pointer;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card,
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.metric-card {
  min-height: 82px;
  padding: 14px;
}

.metric-card span {
  display: block;
  color: var(--muted);
  font-size: 13px;
}

.metric-card strong {
  display: block;
  font-size: 28px;
  margin-top: 8px;
}

.panel {
  padding: 16px;
  margin-bottom: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filters input,
.filters select {
  padding: 0 10px;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 900px;
}

th,
td {
  border-bottom: 1px solid var(--line);
  padding: 10px 8px;
  text-align: left;
  vertical-align: top;
  font-size: 14px;
}

th {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
}

.status {
  display: inline-block;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 700;
}

.status.sent,
.status.confirmed {
  background: #e7f6ee;
  color: var(--success);
}

.status.duplicate,
.status.pending,
.status.detected {
  background: #fff4d6;
  color: var(--warning);
}

.status.failed {
  background: #fde8e5;
  color: var(--danger);
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.list-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
}

.list-row small {
  color: var(--muted);
}

@media (max-width: 900px) {
  .shell {
    padding: 16px;
  }

  .topbar,
  .panel-header {
    align-items: stretch;
    flex-direction: column;
  }

  .metrics,
  .grid {
    grid-template-columns: 1fr;
  }

  .filters {
    display: grid;
    grid-template-columns: 1fr;
  }
}
```

Create `src/integration_app/api/static/dashboard.js`:

```javascript
const state = {
  summary: null,
  events: [],
  suppliers: [],
  reports: [],
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("refresh-button").addEventListener("click", refreshAll);
  document.getElementById("event-filters").addEventListener("input", fetchEvents);
  refreshAll();
});

async function refreshAll() {
  await Promise.all([fetchSummary(), fetchEvents(), fetchSuppliers(), fetchReports()]);
  document.getElementById("last-updated").textContent = `Ultima actualizacao: ${new Date().toLocaleString("pt-PT")}`;
}

async function fetchSummary() {
  try {
    const summary = await getJson("/summary");
    state.summary = summary;
    setMetric("metric-total", summary.total_files);
    setMetric("metric-sent", summary.sent_count);
    setMetric("metric-confirmed", summary.confirmed_count);
    setMetric("metric-pending", summary.pending_count);
    setMetric("metric-duplicate", summary.duplicate_count);
    setMetric("metric-failed", summary.failed_count);
  } catch (error) {
    document.getElementById("last-updated").textContent = `Erro no resumo: ${error.message}`;
  }
}

async function fetchEvents() {
  const params = new URLSearchParams();
  const status = document.getElementById("status-filter").value;
  const connection = document.getElementById("connection-filter").value.trim();
  const limit = document.getElementById("limit-filter").value;
  if (status) params.set("status", status);
  if (connection) params.set("connection_name", connection);
  if (limit) params.set("limit", limit);

  try {
    hideError("events-error");
    const payload = await getJson(`/events?${params.toString()}`);
    state.events = payload.items || [];
    renderEvents();
  } catch (error) {
    showError("events-error", error);
  }
}

async function fetchSuppliers() {
  try {
    hideError("suppliers-error");
    const payload = await getJson("/suppliers");
    state.suppliers = payload.items || [];
    renderSuppliers();
  } catch (error) {
    showError("suppliers-error", error);
  }
}

async function fetchReports() {
  try {
    hideError("reports-error");
    const payload = await getJson("/reports");
    state.reports = payload.items || [];
    renderReports();
  } catch (error) {
    showError("reports-error", error);
  }
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function setMetric(id, value) {
  document.getElementById(id).textContent = value ?? "-";
}

function renderEvents() {
  const body = document.getElementById("events-body");
  body.innerHTML = "";
  if (state.events.length === 0) {
    body.innerHTML = '<tr><td colspan="7">Sem eventos para apresentar.</td></tr>';
    return;
  }
  for (const event of state.events) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${formatDate(event.detected_at)}</td>
      <td>${escapeHtml(event.connection_name || "")}</td>
      <td>${escapeHtml(event.protocol || "")}</td>
      <td>${statusBadge(event.status)}</td>
      <td>${escapeHtml(event.confirmation_status || "")}</td>
      <td>${escapeHtml(shortPath(event.local_path || ""))}</td>
      <td>${escapeHtml(event.error_message || "")}</td>
    `;
    body.appendChild(row);
  }
}

function renderSuppliers() {
  const container = document.getElementById("suppliers-list");
  container.innerHTML = "";
  if (state.suppliers.length === 0) {
    container.textContent = "Sem fornecedores para apresentar.";
    return;
  }
  for (const supplier of state.suppliers) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(supplier.supplier_name || "UNKNOWN")}</strong>
        <small>Total: ${supplier.total_files ?? 0}</small>
      </div>
      <small>Duplicados: ${supplier.duplicate_count ?? 0} | Falhados: ${supplier.failed_count ?? 0}</small>
    `;
    container.appendChild(row);
  }
}

function renderReports() {
  const container = document.getElementById("reports-list");
  container.innerHTML = "";
  if (state.reports.length === 0) {
    container.textContent = "Sem relatorios para apresentar.";
    return;
  }
  for (const report of state.reports.slice(0, 12)) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(report.name || "")}</strong>
        <small>${escapeHtml(report.kind || "other")} | ${formatBytes(report.size_bytes)}</small>
      </div>
      <small>${formatTimestamp(report.modified_at)}</small>
    `;
    container.appendChild(row);
  }
}

function statusBadge(status) {
  const value = status || "unknown";
  return `<span class="status ${escapeHtml(value)}">${escapeHtml(value)}</span>`;
}

function showError(id, error) {
  const element = document.getElementById(id);
  element.hidden = false;
  element.textContent = `Erro ao carregar dados: ${error.message}`;
}

function hideError(id) {
  const element = document.getElementById(id);
  element.hidden = true;
  element.textContent = "";
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("pt-PT");
}

function formatTimestamp(value) {
  if (!value) return "";
  return new Date(Number(value) * 1000).toLocaleString("pt-PT");
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function shortPath(value) {
  const parts = String(value).split(/[\\/]/);
  return parts[parts.length - 1] || value;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
```

- [ ] **Step 4: Mount dashboard in FastAPI**

Modify `src/integration_app/api/app.py`:

```python
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
```

Add inside `create_app`, immediately after `app = FastAPI(...)`:

```python
    static_dir = Path(__file__).with_name("static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "dashboard.html")
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/integration_app/api/app.py src/integration_app/api/static tests/test_api_app.py
git commit -m "feat: serve local dashboard"
```

---

### Task 2: Verify Dashboard Data Contract

**Files:**
- Modify: `tests/test_api_app.py`
- Modify: `src/integration_app/api/static/dashboard.html`
- Modify: `src/integration_app/api/static/dashboard.js`

**Interfaces:**
- Consumes: `/summary`, `/events`, `/suppliers`, `/reports`.
- Produces: stable DOM ids consumed by `dashboard.js`.

- [ ] **Step 1: Write contract tests for required DOM hooks**

Append to `tests/test_api_app.py`:

```python
def test_dashboard_html_contains_required_dom_hooks(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    html = TestClient(app).get("/").text

    required_ids = [
        "last-updated",
        "refresh-button",
        "metric-total",
        "metric-sent",
        "metric-confirmed",
        "metric-pending",
        "metric-duplicate",
        "metric-failed",
        "event-filters",
        "status-filter",
        "connection-filter",
        "limit-filter",
        "events-body",
        "suppliers-list",
        "reports-list",
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in html
```

- [ ] **Step 2: Write contract test for JavaScript API calls**

Append to `tests/test_api_app.py`:

```python
def test_dashboard_javascript_uses_existing_readonly_endpoints(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    javascript = TestClient(app).get("/static/dashboard.js").text

    assert 'getJson("/summary")' in javascript
    assert 'getJson(`/events?' in javascript
    assert 'getJson("/suppliers")' in javascript
    assert 'getJson("/reports")' in javascript
    assert "fetch(" in javascript
    assert "method:" not in javascript
```

- [ ] **Step 3: Run tests and verify they fail if hooks are missing**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: PASS if Task 1 used the exact provided HTML/JS. If it fails, update only the HTML/JS ids or calls to match the contract.

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/integration_app/api/static/dashboard.html src/integration_app/api/static/dashboard.js tests/test_api_app.py
git commit -m "test: lock dashboard data contract"
```

---

### Task 3: Document Dashboard Usage And Run Final Verification

**Files:**
- Modify: `README.md`
- Test: full test suite.

**Interfaces:**
- Consumes: `python -m integration_app.api --db data/integration.db --reports reports`
- Produces: documented dashboard URL `http://127.0.0.1:8000/`

- [ ] **Step 1: Update README dashboard documentation**

Modify the `API Local de Monitorizacao` section in `README.md` to include the dashboard URL:

````markdown
Depois de arrancar, abrir o dashboard no browser:

```text
http://127.0.0.1:8000/
```

O dashboard mostra resumo operacional, eventos recentes, fornecedores e relatorios gerados. Continua a ser apenas de leitura.
````

- [ ] **Step 2: Run focused API/dashboard tests**

Run:

```powershell
python -m pytest tests/test_api_app.py tests/test_api_cli.py tests/test_api_read_models.py -v
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 4: Run smoke test for app title and dashboard route**

Run:

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from pathlib import Path; from fastapi.testclient import TestClient; from integration_app.api.app import create_app; app=create_app(Path('data/integration.db'), Path('reports')); client=TestClient(app); print(app.title); print(client.get('/').status_code)"
```

Expected output:

```text
Relatorios Encomendas EDI EF API
200
```

- [ ] **Step 5: Check git status**

Run:

```powershell
git status --short
```

Expected: no uncommitted implementation files except environment/cache files already ignored.
`README.md` may appear as modified because Step 1 has not been committed yet.

- [ ] **Step 6: Commit**

```powershell
git add README.md
git commit -m "docs: document local dashboard"
```

---

## Final Verification

- [ ] Run full test suite:

```powershell
python -m pytest -v
```

Expected: PASS.

- [ ] Run smoke test:

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from pathlib import Path; from fastapi.testclient import TestClient; from integration_app.api.app import create_app; app=create_app(Path('data/integration.db'), Path('reports')); client=TestClient(app); print(app.title); print(client.get('/').status_code)"
```

Expected:

```text
Relatorios Encomendas EDI EF API
200
```

- [ ] Check git status:

```powershell
git status --short
```

Expected: clean working tree.
