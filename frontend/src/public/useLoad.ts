import { useEffect, useState } from 'react';

/** Minimal loader for the public site (keeps it independent of landlord code). */
export function useLoad<T>(loader: () => Promise<T>, key: string) {
  const [state, setState] = useState<{ key: string; data?: T; error?: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    loader()
      .then((data) => !cancelled && setState({ key, data }))
      .catch((e: Error) => !cancelled && setState({ key, error: e.message }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const current = state?.key === key ? state : null;
  return { data: current?.data, error: current?.error, loading: current === null };
}
