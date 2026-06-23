const app = getApp();

function getBase() {
  return app.globalData.apiBase.replace(/\/$/, "");
}

function request(path, options = {}) {
  const token = wx.getStorageSync("token");
  const header = Object.assign(
    { "Content-Type": "application/json" },
    options.header || {},
  );
  if (token) header.Authorization = `Bearer ${token}`;
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getBase()}${path}`,
      method: options.method || "GET",
      data: options.data,
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        const detail = (res.data && (res.data.detail || res.data.error)) || "请求失败";
        reject(new Error(typeof detail === "string" ? detail : "请求失败"));
      },
      fail(err) {
        reject(new Error(err.errMsg || "网络错误"));
      },
    });
  });
}

function uploadInspect(filePath) {
  const token = wx.getStorageSync("token");
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${getBase()}/api/v1/inspect`,
      filePath,
      name: "file",
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success(res) {
        let data = {};
        try {
          data = JSON.parse(res.data || "{}");
        } catch (_) {}
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data);
          return;
        }
        reject(new Error(data.detail || "上传失败"));
      },
      fail(err) {
        reject(new Error(err.errMsg || "上传失败"));
      },
    });
  });
}

module.exports = { request, uploadInspect };
