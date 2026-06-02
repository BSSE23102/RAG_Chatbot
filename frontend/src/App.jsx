import { useEffect, useMemo, useRef, useState } from 'react';

const STORAGE_KEY = 'rag-chat-session-id';

function createSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function loadSessionId() {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored && stored.trim()) {
    return stored;
  }

  const nextSessionId = createSessionId();
  window.localStorage.setItem(STORAGE_KEY, nextSessionId);
  return nextSessionId;
}

function App() {
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [status, setStatus] = useState('Connecting to backend...');
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const transcriptRef = useRef(null);

  useEffect(() => {
    const nextSessionId = loadSessionId();
    setSessionId(nextSessionId);
    setMessages([{ role: 'assistant', content: 'Ask a question about the document to begin.' }]);
  }, []);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (transcript) {
      transcript.scrollTop = transcript.scrollHeight;
    }
  }, [messages, isSending]);

  useEffect(() => {
    let isMounted = true;

    async function checkHealth() {
      try {
        const response = await fetch('/health');
        if (!response.ok) {
          throw new Error(`Health check failed with ${response.status}`);
        }

        if (isMounted) {
          setStatus('Backend ready');
        }
      } catch (error) {
        if (isMounted) {
          setStatus('Backend unavailable. Start FastAPI on port 8000.');
        }
      }
    }

    checkHealth();

    return () => {
      isMounted = false;
    };
  }, []);

  const sourceCount = useMemo(() => {
    const lastAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === 'assistant' && Array.isArray(message.sources));

    return lastAssistantMessage?.sources?.length ?? 0;
  }, [messages]);

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedInput = input.trim();
    if (!trimmedInput || isSending) {
      return;
    }

    setMessages((current) => [...current, { role: 'user', content: trimmedInput }]);
    setInput('');
    setIsSending(true);
    setStatus('Thinking with retrieved context...');

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: trimmedInput
        })
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Request failed with ${response.status}`);
      }

      const payload = await response.json();
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: payload.answer || 'No answer returned.',
          sources: payload.sources || []
        }
      ]);
      setStatus('Backend ready');
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: `Unable to answer right now: ${error.message}`,
          sources: []
        }
      ]);
      setStatus('Chat request failed');
    } finally {
      setIsSending(false);
    }
  }

  function resetConversation() {
    const nextSessionId = createSessionId();
    window.localStorage.setItem(STORAGE_KEY, nextSessionId);
    setSessionId(nextSessionId);
    setMessages([{ role: 'assistant', content: 'Session reset. Ask a new question.' }]);
    setStatus('Session reset');
    setSourcesOpen(false);
  }

  return (
    <div className="shell">
      <main className="app-frame">
        <section className="hero-panel">
          <div>
            <div className="eyebrow">History-Aware RAG Chatbot</div>
            <h1>Ask the document. Follow up naturally. Keep the context alive.</h1>
            <p>
              React frontend for a FastAPI-backed retrieval system. The assistant uses the
              knowledge document, retrieved chunks, and your chat history to answer follow-up
              questions more accurately.
            </p>
          </div>

          <div className="hero-footer">
            <div className="status-row">
              <span className={`status-dot ${status === 'Backend ready' ? 'ready' : 'pending'}`} />
              <span>{status}</span>
              <span className="session-pill">Session {sessionId ? sessionId.slice(0, 8) : '...'}</span>
            </div>

            <div className="hero-actions">
              <button type="button" className="secondary-button" onClick={resetConversation}>
                Reset conversation
              </button>
              <div className="source-counter">Sources shown: {sourceCount}</div>
            </div>
          </div>
        </section>

        <section className="chat-panel">
          <div className="chat-header">
            <div>
              <h2>Conversation</h2>
              <p>Messages are stored in the browser and sent with the current session id.</p>
            </div>
            <button
              type="button"
              className="ghost-button"
              onClick={() => setSourcesOpen((current) => !current)}
              disabled={sourceCount === 0}
            >
              {sourcesOpen ? 'Hide sources' : 'Show sources'}
            </button>
          </div>

          <div className="message-list" ref={transcriptRef} aria-live="polite">
            {messages.map((message, index) => (
              <article key={`${message.role}-${index}`} className={`message ${message.role}`}>
                <div className="message-label">{message.role === 'user' ? 'You' : 'Assistant'}</div>
                <div className="message-content">{message.content}</div>
                {message.role === 'assistant' && Array.isArray(message.sources) && message.sources.length > 0 && sourcesOpen ? (
                  <details className="source-list" open={sourcesOpen}>
                    <summary>Retrieved context chunks</summary>
                    <ul>
                      {message.sources.map((source, sourceIndex) => (
                        <li key={`${source.source ?? 'source'}-${sourceIndex}`}>
                          <div className="source-path">{source.source || 'Unknown source'}</div>
                          <div className="source-text">{source.content}</div>
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : null}
              </article>
            ))}

            {isSending ? (
              <article className="message assistant typing">
                <div className="message-label">Assistant</div>
                <div className="message-content">Retrieving context and composing an answer...</div>
              </article>
            ) : null}
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about the document or continue the conversation..."
              rows={3}
            />
            <div className="composer-actions">
              <div className="composer-hint">Enter to send, Shift+Enter for a new line</div>
              <button type="submit" className="primary-button" disabled={isSending || !input.trim()}>
                {isSending ? 'Sending...' : 'Send'}
              </button>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}

export default App;