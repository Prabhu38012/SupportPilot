import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The UI calls /api/*; Vite forwards it to FastAPI on :8000 (no CORS setup needed in dev).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
    },
  },
});
