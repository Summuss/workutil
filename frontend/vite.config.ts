import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/**
 * Development runs on the headless Linux box and is reached from macOS over an
 * SSH tunnel, so both this server and the backend stay on loopback
 * (docs/design.md §7). In production there is no Vite: FastAPI serves the
 * build output from `dist/`.
 */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
});
