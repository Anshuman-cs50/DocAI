import React, { useState, useEffect, useRef } from 'react';
import { Lock, FileText, ChevronRight, X, Play, RefreshCw, Send, Search, Database, Activity } from 'lucide-react';

const DEMO_PATIENT = {
  id: "P-8472",
  name: "Margaret Osei",
  age: 64,
  conditions: [
    { name: "T2DM", active: true },
    { name: "Hypertension", active: true },
    { name: "CKD Stage 2", active: true },
    { name: "Lower Back Pain", active: true },
    { name: "Appendectomy", active: false }
  ],
  consultations: [
    { date: "5 months ago", title: "Back Pain Flare-up" },
    { date: "9 months ago", title: "CKD Incidental Finding Follow-up" },
    { date: "14 months ago", title: "Routine Diabetes and BP Check" }
  ],
  vitals: {
    bp: [138, 140, 132, 128, 134, 122, 124], // Example systolic sequence
    hr: [72, 70, 74, 68, 65, 64, 66] // Example sequence
  }
};

// Tiny Sparkline Component logic (SVG path string generator)
const generateSparkline = (data, width = 60, height = 20) => {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const points = data.map((v, i) => {
    const x = i * step;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  });
  return points.join(" ");
};

const TypewriterText = ({ text, delay = 18, onComplete }) => {
  const [displayed, setDisplayed] = useState("");
  const index = useRef(0);

  useEffect(() => {
    index.current = 0;
    setDisplayed("");
    
    if (text === "") {
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

// Main App Component
export default function DocAIWorkspace() {
  const [patient, setPatient] = useState(null);
  const [sessionActive, setSessionActive] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [status, setStatus] = useState("Idle"); // Idle, Processing, Awaiting Input
  const [showModal, setShowModal] = useState(false);
  
  // Conversation state
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);
  
  // Demo State Machine
  // 0: Initial
  // 1: Loaded Patient
  // 2: Turn 1 Patient Msg added
  // 3: Turn 1 Model Msg added (typing)
  // 4: Turn 1 Done, wait 1.5s
  // 5: Turn 2 Search Msg added
  // 6: Turn 2 Model Msg added (typing)
  // 7: Demo complete
  const [demoStage, setDemoStage] = useState(0);

  const [inputText, setInputText] = useState("");
  const [injectMode, setInjectMode] = useState("query"); // 'query' | 'search'

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, messagesEndRef]);

  // Handle Demo Sequence
  useEffect(() => {
    if (demoStage === 1) {
      const t = setTimeout(() => {
        setMessages([{ role: "patient", text: "I want to take ibuprofen for my back pain, is that okay?", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
        setDemoStage(2);
      }, 600);
      return () => clearTimeout(t);
    } 
    else if (demoStage === 2) {
      const t = setTimeout(() => {
        setStatus("Processing");
        setMessages(prev => [...prev, { role: "model", tag: "SEARCH", text: "ibuprofen use and kidney function history", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), isTyping: true }]);
        setDemoStage(3);
      }, 400);
      return () => clearTimeout(t);
    }
    // Stage 3 runs typewriter. On complete -> Stage 4.
    else if (demoStage === 4) {
      const t = setTimeout(() => {
        setMessages(prev => [...prev, { role: "system", text: "Search Result injected: \"CKD Stage 2 diagnosed 8 months ago. eGFR 68. Prior note: Ibuprofen contraindicated, switch to paracetamol.\"", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
        setDemoStage(5);
      }, 1500);
      return () => clearTimeout(t);
    }
    else if (demoStage === 5) {
      const t = setTimeout(() => {
        setStatus("Processing");
        setMessages(prev => [...prev, { role: "model", tag: "ANSWER", text: "Based on your records, ibuprofen is contraindicated for you due to your CKD Stage 2 diagnosis. Your notes from 8 months ago specifically flag this. Paracetamol is the recommended alternative for pain management.", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), isTyping: true }]);
        setDemoStage(6);
      }, 400);
      return () => clearTimeout(t);
    }
  }, [demoStage]);

  const handleTypewriterComplete = (index) => {
    setMessages(prev => prev.map((msg, i) => i === index ? { ...msg, isTyping: false } : msg));
    if (demoStage === 3) {
      setStatus("Awaiting Input");
      setDemoStage(4);
    } else if (demoStage === 6) {
      setStatus("Awaiting Input");
      setDemoStage(7);
    }
  };

  const loadPatient = () => {
    setShowModal(false);
    setPatient(DEMO_PATIENT);
    setSessionActive(true);
    setStatus("Awaiting Input");
    setDemoStage(1);
    setMessages([]);
  };

  const handleReset = () => {
    setPatient(null);
    setSessionActive(false);
    setRightPanelOpen(false);
    setStatus("Idle");
    setDemoStage(0);
    setMessages([]);
    setInputText("");
  };

  const getTagColor = (tag) => {
    switch(tag) {
      case 'SEARCH': return 'bg-slateBlue text-white';
      case 'ASK': return 'bg-accent text-white';
      case 'ANSWER': return 'bg-successGreen text-white';
      default: return 'bg-gray-600 text-white';
    }
  };

  const getStatusColor = () => {
    switch(status) {
      case 'Processing': return 'text-accent animate-pulse';
      case 'Awaiting Input': return 'text-successGreen';
      default: return 'text-gray-500';
    }
  };

  return (
    <div 
      className="flex h-screen w-full overflow-hidden text-textMain"
      style={{
        backgroundColor: '#0f1623',
        backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.8%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22 opacity=%220.02%22/%3E%3C/svg%3E")'
      }}
    >
      {/* LEFT SIDEBAR */}
      <div className="w-[280px] h-full flex flex-col border-r border-[#1f2937] bg-[#0c121e] shadow-xl z-20 shrink-0">
        <div className="p-6 pb-4 border-b border-[#1f2937]">
          <h1 className="font-serif text-3xl tracking-wide text-white mb-1">DocAI</h1>
          <div className="font-mono text-[10px] tracking-widest text-[#2a6b6b] uppercase">Developer Workspace</div>
        </div>

        <div className="p-6 flex-1 flex flex-col gap-8 overflow-y-auto">
          {/* Active Context */}
          <div className="flex flex-col gap-4">
            <h2 className="font-mono text-xs uppercase text-gray-500 tracking-wider">Active Context</h2>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-[#151f2e] border border-[#233147] rounded-md p-3">
                <span className="font-sans text-xs text-gray-400">User ID</span>
                <span className="font-mono text-sm text-white">{patient ? patient.id : "—"}</span>
              </div>
              <div className="flex items-center justify-between bg-[#151f2e] border border-[#233147] rounded-md p-3">
                <span className="font-sans text-xs text-gray-400">Consult ID</span>
                <span className="font-mono text-sm text-white">{sessionActive ? `C-${Math.floor(Math.random()*10000)}` : "—"}</span>
              </div>
            </div>

            {patient && (
              <div className="mt-2 bg-[#1b2535] border border-[#2a6b6b]/40 rounded-md p-4 animate-in slide-in-from-top-4 fade-in duration-300">
                <div className="flex justify-between items-start mb-2">
                  <div className="font-serif text-lg text-white">{patient.name}</div>
                  <div className="font-sans text-xs text-gray-400">{patient.age}y</div>
                </div>
                <div className="flex flex-wrap gap-1 mt-3">
                  {patient.conditions.filter(c => c.active).map(c => (
                    <span key={c.name} className="px-1.5 py-0.5 bg-[#2a6b6b]/20 text-[#2a6b6b] border border-[#2a6b6b]/30 rounded text-[10px] font-sans font-medium">
                      {c.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Operations */}
          <div className="flex flex-col gap-4">
            <h2 className="font-mono text-xs uppercase text-gray-500 tracking-wider">Operations</h2>
            
            <div className="space-y-1 relative before:absolute before:inset-y-0 before:left-3 before:w-px before:bg-[#1f2937]">
              
              {/* Step 1 */}
              <button 
                onClick={() => !patient && setShowModal(true)}
                className={`w-full flex items-center gap-3 p-3 rounded-md text-left transition-colors relative z-10 
                  ${patient ? 'bg-transparent text-gray-400 cursor-default' : 'bg-[#151f2e] hover:bg-[#1b2535] text-white border-l-2 border-accent'}`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${patient ? 'bg-[#1f2937]' : 'bg-accent/20 text-accent'}`}>
                  {patient ? <span className="text-xs">✓</span> : <span className="text-xs">1</span>}
                </div>
                <span className="font-sans text-sm font-medium">Simulate Patient</span>
              </button>

              {/* Step 2 */}
              <button 
                className={`w-full flex items-center gap-3 p-3 rounded-md text-left transition-colors relative z-10 
                  ${!patient ? 'opacity-50 cursor-not-allowed' : sessionActive ? 'bg-transparent text-gray-400' : 'bg-[#151f2e] border-l-2 border-accent text-white'}`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 bg-[#1f2937]`}>
                  {!patient ? <Lock size={12} className="text-gray-500" /> : sessionActive ? <span className="text-xs">✓</span> : <span className="text-xs">2</span>}
                </div>
                <span className="font-sans text-sm font-medium">New Session</span>
              </button>

              {/* Step 3 */}
              <button 
                disabled={!sessionActive}
                className={`w-full flex items-center gap-3 p-3 rounded-md text-left transition-colors relative z-10 
                  ${!sessionActive ? 'opacity-50 cursor-not-allowed' : 'bg-[#151f2e] hover:bg-[#1b2535] text-white'}`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 bg-[#1f2937]`}>
                  {!sessionActive ? <Lock size={12} className="text-gray-500" /> : <Play size={10} className="text-white" />}
                </div>
                <span className="font-sans text-sm font-medium">View Timeline</span>
              </button>
            </div>
          </div>
        </div>

        {/* Status & Reset */}
        <div className="mt-auto p-4 border-t border-[#1f2937] flex flex-col gap-4">
          <div className="flex items-center gap-2 bg-[#0c121e] px-2 py-1 rounded">
            <span className={`text-[10px] ${getStatusColor()}`}>●</span>
            <span className="font-mono text-xs text-gray-300">{status}</span>
          </div>
          <button 
            onClick={handleReset}
            className="flex items-center justify-center gap-2 w-full py-2 rounded font-sans text-xs font-medium text-gray-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
          >
            <RefreshCw size={12} /> Reset Workspace
          </button>
        </div>
      </div>

      {/* MAIN PANEL */}
      <div className="flex-1 flex flex-col relative bg-grid">
        {!sessionActive ? (
          // Empty State
          <div className="w-full h-full flex flex-col items-center justify-center relative">
            <div className="absolute inset-0 bg-watermark pointer-events-none"></div>
            <div className="relative z-10 flex flex-col items-center text-center max-w-md p-8 bg-[#0f1623]/80 backdrop-blur-sm border border-[#1f2937] rounded-xl shadow-2xl">
              <Activity className="w-16 h-16 text-[#1f2937] mb-6" />
              <h2 className="font-serif text-3xl text-white mb-3">No Active Encounter</h2>
              <p className="font-sans text-sm text-gray-400 mb-8 leading-relaxed">
                Load a patient profile to begin a consultation session and monitor the AI pipeline in real-time.
              </p>
              <button 
                onClick={() => setShowModal(true)}
                className="bg-accent hover:bg-[#b5803a] text-[#0f1623] font-sans font-semibold py-3 px-6 rounded-md shadow-lg transition-all hover:scale-105 flex items-center gap-2"
              >
                Simulate Patient <ChevronRight size={16} />
              </button>
            </div>
          </div>
        ) : (
          // Active Consultation
          <div className="flex-1 flex flex-col h-full bg-[#0a0f18]/90">
            {/* Top Panel - Conversation */}
            <div className="relative h-[60%] border-b border-[#1f2937] overflow-y-auto p-6 md:p-10 hide-scrollbar space-y-6">
              {messages.length === 0 && (
                <div className="flex items-center justify-center h-full text-gray-500 font-mono text-sm opacity-50">
                  Awaiting initial query...
                </div>
              )}
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex flex-col max-w-3xl ${msg.role === 'patient' ? 'ml-auto items-end text-right' : msg.role === 'system' ? 'mx-auto items-center text-center my-8' : 'mr-auto items-start text-left'}`}>
                  
                  {msg.role === 'system' && (
                    <div className="bg-[#1b2535] border border-accent/20 px-4 py-2 rounded-md font-mono text-xs text-gray-300 w-full shadow-md">
                      {msg.text}
                    </div>
                  )}

                  {msg.role !== 'system' && (
                    <>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`font-mono text-[10px] uppercase font-semibold ${msg.role === 'patient' ? 'text-[#2a6b6b]' : 'text-gray-400'}`}>
                          {msg.role === 'patient' ? 'Patient' : 'Model'}
                        </span>
                        <span className="font-mono text-[10px] text-gray-600">{msg.timestamp}</span>
                      </div>
                      
                      <div className={`p-4 rounded-lg shadow-md border ${msg.role === 'patient' ? 'bg-[#151f2e] border-[#233147]' : 'bg-[#0f1623] border-[#1f2937]'}`}>
                        {msg.role === 'model' && (
                          <div className={`inline-block font-mono text-[10px] font-bold px-2 py-1 rounded mb-3 mb-2 shadow-sm ${getTagColor(msg.tag)}`}>
                            [{msg.tag}]
                          </div>
                        )}
                        <div className={`font-sans text-sm leading-relaxed ${msg.role === 'patient' ? 'text-gray-200' : 'text-[#e8e4dc]'}`}>
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
              <div ref={messagesEndRef} />
            </div>

            {/* Bottom Panel - Input Component */}
            <div className="h-[40%] bg-[#0f1623] p-6 lg:p-8 flex flex-col relative z-10 shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.5)]">
              <textarea 
                placeholder="Enter patient query..."
                className="w-full flex-1 bg-[#151f2e] border border-[#233147] rounded-md p-4 font-sans text-white placeholder-gray-600 focus:outline-none focus:border-accent/50 resize-none transition-colors"
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                disabled={status === 'Processing'}
              ></textarea>
              
              <div className="mt-4 flex items-center justify-between">
                <div className="flex items-center gap-3 bg-[#151f2e] border border-[#233147] p-1.5 rounded-md">
                  <button 
                    onClick={() => setInjectMode('query')}
                    className={`px-3 py-1.5 rounded text-xs font-mono font-medium flex items-center gap-2 transition-colors ${injectMode === 'query' ? 'bg-[#0f1623] text-white shadow' : 'text-gray-500 hover:text-gray-300'}`}
                  >
                    Patient Query
                  </button>
                  <button 
                    onClick={() => setInjectMode('search')}
                    className={`px-3 py-1.5 rounded text-xs font-mono font-medium flex items-center gap-2 transition-colors ${injectMode === 'search' ? 'bg-accent/20 text-accent shadow' : 'text-gray-500 hover:text-accent/60'}`}
                  >
                    <Database size={12} /> Inject Search
                  </button>
                </div>
                
                <button className="bg-accent hover:bg-[#b5803a] text-[#0f1623] px-6 py-2.5 rounded-md font-sans text-sm font-bold flex items-center gap-2 disabled:opacity-50 transition-colors">
                  Send <Send size={14} />
                </button>
              </div>

              {/* Progress bar */}
              <div className="absolute top-0 left-0 w-full h-1 bg-[#1f2937]">
                <div className="h-full bg-accent transition-all duration-1000 w-[15%]"></div>
              </div>
              <div className="absolute top-2 left-6 right-6 flex justify-between">
                 <span className="font-mono text-[9px] text-gray-500 uppercase">Context Window</span>
                 <span className="font-mono text-[9px] text-gray-500">1,240 / 8,192 tokens</span>
              </div>
            </div>
            
            {/* Tab to open Right Panel */}
            <button 
              onClick={() => setRightPanelOpen(!rightPanelOpen)}
              className="absolute right-0 top-1/3 -translate-y-1/2 bg-[#1b2535] border border-r-0 border-[#233147] rounded-l-lg py-4 px-1.5 shadow-lg group hover:bg-[#233147] transition-colors z-20"
            >
              <div className="font-mono text-[10px] tracking-widest text-[#2a6b6b] transform -rotate-180" style={{ writingMode: 'vertical-rl' }}>
                PATIENT RECORD
              </div>
              <ChevronRight size={14} className={`mt-2 text-gray-500 transition-transform ${rightPanelOpen ? 'rotate-180' : ''}`} />
            </button>
          </div>
        )}
      </div>

      {/* RIGHT PANEL */}
      <div 
        className={`fixed right-0 top-0 h-full w-[320px] bg-[#0c121e] border-l border-[#1f2937] shadow-2xl transition-transform duration-300 ease-in-out z-30 flex flex-col`}
        style={{ transform: rightPanelOpen && sessionActive ? 'translateX(0)' : 'translateX(100%)' }}
      >
        <div className="p-5 flex justify-between items-center border-b border-[#1f2937]">
          <h2 className="font-serif text-xl text-white">Record & Vitals</h2>
          <button onClick={() => setRightPanelOpen(false)} className="text-gray-500 hover:text-white">
            <X size={18} />
          </button>
        </div>

        {patient && (
          <div className="flex-1 overflow-y-auto p-5 space-y-8">
            {/* Conditions Menu */}
            <section>
              <h3 className="font-mono text-[10px] uppercase text-gray-500 tracking-widest border-b border-[#1f2937] pb-2 mb-4">Conditions</h3>
              <div className="space-y-2">
                {patient.conditions.map(c => (
                  <div key={c.name} className="flex items-center justify-between p-2 rounded bg-[#151f2e] border border-[#233147]">
                    <span className="font-sans text-sm text-gray-200">{c.name}</span>
                    <span className={`w-2 h-2 rounded-full ${c.active ? 'bg-accent' : 'bg-gray-600'}`}></span>
                  </div>
                ))}
              </div>
            </section>

            {/* Vitals */}
            <section>
              <h3 className="font-mono text-[10px] uppercase text-gray-500 tracking-widest border-b border-[#1f2937] pb-2 mb-4">Recent Vitals</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-end mb-1">
                    <span className="font-sans text-xs text-gray-400">Blood Pressure</span>
                    <span className="font-mono text-sm text-white">124/76</span>
                  </div>
                  <svg viewBox="0 0 100 20" className="w-full h-5 stroke-current overflow-visible text-accent stroke-2 fill-none stroke-linecap-round stroke-linejoin-round">
                    <path d={`M ${generateSparkline(patient.vitals.bp, 100, 20)}`} />
                  </svg>
                </div>
                <div>
                  <div className="flex justify-between items-end mb-1">
                    <span className="font-sans text-xs text-gray-400">Heart Rate</span>
                    <span className="font-mono text-sm text-white">64 bpm</span>
                  </div>
                  <svg viewBox="0 0 100 20" className="w-full h-5 stroke-current overflow-visible text-[#2a6b6b] stroke-2 fill-none stroke-linecap-round stroke-linejoin-round">
                    <path d={`M ${generateSparkline(patient.vitals.hr, 100, 20)}`} />
                  </svg>
                </div>
              </div>
            </section>

            {/* History */}
            <section>
               <h3 className="font-mono text-[10px] uppercase text-gray-500 tracking-widest border-b border-[#1f2937] pb-2 mb-4">Consultation History</h3>
               <div className="relative border-l border-[#233147] ml-2 space-y-4 pb-4">
                 {patient.consultations.map((c, i) => (
                   <div key={i} className="pl-4 relative">
                     <span className="absolute -left-1.5 top-1.5 w-3 h-3 bg-[#0c121e] border-2 border-accent rounded-full"></span>
                     <div className="font-mono text-[10px] text-accent mb-0.5">{c.date}</div>
                     <div className="font-sans text-sm text-gray-300 leading-snug">{c.title}</div>
                   </div>
                 ))}
               </div>
            </section>
          </div>
        )}
      </div>

      {/* MODAL: Simulate Patient */}
      {showModal && (
        <div className="fixed inset-0 bg-[#0f1623]/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#151f2e] border border-[#233147] rounded-xl shadow-2xl p-6 w-full max-w-sm">
            <h2 className="font-serif text-2xl text-white mb-4">Load Patient Profile</h2>
            <div className="mb-6">
              <label className="block font-sans text-xs text-gray-400 mb-2">Select Seed Profile</label>
              <select className="w-full bg-[#0c121e] border border-[#233147] rounded p-3 text-white font-sans text-sm focus:outline-none focus:border-accent">
                <option value="p8472">Margaret Osei (P-8472)</option>
              </select>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={() => setShowModal(false)}
                className="flex-1 py-3 rounded text-gray-400 hover:text-white font-sans text-sm font-medium transition-colors border border-transparent hover:border-[#233147]"
              >
                Cancel
              </button>
              <button 
                onClick={loadPatient}
                className="flex-[2] py-3 rounded bg-accent text-[#0f1623] hover:bg-[#b5803a] font-sans text-sm font-bold transition-transform hover:scale-105"
              >
                Launch Simulation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
