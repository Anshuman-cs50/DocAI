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
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-16 flex flex-col items-center justify-center text-center relative z-10">
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
        
        <div className="flex flex-col sm:flex-row gap-5">
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

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-24 text-left w-full">
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
      </main>
    </div>
  );
}
