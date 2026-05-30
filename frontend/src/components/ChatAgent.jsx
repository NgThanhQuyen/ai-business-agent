import { useEffect, useRef, useState } from "react";
import axiosClient from "../api/axiosClient";

export default function ChatAgent({ onChatResponse, chatContext }) {
  const [messages, setMessages] = useState([
    {
      sender: "ai",
      text: "Xin chào! Tôi là Trợ lý Phân tích & Tìm kiếm khách hàng tiềm năng AI. Bạn muốn tìm kiếm thông tin doanh nghiệp, cào dữ liệu Google Maps hay phân tích dữ liệu đối thủ hôm nay?",
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
      const response = await axiosClient.post("/api/chat-agent", {
        question,
        context: chatContext || null,
      });
      const responseData = response?.data || {};
      const ai_text = responseData.ai_message;

      // Use actual AI text from response
      if (ai_text != null) {
        setMessages((prev) => [...prev, { sender: "ai", text: ai_text }]);
      } else {
        setMessages((prev) => [...prev, { sender: "ai", text: "" }]);
      }

      if (onChatResponse) {
        onChatResponse(responseData);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: "Xin lỗi bạn, hệ thống đang bận hoặc gặp sự cố kết nối." },
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
    <section className="mt-12 w-full">
      <div className="w-full rounded-2xl border border-white/10 bg-slate-900/80 shadow-2xl backdrop-blur-xl overflow-hidden">
        {/* Thanh tiêu đề trên cùng */}
        <div className="px-8 py-6 border-b border-white/5 bg-slate-950/40">
          <h2 className="text-2xl font-display font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-emerald-300 via-lime-300 to-cyan-300">
            🤖 Trợ lý AI Phân tích & Khai phá Dữ liệu
          </h2>
          <p className="mt-1 text-sm font-mono text-dim">
            Hỏi đáp tự nhiên để truy vấn kho dữ liệu, tìm kiếm ngữ nghĩa hoặc kích hoạt cào dữ liệu Google Maps tự động.
          </p>
        </div>

        {/* Bố cục chia tỷ lệ 7/3 */}
        <div className="grid grid-cols-1 lg:grid-cols-10 divide-y lg:divide-y-0 lg:divide-x divide-white/10">
          {/* Phần 7: Khung trò chuyện AI (chiếm 7/10 cột) */}
          <div className="lg:col-span-7 flex flex-col justify-between">
            {/* Khu vực cuộn hiển thị lịch sử trò chuyện */}
            <div
              ref={scrollRef}
              className="h-[450px] overflow-y-auto px-8 py-6 space-y-4"
            >
              {messages.map((msg, index) => (
                <div
                  key={`${msg.sender}-${index}`}
                  className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-md ${
                      msg.sender === "user"
                        ? "bg-slate-800 text-white"
                        : "border border-emerald-500/30 bg-emerald-500/5 text-emerald-200"
                    }`}
                  >
                    <div className="whitespace-pre-line">{msg.text}</div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm text-emerald-200 border border-emerald-500/30 bg-emerald-500/5">
                    Đang xử lý...
                  </div>
                </div>
              )}
            </div>

            {/* Khu vực nhập câu hỏi của người dùng */}
            <div className="px-8 pb-8 pt-4 border-t border-white/5 bg-slate-950/20">
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Nhập yêu cầu tìm kiếm, phân tích hoặc cào dữ liệu Google Maps..."
                  className="flex-1 rounded-full border border-white/10 bg-slate-900/70 px-6 py-4 text-base text-white placeholder:text-slate-400 shadow-lg shadow-emerald-500/5 focus:outline-none focus:border-emerald-400/60 focus:ring-2 focus:ring-emerald-400/20"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={isLoading || !input.trim()}
                  className="inline-flex items-center gap-2 rounded-full bg-emerald-400 px-6 py-4 text-sm font-semibold text-slate-900 shadow-lg shadow-emerald-500/10 transition-all hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-50 whitespace-nowrap"
                >
                  Gửi
                </button>
              </div>
            </div>
          </div>

          {/* Phần 3: Thanh bên hướng dẫn sử dụng (chiếm 3/10 cột) */}
          <div className="lg:col-span-3 bg-slate-900/40 p-8 flex flex-col justify-between space-y-6">
            <div>
              <h3 className="text-base font-display font-bold text-white mb-4 flex items-center gap-2">
                📖 Hướng dẫn sử dụng
              </h3>
              
              <div className="space-y-5 text-sm leading-relaxed text-slate-300">
                <div className="space-y-1">
                  <p className="font-semibold text-emerald-300 flex items-center gap-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-xs">1</span>
                    Tìm kiếm thông minh
                  </p>
                  <p className="text-xs text-slate-400 pl-6.5">
                    Sử dụng cú pháp <code className="bg-slate-800 text-emerald-400 px-1.5 py-0.5 rounded font-mono">/ai</code> trước câu hỏi để tìm kiếm theo ngữ nghĩa và phân tích review bằng mô hình AI.
                  </p>
                  <p className="text-xs italic text-slate-500 pl-6.5">
                    Ví dụ: <code className="bg-slate-800/50 text-slate-400 px-1 py-0.2 rounded font-mono">/ai quán cafe view đẹp, rộng rãi ở gò vấp</code>
                  </p>
                </div>

                <div className="space-y-1">
                  <p className="font-semibold text-cyan-300 flex items-center gap-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500/20 text-xs">2</span>
                    Cào dữ liệu Google Maps
                  </p>
                  <p className="text-xs text-slate-400 pl-6.5">
                    Nhập các từ khóa chứa <code className="bg-slate-800 text-cyan-400 px-1.5 py-0.5 rounded font-mono">google map</code>, <code className="bg-slate-800 text-cyan-400 px-1.5 py-0.5 rounded font-mono">cào thêm</code>, hoặc <code className="bg-slate-800 text-cyan-400 px-1.5 py-0.5 rounded font-mono">tìm kiếm</code> để kích hoạt tính năng tự động cào dữ liệu mới từ Google Maps.
                  </p>
                  <p className="text-xs italic text-slate-500 pl-6.5">
                    Ví dụ: <code className="bg-slate-800/50 text-slate-400 px-1 py-0.2 rounded font-mono">tìm kiếm google map các quán cà phê quận 1</code> hoặc <code className="bg-slate-800/50 text-slate-400 px-1 py-0.2 rounded font-mono">cào dữ liệu spa ở gò vấp</code>
                  </p>
                </div>

                <div className="space-y-1">
                  <p className="font-semibold text-lime-300 flex items-center gap-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-lime-500/20 text-xs">3</span>
                    Hỏi đáp dữ liệu SQL
                  </p>
                  <p className="text-xs text-slate-400 pl-6.5">
                    Hỏi trực tiếp về số lượng, so sánh, phân tích các địa điểm trong cơ sở dữ liệu hiện tại mà không cần dùng cú pháp đặc biệt.
                  </p>
                  <p className="text-xs italic text-slate-500 pl-6.5">
                    Ví dụ: <code className="bg-slate-800/50 text-slate-400 px-1 py-0.2 rounded font-mono">quán nào có điểm đánh giá cao nhất ở gò vấp?</code>
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-white/5 text-[11px] font-mono text-slate-500">
              Hệ thống tự động nhận diện ý định để truy vấn SQL cục bộ, tìm kiếm Vector ngữ nghĩa (/ai) hoặc tự động kích hoạt pipeline cào dữ liệu Google Maps trực tuyến.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
