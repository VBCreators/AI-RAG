# AI RAG — Chat Streaming Service

A production-oriented FastAPI service providing Server-Sent Events (SSE) streaming chat completions powered by LangChain and Google Gemini (swappable LLM provider).

---

## Features

- **SSE Streaming Endpoint:** `POST /api/v1/chat/stream` streams token chunks in real-time.
- **Modular System Prompt:** Assembled at runtime from configurable components (Persona, Domain expertise, Guardrails, Word limit constraint).
- **Swappable LLM Provider:** Decoupled through `LLMPort` protocol and `LangChainLLMAdapter` wrapping `BaseChatModel`.
- **Structured Logging:** Contextual logging powered by `structlog` with request correlation IDs (`X-Request-ID`).
- **Strict Validation:** Pydantic v2 schemas (`ChatRequest`, `ChatStreamChunk`, `ErrorResponse`) with `extra="forbid"`.
- **Ports & Adapters Architecture:** Domain business logic separated from HTTP routing and infrastructure SDKs.

---

## Requirements

- Python >= 3.14
- [`uv`](https://docs.astral.sh/uv/) package manager

---

## Getting Started

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure Environment

Copy `.env.example` to `.env` and set your Google AI API key:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Only overrides + secrets
DEBUG=true
ENV=dev
GOOGLE_API_KEY=your-gemini-api-key
```

### 3. Run the Development Server

```bash
uv run uvicorn ai_rag.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Usage

### Stream Chat Completion (`POST /api/v1/chat/stream`)

#### Request

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain quantum computing in simple terms."}'
```

#### SSE Stream Format

**Token chunk event:**
```
event: token
data: {"content": "Quantum", "chunk_index": 0}

event: token
data: {"content": " computing", "chunk_index": 1}
```

**Stream completion event:**
```
event: done
data: {"content": "[DONE]"}
```

**Stream error event (if provider fails mid-stream):**
```
event: error
data: {"error": "llm_error", "message": "An error occurred while generating response", "request_id": "abc-123"}
```

---

## JavaScript Client Example

```javascript
const response = await fetch("http://localhost:8000/api/v1/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "What is Python?" }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split("\n");

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("event: error")) {
      const dataLine = lines[i + 1];
      console.error("SSE Error:", JSON.parse(dataLine.replace("data: ", "")));
    } else if (line.startsWith("event: token")) {
      const dataLine = lines[i + 1];
      const payload = JSON.parse(dataLine.replace("data: ", ""));
      process.stdout.write(payload.content);
    }
  }
}
```

---

## Running Tests & Type Checks

```bash
# Run pytest test suite
uv run pytest tests/ -v

# Run static type checking
uv run mypy src tests
```
