import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useMsal } from '@azure/msal-react';
import api from '../../services/api';
import { useToast } from '../common/Toast';
import { useFamilyMember } from '../../context/FamilyMemberContext';
import { useCategories } from '../../context/CategoriesContext';
import CategorySelect from '../common/CategorySelect';
import CategoryManager from '../Categories/CategoryManager';
import { CategorySource } from '../../types/categories';
import './Transactions.css';

interface Transaction {
  transaction_id: string;
  account_id: string;
  account_name: string;
  account_type: string;
  date: string;
  amount: number;
  description: string;
  merchant_name: string | null;
  category: string | null;
  user_category_id: number | null;
  user_category_name: string | null;
  user_category_icon: string | null;
  user_category_color: string | null;
  category_source: CategorySource;
  pending: boolean;
  currency: string;
  data_source: string;
}

const Transactions: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [totals, setTotals] = useState<{ total_income: number; total_expenses: number; pending_count: number }>({
    total_income: 0,
    total_expenses: 0,
    pending_count: 0
  });
  const [currentPage, setCurrentPage] = useState(0);
  const [filter, setFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({
    start: '',
    end: ''
  });
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [showCategoryManager, setShowCategoryManager] = useState(false);
  const limit = 50;

  const { accounts } = useMsal();
  const user = accounts[0];
  const toast = useToast();
  const { selectedMemberId } = useFamilyMember();
  const { categories } = useCategories();

  const fetchTransactions = useCallback(async (offset: number = 0) => {
    if (!user) return;

    try {
      setLoading(true);
      const familyMemberParam = selectedMemberId ? `&family_member_id=${selectedMemberId}` : '';
      const response = await api.get(`/transactions?user_id=${user.localAccountId}&limit=${limit}&offset=${offset}${familyMemberParam}`);
      setTransactions(response.data.transactions || []);
      setTotalCount(response.data.total_count || 0);
      setTotals(response.data.totals || { total_income: 0, total_expenses: 0, pending_count: 0 });
    } catch (err: any) {
      console.error('Error fetching transactions:', err);
      toast.error('Failed to Load Transactions', err.response?.data?.error || 'Please try again later');
    } finally {
      setLoading(false);
    }
  }, [user, toast, selectedMemberId]);

  useEffect(() => {
    fetchTransactions(currentPage * limit);
  }, [fetchTransactions, currentPage, selectedMemberId]);

  const handleSyncTransactions = async () => {
    if (!user) return;

    try {
      setSyncing(true);

      const response = await api.post('/transactions/sync', {
        user_id: user.localAccountId
      });

      const { total_added, total_modified, total_removed } = response.data;
      toast.success('Sync Complete', `${total_added} added, ${total_modified} modified, ${total_removed} removed`);

      await fetchTransactions(0);
      setCurrentPage(0);
    } catch (err: any) {
      console.error('Error syncing transactions:', err);
      toast.error('Sync Failed', err.response?.data?.error || 'Failed to sync transactions');
    } finally {
      setSyncing(false);
    }
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2
    }).format(Math.abs(amount));
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatDateShort = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const getCategoryIcon = (category: string | null) => {
    const cat = category?.toLowerCase() || '';
    if (cat.includes('food') || cat.includes('restaurant')) return '🍽️';
    if (cat.includes('travel') || cat.includes('airline') || cat.includes('hotel')) return '✈️';
    if (cat.includes('shop') || cat.includes('store') || cat.includes('merchandise')) return '🛒';
    if (cat.includes('transfer') || cat.includes('payment')) return '💸';
    if (cat.includes('subscription') || cat.includes('service')) return '📱';
    if (cat.includes('health') || cat.includes('medical')) return '🏥';
    if (cat.includes('gas') || cat.includes('fuel') || cat.includes('automotive')) return '⛽';
    if (cat.includes('entertainment') || cat.includes('recreation')) return '🎬';
    if (cat.includes('groceries') || cat.includes('supermarket')) return '🛒';
    if (cat.includes('utilities') || cat.includes('phone') || cat.includes('internet')) return '💡';
    if (cat.includes('income') || cat.includes('payroll') || cat.includes('deposit')) return '💰';
    return '💳';
  };

  const handleCategoryChange = useCallback(() => {
    // Refresh transactions after category update
    fetchTransactions(currentPage * limit);
  }, [fetchTransactions, currentPage]);

  // Filter and search transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter(txn => {
      // Type filter
      if (filter === 'income' && txn.amount >= 0) return false;
      if (filter === 'expense' && txn.amount < 0) return false;
      if (filter === 'pending' && !txn.pending) return false;

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesDescription = txn.description?.toLowerCase().includes(query);
        const matchesMerchant = txn.merchant_name?.toLowerCase().includes(query);
        const matchesCategory = txn.category?.toLowerCase().includes(query);
        const matchesAccount = txn.account_name?.toLowerCase().includes(query);
        if (!matchesDescription && !matchesMerchant && !matchesCategory && !matchesAccount) {
          return false;
        }
      }

      // Category filter
      if (selectedCategoryId !== null) {
        if (txn.user_category_id !== selectedCategoryId) return false;
      }

      // Date range filter
      if (dateRange.start && new Date(txn.date) < new Date(dateRange.start)) return false;
      if (dateRange.end && new Date(txn.date) > new Date(dateRange.end)) return false;

      return true;
    });
  }, [transactions, filter, searchQuery, dateRange, selectedCategoryId]);

  // Calculate summary stats - use totals from API for accurate all-transactions stats
  const stats = useMemo(() => {
    return {
      income: totals.total_income,
      expenses: totals.total_expenses,
      pending: totals.pending_count,
      net: totals.total_income - totals.total_expenses
    };
  }, [totals]);

  // Group transactions by date
  const groupedTransactions = useMemo(() => {
    const groups: Record<string, Transaction[]> = {};
    filteredTransactions.forEach(txn => {
      const date = txn.date;
      if (!groups[date]) groups[date] = [];
      groups[date].push(txn);
    });
    return Object.entries(groups).sort((a, b) => new Date(b[0]).getTime() - new Date(a[0]).getTime());
  }, [filteredTransactions]);

  const totalPages = Math.ceil(totalCount / limit);

  // Filter tabs show counts from current page (what's visible)
  const filterTabs = [
    { id: 'all', label: 'All', count: transactions.length },
    { id: 'income', label: 'Income', count: transactions.filter(t => t.amount < 0).length },
    { id: 'expense', label: 'Expenses', count: transactions.filter(t => t.amount > 0).length },
    { id: 'pending', label: 'Pending', count: transactions.filter(t => t.pending).length }
  ];

  if (loading && transactions.length === 0) {
    return (
      <div className="transactions-page-3d">
        <div className="page-header-3d">
          <div>
            <div className="skeleton" style={{ width: 200, height: 32, marginBottom: 8 }}></div>
            <div className="skeleton" style={{ width: 300, height: 20 }}></div>
          </div>
        </div>
        <div className="transactions-summary-3d">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton" style={{ height: 100, borderRadius: 16 }}></div>
          ))}
        </div>
        <div className="transactions-list-card-3d">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="skeleton" style={{ height: 70, margin: 12 }}></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="transactions-page-3d">
      {/* Page Header */}
      <div className="page-header-3d">
        <div>
          <h1>
            <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 12 }}>
              <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
            </svg>
            Transactions
          </h1>
          <p className="page-subtitle">View and manage your financial transactions</p>
        </div>
        <div className="page-actions-3d">
          <button
            className="button-3d button-secondary-3d"
            onClick={() => setShowCategoryManager(true)}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M12 2l-5.5 9h11L12 2zm0 3.84L13.93 9h-3.87L12 5.84zM17.5 13c-2.49 0-4.5 2.01-4.5 4.5s2.01 4.5 4.5 4.5 4.5-2.01 4.5-4.5-2.01-4.5-4.5-4.5zm0 7c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5zM3 21.5h8v-8H3v8zm2-6h4v4H5v-4z"/>
            </svg>
            Categories
          </button>
          <button
            className="button-3d button-maroon"
            onClick={handleSyncTransactions}
            disabled={syncing}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" className={syncing ? 'spin' : ''}>
              <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
            </svg>
            {syncing ? 'Syncing...' : 'Sync Transactions'}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="transactions-summary-3d">
        <div className="summary-card-3d maroon">
          <div className="card-3d-inner">
            <div className="card-icon-3d">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
              </svg>
            </div>
            <div className="card-content-3d">
              <span className="card-label-3d">Income</span>
              <span className="card-value-3d">+{formatCurrency(stats.income)}</span>
            </div>
          </div>
        </div>

        <div className="summary-card-3d maroon">
          <div className="card-3d-inner">
            <div className="card-icon-3d">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
              </svg>
            </div>
            <div className="card-content-3d">
              <span className="card-label-3d">Expenses</span>
              <span className="card-value-3d">-{formatCurrency(stats.expenses)}</span>
            </div>
          </div>
        </div>

        <div className="summary-card-3d maroon">
          <div className="card-3d-inner">
            <div className="card-icon-3d">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
              </svg>
            </div>
            <div className="card-content-3d">
              <span className="card-label-3d">Net</span>
              <span className="card-value-3d">
                {stats.net >= 0 ? '+' : '-'}{formatCurrency(stats.net)}
              </span>
            </div>
          </div>
        </div>

        <div className="summary-card-3d maroon">
          <div className="card-3d-inner">
            <div className="card-icon-3d">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <path d="M17 3H7c-1.1 0-1.99.9-1.99 2L5 21l7-3 7 3V5c0-1.1-.9-2-2-2z"/>
              </svg>
            </div>
            <div className="card-content-3d">
              <span className="card-label-3d">Total</span>
              <span className="card-value-3d">{totalCount}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-card-3d">
        <div className="filters-row">
          {/* Filter Tabs */}
          <div className="filter-tabs-3d">
            {filterTabs.map(tab => (
              <button
                key={tab.id}
                className={`filter-tab-3d ${filter === tab.id ? 'active' : ''}`}
                onClick={() => setFilter(tab.id)}
              >
                {tab.label}
                <span className="tab-count-3d">{tab.count}</span>
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="search-box-3d">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" className="search-icon-3d">
              <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
            </svg>
            <input
              type="text"
              placeholder="Search transactions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input-3d"
            />
            {searchQuery && (
              <button className="search-clear-3d" onClick={() => setSearchQuery('')}>×</button>
            )}
          </div>
        </div>

        {/* Date Range and Category Filter */}
        <div className="date-filters-3d">
          <div className="date-input-group-3d">
            <label>From</label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
              className="date-input-3d"
            />
          </div>
          <div className="date-input-group-3d">
            <label>To</label>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
              className="date-input-3d"
            />
          </div>
          <div className="date-input-group-3d">
            <label>Category</label>
            <select
              value={selectedCategoryId ?? ''}
              onChange={(e) => setSelectedCategoryId(e.target.value ? parseInt(e.target.value, 10) : null)}
              className="date-input-3d"
            >
              <option value="">All Categories</option>
              {categories.map(cat => (
                <option key={cat.category_id} value={cat.category_id}>
                  {cat.icon ? `${cat.icon} ` : ''}{cat.name}
                </option>
              ))}
            </select>
          </div>
          {(dateRange.start || dateRange.end || selectedCategoryId !== null) && (
            <button
              className="button-3d button-secondary-3d"
              onClick={() => { setDateRange({ start: '', end: '' }); setSelectedCategoryId(null); }}
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Transactions List */}
      <div className="transactions-list-card-3d">
        {filteredTransactions.length === 0 ? (
          <div className="empty-state-3d">
            <div className="empty-icon-3d">📋</div>
            <h3>No Transactions Found</h3>
            <p>
              {transactions.length === 0
                ? 'Click "Sync Transactions" to fetch from your connected accounts.'
                : 'Try adjusting your filters or search query.'}
            </p>
          </div>
        ) : (
          <div className="transactions-grouped-3d">
            {groupedTransactions.map(([date, txns]) => (
              <div key={date} className="transaction-group-3d">
                <div className="transaction-date-header-3d">
                  <span className="date-label-3d">{formatDate(date)}</span>
                  <span className="date-count-3d">{txns.length} transaction{txns.length !== 1 ? 's' : ''}</span>
                </div>
                <div className="transaction-items-3d">
                  {txns.map((txn) => (
                    <div key={txn.transaction_id} className={`transaction-row-3d ${txn.pending ? 'pending' : ''}`}>
                      <div className="transaction-icon-wrapper-3d">
                        <span className="transaction-category-icon-3d">
                          {txn.user_category_icon || getCategoryIcon(txn.category)}
                        </span>
                      </div>
                      <div className="transaction-info-3d">
                        <div className="transaction-primary-3d">
                          <span className="transaction-merchant-3d">
                            {txn.merchant_name || txn.description}
                          </span>
                          {txn.pending && (
                            <span className="pending-badge-3d">Pending</span>
                          )}
                        </div>
                        <div className="transaction-secondary-3d">
                          <span className="transaction-account-3d">{txn.account_name}</span>
                        </div>
                      </div>
                      <div className="transaction-category-wrapper-3d">
                        <CategorySelect
                          transactionId={txn.transaction_id}
                          currentCategoryId={txn.user_category_id}
                          currentCategoryName={txn.user_category_name}
                          currentCategoryIcon={txn.user_category_icon}
                          currentCategoryColor={txn.user_category_color}
                          categorySource={txn.category_source || 'plaid'}
                          transactionDescription={txn.merchant_name || txn.description || ''}
                          onCategoryChange={handleCategoryChange}
                        />
                      </div>
                      <div className="transaction-amount-wrapper-3d">
                        <span className={`transaction-amount-3d ${txn.amount > 0 ? 'expense' : 'income'}`}>
                          {txn.amount > 0 ? '-' : '+'}{formatCurrency(txn.amount, txn.currency)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination-3d">
            <button
              className="pagination-btn-3d"
              onClick={() => setCurrentPage(0)}
              disabled={currentPage === 0 || loading}
            >
              ««
            </button>
            <button
              className="pagination-btn-3d"
              onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
              disabled={currentPage === 0 || loading}
            >
              Previous
            </button>
            <span className="pagination-info-3d">
              Page <strong>{currentPage + 1}</strong> of <strong>{totalPages}</strong>
            </span>
            <button
              className="pagination-btn-3d"
              onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1 || loading}
            >
              Next
            </button>
            <button
              className="pagination-btn-3d"
              onClick={() => setCurrentPage(totalPages - 1)}
              disabled={currentPage >= totalPages - 1 || loading}
            >
              »»
            </button>
          </div>
        )}
      </div>

      {/* Category Manager Modal */}
      <CategoryManager
        isOpen={showCategoryManager}
        onClose={() => setShowCategoryManager(false)}
      />
    </div>
  );
};

export default Transactions;
