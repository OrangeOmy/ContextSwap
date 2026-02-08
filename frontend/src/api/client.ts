import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export interface Seller {
  seller_id: string;
  evm_address: string;
  price_wei?: number;
  price_conflux_wei?: number;
  price_tron_sun?: number;
  description: string;
  keywords: string[] | string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  transaction_id: string;
  seller_id: string;
  buyer_address: string;
  price_wei: number;
  payment_chain?: 'tron' | 'conflux' | null;
  payment_network?: string;
  status: string;
  tx_hash?: string | null;
  chat_id?: string | null;
  message_thread_id?: number | null;
  metadata?: {
    buyer_bot_username?: string;
    seller_bot_username?: string;
    initial_prompt?: string;
  };
  error_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ListSellersResponse {
  items: Seller[];
}

export interface ListTransactionsResponse {
  items: Transaction[];
}

export const api = {
  health: async (): Promise<{ status: string }> => {
    const res = await client.get('/healthz');
    return res.data;
  },
  sellers: {
    list: async (params?: { limit?: number; offset?: number; status?: string }): Promise<ListSellersResponse> => {
      const res = await client.get('/v1/sellers', { params: params ?? {} });
      return res.data;
    },
    search: async (keyword: string): Promise<ListSellersResponse> => {
      const res = await client.get('/v1/sellers/search', { params: { keyword } });
      return res.data;
    },
    get: async (sellerId: string): Promise<Seller> => {
      const res = await client.get(`/v1/sellers/${sellerId}`);
      return res.data;
    },
    register: async (data: {
      evm_address: string;
      price_wei?: number;
      price_conflux_wei?: number;
      price_tron_sun?: number;
      description?: string;
      keywords?: string[] | string;
      seller_id?: string;
    }): Promise<Seller> => {
      const res = await client.post('/v1/sellers/register', data);
      return res.data;
    },
    unregister: async (data: { seller_id?: string; evm_address?: string }): Promise<Seller> => {
      const res = await client.post('/v1/sellers/unregister', data);
      return res.data;
    },
  },
  transactions: {
    list: async (params?: {
      limit?: number;
      offset?: number;
      status?: string;
      seller_id?: string;
    }): Promise<ListTransactionsResponse> => {
      const res = await client.get('/v1/transactions', { params: params ?? {} });
      return res.data;
    },
    get: async (transactionId: string): Promise<Transaction> => {
      const res = await client.get(`/v1/transactions/${transactionId}`);
      return res.data;
    },
  },
};

export default client;
