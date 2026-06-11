import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProfileLibraryPage } from "@/features/profiles/ProfileLibraryPage";

const elenaId = "11111111-1111-1111-1111-111111111111";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProfileLibraryPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function profilePayload({
  id,
  kind,
  name
}: {
  id: string;
  kind: "host" | "guest";
  name: string;
}) {
  return {
    id,
    name,
    role_title: kind === "host" ? "Editorial Strategy Host" : "Market Expert Guest",
    kind,
    archetype: kind === "host" ? "Sharp editorial strategist" : "Creator market analyst",
    bio: `${name} is a reusable ${kind} persona.`,
    is_active: true,
    created_at: "2026-06-06T00:00:00Z",
    updated_at: "2026-06-06T00:00:00Z"
  };
}

function listPayload(items = activeProfiles()) {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 20,
    total_pages: items.length ? 1 : 0,
    has_next: false,
    has_previous: false
  };
}

function activeProfiles() {
  return [
    profilePayload({ id: elenaId, kind: "host", name: "Elena Park" }),
    profilePayload({
      id: "22222222-2222-2222-2222-222222222222",
      kind: "guest",
      name: "Avery Stone"
    })
  ];
}

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" }
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ProfileLibraryPage", () => {
  it("deletes a profile from the library", async () => {
    let deleted = false;
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes(`/api/v1/profiles/${elenaId}`) && init?.method === "DELETE") {
        deleted = true;
        return jsonResponse({
          ...profilePayload({ id: elenaId, kind: "host", name: "Elena Park" }),
          is_active: false
        });
      }
      if (url.includes("/api/v1/profiles/recommendations")) {
        return jsonResponse({
          items: [
            {
              profile: profilePayload({ id: elenaId, kind: "host", name: "Elena Park" }),
              reason: "Matches the host lane.",
              confidence_score: 91
            }
          ]
        });
      }
      if (url.includes("/api/v1/profiles")) {
        const remaining = activeProfiles().filter((profile) => !deleted || profile.id !== elenaId);
        return jsonResponse(listPayload(remaining));
      }
      return jsonResponse({});
    });

    renderPage();

    const deleteButton = await screen.findByRole("button", { name: /delete elena park/i });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalledWith(expect.stringContaining("Delete Elena Park?"));
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/profiles/${elenaId}`),
        expect.objectContaining({ method: "DELETE" })
      );
    });
  });
});
