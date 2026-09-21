import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import Home from "./pages/Home";
import { checkHealth } from "./services/api";

export default function App() {
  const [health, setHealth] = useState({ compiler: "g++", compiler_available: true, llm_configured: true });

  useEffect(() => {
    checkHealth()
      .then((h) => setHealth(h))
      .catch(() => {
        // Backend not reachable yet; sidebar will show optimistic defaults
        // until the user starts an analysis, which will surface the real error.
      });
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg text-gray-100 font-sans">
      <Sidebar
        llmConfigured={health.llm_configured}
        compilerAvailable={health.compiler_available}
        compilerName={health.compiler}
      />
      <Home />
    </div>
  );
}
