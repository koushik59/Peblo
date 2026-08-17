import { NavLink } from 'react-router-dom';

export default function Navbar() {
  return (
    <header className="navbar">
      <NavLink to="/" className="nav-brand">
        PEBLO <span>TV</span>
      </NavLink>
      <nav className="nav-links">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          Home
        </NavLink>
        <NavLink to="/search" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          🔍 Search & Browse
        </NavLink>
      </nav>
    </header>
  );
}
