import { defineConfig } from "@playwright/test";
export default defineConfig({
 testDir:"./tests/browser",
 timeout:30000,
 fullyParallel:false,
 workers:1,
 use:{baseURL:"http://127.0.0.1:8766", headless:true, viewport:{width:1440,height:1000}, screenshot:"only-on-failure"},
 webServer:{command:".venv/bin/python -m uvicorn tests.browser_server:app --host 127.0.0.1 --port 8766",url:"http://127.0.0.1:8766/api/health",reuseExistingServer:false,timeout:15000},
 reporter:[["list"]],
});
