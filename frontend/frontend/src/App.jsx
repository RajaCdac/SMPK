import { useEffect, useState } from "react";
import API from "./Api";
import Header from "./components/Header/Header";
import Navbar from "./components/Navbar/Navbar";
import Footer from "./components/Footer/Footer";
import Login from "./components/Login/login";

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    API.get("hello/")
      .then((res) => setMessage(res.data.message))
      .catch((err) => console.error(err));
  }, []);

  return (
    <div>
      <Header />
      <Navbar />
     <main className="main-content">
        <Login />
      </main>

      <Footer />
      
    </div>
  );
}

export default App;
