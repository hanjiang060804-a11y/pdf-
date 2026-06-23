const { request } = require("./api");

async function ensureLogin() {
  const cached = wx.getStorageSync("token");
  if (cached) return cached;
  const { code } = await wx.login();
  const data = await request("/api/v2/auth/wechat", {
    method: "POST",
    data: { code },
  });
  wx.setStorageSync("token", data.token);
  return data.token;
}

module.exports = { ensureLogin };
