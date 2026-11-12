import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  root: 'web',
  plugins: [react()],
  // three is most of the page, which twinky serves locally, so one big chunk is fine
  build: { outDir: 'dist', chunkSizeWarningLimit: 1000 },
  server: {
    proxy: { '/ws': { target: 'ws://localhost:8016', ws: true } },
  },
})
