import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navigation } from './components/Navigation';
import { Dashboard } from './pages/Dashboard';
import { PropertiesPage } from './pages/PropertiesPage';
import { PropertyDetail } from './pages/PropertyDetail';
import { LeasesPage } from './pages/LeasesPage';
import { OwnersPage } from './pages/OwnersPage';
import { ManagementCompaniesPage } from './pages/ManagementCompaniesPage';
import { TenantsPage } from './pages/TenantsPage';
import { HOAsPage } from './pages/HOAsPage';
import { HOADetail } from './pages/HOADetail';
import { LeaseBreakPage } from './pages/LeaseBreakPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { NotFound } from './pages/NotFound';

function App() {
  return (
    <Router>
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/properties" element={<PropertiesPage />} />
          <Route path="/properties/:id" element={<PropertyDetail />} />
          <Route path="/leases" element={<LeasesPage />} />
          <Route path="/owners" element={<OwnersPage />} />
          <Route path="/management-companies" element={<ManagementCompaniesPage />} />
          <Route path="/tenants" element={<TenantsPage />} />
          <Route path="/hoas" element={<HOAsPage />} />
          <Route path="/hoas/:id" element={<HOADetail />} />
          <Route path="/lease-breaks" element={<LeaseBreakPage />} />
          <Route path="/lease-breaks/:requestId" element={<LeaseBreakPage />} />
          <Route path="/approvals" element={<ApprovalsPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </Router>
  );
}

export default App;
