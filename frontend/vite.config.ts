import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { output: { manualChunks(id) { if (id.replace(/\\/g,'/').endsWith('/src/public-data/financial-renewals.json')) return 'financial-renewals'; if (id.replace(/\\/g,'/').endsWith('/src/public-data/product-expanded.json')) return 'product-data'; if (id.replace(/\\/g,'/').endsWith('/src/public-data/current-support-web.json')) return 'support-data'; } } } },
  server: { proxy: { '/api': 'http://127.0.0.1:8100' } },
  // Whole-page tests render hundreds of cards with jsdom and run side by side, so on a busy
  // machine they can pass 5 s; a generous limit keeps the result about correctness, not speed.
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'], include: ['src/**/*.test.tsx', 'src/**/*.test.ts'], testTimeout: 30000, hookTimeout: 30000 },
});
