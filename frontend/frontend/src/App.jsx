import { useEffect, useState } from "react";
import API from "./Api";

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    API.get("hello/")
      .then((res) => setMessage(res.data.message))
      .catch((err) => console.error(err));
  }, []);

  return (
    <div>
      <h1>Frontend + Backend Connected 🚀</h1>
      <p>{message}</p>
    </div>
  );
}

export default App;
