// Decide which app this browser tab is: the public tour site or the landlord app.
//
// Deployed: the server says which, via <meta name="apex-site"> (it knows its
// PUBLIC_HOSTS, including staging's dev-tours.). Fallback: the hostname list.
// Local dev: add ?site=public (or ?site=landlord) to the URL to switch; the
// choice sticks for the tab. The backend enforces the real boundary — this
// only picks which UI to render.

const PUBLIC_HOSTS = (import.meta.env.VITE_PUBLIC_HOSTS || 'apexelementgrp.com,www.apexelementgrp.com,tours.apexelementgrp.com')
  .split(',')
  .map((h: string) => h.trim().toLowerCase())
  .filter(Boolean);

export function isPublicSite(): boolean {
  const site = document.querySelector('meta[name="apex-site"]')?.getAttribute('content');
  if (site) return site === 'public';
  if (PUBLIC_HOSTS.includes(window.location.hostname.toLowerCase())) return true;
  if (import.meta.env.DEV) {
    const param = new URLSearchParams(window.location.search).get('site');
    if (param) sessionStorage.setItem('site', param);
    return sessionStorage.getItem('site') === 'public';
  }
  return false;
}
