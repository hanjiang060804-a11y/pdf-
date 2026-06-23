const state = {
  path: null,
  filename: null,
  inspect: null,
  jobId: null,
  pollTimer: null,
  translateEngine: "babeldoc",
  layoutPolish: true,
};

const $ = (sel) => document.querySelector(sel);

function toast(msg, type = "") {
  const stack = $("#toast-stack");
  const el = document.createElement("div");
  el.className = "toast" + (type ? ` toast--${type}` : "");
  el.textContent = msg;
  stack.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = data.error || "请求失败";
    if (typeof data.detail === "string") msg = data.detail;
    else if (Array.isArray(data.detail) && data.detail[0]?.msg) msg = data.detail[0].msg;
    throw new Error(msg);
  }
  return data;
}

function isPdfFile(file) {
  if (!file) return false;
  const name = (file.name || "").toLowerCase();
  return name.endsWith(".pdf") || file.type === "application/pdf";
}

async function loadSettings() {
  const s = await api("/api/v1/settings");
  state.translateEngine = s.translate_engine || "babeldoc";
  state.layoutPolish = s.layout_polish !== false;
  const engineEl = $("#translate-engine");
  const polishEl = $("#layout-polish");
  if (engineEl) engineEl.value = state.translateEngine;
  if (polishEl) polishEl.checked = state.layoutPolish;
  $("#settings-hint").textContent = s.has_api_key
    ? `已配置 ${s.api_key_masked} · 模型 ${s.model} · 引擎 ${state.translateEngine === "babeldoc" ? "BabelDOC" : "经典"}`
    : "尚未配置 API Key";
  $("#api-banner").classList.toggle("hidden", s.has_api_key);
}

function setInspectLoading(filename) {
  $("#file-chip").classList.remove("hidden");
  $("#file-name").textContent = filename || "正在读取…";
  $("#file-meta").textContent = "正在分析文档…";
  $("#inspect-block").classList.remove("hidden");
  $("#skeleton-grid").classList.remove("hidden");
  $("#stat-grid").classList.add("hidden");
  const badge = $("#inspect-badge");
  badge.textContent = "分析中";
  badge.className = "badge badge--loading";
  $("#inspect-hint").textContent = "";
  $("#btn-translate").disabled = true;
  $("#result-block").classList.add("hidden");
  $("#progress-block").classList.add("hidden");
}

function showInspect(data) {
  state.path = data.path;
  state.filename = data.filename;
  state.inspect = data;

  $("#file-chip").classList.remove("hidden");
  $("#file-name").textContent = data.filename;
  $("#inspect-block").classList.remove("hidden");
  $("#skeleton-grid").classList.add("hidden");
  $("#stat-grid").classList.remove("hidden");

  const ok = data.can_translate;
  const isScan = data.pdf_type === "scanned";
  const badge = $("#inspect-badge");
  if (ok) {
    badge.textContent = isScan ? "扫描版 · 可 OCR" : "可以翻译";
    badge.className = "badge " + (isScan ? "badge--scan" : "badge--ok");
  } else {
    badge.textContent = isScan ? "扫描版" : "无法翻译";
    badge.className = "badge badge--bad";
  }

  const typeLabel = data.pdf_type === "text" ? "文字版" : "扫描版";
  $("#file-meta").textContent = `${data.pages} 页 · ${typeLabel}`;
  $("#stat-pages").textContent = `${data.pages} 页`;
  $("#stat-type").textContent = typeLabel + (data.encrypted ? " · 已加密" : "");
  $("#stat-lang").textContent = data.needs_ocr ? "OCR 后自动识别" : data.detected_lang_label;

  if (data.needs_ocr) {
    $("#inspect-hint").textContent = data.suggestion || "";
  } else {
    let hint = `${data.detected_lang_label} → ${data.target_lang_label}`;
    if (data.lang_detect_fallback) hint += " · 语言识别为估算值";
    $("#inspect-hint").textContent = hint;
  }

  const btn = $("#btn-translate");
  btn.disabled = !ok;
  btn.querySelector(".btn-label").textContent =
    data.needs_ocr && ok ? "OCR 识别并翻译" : "开始翻译";
  $("#result-block").classList.add("hidden");
  $("#progress-block").classList.add("hidden");
}

function resetFile() {
  state.path = null;
  state.filename = null;
  state.inspect = null;
  state.jobId = null;
  clearInterval(state.pollTimer);
  document.body.classList.remove("is-busy");
  $("#file-input").value = "";
  $("#file-chip").classList.add("hidden");
  $("#inspect-block").classList.add("hidden");
  $("#progress-block").classList.add("hidden");
  $("#result-block").classList.add("hidden");
  $("#btn-translate").disabled = true;
  $("#btn-translate").classList.remove("is-loading");
  const btn = $("#btn-translate");
  if (btn) btn.querySelector(".btn-label").textContent = "开始翻译";
}

async function inspectUpload(file) {
  if (!isPdfFile(file)) {
    toast("请选择 PDF 文件", "error");
    return;
  }
  setInspectLoading(file.name);
  try {
    const fd = new FormData();
    fd.append("file", file);
    const data = await api("/api/v1/inspect", { method: "POST", body: fd });
    showInspect(data);
  } catch (e) {
    resetFile();
    toast(e.message, "error");
  }
}

async function startTranslate() {
  if (!state.path) return;
  const btn = $("#btn-translate");
  btn.disabled = true;
  btn.classList.add("is-loading");
  document.body.classList.add("is-busy");
  $("#progress-block").classList.remove("hidden");
  $("#result-block").classList.add("hidden");
  $("#progress-fill").style.width = "6%";
  $("#progress-percent").textContent = "6%";
  $("#progress-msg").textContent = "正在提交任务…";

  try {
    const useOcr = !!(state.inspect && state.inspect.needs_ocr);
    const { job_id } = await api("/api/v1/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: state.path,
        ocr: useOcr,
        engine: state.translateEngine,
        polish: state.layoutPolish,
      }),
    });
    state.jobId = job_id;
    pollJob();
  } catch (e) {
    document.body.classList.remove("is-busy");
    btn.classList.remove("is-loading");
    btn.disabled = false;
    $("#progress-block").classList.add("hidden");
    toast(e.message, "error");
  }
}

function formatProgressMsg(job) {
  const { message, page_current: cur, page_total: total, phase } = job;
  if (cur != null && total != null && total > 0) {
    if (/\d+\s*\/\s*\d+/.test(message || "")) return message;
    const verb =
      phase === "ocr"
        ? "正在识别文字"
        : phase === "translate"
          ? "正在翻译"
          : phase === "polish"
            ? "正在优化排版"
            : "处理中";
    return `${verb} ${cur}/${total} 页`;
  }
  return message || "处理中…";
}

function pollJob() {
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    try {
      const job = await api(`/api/v1/jobs/${state.jobId}`);
      const pct = job.progress || 0;
      $("#progress-fill").style.width = `${pct}%`;
      $("#progress-percent").textContent = `${pct}%`;
      $("#progress-msg").textContent = formatProgressMsg(job);
      const label = $("#progress-label");
      if (job.phase === "ocr") label.textContent = "识别文字";
      else if (job.phase === "translate") label.textContent = "翻译中";
      else if (job.phase === "polish") label.textContent = "排版优化";
      else label.textContent = "译文中";

      if (job.status === "done") {
        clearInterval(state.pollTimer);
        document.body.classList.remove("is-busy");
        const btn = $("#btn-translate");
        btn.classList.remove("is-loading");
        btn.querySelector(".btn-label").textContent =
          state.inspect && state.inspect.needs_ocr ? "OCR 识别并翻译" : "开始翻译";
        btn.disabled = false;
        $("#result-block").classList.remove("hidden");
        const monoBtn = $("#btn-dl-mono");
        const dualBtn = $("#btn-dl-dual");
        if (monoBtn) monoBtn.classList.toggle("hidden", !job.has_mono);
        if (dualBtn) dualBtn.classList.toggle("hidden", !job.has_dual);
        toast("翻译完成");
      }
      if (job.status === "error") {
        clearInterval(state.pollTimer);
        document.body.classList.remove("is-busy");
        const btn = $("#btn-translate");
        btn.classList.remove("is-loading");
        btn.disabled = false;
        $("#progress-block").classList.add("hidden");
        toast(job.error || "翻译失败", "error");
      }
    } catch (e) {
      clearInterval(state.pollTimer);
      document.body.classList.remove("is-busy");
      toast(e.message, "error");
    }
  }, 500);
}

function setupUpload() {
  const zone = $("#drop-zone");
  const input = $("#file-input");
  zone.addEventListener("click", (e) => {
    if (e.target.closest("#file-clear")) return;
    input.click();
  });
  input.addEventListener("change", () => {
    if (input.files[0]) inspectUpload(input.files[0]);
  });
  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("is-dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("is-dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("is-dragover");
    const file = e.dataTransfer.files[0];
    if (!file) return;
    if (!isPdfFile(file)) {
      toast("仅支持 PDF 文件", "error");
      return;
    }
    inspectUpload(file);
  });
  $("#file-clear").addEventListener("click", (e) => {
    e.stopPropagation();
    resetFile();
  });
}

function setupSettings() {
  const dlg = $("#settings-dialog");
  const open = () => dlg.showModal();
  $("#btn-settings").addEventListener("click", open);
  $("#banner-settings")?.addEventListener("click", open);
  $("#settings-close").addEventListener("click", () => dlg.close());
  $("#settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const key = $("#api-key-input").value.trim();
    const payload = {
      translate_engine: $("#translate-engine").value,
      layout_polish: $("#layout-polish").checked,
    };
    if (key) payload.api_key = key;
    try {
      await api("/api/v1/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      dlg.close();
      await loadSettings();
      toast("设置已保存");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

function setupDownloads() {
  $("#btn-dl-mono").addEventListener("click", () => {
    if (state.jobId) window.open(`/api/v1/jobs/${state.jobId}/download/mono`, "_blank");
  });
  $("#btn-dl-dual").addEventListener("click", () => {
    if (state.jobId) window.open(`/api/v1/jobs/${state.jobId}/download/dual`, "_blank");
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  setupUpload();
  setupSettings();
  setupDownloads();
  $("#btn-translate").addEventListener("click", startTranslate);
  try {
    await loadSettings();
  } catch (_) {
    /* 离线预览 */
  }
});
