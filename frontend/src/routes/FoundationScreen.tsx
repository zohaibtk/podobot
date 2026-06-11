import type { PrimaryRoute } from "@/routes/routeRegistry";
import { EmptyState } from "@/design-system/components/EmptyState";
import { PageHeader } from "@/design-system/components/PageHeader";

type FoundationScreenProps = {
  route: PrimaryRoute;
};

export function FoundationScreen({ route }: FoundationScreenProps) {
  const Icon = route.icon;

  return (
    <section className="flex min-h-full flex-col gap-6">
      <PageHeader
        actions={
          <div className="grid h-12 w-12 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
            <Icon aria-hidden className="h-5 w-5" />
          </div>
        }
        description={route.description}
        kicker={route.boundary}
        title={route.label}
      />

      <EmptyState
        title={`${route.label} foundation ready`}
        description="This phase establishes the shell, boundaries, routing, and design-system primitives only. Business workflows will be added in later phases."
      />
    </section>
  );
}
