import { useState, useEffect } from "react";
import LoginPanel from "../Login/LoginPanel";
import "./Carousel.css";

const base = import.meta.env.BASE_URL || "/";
const images = [
  `${base}images/Banner1.webp`,
  `${base}images/Banner2.jpg`,
  `${base}images/Banner3.webp`,
  `${base}images/Banner4.jpg`,
];

export default function Carousel({ initialShowLogin = false }) {
  const [current, setCurrent] = useState(0);
  const [showLogin, setShowLogin] = useState(initialShowLogin);

  useEffect(() => {
    setShowLogin(initialShowLogin);
  }, [initialShowLogin]);

  useEffect(() => {
    if (showLogin) return undefined;

    const interval = setInterval(() => {
      setCurrent((prev) => (prev + 1) % images.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [showLogin]);

  return (
    <section
      className={`smpk-hero${showLogin ? " smpk-hero--login-open" : ""}`}
      aria-label="Welcome banner"
    >
      {images.map((img, index) => (
        <div
          key={img}
          className={`smpk-hero__slide${index === current ? " is-active" : ""}`}
          style={{ backgroundImage: `url(${img})` }}
          role="img"
          aria-label={`Banner ${index + 1}`}
        />
      ))}

      <div
        className={`smpk-hero__overlay${showLogin ? " smpk-hero__overlay--login" : ""}`}
      >
        {!showLogin ? (
          <div className="smpk-hero__welcome">
            <h1>Welcome to Pension Management System</h1>
            <p>Streamlining pension processing efficiently</p>
            <button
              type="button"
              className="smpk-hero__login-btn"
              onClick={() => setShowLogin(true)}
            >
              Login
            </button>
          </div>
        ) : (
          <LoginPanel onBack={() => setShowLogin(false)} />
        )}
      </div>
    </section>
  );
}
