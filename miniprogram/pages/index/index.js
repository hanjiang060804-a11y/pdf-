const { uploadInspect, request } = require("../../utils/api");
const { ensureLogin } = require("../../utils/auth");

Page({
  data: {
    filename: "",
    meta: "",
    hint: "",
    canTranslate: false,
    loading: false,
    translateLabel: "开始翻译",
    fileId: "",
    needsOcr: false,
  },

  async onShow() {
    try {
      await ensureLogin();
    } catch (e) {
      wx.showToast({ title: e.message || "登录失败", icon: "none" });
    }
  },

  pickFromChat() {
    this._pickFile();
  },

  pickLocal() {
    this._pickFile();
  },

  _pickFile() {
    wx.chooseMessageFile({
      count: 1,
      type: "file",
      extension: ["pdf"],
      success: (res) => this._inspect(res.tempFiles[0]),
      fail: () => wx.showToast({ title: "未选择文件", icon: "none" }),
    });
  },

  async _inspect(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      wx.showToast({ title: "请选择 PDF", icon: "none" });
      return;
    }
    this.setData({ loading: true, filename: file.name, meta: "正在分析…" });
    try {
      await ensureLogin();
      const data = await uploadInspect(file.path);
      const typeLabel = data.pdf_type === "text" ? "文字版" : "扫描版";
      const can =
        data.can_translate &&
        !(data.needs_ocr && !data.ocr_available);
      let label = "开始翻译";
      if (data.needs_ocr && data.ocr_available) label = "OCR 识别并翻译";
      if (data.needs_ocr && !data.ocr_available) {
        label = "扫描版暂不支持";
      }
      this.setData({
        fileId: data.file_id,
        canTranslate: can,
        needsOcr: !!data.needs_ocr,
        meta: `${data.pages} 页 · ${typeLabel}`,
        hint: data.needs_ocr
          ? data.suggestion || ""
          : `${data.detected_lang_label} → ${data.target_lang_label}`,
        translateLabel: label,
      });
    } catch (e) {
      this.setData({ filename: "", meta: "", canTranslate: false });
      wx.showToast({ title: e.message || "分析失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  async startTranslate() {
    if (!this.data.fileId) return;
    this.setData({ loading: true });
    try {
      await ensureLogin();
      const { job_id } = await request("/api/v1/translate", {
        method: "POST",
        data: {
          file_id: this.data.fileId,
          ocr: this.data.needsOcr,
        },
      });
      wx.navigateTo({
        url: `/pages/progress/progress?jobId=${job_id}&filename=${encodeURIComponent(this.data.filename)}`,
      });
    } catch (e) {
      wx.showToast({ title: e.message || "提交失败", icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },
});
