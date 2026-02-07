import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { useMsal } from '@azure/msal-react';
import api from '../services/api';

export interface FamilyMember {
  family_member_id: number;
  first_name: string;
  last_name: string;
  email?: string;
  is_primary: boolean;
  created_at?: string;
}

interface FamilyMemberContextType {
  familyMembers: FamilyMember[];
  selectedMemberId: number | null;
  loading: boolean;
  error: string | null;
  setSelectedMemberId: (id: number | null) => void;
  addFamilyMember: (firstName: string, lastName: string, email?: string) => Promise<FamilyMember | null>;
  deleteFamilyMember: (id: number) => Promise<boolean>;
  refreshFamilyMembers: () => Promise<void>;
  getSelectedMemberName: () => string;
}

const FamilyMemberContext = createContext<FamilyMemberContextType | undefined>(undefined);

const STORAGE_KEY = 'fwm_selected_family_member';

export const useFamilyMember = () => {
  const context = useContext(FamilyMemberContext);
  if (!context) {
    throw new Error('useFamilyMember must be used within a FamilyMemberProvider');
  }
  return context;
};

interface FamilyMemberProviderProps {
  children: ReactNode;
}

export const FamilyMemberProvider: React.FC<FamilyMemberProviderProps> = ({ children }) => {
  const { accounts } = useMsal();
  const user = accounts[0];

  const [familyMembers, setFamilyMembers] = useState<FamilyMember[]>([]);
  const [selectedMemberId, setSelectedMemberIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? parseInt(stored, 10) : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setSelectedMemberId = useCallback((id: number | null) => {
    setSelectedMemberIdState(id);
    if (id === null) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, id.toString());
    }
  }, []);

  const fetchFamilyMembers = useCallback(async () => {
    if (!user?.localAccountId) return;

    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/family-members?user_id=${user.localAccountId}`);
      const members = response.data.family_members || [];
      setFamilyMembers(members);

      // If selected member no longer exists, reset to "All Family"
      if (selectedMemberId !== null) {
        const memberExists = members.some((m: FamilyMember) => m.family_member_id === selectedMemberId);
        if (!memberExists) {
          setSelectedMemberId(null);
        }
      }
    } catch (err: any) {
      console.error('Error fetching family members:', err);
      setError(err.response?.data?.error || 'Failed to load family members');
    } finally {
      setLoading(false);
    }
  }, [user?.localAccountId, selectedMemberId, setSelectedMemberId]);

  const addFamilyMember = useCallback(async (firstName: string, lastName: string, email?: string): Promise<FamilyMember | null> => {
    if (!user?.localAccountId) return null;

    try {
      const response = await api.post('/family-members', {
        user_id: user.localAccountId,
        first_name: firstName,
        last_name: lastName,
        email: email || undefined
      });

      const newMember = response.data.family_member;
      setFamilyMembers(prev => [...prev, newMember]);
      return newMember;
    } catch (err: any) {
      console.error('Error adding family member:', err);
      throw new Error(err.response?.data?.error || 'Failed to add family member');
    }
  }, [user?.localAccountId]);

  const deleteFamilyMember = useCallback(async (id: number): Promise<boolean> => {
    try {
      await api.delete(`/family-members/${id}`);
      setFamilyMembers(prev => prev.filter(m => m.family_member_id !== id));

      // If deleted member was selected, reset to "All Family"
      if (selectedMemberId === id) {
        setSelectedMemberId(null);
      }
      return true;
    } catch (err: any) {
      console.error('Error deleting family member:', err);
      throw new Error(err.response?.data?.error || 'Failed to delete family member');
    }
  }, [selectedMemberId, setSelectedMemberId]);

  const refreshFamilyMembers = useCallback(async () => {
    await fetchFamilyMembers();
  }, [fetchFamilyMembers]);

  const getSelectedMemberName = useCallback((): string => {
    if (selectedMemberId === null) {
      return 'All Family';
    }
    const member = familyMembers.find(m => m.family_member_id === selectedMemberId);
    return member ? `${member.first_name} ${member.last_name}` : 'All Family';
  }, [selectedMemberId, familyMembers]);

  // Fetch family members when user is available
  useEffect(() => {
    if (user?.localAccountId) {
      fetchFamilyMembers();
    }
  }, [user?.localAccountId, fetchFamilyMembers]);

  return (
    <FamilyMemberContext.Provider
      value={{
        familyMembers,
        selectedMemberId,
        loading,
        error,
        setSelectedMemberId,
        addFamilyMember,
        deleteFamilyMember,
        refreshFamilyMembers,
        getSelectedMemberName
      }}
    >
      {children}
    </FamilyMemberContext.Provider>
  );
};
