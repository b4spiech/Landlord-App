import { Link } from 'react-router-dom';

export const NotFound = () => (
  <div className="text-center py-24">
    <p className="text-6xl font-bold text-blue-600">404</p>
    <h1 className="text-xl font-semibold text-gray-900 mt-4">Page not found</h1>
    <p className="text-gray-500 mt-2">The page you're looking for doesn't exist.</p>
    <Link to="/" className="inline-block mt-6 text-blue-600 font-medium hover:underline">
      &larr; Back to dashboard
    </Link>
  </div>
);
