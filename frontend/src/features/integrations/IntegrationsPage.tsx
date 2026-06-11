import { Globe2 } from "lucide-react";

import { PageHeader } from "@/design-system/components/PageHeader";
import { BufferIntegrationSection } from "@/features/integrations/BufferIntegrationSection";
import { ResearchSourcesSection } from "@/features/integrations/ResearchSourcesSection";

export function IntegrationsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        actions={
          <div className="grid h-12 w-12 place-items-center rounded-streamly-pill bg-streamly-lavender text-streamly-electric">
            <Globe2 aria-hidden className="h-5 w-5" />
          </div>
        }
        description="Connect publishing services and manage the research providers used by future workflow runs."
        kicker="Integrations"
        title="Integrations"
      />

      <BufferIntegrationSection />
      <ResearchSourcesSection />
    </section>
  );
}
