import { NavLink } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { PodoBotBrand } from "@/design-system/components/PodoBotBrand";
import { primaryRoutes } from "@/routes/routeRegistry";

type MainNavigationProps = {
  isCollapsed: boolean;
  onToggleCollapsed: () => void;
};

export function MainNavigation({ isCollapsed, onToggleCollapsed }: MainNavigationProps) {
  const ToggleIcon = isCollapsed ? PanelLeftOpen : PanelLeftClose;

  return (
    <aside
      className={[
        "relative flex flex-col border-b border-streamly-lavenderStrong/70 bg-white/76 px-3 py-4 shadow-[10px_0_40px_rgba(63,11,147,0.06)] backdrop-blur transition-all duration-300 lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:h-screen lg:max-h-screen lg:overflow-visible lg:border-b-0 lg:border-r lg:py-6",
        isCollapsed ? "lg:w-[5.75rem] lg:items-center lg:px-3" : "lg:w-[17rem] lg:px-4"
      ].join(" ")}
    >
      <button
        aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        aria-describedby="sidebar-collapse-tooltip"
        className="group absolute -right-4 top-[6.75rem] z-20 hidden h-8 w-8 place-items-center rounded-streamly-pill border border-streamly-lavenderStrong bg-white text-streamly-electric shadow-streamly-card transition hover:-translate-y-0.5 hover:bg-streamly-lavender focus:outline-none focus:ring-2 focus:ring-streamly-electric lg:grid"
        onClick={onToggleCollapsed}
        title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        type="button"
      >
        <ToggleIcon aria-hidden className="h-4 w-4" />
        <span className="sr-only">{isCollapsed ? "Expand sidebar" : "Collapse sidebar"}</span>
        <span
          className="pointer-events-none absolute left-full ml-2 whitespace-nowrap rounded-streamly-pill bg-streamly-coal px-3 py-1.5 text-xs font-extrabold text-white opacity-0 shadow-streamly-card transition group-hover:opacity-100 group-focus-visible:opacity-100"
          id="sidebar-collapse-tooltip"
          role="tooltip"
        >
          {isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        </span>
      </button>

      <div className="min-h-0 w-full lg:flex lg:flex-1 lg:flex-col lg:overflow-visible">
        <div>
          <div
            className={[
              "mb-5 px-2 py-2 transition-all lg:mb-7",
              isCollapsed ? "lg:flex lg:justify-center lg:px-0" : ""
            ].join(" ")}
          >
            <PodoBotBrand
              className={isCollapsed ? "w-11" : "w-full max-w-[13.75rem]"}
              hideTextClassName={isCollapsed ? "lg:sr-only" : ""}
              markClassName="h-12 w-12 shrink-0"
            />
          </div>

          <nav
            aria-label="Primary navigation"
            className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] lg:flex-col lg:overflow-visible lg:pb-0 [&::-webkit-scrollbar]:hidden"
          >
            {primaryRoutes.map((route) => {
              const Icon = route.icon;
              return (
                <NavLink
                  key={route.path}
                  to={route.path}
                  title={route.label}
                  className={({ isActive }) =>
                    [
                      "group flex shrink-0 items-center gap-3 rounded-streamly-pill px-3 py-3 text-sm font-extrabold transition lg:w-full",
                      isCollapsed ? "lg:justify-center lg:px-2" : "",
                      isActive
                        ? "bg-streamly-electric text-white shadow-streamly-button"
                        : "text-streamly-purpleBlue hover:-translate-y-0.5 hover:bg-streamly-wash hover:text-streamly-violet"
                    ].join(" ")
                  }
                >
                  {({ isActive }) => (
                    <>
                      <span
                        className={[
                          "grid h-8 w-8 place-items-center rounded-streamly-pill shadow-sm",
                          isActive
                            ? "bg-white text-streamly-electric"
                            : "bg-white/70 text-streamly-electric"
                        ].join(" ")}
                      >
                        <Icon aria-hidden className="h-4 w-4" />
                      </span>
                      <span className={isCollapsed ? "lg:sr-only" : ""}>{route.label}</span>
                    </>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>
    </aside>
  );
}
