// Decide which app this browser tab is: the public tour site or the landlord app.
//
// Production: decided by hostname (tours.apexelementgrp.com = public).
// Local dev: add ?site=public (or ?site=landlord) to the URL to switch; the
// choice sticks for the tab. The backend enforces the real boundary — this
// only picks which UI to render.

const PUBLIC_HOSTS = (import.meta.env.VITE_PUBLIC_HOSTS || 'tours.apexelementgrp.com')
  .split(',')
  .map((h: string) => h.trim().toLowerCase())
  .filter(Boolean);

export function isPublicSite(): boolean {
  if (PUBLIC_HOSTS.includes(window.location.hostname.toLowerCase())) return true;
  if (import.meta.env.DEV) {
    const param = new URLSearchParams(window.location.search).get('site');
    if (param) sessionStorage.setItem('site', param);
    return sessionStorage.getItem('site') === 'public';
  }
  return false;
}
