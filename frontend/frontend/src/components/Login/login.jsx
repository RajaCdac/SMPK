import React, { useState } from "react";
// import "./Login.css";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faUser, faLock, faEye, faEyeSlash  } from "@fortawesome/free-solid-svg-icons";

export default function Login() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div style={styles.container}>
      <div style={styles.box}>
        <h2 style={styles.title}>Log in to your account</h2>
        <p style={styles.subtitle}>
          Welcome back! Please enter your details.
        </p>

        {/* <div style={styles.tabs}>
          <button style={styles.tab}>Sign up</button>
          <button style={{ ...styles.tab, ...styles.activeTab }}>
            Log in
          </button>
        </div> */}

        <label style={styles.label}>Email</label>
        <input
          type="email"
          placeholder="Enter your email"
          style={styles.input}
        />

        <label style={styles.label}>Password</label>
        <div style={styles.passwordWrapper}>
          <input
            type={showPassword ? "text" : "password"}
            placeholder="••••••••••"
            style={styles.input}
          />
          <span
            style={styles.eye}
            onClick={() => setShowPassword(!showPassword)}
          >
            👁
          </span>
        </div>

        <div style={styles.options}>
          <label>
            <input type="checkbox" /> Remember for 30 days
          </label>
          <span style={styles.forgot}>Forgot password</span>
        </div>

        <button style={styles.signinBtn}>Sign in</button>

        {/* <button style={styles.googleBtn}>
          <img
            src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png"
            alt="google"
            style={{ width: 18 }}
          />
          Sign in with Google
        </button> */}

        <p style={styles.signupText}>
          Don't have an account? <span style={styles.link}>Sign up</span>
        </p>
      </div>
    </div>
  );
}

const styles = {
  container: {
    height: "60vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    // background: "#0c0a0a",
    fontFamily: "Arial",
  },
  box: {
    width: "360px",
    // background: "#202899",
    padding: "30px",
    borderRadius: "10px",
    boxShadow: "0 0 10px rgba(0,0,0,0.08)",
  },
  title: {
    textAlign: "center",
    margin: 0,
  },
  subtitle: {
    textAlign: "center",
    color: "#000000",
    fontSize: "14px",
    marginBottom: "20px",
  },
  tabs: {
    display: "flex",
    marginBottom: "20px",
  },
  tab: {
    flex: 1,
    padding: "10px",
    border: "1px solid #ddd",
    background: "#f9f9f9",
    cursor: "pointer",
  },
  activeTab: {
    background: "#fff",
    fontWeight: "bold",
  },
  label: {
    display: "block",
    marginTop: "10px",
    marginBottom: "5px",
    fontSize: "14px",
  },
  input: {
    width: "100%",
    padding: "10px",
    borderRadius: "6px",
    border: "1px solid #ddd",
  },
  passwordWrapper: {
    position: "relative",
  },
  eye: {
    position: "absolute",
    right: "10px",
    top: "10px",
    cursor: "pointer",
  },
  options: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "13px",
    marginTop: "10px",
  },
  forgot: {
    color: "#6c63ff",
    cursor: "pointer",
  },
  signinBtn: {
    width: "100%",
    marginTop: "15px",
    padding: "12px",
    background: "linear-gradient(90deg, #6c63ff, #7b4bff)",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontWeight: "bold",
  },
  googleBtn: {
    width: "100%",
    marginTop: "10px",
    padding: "10px",
    background: "#fff",
    border: "1px solid #ddd",
    borderRadius: "6px",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "10px",
    cursor: "pointer",
  },
  signupText: {
    textAlign: "center",
    fontSize: "13px",
    marginTop: "15px",
  },
  link: {
    color: "#6c63ff",
    cursor: "pointer",
  },
};

// export default Login;