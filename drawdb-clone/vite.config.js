import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // '/fr/' when deployed to GitHub Pages (project site), '/' everywhere else.
  base: process.env.VITE_BASE || '/',
});
