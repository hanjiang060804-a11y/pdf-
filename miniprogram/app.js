const { ensureLogin } = require("./utils/auth");

App({
  globalData: {
    apiBase: "http://127.0.0.1:8787",
  },
  async onLaunch() {
    try {
      await ensureLogin();
    } catch (e) {
      console.warn("login deferred", e);
    }
  },
});
