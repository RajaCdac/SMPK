import React from "react";
import "./Footer.css";

const Footer = () => {
  return (
    <footer className="footer">

      <div className="footer-left">
        © 2026 SMP Kolkata
      </div>

      <div className="footer-center">
        Developed by CDAC, Kolkata
      </div>

      <div className="footer-right">
        <a href="#">Privacy Policy</a>
        <a href="#">Terms</a>
      </div>

    </footer>
  );
};

export default Footer;