import React, { useState, useEffect } from 'react';
import { useMsal } from '@azure/msal-react';
import api from '../../services/api';
import ConnectAccount from './ConnectAccount';
import { useToast } from '../common/Toast';
import { useFamilyMember } from '../../context/FamilyMemberContext';
import './Accounts.css';

interface Account {
  account_id: string;
  name: string;
  type: string;
  mask?: string;
  currency: string;
  institution_name?: string;
  family_member_id?: number | null;
  family_member_name?: string | null;
  balances?: {
    current: number;
    available?: number;
    currency: string;
  };
  last_synced_at?: string;
}

const Accounts: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [deleteModal, setDeleteModal] = useState<{ show: boolean; account: Account | null; confirmText: string }>({
    show: false,
    account: null,
    confirmText: ''
  });
  const [deleting, setDeleting] = useState(false);

  const { accounts: msalAccounts } = useMsal();
  const user = msalAccounts[0];
  const toast = useToast();
  const { selectedMemberId, familyMembers } = useFamilyMember();

  useEffect(() => {
    fetchAccounts();
  }, [user, selectedMemberId]);

  const fetchAccounts = async () => {
    if (!user) return;

    try {
      setLoading(true);
      const familyMemberParam = selectedMemberId ? `&family_member_id=${selectedMemberId}` : '';
      const response = await api.get(`/accounts?user_id=${user.localAccountId}${familyMemberParam}`);
      setAccounts(response.data.accounts || []);
    } catch (err: any) {
      console.error('Error fetching accounts:', err);
      toast.error('Failed to Load Accounts', err.response?.data?.error || 'Please try again later');
    } finally {
      setLoading(false);
    }
  };

  const handleAccountConnected = (newAccounts: any[]) => {
    const formattedAccounts = newAccounts.map(acc => ({
      account_id: acc.account_id,
      name: acc.name,
      type: acc.type,
      mask: acc.mask,
      currency: acc.balances?.currency || 'USD',
      balances: acc.balances
    }));
    setAccounts((prev) => [...prev, ...formattedAccounts]);
    setShowConnectModal(false);
    toast.success('Accounts Connected', `Successfully linked ${newAccounts.length} account(s)`);
  };

  const handleDeleteAccount = async () => {
    if (!deleteModal.account || deleteModal.confirmText.toLowerCase() !== 'delete') return;

    try {
      setDeleting(true);
      await api.delete(`/accounts/${deleteModal.account.account_id}`);

      // Remove from local state
      setAccounts(prev => prev.filter(acc => acc.account_id !== deleteModal.account?.account_id));

      toast.success('Account Deleted', `${deleteModal.account.name} and all transactions have been permanently deleted`);
      setDeleteModal({ show: false, account: null, confirmText: '' });
    } catch (err: any) {
      console.error('Error deleting account:', err);
      toast.error('Delete Failed', err.response?.data?.error || 'Failed to delete account');
    } finally {
      setDeleting(false);
    }
  };

  const openDeleteModal = (account: Account) => {
    setDeleteModal({ show: true, account, confirmText: '' });
  };

  const closeDeleteModal = () => {
    setDeleteModal({ show: false, account: null, confirmText: '' });
  };

  const handleUpdateFamilyMember = async (accountId: string, newFamilyMemberId: number | null) => {
    try {
      await api.put(`/accounts/${accountId}/family-member`, {
        family_member_id: newFamilyMemberId
      });

      // Update local state
      setAccounts(prev => prev.map(acc => {
        if (acc.account_id === accountId) {
          const member = familyMembers.find(m => m.family_member_id === newFamilyMemberId);
          return {
            ...acc,
            family_member_id: newFamilyMemberId,
            family_member_name: member ? `${member.first_name} ${member.last_name}` : null
          };
        }
        return acc;
      }));

      toast.success('Account Updated', 'Family member assignment updated');
    } catch (err: any) {
      console.error('Error updating family member:', err);
      toast.error('Update Failed', err.response?.data?.error || 'Failed to update account');
    }
  };

  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2
    }).format(value);
  };

  // SVG Icons for better scalability and contrast
  const BankIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z"/>
    </svg>
  );

  const CreditCardIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M20 4H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/>
    </svg>
  );

  const InvestmentIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
    </svg>
  );

  const LoanIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
    </svg>
  );

  const RetirementIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
    </svg>
  );

  const WalletIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
    </svg>
  );

  const TotalBalanceIcon = () => (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
      <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
    </svg>
  );

  const TrashIcon = () => (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
    </svg>
  );

  const getAccountIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'depository':
      case 'checking':
      case 'savings':
        return <BankIcon />;
      case 'credit':
        return <CreditCardIcon />;
      case 'investment':
      case 'brokerage':
        return <InvestmentIcon />;
      case 'loan':
      case 'mortgage':
        return <LoanIcon />;
      case '401k':
      case 'ira':
      case 'roth':
        return <RetirementIcon />;
      default:
        return <WalletIcon />;
    }
  };

  const getAccentColor = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'depository':
      case 'checking':
      case 'savings':
        return 'maroon';
      case 'credit':
        return 'maroon';
      case 'investment':
      case 'brokerage':
      case '401k':
      case 'ira':
        return 'maroon';
      case 'loan':
      case 'mortgage':
        return 'maroon';
      default:
        return 'maroon';
    }
  };

  // Group accounts by type
  const groupedAccounts = accounts.reduce((acc, account) => {
    const type = account.type || 'other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(account);
    return acc;
  }, {} as Record<string, Account[]>);

  // Calculate totals
  const totalBalance = accounts.reduce((sum, acc) => sum + (acc.balances?.current || 0), 0);
  const totalByType = Object.entries(groupedAccounts).map(([type, accs]) => ({
    type,
    total: accs.reduce((sum, acc) => sum + (acc.balances?.current || 0), 0),
    count: accs.length
  }));

  if (loading) {
    return (
      <div className="accounts-page-3d">
        <div className="page-header-3d">
          <div>
            <div className="skeleton" style={{ width: 200, height: 32, marginBottom: 8 }}></div>
            <div className="skeleton" style={{ width: 300, height: 20 }}></div>
          </div>
        </div>
        <div className="accounts-summary-3d">
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton" style={{ height: 100, borderRadius: 16 }}></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="accounts-page-3d">
      {/* Page Header */}
      <div className="page-header-3d">
        <div>
          <h1>
            <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor" style={{ verticalAlign: 'middle', marginRight: 12 }}>
              <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z"/>
            </svg>
            Connected Accounts
          </h1>
          <p className="page-subtitle">Manage your financial accounts and sync transactions</p>
        </div>
        <div className="page-actions-3d">
          <button
            className="button-3d button-maroon"
            onClick={() => setShowConnectModal(true)}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
            </svg>
            Add Account
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="accounts-summary-3d">
        <div className="summary-card-3d maroon">
          <div className="card-3d-inner">
            <div className="card-icon-3d"><TotalBalanceIcon /></div>
            <div className="card-content-3d">
              <span className="card-label-3d">Total Balance</span>
              <span className="card-value-3d">{formatCurrency(totalBalance)}</span>
            </div>
          </div>
        </div>

        {totalByType.slice(0, 3).map(({ type, total, count }) => (
          <div key={type} className={`summary-card-3d ${getAccentColor(type)}`}>
            <div className="card-3d-inner">
              <div className="card-icon-3d">{getAccountIcon(type)}</div>
              <div className="card-content-3d">
                <span className="card-label-3d">{type} ({count})</span>
                <span className="card-value-3d" style={{ fontSize: 20 }}>{formatCurrency(total)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Accounts List */}
      {accounts.length === 0 ? (
        <div className="empty-state-card-3d">
          <div className="empty-icon-3d">
            <svg viewBox="0 0 24 24" width="64" height="64" fill="currentColor" style={{ color: '#800020' }}>
              <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z"/>
            </svg>
          </div>
          <h3>No Accounts Connected</h3>
          <p>Connect your bank, credit card, or investment accounts to get started.</p>
          <button
            className="button-3d button-maroon"
            onClick={() => setShowConnectModal(true)}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
            </svg>
            Connect Your First Account
          </button>
        </div>
      ) : (
        <div className="accounts-list-container-3d">
          {Object.entries(groupedAccounts).map(([type, typeAccounts]) => (
            <div key={type} className="account-group-3d">
              <h3 className="group-title-3d">
                <span>{getAccountIcon(type)}</span>
                <span style={{ textTransform: 'capitalize' }}>{type}</span>
                <span className="group-count-3d">{typeAccounts.length}</span>
              </h3>
              <div className="accounts-grid-3d">
                {typeAccounts.map(account => (
                  <div key={account.account_id} className="account-card-3d account-card-horizontal">
                    <div className={`account-card-accent-3d ${getAccentColor(account.type)}`}></div>
                    <div className="account-card-content-3d">
                      {/* Left side: Account info */}
                      <div className="account-card-left">
                        <div className="account-card-header-3d">
                          <span className="account-card-icon-3d">{getAccountIcon(account.type)}</span>
                          <div className="account-card-info-3d">
                            <h4>{account.name}</h4>
                            <span className="account-card-meta-3d">
                              {account.institution_name || account.type}
                              {account.mask && ` • ••${account.mask}`}
                            </span>
                          </div>
                        </div>
                        {/* Family Member Assignment */}
                        <div className="account-card-owner-3d">
                          <label className="owner-label-3d">Owner:</label>
                          <select
                            className="owner-select-3d"
                            value={account.family_member_id ?? ''}
                            onChange={(e) => handleUpdateFamilyMember(
                              account.account_id,
                              e.target.value ? parseInt(e.target.value) : null
                            )}
                          >
                            <option value="">Shared</option>
                            {familyMembers.map(member => (
                              <option key={member.family_member_id} value={member.family_member_id}>
                                {member.first_name} {member.last_name}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                      {/* Right side: Balance and Delete */}
                      <div className="account-card-right-3d">
                        <div className="account-card-balance-3d">
                          <span className="balance-label-3d">Current Balance</span>
                          <span className="balance-value-3d">
                            {account.balances?.current !== undefined
                              ? formatCurrency(account.balances.current, account.currency)
                              : '—'}
                          </span>
                          {account.balances?.available !== undefined &&
                           account.balances.available !== account.balances.current && (
                            <span className="balance-available-3d">
                              {formatCurrency(account.balances.available, account.currency)} available
                            </span>
                          )}
                        </div>
                        <button
                          className="delete-account-btn-3d"
                          onClick={() => openDeleteModal(account)}
                          title="Delete account"
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Connect Account Modal */}
      {showConnectModal && (
        <div className="modal-overlay-3d" onClick={() => setShowConnectModal(false)}>
          <div className="modal-content-3d" onClick={e => e.stopPropagation()}>
            <div className="modal-header-3d">
              <h2>Connect a New Account</h2>
              <button className="modal-close-3d" onClick={() => setShowConnectModal(false)}>×</button>
            </div>
            <div style={{ padding: '24px' }}>
              <ConnectAccount
                onSuccess={handleAccountConnected}
                onExit={() => setShowConnectModal(false)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Delete Account Confirmation Modal */}
      {deleteModal.show && deleteModal.account && (
        <div className="modal-overlay-3d" onClick={closeDeleteModal}>
          <div className="modal-content-3d delete-modal-3d" onClick={e => e.stopPropagation()}>
            <div className="modal-header-3d delete-header-3d">
              <h2>Delete Account</h2>
              <button className="modal-close-3d" onClick={closeDeleteModal}>×</button>
            </div>
            <div className="delete-modal-body-3d">
              <div className="delete-warning-icon-3d">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                </svg>
              </div>
              <h3>Are you sure?</h3>
              <p className="delete-account-name-3d">
                <strong>{deleteModal.account.name}</strong>
                {deleteModal.account.institution_name && (
                  <span> ({deleteModal.account.institution_name})</span>
                )}
              </p>
              <p className="delete-warning-text-3d">
                This will permanently delete this account and <strong>all associated transactions</strong>.
                This action cannot be undone.
              </p>
              <div className="delete-confirm-input-3d">
                <label>Type <strong>delete</strong> to confirm:</label>
                <input
                  type="text"
                  value={deleteModal.confirmText}
                  onChange={(e) => setDeleteModal(prev => ({ ...prev, confirmText: e.target.value }))}
                  placeholder="Type 'delete' here"
                  autoFocus
                />
              </div>
              <div className="delete-modal-actions-3d">
                <button
                  className="button-3d button-secondary-3d"
                  onClick={closeDeleteModal}
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  className="button-3d button-danger-3d"
                  onClick={handleDeleteAccount}
                  disabled={deleteModal.confirmText.toLowerCase() !== 'delete' || deleting}
                >
                  {deleting ? 'Deleting...' : 'Delete Account'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Accounts;
