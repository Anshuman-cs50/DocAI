import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Plus, History, LogOut, CheckCircle, Clock, HeartPulse, ChevronRight } from 'lucide-react';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('docai_user');
    if (!savedUser) {
      navigate('/login');
      return;
    }
    const parsedUser = JSON.parse(savedUser);
    setUser(parsedUser);
    fetchProfile(parsedUser.id);
  }, [navigate]);

  const fetchProfile = async (userId) => {
    try {
      const res = await fetch(`http://127.0.0.1:5000/get_user_profile/${userId}`);
      if (res.ok) {
        const data = await res.json();
        setProfileData(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('docai_user');
    navigate('/');
  };

  const handleNewConsultation = async () => {
    try {
      const res = await fetch('http://127.0.0.1:5000/create_consultation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id, heading: "New Live Consultation" })
      });
      if (res.ok) {
        const data = await res.json();
        navigate(`/consultation/${data.consultation_id}`);
      } else {
        alert('Failed to create consultation');
      }
    } catch (err) {
      console.error(err);
      alert('Error connecting to backend');
    }
  };

  const handleEndConsultation = async (e, consultId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to end this consultation? It will be marked as inactive.')) return;
    try {
      const res = await fetch('http://127.0.0.1:5000/end_consultation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consultation_id: consultId })
      });
      if (res.ok) {
        fetchProfile(user.id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-background text-medicalBlue">Loading profile...</div>;
  }

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans relative">
      <div className="absolute inset-0 bg-watermark pointer-events-none"></div>

      {/* Header */}
      <header className="bg-white border-b border-slateBlue/30 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-8 h-8 bg-medicalBlue text-white rounded-lg flex justify-center items-center shadow-sm">
              <Activity size={20} />
            </div>
            <h1 className="font-serif text-2xl text-medicalBlue">DocAI</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="font-medium text-textMain hidden sm:inline-block">Welcome, {user?.name}</span>
            <button onClick={handleLogout} className="flex items-center gap-2 text-textMuted hover:text-alertRed transition-colors">
              <LogOut size={18} /> <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8 relative z-10">
        
        {/* Left Column: Profile & Vitals */}
        <div className="flex flex-col gap-6">
          {/* Active Conditions */}
          <section className="bg-white rounded-2xl shadow-sm border border-slateBlue/30 p-6">
            <h2 className="font-serif text-xl text-textMain flex items-center gap-2 mb-4">
              <Activity className="text-medicalTeal" size={20}/> Active Conditions
            </h2>
            {profileData?.conditions?.length > 0 ? (
              <div className="space-y-3">
                {profileData.conditions.map(c => (
                  <div key={c.id} className="flex items-center justify-between p-3 rounded-lg bg-background border border-slateBlue/40">
                    <div>
                      <div className="font-medium text-textMain">{c.name}</div>
                      <div className="text-xs text-textMuted capitalize">{c.type}</div>
                    </div>
                    {c.active ? (
                      <span className="w-2.5 h-2.5 rounded-full bg-successGreen shadow-[0_0_8px_rgba(22,163,74,0.5)]"></span>
                    ) : (
                      <span className="w-2.5 h-2.5 rounded-full bg-slateBlue/50"></span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-textMuted italic">No conditions recorded.</p>
            )}
          </section>

          {/* Vitals */}
          <section className="bg-white rounded-2xl shadow-sm border border-slateBlue/30 p-6">
             <h2 className="font-serif text-xl text-textMain flex items-center gap-2 mb-4">
              <HeartPulse className="text-alertRed" size={20}/> Recent Vitals
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-background rounded-lg border border-slateBlue/40 flex flex-col items-center justify-center">
                <span className="text-xs text-textMuted uppercase tracking-wider mb-1">Blood Pressure</span>
                <span className="font-serif text-2xl text-medicalBlue">
                  {profileData?.vitals?.bp ? `${profileData.vitals.bp} mmHg` : "--"}
                </span>
              </div>
              <div className="p-4 bg-background rounded-lg border border-slateBlue/40 flex flex-col items-center justify-center">
                <span className="text-xs text-textMuted uppercase tracking-wider mb-1">Heart Rate</span>
                <span className="font-serif text-2xl text-medicalBlue">
                  {profileData?.vitals?.hr ? `${profileData.vitals.hr} bpm` : "--"}
                </span>
              </div>
            </div>
          </section>
        </div>

        {/* Right Column: Consultations */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="flex justify-between items-end">
            <div>
              <h2 className="font-serif text-2xl text-textMain flex items-center gap-2">
                <History className="text-medicalBlue" size={24}/> Consultation History
              </h2>
              <p className="text-textMuted text-sm mt-1">Review past visits or start a new encounter.</p>
            </div>
            <button 
              onClick={handleNewConsultation}
              className="px-5 py-2.5 bg-medicalBlue hover:bg-medicalBlue/90 text-white font-semibold rounded-lg shadow-md transition-transform hover:scale-105 flex items-center gap-2"
            >
              <Plus size={18} /> New Consultation
            </button>
          </div>

          <div className="space-y-4">
            {profileData?.consultations?.length > 0 ? (
              profileData.consultations.map(c => (
                <div key={c.id} className={`bg-white rounded-2xl shadow-sm border p-5 flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center transition-all ${c.is_active !== false ? 'border-medicalTeal/50 hover:shadow-md' : 'border-slateBlue/30 opacity-70'}`}>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="font-bold text-textMain text-lg">{c.title || `Consultation #${c.id}`}</h3>
                      {c.is_active !== false ? (
                        <span className="px-2 py-0.5 bg-medicalCyan text-medicalBlue text-[10px] font-bold uppercase rounded-full border border-medicalTeal/20">Active</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-slateBlue/20 text-textMuted text-[10px] font-bold uppercase rounded-full">Ended</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-textMuted mb-2">
                      <Clock size={12} /> {c.date || "Unknown date"}
                    </div>
                    <p className={`text-sm text-textMuted ${c.is_active !== false ? 'line-clamp-2' : ''}`}>{c.summary || "No summary available."}</p>
                  </div>
                  
                  <div className="flex gap-2 w-full sm:w-auto shrink-0 mt-2 sm:mt-0">
                    {c.is_active !== false && (
                      <button 
                        onClick={(e) => handleEndConsultation(e, c.id)}
                        className="px-4 py-2 border border-alertRed text-alertRed hover:bg-alertRed/10 font-medium rounded-lg transition-colors flex-1 sm:flex-none text-center text-sm"
                      >
                        End
                      </button>
                    )}
                    <button 
                      onClick={() => navigate(`/consultation/${c.id}`)}
                      className="px-4 py-2 bg-accent hover:bg-accentHover text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2 flex-1 sm:flex-none text-sm"
                    >
                      {c.is_active !== false ? "Continue" : "View Record"} <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-white border border-slateBlue/30 border-dashed rounded-2xl p-12 text-center flex flex-col items-center">
                <History className="text-slateBlue mb-3 opacity-50" size={32} />
                <p className="text-textMain font-medium mb-1">No consultation history</p>
                <p className="text-textMuted text-sm mb-4">You haven't had any consultations yet.</p>
                <button 
                  onClick={handleNewConsultation}
                  className="px-4 py-2 text-medicalBlue font-medium underline"
                >
                  Start your first consultation
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
