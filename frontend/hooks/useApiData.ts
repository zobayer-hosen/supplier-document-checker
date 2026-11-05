"use client";

import { useCallback, useEffect, useState } from "react";

interface Options<T> {
  /** Reload this often (milliseconds)... */
  pollEveryMs?: number;
  /** ...but only while this returns true for the latest data. */
  pollWhile?: (data: T) => boolean;
}

interface ApiData<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/**
 * Load data from the API and keep loading/error state.
 * `load` must not change between renders: pass a module function or wrap it in useCallback.
 */
export function useApiData<T>(load: () => Promise<T>, options: Options<T> = {}): ApiData<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    load()
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [load]);

  useEffect(() => {
    reload();
  }, [reload]);

  const { pollEveryMs, pollWhile } = options;
  const shouldPoll = pollEveryMs !== undefined && data !== null && (pollWhile ? pollWhile(data) : true);

  useEffect(() => {
    if (!shouldPoll) return;
    const timer = setInterval(reload, pollEveryMs);
    return () => clearInterval(timer);
  }, [shouldPoll, reload, pollEveryMs]);

  return { data, error, loading, reload };
}
