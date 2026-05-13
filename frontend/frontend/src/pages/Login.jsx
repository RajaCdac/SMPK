import { useState } from "react";
import API from "../services/Api";
import "../styles/Login.css";

export default function Login() {
const [username, setUsername] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [captchaInput, setCaptchaInput] =
    useState("");

  const [captcha, setCaptcha] = useState(
    Math.random().toString(36)
      .substring(2, 7)
      .toUpperCase()
  );
const refreshCaptcha = () => {

    setCaptcha(
      Math.random().toString(36)
        .substring(2, 7)
        .toUpperCase()
    );
  };
const handleLogin = async () => {

    if (
      captchaInput.toUpperCase() !== captcha
    ) {

      alert("Invalid Captcha");

      refreshCaptcha();

      return;
    }

    try {

      const res = await API.post(
        "login/",
        {
          username,
          password,
        }
      );
localStorage.setItem("access",res.data.access);
localStorage.setItem("refresh",res.data.refresh);
localStorage.setItem("user",JSON.stringify(res.data.user));
window.location.href ="/dashboard";
} catch {
alert("Invalid credentials"); }
  };

  return (

    <div
      className="login-wrapper"
      style={{
        backgroundImage: `
          linear-gradient(
            rgba(5, 20, 40, 0.72),
            rgba(5, 20, 40, 0.72)
          ),
          url('/images/Banner4.jpg')
        `
      }}
    >

      <div className="light-effect light1"></div>

      <div className="light-effect light2"></div>

      <div className="light-effect light3"></div>

      <div className="side-content">

        <h1>SMPK Pension Portal</h1>

      </div>

      <div className="login-card">

        <h2>Pension Portal</h2>

        <p className="login-subtitle">
          Employee Pension Management System
        </p>

        <input
          type="text"
          placeholder="Enter Username"
          value={username}
          onChange={(e) =>
            setUsername(e.target.value)
          }
        />

        <input
          type="password"
          placeholder="Enter Password"
          value={password}
          onChange={(e) =>
            setPassword(e.target.value)
          }
        />

        <div className="captcha-box">

          <span className="captcha-text">
            {captcha}
          </span>

          <button
            type="button"
            className="captcha-refresh"
            onClick={refreshCaptcha}
          >
            ↻
          </button>

        </div>

        <input
          type="text"
          placeholder="Enter Captcha"
          value={captchaInput}
          onChange={(e) =>
            setCaptchaInput(e.target.value)
          }
        />

        <button
          className="login-btn"
          onClick={handleLogin}
        >
          Login
        </button>
        <div className="login-footer">
          Secure Pension Dashboard Access
        </div>

      </div>

    </div>
  );
}