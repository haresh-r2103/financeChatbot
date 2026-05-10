import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/auth": "http://localhost:8000",
      "/upload": "http://localhost:8000",
      "/uploads": "http://localhost:8000",
      "/analyze": "http://localhost:8000",
      "/summary": "http://localhost:8000",
      "/forecast": "http://localhost:8000",
      "/ask": "http://localhost:8000",
      "/columns": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
