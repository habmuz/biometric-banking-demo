import axios from 'axios';

const PORTFOLIO_BASE = 'https://portfolio.alhabibi.org';

export interface Account {
  id: string;
  name: string;
  type: 'current' | 'savings' | 'fixed_deposit' | 'investment';
  currency: string;
  balance: number;
  accountNumber: string;
}

export interface Portfolio {
  totalValue: number;
  currency: string;
  accounts: Account[];
  lastUpdated: string;
}

export async function getPortfolio(accessToken: string): Promise<Portfolio> {
  const response = await axios.get<Portfolio>(`${PORTFOLIO_BASE}/portfolio`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    timeout: 10000,
  });
  return response.data;
}
