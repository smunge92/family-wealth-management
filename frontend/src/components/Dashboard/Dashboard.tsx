import React, { useState, useEffect, useMemo } from 'react';
import { useMsal } from '@azure/msal-react';
import { Link, useNavigate } from 'react-router-dom';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, LineChart, Line, Legend,
  BarChart, Bar
} from 'recharts';
import api from '../../services/api';
import { useToast } from '../common/Toast';
import { useFamilyMember } from '../../context/FamilyMemberContext';
import { TransactionWithCategory } from '../../types/categories';
import './Dashboard.css';

interface Account {
  account_id: string;
  name: string;
  type: string;
  mask?: string;
  currency: string;
  institution_name?: string;
  balances?: {
    current: number;
    available?: number;
    currency: string;
  };
}

// New color palette: Maroon, Dark Green, Gold, Dark Blue
const CHART_COLORS = ['#800020', '#1a472a', '#d4af37', '#1a365d', '#8b4513', '#2d3748', '#e74c3c', '#27ae60'];

const Dashboard: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<TransactionWithCategory[]>([]);
  const [totals, setTotals] = useState<{ total_income: number; total_expenses: number; pending_count: number }>({
    total_income: 0, total_expenses: 0, pending_count: 0
  });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { accounts: msalAccounts } = useMsal();
  const user = msalAccounts[0];
  const toast = useToast();
  const navigate = useNavigate();
  const { selectedMemberId, getSelectedMemberName } = useFamilyMember();

  useEffect(() => {
    const fetchData = async () => {
      if (!user) return;

      try {
        setLoading(true);
        const familyMemberParam = selectedMemberId ? `&family_member_id=${selectedMemberId}` : '';
        const [accountsRes, transactionsRes] = await Promise.all([
          api.get(`/accounts?user_id=${user.localAccountId}${familyMemberParam}`),
          api.get(`/transactions?user_id=${user.localAccountId}&limit=500${familyMemberParam}`)
        ]);

        setAccounts(accountsRes.data.accounts || []);
        setTransactions(transactionsRes.data.transactions || []);
        if (transactionsRes.data.totals) {
          setTotals(transactionsRes.data.totals);
        }
      } catch (err: any) {
        console.error('Error fetching dashboard data:', err);
        setError(err.response?.data?.error || 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user, selectedMemberId]);

  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // Calculate totals by account type
  const accountsByType = accounts.reduce((acc, account) => {
    const type = account.type || 'other';
    const balance = account.balances?.current || 0;
    acc[type] = (acc[type] || 0) + balance;
    return acc;
  }, {} as Record<string, number>);

  const totalNetWorth = Object.values(accountsByType).reduce((sum, val) => sum + val, 0);

  // Prepare pie chart data
  const pieData = Object.entries(accountsByType).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: Math.abs(value)
  })).filter(d => d.value > 0);

  // Calculate spending by category using user_category_name
  const spendingByCategory = useMemo(() => {
    const byCategory: Record<string, { total: number; color: string | null; icon: string | null }> = {};

    transactions
      .filter(t => t.amount > 0) // expenses
      .forEach(t => {
        const category = t.user_category_name || t.category?.split(',')[0] || 'Uncategorized';
        const color = t.user_category_color || null;
        const icon = t.user_category_icon || null;
        if (!byCategory[category]) {
          byCategory[category] = { total: 0, color, icon };
        }
        byCategory[category].total += t.amount;
      });

    return byCategory;
  }, [transactions]);

  const spendingPieData = useMemo(() => {
    return Object.entries(spendingByCategory)
      .map(([name, data]) => ({
        name,
        value: Math.round(data.total),
        color: data.color,
        icon: data.icon
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [spendingByCategory]);

  // Use API totals when available, fall back to local computation
  const totalExpenses = totals.total_expenses ||
    transactions.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
  const totalIncome = totals.total_income ||
    transactions.filter(t => t.amount < 0).reduce((sum, t) => sum + Math.abs(t.amount), 0);
  const savingsRate = totalIncome > 0 ? ((totalIncome - totalExpenses) / totalIncome * 100) : 0;

  // Monthly spending trend (last 6 months)
  const monthlySpendingTrend = useMemo(() => {
    const monthlyData: Record<string, { income: number; expenses: number }> = {};
    const now = new Date();

    for (let i = 5; i >= 0; i--) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const key = date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      monthlyData[key] = { income: 0, expenses: 0 };
    }

    transactions.forEach(txn => {
      const date = new Date(txn.date);
      const key = date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      if (monthlyData[key]) {
        if (txn.amount > 0) {
          monthlyData[key].expenses += txn.amount;
        } else {
          monthlyData[key].income += Math.abs(txn.amount);
        }
      }
    });

    return Object.entries(monthlyData).map(([month, data]) => ({
      month,
      income: Math.round(data.income),
      expenses: Math.round(data.expenses),
    }));
  }, [transactions]);

  // Spending by Category bar chart data
  const categoryBarData = useMemo(() => {
    return Object.entries(spendingByCategory)
      .map(([name, data]) => ({
        name: data.icon ? `${data.icon} ${name}` : name,
        amount: Math.round(data.total),
        color: data.color || CHART_COLORS[0],
        percentage: totalExpenses > 0 ? Math.round((data.total / totalExpenses) * 100) : 0
      }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 10);
  }, [spendingByCategory, totalExpenses]);

  // Spending Over Time (weekly aggregation, last 90 days)
  const spendingOverTime = useMemo(() => {
    const weeklyData: Record<string, { expenses: number; income: number }> = {};
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 90);

    transactions.forEach(t => {
      const txDate = new Date(t.date);
      if (txDate < cutoff) return;

      const weekStart = new Date(txDate);
      weekStart.setDate(weekStart.getDate() - weekStart.getDay());
      const key = weekStart.toISOString().split('T')[0];

      if (!weeklyData[key]) {
        weeklyData[key] = { expenses: 0, income: 0 };
      }
      if (t.amount > 0) {
        weeklyData[key].expenses += t.amount;
      } else {
        weeklyData[key].income += Math.abs(t.amount);
      }
    });

    return Object.entries(weeklyData)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([date, data]) => {
        const d = new Date(date);
        return {
          week: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          expenses: Math.round(data.expenses),
          income: Math.round(data.income),
        };
      });
  }, [transactions]);

  // Financial Insights
  const financialInsights = useMemo(() => {
    const insights: Array<{ type: 'warning' | 'success' | 'info'; icon: string; text: string }> = [];
    if (transactions.length === 0) return insights;

    // 1. Top spending category alert
    if (spendingPieData.length > 0) {
      const topCategory = spendingPieData[0];
      const pct = totalExpenses > 0 ? Math.round((topCategory.value / totalExpenses) * 100) : 0;
      if (pct > 30) {
        insights.push({
          type: 'warning',
          icon: '!!',
          text: `${topCategory.icon || ''} ${topCategory.name} is ${pct}% of spending (${formatCurrency(topCategory.value)}). Consider setting a budget for this category.`
        });
      } else {
        insights.push({
          type: 'info',
          icon: '#1',
          text: `Top category: ${topCategory.icon || ''} ${topCategory.name} at ${pct}% of spending (${formatCurrency(topCategory.value)}).`
        });
      }
    }

    // 2. Month-over-month change
    const trendData = monthlySpendingTrend.filter(m => m.expenses > 0);
    if (trendData.length >= 2) {
      const current = trendData[trendData.length - 1];
      const previous = trendData[trendData.length - 2];
      if (previous.expenses > 0) {
        const changePercent = Math.round(((current.expenses - previous.expenses) / previous.expenses) * 100);
        if (changePercent > 10) {
          insights.push({
            type: 'warning',
            icon: '!!',
            text: `Spending increased ${changePercent}% this month vs last (${formatCurrency(current.expenses)} vs ${formatCurrency(previous.expenses)}). Review recent purchases.`
          });
        } else if (changePercent < -10) {
          insights.push({
            type: 'success',
            icon: '++',
            text: `Spending decreased ${Math.abs(changePercent)}% vs last month. You saved ${formatCurrency(previous.expenses - current.expenses)}.`
          });
        } else {
          insights.push({
            type: 'info',
            icon: '--',
            text: `Spending is stable (${changePercent > 0 ? '+' : ''}${changePercent}% vs last month).`
          });
        }
      }
    }

    // 3. Savings rate insight
    if (totalIncome > 0) {
      const rate = Math.round(savingsRate);
      if (rate < 10) {
        insights.push({
          type: 'warning',
          icon: '!!',
          text: `Savings rate is only ${rate}%. Financial experts recommend saving at least 20% of income.`
        });
      } else if (rate >= 20) {
        insights.push({
          type: 'success',
          icon: '++',
          text: `Excellent savings rate of ${rate}%! You're saving ${formatCurrency(totalIncome - totalExpenses)} more than you spend.`
        });
      } else {
        const needed = Math.round(totalIncome * 0.2 - (totalIncome - totalExpenses));
        insights.push({
          type: 'info',
          icon: '--',
          text: `Savings rate: ${rate}%. Aim for 20%+ by saving ${formatCurrency(needed)} more per period.`
        });
      }
    }

    // 4. Largest single transaction
    const expenses = transactions.filter(t => t.amount > 0);
    if (expenses.length > 0) {
      const largest = expenses.reduce((max, t) => t.amount > max.amount ? t : max, expenses[0]);
      const avgExpense = totalExpenses / expenses.length;
      if (largest.amount > avgExpense * 5) {
        insights.push({
          type: 'info',
          icon: '$',
          text: `Largest expense: ${formatCurrency(largest.amount)} "${largest.description}" on ${formatDate(largest.date)} (${Math.round(largest.amount / avgExpense)}x your average).`
        });
      }
    }

    // 5. Pending transactions
    const pendingCount = transactions.filter(t => t.pending).length;
    const pendingTotal = transactions.filter(t => t.pending && t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
    if (pendingCount > 0) {
      insights.push({
        type: 'info',
        icon: '...',
        text: `${pendingCount} pending transaction${pendingCount > 1 ? 's' : ''} totaling ${formatCurrency(pendingTotal)}. These may still change.`
      });
    }

    return insights.slice(0, 5);
  }, [transactions, spendingPieData, monthlySpendingTrend, totalExpenses, totalIncome, savingsRate]);

  // Tooltip style shared across charts
  const chartTooltipStyle = {
    contentStyle: {
      background: 'linear-gradient(145deg, #fff8f0, #ffffff)',
      border: '2px solid #800020',
      borderRadius: '10px',
      boxShadow: '0 8px 24px rgba(128, 0, 32, 0.3), 0 4px 8px rgba(0,0,0,0.1)',
      padding: '12px 16px'
    },
    itemStyle: {
      color: '#1a1a1a',
      fontWeight: 600 as const,
      fontSize: '14px'
    },
    labelStyle: {
      color: '#800020',
      fontWeight: 700 as const,
      fontSize: '13px',
      marginBottom: '4px'
    }
  };

  // Sync transactions handler
  const handleSyncTransactions = async () => {
    if (!user || syncing) return;

    try {
      setSyncing(true);
      const response = await api.post('/transactions/sync', {
        user_id: user.localAccountId
      });

      const { total_added, total_modified } = response.data;
      toast.success('Sync Complete', `${total_added} new transactions, ${total_modified} updated`);

      // Refresh data
      const familyMemberParam = selectedMemberId ? `&family_member_id=${selectedMemberId}` : '';
      const [accountsRes, transactionsRes] = await Promise.all([
        api.get(`/accounts?user_id=${user.localAccountId}${familyMemberParam}`),
        api.get(`/transactions?user_id=${user.localAccountId}&limit=500${familyMemberParam}`)
      ]);
      setAccounts(accountsRes.data.accounts || []);
      setTransactions(transactionsRes.data.transactions || []);
      if (transactionsRes.data.totals) {
        setTotals(transactionsRes.data.totals);
      }
    } catch (err: any) {
      toast.error('Sync Failed', err.response?.data?.error || 'Failed to sync transactions');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-3d">
        <div className="dashboard-grid">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card-3d skeleton-card">
              <div className="skeleton skeleton-title"></div>
              <div className="skeleton skeleton-value"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-3d">
      {/* Welcome Section */}
      <div className="welcome-section-3d">
        <h2>
          <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 12 }}>
            <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
          </svg>
          Welcome back, {user?.name?.split(' ')[0] || 'there'}!
        </h2>
        <p className="subtitle">Here's your financial overview</p>
      </div>

      {error && (
        <div className="error-banner-3d">{error}</div>
      )}

      {/* Summary Cards */}
      <div className="summary-cards-3d">
        <div className="summary-card-3d maroon">
          <div className="card-3d-inner">
            <div className="card-icon-3d">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1.41 16.09V20h-2.67v-1.93c-1.71-.36-3.16-1.46-3.27-3.4h1.96c.1 1.05.82 1.87 2.65 1.87 1.96 0 2.4-.98 2.4-1.59 0-.83-.44-1.61-2.67-2.14-2.48-.6-4.18-1.62-4.18-3.67 0-1.72 1.39-2.84 3.11-3.21V4h2.67v1.95c1.86.45 2.79 1.86 2.85 3.39H14.3c-.05-1.11-.64-1.87-2.22-1.87-1.5 0-2.4.68-2.4 1.64 0 .84.65 1.39 2.67 1.91s4.18 1.39 4.18 3.91c-.01 1.83-1.38 2.83-3.12 3.16z"/>
              </svg>
            </div>
            <div className="card-content-3d">
              <span className="card-label-3d">Net Worth</span>
              <span className="card-value-3d">{formatCurrency(totalNetWorth)}</span>
            </div>
          </div>
        </div>

        <div className="summary-card-3d dark-green">
          <div className="card-3d-inner">
            <div className="card-icon-3d">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
              </svg>
            </div>
            <div className="card-content-3d">
              <span className="card-label-3d">Total Income</span>
              <span className="card-value-3d">+{formatCurrency(totalIncome)}</span>
            </div>
          </div>
        </div>

        <div className="summary-card-3d maroon">
          <div className="card-3d-inner">
            <div className="card-icon-3d">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
              </svg>
            </div>
            <div className="card-content-3d">
              <span className="card-label-3d">Total Expenses</span>
              <span className="card-value-3d">-{formatCurrency(totalExpenses)}</span>
            </div>
          </div>
        </div>

        <div className={`summary-card-3d ${savingsRate >= 20 ? 'dark-green' : savingsRate >= 10 ? 'gold' : 'maroon'}`}>
          <div className="card-3d-inner">
            <div className="card-icon-3d">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
              </svg>
            </div>
            <div className="card-content-3d">
              <span className="card-label-3d">Savings Rate</span>
              <span className="card-value-3d">{savingsRate.toFixed(0)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-content-3d">
        {/* Left Column */}
        <div className="dashboard-main-3d">
          {/* Accounts Overview */}
          <div className="card-3d">
            <div className="card-header-3d">
              <h3>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 8 }}>
                  <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z"/>
                </svg>
                Accounts Overview
              </h3>
              <Link to="/accounts" className="view-all-link-3d">View All &rarr;</Link>
            </div>

            {accounts.length === 0 ? (
              <div className="empty-state-3d">
                <div className="empty-icon-3d">
                  <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor" style={{ color: '#800020' }}>
                    <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z"/>
                  </svg>
                </div>
                <h4>No Accounts Connected</h4>
                <p>Link your bank accounts, credit cards, and investments to see your complete financial picture.</p>
                <Link to="/accounts" className="button-3d button-maroon">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style={{ marginRight: 6 }}>
                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                  </svg>
                  Connect Your First Account
                </Link>
              </div>
            ) : (
              <div className="accounts-grid-3d">
                {accounts.slice(0, 4).map(account => (
                  <div key={account.account_id} className="account-card-3d">
                    <div className="account-icon-3d">
                      {account.type === 'depository' ? (
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                          <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z"/>
                        </svg>
                      ) : account.type === 'credit' ? (
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                          <path d="M20 4H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/>
                        </svg>
                      ) : account.type === 'investment' ? (
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                          <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
                        </svg>
                      ) : account.type === 'loan' ? (
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                          <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                          <path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
                        </svg>
                      )}
                    </div>
                    <div className="account-details-3d">
                      <span className="account-name-3d">{account.name}</span>
                      <span className="account-type-3d">{account.type} {account.mask ? `\u2022\u2022${account.mask}` : ''}</span>
                    </div>
                    <div className="account-balance-3d">
                      {account.balances?.current !== undefined
                        ? formatCurrency(account.balances.current, account.currency)
                        : '\u2014'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Transactions */}
          <div className="card-3d">
            <div className="card-header-3d">
              <h3>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 8 }}>
                  <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                </svg>
                Recent Transactions
              </h3>
              <Link to="/transactions" className="view-all-link-3d">View All &rarr;</Link>
            </div>

            {transactions.length === 0 ? (
              <div className="empty-state-3d">
                <div className="empty-icon-3d">
                  <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor" style={{ color: '#800020' }}>
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                  </svg>
                </div>
                <h4>No Transactions Yet</h4>
                <p>Once you connect accounts, sync your transactions to track your spending and income.</p>
                <button
                  className="button-3d button-maroon"
                  onClick={handleSyncTransactions}
                  disabled={syncing || accounts.length === 0}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" className={syncing ? 'spin' : ''} style={{ marginRight: 6 }}>
                    <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                  </svg>
                  {syncing ? 'Syncing...' : 'Sync Transactions'}
                </button>
              </div>
            ) : (
              <div className="transactions-list-3d">
                {transactions.slice(0, 5).map(txn => (
                  <div key={txn.transaction_id} className="transaction-item-3d">
                    <div className={`transaction-icon-3d ${txn.amount > 0 ? 'expense' : 'income'}`}>
                      {txn.user_category_icon || (txn.amount > 0 ? '\u2191' : '\u2193')}
                    </div>
                    <div className="transaction-details-3d">
                      <span className="transaction-name-3d">{txn.description}</span>
                      <span className="transaction-meta-3d">
                        {formatDate(txn.date)} {'\u2022'} {txn.user_category_name || txn.account_name || 'Account'}
                        {txn.pending && <span className="pending-badge-3d">Pending</span>}
                      </span>
                    </div>
                    <div className={`transaction-amount-3d ${txn.amount > 0 ? 'expense' : 'income'}`}>
                      {txn.amount > 0 ? '-' : '+'}{formatCurrency(Math.abs(txn.amount))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Spending by Category Bar Chart */}
          {categoryBarData.length > 0 && (
            <div className="card-3d chart-card-3d">
              <h3>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 8 }}>
                  <path d="M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z"/>
                </svg>
                Spending by Category
              </h3>
              <p className="chart-description-3d">
                Top spending categories from your {transactions.filter(t => t.amount > 0).length} expense transactions
              </p>
              <div className="chart-container-3d">
                <ResponsiveContainer width="100%" height={Math.max(300, categoryBarData.length * 45)}>
                  <BarChart data={categoryBarData} layout="vertical" margin={{ left: 20, right: 30, top: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis
                      type="number"
                      stroke="rgba(255,255,255,0.6)"
                      tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      stroke="rgba(255,255,255,0.6)"
                      tick={{ fill: 'rgba(255,255,255,0.8)', fontSize: 13 }}
                      width={140}
                    />
                    <Tooltip
                      formatter={(value: number) => [formatCurrency(value), 'Amount']}
                      contentStyle={chartTooltipStyle.contentStyle}
                      labelStyle={{ color: '#800020', fontWeight: 700 }}
                      itemStyle={{ fontWeight: 600 }}
                    />
                    <Bar dataKey="amount" radius={[0, 6, 6, 0]}>
                      {categoryBarData.map((entry, index) => (
                        <Cell key={`cat-bar-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Spending Over Time Area Chart */}
          {spendingOverTime.length > 1 && (
            <div className="card-3d chart-card-3d">
              <h3>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 8 }}>
                  <path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/>
                </svg>
                Spending Over Time
              </h3>
              <p className="chart-description-3d">
                Weekly income vs expenses over the last 3 months
              </p>
              <div className="chart-container-3d">
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={spendingOverTime} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
                    <defs>
                      <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#800020" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#800020" stopOpacity={0.05}/>
                      </linearGradient>
                      <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#1a472a" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#1a472a" stopOpacity={0.05}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis
                      dataKey="week"
                      stroke="rgba(255,255,255,0.6)"
                      tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.6)"
                      tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                    />
                    <Tooltip
                      formatter={(value: number, name: string) => [formatCurrency(value), name]}
                      contentStyle={chartTooltipStyle.contentStyle}
                      labelStyle={{ color: '#800020', fontWeight: 700 }}
                      itemStyle={{ fontWeight: 600 }}
                    />
                    <Legend
                      wrapperStyle={{ paddingTop: '10px' }}
                      formatter={(value) => <span style={{ color: 'rgba(255,255,255,0.8)' }}>{value}</span>}
                    />
                    <Area
                      type="monotone"
                      dataKey="income"
                      stroke="#1a472a"
                      strokeWidth={2}
                      fill="url(#incomeGradient)"
                      name="Income"
                    />
                    <Area
                      type="monotone"
                      dataKey="expenses"
                      stroke="#800020"
                      strokeWidth={2}
                      fill="url(#expenseGradient)"
                      name="Expenses"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Charts */}
        <div className="dashboard-sidebar-3d">
          {/* Account Distribution */}
          {pieData.length > 0 && (
            <div className="card-3d chart-card-3d">
              <h3>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 8 }}>
                  <path d="M11 2v20c-5.07-.5-9-4.79-9-10s3.93-9.5 9-10zm2.03 0v8.99H22c-.47-4.74-4.24-8.52-8.97-8.99zm0 11.01V22c4.74-.47 8.5-4.25 8.97-8.99h-8.97z"/>
                </svg>
                Account Distribution
              </h3>
              <div className="chart-container-3d">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <defs>
                      {CHART_COLORS.map((color, index) => (
                        <linearGradient key={`gradient-${index}`} id={`pieGradient-${index}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={color} stopOpacity={1}/>
                          <stop offset="100%" stopColor={color} stopOpacity={0.7}/>
                        </linearGradient>
                      ))}
                      <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="2" dy="4" stdDeviation="3" floodOpacity="0.3"/>
                      </filter>
                    </defs>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="value"
                      filter="url(#shadow)"
                    >
                      {pieData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={`url(#pieGradient-${index % CHART_COLORS.length})`}
                          stroke={CHART_COLORS[index % CHART_COLORS.length]}
                          strokeWidth={2}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      {...chartTooltipStyle}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="chart-legend-3d">
                  {pieData.map((entry, index) => (
                    <div key={entry.name} className="legend-item-3d">
                      <span className="legend-color-3d" style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}></span>
                      <span className="legend-label-3d">{entry.name}</span>
                      <span className="legend-value-3d">
                        {formatCurrency(entry.value)} ({totalNetWorth > 0 ? ((entry.value / Math.abs(totalNetWorth)) * 100).toFixed(1) : 0}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Spending by Category Pie */}
          {spendingPieData.length > 0 && (
            <div className="card-3d chart-card-3d">
              <h3>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 8 }}>
                  <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
                </svg>
                Recent Spending
              </h3>
              <p className="chart-description-3d">Breakdown by category from {transactions.filter(t => t.amount > 0).length} expenses</p>
              <div className="chart-container-3d">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <defs>
                      {spendingPieData.map((entry, index) => (
                        <linearGradient key={`spendGradient-${index}`} id={`spendGradient-${index}`} x1="0" y1="0" x2="1" y2="1">
                          <stop offset="0%" stopColor={entry.color || CHART_COLORS[index % CHART_COLORS.length]} stopOpacity={1}/>
                          <stop offset="100%" stopColor={entry.color || CHART_COLORS[index % CHART_COLORS.length]} stopOpacity={0.6}/>
                        </linearGradient>
                      ))}
                    </defs>
                    <Pie
                      data={spendingPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="value"
                      filter="url(#shadow)"
                    >
                      {spendingPieData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={`url(#spendGradient-${index})`}
                          stroke={entry.color || CHART_COLORS[index % CHART_COLORS.length]}
                          strokeWidth={2}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      {...chartTooltipStyle}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="chart-legend-3d">
                  {spendingPieData.map((entry, index) => (
                    <div key={entry.name} className="legend-item-3d">
                      <span className="legend-color-3d" style={{ backgroundColor: entry.color || CHART_COLORS[index % CHART_COLORS.length] }}></span>
                      <span className="legend-label-3d">{entry.icon ? `${entry.icon} ` : ''}{entry.name}</span>
                      <span className="legend-value-3d">{formatCurrency(entry.value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Monthly Spending Trend */}
          {monthlySpendingTrend.some(m => m.income > 0 || m.expenses > 0) && (
            <div className="card-3d chart-card-3d">
              <h3>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 8 }}>
                  <path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/>
                </svg>
                Monthly Trend
              </h3>
              <div className="chart-container-3d">
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={monthlySpendingTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis
                      dataKey="month"
                      stroke="rgba(255,255,255,0.6)"
                      tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.6)"
                      tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      contentStyle={chartTooltipStyle.contentStyle}
                      labelStyle={{ color: '#800020', fontWeight: 700 }}
                      itemStyle={{ fontWeight: 600 }}
                    />
                    <Legend
                      wrapperStyle={{ paddingTop: '10px' }}
                      formatter={(value) => <span style={{ color: 'rgba(255,255,255,0.8)' }}>{value}</span>}
                    />
                    <Line
                      type="monotone"
                      dataKey="income"
                      stroke="#1a472a"
                      strokeWidth={3}
                      dot={{ fill: '#1a472a', strokeWidth: 2 }}
                      name="Income"
                    />
                    <Line
                      type="monotone"
                      dataKey="expenses"
                      stroke="#800020"
                      strokeWidth={3}
                      dot={{ fill: '#800020', strokeWidth: 2 }}
                      name="Expenses"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Financial Insights */}
          {financialInsights.length > 0 && (
            <div className="card-3d insights-card-3d">
              <h3>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 8 }}>
                  <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6A4.997 4.997 0 0 1 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z"/>
                </svg>
                Financial Insights
              </h3>
              <div className="insights-list-3d">
                {financialInsights.map((insight, index) => (
                  <div key={index} className={`insight-item-3d insight-${insight.type}`}>
                    <div className={`insight-icon-3d insight-icon-${insight.type}`}>
                      {insight.icon}
                    </div>
                    <p className="insight-text-3d">{insight.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="card-3d">
            <h3>Quick Actions</h3>
            <div className="quick-actions-3d">
              <Link to="/accounts" className="quick-action-btn-3d">
                <span className="action-icon-3d">+</span>
                <span>Add Account</span>
              </Link>
              <button
                className="quick-action-btn-3d"
                onClick={handleSyncTransactions}
                disabled={syncing || accounts.length === 0}
              >
                <span className="action-icon-3d">{syncing ? '...' : 'Sync'}</span>
                <span>{syncing ? 'Syncing...' : 'Sync Transactions'}</span>
              </button>
              <Link to="/planning" className="quick-action-btn-3d">
                <span className="action-icon-3d">AI</span>
                <span>AI Insights</span>
              </Link>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};

export default Dashboard;
