import React, { useState } from 'react';
import { useCategories } from '../../context/CategoriesContext';
import { Category, CategoryRule } from '../../types/categories';
import './CategoryManager.css';

interface CategoryManagerProps {
  isOpen: boolean;
  onClose: () => void;
}

type Tab = 'categories' | 'rules';

// Common emoji options for category icons
const EMOJI_OPTIONS = [
  '', '', '', '', '', '', '', '',
  '', '', '', '', '', '', '', '',
  '', '', '', '', '', '', '', '',
  '', '', '', '', '', '', '', ''
];

// Color palette for categories
const COLOR_OPTIONS = [
  '#e74c3c', '#27ae60', '#3498db', '#f39c12', '#9b59b6',
  '#e91e63', '#00bcd4', '#ff5722', '#607d8b', '#795548',
  '#4caf50', '#9e9e9e', '#f44336', '#2196f3', '#ff9800',
  '#8bc34a', '#673ab7', '#00897b', '#1565c0', '#800020'
];

const CategoryManager: React.FC<CategoryManagerProps> = ({ isOpen, onClose }) => {
  const {
    categories,
    rules,
    createCategory,
    updateCategory,
    deleteCategory,
    deleteRule,
    loading
  } = useCategories();

  const [activeTab, setActiveTab] = useState<Tab>('categories');
  const [showAddCategory, setShowAddCategory] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [categoryName, setCategoryName] = useState('');
  const [categoryIcon, setCategoryIcon] = useState('');
  const [categoryColor, setCategoryColor] = useState('#800020');
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: 'category' | 'rule'; id: number; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const systemCategories = categories.filter(c => c.is_system);
  const userCategories = categories.filter(c => !c.is_system);

  const resetForm = () => {
    setCategoryName('');
    setCategoryIcon('');
    setCategoryColor('#800020');
    setShowAddCategory(false);
    setEditingCategory(null);
  };

  const handleAddCategory = async () => {
    if (!categoryName.trim()) return;

    setSaving(true);
    try {
      await createCategory(categoryName.trim(), categoryIcon || undefined, categoryColor);
      resetForm();
    } catch (error: any) {
      alert(error.message || 'Failed to create category');
    } finally {
      setSaving(false);
    }
  };

  const handleEditCategory = (category: Category) => {
    setEditingCategory(category);
    setCategoryName(category.name);
    setCategoryIcon(category.icon || '');
    setCategoryColor(category.color || '#800020');
    setShowAddCategory(true);
  };

  const handleUpdateCategory = async () => {
    if (!editingCategory || !categoryName.trim()) return;

    setSaving(true);
    try {
      await updateCategory(editingCategory.category_id, {
        name: categoryName.trim(),
        icon: categoryIcon || undefined,
        color: categoryColor
      });
      resetForm();
    } catch (error: any) {
      alert(error.message || 'Failed to update category');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm) return;

    setDeleting(true);
    try {
      if (deleteConfirm.type === 'category') {
        await deleteCategory(deleteConfirm.id);
      } else {
        await deleteRule(deleteConfirm.id);
      }
      setDeleteConfirm(null);
    } catch (error: any) {
      alert(error.message || 'Failed to delete');
    } finally {
      setDeleting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="category-manager-overlay" onClick={onClose}>
      <div className="category-manager" onClick={(e) => e.stopPropagation()}>
        <div className="category-manager-header">
          <h2>Manage Categories</h2>
          <button className="category-manager-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <div className="category-manager-tabs">
          <button
            className={`tab-button ${activeTab === 'categories' ? 'active' : ''}`}
            onClick={() => setActiveTab('categories')}
          >
            Categories ({categories.length})
          </button>
          <button
            className={`tab-button ${activeTab === 'rules' ? 'active' : ''}`}
            onClick={() => setActiveTab('rules')}
          >
            My Rules ({rules.length})
          </button>
        </div>

        <div className="category-manager-content">
          {activeTab === 'categories' && (
            <div className="categories-tab">
              {/* Add/Edit Category Form */}
              {showAddCategory && (
                <div className="category-form">
                  <h3>{editingCategory ? 'Edit Category' : 'Add New Category'}</h3>
                  <div className="form-group">
                    <label>Name</label>
                    <input
                      type="text"
                      value={categoryName}
                      onChange={(e) => setCategoryName(e.target.value)}
                      placeholder="Category name"
                      maxLength={100}
                    />
                  </div>
                  <div className="form-group">
                    <label>Icon</label>
                    <div className="emoji-picker">
                      {EMOJI_OPTIONS.map((emoji) => (
                        <button
                          key={emoji}
                          className={`emoji-option ${categoryIcon === emoji ? 'selected' : ''}`}
                          onClick={() => setCategoryIcon(emoji)}
                        >
                          {emoji}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Color</label>
                    <div className="color-picker">
                      {COLOR_OPTIONS.map((color) => (
                        <button
                          key={color}
                          className={`color-option ${categoryColor === color ? 'selected' : ''}`}
                          style={{ backgroundColor: color }}
                          onClick={() => setCategoryColor(color)}
                        />
                      ))}
                    </div>
                  </div>
                  <div className="form-preview">
                    <span className="preview-label">Preview:</span>
                    <span className="category-preview" style={{ backgroundColor: categoryColor }}>
                      {categoryIcon} {categoryName || 'Category Name'}
                    </span>
                  </div>
                  <div className="form-actions">
                    <button className="btn-cancel" onClick={resetForm}>Cancel</button>
                    <button
                      className="btn-save"
                      onClick={editingCategory ? handleUpdateCategory : handleAddCategory}
                      disabled={saving || !categoryName.trim()}
                    >
                      {saving ? 'Saving...' : (editingCategory ? 'Update' : 'Add Category')}
                    </button>
                  </div>
                </div>
              )}

              {!showAddCategory && (
                <button className="add-category-btn" onClick={() => setShowAddCategory(true)}>
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                  </svg>
                  Add Custom Category
                </button>
              )}

              {/* User Categories */}
              {userCategories.length > 0 && (
                <div className="category-section">
                  <h4>My Categories</h4>
                  <div className="category-list">
                    {userCategories.map((category) => (
                      <div key={category.category_id} className="category-item">
                        <span className="category-badge" style={{ backgroundColor: category.color || '#9e9e9e' }}>
                          {category.icon} {category.name}
                        </span>
                        <div className="category-actions">
                          <button
                            className="action-btn edit"
                            onClick={() => handleEditCategory(category)}
                            title="Edit"
                          >
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                            </svg>
                          </button>
                          <button
                            className="action-btn delete"
                            onClick={() => setDeleteConfirm({ type: 'category', id: category.category_id, name: category.name })}
                            title="Delete"
                          >
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                            </svg>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* System Categories */}
              <div className="category-section">
                <h4>System Categories</h4>
                <p className="section-note">These categories are built-in and cannot be modified.</p>
                <div className="category-list system-categories">
                  {systemCategories.map((category) => (
                    <div key={category.category_id} className="category-item system">
                      <span className="category-badge" style={{ backgroundColor: category.color || '#9e9e9e' }}>
                        {category.icon} {category.name}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'rules' && (
            <div className="rules-tab">
              {rules.length === 0 ? (
                <div className="empty-state">
                  <svg viewBox="0 0 24 24" width="48" height="48" fill="#ccc">
                    <path d="M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-4.86 8.86l-3 3.87L9 13.14 6 17h12l-3.86-5.14z"/>
                  </svg>
                  <h3>No Rules Yet</h3>
                  <p>
                    Rules are created automatically when you change a transaction's category
                    and choose to apply it to similar transactions.
                  </p>
                </div>
              ) : (
                <div className="rules-list">
                  {rules.map((rule) => (
                    <div key={rule.rule_id} className="rule-item">
                      <div className="rule-info">
                        <span className="rule-category" style={{ backgroundColor: rule.category_color || '#9e9e9e' }}>
                          {rule.category_icon} {rule.category_name}
                        </span>
                        <div className="rule-details">
                          <span className="rule-match-type">
                            {rule.match_type === 'merchant_contains' ? 'Merchant contains:' : 'Description contains:'}
                          </span>
                          <span className="rule-match-value">"{rule.match_value}"</span>
                        </div>
                      </div>
                      <button
                        className="action-btn delete"
                        onClick={() => setDeleteConfirm({ type: 'rule', id: rule.rule_id, name: rule.match_value })}
                        title="Delete Rule"
                      >
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                          <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Delete Confirmation Modal */}
        {deleteConfirm && (
          <div className="delete-overlay" onClick={() => setDeleteConfirm(null)}>
            <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
              <div className="delete-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="#d32f2f">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                </svg>
              </div>
              <h3>Delete {deleteConfirm.type === 'category' ? 'Category' : 'Rule'}?</h3>
              <p>
                Are you sure you want to delete "{deleteConfirm.name}"?
                {deleteConfirm.type === 'category' && (
                  <span className="delete-warning">
                    Transactions using this category will be uncategorized.
                  </span>
                )}
              </p>
              <div className="delete-actions">
                <button className="btn-cancel" onClick={() => setDeleteConfirm(null)} disabled={deleting}>
                  Cancel
                </button>
                <button className="btn-delete" onClick={handleDeleteConfirm} disabled={deleting}>
                  {deleting ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CategoryManager;
