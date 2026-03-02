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
    strictPort: true,  // 포트가 사용 중이면 에러 발생 (자동 변경 방지)
    proxy: {
      "/api": {
        target: "http://localhost:8650",
        changeOrigin: true,
      },
    },
  },
});
