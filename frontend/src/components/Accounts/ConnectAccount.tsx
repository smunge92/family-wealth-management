import React, { useCallback, useEffect, useState } from 'react';
import { usePlaidLink, PlaidLinkOptions } from 'react-plaid-link';
import { useMsal } from '@azure/msal-react';
import api from '../../services/api';
import { useFamilyMember, FamilyMember } from '../../context/FamilyMemberContext';

interface ConnectAccountProps {
  onSuccess?: (accounts: any[]) => void;
  onExit?: () => void;
}

const ConnectAccount: React.FC<ConnectAccountProps> = ({ onSuccess, onExit }) => {
  const { accounts } = useMsal();
  const user = accounts[0];
  const { familyMembers, addFamilyMember, refreshFamilyMembers, selectedMemberId } = useFamilyMember();

  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Initialize with currently selected family member from header filter
  const [selectedFamilyMemberId, setSelectedFamilyMemberId] = useState<number | null>(selectedMemberId);
  const [showAddMember, setShowAddMember] = useState(false);
  const [newMemberFirstName, setNewMemberFirstName] = useState('');
  const [newMemberLastName, setNewMemberLastName] = useState('');
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [addingMember, setAddingMember] = useState(false);

  // Fetch link token on component mount
  useEffect(() => {
    const fetchLinkToken = async () => {
      if (!user) return;

      setLoading(true);
      setError(null);

      try {
        const response = await api.post('/plaid/link-token', {
          user_id: user.localAccountId,
          user_email: user.username,
        });

        setLinkToken(response.data.link_token);
      } catch (err: any) {
        console.error('Error fetching link token:', err);
        setError(err.response?.data?.error || 'Failed to initialize bank connection');
      } finally {
        setLoading(false);
      }
    };

    fetchLinkToken();
  }, [user]);

  // Handle adding a new family member
  const handleAddFamilyMember = async () => {
    if (!newMemberFirstName.trim() || !newMemberLastName.trim()) {
      setError('Please enter both first and last name');
      return;
    }

    setAddingMember(true);
    setError(null);

    try {
      const newMember = await addFamilyMember(
        newMemberFirstName.trim(),
        newMemberLastName.trim(),
        newMemberEmail.trim() || undefined
      );
      if (newMember) {
        setSelectedFamilyMemberId(newMember.family_member_id);
        setShowAddMember(false);
        setNewMemberFirstName('');
        setNewMemberLastName('');
        setNewMemberEmail('');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to add family member');
    } finally {
      setAddingMember(false);
    }
  };

  // Handle successful account connection
  const handleOnSuccess = useCallback(
    async (publicToken: string, metadata: any) => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.post('/plaid/exchange-token', {
          public_token: publicToken,
          user_id: user?.localAccountId,
          user_email: user?.username,
          user_name: user?.name || '',
          family_member_id: selectedFamilyMemberId,
        });

        if (onSuccess) {
          onSuccess(response.data.accounts);
        }
      } catch (err: any) {
        console.error('Error exchanging token:', err);
        setError(err.response?.data?.error || 'Failed to connect account');
      } finally {
        setLoading(false);
      }
    },
    [user, onSuccess, selectedFamilyMemberId]
  );

  // Handle Plaid Link exit
  const handleOnExit = useCallback(
    (err: any, metadata: any) => {
      if (err) {
        console.error('Plaid Link error:', err);
        setError(err.display_message || 'Connection cancelled');
      }
      if (onExit) {
        onExit();
      }
    },
    [onExit]
  );

  // Plaid Link configuration
  const config: PlaidLinkOptions = {
    token: linkToken,
    onSuccess: handleOnSuccess,
    onExit: handleOnExit,
  };

  const { open, ready } = usePlaidLink(config);

  return (
    <div className="connect-account">
      <h3>Connect a Bank Account</h3>
      <p>
        Securely connect your bank, investment, or credit card accounts to automatically
        track your transactions and balances.
      </p>

      {/* Family Member Selection */}
      <div style={{ marginTop: '1.5rem', marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, color: '#333' }}>
          Account Owner
        </label>
        <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.75rem' }}>
          Select which family member this account belongs to
        </p>

        {!showAddMember ? (
          <>
            <select
              value={selectedFamilyMemberId ?? ''}
              onChange={(e) => setSelectedFamilyMemberId(e.target.value ? parseInt(e.target.value) : null)}
              style={{
                width: '100%',
                padding: '0.75rem',
                fontSize: '1rem',
                borderRadius: '8px',
                border: '1px solid #ddd',
                backgroundColor: 'white',
                marginBottom: '0.75rem'
              }}
            >
              <option value="">No specific owner (shared account)</option>
              {familyMembers.map((member) => (
                <option key={member.family_member_id} value={member.family_member_id}>
                  {member.first_name} {member.last_name}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={() => setShowAddMember(true)}
              style={{
                background: 'none',
                border: 'none',
                color: '#800020',
                cursor: 'pointer',
                padding: 0,
                fontSize: '0.9rem',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem'
              }}
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
              </svg>
              Add New Family Member
            </button>
          </>
        ) : (
          <div style={{
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #e9ecef'
          }}>
            <div style={{ marginBottom: '0.75rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.25rem', color: '#555' }}>
                First Name
              </label>
              <input
                type="text"
                value={newMemberFirstName}
                onChange={(e) => setNewMemberFirstName(e.target.value)}
                placeholder="e.g., John"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  border: '1px solid #ddd',
                  fontSize: '0.9rem'
                }}
              />
            </div>
            <div style={{ marginBottom: '0.75rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.25rem', color: '#555' }}>
                Last Name
              </label>
              <input
                type="text"
                value={newMemberLastName}
                onChange={(e) => setNewMemberLastName(e.target.value)}
                placeholder="e.g., Doe"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  border: '1px solid #ddd',
                  fontSize: '0.9rem'
                }}
              />
            </div>
            <div style={{ marginBottom: '0.75rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.25rem', color: '#555' }}>
                Email (optional)
              </label>
              <input
                type="email"
                value={newMemberEmail}
                onChange={(e) => setNewMemberEmail(e.target.value)}
                placeholder="e.g., john.doe@email.com"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  border: '1px solid #ddd',
                  fontSize: '0.9rem'
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={handleAddFamilyMember}
                disabled={addingMember}
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  backgroundColor: '#800020',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: addingMember ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: 500,
                  opacity: addingMember ? 0.7 : 1
                }}
              >
                {addingMember ? 'Adding...' : 'Add Member'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAddMember(false);
                  setNewMemberFirstName('');
                  setNewMemberLastName('');
                  setNewMemberEmail('');
                  setError(null);
                }}
                disabled={addingMember}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#e9ecef',
                  color: '#555',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.9rem'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message" style={{ color: 'red', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      <button
        className="button button-primary"
        onClick={() => open()}
        disabled={!ready || loading || showAddMember}
        style={{ marginTop: '1rem', width: '100%' }}
      >
        {loading ? 'Loading...' : 'Connect Account'}
      </button>

      <div style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#666' }}>
        <p>Supported institutions include:</p>
        <ul>
          <li>Chase, Bank of America, Wells Fargo</li>
          <li>Vanguard, Fidelity, Charles Schwab</li>
          <li>Scotia Bank, TD Bank, RBC (Canada)</li>
          <li>And 12,000+ more financial institutions</li>
        </ul>
      </div>
    </div>
  );
};

export default ConnectAccount;
