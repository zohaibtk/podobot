import { afterEach, describe, expect, it, vi } from "vitest";

import {
  deleteEpisodeThumbnail,
  deleteSeries,
  downloadBrief,
  runDiscovery,
  uploadEpisodeTranscript
} from "@/features/series/api";
import {
  clearAccessToken,
  writeAccessToken
} from "@/features/auth/tokenStorage";

afterEach(() => {
  clearAccessToken();
  vi.restoreAllMocks();
});

describe("series API authenticated binary requests", () => {
  it("sends bearer token when downloading a brief", async () => {
    writeAccessToken("download-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("## Brief", {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="brief.md"'
        }
      })
    );

    const result = await downloadBrief("series-1", "brief-1");

    expect(result.filename).toBe("brief.md");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/series/series-1/briefs/brief-1/download"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer download-token"
        })
      })
    );
  });

  it("sends bearer token and FormData when uploading a transcript", async () => {
    writeAccessToken("upload-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ episodes: [], readiness: {}, series: {} }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await uploadEpisodeTranscript(
      "series-1",
      "episode-1",
      new File(["hello"], "transcript.txt", { type: "text/plain" })
    );

    const [, options] = fetchMock.mock.calls[0];
    expect(options?.method).toBe("POST");
    expect(options?.body).toBeInstanceOf(FormData);
    expect(options?.headers).toEqual(
      expect.objectContaining({
        Authorization: "Bearer upload-token"
      })
    );
  });

  it("starts provider-backed discovery for a series", async () => {
    writeAccessToken("discovery-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          series: {},
          progress_percent: 0,
          ledger: [],
          narratives: [],
          selected_narrative_id: null,
          research_activity: {}
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" }
        }
      )
    );

    await runDiscovery("series-1");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/series/series-1/discovery/run"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer discovery-token"
        })
      })
    );
  });

  it("deletes a series with bearer authorization", async () => {
    writeAccessToken("delete-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, {
        status: 204
      })
    );

    await deleteSeries("series-1");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/series/series-1"),
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({
          Authorization: "Bearer delete-token"
        })
      })
    );
  });

  it("deletes an episode thumbnail with bearer authorization", async () => {
    writeAccessToken("thumbnail-delete-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ episodes: [], readiness: {}, series: {} }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await deleteEpisodeThumbnail("series-1", "episode-1", "thumbnail-1");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/api/v1/series/series-1/recordings/episodes/episode-1/thumbnails/thumbnail-1"
      ),
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({
          Authorization: "Bearer thumbnail-delete-token"
        })
      })
    );
  });
});
