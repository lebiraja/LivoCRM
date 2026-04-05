import { useEffect } from "react";
import { motion } from "framer-motion";
import { Wifi, WifiOff, Loader2 } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatTypingIndicator } from "@/components/chat/ChatTypingIndicator";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatSessionList } from "@/components/chat/ChatSessionList";

export default function ChatPage() {
  const {
    sessions,
    activeSessionId,
    messages,
    loading,
    streaming,
    wsStatus,
    bottomRef,
    loadSessions,
    selectSession,
    newSession,
    sendMessage,
  } = useChat();

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Auto-create a session when none exist
  useEffect(() => {
    if (!loading && sessions.length === 0) {
      newSession();
    }
  }, [loading, sessions.length, newSession]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex h-[calc(100vh-4rem)] overflow-hidden rounded-xl border border-border bg-background shadow-sm"
    >
      {/* Session sidebar */}
      <ChatSessionList
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={selectSession}
        onNew={newSession}
      />

      {/* Main chat area */}
      <div className="flex flex-1 flex-col">
        {/* Header bar */}
        <div className="flex items-center justify-between border-b border-border px-6 py-3">
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              AI Assistant
            </h1>
            <p className="text-xs text-muted-foreground">
              Ask anything about your contacts, deals & pipeline
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs">
            {wsStatus === "connected" ? (
              <>
                <Wifi size={14} className="text-emerald-500" />
                <span className="text-emerald-600 font-medium">Live</span>
              </>
            ) : wsStatus === "connecting" ? (
              <>
                <Loader2 size={14} className="animate-spin text-amber-500" />
                <span className="text-amber-600 font-medium">Connecting…</span>
              </>
            ) : (
              <>
                <WifiOff size={14} className="text-gray-400" />
                <span className="text-gray-500 font-medium">Offline</span>
              </>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 text-white shadow-lg">
                <span className="text-2xl font-bold">AI</span>
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-1">
                How can I help you today?
              </h2>
              <p className="text-sm max-w-sm">
                I can create contacts, manage deals, score leads, and
                summarise your CRM data. Just ask!
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {streaming && <ChatTypingIndicator />}

          {/* Auto-scroll anchor */}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={loading || streaming} />
      </div>
    </motion.div>
  );
}
