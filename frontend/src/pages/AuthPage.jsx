import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, User } from 'lucide-react';

export default function AuthPage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAuth = async (e) => {
    e.preventDefault();
    if (!name || !email) {
      setError('Please fill in all fields.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // First try to check if user exists
      const checkRes = await fetch('http://127.0.0.1:5000/get_user_profile_by_email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      if (checkRes.ok) {
        const data = await checkRes.json();
        // User exists, save to local storage and go to dashboard
        localStorage.setItem('docai_user', JSON.stringify({ id: data.id, name: data.name, email: data.email }));
        navigate('/dashboard');
      } else {
        // User doesn't exist, create them
        const createRes = await fetch('http://127.0.0.1:5000/create_user', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, id: Math.floor(Math.random()*10000) })
        });
        
        const createData = await createRes.json();
        if (createRes.ok) {
          localStorage.setItem('docai_user', JSON.stringify({ id: createData.user_id, name: createData.name, email: createData.email }));
          navigate('/dashboard');
        } else {
          setError(createData.error || createData.message || 'Error creating user');
        }
      }
    } catch (err) {
      setError('Failed to connect to the server. Ensure Flask backend is running.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-medicalCyan/40 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute inset-0 bg-grid pointer-events-none opacity-50"></div>

      <div className="w-full max-w-md bg-white border border-slateBlue/40 rounded-2xl shadow-xl p-8 relative z-10">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-medicalBlue text-white rounded-xl flex justify-center items-center shadow-lg mb-4">
            <Activity size={28} />
          </div>
          <h2 className="font-serif text-3xl text-textMain">Welcome to DocAI</h2>
          <p className="text-textMuted text-sm mt-2">Enter your details to access your health profile</p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-alertRed/10 border border-alertRed/30 rounded-lg text-alertRed text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleAuth} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-textMain mb-1">Full Name</label>
            <input 
              type="text" 
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Margaret Osei"
              className="w-full p-3 rounded-lg border border-slateBlue bg-background text-textMain focus:outline-none focus:border-medicalBlue focus:ring-1 focus:ring-medicalBlue transition-shadow"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-textMain mb-1">Email Address</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. margaret@example.com"
              className="w-full p-3 rounded-lg border border-slateBlue bg-background text-textMain focus:outline-none focus:border-medicalBlue focus:ring-1 focus:ring-medicalBlue transition-shadow"
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3.5 bg-medicalBlue hover:bg-medicalBlue/90 text-white font-semibold rounded-lg shadow-md transition-transform hover:scale-[1.02] flex justify-center items-center gap-2 disabled:opacity-70 disabled:hover:scale-100"
          >
            {loading ? 'Authenticating...' : (
              <>Access Dashboard <ArrowRight size={18} /></>
            )}
          </button>
        </form>
        
        <div className="mt-6 text-center">
          <button onClick={() => navigate('/')} className="text-textMuted text-sm hover:text-medicalBlue transition-colors">
            &larr; Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}
