import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 개발 시 API 요청을 백엔드(8001)로 프록시한다.
// 프로덕션(단일 exe)에선 백엔드가 프론트와 같은 출처에서 API를 서빙하므로 프록시가 불필요하다.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/members': 'http://localhost:8001',
      '/projects': 'http://localhost:8001',
      '/participations': 'http://localhost:8001',
    },
  },
})
