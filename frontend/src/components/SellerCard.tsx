import { Seller } from '../api/client';
import { Wallet, Tag, Clock } from 'lucide-react';

interface SellerCardProps {
  seller: Seller;
}

function SellerCard({ seller }: SellerCardProps) {
  const formatPrice = (wei?: number, sun?: number) => {
    if (sun) return `${(sun / 1e6).toFixed(4)} TRX`;
    if (wei) return `${(wei / 1e18).toFixed(6)} CFX`;
    return 'N/A';
  };

  const formatAddress = (address: string) =>
    `${address.slice(0, 6)}...${address.slice(-4)}`;

  const keywords = Array.isArray(seller.keywords)
    ? seller.keywords
    : typeof seller.keywords === 'string'
      ? seller.keywords.split(',').map((k) => k.trim())
      : [];

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm hover:border-gray-300 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            seller.status === 'active'
              ? 'bg-green-50 text-green-700'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          {seller.status === 'active' ? '活跃' : '非活跃'}
        </span>
      </div>
      <div className="flex items-center gap-2 mb-2">
        <Wallet className="w-4 h-4 text-gray-400" />
        <span className="text-sm font-mono text-gray-600">
          {formatAddress(seller.evm_address)}
        </span>
      </div>
      <p className="text-sm text-gray-700 mb-3 line-clamp-2">
        {seller.description || '无描述'}
      </p>
      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {keywords.slice(0, 3).map((keyword, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-100 text-gray-600 text-xs"
            >
              <Tag className="w-3 h-3" />
              {keyword}
            </span>
          ))}
          {keywords.length > 3 && (
            <span className="text-xs text-gray-400">+{keywords.length - 3}</span>
          )}
        </div>
      )}
      <div className="space-y-2 pt-3 border-t border-gray-100">
        {seller.price_conflux_wei != null && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Conflux</span>
            <span className="font-medium text-gray-900">
              {formatPrice(seller.price_conflux_wei)}
            </span>
          </div>
        )}
        {seller.price_tron_sun != null && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Tron</span>
            <span className="font-medium text-gray-900">
              {formatPrice(undefined, seller.price_tron_sun)}
            </span>
          </div>
        )}
        {seller.price_conflux_wei == null &&
          seller.price_tron_sun == null &&
          seller.price_wei != null && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">价格</span>
              <span className="font-medium text-gray-900">
                {formatPrice(seller.price_wei)}
              </span>
            </div>
          )}
      </div>
      <div className="flex items-center gap-1 mt-3 text-xs text-gray-400">
        <Clock className="w-3 h-3" />
        创建于 {new Date(seller.created_at).toLocaleDateString('zh-CN')}
      </div>
    </div>
  );
}

export default SellerCard;
