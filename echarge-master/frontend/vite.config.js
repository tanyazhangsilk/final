import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import viteCompression from 'vite-plugin-compression'

// https://vite.dev/config/
// 开发代理目标：与 `启动.md` 中 uvicorn 端口一致。本机若装有 C-Lodop，8000 常被其占用，请用 8001 或设 VITE_DEV_PROXY_TARGET。
const devApiProxyTarget = process.env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [
    vue(),
    viteCompression({ algorithm: 'gzip' }),
    viteCompression({ algorithm: 'brotliCompress', ext: '.br' }),
  ],
  server: {
    proxy: {
      // 将 /api 前缀的请求代理到 FastAPI 后端，避免浏览器 CORS
      '/api': {
        target: devApiProxyTarget,
        changeOrigin: true,
        // 与 axios 超时对齐，避免代理先于浏览器断开（reload / 慢查询）
        proxyTimeout: 600000,
      },
    },
  },
})
