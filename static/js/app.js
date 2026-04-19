const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("ifcFileInput");
const dropZone = document.getElementById("dropZone");
const fileStatus = document.getElementById("fileStatus");
const resultsBody = document.getElementById("resultsBody");
const resultCount = document.getElementById("resultCount");
const exportPdfButton = document.getElementById("exportPdfButton");
const criticalCount = document.getElementById("criticalCount");
const warningCount = document.getElementById("warningCount");
const infoCount = document.getElementById("infoCount");
const ignoredCount = document.getElementById("ignoredCount");
const ignoredResultsBody = document.getElementById("ignoredResultsBody");
const ignoredResultCount = document.getElementById("ignoredResultCount");

let activeRunId = null;

function setStatus(message) {
  fileStatus.textContent = message;
}

function setLoading(isLoading) {
  const submitButton = uploadForm.querySelector("button[type='submit']");
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Analyzing Model..." : "Run Clash Detection";
}

function updateSummary(summary) {
  criticalCount.textContent = summary.Critical || 0;
  warningCount.textContent = summary.Warning || 0;
  infoCount.textContent = summary.Info || 0;
}

function severityClass(severity) {
  return severity.toLowerCase();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderResults(clashes) {
  resultCount.textContent = `${clashes.length} ${clashes.length === 1 ? "clash" : "clashes"}`;
  resultsBody.innerHTML = "";

  if (clashes.length === 0) {
    resultsBody.innerHTML = '<tr class="empty-row"><td colspan="6">No clashes were detected in this IFC model.</td></tr>';
    return;
  }

  clashes.forEach((clash) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><strong>${escapeHtml(clash.id)}</strong></td>
      <td><span class="severity-pill ${severityClass(clash.severity)}">${escapeHtml(clash.severity)}</span></td>
      <td>${escapeHtml(clash.description)}</td>
      <td>${escapeHtml(clash.location)}</td>
      <td>${escapeHtml(clash.elementA)}</td>
      <td>${escapeHtml(clash.elementB)}</td>
    `;
    resultsBody.appendChild(row);
  });
}

function renderIgnoredResults(ignoredClashes) {
  ignoredCount.textContent = ignoredClashes.length;
  ignoredResultCount.textContent = `${ignoredClashes.length} ${ignoredClashes.length === 1 ? "ignored clash" : "ignored clashes"}`;
  ignoredResultsBody.innerHTML = "";

  if (ignoredClashes.length === 0) {
    ignoredResultsBody.innerHTML = '<tr class="empty-row"><td colspan="6">No clashes were ignored by smart rules for this IFC model.</td></tr>';
    return;
  }

  ignoredClashes.forEach((clash) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><strong>${escapeHtml(clash.id)}</strong></td>
      <td><span class="ignore-pill">${escapeHtml(clash.reason)}</span></td>
      <td>${escapeHtml(clash.description)}</td>
      <td>${escapeHtml(clash.location)}</td>
      <td>${escapeHtml(clash.elementA)}</td>
      <td>${escapeHtml(clash.elementB)}</td>
    `;
    ignoredResultsBody.appendChild(row);
  });
}

function handleSelectedFile(file) {
  if (!file) {
    setStatus("No IFC file selected.");
    return;
  }

  if (!file.name.toLowerCase().endsWith(".ifc")) {
    setStatus("Please select a valid .ifc file.");
    fileInput.value = "";
    return;
  }

  setStatus(`Ready to analyze: ${file.name}`);
}

fileInput.addEventListener("change", () => {
  handleSelectedFile(fileInput.files[0]);
});

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag-over");
  });
});

dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) {
    return;
  }

  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  handleSelectedFile(file);
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = fileInput.files[0];
  if (!file) {
    setStatus("Choose an IFC file before running clash detection.");
    return;
  }

  const formData = new FormData();
  formData.append("ifcFile", file);

  setLoading(true);
  setStatus("Uploading and analyzing IFC model...");

  try {
    const response = await fetch("/api/clashes/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to analyze IFC file.");
    }

    activeRunId = data.runId;
    updateSummary(data.summary);
    renderResults(data.clashes);
    renderIgnoredResults(data.ignoredClashes || []);
    exportPdfButton.disabled = false;
    setStatus(`Analysis complete for ${data.filename}.`);
  } catch (error) {
    setStatus(error.message);
    exportPdfButton.disabled = true;
  } finally {
    setLoading(false);
  }
});

exportPdfButton.addEventListener("click", async () => {
  if (!activeRunId) {
    return;
  }

  exportPdfButton.disabled = true;
  exportPdfButton.textContent = "Preparing PDF...";

  try {
    const response = await fetch(`/api/clashes/${activeRunId}/export-pdf`, {
      method: "POST",
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "Unable to export PDF.");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "bim-clash-report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    setStatus(error.message);
  } finally {
    exportPdfButton.disabled = false;
    exportPdfButton.textContent = "Export PDF";
  }
});
