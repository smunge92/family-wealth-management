import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { useMsal } from '@azure/msal-react';
import api from '../services/api';
import {
  Category,
  CategoryRule,
  CreateCategoryRequest,
  UpdateCategoryRequest,
  CreateCategoryRuleRequest,
  UpdateTransactionCategoryRequest,
  UpdateTransactionCategoryResponse
} from '../types/categories';

interface CategoriesContextType {
  categories: Category[];
  rules: CategoryRule[];
  loading: boolean;
  error: string | null;
  fetchCategories: () => Promise<void>;
  fetchRules: () => Promise<void>;
  createCategory: (name: string, icon?: string, color?: string) => Promise<Category | null>;
  updateCategory: (categoryId: number, updates: { name?: string; icon?: string; color?: string }) => Promise<Category | null>;
  deleteCategory: (categoryId: number) => Promise<boolean>;
  createRule: (categoryId: number, matchType: 'merchant_contains' | 'description_contains', matchValue: string, applyToExisting?: boolean) => Promise<{ rule: CategoryRule; transactionsUpdated: number } | null>;
  deleteRule: (ruleId: number) => Promise<boolean>;
  updateTransactionCategory: (transactionId: string, categoryId: number, createRule?: boolean, matchType?: 'merchant_contains' | 'description_contains') => Promise<UpdateTransactionCategoryResponse | null>;
  getSimilarCount: (matchType: string, matchValue: string) => Promise<number>;
  getCategoryById: (categoryId: number) => Category | undefined;
}

const CategoriesContext = createContext<CategoriesContextType | undefined>(undefined);

export const useCategories = () => {
  const context = useContext(CategoriesContext);
  if (!context) {
    throw new Error('useCategories must be used within a CategoriesProvider');
  }
  return context;
};

interface CategoriesProviderProps {
  children: ReactNode;
}

export const CategoriesProvider: React.FC<CategoriesProviderProps> = ({ children }) => {
  const { accounts } = useMsal();
  const user = accounts[0];

  const [categories, setCategories] = useState<Category[]>([]);
  const [rules, setRules] = useState<CategoryRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCategories = useCallback(async () => {
    if (!user?.localAccountId) return;

    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/categories?user_id=${user.localAccountId}`);
      setCategories(response.data.categories || []);
    } catch (err: any) {
      console.error('Error fetching categories:', err);
      setError(err.response?.data?.error || 'Failed to load categories');
    } finally {
      setLoading(false);
    }
  }, [user?.localAccountId]);

  const fetchRules = useCallback(async () => {
    if (!user?.localAccountId) return;

    try {
      const response = await api.get(`/category-rules?user_id=${user.localAccountId}`);
      setRules(response.data.rules || []);
    } catch (err: any) {
      console.error('Error fetching category rules:', err);
    }
  }, [user?.localAccountId]);

  const createCategory = useCallback(async (name: string, icon?: string, color?: string): Promise<Category | null> => {
    if (!user?.localAccountId) return null;

    try {
      const request: CreateCategoryRequest = {
        user_id: user.localAccountId,
        name,
        icon,
        color
      };
      const response = await api.post('/categories', request);
      const newCategory = response.data.category;
      setCategories(prev => [...prev, newCategory]);
      return newCategory;
    } catch (err: any) {
      console.error('Error creating category:', err);
      throw new Error(err.response?.data?.error || 'Failed to create category');
    }
  }, [user?.localAccountId]);

  const updateCategory = useCallback(async (categoryId: number, updates: { name?: string; icon?: string; color?: string }): Promise<Category | null> => {
    if (!user?.localAccountId) return null;

    try {
      const request: UpdateCategoryRequest = {
        user_id: user.localAccountId,
        ...updates
      };
      const response = await api.put(`/categories/${categoryId}`, request);
      const updatedCategory = response.data.category;
      setCategories(prev => prev.map(c => c.category_id === categoryId ? updatedCategory : c));
      return updatedCategory;
    } catch (err: any) {
      console.error('Error updating category:', err);
      throw new Error(err.response?.data?.error || 'Failed to update category');
    }
  }, [user?.localAccountId]);

  const deleteCategory = useCallback(async (categoryId: number): Promise<boolean> => {
    if (!user?.localAccountId) return false;

    try {
      await api.delete(`/categories/${categoryId}?user_id=${user.localAccountId}`);
      setCategories(prev => prev.filter(c => c.category_id !== categoryId));
      // Also remove any rules that referenced this category
      setRules(prev => prev.filter(r => r.category_id !== categoryId));
      return true;
    } catch (err: any) {
      console.error('Error deleting category:', err);
      throw new Error(err.response?.data?.error || 'Failed to delete category');
    }
  }, [user?.localAccountId]);

  const createRule = useCallback(async (
    categoryId: number,
    matchType: 'merchant_contains' | 'description_contains',
    matchValue: string,
    applyToExisting: boolean = true
  ): Promise<{ rule: CategoryRule; transactionsUpdated: number } | null> => {
    if (!user?.localAccountId) return null;

    try {
      const request: CreateCategoryRuleRequest = {
        user_id: user.localAccountId,
        category_id: categoryId,
        match_type: matchType,
        match_value: matchValue,
        apply_to_existing: applyToExisting
      };
      const response = await api.post('/category-rules', request);
      const newRule = response.data.rule;
      const transactionsUpdated = response.data.transactions_updated || 0;
      setRules(prev => [...prev, newRule]);
      return { rule: newRule, transactionsUpdated };
    } catch (err: any) {
      console.error('Error creating rule:', err);
      throw new Error(err.response?.data?.error || 'Failed to create rule');
    }
  }, [user?.localAccountId]);

  const deleteRule = useCallback(async (ruleId: number): Promise<boolean> => {
    if (!user?.localAccountId) return false;

    try {
      await api.delete(`/category-rules/${ruleId}?user_id=${user.localAccountId}`);
      setRules(prev => prev.filter(r => r.rule_id !== ruleId));
      return true;
    } catch (err: any) {
      console.error('Error deleting rule:', err);
      throw new Error(err.response?.data?.error || 'Failed to delete rule');
    }
  }, [user?.localAccountId]);

  const updateTransactionCategory = useCallback(async (
    transactionId: string,
    categoryId: number,
    createRule: boolean = false,
    matchType: 'merchant_contains' | 'description_contains' = 'merchant_contains'
  ): Promise<UpdateTransactionCategoryResponse | null> => {
    if (!user?.localAccountId) return null;

    try {
      const request: UpdateTransactionCategoryRequest = {
        user_id: user.localAccountId,
        category_id: categoryId,
        create_rule: createRule,
        rule_match_type: matchType
      };
      const response = await api.patch(`/transactions/${transactionId}/category`, request);

      // If a rule was created, refresh rules
      if (response.data.rule_created) {
        await fetchRules();
      }

      return response.data;
    } catch (err: any) {
      console.error('Error updating transaction category:', err);
      throw new Error(err.response?.data?.error || 'Failed to update transaction category');
    }
  }, [user?.localAccountId, fetchRules]);

  const getSimilarCount = useCallback(async (matchType: string, matchValue: string): Promise<number> => {
    if (!user?.localAccountId) return 0;

    try {
      const response = await api.get('/transactions/similar-count', {
        params: {
          user_id: user.localAccountId,
          match_type: matchType,
          match_value: matchValue
        }
      });
      return response.data.count || 0;
    } catch (err: any) {
      console.error('Error getting similar count:', err);
      return 0;
    }
  }, [user?.localAccountId]);

  const getCategoryById = useCallback((categoryId: number): Category | undefined => {
    return categories.find(c => c.category_id === categoryId);
  }, [categories]);

  // Fetch categories when user is available
  useEffect(() => {
    if (user?.localAccountId) {
      fetchCategories();
      fetchRules();
    }
  }, [user?.localAccountId, fetchCategories, fetchRules]);

  return (
    <CategoriesContext.Provider
      value={{
        categories,
        rules,
        loading,
        error,
        fetchCategories,
        fetchRules,
        createCategory,
        updateCategory,
        deleteCategory,
        createRule,
        deleteRule,
        updateTransactionCategory,
        getSimilarCount,
        getCategoryById
      }}
    >
      {children}
    </CategoriesContext.Provider>
  );
};
