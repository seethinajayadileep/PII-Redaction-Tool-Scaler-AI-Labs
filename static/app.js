const form = document.getElementById("form");
const fileInput = document.getElementById("file");
const runBtn = document.getElementById("run");
const sampleBtn = document.getElementById("sample");
const statusEl = document.getElementById("status");
const results = document.getElementById("results");
const countsEl = document.getElementById("counts");
const metricsBox = document.getElementById("metrics-box");
const metricsEl = document.getElementById("metrics");
const docxLink = document.getElementById("docx");
const reportLink = document.getElementById("report");
const dropzone = document.getElementById("dropzone");
const dropEmpty = document.getElementById("dropzone-empty");
const fileChip = document.getElementById("file-chip");
const fileNameEl = document.getElementById("file-name");
const fileMetaEl = document.getElementById("file-meta");
const clearBtn = document.getElementById("clear-file");
const summaryEl = document.getElementById("results-summary");
const startOverBtn = document.getElementById("start-over");

function blobUrl(b64, mime) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mime }));
}

function textBlobUrl(text, mime) {
  return URL.createObjectURL(new Blob([text], { type: mime }));
}

const TYPE_LABELS = {
  name: "Person names",
  email: "Emails",
  phone: "Phone numbers",
  company: "Companies",
  address: "Addresses",
  ssn: "SSNs",
  credit_card: "Credit cards",
  dob: "Dates of birth",
  ip: "IP addresses",
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setStatus(message, kind) {
  statusEl.hidden = !message;
  statusEl.textContent = message || "";
  statusEl.className = `status ${kind || ""}`.trim();
}

function showSelectedFile(file) {
  const ok = file && /\.(pdf|txt|docx)$/i.test(file.name);
  dropEmpty.hidden = Boolean(file);
  fileChip.hidden = !file;
  if (file) {
    fileNameEl.textContent = file.name;
    fileMetaEl.textContent = `${formatSize(file.size)} · ${ok ? "ready to redact" : "use a .pdf, .txt, or .docx file"}`;
  }
  runBtn.disabled = !ok;
}

function clearFile() {
  fileInput.value = "";
  showSelectedFile(null);
  runBtn.disabled = true;
}

fileInput.addEventListener("change", () => {
  showSelectedFile(fileInput.files[0] || null);
});

dropzone.addEventListener("click", (event) => {
  if (event.target.closest("#clear-file")) return;
  fileInput.click();
});

dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});

clearBtn.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  clearFile();
});

["dragenter", "dragover"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  showSelectedFile(file);
});

startOverBtn.addEventListener("click", () => {
  results.hidden = true;
  clearFile();
  setStatus("");
  window.scrollTo({ top: 0, behavior: "smooth" });
});

async function redact(request) {
  runBtn.disabled = true;
  sampleBtn.disabled = true;
  results.hidden = true;
  setStatus("Reading the file and replacing personal details… this can take a minute for large PDFs.", "busy");

  try {
    const response = await fetch(request.url, {
      method: "POST",
      body: request.body,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      const detail = Array.isArray(err.detail) ? err.detail.map((d) => d.msg || d).join("; ") : err.detail;
      throw new Error(detail || "Redaction failed");
    }
    renderResults(await response.json());
    setStatus("Done. Download the Word file to review the redacted document.", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    sampleBtn.disabled = false;
    runBtn.disabled = !fileInput.files[0];
  }
}

function renderResults(payload) {
  const counts = payload.counts || {};
  const keys = Object.keys(counts).sort();
  const total = keys.reduce((sum, key) => sum + counts[key], 0);

  countsEl.innerHTML = "";
  if (!keys.length) {
    countsEl.innerHTML = '<li class="empty-counts">No PII was detected in this file.</li>';
  } else {
    keys.forEach((key) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="n">${counts[key]}</span>${TYPE_LABELS[key] || key}`;
      countsEl.appendChild(li);
    });
  }

  summaryEl.textContent = keys.length
    ? `${total} replacement${total === 1 ? "" : "s"} across ${keys.length} type${keys.length === 1 ? "" : "s"} in ${payload.filename || "your file"}.`
    : `Nothing was replaced in ${payload.filename || "your file"}.`;

  if (payload.metrics) {
    const m = payload.metrics;
    const show = (value) => (value === null || value === undefined ? "N/A" : Number(value).toFixed(3));
    metricsBox.hidden = false;
    metricsEl.innerHTML = `
      <div><dt>Precision</dt><dd>${show(m.precision)}</dd></div>
      <div><dt>Recall</dt><dd>${show(m.recall)}</dd></div>
      <div><dt>F1</dt><dd>${show(m.f1)}</dd></div>
      <div><dt>Accuracy</dt><dd>${show(m.accuracy)}</dd></div>
      <div><dt>Scored</dt><dd>${m.scored ? "true" : "false"}</dd></div>
    `;
  } else {
    metricsBox.hidden = true;
    metricsEl.innerHTML = "";
  }

  docxLink.href = payload.docx_b64
    ? blobUrl(payload.docx_b64, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    : `/download/docx/${payload.job_id}`;
  docxLink.setAttribute("download", "redacted.docx");
  if (payload.report_md || payload.metrics) {
    reportLink.hidden = false;
    reportLink.href = payload.report_md
      ? textBlobUrl(payload.report_md, "text/markdown")
      : `/download/report/${payload.job_id}`;
    reportLink.setAttribute("download", "evaluation_report.md");
  } else {
    reportLink.hidden = true;
    reportLink.removeAttribute("href");
  }

  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    setStatus("Choose a PDF, TXT, or DOCX file first, or try the sample ticket log.", "error");
    return;
  }
  const data = new FormData();
  data.append("file", file);
  await redact({ url: "/redact", body: data });
});

sampleBtn.addEventListener("click", async () => {
  try {
    const sample = await fetch("/static/sample_ticket_log.txt");
    if (!sample.ok) throw new Error("Could not load the sample ticket log.");
    const blob = await sample.blob();
    const file = new File([blob], "ticket_log.txt", { type: "text/plain" });
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    showSelectedFile(file);
    const data = new FormData();
    data.append("file", file);
    await redact({ url: "/redact", body: data });
  } catch (error) {
    setStatus(error.message, "error");
  }
});
