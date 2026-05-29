import { useEffect, useRef, useState } from "react";
import axiosClient from "../api/axiosClient";

export default function ChatAgent({ onChatResponse }) {
  const [messages, setMessages] = useState([
    {
      sender: "ai",
      text: "Chao ban, toi la AI Data Analyst. Ban muon thong ke hay hoi so lieu gi trong kho du lieu?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setMessages((prev) => [...prev, { sender: "user", text: question }]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axiosClient.post("/api/chat-agent", { question });
      const responseData = response?.data || {};
      const ai_text = responseData.ai_message;

      // Use actual AI text from response (no fallback default)
      if (ai_text != null) {
        setMessages((prev) => [...prev, { sender: "ai", text: ai_text }] );
      } else {
        setMessages((prev) => [...prev, { sender: "ai", text: "" }] );
      }

      if (onChatResponse) {
        onChatResponse(responseData);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: "Xin lỗi sếp, hệ thống đang bận hoặc gặp sự cố kết nối." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <section className="mt-12 flex justify-center">
      <div className="w-full max-w-4xl rounded-2xl border border-white/10 bg-slate-900/80 shadow-2xl backdrop-blur-xl">
        <div className="px-8 pt-8 text-center">
          <h2 className="text-2xl font-display font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-emerald-300 via-lime-300 to-cyan-300">
            🤖 AI Data Analyst - Chat voi CSDL
          </h2>
          <p className="mt-2 text-sm font-mono text-dim">
            Dat cau hoi tu nhien, AI se tu dong truy van CSDL.
          </p>
        </div>

        <div
          ref={scrollRef}
          className="mt-6 max-h-60 overflow-y-auto px-8 pb-4 space-y-3"
        >
          {messages.map((msg, index) => (
            <div
              key={`${msg.sender}-${index}`}
              className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-md ${
                  msg.sender === "user"
                    ? "bg-slate-800 text-white"
                    : "border border-emerald-500/30 bg-emerald-500/5 text-emerald-200"
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl px-4 py-3 text-sm text-emerald-200 border border-emerald-500/30 bg-emerald-500/5">
                Dang xu ly...
              </div>
            </div>
          )}
        </div>

        <div className="px-8 pb-8">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Nhap cau hoi ve du lieu..."
              className="flex-1 rounded-full border border-white/10 bg-slate-900/70 px-6 py-4 text-lg text-white placeholder:text-slate-400 shadow-lg shadow-emerald-500/20 focus:outline-none focus:border-emerald-400/60 focus:ring-2 focus:ring-emerald-400/20"
              disabled={isLoading}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="inline-flex items-center gap-2 rounded-full bg-emerald-400 px-6 py-4 text-sm font-semibold text-slate-900 shadow-lg shadow-emerald-500/20 transition-all hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Gui
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
