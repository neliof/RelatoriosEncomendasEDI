const state = {
  summary: null,
  events: [],
  connections: [],
  config: null,
  clients: [],
  suppliers: [],
  reports: [],
};

document.addEventListener("DOMContentLoaded", () => {
  setupNav();
  setupSidebarToggle();
  document.getElementById("refresh-button").addEventListener("click", refreshAll);
  document.getElementById("event-filters").addEventListener("input", fetchEvents);
  document.getElementById("clear-filters-button").addEventListener("click", clearEventFilters);
  document.getElementById("new-connection-form").addEventListener("submit", saveNewConnection);
  document.getElementById("general-config-form").addEventListener("submit", saveGeneralConfig);
  document.getElementById("event-detail-close").addEventListener("click", hideEventDetail);
  document.getElementById("detail-overlay").addEventListener("click", hideEventDetail);
  refreshAll();
});

function setupNav() {
  for (const btn of document.querySelectorAll("[data-view]")) {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  }
}

function setupSidebarToggle() {
  const toggle = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");

  if (toggle) {
    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  document.addEventListener("click", (e) => {
    if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
      sidebar.classList.remove("open");
    }
  });
}

function showView(viewName) {
  for (const view of document.querySelectorAll(".view")) {
    view.classList.toggle("active", view.id === `view-${viewName}`);
  }

  for (const btn of document.querySelectorAll("[data-view]")) {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  }

  document.querySelector(".sidebar").classList.remove("open");
}

async function refreshAll() {
  await Promise.all([
    fetchSummary(),
    fetchEvents(),
    fetchConnections(),
    fetchConfigSummary(),
    fetchClients(),
    fetchSuppliers(),
    fetchReports(),
  ]);
  const now = new Date();
  document.getElementById("last-updated").textContent = `Última atualização: ${now.toLocaleString("pt-PT")}`;
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
    renderOperationalAlerts(summary);
  } catch (error) {
    console.error("Erro ao buscar resumo:", error);
  }
}

async function fetchEvents() {
  const params = new URLSearchParams();
  const status = document.getElementById("status-filter").value;
  const connection = document.getElementById("connection-filter").value.trim();
  const dateFrom = document.getElementById("date-from-filter").value;
  const dateTo = document.getElementById("date-to-filter").value;
  const limit = document.getElementById("limit-filter").value;

  if (status) params.set("status", status);
  if (connection) params.set("connection_name", connection);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
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

function clearEventFilters() {
  document.getElementById("status-filter").value = "";
  document.getElementById("connection-filter").value = "";
  document.getElementById("date-from-filter").value = "";
  document.getElementById("date-to-filter").value = "";
  document.getElementById("limit-filter").value = "100";
  fetchEvents();
}

async function fetchClients() {
  try {
    hideError("clients-error");
    const payload = await getJson("/clients");
    state.clients = payload.items || [];
    renderClients();
  } catch (error) {
    showError("clients-error", error);
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

async function fetchConfigSummary() {
  try {
    hideError("config-error");
    const payload = await getJson("/config/summary");
    state.config = payload;
    renderGeneralConfig();
    renderConfigSummary();
  } catch (error) {
    showError("config-error", error);
  }
}

function renderGeneralConfig() {
  if (!state.config) return;
  const input = document.getElementById("generix-storage");
  if (input && state.config.app?.generix_storage_root) {
    input.value = state.config.app.generix_storage_root;
  }
}

async function saveGeneralConfig(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const generixStorage = document.getElementById("generix-storage").value.trim();

  try {
    button.disabled = true;
    button.textContent = "A guardar...";

    await patchJson("/config/app", { generix_storage_root: generixStorage || null });
    await fetchConfigSummary();
    showConfigMessage(form, "Configurações guardadas.", "success");
  } catch (error) {
    showConfigMessage(form, `Erro ao guardar: ${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Guardar Configurações";
  }
}

function renderConfigSummary() {
  const container = document.getElementById("config-list");
  container.innerHTML = "";
  const connections = state.config?.connections || [];

  if (connections.length === 0) {
    container.innerHTML = `<div style="padding: 16px; text-align: center; color: var(--text-tertiary);">
      ${state.config?.config_exists === false ? "Config.yaml não encontrado." : "Sem ligações configuradas."}
    </div>`;
    return;
  }

  for (const connection of connections) {
    const row = document.createElement("div");
    row.className = "config-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(connection.name || "")}</strong>
        <small>${escapeHtml(connection.protocol || "")} | ${connection.enabled ? "Ativo" : "Inativo"} | ${escapeHtml(connection.file_pattern || "")}</small>
      </div>
      <form class="config-form">
        <div class="form-row">
          <div class="form-field">
            <label>Origem</label>
            <input name="source_dir" value="${escapeHtml(connection.source_dir || "")}">
          </div>
          <div class="form-field">
            <label>Destino</label>
            <input name="remote_dir" value="${escapeHtml(connection.remote_dir || "")}">
          </div>
        </div>
        <div class="form-row">
          <div class="form-field">
            <label>Padrão</label>
            <input name="file_pattern" value="${escapeHtml(connection.file_pattern || "")}">
          </div>
          <div class="form-field">
            <label>Duplicados</label>
            <select name="duplicate_policy">
              <option value="report_only"${connection.duplicate_policy === "report_only" ? " selected" : ""}>Reportar</option>
              <option value="move_to_duplicates"${connection.duplicate_policy === "move_to_duplicates" ? " selected" : ""}>Mover</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <label class="checkbox-label">
            <input name="confirm_remote_processing" type="checkbox"${connection.confirm_remote_processing ? " checked" : ""}>
            <span>Confirmar processamento remoto</span>
          </label>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">Guardar</button>
          <button type="button" class="btn btn-secondary config-action-btn" data-action="toggle">${connection.enabled ? "Desativar" : "Ativar"}</button>
          <button type="button" class="btn btn-secondary edit-credentials-btn">Editar Credenciais</button>
          <button type="button" class="btn btn-secondary edit-schedule-btn">Agendar</button>
          <span class="form-message" aria-live="polite"></span>
        </div>
      </form>
    `;

    const actionBtn = row.querySelector(".config-action-btn");
    actionBtn.addEventListener("click", () => toggleConnectionEnabled(connection.name, !connection.enabled));

    const editCredsBtn = row.querySelector(".edit-credentials-btn");
    editCredsBtn.addEventListener("click", () => openEditCredentials(connection));

    const editScheduleBtn = row.querySelector(".edit-schedule-btn");
    editScheduleBtn.addEventListener("click", () => openEditSchedule(connection));

    row.querySelector(".config-form").addEventListener("submit", (event) => saveConnectionSettings(event, connection.name));
    container.appendChild(row);
  }
}

async function toggleConnectionEnabled(connectionName, enabled) {
  try {
    await patchJson(`/config/connections/${encodeURIComponent(connectionName)}`, { enabled });
    await fetchConfigSummary();
  } catch (error) {
    showError("config-error", error);
  }
}

function openEditCredentials(connection) {
  const panel = document.getElementById("edit-credentials-panel");
  const nameSpan = document.getElementById("edit-connection-name");
  const form = document.getElementById("edit-credentials-form");

  nameSpan.textContent = connection.name;
  form.reset();

  document.getElementById("edit-host").value = connection.host || "";
  document.getElementById("edit-port").value = connection.port || 21;
  document.getElementById("edit-username").value = connection.username || "";
  document.getElementById("edit-password-env").value = connection.password_env || "";

  form.onsubmit = (e) => saveEditCredentials(e, connection.name);
  document.getElementById("edit-credentials-cancel").onclick = () => {
    panel.hidden = true;
  };

  panel.hidden = false;
}

async function saveEditCredentials(event, connectionName) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const panel = document.getElementById("edit-credentials-panel");

  const credentials = {
    host: document.getElementById("edit-host").value.trim(),
    port: Number(document.getElementById("edit-port").value),
    username: document.getElementById("edit-username").value.trim(),
    password_env: document.getElementById("edit-password-env").value.trim() || null,
  };

  if (!credentials.host || !credentials.username || !credentials.port) {
    showEditMessage("Host, utilizador e porta são obrigatórios.", "error");
    return;
  }

  if (credentials.port <= 0 || credentials.port > 65535) {
    showEditMessage("Porta deve estar entre 1 e 65535.", "error");
    return;
  }

  try {
    button.disabled = true;
    button.textContent = "A guardar...";

    await patchJson(`/config/connections/${encodeURIComponent(connectionName)}/credentials`, credentials);
    await fetchConfigSummary();
    showEditMessage("Credenciais guardadas. Backup criado.", "success");

    setTimeout(() => {
      panel.hidden = true;
    }, 1500);
  } catch (error) {
    showEditMessage(`Erro ao guardar: ${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Guardar Credenciais";
  }
}

function showEditMessage(message, kind) {
  const element = document.getElementById("edit-credentials-message");
  element.textContent = message;
  element.className = `form-message ${kind}`;
}

function openEditSchedule(connection) {
  const panel = document.getElementById("edit-schedule-panel");
  const nameSpan = document.getElementById("schedule-connection-name");
  const form = document.getElementById("edit-schedule-form");

  nameSpan.textContent = connection.name;
  form.reset();

  document.getElementById("schedule-enabled").checked = connection.schedule_enabled || false;
  document.getElementById("schedule-frequency").value = connection.schedule_frequency || "daily";
  document.getElementById("schedule-interval").value = connection.schedule_interval || 1;
  document.getElementById("schedule-hour").value = connection.schedule_hour || 0;
  document.getElementById("schedule-minute").value = connection.schedule_minute || 0;

  form.onsubmit = (e) => saveEditSchedule(e, connection.name);
  document.getElementById("edit-schedule-cancel").onclick = () => {
    panel.hidden = true;
  };

  panel.hidden = false;
}

async function saveEditSchedule(event, connectionName) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const panel = document.getElementById("edit-schedule-panel");

  const schedule = {
    schedule_enabled: document.getElementById("schedule-enabled").checked,
    schedule_frequency: document.getElementById("schedule-frequency").value,
    schedule_interval: Number(document.getElementById("schedule-interval").value),
    schedule_hour: Number(document.getElementById("schedule-hour").value),
    schedule_minute: Number(document.getElementById("schedule-minute").value),
  };

  if (schedule.schedule_interval <= 0) {
    showScheduleMessage("Intervalo deve ser maior que 0.", "error");
    return;
  }

  if (schedule.schedule_hour < 0 || schedule.schedule_hour > 23) {
    showScheduleMessage("Hora deve estar entre 0 e 23.", "error");
    return;
  }

  if (schedule.schedule_minute < 0 || schedule.schedule_minute > 59) {
    showScheduleMessage("Minuto deve estar entre 0 e 59.", "error");
    return;
  }

  try {
    button.disabled = true;
    button.textContent = "A guardar...";

    await patchJson(`/config/connections/${encodeURIComponent(connectionName)}/schedule`, schedule);
    await fetchConfigSummary();
    showScheduleMessage("Agendamento guardado. Backup criado.", "success");

    setTimeout(() => {
      panel.hidden = true;
    }, 1500);
  } catch (error) {
    showScheduleMessage(`Erro ao guardar: ${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Guardar Agendamento";
  }
}

function showScheduleMessage(message, kind) {
  const element = document.getElementById("edit-schedule-message");
  element.textContent = message;
  element.className = `form-message ${kind}`;
}

async function saveConnectionSettings(event, connectionName) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const settings = collectConnectionSettings(form);
  const validationError = validateConnectionSettings(settings);

  if (validationError) {
    showConfigMessage(form, validationError, "error");
    return;
  }

  try {
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = "A guardar...";

    await patchJson(`/config/connections/${encodeURIComponent(connectionName)}`, settings);
    await fetchConfigSummary();

    const refreshed = form.closest(".config-row");
    if (refreshed) {
      showConfigMessage(form, "Configuração guardada. Backup criado.", "success");
    }
  } catch (error) {
    showConfigMessage(form, `Erro ao guardar: ${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Guardar";
  }
}

function collectConnectionSettings(form) {
  const data = new FormData(form);
  return {
    source_dir: String(data.get("source_dir") || ""),
    remote_dir: String(data.get("remote_dir") || ""),
    file_pattern: String(data.get("file_pattern") || ""),
    duplicate_policy: String(data.get("duplicate_policy") || ""),
    confirm_remote_processing: data.has("confirm_remote_processing"),
  };
}

function validateConnectionSettings(settings) {
  if (!settings.source_dir.trim() || !settings.remote_dir.trim() || !settings.file_pattern.trim()) {
    return "Origem, destino e padrão são obrigatórios.";
  }
  if (!["report_only", "move_to_duplicates"].includes(settings.duplicate_policy)) {
    return "Política de duplicados inválida.";
  }
  return "";
}

function showConfigMessage(form, message, kind) {
  const element = form.querySelector(".form-message");
  if (!element) return;
  element.textContent = message;
  element.className = `form-message ${kind}`;
}

async function saveNewConnection(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const { adminPassword, connection } = collectNewConnection(form);
  const validationError = validateNewConnection(connection, adminPassword);

  if (validationError) {
    showConfigMessage(form, validationError, "error");
    return;
  }

  try {
    button.disabled = true;
    button.textContent = "A criar...";

    await postJson("/config/connections", connection, adminPassword);
    form.reset();
    form.querySelector('[name="port"]').value = connection.protocol === "sftp" ? "22" : "21";
    form.querySelector('[name="file_pattern"]').value = "*";
    form.querySelector('[name="confirm_remote_processing"]').checked = true;

    await fetchConfigSummary();
    showConfigMessage(form, "Ligação criada. Backup criado.", "success");
  } catch (error) {
    showConfigMessage(form, `Erro ao criar: ${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Criar Ligação";
  }
}

function collectNewConnection(form) {
  const data = new FormData(form);
  const passwordEnv = String(data.get("password_env") || "").trim();
  const connection = {
    name: String(data.get("name") || "").trim(),
    enabled: true,
    flow_type: "generic",
    protocol: String(data.get("protocol") || "").trim(),
    host: String(data.get("host") || "").trim(),
    port: Number(data.get("port") || 0),
    username: String(data.get("username") || "").trim(),
    source_dir: String(data.get("source_dir") || "").trim(),
    remote_dir: String(data.get("remote_dir") || "").trim(),
    file_pattern: String(data.get("file_pattern") || "").trim(),
    sent_dir: "Enviados",
    error_dir: "Erros",
    duplicate_policy: String(data.get("duplicate_policy") || "").trim(),
    confirm_remote_processing: data.has("confirm_remote_processing"),
  };

  if (passwordEnv) {
    connection.password_env = passwordEnv;
  }

  return {
    adminPassword: String(data.get("admin_password") || ""),
    connection,
  };
}

function validateNewConnection(connection, adminPassword) {
  if (!adminPassword) return "Password admin obrigatória.";
  if (!connection.name || !connection.host || !connection.username) return "Nome, host e utilizador são obrigatórios.";
  if (!connection.source_dir || !connection.remote_dir || !connection.file_pattern) return "Origem, destino e padrão são obrigatórios.";
  if (!["ftp", "sftp"].includes(connection.protocol)) return "Protocolo inválido.";
  if (!Number.isInteger(connection.port) || connection.port <= 0) return "Porta inválida.";
  if (!["report_only", "move_to_duplicates"].includes(connection.duplicate_policy)) return "Política de duplicados inválida.";
  return "";
}

async function fetchConnections() {
  try {
    hideError("connections-error");
    const payload = await getJson("/connections");
    state.connections = payload.items || [];
    renderConnections();
  } catch (error) {
    showError("connections-error", error);
  }
}

function renderConnections() {
  const container = document.getElementById("connections-list");
  container.innerHTML = "";

  if (state.connections.length === 0) {
    container.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-tertiary);">Sem ligações para apresentar.</div>`;
    return;
  }

  for (const connection of state.connections) {
    const btn = document.createElement("button");
    btn.className = `connection-row ${connectionRowClass(connection)}`;
    btn.type = "button";
    btn.innerHTML = `
      <strong>${escapeHtml(connection.connection_name || "")}</strong>
      <small>${escapeHtml(connection.protocol || "")} • Total: ${connection.total_files ?? 0}</small>
      <small>Falhados: ${connection.failed_count ?? 0} | Pendentes: ${connection.pending_count ?? 0} | Duplicados: ${connection.duplicate_count ?? 0}</small>
    `;
    btn.addEventListener("click", () => filterEventsByConnection(connection.connection_name));
    container.appendChild(btn);
  }
}

function filterEventsByConnection(connectionName) {
  document.getElementById("connection-filter").value = connectionName || "";
  fetchEvents();
}

function connectionRowClass(connection) {
  if (Number(connection.failed_count || 0) > 0) {
    return "failed";
  }
  if (Number(connection.pending_count || 0) > 0) {
    return "pending";
  }
  return "";
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

async function patchJson(url, payload) {
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function postJson(url, payload, adminPassword) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": adminPassword,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function setMetric(id, value) {
  document.getElementById(id).textContent = value ?? "-";
}

function renderOperationalAlerts(summary) {
  const alerts = [
    { count: summary.failed_count, label: "Falhas", className: "failed" },
    { count: summary.duplicate_count, label: "Duplicados", className: "duplicate" },
    { count: summary.pending_count, label: "Pendentes", className: "pending" },
  ].filter((item) => Number(item.count || 0) > 0);

  const container = document.getElementById("operational-alerts");
  container.innerHTML = "";
  container.hidden = alerts.length === 0;

  for (const alert of alerts) {
    const item = document.createElement("div");
    item.className = `alert-item ${alert.className}`;
    item.innerHTML = `<strong>${alert.count}</strong><span>${alert.label} requerem atenção.</span>`;
    container.appendChild(item);
  }
}

function renderEvents() {
  const body = document.getElementById("events-body");
  body.innerHTML = "";

  if (state.events.length === 0) {
    body.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 40px; color: var(--text-tertiary);">Sem eventos para apresentar.</td></tr>';
    return;
  }

  for (const event of state.events) {
    const row = document.createElement("tr");
    row.className = `event-row ${eventRowClass(event)}`;
    row.innerHTML = `
      <td>${formatDate(event.detected_at)}</td>
      <td>${escapeHtml(event.connection_name || "")}</td>
      <td>${escapeHtml(supplierForEvent(event))}</td>
      <td>${escapeHtml(orderNumberForEvent(event))}</td>
      <td>${escapeHtml(event.protocol || "")}</td>
      <td>${statusBadge(event.status)}</td>
      <td>${escapeHtml(event.confirmation_status || "-")}</td>
      <td title="${escapeHtml(event.local_path || "")}">${escapeHtml(shortPath(event.local_path || ""))}</td>
      <td title="${escapeHtml(event.error_message || "")}">${escapeHtml((event.error_message || "").substring(0, 30))}</td>
      <td style="text-align: center;"><button class="link-button" type="button" data-event-id="${event.id}">Ver</button></td>
    `;
    row.querySelector("button").addEventListener("click", () => showEventDetail(event.id));
    body.appendChild(row);
  }
}

function eventRowClass(event) {
  if (event.confirmation_status === "pending") {
    return "pending";
  }
  return event.status || "unknown";
}

function supplierForEvent(event) {
  return event.edi_fornecedor_nome || event.xml_seller_name || "";
}

function orderNumberForEvent(event) {
  return event.edi_numero_encomenda || event.xml_order_number || event.xml_buyer_order_number || "";
}

async function showEventDetail(eventId) {
  const panel = document.getElementById("event-detail");
  const body = document.getElementById("event-detail-body");

  panel.hidden = false;
  body.textContent = "A carregar detalhe...";

  try {
    const detail = await getJson(`/events/${eventId}`);
    body.innerHTML = detailRows([
      ["Ligação", detail.connection_name],
      ["Estado", detail.status],
      ["Confirmação", detail.confirmation_status],
      ["Fornecedor EDI", detail.edi_fornecedor_nome],
      ["Número encomenda EDI", detail.edi_numero_encomenda],
      ["Fornecedor XML", detail.xml_seller_name],
      ["Número encomenda XML", detail.xml_order_number],
      ["Ficheiro local", detail.local_path],
      ["Ficheiro remoto", detail.remote_path],
      ["Erro", detail.error_message],
    ]);
  } catch (error) {
    body.textContent = `Erro ao carregar detalhe: ${error.message}`;
  }
}

function hideEventDetail() {
  document.getElementById("event-detail").hidden = true;
}

function detailRows(rows) {
  return rows
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([label, value]) => `<div class="detail-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
}

function renderClients() {
  const container = document.getElementById("clients-list");
  container.innerHTML = "";

  if (state.clients.length === 0) {
    container.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-tertiary);">Sem clientes para apresentar.</div>`;
    return;
  }

  for (const client of state.clients) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(client.client_name || "DESCONHECIDO")}</strong>
        <small>Total: ${client.total_files ?? 0}</small>
      </div>
      <small>Duplicados: ${client.duplicate_count ?? 0} | Falhados: ${client.failed_count ?? 0}</small>
    `;
    container.appendChild(row);
  }
}

function renderSuppliers() {
  const container = document.getElementById("suppliers-list");
  container.innerHTML = "";

  if (state.suppliers.length === 0) {
    container.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-tertiary);">Sem fornecedores para apresentar.</div>`;
    return;
  }

  for (const supplier of state.suppliers) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(supplier.supplier_name || "DESCONHECIDO")}</strong>
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
    container.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-tertiary);">Sem relatórios para apresentar.</div>`;
    return;
  }

  for (const report of state.reports.slice(0, 12)) {
    const href = `/reports/${encodeURIComponent(report.name || "")}`;
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(report.name || "")}</strong>
        <small>${escapeHtml(report.kind || "other")} • ${formatBytes(report.size_bytes)}</small>
      </div>
      <small><a href="${href}" target="_blank" rel="noopener">Abrir</a></small>
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
  if (element) {
    element.hidden = false;
    element.textContent = `Erro ao carregar dados: ${error.message}`;
  }
}

function hideError(id) {
  const element = document.getElementById(id);
  if (element) {
    element.hidden = true;
    element.textContent = "";
  }
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("pt-PT");
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
