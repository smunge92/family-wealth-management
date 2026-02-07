/**
 * Category types for transaction categorization system
 */

// Base category interface
export interface Category {
  category_id: number;
  name: string;
  icon: string | null;
  color: string | null;
  is_system: boolean;
  display_order: number;
  created_at?: string;
}

// Category rule interface
export interface CategoryRule {
  rule_id: number;
  category_id: number;
  category_name?: string;
  category_icon?: string;
  category_color?: string;
  match_type: 'merchant_contains' | 'description_contains';
  match_value: string;
  priority: number;
  created_at?: string;
}

// Request/Response types for API calls

export interface CreateCategoryRequest {
  user_id: string;
  name: string;
  icon?: string;
  color?: string;
}

export interface UpdateCategoryRequest {
  user_id: string;
  name?: string;
  icon?: string;
  color?: string;
}

export interface CreateCategoryRuleRequest {
  user_id: string;
  category_id: number;
  match_type: 'merchant_contains' | 'description_contains';
  match_value: string;
  apply_to_existing?: boolean;
}

export interface UpdateTransactionCategoryRequest {
  user_id: string;
  category_id: number;
  create_rule?: boolean;
  rule_match_type?: 'merchant_contains' | 'description_contains';
}

export interface UpdateTransactionCategoryResponse {
  success: boolean;
  rule_created: boolean;
  similar_updated: number;
}

export interface CategoriesResponse {
  categories: Category[];
}

export interface CategoryResponse {
  success: boolean;
  category: Category;
}

export interface CategoryRulesResponse {
  rules: CategoryRule[];
}

export interface CategoryRuleResponse {
  success: boolean;
  rule: CategoryRule;
  transactions_updated: number;
}

export interface SimilarCountResponse {
  count: number;
  match_type: string;
  match_value: string;
}

// Category source types
export type CategorySource = 'plaid' | 'rule' | 'manual';

// Extended transaction type with category fields
export interface TransactionWithCategory {
  transaction_id: string;
  account_id: string;
  account_name?: string;
  account_type?: string;
  family_member_name?: string;
  date: string;
  amount: number;
  description?: string;
  merchant_name?: string;
  category?: string; // Plaid category
  user_category_id?: number | null;
  user_category_name?: string | null;
  user_category_icon?: string | null;
  user_category_color?: string | null;
  category_source: CategorySource;
  pending: boolean;
  currency: string;
  data_source: string;
}
