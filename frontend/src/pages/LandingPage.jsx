import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ShieldCheck, Database, BrainCircuit, ArrowRight, Play } from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background text-textMain flex flex-col font-sans relative overflow-hidden">
      {/* Abstract Background Design */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-medicalCyan/40 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-accent/10 rounded-full blur-[100px] pointer-events-none"></div>
      <div className="absolute inset-0 bg-grid pointer-events-none opacity-50"></div>
      
      {/* Navigation */}
      <nav className="w-full max-w-7xl mx-auto px-6 py-6 flex justify-between items-center relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-medicalBlue text-white rounded-xl flex justify-center items-center shadow-lg">
            <Activity size={24} />
          </div>
          <h1 className="font-serif text-3xl text-medicalBlue">DocAI</h1>
        </div>
        <div className="flex gap-4">
          <button onClick={() => navigate('/login')} className="px-5 py-2.5 text-medicalBlue font-medium hover:bg-slateBlue/50 rounded-lg transition-colors">
            Login
          </button>
          <button onClick={() => navigate('/demo')} className="px-5 py-2.5 bg-medicalBlue text-white font-medium rounded-lg shadow-md hover:bg-medicalBlue/90 transition-transform hover:scale-105 flex items-center gap-2">
            Watch Demo <Play size={16} />
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="w-full relative z-10 flex flex-col items-center">
        
        {/* Full-Height Hero Content */}
        <div className="w-full max-w-7xl mx-auto px-6 flex flex-col items-center justify-center text-center min-h-[calc(100vh-88px)]">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-medicalCyan text-medicalBlue font-mono text-xs uppercase tracking-wide mb-8 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-medicalBlue animate-pulse"></span>
            ReAct Agent Architecture
          </div>
          
          <h2 className="font-serif text-5xl md:text-7xl text-textMain max-w-4xl leading-tight mb-6">
            Agentic Medical Consultation <br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-medicalBlue to-accent">Assistant</span>
          </h2>
          
          <p className="text-lg md:text-xl text-textMuted max-w-2xl mb-12 leading-relaxed">
            DocAI replaces naive static RAG with a dynamic ReAct Agent architecture, utilizing Google's MedGemma-4b model to interact with patients and autonomously query historical health records.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-5 mb-16">
            <button 
              onClick={() => navigate('/login')}
              className="px-8 py-4 bg-accent hover:bg-accentHover text-white font-bold rounded-xl shadow-lg transition-all hover:scale-105 hover:shadow-xl flex items-center justify-center gap-2 text-lg"
            >
              Try Live Action <ArrowRight size={20} />
            </button>
            <button 
              onClick={() => navigate('/demo')}
              className="px-8 py-4 bg-white border-2 border-slateBlue hover:border-medicalBlue text-medicalBlue font-bold rounded-xl shadow-sm transition-all hover:bg-slateBlue/30 flex items-center justify-center gap-2 text-lg"
            >
              View Simulation
            </button>
          </div>
        </div>

        {/* Animated Workflow Section */}
        <div className="w-full bg-slateBlue/10 py-24 border-y border-slateBlue/30 relative overflow-hidden">
          <div className="max-w-7xl mx-auto px-6 flex flex-col items-center text-center">
            <h3 className="font-serif text-3xl text-textMain mb-4">How DocAI Thinks</h3>
            <p className="text-textMuted mb-16 max-w-2xl">Unlike basic chatbots, DocAI actively reasons about your symptoms and autonomously decides when to search your health history.</p>

            <div className="relative w-full max-w-5xl flex flex-col md:flex-row justify-between items-center gap-12 md:gap-4 px-4">
              
              {/* Connecting Line (Desktop) */}
              <div className="hidden md:block absolute top-1/2 left-24 right-24 h-0.5 bg-slateBlue/50 -translate-y-1/2 z-0"></div>
              
              {/* Animated Dot (Desktop) */}
              <div className="hidden md:block absolute top-1/2 left-24 w-4 h-4 bg-accent rounded-full -translate-y-1/2 -mt-2 shadow-[0_0_15px_rgba(255,107,107,0.8)] z-10 animate-[travel_6s_ease-in-out_infinite]"></div>

              {/* Step 1: User Input */}
              <div className="relative z-10 flex flex-col items-center bg-white p-6 rounded-2xl shadow-md border border-medicalCyan/50 w-full md:w-64">
                <div className="w-16 h-16 bg-medicalCyan/30 text-medicalBlue rounded-full flex items-center justify-center mb-4 border-2 border-medicalCyan">
                  <span className="text-2xl">💬</span>
                </div>
                <h4 className="font-bold text-textMain mb-2">1. You Ask</h4>
                <p className="text-sm text-textMuted leading-relaxed text-center">"I've had a headache since yesterday."</p>
              </div>

              {/* Step 2: Agent Reasoning */}
              <div className="relative z-10 flex flex-col items-center bg-white p-6 rounded-2xl shadow-xl border-2 border-medicalBlue w-full md:w-72 transform md:-translate-y-4">
                <div className="absolute -top-3 px-3 py-1 bg-medicalBlue text-white text-[10px] font-bold rounded-full uppercase tracking-wider">ReAct Loop</div>
                <div className="w-20 h-20 bg-medicalBlue text-white rounded-full flex items-center justify-center mb-4 shadow-lg animate-[pulse_3s_ease-in-out_infinite]">
                  <BrainCircuit size={36} />
                </div>
                <h4 className="font-bold text-textMain mb-2 text-lg">2. AI Reasons & Searches</h4>
                <p className="text-sm text-textMuted leading-relaxed text-center">DocAI detects the symptom and searches the vector database for your blood pressure history.</p>
              </div>

              {/* Step 3: Personalized Response */}
              <div className="relative z-10 flex flex-col items-center bg-white p-6 rounded-2xl shadow-md border border-medicalCyan/50 w-full md:w-64">
                <div className="w-16 h-16 bg-successGreen/20 text-successGreen rounded-full flex items-center justify-center mb-4 border-2 border-successGreen/50">
                  <span className="text-2xl">✨</span>
                </div>
                <h4 className="font-bold text-textMain mb-2">3. Precision Answer</h4>
                <p className="text-sm text-textMuted leading-relaxed text-center">"I see your hypertension is active. Let's check your recent vitals..."</p>
              </div>

            </div>
          </div>
          
          <style dangerouslySetInnerHTML={{__html: `
            @keyframes travel {
              0% { left: 10%; opacity: 0; }
              10% { opacity: 1; }
              40% { left: 50%; transform: translate(-50%, -50%) scale(1.5); }
              60% { left: 50%; transform: translate(-50%, -50%) scale(1.5); }
              90% { opacity: 1; }
              100% { left: 90%; opacity: 0; }
            }
          `}} />
        </div>

        {/* Feature Highlights */}
        <div className="w-full max-w-7xl mx-auto px-6 py-24 text-left">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slateBlue/50 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-medicalCyan text-medicalBlue rounded-lg flex items-center justify-center mb-4">
                <BrainCircuit size={24} />
              </div>
              <h3 className="font-serif text-xl text-textMain mb-2">Autonomous ReAct Loop</h3>
              <p className="text-textMuted text-sm leading-relaxed">The AI natively evaluates the conversation and decides whether to search medical history or answer directly, minimizing hallucinations.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slateBlue/50 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-medicalCyan text-medicalBlue rounded-lg flex items-center justify-center mb-4">
                <Database size={24} />
              </div>
              <h3 className="font-serif text-xl text-textMain mb-2">Semantic BioBERT Search</h3>
              <p className="text-textMuted text-sm leading-relaxed">Integrates pgvector and BioBERT to perform high-speed, semantic similarity searches across a user's clinical notes.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slateBlue/50 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-medicalCyan text-medicalBlue rounded-lg flex items-center justify-center mb-4">
                <ShieldCheck size={24} />
              </div>
              <h3 className="font-serif text-xl text-textMain mb-2">Privacy-Focused Security</h3>
              <p className="text-textMuted text-sm leading-relaxed">Keeps patient data secure with decoupled architecture, running the heavy 4B model off-device while keeping the database local.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
