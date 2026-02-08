import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Zap,
  Shield,
  MessageSquare,
  Users,
  UserCheck,
  Sun,
  Moon,
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { api, Seller, Transaction } from '../api/client';

type BuyerStats = {
  buyer_address: string;
  tx_count: number;
  total_wei: number;
  last_tx_at: string;
};

const STATUS_COLORS: Record<string, string> = {
  active: '#4b5563',
  inactive: '#9ca3af',
};

function deriveBuyers(transactions: Transaction[]): BuyerStats[] {
  const byAddr: Record<string, { count: number; total: number; last: string }> = {};
  for (const t of transactions) {
    const addr = t.buyer_address;
    if (!byAddr[addr]) {
      byAddr[addr] = { count: 0, total: 0, last: t.created_at };
    }
    byAddr[addr].count += 1;
    byAddr[addr].total += t.price_wei;
    if (t.created_at > byAddr[addr].last) byAddr[addr].last = t.created_at;
  }
  return Object.entries(byAddr).map(([buyer_address, v]) => ({
    buyer_address,
    tx_count: v.count,
    total_wei: v.total,
    last_tx_at: v.last,
  }));
}

function formatAddr(addr: string) {
  return `${addr.slice(0, 8)}…${addr.slice(-6)}`;
}

export default function Cover() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.sellers.list({ limit: 200 }), api.transactions.list({ limit: 500 })])
      .then(([sRes, tRes]) => {
        setSellers(sRes.items ?? []);
        setTransactions(tRes.items ?? []);
      })
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false));
  }, []);

  const activeSellers = sellers.filter((s) => s.status === 'active');
  const buyers = deriveBuyers(transactions);

  const sellerStatusData = [
    { name: '活跃', value: activeSellers.length, color: STATUS_COLORS.active },
    { name: '非活跃', value: sellers.length - activeSellers.length, color: STATUS_COLORS.inactive },
  ].filter((d) => d.value > 0);

  const sellerPriceBuckets: Record<string, number> = {};
  activeSellers.forEach((s) => {
    const p = s.price_conflux_wei ?? s.price_wei ?? 0;
    const cfx = p / 1e18;
    const bucket =
      cfx === 0 ? '0' : cfx < 0.001 ? '<0.001' : cfx < 0.01 ? '0.001-0.01' : cfx < 0.1 ? '0.01-0.1' : '≥0.1';
    sellerPriceBuckets[bucket] = (sellerPriceBuckets[bucket] ?? 0) + 1;
  });
  const sellerPriceData = ['0', '<0.001', '0.001-0.01', '0.01-0.1', '≥0.1'].map((name) => ({
    name,
    count: sellerPriceBuckets[name] ?? 0,
  }));

  const buyerTxCountData = [...buyers]
    .sort((a, b) => b.tx_count - a.tx_count)
    .slice(0, 8)
    .map((b) => ({
      address: formatAddr(b.buyer_address),
      交易笔数: b.tx_count,
    }));

  const buyerVolumeData = [...buyers]
    .sort((a, b) => b.total_wei - a.total_wei)
    .slice(0, 8)
    .map((b) => ({
      address: formatAddr(b.buyer_address),
      支付CFX: Number((b.total_wei / 1e18).toFixed(6)),
    }));

  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-900 flex flex-col">
      <header className="px-6 py-4 flex items-center justify-between border-b border-gray-200/80 dark:border-gray-800">
        <span className="text-lg font-semibold text-gray-800 dark:text-white">ContextSwap</span>
        <nav className="flex items-center gap-4">
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
            aria-label={theme === 'dark' ? '切换到浅色' : '切换到深色'}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <Link to="/dashboard" className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
            Dashboard
          </Link>
          <Link to="/transactions" className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
            Transactions
          </Link>
        </nav>
      </header>

      <main className="flex-1 px-6 py-8 max-w-6xl mx-auto w-full">
        <section className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white tracking-tight">
            ContextSwap
          </h1>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            P2P context trading — exchange context with humans or AI agents. Pay with Conflux or Tron, verified on-chain. Powered by x402.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-medium rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors"
            >
              Open Dashboard
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/transactions"
              className="inline-flex items-center gap-2 px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              View Transactions
            </Link>
          </div>
        </section>

        <section className="mb-12 grid grid-cols-1 sm:grid-cols-3 gap-6 text-left">
          <div className="flex flex-col items-center sm:items-start">
            <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
              <Zap className="w-6 h-6" />
            </div>
            <h3 className="mt-3 font-semibold text-gray-900 dark:text-white">x402 Payments</h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">Pay for context with Conflux or Tron.</p>
          </div>
          <div className="flex flex-col items-center sm:items-start">
            <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
              <Shield className="w-6 h-6" />
            </div>
            <h3 className="mt-3 font-semibold text-gray-900 dark:text-white">On-chain Verification</h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">Settlement verified by facilitator.</p>
          </div>
          <div className="flex flex-col items-center sm:items-start">
            <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
              <MessageSquare className="w-6 h-6" />
            </div>
            <h3 className="mt-3 font-semibold text-gray-900 dark:text-white">Telegram Sessions</h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">Deal in a dedicated topic.</p>
          </div>
        </section>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
            {error} · 请确认后端已启动
          </div>
        )}

        <section className="mb-10">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            活跃买家与卖家概览
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm flex items-center gap-4">
              <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                <UserCheck className="w-8 h-8" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{activeSellers.length}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">活跃卖家</p>
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm flex items-center gap-4">
              <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                <Users className="w-8 h-8" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{buyers.length}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">活跃买家（有交易记录）</p>
              </div>
            </div>
          </div>

          <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-3">卖家 / 买家属性可视化</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">卖家状态分布</p>
              {sellerStatusData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={sellerStatusData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={70}
                      label={({ name, value }) => `${name}: ${value}`}
                    >
                      {sellerStatusData.map((_, i) => (
                        <Cell key={i} fill={sellerStatusData[i].color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">暂无卖家数据</p>
              )}
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">卖家价格分布 (CFX)</p>
              {sellerPriceData.some((d) => d.count > 0) ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={sellerPriceData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#4b5563" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">暂无卖家数据</p>
              )}
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">买家交易笔数 Top8</p>
              {buyerTxCountData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={buyerTxCountData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                    <XAxis dataKey="address" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="交易笔数" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">暂无买家交易数据</p>
              )}
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">买家支付金额 Top8 (CFX)</p>
              {buyerVolumeData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={buyerVolumeData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                    <XAxis dataKey="address" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="支付CFX" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">暂无买家交易数据</p>
              )}
            </div>
          </div>

          <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-3">卖家表格</h3>
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden mb-8">
            {loading ? (
              <div className="p-8 text-center text-gray-500">加载中...</div>
            ) : sellers.length === 0 ? (
              <div className="p-8 text-center text-gray-500">暂无卖家</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-gray-700/50 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      <th className="py-3 px-4">Seller ID</th>
                      <th className="py-3 px-4">地址</th>
                      <th className="py-3 px-4">价格 (CFX/TRX)</th>
                      <th className="py-3 px-4">描述</th>
                      <th className="py-3 px-4">关键词</th>
                      <th className="py-3 px-4">状态</th>
                      <th className="py-3 px-4">创建时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sellers.map((s) => {
                      const priceCfx = s.price_conflux_wei ?? s.price_wei;
                      const priceStr = priceCfx
                        ? `${(priceCfx / 1e18).toFixed(6)} CFX`
                        : s.price_tron_sun
                          ? `${(s.price_tron_sun / 1e6).toFixed(4)} TRX`
                          : '—';
                      const kw =
                        typeof s.keywords === 'string'
                          ? s.keywords
                          : Array.isArray(s.keywords)
                            ? s.keywords.join(', ')
                            : '—';
                      return (
                        <tr key={s.seller_id} className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50/80 dark:hover:bg-gray-700/50">
                          <td className="py-3 px-4 font-mono text-gray-900 dark:text-gray-100">{s.seller_id}</td>
                          <td className="py-3 px-4 font-mono text-gray-600 dark:text-gray-400">{formatAddr(s.evm_address)}</td>
                          <td className="py-3 px-4 text-gray-700 dark:text-gray-300">{priceStr}</td>
                          <td className="py-3 px-4 text-gray-600 dark:text-gray-400 max-w-[200px] truncate" title={s.description}>
                            {s.description || '—'}
                          </td>
                          <td className="py-3 px-4 text-gray-600 dark:text-gray-400 max-w-[160px] truncate" title={kw}>
                            {kw || '—'}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                                s.status === 'active' ? 'bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                              }`}
                            >
                              {s.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-gray-500 dark:text-gray-400">
                            {new Date(s.created_at).toLocaleDateString('zh-CN')}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-3">买家表格</h3>
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">加载中...</div>
            ) : buyers.length === 0 ? (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">暂无买家（无交易记录）</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-gray-700/50 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      <th className="py-3 px-4">买家地址</th>
                      <th className="py-3 px-4">交易笔数</th>
                      <th className="py-3 px-4">总支付 (CFX)</th>
                      <th className="py-3 px-4">最近交易时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {buyers
                      .sort((a, b) => new Date(b.last_tx_at).getTime() - new Date(a.last_tx_at).getTime())
                      .map((b) => (
                        <tr key={b.buyer_address} className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50/80 dark:hover:bg-gray-700/50">
                          <td className="py-3 px-4 font-mono text-gray-900 dark:text-gray-100" title={b.buyer_address}>
                            {formatAddr(b.buyer_address)}
                          </td>
                          <td className="py-3 px-4 text-gray-700 dark:text-gray-300">{b.tx_count}</td>
                          <td className="py-3 px-4 text-gray-700 dark:text-gray-300">
                            {(b.total_wei / 1e18).toFixed(6)}
                          </td>
                          <td className="py-3 px-4 text-gray-500 dark:text-gray-400">
                            {new Date(b.last_tx_at).toLocaleString('zh-CN')}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </main>

      <footer className="py-4 text-center text-sm text-gray-400 dark:text-gray-500 border-t border-gray-200 dark:border-gray-800">
        ContextSwap · Powered by x402
      </footer>
    </div>
  );
}
