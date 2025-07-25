import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';

// Initialize Supabase client
const supabase = createClient(
  'YOUR_SUPABASE_URL', // Replace with your Supabase project URL
  'YOUR_SUPABASE_ANON_KEY' // Replace with your Supabase anon key
);

export default function LoginSystem() {
  const [session, setSession] = useState(null);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    // Cleanup subscription on component unmount
    return () => subscription.unsubscribe();
  }, []);

  // Handle logout
  const handleLogout = async () => {
    await supabase.auth.signOut();
    setSession(null);
  };

  return (
    <div style={{ maxWidth: '400px', margin: '0 auto', padding: '20px' }}>
      {!session ? (
        <Auth
          supabaseClient={supabase}
          appearance={{ theme: ThemeSupa }}
          providers={['google']} // Add other providers like 'facebook', 'github' if needed
          redirectTo={window.location.origin}
        />
      ) : (
        <div>
          <h2>Welcome, {session.user.email}</h2>
          <button 
            onClick={handleLogout}
            style={{
              padding: '10px 20px',
              backgroundColor: '#ff4d4f',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Log Out
          </button>
        </div>
      )}
    </div>
  );
}