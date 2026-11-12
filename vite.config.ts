import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  root: 'web',
  plugins: [react()],
  build: {
    outDir: 'dist',
    // three is most of the simulator, which twinky serves locally, so one big chunk is fine
    chunkSizeWarningLimit: 1000,
    // the simulator at /, the remote at /remote
    rollupOptions: { input: { main: 'web/index.html', remote: 'web/remote/index.html' } },
  },
  server: {
    proxy: { '/ws': { target: 'ws://localhost:8016', ws: true } },
  },
})
