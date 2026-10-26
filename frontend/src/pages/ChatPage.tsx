import { useEffect } from "react";
import { motion } from "framer-motion";
import { Wifi, WifiOff, Loader2 } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useChatStore } from "@/stores/chatStore";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatTypingIndicator } from "@/components/chat/ChatTypingIndicator";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatSessionList } from "@/components/chat/ChatSessionList";
import { ConfirmationCard } from "@/components/chat/ConfirmationCard";

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

  const { pendingConfirmation, setPendingConfirmation } = useChatStore();

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
      className="flex h-[calc(100dvh-12rem)] min-w-0 flex-col overflow-hidden border-y border-border md:h-[calc(100dvh-8.5rem)] md:flex-row md:border-y-0"
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
        <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 md:px-6">
          <div className="min-w-0">
            <h1 className="font-serif text-xl leading-tight">AI Assistant</h1>
            <p className="text-xs text-muted-foreground">Ask anything about your contacts, deals & pipeline</p>
          </div>
          <div className="flex shrink-0 items-center gap-1.5 text-xs">
            {wsStatus === "connected" ? (
              <>
                <Wifi size={14} aria-hidden="true" className="text-success" />
                <span role="status" className="font-medium text-success">Live</span>
              </>
            ) : wsStatus === "connecting" ? (
              <>
                <Loader2 size={14} aria-hidden="true" className="animate-spin text-warning" />
                <span role="status" className="font-medium text-warning">Connecting…</span>
              </>
            ) : (
              <>
                <WifiOff size={14} aria-hidden="true" className="text-muted-foreground" />
                <span role="status" className="font-medium text-muted-foreground">Offline</span>
              </>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 space-y-1 overflow-y-auto px-4 py-6">
          {messages.length === 0 && !loading && (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-muted-foreground">
              <h2 className="font-serif text-2xl text-foreground">How can I help you today?</h2>
              <p className="max-w-sm text-sm">
                I can create contacts, manage deals, score leads, and summarise your CRM data. Just ask!
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {streaming && <ChatTypingIndicator />}

          {/* Confirmation card */}
          {pendingConfirmation && (
            <ConfirmationCard
              confirmation={pendingConfirmation}
              onConfirm={() => setPendingConfirmation(null)}
              onDismiss={() => setPendingConfirmation(null)}
            />
          )}

          {/* Auto-scroll anchor */}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={loading || streaming} />
      </div>
    </motion.div>
  );
}
