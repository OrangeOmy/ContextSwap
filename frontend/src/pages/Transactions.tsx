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

function TransactionRow({ tx }: { tx: Transaction }) {
  const config = STATUS_CONFIG[tx.status] ?? {
    label: tx.status,
    color: 'text-gray-700 bg-gray-100',
    icon: Clock,
  };
  const Icon = config.icon;
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
      <td className="py-3 px-4 text-sm text-gray-600">
        {tx.seller_id}
      </td>
      <td className="py-3 px-4 font-mono text-xs text-gray-500">
        {tx.buyer_address.slice(0, 10)}…{tx.buyer_address.slice(-8)}
      </td>
      <td className="py-3 px-4 text-sm font-medium text-gray-900">
        {(tx.price_wei / 1e18).toFixed(6)} CFX
      </td>
      <td className="py-3 px-4">
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}
        >
          <Icon className="w-3.5 h-3.5" />
          {config.label}
        </span>
      </td>
      <td className="py-3 px-4 text-sm text-gray-500">
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

  useEffect(() => {
    api.transactions
      .list({ limit: 100 })
      .then((res) => {
        setTransactions(res.items || []);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : '加载失败');
        setTransactions([]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Transactions</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          交易列表与详情
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16 text-gray-500">
          <span className="animate-pulse">加载中...</span>
        </div>
      ) : transactions.length === 0 ? (
        <div className="py-16 text-center rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400">
          暂无交易记录
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-700/50 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <th className="py-3 px-4">交易 ID</th>
                <th className="py-3 px-4">卖家 ID</th>
                <th className="py-3 px-4">买家地址</th>
                <th className="py-3 px-4">金额</th>
                <th className="py-3 px-4">状态</th>
                <th className="py-3 px-4">时间</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <TransactionRow key={tx.transaction_id} tx={tx} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <footer className="mt-12 pt-6 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-400 dark:text-gray-500">
        Powered by x402
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

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <Link
        to="/transactions"
        className="text-sm text-gray-800 dark:text-gray-200 hover:underline mb-6 inline-block"
      >
        ← 返回交易列表
      </Link>
      <h1 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">交易详情</h1>
      <p className="font-mono text-sm text-gray-500 dark:text-gray-400 break-all mb-8">
        {tx.transaction_id}
      </p>

      <div className="space-y-6">
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">
            交易流程
          </h3>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
              <User className="w-5 h-5 text-gray-400 dark:text-gray-500" />
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">买家</p>
                <p className="font-mono text-sm text-gray-900 dark:text-gray-100 break-all">
                  {tx.buyer_address}
                </p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-300 shrink-0 hidden sm:block" />
            <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600">
              <Wallet className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">支付</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {(tx.price_wei / 1e18).toFixed(6)} CFX
                </p>
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
                    {tx.message_thread_id != null &&
                      ` · Thread: ${tx.message_thread_id}`}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
            状态
          </h3>
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
            <p className="font-mono text-sm text-gray-700 dark:text-gray-300 break-all">
              {tx.tx_hash}
            </p>
          </div>
        )}

        {tx.metadata?.initial_prompt && (
          <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
              初始提示
            </h3>
            <p className="text-sm text-gray-700 dark:text-gray-300">{tx.metadata.initial_prompt}</p>
          </div>
        )}

        <div className="text-sm text-gray-500 dark:text-gray-400">
          创建时间: {new Date(tx.created_at).toLocaleString('zh-CN')} · 更新:{' '}
          {new Date(tx.updated_at).toLocaleString('zh-CN')}
        </div>
      </div>
    </div>
  );
}
