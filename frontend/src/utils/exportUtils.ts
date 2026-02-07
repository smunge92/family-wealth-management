/**
 * Export utilities for CSV and XLSX downloads
 */
import * as XLSX from 'xlsx';

interface Column {
  key: string;
  header: string;
  formatter?: (value: any) => string;
}

interface SheetData {
  name: string;
  data: any[];
  columns: Column[];
}

/**
 * Format a value for CSV/Excel export
 */
const formatValue = (value: any, formatter?: (value: any) => string): string => {
  if (formatter) {
    return formatter(value);
  }
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'number') {
    return value.toString();
  }
  return String(value);
};

/**
 * Export data to CSV and trigger download
 */
export const exportToCSV = (
  data: any[],
  columns: Column[],
  filename: string
): void => {
  if (!data || data.length === 0) {
    console.warn('No data to export');
    return;
  }

  // Build header row
  const headerRow = columns.map(col => `"${col.header}"`).join(',');

  // Build data rows
  const dataRows = data.map(row =>
    columns.map(col => {
      const value = formatValue(row[col.key], col.formatter);
      // Escape quotes and wrap in quotes for CSV safety
      return `"${String(value).replace(/"/g, '""')}"`;
    }).join(',')
  );

  // Combine header and data
  const csvContent = [headerRow, ...dataRows].join('\n');

  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  downloadBlob(blob, `${filename}.csv`);
};

/**
 * Export multiple sheets to XLSX and trigger download
 */
export const exportToXLSX = (
  sheets: SheetData[],
  filename: string
): void => {
  if (!sheets || sheets.length === 0) {
    console.warn('No data to export');
    return;
  }

  // Create workbook
  const workbook = XLSX.utils.book_new();

  sheets.forEach(sheet => {
    if (!sheet.data || sheet.data.length === 0) {
      return;
    }

    // Build header row
    const headers = sheet.columns.map(col => col.header);

    // Build data rows
    const rows = sheet.data.map(row =>
      sheet.columns.map(col => {
        const value = row[col.key];
        if (col.formatter) {
          return col.formatter(value);
        }
        return value;
      })
    );

    // Create worksheet with header + data
    const worksheetData = [headers, ...rows];
    const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);

    // Auto-size columns
    const colWidths = sheet.columns.map((col, i) => {
      const maxLength = Math.max(
        col.header.length,
        ...rows.map(row => String(row[i] ?? '').length)
      );
      return { wch: Math.min(maxLength + 2, 50) };
    });
    worksheet['!cols'] = colWidths;

    // Add worksheet to workbook (sheet name max 31 chars)
    const sheetName = sheet.name.substring(0, 31);
    XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);
  });

  // Generate XLSX file
  const xlsxData = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
  const blob = new Blob([xlsxData], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  downloadBlob(blob, `${filename}.xlsx`);
};

/**
 * Helper to trigger file download
 */
const downloadBlob = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Format currency value for export
 */
export const formatCurrencyForExport = (value: number): string => {
  if (value === null || value === undefined) return '';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
};

/**
 * Format percentage value for export
 */
export const formatPercentForExport = (value: number): string => {
  if (value === null || value === undefined) return '';
  return `${value.toFixed(1)}%`;
};

/**
 * Format date value for export
 */
export const formatDateForExport = (value: string | Date): string => {
  if (!value) return '';
  const date = typeof value === 'string' ? new Date(value) : value;
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

// Pre-defined column configurations for common export scenarios
export const PortfolioColumns = {
  accounts: [
    { key: 'name', header: 'Account Name' },
    { key: 'type', header: 'Account Type' },
    { key: 'institution', header: 'Institution' },
    { key: 'balance', header: 'Balance', formatter: formatCurrencyForExport }
  ],
  summary: [
    { key: 'metric', header: 'Metric' },
    { key: 'value', header: 'Value', formatter: formatCurrencyForExport }
  ]
};

export const SpendingColumns = {
  categories: [
    { key: 'category', header: 'Category' },
    { key: 'amount', header: 'Amount', formatter: formatCurrencyForExport },
    { key: 'percentage', header: 'Percentage', formatter: formatPercentForExport }
  ],
  monthly: [
    { key: 'month', header: 'Month' },
    { key: 'expenses', header: 'Expenses', formatter: formatCurrencyForExport },
    { key: 'income', header: 'Income', formatter: formatCurrencyForExport }
  ],
  merchants: [
    { key: 'name', header: 'Merchant' },
    { key: 'amount', header: 'Total Spent', formatter: formatCurrencyForExport },
    { key: 'count', header: 'Transactions' }
  ]
};

export const RetirementColumns = {
  projections: [
    { key: 'age', header: 'Age' },
    { key: 'p10', header: '10th Percentile', formatter: formatCurrencyForExport },
    { key: 'p50', header: 'Median (50th)', formatter: formatCurrencyForExport },
    { key: 'p90', header: '90th Percentile', formatter: formatCurrencyForExport }
  ],
  inputs: [
    { key: 'parameter', header: 'Parameter' },
    { key: 'value', header: 'Value' }
  ]
};

export const HouseColumns = {
  calculations: [
    { key: 'metric', header: 'Metric' },
    { key: 'value', header: 'Value' }
  ],
  timeline: [
    { key: 'month', header: 'Month' },
    { key: 'savings', header: 'Savings', formatter: formatCurrencyForExport },
    { key: 'target', header: 'Target', formatter: formatCurrencyForExport }
  ]
};
