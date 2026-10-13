import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './tests', use: { baseURL: 'http://127.0.0.1:4200', screenshot: 'only-on-failure' }, webServer: [
  { command: 'uv run uvicorn opsatlas.api:create_app --factory --host 127.0.0.1 --port 8000', cwd: '..', url: 'http://127.0.0.1:8000/health/ready', reuseExistingServer: !process.env['CI'] },
  { command: 'npm start', url: 'http://127.0.0.1:4200', reuseExistingServer: !process.env['CI'] }
] });
