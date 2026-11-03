import { useEffect } from 'react';
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';

import { COMPANY } from './company';
import { HomePage } from './pages/HomePage';
import { ListingPage } from './pages/ListingPage';
import { FeedbackPage } from './pages/FeedbackPage';
import { TourRequestPage } from './pages/TourRequestPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { SmsTermsPage } from './pages/SmsTermsPage';

const ScrollToTop = () => {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
};

/** "Request a tour" in the header: keeps the home you're viewing selected. */
const HeaderTourLink = () => {
  const { pathname } = useLocation();
  const home = pathname.match(/^\/homes\/([^/]+)/)?.[1];
  return (
    <Link
      to={home ? `/tour?home=${home}` : '/tour'}
      className="text-sm font-medium text-blue-700 hover:underline"
    >
      Request a tour
    </Link>
  );
};

const NotFound = () => (
  <div className="text-center py-24">
    <h1 className="text-2xl font-semibold">Page not found</h1>
    <Link to="/" className="inline-block mt-6 text-blue-700 font-medium hover:underline">
      &larr; See available homes
    </Link>
  </div>
);

export default function PublicApp() {
  useEffect(() => {
    document.title = `Tour a home | ${COMPANY.shortName}`;
  }, []);

  return (
    <BrowserRouter>
      <ScrollToTop />
      <div className="min-h-screen flex flex-col bg-white">
        <header className="border-b">
          <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
            <Link to="/" className="text-lg font-bold text-gray-900">
              {COMPANY.shortName}
            </Link>
            <HeaderTourLink />
          </div>
        </header>

        <main className="flex-1 w-full max-w-3xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/homes/:id" element={<ListingPage />} />
            <Route path="/tour" element={<TourRequestPage />} />
            <Route path="/feedback/:token" element={<FeedbackPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/sms-terms" element={<SmsTermsPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>

        <footer className="border-t text-sm text-gray-500">
          <div className="max-w-3xl mx-auto px-4 py-6 flex flex-wrap gap-x-6 gap-y-2 justify-between">
            <span>
              &copy; {new Date().getFullYear()} {COMPANY.legalName}
            </span>
            <nav className="flex gap-4">
              <Link to="/privacy" className="hover:underline">Privacy Policy</Link>
              <Link to="/sms-terms" className="hover:underline">SMS Terms</Link>
              <a href={`mailto:${COMPANY.email}`} className="hover:underline">{COMPANY.email}</a>
            </nav>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}
