import { useState, useEffect } from "react";
import "./Carousel.css";

const images = [
  "/images/Banner1.webp",
  "/images/Banner2.jpg",
  "/images/Banner3.webp",
  "/images/Banner4.jpg",
];

export default function Carousel() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrent((prev) => (prev + 1) % images.length);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="carousel">
      
      {/* Images */}
      {images.map((img, index) => (
        <div
          key={index}
          className={`slide ${index === current ? "active" : ""}`}
          style={{ backgroundImage: `url(${img})` }}
        ></div>
      ))}

      {/* STATIC TEXT OVERLAY */}
      <div className="overlay">
        <h1>Welcome to Pension Management System</h1>
        <p>Streamlining pension processing efficiently</p>
      </div>

    </div>
  );
}