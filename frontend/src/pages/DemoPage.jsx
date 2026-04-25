import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowLeft, RefreshCw, Play } from 'lucide-react';

const DEMO_SEQUENCE = [
  { role: 'patient', text: "Hi, I've been having this really sharp pain in my lower back since yesterday morning. It hurts more when I bend over." },
  { role: 'model', tag: 'ASK', text: "I'm sorry to hear about your back pain. To better understand what might be going on, could you tell me if the pain radiates down your leg, or if you've experienced any numbness, tingling, or weakness?" },
  { role: 'patient', text: "No tingling or weakness, but it does sort of shoot down into my right buttock sometimes. I took some ibuprofen but it didn't do much." },
  { role: 'model', tag: 'SEARCH', text: "patient history for chronic back issues, kidney function, and recent medications" },
  { role: 'system', text: "Search Result injected: \"Patient has CKD Stage 2 (eGFR 68). Prior note from Dr. Smith: NSAIDs including ibuprofen are contraindicated due to kidney status. Recommends acetaminophen or topical agents for musculoskeletal pain.\"" },
  { role: 'model', tag: 'ANSWER', text: "Thank you for sharing that. Based on your symptoms of pain radiating to the buttock without numbness or weakness, this sounds like it could be a muscle strain or early sciatica.\n\nHowever, I noticed in your medical records that you have Stage 2 Chronic Kidney Disease. **Ibuprofen (an NSAID) is strictly contraindicated for you**, as it can further damage your kidneys. Please stop taking the ibuprofen immediately. For pain relief, acetaminophen (Tylenol) is much safer for your kidneys, or you can try a warm compress on the area." },
  { role: 'patient', text: "Oh wow, I completely forgot about the ibuprofen rule from my kidney doctor. Thank you. How much Tylenol can I take?" },
  { role: 'model', tag: 'ANSWER', text: "You're very welcome, it's easy to forget when you're in pain!\n\nFor acetaminophen (Tylenol), a typical safe dose for an adult is 500mg to 1000mg every 6 hours as needed for pain. However, do not exceed 3,000mg in a 24-hour period. Since you have CKD Stage 2, it is especially important to stay within these limits and ensure you stay well hydrated." },
  { role: 'patient', text: "Okay, I'll switch to Tylenol. Should I be worried about this back pain though? Could it be my kidneys failing?" },
  { role: 'model', tag: 'SEARCH', text: "typical presentation of kidney pain vs musculoskeletal pain" },
  { role: 'system', text: "Search Result injected: \"Kidney pain (renal colic/pyelonephritis) typically presents as deep, dull ache in the flank/costovertebral angle, accompanied by urinary symptoms, fever, or nausea. Worsening with bending is a hallmark of mechanical musculoskeletal back pain.\"" },
  { role: 'model', tag: 'ANSWER', text: "That is a very understandable concern. However, pain that worsens specifically when you bend over, and pain that radiates into the buttock, are classic signs of a mechanical or muscular issue in the back.\n\nPain coming directly from the kidneys is usually located higher up in the back (the flank), feels like a deep, dull ache, and is often accompanied by changes in urination, fever, or nausea. It does not typically change much when you bend your spine.\n\nSo this presentation strongly points to a musculoskeletal strain rather than kidney failure." },
  { role: 'patient', text: "That is a huge relief. Thank you DocAI. I'll stick to Tylenol and rest." },
  { role: 'model', tag: 'ANSWER', text: "I'm glad I could put your mind at ease. Rest, gentle stretching when comfortable, and the acetaminophen should help. If the pain persists for more than a few weeks, or if you develop new symptoms like numbness or urinary incontinence, please schedule an in-person visit. Take care!" }
];

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

export default function DemoPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [demoIndex, setDemoIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!isPlaying) return;
    
    if (demoIndex >= DEMO_SEQUENCE.length) {
      setIsPlaying(false);
      return;
    }

    const nextMsg = DEMO_SEQUENCE[demoIndex];
    let timeoutId;

    if (nextMsg.role === 'patient' || nextMsg.role === 'system') {
      timeoutId = setTimeout(() => {
        setMessages(prev => [...prev, { ...nextMsg, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
        setDemoIndex(idx => idx + 1);
      }, 1500);
    } else if (nextMsg.role === 'model') {
      timeoutId = setTimeout(() => {
        setMessages(prev => [...prev, { ...nextMsg, isTyping: true, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
      }, 800); // slight delay before model starts typing
    }

    return () => clearTimeout(timeoutId);
  }, [demoIndex, isPlaying]);

  const handleTypewriterComplete = () => {
    setMessages(prev => {
      const newArr = [...prev];
      const lastIdx = newArr.length - 1;
      if (newArr[lastIdx]) newArr[lastIdx].isTyping = false;
      return newArr;
    });
    // advance sequence
    setDemoIndex(idx => idx + 1);
  };

  const getTagColor = (tag) => {
    switch(tag) {
      case 'SEARCH': return 'bg-slateBlue text-medicalBlue border border-medicalBlue/20';
      case 'ASK': return 'bg-accent/10 text-accent border border-accent/20';
      case 'ANSWER': return 'bg-successGreen/10 text-successGreen border border-successGreen/20';
      default: return 'bg-gray-200 text-gray-700';
    }
  };

  const startDemo = () => {
    setMessages([]);
    setDemoIndex(0);
    setIsPlaying(true);
  };

  const getTourGuideContent = () => {
    if (!isPlaying && messages.length === 0) return { title: "Welcome", text: "Click 'Start Demo' to see the ReAct loop in action." };
    if (!isPlaying && messages.length > 0) return { title: "Simulation Complete", text: "You've seen the Agentic architecture in action! Head to the Login page or deploy this to Vercel." };
    
    switch (demoIndex) {
      case 1: return { title: "Step 1: Patient Input", text: "The patient inputs their symptom." };
      case 2: return { title: "Step 2: AI Gathers Context", text: "Notice how DocAI doesn't just guess. It autonomously decides to [ASK] a targeted follow-up question to gather more context." };
      case 4: return { title: "Step 3: Semantic Search", text: "Now DocAI uses BioBERT to semantically [SEARCH] the patient's medical history for relevant contraindications." };
      case 5: return { title: "Step 4: Context Injection", text: "The search results are injected into the hidden system prompt." };
      case 6: return { title: "Step 5: Precision Answer", text: "Finally, DocAI synthesizes the live symptoms with the historical database to provide a safe, personalized [ANSWER]." };
      default: 
        if (demoIndex > 6) return { title: "Ongoing Evaluation", text: "The agent continues to use this ReAct framework to guide the conversation safely." };
        return null;
    }
  };

  const tourContent = getTourGuideContent();

  return (
    <div className="h-screen flex flex-col bg-background font-sans relative">
      <div className="absolute inset-0 bg-watermark pointer-events-none z-0 opacity-50"></div>

      {/* Floating Tour Guide */}
      {tourContent && (
        <div className="absolute bottom-24 right-8 z-50 w-72 bg-white border border-medicalCyan rounded-xl shadow-2xl overflow-hidden animate-[fade-in-up_0.3s_ease-out]">
          <div className="bg-medicalCyan/20 px-4 py-2 border-b border-medicalCyan/30 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-medicalBlue animate-pulse"></span>
            <span className="font-mono text-xs font-bold text-medicalBlue uppercase tracking-wider">Tour Guide</span>
          </div>
          <div className="p-4">
            <h4 className="font-bold text-textMain text-sm mb-1">{tourContent.title}</h4>
            <p className="text-xs text-textMuted leading-relaxed">{tourContent.text}</p>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b border-slateBlue/30 p-4 flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/')} className="p-2 text-textMuted hover:text-medicalBlue hover:bg-medicalCyan rounded-lg transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="font-serif text-xl text-medicalBlue flex items-center gap-2">
              <Activity size={18} /> Simulation Mode
            </h1>
            <div className="font-mono text-xs text-textMuted uppercase flex items-center gap-2">
              <span>Margaret Osei (P-8472)</span>
              <span className="w-1 h-1 rounded-full bg-slateBlue"></span>
              <span className={isPlaying ? 'text-accent animate-pulse' : 'text-medicalBlue'}>
                {isPlaying ? 'Running Sequence...' : (messages.length > 0 ? 'Simulation Complete' : 'Ready')}
              </span>
            </div>
          </div>
        </div>
        {!isPlaying && messages.length === 0 && (
          <button onClick={startDemo} className="px-4 py-2 bg-medicalBlue text-white font-medium rounded-lg hover:bg-medicalBlue/90 flex items-center gap-2 transition-transform hover:scale-105">
            <Play size={16} /> Start Demo
          </button>
        )}
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 z-10 hide-scrollbar pb-32">
        {messages.length === 0 && !isPlaying && (
          <div className="h-full flex flex-col items-center justify-center opacity-70">
            <Activity className="text-medicalBlue mb-4" size={48} />
            <p className="font-sans text-lg text-textMain mb-2">Welcome to the DocAI Agent Demo</p>
            <p className="text-textMuted text-sm max-w-md text-center leading-relaxed">
              Click the button above to watch how DocAI autonomously searches a patient's historical records to prevent a dangerous drug interaction.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex flex-col w-full max-w-4xl mx-auto ${msg.role === 'patient' ? 'items-end' : msg.role === 'system' ? 'items-center my-6' : 'items-start'}`}>
            
            {msg.role === 'system' ? (
              <div className="bg-medicalCyan/50 border border-medicalTeal/20 px-4 py-2 rounded-md font-mono text-xs text-medicalBlue w-full max-w-2xl text-center shadow-sm">
                {msg.text}
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-1.5 px-1">
                  <span className={`font-mono text-[10px] uppercase font-bold tracking-wider ${msg.role === 'patient' ? 'text-medicalBlue' : 'text-accent'}`}>
                    {msg.role === 'patient' ? 'Margaret O.' : 'DocAI'}
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
                      <TypewriterText text={msg.text} onComplete={handleTypewriterComplete} />
                    ) : (
                      msg.text
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        ))}
        {isPlaying && demoIndex < DEMO_SEQUENCE.length && DEMO_SEQUENCE[demoIndex].role === 'model' && !messages.find(m => m === DEMO_SEQUENCE[demoIndex]) && (
           <div className="flex flex-col w-full max-w-4xl mx-auto items-start animate-pulse mt-6">
             <div className="p-4 rounded-2xl bg-white border border-slateBlue/40 rounded-tl-sm flex items-center gap-2">
               <RefreshCw size={16} className="text-accent animate-spin" />
               <span className="font-mono text-xs text-textMuted">DocAI is thinking...</span>
             </div>
           </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area (Disabled for Demo) */}
      <footer className="bg-white border-t border-slateBlue/30 p-4 md:p-6 z-10 shrink-0">
        <div className="max-w-4xl mx-auto relative flex items-center opacity-50 cursor-not-allowed">
          <textarea
            placeholder="Input disabled during simulation playback..."
            className="w-full bg-background border border-slateBlue/50 rounded-xl py-4 pl-4 pr-16 font-sans text-textMain placeholder-textMuted resize-none cursor-not-allowed"
            rows="2"
            disabled
          ></textarea>
        </div>
      </footer>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}} />
    </div>
  );
}
