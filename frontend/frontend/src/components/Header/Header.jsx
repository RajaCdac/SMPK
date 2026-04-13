import React from "react";
import "./Header.css";
import bg from "../../assets/images/background.png";
import ashoka from "../../assets/images/goi_logo.png";
import smpLogo from "../../assets/images/SMP_Logo.png";

const Header = () => {
  return (
    <header
      className="header"
      style={{ backgroundImage: `url(${bg})` }}   // 👈 IMPORTANT
    >
      <div className="left">
        <img src={ashoka} alt="Ashoka" />
      </div>

      <div className="center">
        <h1>SYAMA PRASAD MOOKERJEE PORT, KOLKATA</h1>
        <h4>A Statutory Body under the Ministry of Ports, Shipping and Waterways, Government of India</h4>
      </div>

      <div className="right">
        <img src={smpLogo} alt="SMP Logo" />
      </div>
    </header>
  );
};

export default Header;