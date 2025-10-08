import { createTheme, MantineColorsTuple } from '@mantine/core';

// NHS Blue inspired color palette
const nhsBlue: MantineColorsTuple = [
  '#f0f8ff', // lightest
  '#e1f0ff',
  '#b3deff',
  '#80c7ff',
  '#4db0ff',
  '#005eb8', // NHS Blue primary
  '#004a94',
  '#003670',
  '#00224c',
  '#000e28'  // darkest
];

// Healthcare red for urgent/critical items
const healthcareRed: MantineColorsTuple = [
  '#fef2f2',
  '#fee2e2',
  '#fecaca',
  '#fca5a5',
  '#f87171',
  '#dc143c', // Medical red
  '#b91c1c',
  '#991b1b',
  '#7f1d1d',
  '#6b1d1d'
];

// Healthcare green for positive indicators
const healthcareGreen: MantineColorsTuple = [
  '#f0fdf4',
  '#dcfce7',
  '#bbf7d0',
  '#86efac',
  '#4ade80',
  '#22c55e', // Healthy green
  '#16a34a',
  '#15803d',
  '#166534',
  '#14532d'
];

export const theme = createTheme({
  primaryColor: 'nhsBlue',
  
  colors: {
    nhsBlue,
    healthcareRed,
    healthcareGreen,
  },

  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
  headings: {
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
    fontWeight: '600',
  },

  components: {
    Card: {
      defaultProps: {
        withBorder: true,
      },
      styles: (theme) => ({
        root: {
          transition: 'all 0.2s ease',
          backgroundColor: theme.colorScheme === 'dark' 
            ? theme.colors.dark[7] 
            : theme.white,
          borderColor: theme.colorScheme === 'dark' 
            ? theme.colors.dark[4] 
            : theme.colors.gray[3],
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: theme.colorScheme === 'dark'
              ? '0 8px 16px rgba(0, 0, 0, 0.3)'
              : '0 8px 16px rgba(0, 0, 0, 0.15)',
          },
        },
      }),
    },

    Button: {
      styles: (theme) => ({
        root: {
          fontWeight: '500',
          '&[data-variant="filled"]': {
            backgroundColor: theme.colors.nhsBlue[5],
            '&:hover': {
              backgroundColor: theme.colors.nhsBlue[6],
            },
          },
        },
      }),
    },

    Badge: {
      styles: {
        root: {
          fontWeight: '600',
          textTransform: 'uppercase',
          fontSize: '0.75rem',
        },
      },
    },

    Table: {
      styles: (theme) => ({
        th: {
          fontWeight: '600',
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.05em',
          backgroundColor: theme.colorScheme === 'dark' 
            ? theme.colors.dark[6] 
            : theme.colors.gray[0],
        },
        tr: {
          transition: 'all 0.2s ease',
          '&:hover': {
            transform: 'translateY(-1px)',
            boxShadow: theme.colorScheme === 'dark'
              ? '0 4px 8px rgba(0, 0, 0, 0.2)'
              : '0 4px 8px rgba(0, 0, 0, 0.1)',
            backgroundColor: theme.colorScheme === 'dark'
              ? theme.colors.dark[6]
              : theme.colors.gray[0],
          },
        },
      }),
    },

    AppShell: {
      styles: (theme) => ({
        header: {
          borderBottom: `1px solid ${theme.colorScheme === 'dark' 
            ? theme.colors.dark[4] 
            : theme.colors.gray[3]}`,
          boxShadow: theme.colorScheme === 'dark'
            ? '0 1px 3px rgba(0, 0, 0, 0.3)'
            : '0 1px 3px rgba(0, 0, 0, 0.1)',
          backgroundColor: theme.colorScheme === 'dark'
            ? theme.colors.dark[7]
            : theme.white,
        },
      }),
    },

    Modal: {
      styles: (theme) => ({
        content: {
          boxShadow: theme.colorScheme === 'dark'
            ? '0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2)'
            : '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          backgroundColor: theme.colorScheme === 'dark'
            ? theme.colors.dark[7]
            : theme.white,
        },
      }),
    },
  },
});