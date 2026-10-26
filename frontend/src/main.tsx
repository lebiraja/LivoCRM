import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MotionConfig } from "framer-motion";
import { Toaster } from "@/components/ui/sonner";
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import "@fontsource-variable/noto-sans-tamil";
import "./index.css";
import "@/stores/themeStore";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      <App />
    </MotionConfig>
    <Toaster richColors position="bottom-center" mobileOffset="5rem" />
  </StrictMode>
);
