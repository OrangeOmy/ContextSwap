import { Transaction } from '../api/client';
import { Hash, Clock } from 'lucide-react';

interface TransactionListProps {
  transactions: Transaction[];
}

function TransactionList({ transactions }: TransactionListProps) {
  const formatAddress = (address: string) =>
    `${address.slice(0, 8)}...${address.slice(-6)}`;

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'paid':
      case 'session_created':
        return 'bg-green-50 text-green-700';
      case 'pending':
        return 'bg-amber-50 text-amber-700';
      case 'failed':
        return 'bg-red-50 text-red-700';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  if (transactions.length === 0) {
    return (
      <div className="text-center py-12 rounded-lg border border-gray-200 bg-gray-50 text-gray-500">
        暂无交易记录
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {transactions.map((tx) => (
        <div
          key={tx.transaction_id}
          className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <Hash className="w-5 h-5 text-gray-400" />
              <div>
                <p className="font-mono text-sm text-gray-700">
                  {formatAddress(tx.transaction_id)}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(tx.created_at).toLocaleString('zh-CN')}
                </p>
              </div>
            </div>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusClass(tx.status)}`}
            >
              {tx.status}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-gray-500 mb-1">买家地址</p>
              <p className="font-mono text-sm text-gray-700">
                {formatAddress(tx.buyer_address)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">价格</p>
              <p className="text-sm font-medium text-gray-900">
                {(tx.price_wei / 1e18).toFixed(6)} CFX
              </p>
            </div>
          </div>
          {tx.metadata?.initial_prompt && (
            <div className="pt-4 border-t border-gray-100">
              <p className="text-xs text-gray-500 mb-2">初始提示</p>
              <p className="text-sm text-gray-700 line-clamp-2">
                {tx.metadata.initial_prompt}
              </p>
            </div>
          )}
          {tx.tx_hash && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs text-gray-500 mb-1">交易哈希</p>
              <p className="font-mono text-xs text-gray-600 break-all">
                {tx.tx_hash}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default TransactionList;
