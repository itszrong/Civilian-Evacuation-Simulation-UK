/**
 * GOV.UK Layout Component
 * Standard government page layout with header, main content, and footer
 */

import React from 'react';
import Header from './Header';
import { getCurrentTheme } from '../../theme/govuk';

interface LayoutProps {
  children: React.ReactNode;
  pageTitle?: string;
}

const Layout: React.FC<LayoutProps> = ({ 
  children, 
  pageTitle
}) => {
  const theme = getCurrentTheme();

  return (
    <div className="govuk-template">
      {/* Skip link */}
      <a href="#main-content" className="govuk-skip-link">
        Skip to main content
      </a>

      {/* Header */}
      <Header />

      {/* Main content */}
      <div className="govuk-width-container">
        <main className="govuk-main-wrapper" id="main-content" role="main">
          {pageTitle && (
            <div className="govuk-grid-row">
              <div className="govuk-grid-column-two-thirds">
                <span className="govuk-caption-xl">{theme.fullName}</span>
                <h1 className="govuk-heading-xl">{pageTitle}</h1>
                <p className="govuk-body-lead">{theme.description}</p>
              </div>
            </div>
          )}
          {children}
        </main>
      </div>

      {/* Footer */}
      <footer className="govuk-footer" role="contentinfo">
        <div className="govuk-width-container">
          <div className="govuk-footer__meta">
            <div className="govuk-footer__meta-item govuk-footer__meta-item--grow">
              <h2 className="govuk-visually-hidden">Support links</h2>
              <ul className="govuk-footer__inline-list">
                <li className="govuk-footer__inline-list-item">
                  <a className="govuk-footer__link" href="/help">
                    Help
                  </a>
                </li>
                {/* <li className="govuk-footer__inline-list-item">
                  <a className="govuk-footer__link" href="/privacy">
                    Privacy
                  </a>
                </li>
                <li className="govuk-footer__inline-list-item">
                  <a className="govuk-footer__link" href="/cookies">
                    Cookies
                  </a>
                </li>
                <li className="govuk-footer__inline-list-item">
                  <a className="govuk-footer__link" href="/accessibility">
                    Accessibility statement
                  </a>
                </li> */}
                <li className="govuk-footer__inline-list-item">
                  <a className="govuk-footer__link" href="/contact">
                    Contact
                  </a>
                </li>
              </ul>
              <div className="govuk-footer__meta-custom">
                {/* Built by the {theme.fullName} */}
                Built by Zhen Rong Yap
              </div>
            </div>
            {/* <div className="govuk-footer__meta-item">
              <a 
                className="govuk-footer__link govuk-footer__copyright-logo" 
                href="https://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/uk-government-licensing-framework/crown-copyright/"
              >
                <svg
                  aria-hidden="true"
                  focusable="false"
                  className="govuk-footer__licence-logo"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 483.2 195.7"
                  height="17"
                  width="41"
                >
                  <path
                    fill="currentColor"
                    d="M421.5 142.8V.1l-50.7 32.3v161.1h112.4v-50.7zm-122.3-9.6A47.12 47.12 0 0 1 221 97.8c0-26 21.1-47.1 47.1-47.1 16.7 0 31.4 8.7 39.7 21.8l42.7-27.2A98.66 98.66 0 0 0 268.1 0c-36.5 0-68.3 19.6-85.4 48.8A98.27 98.27 0 0 0 97.8 0C43.9 0 0 43.9 0 97.8s43.9 97.8 97.8 97.8c36.5 0 68.3-19.6 85.4-48.8 17.1 29.2 48.9 48.8 85.4 48.8 54.1 0 97.8-43.9 97.8-97.8 0-36.5-19.6-68.3-48.8-85.4l-27.2 42.7c13.2 8.3 21.8 23.1 21.8 39.7 0 26-21.1 47.1-47.1 47.1s-47.1-21.1-47.1-47.1z"
                  />
                  <path
                    fill="currentColor"
                    d="M97.8 145c-26 0-47.1-21.1-47.1-47.1s21.1-47.1 47.1-47.1 47.2 21 47.2 47S123.8 145 97.8 145"
                  />
                </svg>
                <span className="govuk-visually-hidden">
                  © Crown copyright
                </span>
              </a>
            </div> */}
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
