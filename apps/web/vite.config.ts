import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  base: process.env.VITE_BASE_PATH ?? (mode === "production" ? "/soricall/" : "/"),
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    allowedHosts: true,
    proxy: {
      "/soricall-api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/soricall-api/, ""),
      },
      "/api": process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
      "/health": process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
    },
  },
}));
