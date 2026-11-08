import type { Profile, ProfileUpdate, Track, TrackSummary } from "../types/track.types";
import { requestJson } from "./httpClient";

export const trackApi = {
  listTracks: () => requestJson<TrackSummary[]>("/api/tracks"),

  getTrack: (trackId: string) => requestJson<Track>(`/api/tracks/${encodeURIComponent(trackId)}`),

  /** null until the learner has picked a track. */
  getProfile: () => requestJson<Profile | null>("/api/profile"),

  saveProfile: (update: ProfileUpdate) =>
    requestJson<Profile>("/api/profile", { method: "PUT", body: JSON.stringify(update) }),
};
