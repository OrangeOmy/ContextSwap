import { useState, useEffect } from 'react';
import { Search, Users, Activity, TrendingUp, Zap } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
} from 'recharts';
import { api, Seller, Transaction } from '../api/client';
import SellerCard from '../components/SellerCard';
import StatsCard from '../components/StatsCard';

const STATUS_COLORS: Record<string, string> = {
  paid: '#4b5563',
  session_created: '#6b7280',
  pending: '#d97706',
  failed: '#dc2626',
};

function Dashboard() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sellersRes, txRes] = await Promise.all([
        searchKeyword.trim()
          ? api.sellers.search(searchKeyword.trim() || ' ')
          : api.sellers.list({ limit: 200, status: 'active' }),
        api.transactions.list({ limit: 100 }),
      ]);
      const sellerList = sellersRes.items || [];
      const txList = txRes.items || [];
      setSellers(sellerList);
      setTransactions(txList);
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败');
      setSellers([]);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAll();
  };

  const totalSellers = sellers.length;
  const activeTx = transactions.filter(
    (t) => t.status === 'paid' || t.status === 'session_created'
  ).length;
  const totalVolume = transactions.reduce((s, t) => s + t.price_wei, 0);
  const avgPrice =
    transactions.length > 0 ? totalVolume / transactions.length : 0;

  const statusCounts = transactions.reduce<Record<string, number>>((acc, t) => {
    acc[t.status] = (acc[t.status] || 0) + 1;
    return acc;
  }, {});
  const statusChartData = Object.entries(statusCounts).map(([name, value]) => ({
    name,
    value,
  }));

  const byDate = transactions.reduce<Record<string, number>>((acc, t) => {
    const d = t.created_at.slice(0, 10);
    acc[d] = (acc[d] || 0) + t.price_wei;
    return acc;
  }, {});
  const volumeChartData = Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14)
    .map(([date, volume]) => ({
      date,
      volume: Number((volume / 1e18).toFixed(6)),
    }));

  const priceBuckets = sellers.reduce<Record<string, number>>((acc, s) => {
    const p = s.price_conflux_wei ?? s.price_wei ?? s.price_tron_sun ?? 0;
    const cfx = p / 1e18;
    const bucket =
      cfx === 0
        ? '0'
        : cfx < 0.001
          ? '<0.001'
          : cfx < 0.01
            ? '0.001-0.01'
            : cfx < 0.1
              ? '0.01-0.1'
              : '≥0.1';
    acc[bucket] = (acc[bucket] || 0) + 1;
    return acc;
  }, {});
  const priceChartData = ['0', '<0.001', '0.001-0.01', '0.01-0.1', '≥0.1'].map(
    (name) => ({ name, count: priceBuckets[name] || 0 })
  );

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          P2P context trading
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
          API 错误: {error}. 请确认后端已启动:{' '}
          <code className="bg-red-100 dark:bg-red-900/40 px-1 rounded">
            uv run python -m contextswap.platform.main
          </code>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard title="活跃卖家" value={totalSellers} icon={Users} />
        <StatsCard title="成功交易" value={activeTx} icon={Activity} />
        <StatsCard
          title="总交易量 (CFX)"
          value={(totalVolume / 1e18).toFixed(4)}
          icon={TrendingUp}
        />
        <StatsCard
          title="平均单价 (CFX)"
          value={(avgPrice / 1e18).toFixed(6)}
          icon={Zap}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-[#171717] p-5 shadow-sm">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            交易状态分布
          </h3>
          {statusChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={statusChartData}
                layout="vertical"
                margin={{ top: 4, right: 16, left: 60, bottom: 4 }}
              >
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={52} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar
                  dataKey="value"
                  nameKey="name"
                  radius={[0, 4, 4, 0]}
                  label={{ position: 'right', fontSize: 11 }}
                >
                  {statusChartData.map((entry, i) => (
                    <rect
                      key={entry.name}
                      x={0}
                      y={0}
                      width="100%"
                      height="100%"
                      fill={STATUS_COLORS[entry.name] ?? '#94a3b8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">
              暂无交易数据
            </p>
          )}
        </div>
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            每日交易量 (CFX)
          </h3>
          {volumeChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={volumeChartData}>
                <defs>
                  <linearGradient id="vol" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4b5563" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#4b5563" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => [v, 'CFX']} />
                <Area
                  type="monotone"
                  dataKey="volume"
                  stroke="#4b5563"
                  fill="url(#vol)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">
              暂无交易数据
            </p>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm mb-8">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          卖家价格分布 (CFX)
        </h3>
        {priceChartData.some((d) => d.count > 0) ? (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={priceChartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#4b5563" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400 dark:text-gray-500 text-sm py-8 text-center">
            暂无卖家数据
          </p>
        )}
      </div>

      <form onSubmit={handleSearch} className="flex gap-3 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            placeholder="搜索卖家关键词..."
            className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-400/30 focus:border-gray-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-5 py-2.5 bg-gray-800 dark:bg-gray-200 hover:bg-gray-900 dark:hover:bg-white text-white dark:text-gray-900 text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? '搜索中...' : '搜索'}
        </button>
      </form>

      <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">卖家列表</h2>
      {loading ? (
        <div className="flex justify-center py-16 text-gray-500 dark:text-gray-400">
          <span className="animate-pulse">加载中...</span>
        </div>
      ) : sellers.length === 0 ? (
        <div className="py-16 text-center rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400">
          未找到卖家
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sellers.map((s) => (
            <SellerCard key={s.seller_id} seller={s} />
          ))}
        </div>
      )}

      <footer className="mt-12 pt-6 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-400 dark:text-gray-500">
        Powered by x402
      </footer>
    </div>
  );
}

export default Dashboard;
