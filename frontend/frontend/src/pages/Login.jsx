import { useState } from "react";
import API from "../services/Api";
import "../styles/Login.css";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [captchaInput, setCaptchaInput] = useState("");

  // simple captcha
  const [captcha, setCaptcha] = useState(
    Math.random().toString(36).substring(2, 7)
  );

  const refreshCaptcha = () => {
    setCaptcha(Math.random().toString(36).substring(2, 7));
  };

  const handleLogin = async () => {
    if (captchaInput !== captcha) {
      alert("Invalid Captcha");
      refreshCaptcha();
      return;
    }

    try {
      const res = await API.post("login/", {
        username,
        password,
      });

      localStorage.setItem("access", res.data.access);
      localStorage.setItem("refresh", res.data.refresh);
      localStorage.setItem("user", JSON.stringify(res.data.user));

      window.location.href = "/dashboard";
    } catch {
      alert("Invalid credentials");
    }
  };

  return (
    <div className="login-wrapper">
      <div className="login-card">

        <h2>Pension User Login</h2>

        <input
          type="text"
          placeholder="Username"
          onChange={(e) => setUsername(e.target.value)}
        />

        <input
          type="password"
          placeholder="Password"
          onChange={(e) => setPassword(e.target.value)}
        />

        {/* CAPTCHA */}
        <div className="captcha-box">
          <span className="captcha-text">{captcha}</span>
          <button onClick={refreshCaptcha}>↻</button>
        </div>

        <input
          type="text"
          placeholder="Enter Captcha"
          onChange={(e) => setCaptchaInput(e.target.value)}
        />

        <button className="login-btn" onClick={handleLogin}>
          Login
        </button>

      </div>
    </div>
  );
}