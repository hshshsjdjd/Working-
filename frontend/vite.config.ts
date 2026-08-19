import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const backend = process.env.BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "NVIDIA AI",
        short_name: "NVIDIA AI",
        description: "A premium web chat interface powered by NVIDIA AI models.",
        theme_color: "#000000",
        background_color: "#000000",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icons/icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Never cache API responses; AI requests always require the network.
        navigateFallbackDenylist: [/^\/api/, /^\/health/, /^\/ready/],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/api"),
            handler: "NetworkOnly",
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": { target: backend, changeOrigin: true },
      "/health": { target: backend, changeOrigin: true },
      "/ready": { target: backend, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
