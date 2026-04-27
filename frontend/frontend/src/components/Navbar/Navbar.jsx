import React, { useState } from "react";
import "./Navbar.css";
import { Link } from "react-router-dom";

const Navbar = () => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="navbar">

      {/* LEFT */}
      <div className="nav-left">
        <span className="brand">SMP Kolkata</span>
      </div>

      {/* MENU */}
      <ul className={`nav-menu ${menuOpen ? "active" : ""}`}>

        <li><a href="/">Home</a></li>

        {/* LEVEL 1 */}
        <li className="dropdown">
          <span>Pension ▾</span>

          {/* LEVEL 2 */}
          <ul className="dropdown-menu">
            <li><a href="#">First Pension Proposal</a></li>
            <li><a href="#">Family Pension</a></li>

            {/* LEVEL 3 */}
            <li className="dropdown-sub">
              <span>Organization ▸</span>
              <ul className="dropdown-submenu">
                <li><a href="#">Board Members</a></li>
                <li><a href="#">Departments</a></li>
              </ul>
            </li>

          </ul>
        </li>

        <li><a href="#">Services</a></li>

        <li className="dropdown">
          <span>Departments ▾</span>
          <ul className="dropdown-menu">
            <li><a href="#">Marine</a></li>
            <li><a href="#">Traffic</a></li>
          </ul>
        </li>

        <li><a href="#">Contact</a></li>

      </ul>

      {/* RIGHT */}
      <div className="nav-right">
        {/* <button className="login-btn" href="/login">
          Login
        </button> */}
        <Link to="/login" className="login-btn">Login</Link>

        <div
          className="hamburger"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          ☰
        </div>
      </div>

    </nav>
  );
};

export default Navbar;