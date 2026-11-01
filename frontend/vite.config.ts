import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { output: { manualChunks(id) { if (id.replace(/\\/g,'/').endsWith('/src/public-data/product-expanded.json')) return 'product-data'; if (id.replace(/\\/g,'/').endsWith('/src/public-data/current-support-web.json')) return 'support-data'; } } } },
  server: { proxy: { '/api': 'http://127.0.0.1:8100' } },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'], include: ['src/**/*.test.tsx', 'src/**/*.test.ts'] },
});
