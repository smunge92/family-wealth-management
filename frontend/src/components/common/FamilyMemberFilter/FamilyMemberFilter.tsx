import React, { useState, useRef, useEffect } from 'react';
import { useFamilyMember, FamilyMember } from '../../../context/FamilyMemberContext';
import './FamilyMemberFilter.css';

const FamilyMemberFilter: React.FC = () => {
  const {
    familyMembers,
    selectedMemberId,
    setSelectedMemberId,
    getSelectedMemberName,
    deleteFamilyMember,
    loading
  } = useFamilyMember();

  const [isOpen, setIsOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<FamilyMember | null>(null);
  const [deleting, setDeleting] = useState(false);
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

  const handleSelect = (memberId: number | null) => {
    setSelectedMemberId(memberId);
    setIsOpen(false);
  };

  const handleDeleteClick = (e: React.MouseEvent, member: FamilyMember) => {
    e.stopPropagation();
    setDeleteConfirm(member);
  };

  const handleConfirmDelete = async () => {
    if (!deleteConfirm) return;

    setDeleting(true);
    try {
      await deleteFamilyMember(deleteConfirm.family_member_id);
      setDeleteConfirm(null);
      setIsOpen(false);
    } catch (error) {
      console.error('Error deleting family member:', error);
      alert('Failed to delete family member. Please try again.');
    } finally {
      setDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setDeleteConfirm(null);
  };

  if (loading) {
    return (
      <div className="family-member-filter">
        <span className="filter-loading">Loading...</span>
      </div>
    );
  }

  return (
    <div className="family-member-filter" ref={dropdownRef}>
      <button
        className="filter-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="filter-icon">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
          </svg>
        </span>
        <span className="filter-text">{getSelectedMemberName()}</span>
        <span className={`filter-arrow ${isOpen ? 'open' : ''}`}>
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M7 10l5 5 5-5z"/>
          </svg>
        </span>
      </button>

      {isOpen && (
        <div className="filter-dropdown" role="listbox">
          <button
            className={`filter-option ${selectedMemberId === null ? 'selected' : ''}`}
            onClick={() => handleSelect(null)}
            role="option"
            aria-selected={selectedMemberId === null}
          >
            <span className="option-icon">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
              </svg>
            </span>
            <span className="option-text">All Family</span>
            {selectedMemberId === null && (
              <span className="option-check">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
              </span>
            )}
          </button>

          {familyMembers.length > 0 && <div className="filter-divider" />}

          {familyMembers.map((member) => (
            <div
              key={member.family_member_id}
              className={`filter-option-row ${selectedMemberId === member.family_member_id ? 'selected' : ''}`}
            >
              <button
                className={`filter-option ${selectedMemberId === member.family_member_id ? 'selected' : ''}`}
                onClick={() => handleSelect(member.family_member_id)}
                role="option"
                aria-selected={selectedMemberId === member.family_member_id}
              >
                <span className="option-icon">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                  </svg>
                </span>
                <span className="option-text">{member.first_name} {member.last_name}</span>
                {selectedMemberId === member.family_member_id && (
                  <span className="option-check">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                    </svg>
                  </span>
                )}
              </button>
              <button
                className="delete-member-btn"
                onClick={(e) => handleDeleteClick(e, member)}
                title={`Delete ${member.first_name} ${member.last_name}`}
                aria-label={`Delete ${member.first_name} ${member.last_name}`}
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="delete-confirm-overlay" onClick={handleCancelDelete}>
          <div className="delete-confirm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="delete-confirm-icon">
              <svg viewBox="0 0 24 24" width="48" height="48" fill="#d32f2f">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
              </svg>
            </div>
            <h3 className="delete-confirm-title">Delete Family Member?</h3>
            <p className="delete-confirm-message">
              Are you sure you want to delete <strong>{deleteConfirm.first_name} {deleteConfirm.last_name}</strong>?
            </p>
            <p className="delete-confirm-warning">
              This will permanently delete all their accounts, transactions, and balances. This action cannot be undone.
            </p>
            <div className="delete-confirm-actions">
              <button
                className="delete-confirm-cancel"
                onClick={handleCancelDelete}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="delete-confirm-delete"
                onClick={handleConfirmDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FamilyMemberFilter;
