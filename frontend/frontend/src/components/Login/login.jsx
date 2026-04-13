import React, { useState } from "react";
import "./Login.css";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faUser, faLock, faEye, faEyeSlash  } from "@fortawesome/free-solid-svg-icons";

const Login = () => {
    const [showPassword, setShowPassword] = useState(false);
  return (
    <div className="login-container">

      <div className="login-card">
        <h2>Pension Module Login</h2>

        <form>
          <div className="input-group">
            <FontAwesomeIcon icon={faUser} className="icon" />           
            <input type="text" placeholder="Enter username" />
          </div>

          <div className="input-group">
            <FontAwesomeIcon icon={faLock} className="icon" />
            
            <input type={showPassword ? "text" : "password"} placeholder="Enter password" />
            <FontAwesomeIcon
            icon={showPassword ? faEyeSlash : faEye}
            className="eye-icon"
            onClick={() => setShowPassword(!showPassword)}
           />
          </div>

          <button className="login-btn">Login</button>

          <p className="extra">
            Forgot Password? <a href="#">Click here</a>
          </p>
        </form>
      </div>

    </div>
  );
};

export default Login;