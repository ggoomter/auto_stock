import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  root: path.resolve(__dirname),
  resolve: {
    alias: {
      "~": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 4783,
    host: "localhost",
    open: false,
    proxy: {
      "/api": {
        target: "http://localhost:8650",
        changeOrigin: true,
      },
    },
  },
});
