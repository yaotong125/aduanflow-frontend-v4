import React, { useState, useRef, useEffect } from 'react';
import { apiFetch } from '../config';
import { COPILOT_SUGGESTIONS, COPILOT_RESPONSES } from '../data/mockData';
import { TASKFORCE_TEAM } from '../data/taskforceData';

const TASKFORCE_SUGGESTIONS = TASKFORCE_TEAM.commandPrompts;

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3 bg-slate-50 border-l-3 border-blue-500 rounded-xl max-w-[80%]">
      <span className="typing-dot animate-bounce-dot" />
      <span className="typing-dot animate-bounce-dot" />
      <span className="typing-dot animate-bounce-dot" />
    </div>
  );
}

function renderBoldLine(line) {
  const parts = line.split(/\*\*(.*?)\*\*/g);
  return parts.map((part, j) =>
    j % 2 === 1 ? <strong key={j}>{part}</strong> : part
  );
}

function BotMessage({ text }) {
  return (
    <div className="whitespace-pre-line bg-slate-50 text-slate-700 border-l-3 border-blue-500 rounded-xl px-4 py-3 max-w-[85%]">
      {text.split('\n').map((line, i) => (
        <p key={i} className={`${i > 0 ? 'mt-1' : ''} text-sm`}>
          {renderBoldLine(line)}
        </p>
      ))}
    </div>
  );
}

export default function Copilot({ onViewCase }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "Hello! I'm the AduanFlow AI Copilot. The AI Banking Dispute Automation Taskforce is now integrated, so I can help with dispute pipeline monitoring, taskforce coverage, escalations, and remediation planning.",
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = (text) => {
    const query = text || input.trim();
    if (!query) return;

    setMessages((prev) => [...prev, { role: 'user', text: query }]);
    setInput('');
    setIsTyping(true);

    apiFetch('/api/copilot/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('API Error');
        return res.json();
      })
      .then((data) => {
        setMessages((prev) => [...prev, { role: 'assistant', text: data.reply }]);
        setIsTyping(false);
      })
      .catch(() => {
        const response =
          COPILOT_RESPONSES[query] || {
            text:
              "I understand you're asking about: \"" +
              query +
              '".\n\nI can now help with:\n- Case statuses\n- SLA tracking\n- Investigator workload\n- Taskforce coverage\n- High-risk dispute escalation\n- Manual review remediation plans',
          };
        setMessages((prev) => [...prev, { role: 'assistant', text: response.text }]);
        setIsTyping(false);
      });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-9.5rem)] md:h-[calc(100vh-9rem)] max-w-4xl mx-auto min-h-0 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 mb-3">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-bold text-slate-900">AI Copilot</h2>
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
            <span className="w-2 h-2 rounded-full bg-green-400" />
            Online
          </span>
        </div>
        <p className="text-xs md:text-sm text-slate-500 mt-0.5">Natural language interface for dispute operations and taskforce orchestration</p>
      </div>

      {/* Taskforce Integration Banner */}
      <div className="shrink-0 mb-3 rounded-xl border border-blue-100 bg-blue-50/80 p-3 text-xs md:text-sm text-blue-900 shadow-xs">
        <p className="font-semibold text-blue-950">Taskforce integration active</p>
        <p className="mt-0.5 text-blue-800/90 text-xs">
          Ask about squad ownership, escalation strategy, manual review remediation, or high-risk dispute watchlists.
        </p>
      </div>

      {/* Main Chat Card */}
      <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-card overflow-hidden flex flex-col min-h-0">
        {/* Messages scroll area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-5 space-y-4 min-h-0">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'user' ? (
                <div className="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm text-white bg-gradient-to-r from-blue-500 to-blue-600 shadow-sm">
                  <p>{msg.text}</p>
                </div>
              ) : msg.role === 'assistant' ? (
                <BotMessage text={msg.text} />
              ) : null}
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <TypingIndicator />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {messages.length <= 1 && !isTyping && (
          <div className="shrink-0 px-4 md:px-5 pb-3 pt-1 space-y-2 border-t border-slate-50 bg-slate-50/40">
            <div>
              <p className="text-[11px] font-medium text-slate-400 mb-1.5">Core suggestions:</p>
              <div className="flex flex-wrap gap-1.5">
                {COPILOT_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSend(s)}
                    className="text-xs px-2.5 py-1 rounded-full border border-slate-200 bg-white text-slate-600 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600 transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[11px] font-medium text-slate-400 mb-1.5">Taskforce prompts:</p>
              <div className="flex flex-wrap gap-1.5">
                {TASKFORCE_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSend(s)}
                    className="text-xs px-2.5 py-1 rounded-full border border-blue-100 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Footer / Input Bar */}
        <div className="shrink-0 border-t border-slate-100 p-3 md:p-4 bg-white">
          <div className="flex items-center gap-2 md:gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about cases, escalations, squads, or remediation..."
              className="flex-1 px-4 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isTyping}
              className="px-4 md:px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-xs"
            >
              Send
            </button>
          </div>
          <p className="text-[10px] text-slate-400 mt-1 text-right">Press Enter to send</p>
        </div>
      </div>
    </div>
  );
}
