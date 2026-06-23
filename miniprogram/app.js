const { ensureLogin } = require("./utils/auth");

App({
  globalData: {
    // 生产: https://api.hanjianglab.com
    apiBase: "https://api.hanjianglab.com",
  },
  async onLaunch() {
    try {
      await ensureLogin();
    } catch (e) {
      console.warn("login deferred", e);
    }
  },
});
