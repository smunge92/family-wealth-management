import React, { useState, useRef, useEffect } from 'react';
import { useCategories } from '../../../context/CategoriesContext';
import { useToast } from '../Toast';
import { Category, CategorySource } from '../../../types/categories';
import './CategorySelect.css';

interface CategorySelectProps {
  transactionId: string;
  currentCategoryId: number | null;
  currentCategoryName: string | null;
  currentCategoryIcon: string | null;
  currentCategoryColor: string | null;
  categorySource: CategorySource;
  transactionDescription: string;
  onCategoryChange?: () => void;
}

const CategorySelect: React.FC<CategorySelectProps> = ({
  transactionId,
  currentCategoryId,
  currentCategoryName,
  currentCategoryIcon,
  currentCategoryColor,
  categorySource,
  transactionDescription,
  onCategoryChange
}) => {
  const {
    categories,
    updateTransactionCategory,
    getSimilarCount
  } = useCategories();
  const { addToast } = useToast();

  const [isOpen, setIsOpen] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [applyToSimilar, setApplyToSimilar] = useState(false);
  const [similarCount, setSimilarCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleCategoryClick = async (category: Category) => {
    // If clicking the same category, just close
    if (category.category_id === currentCategoryId) {
      setIsOpen(false);
      return;
    }

    // Check for similar transactions
    const count = await getSimilarCount('merchant_contains', transactionDescription);
    setSimilarCount(count);

    if (count > 1) {
      // Show modal to ask about creating rule
      setSelectedCategory(category);
      setApplyToSimilar(false);
      setShowModal(true);
      setIsOpen(false);
    } else {
      // Just update this transaction
      await handleUpdateCategory(category, false);
    }
  };

  const handleUpdateCategory = async (category: Category, createRule: boolean) => {
    setLoading(true);
    try {
      await updateTransactionCategory(
        transactionId,
        category.category_id,
        createRule,
        'merchant_contains'
      );
      setShowModal(false);
      setIsOpen(false);
      if (onCategoryChange) {
        onCategoryChange();
      }
    } catch (error) {
      addToast({ type: 'error', title: 'Failed to update category. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const handleModalConfirm = async () => {
    if (selectedCategory) {
      await handleUpdateCategory(selectedCategory, applyToSimilar);
    }
  };

  const handleModalCancel = () => {
    setShowModal(false);
    setSelectedCategory(null);
  };

  const getDisplayCategory = () => {
    if (currentCategoryId && currentCategoryName) {
      return {
        icon: currentCategoryIcon || '',
        name: currentCategoryName,
        color: currentCategoryColor
      };
    }
    return {
      icon: '',
      name: 'Uncategorized',
      color: '#9e9e9e'
    };
  };

  const displayCategory = getDisplayCategory();

  const getSourceBadge = () => {
    switch (categorySource) {
      case 'manual':
        return <span className="category-source-badge manual">Manual</span>;
      case 'rule':
        return <span className="category-source-badge auto">Auto</span>;
      default:
        return null;
    }
  };

  // Group categories by system vs user
  const systemCategories = categories.filter(c => c.is_system);
  const userCategories = categories.filter(c => !c.is_system);

  return (
    <div className="category-select" ref={dropdownRef}>
      <button
        className="category-select-button"
        onClick={() => setIsOpen(!isOpen)}
        style={{ borderColor: displayCategory.color || undefined }}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="category-icon">{displayCategory.icon}</span>
        <span className="category-name">{displayCategory.name}</span>
        <span className={`category-arrow ${isOpen ? 'open' : ''}`}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
            <path d="M7 10l5 5 5-5z"/>
          </svg>
        </span>
      </button>
      {getSourceBadge()}

      {isOpen && (
        <div className="category-dropdown" role="listbox">
          <div className="category-dropdown-header">Select Category</div>

          {systemCategories.map((category) => (
            <button
              key={category.category_id}
              className={`category-option ${currentCategoryId === category.category_id ? 'selected' : ''}`}
              onClick={() => handleCategoryClick(category)}
              role="option"
              aria-selected={currentCategoryId === category.category_id}
            >
              <span className="category-option-icon">{category.icon || ''}</span>
              <span className="category-option-name">{category.name}</span>
              {currentCategoryId === category.category_id && (
                <span className="category-check">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                  </svg>
                </span>
              )}
            </button>
          ))}

          {userCategories.length > 0 && (
            <>
              <div className="category-divider" />
              <div className="category-section-label">My Categories</div>
              {userCategories.map((category) => (
                <button
                  key={category.category_id}
                  className={`category-option ${currentCategoryId === category.category_id ? 'selected' : ''}`}
                  onClick={() => handleCategoryClick(category)}
                  role="option"
                  aria-selected={currentCategoryId === category.category_id}
                >
                  <span className="category-option-icon">{category.icon || ''}</span>
                  <span className="category-option-name">{category.name}</span>
                  {currentCategoryId === category.category_id && (
                    <span className="category-check">
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                      </svg>
                    </span>
                  )}
                </button>
              ))}
            </>
          )}
        </div>
      )}

      {/* Category Change Modal */}
      {showModal && selectedCategory && (
        <div className="category-modal-overlay" onClick={handleModalCancel}>
          <div className="category-modal" onClick={(e) => e.stopPropagation()}>
            <div className="category-modal-header">
              <h3>Change Category</h3>
              <button className="category-modal-close" onClick={handleModalCancel}>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>

            <div className="category-modal-body">
              <div className="category-modal-transaction">
                <span className="modal-label">Transaction:</span>
                <span className="modal-value">{transactionDescription}</span>
              </div>

              <div className="category-modal-new-category">
                <span className="modal-label">New Category:</span>
                <span className="modal-category-badge" style={{ backgroundColor: selectedCategory.color || '#9e9e9e' }}>
                  {selectedCategory.icon} {selectedCategory.name}
                </span>
              </div>

              <div className="category-modal-similar">
                <label className="category-checkbox-label">
                  <input
                    type="checkbox"
                    checked={applyToSimilar}
                    onChange={(e) => setApplyToSimilar(e.target.checked)}
                  />
                  <span className="checkbox-text">
                    Apply to all transactions from "{transactionDescription}"
                    <span className="similar-count">(found {similarCount} similar)</span>
                  </span>
                </label>
              </div>
            </div>

            <div className="category-modal-actions">
              <button
                className="category-modal-cancel"
                onClick={handleModalCancel}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                className="category-modal-save"
                onClick={handleModalConfirm}
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CategorySelect;
