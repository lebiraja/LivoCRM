import { Outlet } from "react-router-dom";
import { useT } from "@/i18n";
import { CommandMenu } from "@/components/shared/CommandMenu";
import { BottomNav } from "./BottomNav";
import { SideNav } from "./SideNav";
import { TopBar } from "./TopBar";

export function Layout() {
  const t = useT();

  return (
    <div className="min-h-dvh md:flex">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        {t("common.skipToContent")}
      </a>

      <SideNav />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main id="main" tabIndex={-1} className="flex-1 px-4 pt-5 pb-28 md:px-8 md:pt-8 md:pb-12">
          <div className="mx-auto w-full min-w-0 max-w-[1120px]">
            <Outlet />
          </div>
        </main>
      </div>

      <BottomNav />
      <CommandMenu />
    </div>
  );
}
