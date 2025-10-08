/**
 * Global Chat Button Component
 * Floating action button that opens context-aware chat from any page
 */

import React, { useState } from 'react';
import ContextAwareChat from './ContextAwareChat';
import { useChatContext } from '../hooks/useContextInjection';

interface GlobalChatButtonProps {
  userRole?: string;
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
}

const GlobalChatButton: React.FC<GlobalChatButtonProps> = ({ 
  userRole = 'Prime Minister',
  position = 'bottom-right'
}) => {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const { hasContext, currentPage } = useChatContext();

  const getPositionStyles = (): React.CSSProperties => {
    const baseStyles: React.CSSProperties = {
      position: 'fixed',
      zIndex: 1500,
      width: '60px',
      height: '60px',
      borderRadius: '50%',
      backgroundColor: '#1d70b8',
      color: 'white',
      border: 'none',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '24px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
      transition: 'all 0.3s ease'
    };

    const positionMap: Record<string, React.CSSProperties> = {
      'bottom-right': { bottom: '20px', right: '20px' },
      'bottom-left': { bottom: '20px', left: '20px' },
      'top-right': { top: '20px', right: '20px' },
      'top-left': { top: '20px', left: '20px' }
    };

    return { ...baseStyles, ...positionMap[position] };
  };

  return (
    <>
      {/* Only show chat button when chat is closed */}
      {!isChatOpen && (
        <>
          <button
            style={getPositionStyles()}
            onClick={() => setIsChatOpen(true)}
            title={`Emergency Response Assistant${currentPage ? ` - ${currentPage}` : ''}`}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.1)';
              e.currentTarget.style.backgroundColor = '#003078';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.backgroundColor = '#1d70b8';
            }}
          >
            💬
          </button>

          {/* Context indicator badge */}
          {hasContext() && (
            <div style={{
              position: 'fixed',
              bottom: position.includes('bottom') ? '65px' : undefined,
              top: position.includes('top') ? '65px' : undefined,
              right: position.includes('right') ? '30px' : undefined,
              left: position.includes('left') ? '30px' : undefined,
              zIndex: 1501,
              backgroundColor: '#00703c',
              color: 'white',
              borderRadius: '10px',
              padding: '2px 6px',
              fontSize: '10px',
              fontWeight: 'bold'
            }}>
              ✓
            </div>
          )}
        </>
      )}

      <ContextAwareChat
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        userRole={userRole}
      />
    </>
  );
};

export default GlobalChatButton;