import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { trackApi } from "../api/trackApi";
import type { Profile, ProfileUpdate } from "../types/track.types";

interface ProfileValue {
  /** undefined while loading, null when no track has been picked yet. */
  profile: Profile | null | undefined;
  error: string | null;
  saveProfile: (update: ProfileUpdate) => Promise<Profile>;
  reload: () => Promise<void>;
}

const ProfileContext = createContext<ProfileValue | null>(null);

/** The learner's track, interview date and session length, shared by every page. */
export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setError(null);
    try {
      setProfile(await trackApi.getProfile());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const saveProfile = useCallback(async (update: ProfileUpdate) => {
    const saved = await trackApi.saveProfile(update);
    setProfile(saved);
    return saved;
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const value = useMemo(() => ({ profile, error, saveProfile, reload }), [profile, error, saveProfile, reload]);
  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile(): ProfileValue {
  const value = useContext(ProfileContext);
  if (!value) throw new Error("useProfile must be used inside <ProfileProvider>");
  return value;
}
