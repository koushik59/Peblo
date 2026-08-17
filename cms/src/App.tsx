import { Routes, Route, Navigate, NavLink, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import LoginPage from './pages/LoginPage';
import ShowsPage from './pages/ShowsPage';
import ShowEditPage from './pages/ShowEditPage';
import PublishPage from './pages/PublishPage';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const stored = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    if (stored && token) {
      try {
        setUser(JSON.parse(stored));
      } catch {
        localStorage.removeItem('user');
        localStorage.removeItem('token');
      }
    }
  }, []);

  const handleLogin = (userData: User, token: string) => {
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('token', token);
    setUser(userData);
    navigate('/shows');
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    setUser(null);
    navigate('/login');
  };

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    );
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>📺 Peblo CMS</h2>
          <p>{user.name} ({user.role})</p>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/shows" className={({ isActive }) => isActive ? 'active' : ''}>
            📋 Shows
          </NavLink>
          <NavLink to="/publish" className={({ isActive }) => isActive ? 'active' : ''}>
            🚀 Publish
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <button className="btn-secondary" onClick={handleLogout} style={{ width: '100%' }}>
            Logout
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/shows" element={<ShowsPage />} />
          <Route path="/shows/new" element={<ShowEditPage />} />
          <Route path="/shows/:id" element={<ShowEditPage />} />
          <Route path="/publish" element={<PublishPage user={user} />} />
          <Route path="*" element={<Navigate to="/shows" />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
