import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Receipt, Home, Sun, Moon } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

export default function Layout() {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex h-screen bg-white dark:bg-[#0d0d0d]">
      <aside className="w-64 flex flex-col border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-[#171717] shrink-0">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <Link
            to="/"
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium transition-colors"
          >
            <Home className="w-4 h-4" />
            Home
          </Link>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          <div className="flex items-center gap-2 px-3 py-2">
            <img src="/contecxtswapsvg.svg" alt="" className="h-10 w-auto" aria-hidden />
            <span className="text-xs text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wider">ContextSwap</span>
          </div>
          <Link
            to="/dashboard"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              location.pathname === '/dashboard'
                ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white font-medium'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </Link>
          <Link
            to="/transactions"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              location.pathname === '/transactions'
                ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white font-medium'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            <Receipt className="w-4 h-4" />
            Transactions
          </Link>
        </nav>
        <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <span className="text-xs text-gray-400 dark:text-gray-500 px-1">ContextSwap</span>
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 transition-colors"
            aria-label={theme === 'dark' ? '切换到浅色' : '切换到深色'}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
