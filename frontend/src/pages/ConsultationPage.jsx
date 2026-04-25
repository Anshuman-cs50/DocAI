import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, ArrowLeft, Database, Activity, RefreshCw } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';

const TypewriterText = ({ text, delay = 18, onComplete }) => {
  const [displayed, setDisplayed] = useState("");
  const index = useRef(0);

  useEffect(() => {
    index.current = 0;
    setDisplayed("");
    
    if (!text) {
      onComplete?.();
      return;
    }

    const intervalId = setInterval(() => {
      if (index.current < text.length) {
        setDisplayed((prev) => prev + text.charAt(index.current));
        index.current += 1;
      } else {
        clearInterval(intervalId);
        onComplete?.();
      }
    }, delay);

    return () => clearInterval(intervalId);
  }, [text, delay]);

  return <span>{displayed}</span>;
};

export default function ConsultationPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [status, setStatus] = useState("Loading...");
  const [consultationInfo, setConsultationInfo] = useState(null);
  const [isActive, setIsActive] = useState(true);
  
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const savedUser = localStorage.getItem('docai_user');
    if (!savedUser) {
      navigate('/login');
      return;
    }
    setUser(JSON.parse(savedUser));
    
    // Fetch History
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const [expandedSystemMessages, setExpandedSystemMessages] = useState({});
  const toggleSystemMessage = (idx) => {
    setExpandedSystemMessages(prev => ({ ...prev, [idx]: !prev[idx] }));
  };
  const SYSTEM_PREVIEW_CHARS = 180;

  const parseResponse = (rawText, timestamp, isTyping) => {
    const parts = [];
    const regex = /\[(SEARCH|ASK|ANSWER|SYSTEM)\]([\s\S]*?)(?=\[(SEARCH|ASK|ANSWER|SYSTEM)\]|$)/g;
    let match;
    let found = false;
    
    while ((match = regex.exec(rawText)) !== null) {
      found = true;
      const tag = match[1];
      const text = match[2].trim();
      
      if (tag === 'SYSTEM') {
        parts.push({
          role: 'system',
          text: text,
          timestamp: timestamp
        });
      } else {
        parts.push({
          role: 'model',
          tag: tag,
          text: text,
          timestamp: timestamp,
          isTyping: isTyping && tag === 'ANSWER'
        });
      }
    }
    
    if (!found) {
      parts.push({
        role: 'model',
        tag: 'ANSWER',
        text: rawText,
        timestamp: timestamp,
        isTyping: isTyping
      });
    }
    return parts;
  };

  const fetchHistory = async () => {
    try {
      setStatus("Loading history...");
      const res = await fetch(`${API_BASE_URL}/get_consultation_history/${id}`);
      if (res.ok) {
        const data = await res.json();
        setConsultationInfo(data.consultation);
        
        // Let's check if it's active from the user profile since get_consultation_history doesn't return is_active directly.
        // Or we could have added it. For now, assume it's active unless we check profile.
        
        const mappedMessages = [];
        data.timeline.forEach(item => {
          mappedMessages.push({
            role: 'patient',
            text: item.user_query,
            timestamp: new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          });
          
          const parts = parseResponse(
            item.model_response || "", 
            new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), 
            false
          );
          mappedMessages.push(...parts);
        });
        
        setMessages(mappedMessages);
        
        // Fetch profile to verify if active
        const savedUser = JSON.parse(localStorage.getItem('docai_user'));
        const profRes = await fetch(`${API_BASE_URL}/get_user_profile/${savedUser.id}`);
        if (profRes.ok) {
           const profData = await profRes.json();
           const thisConsult = profData.consultations.find(c => c.id == id);
           if (thisConsult && thisConsult.is_active === false) {
             setIsActive(false);
             setStatus("Session Ended");
           } else {
             setStatus("Awaiting Input");
           }
        } else {
           setStatus("Awaiting Input");
        }
      } else {
        alert("Consultation not found");
        navigate('/dashboard');
      }
    } catch (e) {
      console.error(e);
      setStatus("Error loading.");
    }
  };

  const handleSend = async () => {
    if (!inputText.trim() || status === 'Processing' || !isActive) return;
    
    const query = inputText;
    setInputText("");
    
    const newMsg = {
      role: 'patient',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    
    setMessages(prev => [...prev, newMsg]);
    setStatus("Processing");

    try {
      const res = await fetch(`${API_BASE_URL}/consult`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          consultation_id: id,
          user_query: query
        })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        const parts = parseResponse(
          data.response || "", 
          new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), 
          true
        );
        setMessages(prev => [...prev, ...parts]);
      } else {
        alert("Error from AI: " + data.error);
        setStatus("Awaiting Input");
      }
    } catch (e) {
      console.error(e);
      setStatus("Awaiting Input");
    }
  };

  const handleTypewriterComplete = (index) => {
    setMessages(prev => prev.map((msg, i) => i === index ? { ...msg, isTyping: false } : msg));
    setStatus("Awaiting Input");
  };

  const getTagColor = (tag) => {
    switch(tag) {
      case 'SEARCH': return 'bg-slateBlue text-medicalBlue border border-medicalBlue/20';
      case 'ASK': return 'bg-accent/10 text-accent border border-accent/20';
      case 'ANSWER': return 'bg-successGreen/10 text-successGreen border border-successGreen/20';
      default: return 'bg-gray-200 text-gray-700';
    }
  };

  return (
    <div className="h-screen flex flex-col bg-background font-sans relative">
      <div className="absolute inset-0 bg-watermark pointer-events-none z-0"></div>

      {/* Header */}
      <header className="bg-white border-b border-slateBlue/30 p-4 flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/dashboard')} className="p-2 text-textMuted hover:text-medicalBlue hover:bg-medicalCyan rounded-lg transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="font-serif text-xl text-medicalBlue flex items-center gap-2">
              <Activity size={18} /> {consultationInfo?.heading || `Consultation #${id}`}
            </h1>
            <div className="font-mono text-xs text-textMuted uppercase flex items-center gap-2">
              <span>{user?.name}</span>
              <span className="w-1 h-1 rounded-full bg-slateBlue"></span>
              <span className={status === 'Processing' ? 'text-accent animate-pulse' : 'text-successGreen'}>
                {isActive ? status : 'Ended'}
              </span>
            </div>
          </div>
        </div>
        {!isActive && (
          <div className="px-3 py-1 bg-slateBlue/20 text-textMuted text-xs font-bold uppercase rounded-full">
            Read Only
          </div>
        )}
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 z-10 hide-scrollbar">
        {messages.length === 0 && !status.includes('Loading') && (
          <div className="h-full flex flex-col items-center justify-center opacity-50">
            <Database className="text-medicalBlue mb-4" size={48} />
            <p className="font-mono text-sm text-textMain">Start the conversation...</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex flex-col w-full max-w-4xl mx-auto ${msg.role === 'patient' ? 'items-end' : msg.role === 'system' ? 'items-center my-6' : 'items-start'}`}>
            {msg.role === 'system' ? (
              <div className="bg-medicalCyan/50 border border-medicalTeal/20 px-4 py-3 rounded-md font-mono text-xs text-medicalBlue w-full max-w-2xl shadow-sm">
                <div className="font-bold text-[10px] uppercase tracking-widest mb-2 opacity-60">⚡ Search Results Injected</div>
                <p className="whitespace-pre-wrap leading-relaxed">
                  {expandedSystemMessages[idx] || msg.text.length <= SYSTEM_PREVIEW_CHARS
                    ? msg.text
                    : msg.text.slice(0, SYSTEM_PREVIEW_CHARS) + '…'}
                </p>
                {msg.text.length > SYSTEM_PREVIEW_CHARS && (
                  <button
                    onClick={() => toggleSystemMessage(idx)}
                    className="mt-2 text-[10px] font-bold text-medicalBlue/70 hover:text-medicalBlue underline underline-offset-2 transition-colors"
                  >
                    {expandedSystemMessages[idx] ? 'Show less ▲' : 'Show more ▼'}
                  </button>
                )}
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-1.5 px-1">
                  <span className={`font-mono text-[10px] uppercase font-bold tracking-wider ${msg.role === 'patient' ? 'text-medicalBlue' : 'text-accent'}`}>
                    {msg.role === 'patient' ? user?.name : 'DocAI'}
                  </span>
                  <span className="font-mono text-[10px] text-textMuted">{msg.timestamp}</span>
                </div>
                
                <div className={`p-4 rounded-2xl shadow-sm border ${
                  msg.role === 'patient' 
                    ? 'bg-medicalBlue text-white border-medicalBlue rounded-tr-sm' 
                    : 'bg-white text-textMain border-slateBlue/40 rounded-tl-sm'
                }`}>
                  {msg.role === 'model' && (
                    <div className={`inline-block font-mono text-[10px] font-bold px-2 py-0.5 rounded-md mb-2 shadow-sm ${getTagColor(msg.tag)}`}>
                      [{msg.tag}]
                    </div>
                  )}
                  <div className="font-sans text-sm leading-relaxed whitespace-pre-wrap">
                    {msg.isTyping ? (
                      <TypewriterText text={msg.text} onComplete={() => handleTypewriterComplete(idx)} />
                    ) : (
                      msg.text
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        ))}
        {status === 'Processing' && (
           <div className="flex flex-col w-full max-w-4xl mx-auto items-start animate-pulse">
             <div className="p-4 rounded-2xl bg-white border border-slateBlue/40 rounded-tl-sm flex items-center gap-2">
               <RefreshCw size={16} className="text-accent animate-spin" />
               <span className="font-mono text-xs text-textMuted">DocAI is thinking...</span>
             </div>
           </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t border-slateBlue/30 p-4 md:p-6 z-10 shrink-0">
        <div className="max-w-4xl mx-auto relative flex items-center">
          <textarea
            placeholder={isActive ? "Describe your symptoms or ask a medical question..." : "This consultation has ended."}
            className="w-full bg-background border border-slateBlue/50 rounded-xl py-4 pl-4 pr-16 font-sans text-textMain placeholder-textMuted focus:outline-none focus:border-medicalBlue focus:ring-1 focus:ring-medicalBlue resize-none shadow-inner"
            rows="2"
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            disabled={status === 'Processing' || !isActive}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          ></textarea>
          <button 
            onClick={handleSend}
            disabled={status === 'Processing' || !isActive || !inputText.trim()}
            className="absolute right-3 bottom-3 p-2 bg-medicalBlue hover:bg-medicalBlue/90 text-white rounded-lg shadow-sm transition-transform hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
          >
            <Send size={18} />
          </button>
        </div>
      </footer>
    </div>
  );
}
