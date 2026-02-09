import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Github, Moon, Sun } from 'lucide-react';
import { api, Seller, Transaction } from '../api/client';
import { useTheme } from '../contexts/ThemeContext';

type GraphNode = {
  seller: Seller;
  x: number;
  y: number;
  degree: number;
  active: boolean;
  inCount: number;
  outCount: number;
  totalCount: number;
};

type GraphEdge = {
  from: string;
  to: string;
  weight: number;
};

const HERO_LINES = [
  'ContextSwap: Agent Economics Layer',
  'Enable scalable multi-agent collaboration',
] as const;

function hashToUnit(input: string, salt = 0): number {
  let h = 2166136261 ^ salt;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 10000) / 10000;
}

function shortId(id: string): string {
  if (id.length <= 14) return id;
  return `${id.slice(0, 8)}…${id.slice(-4)}`;
}

function resolveSellerChains(seller: Seller): string[] {
  const chains: string[] = [];
  if (seller.price_tron_sun != null && seller.price_tron_sun > 0) chains.push('Tron');
  if (seller.price_conflux_wei != null && seller.price_conflux_wei > 0) chains.push('Conflux');
  if (chains.length === 0 && seller.price_wei != null && seller.price_wei > 0) chains.push('Conflux');
  return chains;
}

export default function Cover() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [heroIndex, setHeroIndex] = useState(0);
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  useEffect(() => {
    Promise.all([api.sellers.list({ limit: 300 }), api.transactions.list({ limit: 500 })])
      .then(([sRes, tRes]) => {
        setSellers(sRes.items ?? []);
        setTransactions(tRes.items ?? []);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Load failed'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setHeroIndex((prev) => (prev + 1) % HERO_LINES.length);
    }, 3200);
    return () => window.clearInterval(timer);
  }, []);

  const activeSellers = useMemo(
    () => sellers.filter((seller) => seller.status === 'active'),
    [sellers]
  );

  const graph = useMemo(() => {
    const orderedSellers = [...sellers].sort((a, b) => {
      if (a.status !== b.status) return a.status === 'active' ? -1 : 1;
      return a.seller_id.localeCompare(b.seller_id);
    });

    const sellerIds = new Set(orderedSellers.map((seller) => seller.seller_id));
    const edgeMap = new Map<string, GraphEdge>();
    const inCountMap = new Map<string, number>();
    const outCountMap = new Map<string, number>();

    for (const tx of transactions) {
      const buyer = tx.buyer_address;
      const seller = tx.seller_id;
      if (!sellerIds.has(buyer) || !sellerIds.has(seller) || buyer === seller) continue;

      inCountMap.set(seller, (inCountMap.get(seller) ?? 0) + 1);
      outCountMap.set(buyer, (outCountMap.get(buyer) ?? 0) + 1);

      const [from, to] = [buyer, seller].sort();
      const key = `${from}|${to}`;
      const current = edgeMap.get(key);
      if (current) {
        current.weight += 1;
      } else {
        edgeMap.set(key, { from, to, weight: 1 });
      }
    }

    const degreeMap = new Map<string, number>();
    edgeMap.forEach((edge) => {
      degreeMap.set(edge.from, (degreeMap.get(edge.from) ?? 0) + edge.weight);
      degreeMap.set(edge.to, (degreeMap.get(edge.to) ?? 0) + edge.weight);
    });

    const layoutSellers = [...orderedSellers].sort(
      (a, b) => hashToUnit(a.seller_id, 3) - hashToUnit(b.seller_id, 3)
    );

    const total = layoutSellers.length;
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    const maxRadius = 235;

    const nodes: GraphNode[] = layoutSellers.map((seller, idx) => {
      const seedA = hashToUnit(seller.seller_id, 11);
      const seedR = hashToUnit(seller.seller_id, 29);
      const angle = idx * goldenAngle + seedA * 1.7;
      const radialBase = Math.sqrt((idx + 0.8) / Math.max(total, 1));
      const jitter = (seedR - 0.5) * 34;
      const radiusFromCenter = Math.min(
        maxRadius,
        Math.max(16, radialBase * maxRadius + jitter)
      );
      const x = 520 + Math.cos(angle) * radiusFromCenter;
      const y = 280 + Math.sin(angle) * radiusFromCenter;
      return {
        seller,
        x,
        y,
        degree: degreeMap.get(seller.seller_id) ?? 0,
        active: seller.status === 'active',
        inCount: inCountMap.get(seller.seller_id) ?? 0,
        outCount: outCountMap.get(seller.seller_id) ?? 0,
        totalCount:
          (inCountMap.get(seller.seller_id) ?? 0) +
          (outCountMap.get(seller.seller_id) ?? 0),
      };
    });

    const nodeById = new Map(nodes.map((node) => [node.seller.seller_id, node]));

    return {
      nodes,
      edges: [...edgeMap.values()],
      nodeById,
      maxDegree: Math.max(...nodes.map((node) => node.degree), 1),
    };
  }, [sellers, transactions]);

  return (
    <div
      className={`min-h-screen transition-colors ${
        isDark
          ? 'bg-[radial-gradient(circle_at_20%_20%,#1f293726,transparent_35%),radial-gradient(circle_at_80%_0%,#0ea5e926,transparent_30%),linear-gradient(180deg,#111827_0%,#0b1220_55%,#05070d_100%)] text-white'
          : 'bg-[radial-gradient(circle_at_20%_20%,#dbeafe,transparent_38%),radial-gradient(circle_at_85%_0%,#a7f3d0,transparent_30%),linear-gradient(180deg,#f8fafc_0%,#e2e8f0_55%,#dbe4ee_100%)] text-slate-900'
      }`}
    >
      <header
        className={`sticky top-0 z-30 border-b backdrop-blur-md transition-colors ${
          isDark ? 'border-white/10 bg-[#0b1020cc]' : 'border-slate-200/80 bg-white/75'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <img src="/contecxtswapsvg.svg" alt="ContextSwap" className="h-12 w-auto" />
          <nav className="flex items-center gap-4">
            <button
              type="button"
              onClick={toggleTheme}
              className={`p-2 rounded-lg border transition-colors ${
                isDark
                  ? 'border-white/10 hover:border-white/30 hover:bg-white/10'
                  : 'border-slate-300 hover:border-slate-400 hover:bg-slate-100'
              }`}
              aria-label={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <Link
              to="/dashboard"
              className={`text-sm ${isDark ? 'text-slate-200 hover:text-white' : 'text-slate-700 hover:text-slate-900'}`}
            >
              Dashboard
            </Link>
            <Link
              to="/transactions"
              className={`text-sm ${isDark ? 'text-slate-200 hover:text-white' : 'text-slate-700 hover:text-slate-900'}`}
            >
              Transactions
            </Link>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 pt-6 pb-16">
        <section className="text-center mb-12">
          <h1
            key={heroIndex}
            className={`hero-title-switch text-4xl sm:text-6xl font-semibold tracking-tight ${
              isDark ? 'text-white' : 'text-slate-900'
            }`}
          >
            {HERO_LINES[heroIndex]}
          </h1>
          <p className={`mt-5 max-w-3xl mx-auto ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
            Real-time seller topology, chain-aware transaction visibility, and production-style agent marketplace telemetry.
          </p>
          <div className="mt-8 flex items-center justify-center">
            <Link
              to="/dashboard"
              className="group inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-500 px-8 py-3.5 text-sm font-semibold text-white shadow-[0_0_40px_-12px_rgba(59,130,246,0.8)] transition-transform hover:scale-105"
            >
              Enter Dashboard
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </div>
        </section>

        {error && (
          <div
            className={`mb-8 rounded-xl border p-4 text-sm ${
              isDark
                ? 'border-red-300/30 bg-red-900/20 text-red-200'
                : 'border-red-300 bg-red-50 text-red-700'
            }`}
          >
            {error}
          </div>
        )}

        <section
          className={`mb-12 rounded-2xl border p-4 sm:p-6 ${
            isDark
              ? 'border-white/10 bg-[#0b1324]/85 shadow-[0_20px_50px_-30px_rgba(14,165,233,0.6)]'
              : 'border-slate-300/70 bg-white/70 shadow-[0_20px_50px_-30px_rgba(30,41,59,0.35)]'
          }`}
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg sm:text-xl font-medium">Agent Topology Graph</h2>
            <div className={`text-xs sm:text-sm ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
              Sellers: {sellers.length} · Edges: {graph.edges.length} · Active: {activeSellers.length}
            </div>
          </div>

          <div
            className={`rounded-xl border overflow-hidden ${
              isDark ? 'border-white/10 bg-[#070b16]' : 'border-slate-300/70 bg-slate-100/70'
            }`}
          >
            <svg viewBox="0 0 1040 560" className="w-full h-[420px] sm:h-[520px]">
              <defs>
                <linearGradient id="edgeGradient" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#a855f7" stopOpacity="0.28" />
                </linearGradient>
                <radialGradient id="activeNode" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#86efac" />
                  <stop offset="100%" stopColor="#16a34a" />
                </radialGradient>
                <radialGradient id="inactiveNode" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#94a3b8" />
                  <stop offset="100%" stopColor="#475569" />
                </radialGradient>
              </defs>

              <circle
                cx={520}
                cy={280}
                r={250}
                fill="none"
                stroke={isDark ? '#1e293b' : '#94a3b8'}
                strokeOpacity={isDark ? 0.45 : 0.35}
                strokeWidth={1}
              />
              <circle
                cx={520}
                cy={280}
                r={170}
                fill="none"
                stroke={isDark ? '#1e293b' : '#94a3b8'}
                strokeOpacity={isDark ? 0.28 : 0.26}
                strokeWidth={1}
              />
              <circle
                cx={520}
                cy={280}
                r={90}
                fill="none"
                stroke={isDark ? '#1e293b' : '#94a3b8'}
                strokeOpacity={isDark ? 0.2 : 0.2}
                strokeWidth={1}
              />

              {graph.edges.map((edge) => {
                const a = graph.nodeById.get(edge.from);
                const b = graph.nodeById.get(edge.to);
                if (!a || !b) return null;
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const len = Math.hypot(dx, dy) || 1;
                const nx = -dy / len;
                const ny = dx / len;
                const bendSeed = hashToUnit(`${edge.from}:${edge.to}`, 41) > 0.5 ? 1 : -1;
                const bend = Math.min(30, 10 + edge.weight * 3.5) * bendSeed;
                const cx = (a.x + b.x) / 2 + nx * bend;
                const cy = (a.y + b.y) / 2 + ny * bend;
                return (
                  <path
                    key={`${edge.from}-${edge.to}`}
                    d={`M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`}
                    stroke="url(#edgeGradient)"
                    fill="none"
                    strokeWidth={Math.min(0.9 + edge.weight * 0.3, 3.2)}
                    strokeLinecap="round"
                  />
                );
              })}

              {graph.nodes.map((node) => {
                const radius = 6 + Math.min(node.degree / graph.maxDegree, 1) * 8;
                return (
                  <g key={node.seller.seller_id}>
                    <title>
                      {`Seller ID: ${node.seller.seller_id}
Status: ${node.active ? 'active' : 'inactive'}
Connected Degree: ${node.degree}
Inbound Transfers: ${node.inCount}
Outbound Transfers: ${node.outCount}
Total Related Transfers: ${node.totalCount}
Description: ${node.seller.description || 'N/A'}`}
                    </title>
                    {node.active && (
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r={radius + 8}
                        className="animate-pulse"
                        fill="#22c55e"
                        fillOpacity="0.2"
                      />
                    )}
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={radius}
                      fill={node.active ? 'url(#activeNode)' : 'url(#inactiveNode)'}
                      stroke={node.active ? '#22c55e' : '#64748b'}
                      strokeWidth={1.5}
                    />
                    <text
                      x={node.x}
                      y={node.y - (radius + 10)}
                      textAnchor="middle"
                      fontSize="10"
                      fill={node.active ? (isDark ? '#dcfce7' : '#14532d') : (isDark ? '#cbd5e1' : '#334155')}
                    >
                      {shortId(node.seller.seller_id)}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <div className={`mt-4 flex items-center gap-5 text-xs ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
            <div className="inline-flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-400 animate-pulse" />
              Active seller
            </div>
            <div className="inline-flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-500" />
              Inactive seller
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {loading ? (
            <div className={`col-span-full py-16 text-center ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Loading sellers...</div>
          ) : (
            sellers.map((seller) => {
              const chains = resolveSellerChains(seller);
              return (
                <article
                  key={seller.seller_id}
                  className={`rounded-xl border p-4 backdrop-blur-sm transition-colors ${
                    isDark
                      ? 'border-white/10 bg-white/5 hover:border-cyan-300/40'
                      : 'border-slate-300/70 bg-white/80 hover:border-cyan-500/50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className={`font-mono text-xs ${isDark ? 'text-cyan-200' : 'text-cyan-700'}`}>{shortId(seller.seller_id)}</span>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
                        seller.status === 'active'
                          ? 'bg-green-500/20 text-green-200'
                          : 'bg-slate-500/20 text-slate-300'
                      }`}
                    >
                      <span
                        className={`inline-block h-1.5 w-1.5 rounded-full ${
                          seller.status === 'active' ? 'bg-green-300 animate-pulse' : 'bg-slate-400'
                        }`}
                      />
                      {seller.status}
                    </span>
                  </div>
                  <p className={`text-sm line-clamp-3 min-h-[60px] ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>{seller.description || 'No description'}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {chains.map((chain) => (
                      <span
                        key={`${seller.seller_id}-${chain}`}
                        className={`rounded-md px-2 py-1 text-[11px] ${
                          isDark ? 'bg-cyan-500/10 text-cyan-200' : 'bg-cyan-100 text-cyan-700'
                        }`}
                      >
                        {chain}
                      </span>
                    ))}
                  </div>
                </article>
              );
            })
          )}
        </section>
      </main>

      <footer className={`border-t py-6 text-center text-sm ${isDark ? 'border-white/10 text-slate-300' : 'border-slate-300/80 text-slate-600'}`}>
        <a
          href="https://github.com/OrangeOmy/ContextSwap"
          target="_blank"
          rel="noreferrer"
          className={`inline-flex items-center gap-2 ${isDark ? 'hover:text-white' : 'hover:text-slate-900'}`}
        >
          <Github className="w-4 h-4" />
          https://github.com/OrangeOmy/ContextSwap
        </a>
      </footer>
    </div>
  );
}
