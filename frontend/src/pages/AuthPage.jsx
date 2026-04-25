import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, UserPlus, LogIn, Info, Plus, X } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';

export default function AuthPage() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Backend Health State
  const [backendReady, setBackendReady] = useState(true);
  const [checkingBackend, setCheckingBackend] = useState(true);

  // Form states
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        const res = await fetch(`${API_BASE_URL}/health`, { signal: controller.signal });
        clearTimeout(timeoutId);
        if (!res.ok) {
          setBackendReady(false);
        }
      } catch (err) {
        setBackendReady(false);
      } finally {
        setCheckingBackend(false);
      }
    };
    checkHealth();
  }, []);
  
  // Metadata states
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [bloodType, setBloodType] = useState('');
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');
  
  // Conditions states
  const [conditions, setConditions] = useState([]);
  const [currentCondition, setCurrentCondition] = useState('');

  const handleAddCondition = () => {
    if (currentCondition.trim() && !conditions.includes(currentCondition.trim())) {
      setConditions([...conditions, currentCondition.trim()]);
      setCurrentCondition('');
    }
  };

  const handleRemoveCondition = (condToRemove) => {
    setConditions(conditions.filter(c => c !== condToRemove));
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    
    if (isLogin) {
      if (!email || !password) {
        setError('Please enter your email and password.');
        return;
      }
    } else {
      if (!name || !email || !password) {
        setError('Name, email, and password are required.');
        return;
      }
    }

    setLoading(true);
    setError('');

    try {
      const endpoint = isLogin ? '/login' : '/signup';
      const payload = isLogin 
        ? { email, password }
        : { 
            name, 
            email, 
            password,
            age: age ? parseInt(age) : null,
            gender: gender || null,
            blood_type: bloodType || null,
            height_cm: height ? parseFloat(height) : null,
            weight_kg: weight ? parseFloat(weight) : null,
            pre_existing_conditions: conditions
          };

      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();

      if (res.ok) {
        // Successful login or signup
        const userToSave = isLogin ? data.user : { id: data.user_id, name: data.name, email: data.email };
        localStorage.setItem('docai_user', JSON.stringify(userToSave));
        navigate('/dashboard');
      } else {
        setError(data.message || data.error || 'Authentication failed');
      }
    } catch (err) {
      setError('Failed to connect to the server. Ensure the backend is running.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const inputClass = "w-full p-3 rounded-lg border border-slateBlue bg-background text-textMain focus:outline-none focus:border-medicalBlue focus:ring-1 focus:ring-medicalBlue transition-shadow";
  const labelClass = "block text-sm font-medium text-textMain mb-1";

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-medicalCyan/40 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute inset-0 bg-grid pointer-events-none opacity-50"></div>

      <div className="w-full max-w-xl bg-white border border-slateBlue/40 rounded-2xl shadow-xl p-8 relative z-10 max-h-[90vh] overflow-y-auto custom-scrollbar">
        <div className="flex flex-col items-center mb-6">
          <div className="w-12 h-12 bg-medicalBlue text-white rounded-xl flex justify-center items-center shadow-lg mb-4">
            <Activity size={28} />
          </div>
          <h2 className="font-serif text-3xl text-textMain">
            {isLogin ? 'Welcome Back' : 'Create your Health Profile'}
          </h2>
          <p className="text-textMuted text-sm mt-2 text-center">
            {isLogin ? 'Enter your credentials to access your dashboard' : 'Your data helps DocAI provide personalized, accurate medical guidance.'}
          </p>
        </div>

        {!checkingBackend && !backendReady && (
          <div className="mb-6 p-4 bg-slateBlue/10 border border-slateBlue/30 rounded-xl flex flex-col items-center text-center">
            <Info className="text-medicalBlue mb-2" size={24} />
            <p className="text-textMain font-medium mb-1">The backend server is currently resting.</p>
            <p className="text-sm text-textMuted mb-4">To save resources, the server spins down when inactive. You cannot log in right now, but you can explore the simulation!</p>
            <button onClick={() => navigate('/demo')} className="px-4 py-2 bg-medicalBlue text-white text-sm font-medium rounded-lg hover:bg-medicalBlue/90 transition-colors">
              View Interactive Demo
            </button>
          </div>
        )}

        {error && (
          <div className="mb-6 p-3 bg-alertRed/10 border border-alertRed/30 rounded-lg text-alertRed text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleAuth} className={`space-y-5 ${!backendReady ? 'opacity-50 pointer-events-none' : ''}`}>
          {/* Core Fields */}
          {!isLogin && (
            <div>
              <label className={labelClass}>Full Name *</label>
              <input 
                type="text" value={name} onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Margaret Osei" className={inputClass}
              />
            </div>
          )}
          
          <div>
            <label className={labelClass}>Email Address *</label>
            <input 
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. margaret@example.com" className={inputClass}
            />
          </div>

          <div>
            <label className={labelClass}>Password *</label>
            <input 
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••" className={inputClass}
            />
          </div>

          {/* Extended Metadata Fields (Only in Signup) */}
          {!isLogin && (
            <div className="pt-4 border-t border-slateBlue/30">
              <h3 className="font-semibold text-textMain mb-4 flex items-center gap-2">
                <UserPlus size={18} className="text-medicalBlue"/> 
                Personal Details <span className="text-xs font-normal text-textMuted">(Optional)</span>
              </h3>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className={labelClass}>Age</label>
                  <input type="number" min="0" max="120" value={age} onChange={(e) => setAge(e.target.value)} placeholder="e.g. 34" className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Gender</label>
                  <select value={gender} onChange={(e) => setGender(e.target.value)} className={inputClass}>
                    <option value="">Select...</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                    <option value="Prefer not to say">Prefer not to say</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Height (cm)</label>
                  <input type="number" step="0.1" value={height} onChange={(e) => setHeight(e.target.value)} placeholder="e.g. 175" className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Weight (kg)</label>
                  <input type="number" step="0.1" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="e.g. 70.5" className={inputClass} />
                </div>
                <div className="col-span-2">
                  <label className={labelClass}>Blood Type</label>
                  <select value={bloodType} onChange={(e) => setBloodType(e.target.value)} className={inputClass}>
                    <option value="">Select...</option>
                    <option value="A+">A+</option><option value="A-">A-</option>
                    <option value="B+">B+</option><option value="B-">B-</option>
                    <option value="AB+">AB+</option><option value="AB-">AB-</option>
                    <option value="O+">O+</option><option value="O-">O-</option>
                  </select>
                </div>
              </div>

              {/* Pre-existing Conditions */}
              <div className="bg-medicalCyan/10 p-4 rounded-xl border border-medicalCyan/30 mt-6">
                <label className="block text-sm font-semibold text-textMain mb-1">Pre-existing Conditions</label>
                <div className="flex items-start gap-2 mb-3 text-xs text-textMuted">
                  <Info size={14} className="min-w-3 mt-0.5 text-medicalCyan" />
                  <p>Recommended: Telling DocAI about your past health (like asthma or hypertension) acts as a safety net. It helps the AI recognize when a simple symptom might actually be a warning sign for your specific body.</p>
                </div>
                
                <div className="flex gap-2 mb-3">
                  <input 
                    type="text" 
                    value={currentCondition} 
                    onChange={(e) => setCurrentCondition(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCondition())}
                    placeholder="e.g. Type 2 Diabetes" 
                    className={`${inputClass} py-2 text-sm`}
                  />
                  <button 
                    type="button" 
                    onClick={handleAddCondition}
                    className="bg-medicalCyan text-white p-2 rounded-lg hover:bg-medicalCyan/90 transition-colors shrink-0"
                  >
                    <Plus size={20} />
                  </button>
                </div>

                {conditions.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {conditions.map((cond, idx) => (
                      <span key={idx} className="inline-flex items-center gap-1 bg-white border border-medicalCyan/50 text-medicalBlue px-3 py-1 rounded-full text-sm shadow-sm">
                        {cond}
                        <button type="button" onClick={() => handleRemoveCondition(cond)} className="hover:text-alertRed transition-colors">
                          <X size={14} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3.5 mt-6 bg-medicalBlue hover:bg-medicalBlue/90 text-white font-semibold rounded-lg shadow-md transition-transform hover:scale-[1.02] flex justify-center items-center gap-2 disabled:opacity-70 disabled:hover:scale-100"
          >
            {loading ? 'Processing...' : (
              isLogin ? <><LogIn size={18} /> Sign In</> : <><UserPlus size={18} /> Create Profile & Access Dashboard</>
            )}
          </button>
        </form>
        
        <div className="mt-6 text-center border-t border-slateBlue/20 pt-4">
          <button 
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }} 
            className="text-medicalBlue text-sm font-medium hover:underline transition-all"
          >
            {isLogin ? "Don't have an account? Sign up here." : "Already have a profile? Sign in instead."}
          </button>
        </div>
        
        <div className="mt-4 text-center">
          <button onClick={() => navigate('/')} className="text-textMuted text-xs hover:text-medicalBlue transition-colors">
            &larr; Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}
