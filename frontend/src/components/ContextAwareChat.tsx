/**
 * Context-Aware Chat Component
 * Integrates current page context into chat conversations
 */

import React, { useState, useEffect, useRef } from 'react';
import { GOVUK_CLASSES } from '../theme/govuk';
import { useChatContext } from '../hooks/useContextInjection';
import { API_CONFIG } from '../config/api';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  context?: string;
}

interface ContextAwareChatProps {
  isOpen: boolean;
  onClose: () => void;
  userRole?: string;
}

const ContextAwareChat: React.FC<ContextAwareChatProps> = ({ 
  isOpen, 
  onClose, 
  userRole = 'PM' 
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState(userRole);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Government roles from the existing system
  const roles = [
    { id: 'PM', title: 'Prime Minister', description: 'Strategic oversight and public communication' },
    { id: 'DPM', title: 'Deputy PM', description: 'Operational coordination and inter-agency liaison' },
    { id: 'Comms', title: 'Communications Director', description: 'Public messaging and media coordination' },
    { id: 'Chief of Staff', title: 'Chief of Staff', description: 'Executive coordination and resource management' },
    { id: 'CE', title: 'Chief Executive', description: 'Operational implementation and service delivery' },
    { id: 'Permanent Secretary', title: 'Permanent Secretary', description: 'Departmental expertise and protocol compliance' }
  ];
  
  const { getFormattedContext, hasContext, currentPage, currentTab } = useChatContext();

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize chat with context when opened
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const contextString = getFormattedContext();
      const selectedRoleTitle = roles.find(r => r.id === selectedRole)?.title || 'Prime Minister';
      const welcomeMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Welcome to the Emergency Planning Assistant for ${currentPage || 'London'}. I'm here to help you with evacuation planning and emergency response decisions as ${selectedRoleTitle}. How can I assist you today?`,
        timestamp: new Date().toISOString(),
        context: contextString
      };
      setMessages([welcomeMessage]);
      
      // Generate role-specific suggestions
      generateSuggestions();
    }
  }, [isOpen, messages.length, getFormattedContext, currentPage, selectedRole]);

  // Generate role-specific suggestions based on current page and role
  const generateSuggestions = () => {
    const baseSuggestions = {
      'PM': [
        "What should be my key public statement?",
        "What are the critical decisions I need to make?",
        "What do you see on this page that needs my attention?"
      ],
      'DPM': [
        "Which departments need immediate coordination?",
        "What are the resource allocation priorities?",
        "What operational issues do you see?"
      ],
      'Comms': [
        "What messaging should we use for the public?",
        "How should we communicate this information?",
        "What are the key talking points?"
      ],
      'Chief of Staff': [
        "How should we deploy resources?",
        "What's the timeline for response?",
        "What teams need activation?"
      ],
      'CE': [
        "What emergency services need deployment?",
        "What are the operational priorities?",
        "How do we ensure service continuity?"
      ],
      'Permanent Secretary': [
        "What protocols need to be followed?",
        "What are the compliance requirements?",
        "What inter-governmental coordination is required?"
      ]
    };

    // Add page-specific suggestions
    let pageSuggestions: string[] = [];
    if (currentPage?.toLowerCase().includes('sources')) {
      pageSuggestions = [
        "What do you know from the page?",
        "Are there any high-risk incidents I should know about?",
        "What's the status of our data sources?"
      ];
    } else if (currentPage?.toLowerCase().includes('dashboard')) {
      pageSuggestions = [
        "What's the current system status?",
        "What are the key metrics I should focus on?",
        "What actions are recommended?"
      ];
    } else if (currentPage?.toLowerCase().includes('results')) {
      pageSuggestions = [
        "What do these simulation results tell us?",
        "What are the key findings?",
        "What should be our next steps?"
      ];
    }

    const roleSuggestions = baseSuggestions[selectedRole as keyof typeof baseSuggestions] || baseSuggestions['PM'];
    setSuggestions([...pageSuggestions, ...roleSuggestions].slice(0, 4));
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(null);

    try {
      // Get current page context
      const currentContext = getFormattedContext();
      
      // Prepare the message with context
      const messageWithContext = hasContext() 
        ? `${currentContext}\n\n---\n\nUser Question: ${inputMessage}`
        : inputMessage;

      // Send to chat API (this would be your actual chat endpoint)
      const response = await fetch(`${API_CONFIG.baseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: messageWithContext,
          role: selectedRole,
          context: {
            page: currentPage,
            tab: currentTab,
            timestamp: new Date().toISOString()
          },
          conversation_history: messages.slice(-5) // Last 5 messages for context
        })
      });

      if (!response.ok) {
        // Handle API errors gracefully
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Chat failed: 404: No simulation found for ${currentPage?.toLowerCase() || 'london'}`);
      }

      const data = await response.json();
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || "I'm experiencing technical difficulties. The service may be temporarily unavailable. Please try again in a moment.",
        timestamp: new Date().toISOString(),
        context: currentContext
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Chat error:', err);
      
      // Provide a helpful fallback response based on the error
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      let fallbackResponse = "I'm experiencing technical difficulties. The service may be temporarily unavailable. Please try again in a moment.";
      
      if (errorMessage.includes('404') || errorMessage.includes('No simulation found')) {
        fallbackResponse = `I'm experiencing technical difficulties. The service may be temporarily unavailable. Please try again in a moment.

However, based on your current page context, I can see you're viewing ${currentPage || 'the emergency planning system'}${currentTab ? ` on the ${currentTab} tab` : ''}. 

${hasContext() ? 'I have access to the current page data and can help with questions about what you\'re seeing on screen.' : 'Please let me know what specific information you need assistance with.'}`;
      }

      const errorResponseMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: fallbackResponse,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, errorResponseMessage]);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Function to render message content with markdown-style formatting
  const renderMessageContent = (content: string) => {
    // Split content by lines to preserve structure
    const lines = content.split('\n');
    
    return lines.map((line, lineIndex) => {
      // Process each line for markdown formatting
      const processedLine = processMarkdownLine(line);
      
      return (
        <div key={lineIndex} style={{ marginBottom: lineIndex < lines.length - 1 ? '8px' : '0' }}>
          {processedLine}
        </div>
      );
    });
  };

  const processMarkdownLine = (line: string) => {
    const parts: React.ReactNode[] = [];
    let currentIndex = 0;
    
    // Regular expressions for different markdown elements
    const patterns = [
      { regex: /\*\*(.*?)\*\*/g, component: (text: string, key: number) => <strong key={key}>{text}</strong> },
      { regex: /\*(.*?)\*/g, component: (text: string, key: number) => <em key={key}>{text}</em> },
      { regex: /`(.*?)`/g, component: (text: string, key: number) => <code key={key} style={{ backgroundColor: '#f3f2f1', padding: '2px 4px', borderRadius: '3px', fontSize: '14px', fontFamily: 'monospace' }}>{text}</code> },
    ];
    
    // Find all matches for all patterns
    const allMatches: Array<{ start: number; end: number; replacement: React.ReactNode }> = [];
    
    patterns.forEach(pattern => {
      let match;
      const regex = new RegExp(pattern.regex);
      while ((match = regex.exec(line)) !== null) {
        allMatches.push({
          start: match.index,
          end: match.index + match[0].length,
          replacement: pattern.component(match[1], allMatches.length)
        });
      }
    });
    
    // Sort matches by start position
    allMatches.sort((a, b) => a.start - b.start);
    
    // Remove overlapping matches (keep the first one)
    const validMatches = [];
    let lastEnd = 0;
    for (const match of allMatches) {
      if (match.start >= lastEnd) {
        validMatches.push(match);
        lastEnd = match.end;
      }
    }
    
    // Build the result with replacements
    let partIndex = 0;
    for (const match of validMatches) {
      // Add text before the match
      if (match.start > currentIndex) {
        parts.push(line.substring(currentIndex, match.start));
      }
      
      // Add the formatted component
      parts.push(match.replacement);
      currentIndex = match.end;
    }
    
    // Add remaining text
    if (currentIndex < line.length) {
      parts.push(line.substring(currentIndex));
    }
    
    // Handle special line types
    if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
      const textWithoutBullet = line.replace(/^[\s]*[•-][\s]*/, '');
      
      // Process the text part for markdown formatting
      const processedBulletParts: React.ReactNode[] = [];
      let currentIdx = 0;
      
      // Apply markdown formatting to the text part only
      const bulletMatches: Array<{ start: number; end: number; replacement: React.ReactNode }> = [];
      
      patterns.forEach(pattern => {
        let match;
        const regex = new RegExp(pattern.regex);
        while ((match = regex.exec(textWithoutBullet)) !== null) {
          bulletMatches.push({
            start: match.index,
            end: match.index + match[0].length,
            replacement: pattern.component(match[1], bulletMatches.length)
          });
        }
      });
      
      // Sort and remove overlapping matches
      bulletMatches.sort((a, b) => a.start - b.start);
      const validBulletMatches = [];
      let lastBulletEnd = 0;
      for (const match of bulletMatches) {
        if (match.start >= lastBulletEnd) {
          validBulletMatches.push(match);
          lastBulletEnd = match.end;
        }
      }
      
      // Build the formatted text
      for (const match of validBulletMatches) {
        if (match.start > currentIdx) {
          processedBulletParts.push(textWithoutBullet.substring(currentIdx, match.start));
        }
        processedBulletParts.push(match.replacement);
        currentIdx = match.end;
      }
      
      if (currentIdx < textWithoutBullet.length) {
        processedBulletParts.push(textWithoutBullet.substring(currentIdx));
      }
      
      return (
        <div style={{ paddingLeft: '16px', position: 'relative' }}>
          <span style={{ position: 'absolute', left: '0', fontWeight: 'bold' }}>•</span>
          {processedBulletParts.length > 0 ? <>{processedBulletParts}</> : textWithoutBullet}
        </div>
      );
    }
    
    // Handle numbered lists
    if (/^\d+\./.test(line.trim())) {
      const numberMatch = line.match(/^\s*(\d+\.)/);
      const textWithoutNumber = line.replace(/^\s*\d+\.\s*/, '');
      
      // Process the text part for markdown formatting
      const processedTextParts: React.ReactNode[] = [];
      let currentIdx = 0;
      
      // Apply markdown formatting to the text part only
      const textMatches: Array<{ start: number; end: number; replacement: React.ReactNode }> = [];
      
      patterns.forEach(pattern => {
        let match;
        const regex = new RegExp(pattern.regex);
        while ((match = regex.exec(textWithoutNumber)) !== null) {
          textMatches.push({
            start: match.index,
            end: match.index + match[0].length,
            replacement: pattern.component(match[1], textMatches.length)
          });
        }
      });
      
      // Sort and remove overlapping matches
      textMatches.sort((a, b) => a.start - b.start);
      const validTextMatches = [];
      let lastTextEnd = 0;
      for (const match of textMatches) {
        if (match.start >= lastTextEnd) {
          validTextMatches.push(match);
          lastTextEnd = match.end;
        }
      }
      
      // Build the formatted text
      for (const match of validTextMatches) {
        if (match.start > currentIdx) {
          processedTextParts.push(textWithoutNumber.substring(currentIdx, match.start));
        }
        processedTextParts.push(match.replacement);
        currentIdx = match.end;
      }
      
      if (currentIdx < textWithoutNumber.length) {
        processedTextParts.push(textWithoutNumber.substring(currentIdx));
      }
      
      return (
        <div style={{ paddingLeft: '20px', position: 'relative' }}>
          <span style={{ position: 'absolute', left: '0', fontWeight: 'bold' }}>
            {numberMatch?.[1]}
          </span>
          {processedTextParts.length > 0 ? <>{processedTextParts}</> : textWithoutNumber}
        </div>
      );
    }
    
    // Handle emoji indicators
    if (line.includes('🔴') || line.includes('🟡') || line.includes('🟢') || line.includes('🚨') || line.includes('⚠️') || line.includes('✅')) {
      return <div style={{ fontWeight: '500' }}>{parts.length > 0 ? parts : line}</div>;
    }
    
    return parts.length > 0 ? <>{parts}</> : line;
  };

  const startNewChat = () => {
    // Only show confirmation if there are existing messages (more than just the welcome message)
    if (messages.length > 1) {
      const confirmed = window.confirm(
        'Are you sure you want to start a new chat? This will clear your current conversation history.'
      );
      if (!confirmed) return;
    }
    
    setMessages([]);
    setInputMessage('');
    setError(null);
    
    // Generate new welcome message
    const contextString = getFormattedContext();
    const selectedRoleTitle = roles.find(r => r.id === selectedRole)?.title || 'Prime Minister';
    const welcomeMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'assistant',
      content: `Welcome to the Emergency Planning Assistant for ${currentPage || 'London'}. I'm here to help you with evacuation planning and emergency response decisions as ${selectedRoleTitle}. How can I assist you today?`,
      timestamp: new Date().toISOString(),
      context: contextString
    };
    setMessages([welcomeMessage]);
    
    // Regenerate suggestions
    generateSuggestions();
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      bottom: 0,
      left: isFullScreen ? 0 : 'auto',
      width: isFullScreen ? '100vw' : '500px',
      maxWidth: isFullScreen ? '100vw' : '90vw',
      backgroundColor: '#ffffff',
      boxShadow: isFullScreen ? 'none' : '-4px 0 24px rgba(0, 0, 0, 0.2)',
      zIndex: 999,
      display: 'flex',
      flexDirection: 'column',
      animation: isFullScreen ? 'none' : 'slideInRight 0.3s ease-out',
      transition: 'all 0.3s ease-out'
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px',
        borderBottom: '1px solid #b1b4b6',
        backgroundColor: '#1d70b8',
        color: '#ffffff'
      }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 className="govuk-heading-m" style={{ color: '#ffffff', margin: 0 }}>
                Emergency Response Assistant
              </h2>
              <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: '#ffffff', opacity: 0.9 }}>
                {currentPage && `${currentPage}${currentTab ? ` - ${currentTab}` : ''}`}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                className="govuk-button govuk-button--secondary"
                onClick={startNewChat}
                style={{
                  marginTop: 0,
                  marginBottom: 0,
                  padding: '8px 12px',
                  fontSize: '14px'
                }}
                title="Start a new conversation"
              >
                New Chat
              </button>
              <button 
                className="govuk-button govuk-button--secondary"
                onClick={() => setIsFullScreen(!isFullScreen)}
                style={{
                  marginTop: 0,
                  marginBottom: 0,
                  padding: '8px 12px',
                  fontSize: '16px'
                }}
                title={isFullScreen ? 'Exit full screen' : 'Expand to full screen'}
              >
                {isFullScreen ? '⊟' : '⊞'}
              </button>
              <button 
                className="govuk-button govuk-button--secondary"
                onClick={onClose}
                style={{
                  marginTop: 0,
                  marginBottom: 0,
                  padding: '8px 16px',
                  fontSize: '16px'
                }}
              >
                Close
              </button>
            </div>
          </div>

          {/* Role Selector */}
          <div style={{ marginTop: '16px' }}>
            <label
              className={GOVUK_CLASSES.form.label}
              htmlFor="role-select"
              style={{ color: '#ffffff', marginBottom: '8px' }}
            >
              Your Role
            </label>
            <select
              id="role-select"
              className={GOVUK_CLASSES.form.select}
              value={selectedRole}
              onChange={(e) => {
                setSelectedRole(e.target.value);
                generateSuggestions();
                
                // Update welcome message if it's the only message
                if (messages.length === 1 && messages[0].role === 'assistant') {
                  const contextString = getFormattedContext();
                  const newRoleTitle = roles.find(r => r.id === e.target.value)?.title || 'Prime Minister';
                  const updatedWelcomeMessage: ChatMessage = {
                    ...messages[0],
                    content: `Welcome to the Emergency Planning Assistant for ${currentPage || 'London'}. I'm here to help you with evacuation planning and emergency response decisions as ${newRoleTitle}. How can I assist you today?`,
                    timestamp: new Date().toISOString(),
                    context: contextString
                  };
                  setMessages([updatedWelcomeMessage]);
                }
              }}
              style={{ width: '100%' }}
            >
              {roles.map(role => (
                <option key={role.id} value={role.id}>
                  {role.title}
                </option>
              ))}
            </select>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', opacity: 0.8 }}>
              {roles.find(r => r.id === selectedRole)?.description}
            </p>
          </div>
      </div>

      {/* Context Summary Panel */}
      {hasContext() && (
        <div style={{
          padding: '16px 24px',
          backgroundColor: '#f3f2f1',
          borderBottom: '1px solid #b1b4b6'
        }}>
          <p className={GOVUK_CLASSES.body.s} style={{ margin: '0 0 8px 0', fontWeight: 'bold' }}>
            Current Context:
          </p>
          <p className={GOVUK_CLASSES.body.s} style={{ margin: 0 }}>
            <strong>{currentPage}</strong>{currentTab ? ` - ${currentTab} tab` : ''}
            <br />
            <span style={{ color: '#00703c' }}>✓ Live page data available</span>
          </p>
        </div>
      )}

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: isFullScreen ? '24px 10%' : '24px',
        backgroundColor: '#f3f2f1',
        maxWidth: isFullScreen ? 'none' : '100%'
      }}>
          {messages.length === 0 && (
            <div style={{
              textAlign: 'center',
              padding: '40px 20px',
              color: '#505a5f'
            }}>
              <p style={{ fontSize: '18px', marginBottom: '16px' }}>
                No conversation started yet
              </p>
              <p style={{ fontSize: '14px', opacity: 0.8 }}>
                Use the suggestions below or ask me anything about emergency planning
              </p>
            </div>
          )}
          
          {messages.map((message) => (
            <div key={message.id} style={{ marginBottom: '16px' }}>
              <div style={{
                backgroundColor: message.role === 'user' ? '#1d70b8' : '#ffffff',
                color: message.role === 'user' ? '#ffffff' : '#0b0c0c',
                padding: '16px',
                borderRadius: '4px',
                border: message.role === 'assistant' ? '1px solid #b1b4b6' : 'none',
                marginLeft: message.role === 'user' ? (isFullScreen ? '20%' : '40px') : '0',
                marginRight: message.role === 'user' ? '0' : (isFullScreen ? '20%' : '40px'),
                maxWidth: isFullScreen ? '60%' : 'none'
              }}>
                <div style={{ 
                  fontSize: '16px', 
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap'
                }}>
                  {renderMessageContent(message.content)}
                </div>
                <div style={{
                  fontSize: '12px',
                  opacity: 0.7,
                  marginTop: '8px',
                  textAlign: message.role === 'user' ? 'right' : 'left'
                }}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{
                backgroundColor: '#ffffff',
                color: '#0b0c0c',
                padding: '16px',
                borderRadius: '4px',
                border: '1px solid #b1b4b6',
                marginRight: isFullScreen ? '20%' : '40px',
                maxWidth: isFullScreen ? '60%' : 'none'
              }}>
                <div style={{ fontSize: '16px', lineHeight: '1.5' }}>
                  <em>Analysing your request and current context...</em>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div style={{
          padding: '0.5rem 2rem',
          backgroundColor: '#d4351c',
          color: 'white',
          fontSize: '14px'
        }}>
          Connection Issue: {error.includes('404') ? 'API Error (500)' : 'Service temporarily unavailable'}
        </div>
      )}

      {/* Input */}
      <div style={{
        padding: isFullScreen ? '24px 10%' : '24px',
        borderTop: '1px solid #b1b4b6',
        backgroundColor: '#ffffff'
      }}>
          {/* Suggestions */}
          {suggestions.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <p style={{ margin: '0 0 0.5rem 0', fontSize: '14px', fontWeight: 'bold' }}>
                Suggested questions:
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    className="govuk-button govuk-button--secondary"
                    style={{ 
                      fontSize: '12px', 
                      padding: '4px 8px', 
                      margin: 0,
                      whiteSpace: 'nowrap'
                    }}
                    onClick={() => setInputMessage(suggestion)}
                    disabled={isLoading}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="govuk-form-group" style={{ margin: 0 }}>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <textarea
                className="govuk-textarea"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about priorities, resources, or actions..."
                rows={2}
                style={{ flex: 1, resize: 'none' }}
                disabled={isLoading}
              />
              <button
                className={`govuk-button ${isLoading ? 'govuk-button--disabled' : ''}`}
                onClick={sendMessage}
                disabled={isLoading || !inputMessage.trim()}
                style={{ alignSelf: 'flex-end', margin: 0 }}
              >
                Send
              </button>
            </div>
          </div>
      </div>
    </div>
  );
};

export default ContextAwareChat;
