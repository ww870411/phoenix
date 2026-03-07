import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  server: {
    host: '0.0.0.0', // 允许外部通过宿主机访问
    port: 5173,
    proxy: {
      '/api': {
        // 在 Docker 容器中运行时，应该指向后端服务的容器名 'backend'
        // 而不是 127.0.0.1。8000 是后端容器内部端口。
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
