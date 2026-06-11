import { useEffect, useMemo, useRef, useState } from "react";

import { BarChart3, ChevronDown, LogOut, Search, UserCircle } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth, useCurrentUser } from "@/features/auth/hooks";
import { primaryRoutes, seriesStages } from "@/routes/routeRegistry";

type WorkspaceSearchItem = {
  description: string;
  keywords: string;
  label: string;
  path: string;
};

const workspaceSearchItems: WorkspaceSearchItem[] = [
  ...primaryRoutes.map((route) => ({
    description: route.description,
    keywords: `${route.label} ${route.boundary}`,
    label: route.label,
    path: route.path
  })),
  {
    description: "Research run history, evidence scoring, and source documents.",
    keywords: "research evidence runs documents scoring",
    label: "Research",
    path: "/research"
  },
  {
    description: "LLM token utilization and per-agent AI usage.",
    keywords: "ai stats tokens llm agents usage utilization",
    label: "AI Stats",
    path: "/ai-stats"
  },
  {
    description: "External services, credentials, health, and quotas.",
    keywords: "integrations external services credentials api keys providers sources settings",
    label: "Integrations",
    path: "/settings?tab=integrations"
  }
];

export function TopBar() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLFormElement>(null);

  const currentSeriesId = useMemo(() => {
    const match = location.pathname.match(/^\/series\/([^/]+)/);
    return match?.[1] ?? null;
  }, [location.pathname]);

  const searchResults = useMemo(() => {
    const seriesStageItems = currentSeriesId
      ? seriesStages.map((stage) => ({
          description: `Open the ${stage.label} stage for this series.`,
          keywords: `series production stage ${stage.id} ${stage.label}`,
          label: stage.label,
          path: `/series/${currentSeriesId}/${stage.id}`
        }))
      : [];
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return [];
    }

    return [...workspaceSearchItems, ...seriesStageItems]
      .filter((item) =>
        `${item.label} ${item.description} ${item.keywords}`.toLowerCase().includes(query)
      )
      .slice(0, 7);
  }, [currentSeriesId, searchQuery]);

  useEffect(() => {
    if (!isAccountMenuOpen && !isSearchOpen) {
      return undefined;
    }

    function handlePointerDown(event: PointerEvent) {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setIsAccountMenuOpen(false);
      }
      if (!searchRef.current?.contains(event.target as Node)) {
        setIsSearchOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsAccountMenuOpen(false);
        setIsSearchOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isAccountMenuOpen, isSearchOpen]);

  async function signOut() {
    setIsAccountMenuOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  function openAccountRoute(path: string) {
    setIsAccountMenuOpen(false);
    navigate(path);
  }

  function runSearch(path = searchResults[0]?.path) {
    if (!path) {
      return;
    }
    navigate(path);
    setSearchQuery("");
    setIsSearchOpen(false);
  }

  return (
    <header className="sticky top-0 z-20 flex min-h-16 flex-col items-stretch justify-between gap-3 border-b border-streamly-lavenderStrong/70 bg-streamly-paper/84 px-4 py-3 backdrop-blur-xl sm:flex-row sm:items-center sm:px-6 lg:px-10">
      <form
        className="relative block w-full max-w-md"
        onSubmit={(event) => {
          event.preventDefault();
          runSearch();
        }}
        ref={searchRef}
        role="search"
      >
        <label className="sr-only" htmlFor="workspace-search">
          Search workspace
        </label>
        <Search
          aria-hidden
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--streamly-text-muted)]"
        />
        <input
          aria-autocomplete="list"
          aria-controls="workspace-search-results"
          aria-expanded={isSearchOpen && searchQuery.trim().length > 0}
          aria-label="Search workspace"
          autoComplete="off"
          className="h-11 w-full rounded-streamly-pill border border-streamly-lavenderStrong/80 bg-white/86 pl-9 pr-4 text-sm font-semibold outline-none shadow-streamly-card transition focus:border-streamly-electric focus:ring-2 focus:ring-streamly-electric/25"
          id="workspace-search"
          onChange={(event) => {
            setSearchQuery(event.target.value);
            setIsSearchOpen(true);
          }}
          onFocus={() => setIsSearchOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              runSearch();
            }
          }}
          placeholder="Search workspace"
          type="search"
          value={searchQuery}
        />

        {isSearchOpen && searchQuery.trim().length > 0 ? (
          <div
            className="absolute left-0 top-[calc(100%+0.55rem)] z-40 w-full overflow-hidden rounded-streamly-card border border-streamly-lavenderStrong/80 bg-white shadow-streamly-elevated"
            id="workspace-search-results"
            role="listbox"
          >
            {searchResults.length ? (
              searchResults.map((item) => (
                <button
                  className="block w-full px-4 py-3 text-left transition hover:bg-streamly-wash focus:bg-streamly-wash focus:outline-none"
                  key={item.path}
                  onClick={() => runSearch(item.path)}
                  role="option"
                  type="button"
                >
                  <span className="block text-sm font-extrabold text-streamly-coal">
                    {item.label}
                  </span>
                  <span className="mt-0.5 block text-xs font-bold leading-5 text-streamly-purpleBlue">
                    {item.description}
                  </span>
                </button>
              ))
            ) : (
              <p className="px-4 py-3 text-sm font-bold text-[var(--streamly-text-muted)]">
                No workspace matches.
              </p>
            )}
          </div>
        ) : null}
      </form>

      <div className="flex flex-wrap items-center gap-3 sm:ml-6 sm:justify-end">
        {user ? (
          <div className="relative" ref={accountMenuRef}>
            <button
              aria-expanded={isAccountMenuOpen}
              aria-haspopup="menu"
              className="inline-flex min-h-11 items-center gap-2 rounded-streamly-pill bg-white px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card transition hover:-translate-y-0.5 hover:shadow-streamly-glow focus:outline-none focus:ring-2 focus:ring-streamly-electric focus:ring-offset-2"
              onClick={() => setIsAccountMenuOpen((value) => !value)}
              type="button"
            >
              <UserCircle aria-hidden className="h-5 w-5 text-streamly-electric" />
              <span className="max-w-[12rem] truncate">{user.name || user.email}</span>
              <ChevronDown
                aria-hidden
                className={`h-4 w-4 text-[var(--streamly-text-muted)] transition ${
                  isAccountMenuOpen ? "rotate-180" : ""
                }`}
              />
            </button>

            {isAccountMenuOpen ? (
              <div
                className="absolute right-0 top-[calc(100%+0.65rem)] z-30 min-w-52 rounded-streamly-card border border-streamly-lavenderStrong/80 bg-white p-2 shadow-streamly-elevated"
                role="menu"
              >
                <button
                  className="flex w-full items-center gap-2 rounded-streamly-card px-3 py-2.5 text-left text-sm font-extrabold text-streamly-coal transition hover:bg-streamly-wash focus:outline-none focus:ring-2 focus:ring-streamly-electric"
                  onClick={() => openAccountRoute("/ai-stats")}
                  role="menuitem"
                  type="button"
                >
                  <BarChart3 aria-hidden className="h-4 w-4 text-streamly-electric" />
                  AI Stats
                </button>
                <button
                  className="flex w-full items-center gap-2 rounded-streamly-card px-3 py-2.5 text-left text-sm font-extrabold text-streamly-coal transition hover:bg-streamly-wash focus:outline-none focus:ring-2 focus:ring-streamly-electric"
                  onClick={() => void signOut()}
                  role="menuitem"
                  type="button"
                >
                  <LogOut aria-hidden className="h-4 w-4 text-streamly-electric" />
                  Log out
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </header>
  );
}
