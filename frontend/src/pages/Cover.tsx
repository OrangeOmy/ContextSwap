import { Link } from 'react-router-dom';
import { ArrowRight, Zap, Shield, MessageSquare } from 'lucide-react';

export default function Cover() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white flex flex-col">
      <header className="px-6 py-4 flex items-center justify-between border-b border-gray-200/80">
        <span className="text-lg font-semibold text-gray-800">ContextSwap</span>
        <nav className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Dashboard
          </Link>
          <Link
            to="/transactions"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Transactions
          </Link>
        </nav>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center max-w-2xl mx-auto">
        <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 tracking-tight">
          P2P Context Trading
        </h1>
        <p className="mt-4 text-lg text-gray-600">
          Exchange context with humans or AI agents. Powered by x402 and verified on-chain.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white font-medium rounded-lg hover:bg-primary-hover transition-colors"
          >
            Open Dashboard
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/transactions"
            className="inline-flex items-center gap-2 px-6 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            View Transactions
          </Link>
        </div>

        <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-8 text-left">
          <div className="flex flex-col items-center sm:items-start">
            <div className="p-3 rounded-lg bg-primary/10 text-primary">
              <Zap className="w-6 h-6" />
            </div>
            <h3 className="mt-3 font-semibold text-gray-900">x402 Payments</h3>
            <p className="mt-1 text-sm text-gray-600">Pay for context with Conflux or Tron.</p>
          </div>
          <div className="flex flex-col items-center sm:items-start">
            <div className="p-3 rounded-lg bg-primary/10 text-primary">
              <Shield className="w-6 h-6" />
            </div>
            <h3 className="mt-3 font-semibold text-gray-900">On-chain Verification</h3>
            <p className="mt-1 text-sm text-gray-600">Settlement verified by facilitator.</p>
          </div>
          <div className="flex flex-col items-center sm:items-start">
            <div className="p-3 rounded-lg bg-primary/10 text-primary">
              <MessageSquare className="w-6 h-6" />
            </div>
            <h3 className="mt-3 font-semibold text-gray-900">Telegram Sessions</h3>
            <p className="mt-1 text-sm text-gray-600">Deal in a dedicated topic.</p>
          </div>
        </div>
      </main>

      <footer className="py-4 text-center text-sm text-gray-400">
        Data from FastAPI · ContextSwap
      </footer>
    </div>
  );
}
