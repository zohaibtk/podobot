export type HealthStatus = "healthy" | "degraded" | "failed";

export type FoundationBoundary =
  | "frontend"
  | "backend"
  | "database"
  | "queue"
  | "agents"
  | "mcp"
  | "design-system";
