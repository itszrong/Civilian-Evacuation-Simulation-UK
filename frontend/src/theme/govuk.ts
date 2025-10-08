/**
 * GOV.UK Theme Configuration for Civilian Evacuation Planning Tool
 * Supports Cabinet Office and London Resilience department branding
 */

export interface DepartmentTheme {
  name: string;
  fullName: string;
  headerTitle: string;
  serviceName: string;
  logoUrl?: string;
  primaryColor: string;
  headerBackgroundColor: string;
  description: string;
}

export const DEPARTMENT_THEMES: Record<string, DepartmentTheme> = {
  'cabinet-office': {
    name: 'Cabinet Office',
    fullName: 'Cabinet Office - Civil Contingencies Secretariat',
    headerTitle: 'HM Government',
    serviceName: 'Civilian Evacuation Planning Tool',
    primaryColor: '#1d70b8', // GOV.UK blue
    headerBackgroundColor: '#0b0c0c', // GOV.UK black
    description: 'Real-time agentic simulation for national emergency planning and response'
  },
  'london-resilience': {
    name: 'London Resilience',
    fullName: 'Greater London Authority - London Resilience',
    headerTitle: 'London Resilience',
    serviceName: 'London Evacuation Planning',
    primaryColor: '#9d1a25', // London red
    headerBackgroundColor: '#0b0c0c',
    description: 'Multi-agency evacuation planning for Greater London'
  },
  'situation-centre': {
    name: 'Situation Centre',
    fullName: 'Emergency Planning Situation Centre',
    headerTitle: 'GOV.UK',
    serviceName: 'Civilian Evacuation Simulation',
    primaryColor: '#1d70b8', // GOV.UK blue
    headerBackgroundColor: '#0b0c0c', // GOV.UK black
    description: 'Advanced emergency planning and simulation system'
  }
};

export const DEFAULT_DEPARTMENT = 'situation-centre';

// GOV.UK Design System CSS Classes
export const GOVUK_CLASSES = {
  // Layout
  container: 'govuk-width-container',
  mainWrapper: 'govuk-main-wrapper',
  gridRow: 'govuk-grid-row',
  gridColumn: {
    full: 'govuk-grid-column-full',
    twoThirds: 'govuk-grid-column-two-thirds',
    oneThird: 'govuk-grid-column-one-third',
    half: 'govuk-grid-column-one-half'
  },

  // Typography
  heading: {
    xl: 'govuk-heading-xl',
    l: 'govuk-heading-l',
    m: 'govuk-heading-m',
    s: 'govuk-heading-s'
  },
  body: {
    m: 'govuk-body',
    s: 'govuk-body-s',
    lead: 'govuk-body-lead'
  },
  caption: {
    xl: 'govuk-caption-xl',
    l: 'govuk-caption-l',
    m: 'govuk-caption-m',
    s: 'govuk-caption-s'
  },

  // Components
  button: {
    primary: 'govuk-button',
    secondary: 'govuk-button govuk-button--secondary',
    warning: 'govuk-button govuk-button--warning',
    disabled: 'govuk-button govuk-button--disabled',
    start: 'govuk-button govuk-button--start'
  },
  form: {
    group: 'govuk-form-group',
    label: 'govuk-label',
    hint: 'govuk-hint',
    input: 'govuk-input',
    textarea: 'govuk-textarea',
    select: 'govuk-select',
    fieldset: 'govuk-fieldset',
    legend: 'govuk-fieldset__legend'
  },
  panel: 'govuk-panel govuk-panel--confirmation',
  insetText: 'govuk-inset-text',
  warningText: 'govuk-warning-text',
  summaryList: {
    container: 'govuk-summary-list',
    row: 'govuk-summary-list__row',
    key: 'govuk-summary-list__key',
    value: 'govuk-summary-list__value',
    actions: 'govuk-summary-list__actions'
  },
  tabs: {
    container: 'govuk-tabs',
    list: 'govuk-tabs__list',
    item: 'govuk-tabs__list-item',
    tab: 'govuk-tabs__tab',
    panel: 'govuk-tabs__panel'
  },
  tag: {
    base: 'govuk-tag',
    green: 'govuk-tag govuk-tag--green',
    blue: 'govuk-tag govuk-tag--blue',
    orange: 'govuk-tag govuk-tag--orange',
    red: 'govuk-tag govuk-tag--red',
    grey: 'govuk-tag govuk-tag--grey'
  },
  table: {
    container: 'govuk-table',
    caption: 'govuk-table__caption',
    head: 'govuk-table__head',
    body: 'govuk-table__body',
    row: 'govuk-table__row',
    header: 'govuk-table__header',
    cell: 'govuk-table__cell'
  },
  notification: {
    banner: 'govuk-notification-banner',
    header: 'govuk-notification-banner__header',
    title: 'govuk-notification-banner__title',
    content: 'govuk-notification-banner__content',
    success: 'govuk-notification-banner--success'
  },
  details: {
    container: 'govuk-details',
    summary: 'govuk-details__summary',
    text: 'govuk-details__text'
  },
  accordion: {
    container: 'govuk-accordion',
    section: 'govuk-accordion__section',
    header: 'govuk-accordion__section-header',
    button: 'govuk-accordion__section-button',
    content: 'govuk-accordion__section-content'
  },

  // Utilities
  spacing: {
    marginBottom: {
      0: 'govuk-!-margin-bottom-0',
      1: 'govuk-!-margin-bottom-1',
      2: 'govuk-!-margin-bottom-2',
      3: 'govuk-!-margin-bottom-3',
      4: 'govuk-!-margin-bottom-4',
      5: 'govuk-!-margin-bottom-5',
      6: 'govuk-!-margin-bottom-6',
      7: 'govuk-!-margin-bottom-7',
      8: 'govuk-!-margin-bottom-8',
      9: 'govuk-!-margin-bottom-9'
    },
    marginTop: {
      0: 'govuk-!-margin-top-0',
      1: 'govuk-!-margin-top-1',
      2: 'govuk-!-margin-top-2',
      3: 'govuk-!-margin-top-3',
      4: 'govuk-!-margin-top-4',
      5: 'govuk-!-margin-top-5',
      6: 'govuk-!-margin-top-6',
      7: 'govuk-!-margin-top-7',
      8: 'govuk-!-margin-top-8',
      9: 'govuk-!-margin-top-9'
    }
  },
  font: {
    weightBold: 'govuk-!-font-weight-bold',
    weightRegular: 'govuk-!-font-weight-regular'
  }
};

// Helper function to get current theme
export const getCurrentTheme = (): DepartmentTheme => {
  const stored = localStorage.getItem('department-theme');
  return DEPARTMENT_THEMES[stored || DEFAULT_DEPARTMENT];
};

// Helper function to set theme
export const setCurrentTheme = (departmentKey: string): void => {
  if (DEPARTMENT_THEMES[departmentKey]) {
    localStorage.setItem('department-theme', departmentKey);
    // Trigger a custom event to notify components of theme change
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: departmentKey }));
  }
};
