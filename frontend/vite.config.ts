import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";
import { AppEntries } from "./src/entry";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 8000,
    host: true,
    proxy: {
      "/~demo": "http://localhost:9001",
      "/p": "http://localhost:9001",
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    emptyOutDir: false,
    minify: process.env.NODE_ENV === "production",
    sourcemap: process.env.NODE_ENV !== "production",
    rollupOptions: {
      input: AppEntries,
      output: {
        entryFileNames: "[name].js",
        manualChunks(id: string) {
          // splitting based on https://dev.to/tassiofront/splitting-vendor-chunk-with-vite-and-loading-them-async-15o3
          if (id.includes("react") || id.includes("@radix-ui")) {
            return "@react";
          }
          if (id.includes("flowbite")) {
            return "@flowbite";
          }
        },
      },
    },
  },
});
