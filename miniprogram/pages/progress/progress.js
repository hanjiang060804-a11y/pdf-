const { request } = require("../../utils/api");

Page({
  data: {
    jobId: "",
    filename: "",
    progress: 0,
    message: "准备中…",
    phaseLabel: "译文中",
    done: false,
    tempFilePath: "",
  },

  onLoad(query) {
    this.setData({
      jobId: query.jobId || "",
      filename: decodeURIComponent(query.filename || "译文"),
    });
    this._timer = setInterval(() => this._poll(), 1000);
    this._poll();
  },

  onUnload() {
    clearInterval(this._timer);
  },

  async _poll() {
    if (!this.data.jobId) return;
    try {
      const job = await request(`/api/v1/jobs/${this.data.jobId}`);
      const label =
        job.phase === "ocr"
          ? "识别文字"
          : job.phase === "translate"
            ? "翻译中"
            : job.phase === "polish"
              ? "排版优化"
              : "译文中";
      this.setData({
        progress: job.progress || 0,
        message: job.message || "处理中…",
        phaseLabel: label,
      });
      if (job.status === "done") {
        clearInterval(this._timer);
        this.setData({ done: true, progress: 100, message: "翻译完成" });
      }
      if (job.status === "error") {
        clearInterval(this._timer);
        wx.showToast({ title: job.error || "翻译失败", icon: "none" });
      }
    } catch (e) {
      clearInterval(this._timer);
      wx.showToast({ title: e.message || "轮询失败", icon: "none" });
    }
  },

  download() {
    const token = wx.getStorageSync("token");
    const app = getApp();
    const url = `${app.globalData.apiBase.replace(/\/$/, "")}/api/v1/jobs/${this.data.jobId}/download/mono`;
    wx.downloadFile({
      url,
      header: { Authorization: `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({ tempFilePath: res.tempFilePath });
          wx.saveFile({
            tempFilePath: res.tempFilePath,
            success: () => wx.showToast({ title: "已保存" }),
          });
        } else {
          wx.showToast({ title: "下载失败", icon: "none" });
        }
      },
      fail: () => wx.showToast({ title: "下载失败", icon: "none" }),
    });
  },

  preview() {
    const open = (path) => wx.openDocument({ filePath: path, fileType: "pdf" });
    if (this.data.tempFilePath) {
      open(this.data.tempFilePath);
      return;
    }
    const token = wx.getStorageSync("token");
    const app = getApp();
    const url = `${app.globalData.apiBase.replace(/\/$/, "")}/api/v1/jobs/${this.data.jobId}/download/mono`;
    wx.downloadFile({
      url,
      header: { Authorization: `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({ tempFilePath: res.tempFilePath });
          open(res.tempFilePath);
        }
      },
    });
  },
});
