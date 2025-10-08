/**
 * Simple Chart Component for GOV.UK Design System
 * Basic visualisation components using CSS and HTML for government reports
 */

import React from 'react';
import { GOVUK_CLASSES } from '../../theme/govuk';

interface DataPoint {
  label: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  title: string;
  data: DataPoint[];
  unit?: string;
  maxValue?: number;
}

export const BarChart: React.FC<BarChartProps> = ({ title, data, unit = '', maxValue }) => {
  const max = maxValue || Math.max(...data.map(d => d.value));
  
  return (
    <div className={`${GOVUK_CLASSES.spacing.marginBottom[4]}`} style={{ border: 'none', outline: 'none' }}>
      <h3 className={GOVUK_CLASSES.heading.s}>{title}</h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', border: 'none', outline: 'none' }}>
        {data.map((item, index) => {
          const percentage = (item.value / max) * 100;
          
          return (
            <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '160px', fontSize: '14px' }}>
                {item.label}
              </div>
              <div style={{ 
                flex: 1, 
                height: '24px', 
                backgroundColor: '#f3f2f1', 
                position: 'relative'
              }}>
                <div 
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    width: `${percentage}%`,
                    height: '100%',
                    backgroundColor: item.color || '#1d70b8',
                    transition: 'width 0.3s ease'
                  }}
                />
              </div>
              <div style={{ width: '80px', fontSize: '14px', fontWeight: 'bold', textAlign: 'right' }}>
                {item.value}{unit}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface MetricCardProps {
  title: string;
  value: number | string;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  description?: string;
  status?: 'good' | 'warning' | 'danger';
}

export const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  unit = '', 
  trend, 
  description, 
  status = 'good' 
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'good': return '#00703c';
      case 'warning': return '#f47738';
      case 'danger': return '#d4351c';
      default: return '#1d70b8';
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'up': return '↗';
      case 'down': return '↘';
      case 'stable': return '→';
      default: return '';
    }
  };

  return (
    <div style={{
      border: '1px solid #b1b4b6',
      padding: '20px',
      backgroundColor: '#ffffff',
      minHeight: '120px'
    }}>
      <h4 className={GOVUK_CLASSES.heading.s} style={{ marginBottom: '10px' }}>
        {title}
      </h4>
      
      <div style={{ 
        fontSize: '32px', 
        fontWeight: 'bold', 
        color: getStatusColor(),
        marginBottom: '5px'
      }}>
        {value}{unit}
        {trend && (
          <span style={{ fontSize: '20px', marginLeft: '8px' }}>
            {getTrendIcon()}
          </span>
        )}
      </div>
      
      {description && (
        <p className="govuk-hint" style={{ marginBottom: 0 }}>
          {description}
        </p>
      )}
    </div>
  );
};

interface ProgressRingProps {
  percentage: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  label?: string;
}

export const ProgressRing: React.FC<ProgressRingProps> = ({ 
  percentage, 
  size = 100, 
  strokeWidth = 8, 
  color = '#1d70b8',
  label 
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDasharray = `${circumference} ${circumference}`;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <svg
          height={size}
          width={size}
          style={{ transform: 'rotate(-90deg)' }}
        >
          <circle
            stroke="#f3f2f1"
            fill="transparent"
            strokeWidth={strokeWidth}
            r={radius}
            cx={size / 2}
            cy={size / 2}
          />
          <circle
            stroke={color}
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            r={radius}
            cx={size / 2}
            cy={size / 2}
            style={{ transition: 'stroke-dashoffset 0.3s ease' }}
          />
        </svg>
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: '18px',
            fontWeight: 'bold'
          }}
        >
          {Math.round(percentage)}%
        </div>
      </div>
      {label && (
        <div style={{ marginTop: '8px', fontSize: '14px' }}>
          {label}
        </div>
      )}
    </div>
  );
};

interface ComparisonTableProps {
  title: string;
  scenarios: Array<{
    name: string;
    metrics: { [key: string]: number | string };
  }>;
  highlightBest?: boolean;
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({ 
  title, 
  scenarios, 
  highlightBest = true 
}) => {
  if (scenarios.length === 0) return null;

  const metricKeys = Object.keys(scenarios[0].metrics);
  
  // Find best values for highlighting (assuming lower is better for most metrics)
  const bestValues: { [key: string]: number } = {};
  if (highlightBest) {
    metricKeys.forEach(key => {
      const numericValues = scenarios
        .map(s => s.metrics[key])
        .filter(v => typeof v === 'number') as number[];
      
      if (numericValues.length > 0) {
        bestValues[key] = Math.min(...numericValues);
      }
    });
  }

  return (
    <div className={GOVUK_CLASSES.spacing.marginBottom[4]}>
      <h3 className={GOVUK_CLASSES.heading.s}>{title}</h3>
      
      {/* Mobile-responsive table wrapper */}
      <div style={{ overflowX: 'auto', marginBottom: '1rem' }}>
        <table className={GOVUK_CLASSES.table.container} style={{ minWidth: '500px' }}>
          <thead className={GOVUK_CLASSES.table.head}>
            <tr className={GOVUK_CLASSES.table.row}>
              <th scope="col" className={GOVUK_CLASSES.table.header}>Scenario</th>
              {metricKeys.map(key => (
                <th key={key} scope="col" className={GOVUK_CLASSES.table.header}>
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className={GOVUK_CLASSES.table.body}>
            {scenarios.map((scenario, index) => (
              <tr key={index} className={GOVUK_CLASSES.table.row}>
                <td className={GOVUK_CLASSES.table.cell}>
                  <strong>{scenario.name}</strong>
                </td>
                {metricKeys.map(key => {
                  const value = scenario.metrics[key];
                  const isBest = highlightBest && 
                                typeof value === 'number' && 
                                value === bestValues[key];
                  
                  return (
                    <td 
                      key={key} 
                      className={GOVUK_CLASSES.table.cell}
                      style={isBest ? { 
                        backgroundColor: '#d2e2f1', 
                        fontWeight: 'bold' 
                      } : {}}
                    >
                      {typeof value === 'number' ? value.toFixed(2) : value}
                      {isBest && <span style={{ color: '#00703c' }}> ★</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
