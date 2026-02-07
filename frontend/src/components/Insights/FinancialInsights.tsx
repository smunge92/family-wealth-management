import React, { useState } from 'react';
import { useMsal } from '@azure/msal-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar
} from 'recharts';
import api from '../../services/api';
import { useFamilyMember } from '../../context/FamilyMemberContext';
import {
  exportToCSV, exportToXLSX,
  PortfolioColumns, SpendingColumns, RetirementColumns, HouseColumns,
  formatCurrencyForExport
} from '../../utils/exportUtils';
import './FinancialInsights.css';

type InsightType = 'portfolio' | 'spending' | 'retirement' | 'house' | null;

interface RetirementFormData {
  current_age: number;
  retirement_age: number;
  current_savings: number;
  monthly_contribution: number;
  desired_annual_income: number;
  risk_tolerance: 'conservative' | 'moderate' | 'aggressive';
  life_expectancy: number;
  social_security_annual: number;
}

interface HouseFormData {
  annual_income: number;
  current_savings: number;
  monthly_debts: number;
  target_location: string;
  down_payment_percent: number;
}

interface MonteCarloData {
  num_simulations: number;
  success_probability: number;
  on_track: boolean;
  savings_gap: number;
  additional_monthly_needed: number;
  safe_withdrawal_rate: number;
  accumulation: {
    median_at_retirement: number;
    p10_at_retirement: number;
    p90_at_retirement: number;
  };
  withdrawal: {
    success_rate: number;
    yearly_success_rates: number[];
  };
}

interface PortfolioChartData {
  by_account_type: Array<{ name: string; value: number }>;
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
}

interface PortfolioTableData {
  accounts: Array<{
    name: string;
    type: string;
    balance: number;
    institution: string;
  }>;
}

interface SpendingChartData {
  by_category: Array<{ name: string; value: number }>;
  monthly_trend: Array<{ month: string; expenses: number; income: number }>;
  top_merchants: Array<{ name: string; amount: number; count: number }>;
  summary: {
    total_expenses: number;
    total_income: number;
  };
}

interface SpendingTableData {
  category_breakdown: Array<{
    category: string;
    amount: number;
    percentage: number;
  }>;
}

const COLORS = ['#800020', '#1a472a', '#d4af37', '#1a365d', '#8b4513', '#2d3748', '#6b21a8', '#0369a1'];

const FinancialInsights: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeInsight, setActiveInsight] = useState<InsightType>(null);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [chartData, setChartData] = useState<any>(null);
  const [monteCarloData, setMonteCarloData] = useState<MonteCarloData | null>(null);
  const [portfolioChartData, setPortfolioChartData] = useState<PortfolioChartData | null>(null);
  const [portfolioTableData, setPortfolioTableData] = useState<PortfolioTableData | null>(null);
  const [spendingChartData, setSpendingChartData] = useState<SpendingChartData | null>(null);
  const [spendingTableData, setSpendingTableData] = useState<SpendingTableData | null>(null);

  const [retirementForm, setRetirementForm] = useState<RetirementFormData>({
    current_age: 35,
    retirement_age: 65,
    current_savings: 100000,
    monthly_contribution: 1500,
    desired_annual_income: 80000,
    risk_tolerance: 'moderate',
    life_expectancy: 90,
    social_security_annual: 20000
  });

  const [houseForm, setHouseForm] = useState<HouseFormData>({
    annual_income: 150000,
    current_savings: 80000,
    monthly_debts: 0,
    target_location: 'Seattle, WA',
    down_payment_percent: 20
  });

  const { accounts } = useMsal();
  const user = accounts[0];
  const { selectedMemberId, getSelectedMemberName } = useFamilyMember();

  const fetchInsight = async (type: InsightType, additionalData: any = {}) => {
    if (!user || !type) return;

    setLoading(true);
    setError(null);
    setAnalysis(null);
    setChartData(null);
    setMonteCarloData(null);
    setPortfolioChartData(null);
    setPortfolioTableData(null);
    setSpendingChartData(null);
    setSpendingTableData(null);
    setActiveInsight(type);

    try {
      const endpoint = type === 'spending' ? '/insights/spending' :
                       type === 'portfolio' ? '/insights/portfolio' :
                       type === 'retirement' ? '/insights/retirement' :
                       '/insights/house';

      // Include family_member_id for spending and portfolio analysis
      const familyMemberData = (type === 'spending' || type === 'portfolio') && selectedMemberId
        ? { family_member_id: selectedMemberId }
        : {};

      const requestData = {
        user_id: user.localAccountId,
        ...familyMemberData,
        ...additionalData
      };
      console.log('Sending request to', endpoint, 'with data:', requestData);

      const response = await api.post(endpoint, requestData);
      console.log('Received response:', response.data);

      setAnalysis(response.data.analysis);

      // Handle portfolio chart and table data
      if (type === 'portfolio' && response.data.chart_data) {
        setPortfolioChartData(response.data.chart_data);
        setPortfolioTableData(response.data.table_data);
      }

      // Handle spending chart and table data
      if (type === 'spending' && response.data.chart_data) {
        setSpendingChartData(response.data.chart_data);
        setSpendingTableData(response.data.table_data);
      }

      if (type === 'retirement' && response.data.projections) {
        setChartData({
          type: 'retirement',
          projections: response.data.projections,
          summary: response.data.summary
        });
        if (response.data.monte_carlo) {
          setMonteCarloData(response.data.monte_carlo);
        }
      } else if (type === 'house' && response.data.calculations) {
        console.log('House calculations received:', response.data.calculations);
        console.log('Max Home Price:', response.data.calculations.max_home_price);
        console.log('Max Monthly Payment:', response.data.calculations.max_monthly_payment);
        console.log('Debug info:', response.data.debug);
        setChartData({
          type: 'house',
          calculations: response.data.calculations,
          timeline: response.data.savings_timeline,
          debug: response.data.debug
        });
      }

    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to get insights');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const renderAnalysis = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, index) => {
      if (line.startsWith('## ')) {
        return <h4 key={index} className="analysis-heading">{line.replace('## ', '')}</h4>;
      } else if (line.startsWith('### ')) {
        return <h5 key={index} className="analysis-subheading">{line.replace('### ', '')}</h5>;
      } else if (line.startsWith('**') && line.endsWith('**')) {
        return <p key={index} className="analysis-bold">{line.replace(/\*\*/g, '')}</p>;
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        return <li key={index} className="analysis-bullet">{line.substring(2)}</li>;
      } else if (line.match(/^\d+\./)) {
        return <li key={index} className="analysis-numbered">{line.replace(/^\d+\.\s*/, '')}</li>;
      } else if (line.trim() === '') {
        return <br key={index} />;
      } else {
        return <p key={index} className="analysis-text">{line}</p>;
      }
    });
  };

  const insightCards = [
    {
      id: 'portfolio',
      title: 'Portfolio Analysis',
      description: 'Get AI-powered analysis of your investment allocation, diversification, and risk profile.',
      icon: '📊',
      iconClass: 'portfolio'
    },
    {
      id: 'spending',
      title: 'Spending Analysis',
      description: 'Understand your spending patterns and get personalized recommendations to optimize your budget.',
      icon: '💰',
      iconClass: 'portfolio'
    },
    {
      id: 'retirement',
      title: 'Retirement Planning',
      description: 'Monte Carlo simulation with 10,000 scenarios to project your retirement success probability.',
      icon: '🎯',
      iconClass: 'retirement'
    },
    {
      id: 'house',
      title: 'House Affordability',
      description: 'Calculate how much house you can afford and plan your path to homeownership.',
      icon: '🏠',
      iconClass: 'house'
    }
  ];

  return (
    <div className="insights-page-3d">
      {/* Page Header */}
      <div className="page-header-3d">
        <div>
          <h1>Financial Planning</h1>
          <p className="page-subtitle">AI-powered insights and Monte Carlo simulation for your financial future</p>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="message-3d message-error-3d">
          <span>Error</span> {error}
        </div>
      )}

      {/* Insight Selection Cards */}
      {!loading && !analysis && (
        <div className="insights-grid-3d">
          {insightCards.map(card => (
            <div
              key={card.id}
              className={`insight-card-3d ${activeInsight === card.id ? 'active' : ''}`}
              onClick={() => {
                if (card.id === 'portfolio' || card.id === 'spending') {
                  fetchInsight(card.id as InsightType);
                } else {
                  setActiveInsight(card.id as InsightType);
                }
              }}
            >
              <div className="insight-card-header-3d">
                <div className={`insight-card-icon-3d ${card.iconClass}`}>
                  {card.icon}
                </div>
                <h3>{card.title}</h3>
              </div>
              <p>{card.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Retirement Planning Form */}
      {activeInsight === 'retirement' && !analysis && !loading && (
        <div className="insight-form-3d">
          <h3>Retirement Planning Details</h3>
          <p style={{ color: '#666', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            We'll run 10,000 Monte Carlo simulations to calculate your probability of retirement success.
          </p>
          <div className="form-grid-3d">
            <div className="form-group-3d">
              <label>Current Age</label>
              <input
                type="number"
                value={retirementForm.current_age}
                onChange={(e) => setRetirementForm({ ...retirementForm, current_age: parseInt(e.target.value) || 0 })}
              />
            </div>
            <div className="form-group-3d">
              <label>Retirement Age</label>
              <input
                type="number"
                value={retirementForm.retirement_age}
                onChange={(e) => setRetirementForm({ ...retirementForm, retirement_age: parseInt(e.target.value) || 0 })}
              />
            </div>
            <div className="form-group-3d">
              <label>Life Expectancy</label>
              <input
                type="number"
                value={retirementForm.life_expectancy}
                onChange={(e) => setRetirementForm({ ...retirementForm, life_expectancy: parseInt(e.target.value) || 0 })}
              />
            </div>
            <div className="form-group-3d">
              <label>Current Savings ($)</label>
              <input
                type="number"
                value={retirementForm.current_savings}
                onChange={(e) => setRetirementForm({ ...retirementForm, current_savings: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="form-group-3d">
              <label>Monthly Contribution ($)</label>
              <input
                type="number"
                value={retirementForm.monthly_contribution}
                onChange={(e) => setRetirementForm({ ...retirementForm, monthly_contribution: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="form-group-3d">
              <label>Desired Annual Retirement Income ($)</label>
              <input
                type="number"
                value={retirementForm.desired_annual_income}
                onChange={(e) => setRetirementForm({ ...retirementForm, desired_annual_income: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="form-group-3d">
              <label>Expected Social Security ($/year)</label>
              <input
                type="number"
                value={retirementForm.social_security_annual}
                onChange={(e) => setRetirementForm({ ...retirementForm, social_security_annual: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="form-group-3d">
              <label>Risk Tolerance</label>
              <select
                value={retirementForm.risk_tolerance}
                onChange={(e) => setRetirementForm({ ...retirementForm, risk_tolerance: e.target.value as any })}
              >
                <option value="conservative">Conservative (30% stocks, 50% bonds)</option>
                <option value="moderate">Moderate (50% stocks, 30% bonds)</option>
                <option value="aggressive">Aggressive (70% stocks, 15% bonds)</option>
              </select>
            </div>
          </div>
          <div className="form-actions-3d">
            <button
              className="button-3d button-maroon"
              onClick={() => fetchInsight('retirement', retirementForm)}
              disabled={loading}
            >
              Run Monte Carlo Simulation
            </button>
            <button
              className="button-3d button-secondary-3d"
              onClick={() => setActiveInsight(null)}
            >
              Back
            </button>
          </div>
        </div>
      )}

      {/* House Affordability Form */}
      {activeInsight === 'house' && !analysis && !loading && (
        <div className="insight-form-3d">
          <h3>Home Buying Details</h3>
          <div className="form-grid-3d">
            <div className="form-group-3d">
              <label>Annual Household Income ($)</label>
              <input
                type="number"
                value={houseForm.annual_income}
                onChange={(e) => setHouseForm({ ...houseForm, annual_income: parseFloat(e.target.value) || 0 })}
                min="1000"
              />
            </div>
            <div className="form-group-3d">
              <label>Current Savings ($)</label>
              <input
                type="number"
                value={houseForm.current_savings}
                onChange={(e) => setHouseForm({ ...houseForm, current_savings: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="form-group-3d">
              <label>Monthly Debt Payments ($)</label>
              <input
                type="number"
                value={houseForm.monthly_debts}
                onChange={(e) => setHouseForm({ ...houseForm, monthly_debts: parseFloat(e.target.value) || 0 })}
                placeholder="0"
                min="0"
              />
            </div>
            <div className="form-group-3d">
              <label>Target Location</label>
              <input
                type="text"
                value={houseForm.target_location}
                onChange={(e) => setHouseForm({ ...houseForm, target_location: e.target.value })}
                placeholder="e.g., Seattle, WA"
              />
            </div>
            <div className="form-group-3d">
              <label>Down Payment (%)</label>
              <input
                type="number"
                value={houseForm.down_payment_percent}
                onChange={(e) => setHouseForm({ ...houseForm, down_payment_percent: parseFloat(e.target.value) || 0 })}
              />
            </div>
          </div>
          <div className="form-actions-3d">
            <button
              className="button-3d button-maroon"
              onClick={() => {
                console.log('House form values being sent:', houseForm);
                console.log('annual_income:', houseForm.annual_income, 'type:', typeof houseForm.annual_income);
                console.log('down_payment_percent:', houseForm.down_payment_percent, 'type:', typeof houseForm.down_payment_percent);
                if (houseForm.annual_income < 1000) {
                  setError('Please enter a valid annual income (at least $1,000)');
                  return;
                }
                fetchInsight('house', houseForm);
              }}
              disabled={loading}
            >
              Get Affordability Analysis
            </button>
            <button
              className="button-3d button-secondary-3d"
              onClick={() => setActiveInsight(null)}
            >
              Back
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-card-3d">
          <div className="spinner-3d"></div>
          <div className="loading-text-3d">
            {activeInsight === 'retirement'
              ? 'Running 10,000 Monte Carlo simulations...'
              : 'Analyzing your finances with Claude AI...'}
          </div>
          <div className="loading-subtext-3d">This may take 10-20 seconds</div>
        </div>
      )}

      {/* Portfolio Analysis Section */}
      {portfolioChartData && (
        <div className="insight-result-3d">
          <div className="insight-result-header-3d">
            <h3>Portfolio Analysis</h3>
            <div className="download-buttons">
              <button
                className="button-3d button-download"
                onClick={() => {
                  if (portfolioTableData?.accounts) {
                    exportToCSV(portfolioTableData.accounts, PortfolioColumns.accounts, 'portfolio-accounts');
                  }
                }}
              >
                CSV
              </button>
              <button
                className="button-3d button-download"
                onClick={() => {
                  const sheets = [];
                  if (portfolioTableData?.accounts) {
                    sheets.push({
                      name: 'Accounts',
                      data: portfolioTableData.accounts,
                      columns: PortfolioColumns.accounts
                    });
                  }
                  sheets.push({
                    name: 'Summary',
                    data: [
                      { metric: 'Total Assets', value: portfolioChartData.total_assets },
                      { metric: 'Total Liabilities', value: portfolioChartData.total_liabilities },
                      { metric: 'Net Worth', value: portfolioChartData.net_worth }
                    ],
                    columns: PortfolioColumns.summary
                  });
                  exportToXLSX(sheets, 'portfolio-analysis');
                }}
              >
                Excel
              </button>
              <button
                className="button-3d button-secondary-3d"
                onClick={() => {
                  setAnalysis(null);
                  setPortfolioChartData(null);
                  setPortfolioTableData(null);
                  setActiveInsight(null);
                }}
                style={{ padding: '10px 20px', fontSize: '14px' }}
              >
                Back
              </button>
            </div>
          </div>
          <div className="insight-result-content-3d">
            {/* Summary Cards */}
            <div className="summary-cards-3d">
              <div className="summary-card-3d maroon">
                <div className="card-3d-inner">
                  <div className="card-icon-3d">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                      <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
                    </svg>
                  </div>
                  <div className="card-content-3d">
                    <span className="card-label-3d">Total Assets</span>
                    <span className="card-value-3d">{formatCurrency(portfolioChartData.total_assets)}</span>
                  </div>
                </div>
              </div>
              <div className="summary-card-3d dark-green">
                <div className="card-3d-inner">
                  <div className="card-icon-3d">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                      <path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
                    </svg>
                  </div>
                  <div className="card-content-3d">
                    <span className="card-label-3d">Total Liabilities</span>
                    <span className="card-value-3d">{formatCurrency(portfolioChartData.total_liabilities)}</span>
                  </div>
                </div>
              </div>
              <div className="summary-card-3d gold">
                <div className="card-3d-inner">
                  <div className="card-icon-3d">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                  </div>
                  <div className="card-content-3d">
                    <span className="card-label-3d">Net Worth</span>
                    <span className="card-value-3d">{formatCurrency(portfolioChartData.net_worth)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Asset Allocation Pie Chart */}
            {portfolioChartData.by_account_type.length > 0 && (
              <div className="chart-table-row">
                <div className="insight-chart-3d chart-half">
                  <h4 style={{ marginBottom: '1rem', color: '#800020' }}>Asset Allocation by Account Type</h4>
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        data={portfolioChartData.by_account_type}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                        labelLine={false}
                      >
                        {portfolioChartData.by_account_type.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value: number) => formatCurrency(value)}
                        contentStyle={{
                          background: 'linear-gradient(145deg, #fff8f0, #ffffff)',
                          border: '2px solid #800020',
                          borderRadius: '10px'
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                {/* Accounts Table */}
                {portfolioTableData?.accounts && portfolioTableData.accounts.length > 0 && (
                  <div className="data-table-container table-half">
                    <h4 style={{ marginBottom: '1rem', color: '#800020' }}>Account Details</h4>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Account</th>
                          <th>Type</th>
                          <th>Balance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {portfolioTableData.accounts.map((account, index) => (
                          <tr key={index}>
                            <td>{account.name}</td>
                            <td>{account.type}</td>
                            <td className={account.balance < 0 ? 'negative' : ''}>{formatCurrency(account.balance)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Spending Analysis Section */}
      {spendingChartData && (
        <div className="insight-result-3d">
          <div className="insight-result-header-3d">
            <h3>Spending Analysis</h3>
            <div className="download-buttons">
              <button
                className="button-3d button-download"
                onClick={() => {
                  if (spendingTableData?.category_breakdown) {
                    exportToCSV(spendingTableData.category_breakdown, SpendingColumns.categories, 'spending-categories');
                  }
                }}
              >
                CSV
              </button>
              <button
                className="button-3d button-download"
                onClick={() => {
                  const sheets = [];
                  if (spendingTableData?.category_breakdown) {
                    sheets.push({
                      name: 'Categories',
                      data: spendingTableData.category_breakdown,
                      columns: SpendingColumns.categories
                    });
                  }
                  if (spendingChartData.monthly_trend) {
                    sheets.push({
                      name: 'Monthly Trend',
                      data: spendingChartData.monthly_trend,
                      columns: SpendingColumns.monthly
                    });
                  }
                  if (spendingChartData.top_merchants) {
                    sheets.push({
                      name: 'Top Merchants',
                      data: spendingChartData.top_merchants,
                      columns: SpendingColumns.merchants
                    });
                  }
                  exportToXLSX(sheets, 'spending-analysis');
                }}
              >
                Excel
              </button>
              <button
                className="button-3d button-secondary-3d"
                onClick={() => {
                  setAnalysis(null);
                  setSpendingChartData(null);
                  setSpendingTableData(null);
                  setActiveInsight(null);
                }}
                style={{ padding: '10px 20px', fontSize: '14px' }}
              >
                Back
              </button>
            </div>
          </div>
          <div className="insight-result-content-3d">
            {/* Summary Cards */}
            <div className="summary-cards-3d">
              <div className="summary-card-3d maroon">
                <div className="card-3d-inner">
                  <div className="card-icon-3d">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                      <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/>
                    </svg>
                  </div>
                  <div className="card-content-3d">
                    <span className="card-label-3d">Total Expenses</span>
                    <span className="card-value-3d">{formatCurrency(spendingChartData.summary.total_expenses)}</span>
                  </div>
                </div>
              </div>
              <div className="summary-card-3d dark-green">
                <div className="card-3d-inner">
                  <div className="card-icon-3d">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                      <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
                    </svg>
                  </div>
                  <div className="card-content-3d">
                    <span className="card-label-3d">Total Income</span>
                    <span className="card-value-3d">{formatCurrency(spendingChartData.summary.total_income)}</span>
                  </div>
                </div>
              </div>
              <div className={`summary-card-3d ${(spendingChartData.summary.total_income - spendingChartData.summary.total_expenses) >= 0 ? 'gold' : 'dark-blue'}`}>
                <div className="card-3d-inner">
                  <div className="card-icon-3d">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                      <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
                    </svg>
                  </div>
                  <div className="card-content-3d">
                    <span className="card-label-3d">Net Cash Flow</span>
                    <span className="card-value-3d">{formatCurrency(spendingChartData.summary.total_income - spendingChartData.summary.total_expenses)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Charts Row */}
            <div className="chart-table-row">
              {/* Category Pie Chart */}
              {spendingChartData.by_category.length > 0 && (
                <div className="insight-chart-3d chart-half">
                  <h4 style={{ marginBottom: '1rem', color: '#800020' }}>Spending by Category</h4>
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        data={spendingChartData.by_category}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ name, percent }) => `${name.substring(0, 10)}${name.length > 10 ? '...' : ''} (${(percent * 100).toFixed(0)}%)`}
                        labelLine={false}
                      >
                        {spendingChartData.by_category.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value: number) => formatCurrency(value)}
                        contentStyle={{
                          background: 'linear-gradient(145deg, #fff8f0, #ffffff)',
                          border: '2px solid #800020',
                          borderRadius: '10px'
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Monthly Trend Bar Chart */}
              {spendingChartData.monthly_trend.length > 0 && (
                <div className="insight-chart-3d chart-half">
                  <h4 style={{ marginBottom: '1rem', color: '#800020' }}>Monthly Income vs Expenses</h4>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={spendingChartData.monthly_trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e8dce0" />
                      <XAxis dataKey="month" stroke="#666" />
                      <YAxis tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`} stroke="#666" />
                      <Tooltip
                        formatter={(value: number) => formatCurrency(value)}
                        contentStyle={{
                          background: 'linear-gradient(145deg, #fff8f0, #ffffff)',
                          border: '2px solid #800020',
                          borderRadius: '10px'
                        }}
                      />
                      <Legend />
                      <Bar dataKey="income" fill="#1a472a" name="Income" />
                      <Bar dataKey="expenses" fill="#800020" name="Expenses" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Tables Row */}
            <div className="chart-table-row" style={{ marginTop: '1.5rem' }}>
              {/* Category Breakdown Table */}
              {spendingTableData?.category_breakdown && spendingTableData.category_breakdown.length > 0 && (
                <div className="data-table-container table-half">
                  <h4 style={{ marginBottom: '1rem', color: '#800020' }}>Category Breakdown</h4>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th>Amount</th>
                        <th>%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {spendingTableData.category_breakdown.slice(0, 10).map((cat, index) => (
                        <tr key={index}>
                          <td>{cat.category}</td>
                          <td>{formatCurrency(cat.amount)}</td>
                          <td>{cat.percentage.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Top Merchants Table */}
              {spendingChartData.top_merchants && spendingChartData.top_merchants.length > 0 && (
                <div className="data-table-container table-half">
                  <h4 style={{ marginBottom: '1rem', color: '#800020' }}>Top Merchants</h4>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Merchant</th>
                        <th>Amount</th>
                        <th>Txns</th>
                      </tr>
                    </thead>
                    <tbody>
                      {spendingChartData.top_merchants.slice(0, 10).map((merchant, index) => (
                        <tr key={index}>
                          <td>{merchant.name}</td>
                          <td>{formatCurrency(merchant.amount)}</td>
                          <td>{merchant.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Charts Section */}
      {chartData && (
        <div className="insight-result-3d">
          <div className="insight-result-header-3d">
            <h3>
              {chartData.type === 'retirement' ? 'Monte Carlo Retirement Projections' : 'Financial Projections'}
            </h3>
            <div className="download-buttons">
              {chartData.type === 'retirement' && chartData.projections && (
                <>
                  <button
                    className="button-3d button-download"
                    onClick={() => {
                      exportToCSV(chartData.projections, RetirementColumns.projections, 'retirement-projections');
                    }}
                  >
                    CSV
                  </button>
                  <button
                    className="button-3d button-download"
                    onClick={() => {
                      const sheets = [
                        {
                          name: 'Projections',
                          data: chartData.projections,
                          columns: RetirementColumns.projections
                        },
                        {
                          name: 'Input Parameters',
                          data: [
                            { parameter: 'Current Age', value: retirementForm.current_age },
                            { parameter: 'Retirement Age', value: retirementForm.retirement_age },
                            { parameter: 'Life Expectancy', value: retirementForm.life_expectancy },
                            { parameter: 'Current Savings', value: formatCurrencyForExport(retirementForm.current_savings) },
                            { parameter: 'Monthly Contribution', value: formatCurrencyForExport(retirementForm.monthly_contribution) },
                            { parameter: 'Desired Annual Income', value: formatCurrencyForExport(retirementForm.desired_annual_income) },
                            { parameter: 'Social Security (Annual)', value: formatCurrencyForExport(retirementForm.social_security_annual) },
                            { parameter: 'Risk Tolerance', value: retirementForm.risk_tolerance }
                          ],
                          columns: RetirementColumns.inputs
                        }
                      ];
                      if (monteCarloData) {
                        sheets.push({
                          name: 'Monte Carlo Summary',
                          data: [
                            { parameter: 'Success Probability', value: `${monteCarloData.success_probability}%` },
                            { parameter: 'Simulations Run', value: monteCarloData.num_simulations.toLocaleString() },
                            { parameter: 'Median at Retirement', value: formatCurrencyForExport(monteCarloData.accumulation.median_at_retirement) },
                            { parameter: '10th Percentile', value: formatCurrencyForExport(monteCarloData.accumulation.p10_at_retirement) },
                            { parameter: '90th Percentile', value: formatCurrencyForExport(monteCarloData.accumulation.p90_at_retirement) },
                            { parameter: 'Safe Withdrawal Rate', value: `${monteCarloData.safe_withdrawal_rate}%` },
                            { parameter: 'On Track', value: monteCarloData.on_track ? 'Yes' : 'No' }
                          ],
                          columns: RetirementColumns.inputs
                        });
                      }
                      exportToXLSX(sheets, 'retirement-analysis');
                    }}
                  >
                    Excel
                  </button>
                </>
              )}
              {chartData.type === 'house' && chartData.calculations && (
                <>
                  <button
                    className="button-3d button-download"
                    onClick={() => {
                      const data = [
                        { metric: 'Max Home Price', value: formatCurrencyForExport(chartData.calculations.max_home_price) },
                        { metric: 'Max Monthly Payment', value: formatCurrencyForExport(chartData.calculations.max_monthly_payment) },
                        { metric: 'Ready to Buy', value: chartData.calculations.ready_to_buy ? 'Yes' : 'No' },
                        { metric: 'Savings Gap', value: formatCurrencyForExport(chartData.calculations.savings_gap || 0) }
                      ];
                      exportToCSV(data, HouseColumns.calculations, 'house-affordability');
                    }}
                  >
                    CSV
                  </button>
                  <button
                    className="button-3d button-download"
                    onClick={() => {
                      const sheets = [
                        {
                          name: 'Calculations',
                          data: [
                            { metric: 'Max Home Price', value: formatCurrencyForExport(chartData.calculations.max_home_price) },
                            { metric: 'Max Monthly Payment', value: formatCurrencyForExport(chartData.calculations.max_monthly_payment) },
                            { metric: 'Ready to Buy', value: chartData.calculations.ready_to_buy ? 'Yes' : 'No' },
                            { metric: 'Savings Gap', value: formatCurrencyForExport(chartData.calculations.savings_gap || 0) }
                          ],
                          columns: HouseColumns.calculations
                        },
                        {
                          name: 'Input Parameters',
                          data: [
                            { metric: 'Annual Income', value: formatCurrencyForExport(houseForm.annual_income) },
                            { metric: 'Current Savings', value: formatCurrencyForExport(houseForm.current_savings) },
                            { metric: 'Monthly Debts', value: formatCurrencyForExport(houseForm.monthly_debts) },
                            { metric: 'Target Location', value: houseForm.target_location },
                            { metric: 'Down Payment %', value: `${houseForm.down_payment_percent}%` }
                          ],
                          columns: HouseColumns.calculations
                        }
                      ];
                      if (chartData.timeline) {
                        sheets.push({
                          name: 'Savings Timeline',
                          data: chartData.timeline,
                          columns: HouseColumns.timeline
                        });
                      }
                      exportToXLSX(sheets, 'house-affordability-analysis');
                    }}
                  >
                    Excel
                  </button>
                </>
              )}
              <button
                className="button-3d button-secondary-3d"
                onClick={() => {
                  setAnalysis(null);
                  setChartData(null);
                  setMonteCarloData(null);
                  setActiveInsight(null);
                }}
                style={{ padding: '10px 20px', fontSize: '14px' }}
              >
                Back
              </button>
            </div>
          </div>
          <div className="insight-result-content-3d">
            {chartData.type === 'retirement' && chartData.projections && (
              <>
                {/* Monte Carlo Summary Cards */}
                <div className="summary-cards-3d">
                  {monteCarloData && (
                    <>
                      <div className="summary-card-3d maroon">
                        <div className="card-3d-inner">
                          <div className="card-icon-3d">
                            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                            </svg>
                          </div>
                          <div className="card-content-3d">
                            <span className="card-label-3d">Success Probability</span>
                            <span className="card-value-3d">{monteCarloData.success_probability}%</span>
                          </div>
                        </div>
                      </div>
                      <div className="summary-card-3d maroon">
                        <div className="card-3d-inner">
                          <div className="card-icon-3d">
                            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                              <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
                            </svg>
                          </div>
                          <div className="card-content-3d">
                            <span className="card-label-3d">Median at Retirement</span>
                            <span className="card-value-3d">{formatCurrency(monteCarloData.accumulation.median_at_retirement)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="summary-card-3d maroon">
                        <div className="card-3d-inner">
                          <div className="card-icon-3d">
                            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                              <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
                            </svg>
                          </div>
                          <div className="card-content-3d">
                            <span className="card-label-3d">10th - 90th Percentile</span>
                            <span className="card-value-3d" style={{ fontSize: '1.1rem' }}>
                              {formatCurrency(monteCarloData.accumulation.p10_at_retirement)} - {formatCurrency(monteCarloData.accumulation.p90_at_retirement)}
                            </span>
                          </div>
                        </div>
                      </div>
                      {monteCarloData.savings_gap > 0 && (
                        <div className="summary-card-3d maroon">
                          <div className="card-3d-inner">
                            <div className="card-icon-3d">
                              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                              </svg>
                            </div>
                            <div className="card-content-3d">
                              <span className="card-label-3d">Additional Monthly Needed</span>
                              <span className="card-value-3d">{formatCurrency(monteCarloData.additional_monthly_needed)}</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* Monte Carlo Probability Chart */}
                <div className="insight-chart-3d" style={{ marginTop: '2rem' }}>
                  <h4 style={{ marginBottom: '1rem', color: '#800020' }}>Retirement Balance Projection (with uncertainty bands)</h4>
                  <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '1rem' }}>
                    The shaded areas show the range of possible outcomes from 10,000 simulations
                  </p>
                  <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={chartData.projections}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e8dce0" />
                      <XAxis
                        dataKey="age"
                        stroke="#666"
                        label={{ value: 'Age', position: 'bottom', offset: -5 }}
                      />
                      <YAxis
                        tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
                        stroke="#666"
                      />
                      <Tooltip
                        formatter={(value: number, name: string) => {
                          const labels: { [key: string]: string } = {
                            p90: '90th Percentile (Optimistic)',
                            p75: '75th Percentile',
                            p50: '50th Percentile (Median)',
                            p25: '25th Percentile',
                            p10: '10th Percentile (Pessimistic)'
                          };
                          return [formatCurrency(value), labels[name] || name];
                        }}
                        contentStyle={{
                          background: 'linear-gradient(145deg, #fff8f0, #ffffff)',
                          border: '2px solid #800020',
                          borderRadius: '10px',
                          boxShadow: '0 8px 24px rgba(128, 0, 32, 0.3)'
                        }}
                        labelStyle={{ color: '#800020', fontWeight: 700 }}
                        labelFormatter={(label) => `Age ${label}`}
                      />
                      <Legend
                        formatter={(value) => {
                          const labels: { [key: string]: string } = {
                            p90: '90th Percentile',
                            p50: 'Median (50th)',
                            p10: '10th Percentile'
                          };
                          return labels[value] || value;
                        }}
                      />
                      {/* 10th-90th percentile band */}
                      <Area
                        type="monotone"
                        dataKey="p90"
                        stroke="#1a472a"
                        fill="#1a472a"
                        fillOpacity={0.1}
                        strokeWidth={1}
                        strokeDasharray="3 3"
                      />
                      <Area
                        type="monotone"
                        dataKey="p10"
                        stroke="#d4af37"
                        fill="#ffffff"
                        fillOpacity={1}
                        strokeWidth={1}
                        strokeDasharray="3 3"
                      />
                      {/* Median line */}
                      <Line
                        type="monotone"
                        dataKey="p50"
                        stroke="#800020"
                        strokeWidth={3}
                        dot={false}
                        name="p50"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Simulation Details */}
                {monteCarloData && (
                  <div style={{
                    marginTop: '1.5rem',
                    padding: '1rem',
                    background: '#f8f9fa',
                    borderRadius: '10px',
                    fontSize: '0.9rem'
                  }}>
                    <h4 style={{ marginBottom: '0.75rem', color: '#800020' }}>Monte Carlo Simulation Details</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.5rem' }}>
                      <div><strong>Simulations Run:</strong> {monteCarloData.num_simulations.toLocaleString()}</div>
                      <div><strong>Safe Withdrawal Rate:</strong> {monteCarloData.safe_withdrawal_rate}%</div>
                      <div><strong>On Track:</strong> {monteCarloData.on_track ? 'Yes' : 'No'}</div>
                      {monteCarloData.savings_gap > 0 && (
                        <div><strong>Savings Gap:</strong> {formatCurrency(monteCarloData.savings_gap)}</div>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}

            {chartData.type === 'house' && chartData.calculations && (
              <>
                {/* Debug info - remove after fixing */}
                {chartData.calculations.max_home_price === 0 && chartData.debug && (
                  <div style={{ padding: '1rem', background: '#fee2e2', borderRadius: '8px', marginBottom: '1rem', color: '#800020' }}>
                    <strong>Debug:</strong> Calculations returned 0. Backend debug info:
                    <pre style={{ fontSize: '0.8rem', marginTop: '0.5rem', whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(chartData.debug, null, 2)}
                    </pre>
                  </div>
                )}
                {chartData.calculations.max_home_price === 0 && !chartData.debug && (
                  <div style={{ padding: '1rem', background: '#fee2e2', borderRadius: '8px', marginBottom: '1rem', color: '#800020' }}>
                    <strong>Debug:</strong> Calculations returned 0 but no debug info. Backend may need restart.
                    Raw values: max_home_price={chartData.calculations.max_home_price}, max_monthly_payment={chartData.calculations.max_monthly_payment}
                  </div>
                )}
                <div className="summary-cards-3d">
                  <div className="summary-card-3d maroon">
                    <div className="card-3d-inner">
                      <div className="card-icon-3d">
                        <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                          <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
                        </svg>
                      </div>
                      <div className="card-content-3d">
                        <span className="card-label-3d">Max Home Price</span>
                        <span className="card-value-3d">{formatCurrency(chartData.calculations.max_home_price)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="summary-card-3d maroon">
                    <div className="card-3d-inner">
                      <div className="card-icon-3d">
                        <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                          <path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
                        </svg>
                      </div>
                      <div className="card-content-3d">
                        <span className="card-label-3d">Max Monthly Payment</span>
                        <span className="card-value-3d">{formatCurrency(chartData.calculations.max_monthly_payment)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="summary-card-3d maroon">
                    <div className="card-3d-inner">
                      <div className="card-icon-3d">
                        {chartData.calculations.ready_to_buy ? (
                          <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                          </svg>
                        ) : (
                          <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                          </svg>
                        )}
                      </div>
                      <div className="card-content-3d">
                        <span className="card-label-3d">Ready to Buy?</span>
                        <span className="card-value-3d">
                          {chartData.calculations.ready_to_buy ? 'Yes!' : 'Not Yet'}
                        </span>
                      </div>
                    </div>
                  </div>
                  {!chartData.calculations.ready_to_buy && (
                    <div className="summary-card-3d maroon">
                      <div className="card-3d-inner">
                        <div className="card-icon-3d">
                          <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                            <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
                          </svg>
                        </div>
                        <div className="card-content-3d">
                          <span className="card-label-3d">Savings Gap</span>
                          <span className="card-value-3d">{formatCurrency(chartData.calculations.savings_gap)}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {chartData.timeline && (
                  <div className="insight-chart-3d">
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={chartData.timeline.filter((_: any, i: number) => i % 3 === 0)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e8dce0" />
                        <XAxis dataKey="month" label={{ value: 'Months', position: 'bottom', offset: -5 }} stroke="#666" />
                        <YAxis tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`} stroke="#666" />
                        <Tooltip
                          formatter={(value: number) => formatCurrency(value)}
                          contentStyle={{
                            background: 'linear-gradient(145deg, #fff8f0, #ffffff)',
                            border: '2px solid #800020',
                            borderRadius: '10px',
                            boxShadow: '0 8px 24px rgba(128, 0, 32, 0.3)'
                          }}
                          labelStyle={{ color: '#800020', fontWeight: 700 }}
                          itemStyle={{ color: '#1a1a1a', fontWeight: 600 }}
                        />
                        <Legend />
                        <Line type="monotone" dataKey="savings" stroke="#800020" strokeWidth={3} name="Your Savings" dot={false} />
                        <Line type="monotone" dataKey="target" stroke="#1a472a" strokeWidth={3} strokeDasharray="5 5" name="Target (Down Payment + Closing)" dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Analysis Results */}
      {analysis && (
        <div className="insight-result-3d" style={{ marginTop: '24px' }}>
          <div className="insight-result-header-3d">
            <h3>AI Analysis</h3>
          </div>
          <div className="insight-result-content-3d">
            <div className="insight-analysis-3d">
              {renderAnalysis(analysis)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FinancialInsights;
