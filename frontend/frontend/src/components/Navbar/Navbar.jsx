import "./Navbar.css";

/** Blue accent bar — avoid Bootstrap `.navbar` class (conflicts with layout). */
const Navbar = () => {
  return <nav className="smpk-topbar" aria-label="Site accent bar" />;
};

export default Navbar;
