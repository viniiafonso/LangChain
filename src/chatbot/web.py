import json
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .core import ask_chatbot, build_model, default_care_data, load_pdf_exam_texts, parse_pressure_input

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def is_pressure_message(text: str) -> bool:
    normalized = normalize_text(text)
    return "pressao" in normalized or "press" in normalized


def parse_message_payload(payload: dict[str, Any]) -> str | None:
    message = payload.get("message")
    if not isinstance(message, str):
        return None

    cleaned = message.strip()
    return cleaned or None


@dataclass
class CareChatState:
    care_data: dict[str, Any] = field(default_factory=default_care_data)
    exam_texts: dict[str, str] = field(default_factory=lambda: load_pdf_exam_texts(REPO_ROOT / "documentos"))
    history: list[tuple[str, str]] = field(default_factory=lambda: [])
    model: Any = field(default_factory=build_model)

    def chat(self, query: str) -> str:
        pressure = parse_pressure_input(query)
        if pressure and is_pressure_message(query):
            self.care_data["pressao_arterial"].append(
                {
                    "data": datetime.now().strftime("%Y-%m-%d"),
                    "sistolica": pressure["sistolica"],
                    "diastolica": pressure["diastolica"],
                }
            )
            answer = (
                f"Pressão registrada: {pressure['sistolica']}/{pressure['diastolica']} mmHg. "
                "Deseja que eu analise a tendência recente?"
            )
            self.history.append((query, answer))
            return answer

        try:
            answer = ask_chatbot(
                model=self.model,
                care_data=self.care_data,
                exam_texts=self.exam_texts,
                history=self.history,
                query=query,
            )
        except Exception as exc:
            answer = (
                "Não consegui acessar o modelo local agora. "
                "Confirme se o servidor está ativo em http://127.0.0.1:1234. "
                f"Detalhe técnico: {exc}"
            )

        self.history.append((query, answer))
        return answer


class CareChatHandler(SimpleHTTPRequestHandler):
    state: CareChatState | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Endpoint não encontrado."})
            return

        if self.state is None:
            self._send_json(500, {"error": "Estado do chatbot não inicializado."})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "JSON inválido."})
            return

        message = parse_message_payload(payload)
        if not message:
            self._send_json(400, {"error": "Campo 'message' é obrigatório."})
            return

        answer = self.state.chat(message)
        self._send_json(
            200,
            {
                "reply": answer,
                "historySize": len(self.state.history),
            },
        )


def run_web_chat(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    state = CareChatState()
    CareChatHandler.state = state

    server = ThreadingHTTPServer((host, port), CareChatHandler)
    print(f"Gestão de Cuidado Web disponível em http://{host}:{port}")
    print("Pressione Ctrl+C para encerrar.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
