import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowRight,
  User,
  Wallet,
  MessageSquare,
  CheckCircle,
  XCircle,
  Clock,
  Hash,
  Filter,
} from 'lucide-react';
import { api, Transaction } from '../api/client';

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; icon: typeof CheckCircle }
> = {
  paid: { label: '已支付', color: 'text-gray-800 dark:text-gray-200 bg-gray-200 dark:bg-gray-600', icon: CheckCircle },
  session_created: {
    label: '会话已创建',
    color: 'text-gray-800 dark:text-gray-200 bg-gray-200 dark:bg-gray-600',
    icon: CheckCircle,
  },
  pending: { label: '待处理', color: 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30', icon: Clock },
  failed: { label: '失败', color: 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30', icon: XCircle },
};

type PaymentChain = 'tron' | 'conflux';
type ChainFilter = PaymentChain | 'all';

function resolveChain(tx: Transaction): PaymentChain | null {
  if (tx.payment_chain === 'tron' || tx.payment_chain === 'conflux') {
    return tx.payment_chain;
  }
  const network = (tx.payment_network || '').toLowerCase();
  if (!network) return null;
  if (network.includes('2494104990') || network.includes('tron')) return 'tron';
  return 'conflux';
}

function formatConfluxAmount(tx: Transaction): string {
  return resolveChain(tx) === 'conflux' ? `${(tx.price_wei / 1e18).toFixed(6)} CFX` : '--';
}

function formatTronAmount(tx: Transaction): string {
  return resolveChain(tx) === 'tron' ? `${(tx.price_wei / 1e6).toFixed(3)} TRX` : '--';
}

function chainBadgeClass(chain: PaymentChain | null): string {
  if (chain === 'tron') return 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300';
  if (chain === 'conflux') return 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300';
  return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300';
}

function chainLabel(chain: PaymentChain | null): string {
  if (chain === 'tron') return 'Tron';
  if (chain === 'conflux') return 'Conflux';
  return 'Unknown';
}

function TransactionRow({ tx }: { tx: Transaction }) {
  const config = STATUS_CONFIG[tx.status] ?? {
    label: tx.status,
    color: 'text-gray-700 bg-gray-100 dark:bg-gray-700 dark:text-gray-300',
    icon: Clock,
  };
  const Icon = config.icon;
  const chain = resolveChain(tx);
  const shortId =
    tx.transaction_id.length > 16
      ? `${tx.transaction_id.slice(0, 8)}…${tx.transaction_id.slice(-6)}`
      : tx.transaction_id;

  return (
    <tr className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50/80 dark:hover:bg-gray-800/50">
      <td className="py-3 px-4">
        <Link
          to={`/transactions/${tx.transaction_id}`}
          className="font-mono text-sm text-gray-800 dark:text-gray-200 hover:underline"
        >
          {shortId}
        </Link>
      </td>
      <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-300">{tx.seller_id}</td>
      <td className="py-3 px-4 font-mono text-xs text-gray-500 dark:text-gray-400">
        {tx.buyer_address.slice(0, 10)}…{tx.buyer_address.slice(-8)}
      </td>
      <td className="py-3 px-4 text-sm font-medium text-gray-900 dark:text-gray-100">{formatConfluxAmount(tx)}</td>
      <td className="py-3 px-4 text-sm font-medium text-gray-900 dark:text-gray-100">{formatTronAmount(tx)}</td>
      <td className="py-3 px-4">
        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${chainBadgeClass(chain)}`}>
          {chainLabel(chain)}
        </span>
      </td>
      <td className="py-3 px-4">
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}
        >
          <Icon className="w-3.5 h-3.5" />
          {config.label}
        </span>
      </td>
      <td className="py-3 px-4 text-sm text-gray-500 dark:text-gray-400">
        {new Date(tx.created_at).toLocaleString('zh-CN')}
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/transactions/${tx.transaction_id}`}
          className="text-gray-800 dark:text-gray-200 text-sm font-medium hover:underline inline-flex items-center gap-1"
        >
          详情
          <ArrowRight className="w-4 h-4" />
        </Link>
      </td>
    </tr>
  );
}

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chainFilter, setChainFilter] = useState<ChainFilter>('tron');

  useEffect(() => {
    api.transactions
      .list({ limit: 200 })
      .then((res) => {
        setTransactions(res.items || []);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : '加载失败');
        setTransactions([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredTransactions = transactions.filter((tx) => {
    if (chainFilter === 'all') return true;
    return resolveChain(tx) === chainFilter;
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Transactions</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">按链路查看交易，默认筛选 Tron</p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          <label htmlFor="chain-filter" className="text-sm text-gray-600 dark:text-gray-300">Chain</label>
          <select
            id="chain-filter"
            value={chainFilter}
            onChange={(e) => setChainFilter(e.target.value as ChainFilter)}
            className="bg-transparent text-sm text-gray-800 dark:text-gray-100 outline-none"
          >
            <option value="tron">Tron (Default)</option>
            <option value="conflux">Conflux</option>
            <option value="all">All</option>
          </select>
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          Showing {filteredTransactions.length} / {transactions.length}
        </span>
      </div>

      {loading ? (
        <div className="flex justify-center py-16 text-gray-500">
          <span className="animate-pulse">加载中...</span>
        </div>
      ) : filteredTransactions.length === 0 ? (
        <div className="py-16 text-center rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400">
          当前筛选下暂无交易记录
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1180px]">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  <th className="py-3 px-4">交易 ID</th>
                  <th className="py-3 px-4">卖家 ID</th>
                  <th className="py-3 px-4">买家地址</th>
                  <th className="py-3 px-4">Conflux Amount</th>
                  <th className="py-3 px-4">Tron Amount</th>
                  <th className="py-3 px-4">Chain</th>
                  <th className="py-3 px-4">状态</th>
                  <th className="py-3 px-4">时间</th>
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <tbody>
                {filteredTransactions.map((tx) => (
                  <TransactionRow key={tx.transaction_id} tx={tx} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <footer className="mt-12 pt-6 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-400 dark:text-gray-500 flex flex-wrap items-center justify-between gap-3">
        <span>Powered by x402</span>
        <a
          href="https://github.com/OrangeOmy/ContextSwap"
          target="_blank"
          rel="noreferrer"
          className="hover:text-gray-700 dark:hover:text-gray-300"
        >
          github.com/OrangeOmy/ContextSwap
        </a>
      </footer>
    </div>
  );
}

export function TransactionDetail() {
  const { transactionId } = useParams<{ transactionId: string }>();
  const [tx, setTx] = useState<Transaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const id = transactionId ?? '';

  useEffect(() => {
    if (!id) return;
    api.transactions
      .get(id)
      .then(setTx)
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center text-gray-500">
        加载中...
      </div>
    );
  }
  if (error || !tx) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center text-red-600">
        {error || '未找到该交易'}
      </div>
    );
  }

  const config = STATUS_CONFIG[tx.status] ?? {
    label: tx.status,
    color: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
    icon: Clock,
  };
  const Icon = config.icon;
  const chain = resolveChain(tx);

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <Link
        to="/transactions"
        className="text-sm text-gray-800 dark:text-gray-200 hover:underline mb-6 inline-block"
      >
        ← 返回交易列表
      </Link>
      <h1 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">交易详情</h1>
      <p className="font-mono text-sm text-gray-500 dark:text-gray-400 break-all mb-8">{tx.transaction_id}</p>

      <div className="space-y-6">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">交易流程</h3>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <User className="w-5 h-5 text-gray-400 dark:text-gray-500" />
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">买家</p>
                <p className="font-mono text-sm text-gray-900 dark:text-gray-100 break-all">{tx.buyer_address}</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-300 shrink-0 hidden sm:block" />
            <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600">
              <Wallet className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">支付</p>
                <p className="font-semibold text-gray-900 dark:text-white">{chain === 'tron' ? formatTronAmount(tx) : formatConfluxAmount(tx)}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{chainLabel(chain)}</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-300 shrink-0 hidden sm:block" />
            <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <MessageSquare className="w-5 h-5 text-gray-400 dark:text-gray-500" />
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">卖家 / 会话</p>
                <p className="text-sm text-gray-900 dark:text-gray-100">{tx.seller_id}</p>
                {tx.chat_id && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Chat: {tx.chat_id}
                    {tx.message_thread_id != null && ` · Thread: ${tx.message_thread_id}`}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">状态</h3>
          <span
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${config.color}`}
          >
            <Icon className="w-4 h-4" />
            {config.label}
          </span>
        </div>

        {tx.tx_hash && (
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
              <Hash className="w-4 h-4" />
              链上交易哈希
            </h3>
            <p className="font-mono text-sm text-gray-700 dark:text-gray-300 break-all">{tx.tx_hash}</p>
          </div>
        )}

        {tx.metadata?.initial_prompt && (
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">初始提示</h3>
            <p className="text-sm text-gray-700 dark:text-gray-300">{tx.metadata.initial_prompt}</p>
          </div>
        )}

        <div className="text-sm text-gray-500 dark:text-gray-400">
          创建时间: {new Date(tx.created_at).toLocaleString('zh-CN')} · 更新: {new Date(tx.updated_at).toLocaleString('zh-CN')}
        </div>
      </div>
    </div>
  );
}
