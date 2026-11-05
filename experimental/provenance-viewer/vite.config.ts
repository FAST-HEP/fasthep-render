import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Data (runs.json and per-run folders) is served from VIEWER_DATA_DIR, default the
// checked-in fixtures. Point it at gitignored local output for the large case.
export default defineConfig({
  plugins: [react()],
  base: "./",
  publicDir: process.env.VIEWER_DATA_DIR ?? "fixtures",
  test: { environment: "node" },
});
