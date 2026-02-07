import React, { useState, useEffect } from 'react';
import { useMsal } from '@azure/msal-react';
import './About.css';

const About: React.FC = () => {
  const { accounts } = useMsal();
  const user = accounts[0];
  const firstName = user?.name?.split(' ')[0] || 'Friend';

  // Animated counters
  const [counters, setCounters] = useState({ apis: 0, lines: 0, coffees: 0, bugs: 0 });

  useEffect(() => {
    const targets = { apis: 7, lines: 15000, coffees: 42, bugs: 0 };
    const duration = 1500;
    const steps = 40;
    const interval = duration / steps;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      const progress = Math.min(step / steps, 1);
      const ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setCounters({
        apis: Math.round(targets.apis * ease),
        lines: Math.round(targets.lines * ease),
        coffees: Math.round(targets.coffees * ease),
        bugs: Math.round(targets.bugs * ease),
      });
      if (step >= steps) clearInterval(timer);
    }, interval);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="about-page">
      {/* Hero Section */}
      <div className="about-hero">
        <div className="hero-badge">v1.0</div>
        <h1 className="hero-title">
          Family Wealth Management
        </h1>
        <p className="hero-subtitle">
          Because spreadsheets are so 2005, and asking "where did all my money go?"
          at 2 AM is not a healthy coping mechanism.
        </p>
        <div className="hero-wave"></div>
      </div>

      {/* Stats Bar */}
      <div className="about-stats-bar">
        <div className="stat-item">
          <span className="stat-number">{counters.apis}</span>
          <span className="stat-label">APIs Integrated</span>
        </div>
        <div className="stat-divider"></div>
        <div className="stat-item">
          <span className="stat-number">{counters.lines.toLocaleString()}+</span>
          <span className="stat-label">Lines of Code</span>
        </div>
        <div className="stat-divider"></div>
        <div className="stat-item">
          <span className="stat-number">{counters.coffees}</span>
          <span className="stat-label">Cups of Coffee</span>
        </div>
        <div className="stat-divider"></div>
        <div className="stat-item">
          <span className="stat-number">{counters.bugs}*</span>
          <span className="stat-label">Known Bugs</span>
        </div>
      </div>

      {/* What Is This Thing */}
      <div className="about-section">
        <div className="section-header">
          <div className="section-icon">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          <h2>So... What Is This Thing?</h2>
        </div>
        <p className="section-text">
          Welcome, {firstName}! This is your family's personal finance command center.
          Think of it as a financial co-pilot that doesn't judge you for that third
          Starbucks run today. It connects to your real bank accounts, tracks every
          penny (yes, even that "miscellaneous" charge you don't remember), and
          uses AI to tell you things you probably already know but are choosing to ignore.
        </p>
        <div className="feature-callout">
          <span className="callout-emoji">*</span>
          <span className="callout-text">
            *"Known Bugs: 0" is aspirational. If you find one, it's a feature.
          </span>
        </div>
      </div>

      {/* How It Works - Pipeline */}
      <div className="about-section dark-section">
        <h2>How The Magic Happens</h2>
        <p className="section-subtitle">
          (Spoiler: It's not actually magic. It's APIs, databases, and a lot of patience.)
        </p>
        <div className="pipeline">
          <div className="pipeline-step">
            <div className="step-icon bank">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <path d="M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z"/>
              </svg>
            </div>
            <h3>Your Banks</h3>
            <p>Chase, BoA, Credit Cards... we talk to all of them via Plaid. Securely. We promise.</p>
          </div>
          <div className="pipeline-arrow">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
              <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
            </svg>
          </div>
          <div className="pipeline-step">
            <div className="step-icon sync">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
              </svg>
            </div>
            <h3>Sync & Sort</h3>
            <p>Transactions get pulled, categorized by smart rules, and stored in Azure SQL. No duplicates!</p>
          </div>
          <div className="pipeline-arrow">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
              <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
            </svg>
          </div>
          <div className="pipeline-step">
            <div className="step-icon brain">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6A4.997 4.997 0 0 1 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z"/>
              </svg>
            </div>
            <h3>AI Thinks</h3>
            <p>Claude AI analyzes your habits, runs Monte Carlo simulations, and tries not to be judgy about your spending.</p>
          </div>
          <div className="pipeline-arrow">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
              <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
            </svg>
          </div>
          <div className="pipeline-step">
            <div className="step-icon chart">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                <path d="M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z"/>
              </svg>
            </div>
            <h3>Pretty Charts</h3>
            <p>Because data without charts is just... sad numbers in a table. And we're better than that.</p>
          </div>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="about-section">
        <h2>The Good Stuff</h2>
        <p className="section-subtitle">a.k.a. why you should actually use this instead of your "mental budget"</p>
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-card-icon" style={{ background: 'linear-gradient(135deg, #800020, #a02040)' }}>
              <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
                <path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/>
              </svg>
            </div>
            <h3>Multi-Account Sync</h3>
            <p>
              Connect checking, savings, credit cards, investments -- basically anything
              that makes your money disappear. All in one place.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card-icon" style={{ background: 'linear-gradient(135deg, #1a472a, #2d6a4f)' }}>
              <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
                <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
              </svg>
            </div>
            <h3>Smart Categories</h3>
            <p>
              24 built-in categories with auto-matching rules. It knows that
              "SWIGGY" is food and "MTA" is transportation. Smarter than your average app.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card-icon" style={{ background: 'linear-gradient(135deg, #d4af37, #e8c84a)' }}>
              <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
                <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
              </svg>
            </div>
            <h3>Charts That Slap</h3>
            <p>
              Pie charts, bar charts, area charts, trend lines. Your Dashboard
              looks like a Bloomberg terminal (but actually understandable).
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card-icon" style={{ background: 'linear-gradient(135deg, #1a365d, #2c5282)' }}>
              <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
                <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/>
              </svg>
            </div>
            <h3>Bank-Level Security</h3>
            <p>
              Azure AD authentication, encrypted tokens, OWASP-audited backend.
              Your data is safer here than under your mattress.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card-icon" style={{ background: 'linear-gradient(135deg, #e74c3c, #c0392b)' }}>
              <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
                <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
              </svg>
            </div>
            <h3>Family Profiles</h3>
            <p>
              Track finances for the whole family. Each member gets their own
              accounts and transactions. Family drama not included.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card-icon" style={{ background: 'linear-gradient(135deg, #9b59b6, #8e44ad)' }}>
              <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
                <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/>
              </svg>
            </div>
            <h3>Cloud-Powered</h3>
            <p>
              Azure Functions, SQL Database, Cosmos DB, Key Vault. The whole
              Azure buffet. Runs 24/7 so you don't have to.
            </p>
          </div>
        </div>
      </div>

      {/* Tech Stack */}
      <div className="about-section dark-section">
        <h2>Under The Hood</h2>
        <p className="section-subtitle">For the nerds (said with love)</p>
        <div className="tech-grid">
          <div className="tech-group">
            <h3>Frontend</h3>
            <div className="tech-tags">
              <span className="tech-tag react">React 19</span>
              <span className="tech-tag ts">TypeScript</span>
              <span className="tech-tag recharts">Recharts</span>
              <span className="tech-tag msal">MSAL.js</span>
              <span className="tech-tag css">CSS3 / 3D</span>
            </div>
          </div>
          <div className="tech-group">
            <h3>Backend</h3>
            <div className="tech-tags">
              <span className="tech-tag python">Python 3.14</span>
              <span className="tech-tag azure">Azure Functions v2</span>
              <span className="tech-tag sql">Azure SQL</span>
              <span className="tech-tag cosmos">Cosmos DB</span>
              <span className="tech-tag kv">Key Vault</span>
            </div>
          </div>
          <div className="tech-group">
            <h3>Integrations</h3>
            <div className="tech-tags">
              <span className="tech-tag plaid">Plaid API</span>
              <span className="tech-tag claude">Claude AI</span>
              <span className="tech-tag aad">Azure AD</span>
              <span className="tech-tag ghpages">GitHub Pages</span>
            </div>
          </div>
        </div>
      </div>

      {/* Architecture Diagram */}
      <div className="about-section">
        <h2>Architecture (The Fancy Diagram)</h2>
        <p className="section-subtitle">How the pieces fit together</p>
        <div className="arch-diagram">
          <div className="arch-row">
            <div className="arch-box user-box">
              <div className="arch-icon">
                <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
              </div>
              <span>You ({firstName})</span>
            </div>
          </div>
          <div className="arch-connector">|</div>
          <div className="arch-row">
            <div className="arch-box frontend-box">
              <span>React + TypeScript</span>
              <span className="arch-sub">GitHub Pages</span>
            </div>
          </div>
          <div className="arch-connector">| HTTPS</div>
          <div className="arch-row">
            <div className="arch-box backend-box">
              <span>Azure Functions (Python)</span>
              <span className="arch-sub">REST API</span>
            </div>
          </div>
          <div className="arch-connector-split">
            <span>/</span>
            <span>|</span>
            <span>\</span>
          </div>
          <div className="arch-row arch-row-multi">
            <div className="arch-box db-box">
              <span>Azure SQL</span>
              <span className="arch-sub">Transactions</span>
            </div>
            <div className="arch-box db-box">
              <span>Plaid API</span>
              <span className="arch-sub">Bank Data</span>
            </div>
            <div className="arch-box db-box">
              <span>Claude AI</span>
              <span className="arch-sub">Insights</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="about-footer">
        <p className="footer-text">
          Built with a mass amount of coffee, questionable life choices, and Claude Code.
        </p>
        <p className="footer-version">
          v1.0 &middot; {new Date().getFullYear()} &middot; The Munge Family
        </p>
      </div>
    </div>
  );
};

export default About;
