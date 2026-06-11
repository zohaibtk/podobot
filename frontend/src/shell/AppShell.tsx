import { useState, type PropsWithChildren } from "react";

import { MainNavigation } from "@/shell/MainNavigation";
import { TopBar } from "@/shell/TopBar";

export function AppShell({ children }: PropsWithChildren) {
  const [isSidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="streamly-theme min-h-screen overflow-hidden bg-streamly-paper text-streamly-coal">
      <a
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-streamly-pill focus:bg-streamly-electric focus:px-4 focus:py-2 focus:text-sm focus:font-bold focus:text-white"
        href="#main-content"
      >
        Skip to main content
      </a>
      <div
        className={[
          "grid min-h-screen grid-cols-1 transition-[grid-template-columns] duration-300 ease-out",
          isSidebarCollapsed
            ? "lg:grid-cols-[5.75rem_minmax(0,1fr)]"
            : "lg:grid-cols-[17rem_minmax(0,1fr)]"
        ].join(" ")}
      >
        <div className="min-w-0">
          <MainNavigation
            isCollapsed={isSidebarCollapsed}
            onToggleCollapsed={() => setSidebarCollapsed((value) => !value)}
          />
        </div>
        <div className="flex min-w-0 flex-col">
          <TopBar />
          <main
            className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6 lg:px-10 lg:py-8"
            id="main-content"
          >
            <div className="mx-auto w-full max-w-[92rem]">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
