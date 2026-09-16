const state = {
  summary: null,
  events: [],
  suppliers: [],
  reports: [],
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("refresh-button").addEventListener("click", refreshAll);
  document.getElementById("event-filters").addEventListener("input", fetchEvents);
  document.getElementById("clear-filters-button").addEventListener("click", clearEventFilters);
  document.getElementById("event-detail-close").addEventListener("click", hideEventDetail);
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
    renderOperationalAlerts(summary);
  } catch (error) {
    document.getElementById("last-updated").textContent = `Erro no resumo: ${error.message}`;
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
    item.innerHTML = `<strong>${alert.count}</strong><span>${alert.label} requerem atencao.</span>`;
    container.appendChild(item);
  }
}

function renderEvents() {
  const body = document.getElementById("events-body");
  body.innerHTML = "";
  if (state.events.length === 0) {
    body.innerHTML = '<tr><td colspan="10">Sem eventos para apresentar.</td></tr>';
    return;
  }
  for (const event of state.events) {
    const row = document.createElement("tr");
    row.className = eventRowClass(event);
    row.innerHTML = `
      <td>${formatDate(event.detected_at)}</td>
      <td>${escapeHtml(event.connection_name || "")}</td>
      <td>${escapeHtml(supplierForEvent(event))}</td>
      <td>${escapeHtml(orderNumberForEvent(event))}</td>
      <td>${escapeHtml(event.protocol || "")}</td>
      <td>${statusBadge(event.status)}</td>
      <td>${escapeHtml(event.confirmation_status || "")}</td>
      <td>${escapeHtml(shortPath(event.local_path || ""))}</td>
      <td>${escapeHtml(event.error_message || "")}</td>
      <td><button class="link-button" type="button" data-event-id="${event.id}">Detalhe</button></td>
    `;
    row.querySelector("button").addEventListener("click", () => showEventDetail(event.id));
    body.appendChild(row);
  }
}

function eventRowClass(event) {
  if (event.confirmation_status === "pending") {
    return "event-row pending";
  }
  return `event-row ${event.status || "unknown"}`;
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
      ["Ligacao", detail.connection_name],
      ["Estado", detail.status],
      ["Confirmacao", detail.confirmation_status],
      ["Fornecedor EDI", detail.edi_fornecedor_nome],
      ["Numero encomenda EDI", detail.edi_numero_encomenda],
      ["Fornecedor XML", detail.xml_seller_name],
      ["Numero encomenda XML", detail.xml_order_number],
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
    const href = `/reports/${encodeURIComponent(report.name || "")}`;
    const row = document.createElement("div");
    row.className = "list-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(report.name || "")}</strong>
        <small>${escapeHtml(report.kind || "other")} | ${formatBytes(report.size_bytes)}</small>
      </div>
      <small>${formatTimestamp(report.modified_at)} | <a href="${href}" target="_blank" rel="noopener">Abrir</a></small>
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
