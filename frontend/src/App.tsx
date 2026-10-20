import { useState } from "react";
import Chat from "./components/Chat";
import Dashboard from "./components/Dashboard";
import Inspector from "./components/Inspector";

type Tab = "chat" | "dashboard";

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <div className="app">
      <header>
        <div className="brand">
          <span className="logo">SP</span> SupportPilot
        </div>
        <nav>
          <button className={tab === "chat" ? "active" : ""} onClick={() => setTab("chat")}>Chat</button>
          <button className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")}>Dashboard</button>
        </nav>
      </header>
      {tab === "chat" ? (
        <main className="split">
          <Chat selectedTrace={selected} onSelect={setSelected} />
          <Inspector traceId={selected} />
        </main>
      ) : (
        <main className="single">
          <Dashboard />
        </main>
      )}
    </div>
  );
}
