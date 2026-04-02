import { Outlet } from "react-router-dom";
import { motion } from "framer-motion";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandMenu } from "@/components/shared/CommandMenu";
import { useUIStore } from "@/stores/uiStore";

export function Layout() {
  const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <motion.div
        className="flex flex-1 flex-col"
        animate={{ marginLeft: sidebarCollapsed ? 72 : 240 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
      >
        <TopBar />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </motion.div>
      <CommandMenu />
    </div>
  );
}
