import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
      <p className="font-mono text-6xl font-bold text-orange">404</p>
      <h1 className="mt-4 text-xl font-semibold text-ink">Page not found</h1>
      <p className="mt-2 text-sm text-muted">
        The page you're looking for doesn't exist or has moved.
      </p>
      <Link
        to="/dashboard"
        className="mt-6 rounded-lg bg-orange px-4 py-2 text-sm font-semibold text-white transition hover:bg-orangeDark"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
