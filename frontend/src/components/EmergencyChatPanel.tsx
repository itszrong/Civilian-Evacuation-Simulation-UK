/**
 * Emergency Response Chat Panel
 * Slide-over panel for role-specific emergency planning assistance
 * Using GOV.UK Design System
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { GOVUK_CLASSES } from '../theme/govuk';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  id?: string;
}

interface ChatError {
  message: string;
  type: 'network' | 'api' | 'unknown';
  timestamp: string;
}

interface EmergencyChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
  city: string;
  runId?: string;
}

const EmergencyChatPanel: React.FC<EmergencyChatPanelProps> = ({
  isOpen,
  onClose,
  city,
  runId
}) => {
  // Generate unique chat session ID
  const chatSessionId = useRef(`chat_${city}_${runId || 'default'}_${Date.now()}`);
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatError, setChatError] = useState<ChatError | null>(null);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRole, setSelectedRole] = useState('PM');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [emergencyPlan, setEmergencyPlan] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const roles = [
    { id: 'PM', title: 'Prime Minister' },
    { id: 'DPM', title: 'Deputy PM' },
    { id: 'Comms', title: 'Communications' },
    { id: 'Chief of Staff', title: 'Chief of Staff' },
    { id: 'CE', title: 'Chief Executive' },
    { id: 'Permanent Secretary', title: 'Permanent Secretary' }
  ];

  // Memory management functions
  const saveConversationToMemory = useCallback((newMessages: Message[]) => {
    try {
      const conversationData = {
        messages: newMessages,
        city,
        runId,
        selectedRole,
        timestamp: new Date().toISOString(),
        sessionId: chatSessionId.current
      };
      localStorage.setItem(chatSessionId.current, JSON.stringify(conversationData));
    } catch (error) {
      console.warn('Failed to save conversation to memory:', error);
    }
  }, [city, runId, selectedRole]);

  const loadConversationFromMemory = useCallback(() => {
    try {
      const saved = localStorage.getItem(chatSessionId.current);
      if (saved) {
        const conversationData = JSON.parse(saved);
        if (conversationData.messages && Array.isArray(conversationData.messages)) {
          setMessages(conversationData.messages);
          if (conversationData.selectedRole) {
            setSelectedRole(conversationData.selectedRole);
          }
          return true;
        }
      }
    } catch (error) {
      console.warn('Failed to load conversation from memory:', error);
    }
    return false;
  }, []);

  // Initialize chat with welcome message
  const initializeChat = useCallback(() => {
    if (!loadConversationFromMemory()) {
      const welcomeMessage: Message = {
        id: 'welcome',
        role: 'assistant',
        content: `Welcome to the Emergency Planning Assistant for ${city}. I'm here to help you with evacuation planning and emergency response decisions. How can I assist you today?`,
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMessage]);
      saveConversationToMemory([welcomeMessage]);
    }
  }, [city, loadConversationFromMemory, saveConversationToMemory]);

  // Load emergency plan and initialize chat on mount
  useEffect(() => {
    if (isOpen && city) {
      loadEmergencyPlan();
      initializeChat();
    }
  }, [isOpen, city, runId, initializeChat]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadEmergencyPlan = async () => {
    try {
      const url = runId
        ? `${API_CONFIG.baseUrl}/api/emergency/plan/${city}?run_id=${runId}`
        : `${API_CONFIG.baseUrl}/api/emergency/plan/${city}`;

      const response = await fetch(url);

      if (response.ok) {
        const plan = await response.json();
        setEmergencyPlan(plan);
      } else if (response.status === 404) {
        // Generate plan if not found
        await generateEmergencyPlan();
      }
    } catch (error) {
      console.error('Failed to load emergency plan:', error);
    }
  };

  const generateEmergencyPlan = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_CONFIG.baseUrl}/api/emergency/generate-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city, run_id: runId })
      });

      if (response.ok) {
        const plan = await response.json();
        setEmergencyPlan(plan);
      }
    } catch (error) {
      console.error('Failed to generate emergency plan:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const generateScenarioFromChat = async () => {
    if (!inputMessage.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.baseUrl}${API_ENDPOINTS.agentic.generateScenario}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_intent: inputMessage,
          city_context: city,
          constraints: `Emergency response scenario for ${selectedRole} role`
        })
      });

      if (!response.ok) {
        throw new Error('Failed to generate scenario');
      }

      const result = await response.json();
      
      // Add the generated scenario as an assistant message
      const scenarioMessage: Message = {
        role: 'assistant',
        content: `**AI Generated Scenario**: ${result.specification.name}\n\n` +
                `**Hazard Type**: ${result.specification.hazard_type}\n` +
                `**Population Affected**: ${result.specification.population_affected?.toLocaleString()}\n` +
                `**Duration**: ${result.specification.duration_minutes} minutes\n` +
                `**Severity**: ${result.specification.severity}\n\n` +
                `**AI Reasoning**: ${result.reasoning}\n\n` +
                `This scenario has been generated and can be used for simulation planning.`,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, scenarioMessage]);
      setInputMessage('');
      
    } catch (error) {
      console.error('Scenario generation failed:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Failed to generate scenario. Please try again with a different description.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (messageText?: string) => {
    const textToSend = messageText || inputMessage;
    if (!textToSend.trim() || isLoading) return;

    setChatError(null); // Clear any previous errors

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString()
    };

    // Update messages with user message immediately
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    saveConversationToMemory(updatedMessages);
    setInputMessage('');
    setIsLoading(true);

    try {
      console.log('Sending chat request to:', `${API_CONFIG.baseUrl}/api/emergency/chat`);
      console.log('Request payload:', {
        city,
        run_id: runId,
        user_role: selectedRole,
        message: textToSend,
        conversation_history: messages.slice(-10) // Send last 10 messages for context
      });

      const response = await fetch(`${API_CONFIG.baseUrl}/api/emergency/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          city,
          run_id: runId,
          user_role: selectedRole,
          message: textToSend,
          conversation_history: messages.slice(-10) // Limit context to prevent payload bloat
        })
      });

      console.log('Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', errorText);
        throw new Error(`API Error (${response.status}): ${errorText}`);
      }

      const data = await response.json();
      console.log('Chat response received:', data);

      const assistantMessage: Message = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: data.message || 'I received your message but couldn\'t generate a proper response.',
        timestamp: new Date().toISOString()
      };

      const finalMessages = [...updatedMessages, assistantMessage];
      setMessages(finalMessages);
      saveConversationToMemory(finalMessages);

      if (data.suggestions && Array.isArray(data.suggestions)) {
        setSuggestions(data.suggestions);
      }

    } catch (error) {
      console.error('Chat request failed:', error);
      
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      const chatErrorObj: ChatError = {
        message: errorMessage,
        type: errorMessage.includes('fetch') ? 'network' : 'api',
        timestamp: new Date().toISOString()
      };
      
      setChatError(chatErrorObj);

      const errorResponse: Message = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: `I'm experiencing technical difficulties. ${errorMessage.includes('fetch') ? 'Please check your internet connection.' : 'The service may be temporarily unavailable.'} Please try again in a moment.`,
        timestamp: new Date().toISOString()
      };

      const errorMessages = [...updatedMessages, errorResponse];
      setMessages(errorMessages);
      saveConversationToMemory(errorMessages);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion);
    setSuggestions([]);
  };

  const clearConversation = () => {
    if (confirm('Are you sure you want to clear the conversation? This cannot be undone.')) {
      setMessages([]);
      setSuggestions([]);
      setChatError(null);
      localStorage.removeItem(chatSessionId.current);
      initializeChat();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="govuk-emergency-chat-backdrop"
        onClick={onClose}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          zIndex: 998,
          animation: 'fadeIn 0.3s ease-in-out'
        }}
      />

      {/* Slide-over Panel */}
      <div
        className="govuk-emergency-chat-panel"
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '500px',
          maxWidth: '90vw',
          backgroundColor: '#ffffff',
          boxShadow: '-4px 0 24px rgba(0, 0, 0, 0.2)',
          zIndex: 999,
          display: 'flex',
          flexDirection: 'column',
          animation: 'slideInRight 0.3s ease-out'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #b1b4b6',
            backgroundColor: '#1d70b8',
            color: '#ffffff'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 className="govuk-heading-m" style={{ margin: 0, color: '#ffffff' }}>
                Emergency Response Assistant
              </h2>
              <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: '#ffffff', opacity: 0.9 }}>
                {city.charAt(0).toUpperCase() + city.slice(1)} Emergency Planning
              </p>
            </div>
            <button
              onClick={onClose}
              className="govuk-button govuk-button--secondary"
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
              onChange={(e) => setSelectedRole(e.target.value)}
              style={{ width: '100%' }}
            >
              {roles.map(role => (
                <option key={role.id} value={role.id}>
                  {role.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Emergency Plan Summary */}
        {emergencyPlan && (
          <div
            style={{
              padding: '16px 24px',
              backgroundColor: '#f3f2f1',
              borderBottom: '1px solid #b1b4b6'
            }}
          >
            <p className={GOVUK_CLASSES.body.s} style={{ margin: '0 0 8px 0', fontWeight: 'bold' }}>
              Situation Overview:
            </p>
            <p className={GOVUK_CLASSES.body.s} style={{ margin: 0 }}>
              <strong>{emergencyPlan.total_hotspots}</strong> hotspots identified
              ({emergencyPlan.critical_hotspots} critical)
            </p>
          </div>
        )}

        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px',
            backgroundColor: '#f3f2f1'
          }}
        >
          {/* Error Banner */}
          {chatError && (
            <div style={{
              backgroundColor: '#d4351c',
              color: 'white',
              padding: '12px 16px',
              borderRadius: '4px',
              marginBottom: '16px',
              fontSize: '14px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>
                <strong>Connection Issue:</strong> {chatError.message}
              </span>
              <button 
                onClick={() => setChatError(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '18px',
                  padding: '0 4px'
                }}
                title="Dismiss error"
              >
                ×
              </button>
            </div>
          )}

          {messages.length === 0 && (
            <div
              className="govuk-inset-text"
              style={{ backgroundColor: '#ffffff' }}
            >
              <p>
                Welcome, {roles.find(r => r.id === selectedRole)?.title}.
                I'm here to assist with emergency response planning for {city}.
              </p>
              <p>
                Ask me about priorities, resource allocation, communication strategies,
                or any aspect of the emergency response plan.
              </p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={msg.id || idx}
              style={{
                marginBottom: '16px',
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
              }}
            >
              <div
                style={{
                  maxWidth: '80%',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  backgroundColor: msg.role === 'user' ? '#1d70b8' : '#ffffff',
                  color: msg.role === 'user' ? '#ffffff' : '#0b0c0c',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}
              >
                <p className={GOVUK_CLASSES.body.s} style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </p>
                <p
                  style={{
                    margin: '4px 0 0 0',
                    fontSize: '11px',
                    opacity: 0.7
                  }}
                >
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div style={{ textAlign: 'center', padding: '16px' }}>
              <span className="govuk-body" style={{ color: '#505a5f' }}>
                Analysing...
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Actions */}
        <div
          style={{
            padding: '12px 24px',
            borderTop: '1px solid #b1b4b6',
            backgroundColor: '#f8f9fa',
            display: 'flex',
            gap: '8px',
            flexWrap: 'wrap'
          }}
        >
          <button
            onClick={() => sendMessage('Generate strategy')}
            disabled={isLoading}
            className="govuk-button govuk-button--start"
            style={{
              marginTop: 0,
              marginBottom: 0,
              fontSize: '14px',
              padding: '8px 16px',
              background: 'linear-gradient(135deg, #00703c, #005a30)',
              fontWeight: '600'
            }}
          >
            Generate Strategy
            <svg
              className="govuk-button__start-icon"
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="16"
              viewBox="0 0 33 40"
              aria-hidden="true"
              focusable="false"
              style={{ marginLeft: '4px' }}
            >
              <path fill="currentColor" d="M0 0h13l20 20-20 20H0l20-20z" />
            </svg>
          </button>
          <button
            onClick={() => sendMessage('What are the critical priorities?')}
            disabled={isLoading}
            className="govuk-button govuk-button--secondary"
            style={{
              marginTop: 0,
              marginBottom: 0,
              fontSize: '13px',
              padding: '6px 12px'
            }}
          >
            Priorities
          </button>
          <button
            onClick={() => sendMessage('Who should I contact?')}
            disabled={isLoading}
            className="govuk-button govuk-button--secondary"
            style={{
              marginTop: 0,
              marginBottom: 0,
              fontSize: '13px',
              padding: '6px 12px'
            }}
          >
            Personnel
          </button>
          <button
            onClick={() => sendMessage('What resources do we need?')}
            disabled={isLoading}
            className="govuk-button govuk-button--secondary"
            style={{
              marginTop: 0,
              marginBottom: 0,
              fontSize: '13px',
              padding: '6px 12px'
            }}
          >
            Resources
          </button>
        </div>

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div
            style={{
              padding: '12px 24px',
              borderTop: '1px solid #b1b4b6',
              backgroundColor: '#ffffff'
            }}
          >
            <p className={GOVUK_CLASSES.body.s} style={{ margin: '0 0 8px 0', fontWeight: 'bold' }}>
              Suggested questions:
            </p>
            {suggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(suggestion)}
                className="govuk-button govuk-button--secondary"
                style={{
                  marginTop: '4px',
                  marginRight: '8px',
                  marginBottom: '4px',
                  padding: '8px 12px',
                  fontSize: '14px',
                  display: 'inline-block'
                }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid #b1b4b6',
            backgroundColor: '#ffffff'
          }}
        >
          <div className={GOVUK_CLASSES.form.group} style={{ marginBottom: 0 }}>
            <label className={GOVUK_CLASSES.form.label} htmlFor="message-input">
              Your question
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <textarea
                id="message-input"
                className={GOVUK_CLASSES.form.textarea}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                rows={2}
                disabled={isLoading}
                placeholder="Ask about priorities, resources, or actions..."
                style={{ flex: 1, resize: 'none' }}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <button
                  onClick={() => sendMessage()}
                  disabled={isLoading || !inputMessage.trim()}
                  className="govuk-button"
                  style={{
                    marginTop: 0,
                    marginBottom: 0,
                    height: 'fit-content',
                    fontSize: '14px'
                  }}
                >
                  Send
                </button>
                <button
                  onClick={generateScenarioFromChat}
                  disabled={isLoading || !inputMessage.trim()}
                  className="govuk-button govuk-button--secondary"
                  style={{
                    marginTop: 0,
                    marginBottom: 0,
                    height: 'fit-content',
                    fontSize: '12px',
                    padding: '4px 8px'
                  }}
                  title="Generate an evacuation scenario from your message using AI"
                >
Generate Scenario
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
};

export default EmergencyChatPanel;
