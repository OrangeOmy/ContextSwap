import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Receipt, Home } from 'lucide-react';

export default function Layout() {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-white">
      <aside className="w-64 flex flex-col border-r border-gray-200 bg-gray-50 shrink-0">
        <div className="p-4 border-b border-gray-200">
          <Link
            to="/"
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-gray-700 text-sm font-medium transition-colors"
          >
            <Home className="w-4 h-4" />
            Home
          </Link>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          <div className="text-xs text-gray-400 font-medium px-3 py-2 uppercase tracking-wider">
            ContextSwap
          </div>
          <Link
            to="/dashboard"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              location.pathname === '/dashboard'
                ? 'bg-primary/10 text-primary font-medium'
                : 'hover:bg-gray-100 text-gray-700'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </Link>
          <Link
            to="/transactions"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              location.pathname === '/transactions'
                ? 'bg-primary/10 text-primary font-medium'
                : 'hover:bg-gray-100 text-gray-700'
            }`}
          >
            <Receipt className="w-4 h-4" />
            Transactions
          </Link>
        </nav>
        <div className="p-3 border-t border-gray-200">
          <div className="text-xs text-gray-400 px-3">Data from FastAPI</div>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
