import { useEffect } from "react";
import Header from "../Header/Header";
import Navbar from "../Navbar/Navbar";
import Footer from "../Footer/Footer";
import { Outlet, useLocation } from "react-router-dom";
import "../../styles/home-layout.css";

export default function MainLayout() {
  const { pathname } = useLocation();
  const isHome = pathname === "/" || pathname === "/login";

  useEffect(() => {
    if (isHome) {
      document.body.classList.add("page-home");
    } else {
      document.body.classList.remove("page-home");
    }
    return () => document.body.classList.remove("page-home");
  }, [isHome]);

  return (
    <>
      <Header />
      <Navbar />

      <main className={`main-content${isHome ? " main-content--home" : ""}`}>
        <Outlet />
      </main>

      <Footer />
    </>
  );
}