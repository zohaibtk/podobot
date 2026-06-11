import {
  CalendarClock,
  Gauge,
  Library,
  Settings,
  Sparkles,
  Users
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type PrimaryRoute = {
  path: string;
  label: string;
  description: string;
  icon: LucideIcon;
  boundary: string;
};

export const primaryRoutes: PrimaryRoute[] = [
  {
    path: "/dashboard",
    label: "Dashboard",
    description: "Operational work queue, blockers, and pipeline health.",
    icon: Gauge,
    boundary: "dashboard"
  },
  {
    path: "/series",
    label: "Series",
    description: "Series list and staged production workspace entry.",
    icon: Library,
    boundary: "series"
  },
  {
    path: "/strategy",
    label: "Strategy",
    description: "Scheduled research runs and idea backlog.",
    icon: Sparkles,
    boundary: "strategy"
  },
  {
    path: "/profiles",
    label: "Profiles",
    description: "Reusable host, guest, and persona library.",
    icon: Users,
    boundary: "profiles"
  },
  {
    path: "/publishing",
    label: "Publishing",
    description: "Caption approval, schedules, Buffer status, and recovery.",
    icon: CalendarClock,
    boundary: "publishing"
  },
  {
    path: "/settings",
    label: "Settings",
    description: "Role management, user management, and integrations.",
    icon: Settings,
    boundary: "settings"
  }
];

export const foundationRoutes = primaryRoutes.filter(
  (route) =>
    ![
      "/dashboard",
      "/series",
      "/strategy",
      "/profiles",
      "/publishing",
      "/settings"
    ].includes(route.path)
);

export const seriesStages = [
  { id: "discovery", label: "Discovery" },
  { id: "narrative", label: "Narrative" },
  { id: "plan", label: "Plan" },
  { id: "outlines", label: "Outlines" },
  { id: "briefs", label: "Briefs" },
  { id: "recordings", label: "Recordings" },
  { id: "captions", label: "Captions" },
  { id: "schedule", label: "Schedule" }
] as const;

export type SeriesStageId = (typeof seriesStages)[number]["id"];
