import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_DIR = REPO_ROOT / "documentos"


def normalize_base_url(url: str) -> str:
    """Normaliza URL para endpoints compatíveis com OpenAI.

    Se a URL terminar sem caminho (ex.: http://127.0.0.1:1234), adiciona /v1.
    """
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned

    if re.match(r"^https?://[^/]+$", cleaned):
        return f"{cleaned}/v1"

    return cleaned


def parse_pressure_input(text: str) -> dict[str, int] | None:
    """Extrai medida de pressão arterial no formato 120/80."""
    match = re.search(r"(\d{1,3})\s*/\s*(\d{1,3})", text)
    if not match:
        return None

    sistolica = int(match.group(1))
    diastolica = int(match.group(2))

    # Aceita notação abreviada comum no Brasil, ex.: 13/8 -> 130/80.
    if 8 <= sistolica <= 26 and 5 <= diastolica <= 16:
        sistolica *= 10
        diastolica *= 10

    if not (70 <= sistolica <= 260 and 40 <= diastolica <= 160):
        return None

    return {"sistolica": sistolica, "diastolica": diastolica}


def load_pdf_exam_texts(exams_folder: Path) -> dict[str, str]:
    """Lê todos os PDFs de exames da pasta e devolve conteúdo por arquivo."""
    try:
        import importlib

        PdfReader = importlib.import_module("pypdf").PdfReader
    except Exception:
        return {}

    if not exams_folder.exists() or not exams_folder.is_dir():
        return {}

    contents: dict[str, str] = {}
    for pdf_file in sorted(exams_folder.glob("*.pdf")):
        try:
            reader = PdfReader(str(pdf_file))
            joined = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            if joined:
                contents[pdf_file.name] = joined
        except Exception:
            # Segue mesmo com PDFs corrompidos/ilegíveis.
            continue

    return contents


def search_exam_snippets(exams: dict[str, str], query: str, limit: int = 2) -> list[str]:
    """Busca trechos simples por palavra-chave dentro dos exames em PDF."""
    if not exams:
        return []

    terms = {
        token.lower()
        for token in re.findall(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9]+", query)
        if len(token) > 2
    }

    scored: list[tuple[int, str, str]] = []
    for file_name, content in exams.items():
        lowered = content.lower()
        score = sum(1 for term in terms if term in lowered)
        if score == 0 and terms:
            continue

        excerpt = content[:900].replace("\n", " ")
        scored.append((score, file_name, excerpt))

    if not scored:
        # fallback: envia ao menos o início do primeiro exame
        first_file, first_content = next(iter(exams.items()))
        return [f"{first_file}: {first_content[:900].replace(chr(10), ' ')}"]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [f"{file_name}: {excerpt}" for _, file_name, excerpt in scored[:limit]]


def default_care_data() -> dict[str, Any]:
    return {
        "paciente": {
            "nome": "Paciente Exemplo",
            "idade": 67,
            "condicoes": ["Hipertensão", "Diabetes tipo 2"],
        },
        "medicamentos_em_uso": [
            {"nome": "Losartana 50mg", "frequencia": "1x ao dia"},
            {"nome": "Metformina 850mg", "frequencia": "2x ao dia"},
        ],
        "consultas": [
            {"data": "2026-05-05", "especialidade": "Cardiologia", "status": "agendada"},
            {"data": "2026-05-12", "especialidade": "Clínico geral", "status": "agendada"},
        ],
        "pressao_arterial": [
            {"data": "2026-04-29", "sistolica": 128, "diastolica": 82},
            {"data": "2026-04-30", "sistolica": 132, "diastolica": 84},
        ],
        "alergias": ["Penicilina", "Dipirona"],
    }


def build_model() -> ChatOpenAI:
    load_dotenv()
    model_name = os.getenv("LOCAL_LLM_MODEL", "allura-forge_llama-3.3-8b-instruct")
    base_url = normalize_base_url(os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234"))
    api_key = os.getenv("OPENAI_API_KEY", "local-key")

    return ChatOpenAI(
        model=model_name,
        temperature=0.2,
        api_key=SecretStr(api_key),
        base_url=base_url,
    )


def build_system_prompt() -> str:
    return """
Você é um assistente do sistema Gestão de Cuidado.
Seu papel é orientar a equipe de cuidado com base APENAS nos dados fornecidos.

Regras:
- Priorize segurança do paciente.
- Responda em português, de forma clara e objetiva.
- Quando houver incerteza, diga que é necessário validar com profissional de saúde.
- Se perguntarem sobre exames, utilize os trechos dos PDFs disponíveis no contexto.
    """.strip()


def build_human_prompt(
    today: str,
    care_data: dict[str, Any],
    exam_context: str,
    history_text: str,
    query: str,
) -> str:
    return f"""
Data de referência: {today}

Dados estruturados do paciente:
{care_data}

Trechos de exames em PDF:
{exam_context}

Histórico recente da conversa:
{history_text}

Pergunta do usuário:
{query}
    """.strip()


def ask_chatbot(
    model: ChatOpenAI,
    care_data: dict[str, Any],
    exam_texts: dict[str, str],
    history: list[tuple[str, str]],
    query: str,
) -> str:
    snippets = search_exam_snippets(exam_texts, query, limit=2)
    exam_context = "\n".join(f"- {snippet}" for snippet in snippets) if snippets else "Sem exames em PDF disponíveis."

    history_text = "\n".join(
        f"Usuário: {user}\nAssistente: {assistant}" for user, assistant in history[-4:]
    ) or "Sem histórico anterior."

    today = datetime.now().strftime("%Y-%m-%d")
    human_prompt = build_human_prompt(
        today=today,
        care_data=care_data,
        exam_context=exam_context,
        history_text=history_text,
        query=query,
    )

    response = model.invoke(
        [
            SystemMessage(content=build_system_prompt()),
            HumanMessage(content=human_prompt),
        ]
    )
    content: Any = getattr(response, "content", "")
    return content if isinstance(content, str) else str(content)


def run_chat() -> None:
    care_data = default_care_data()
    exam_texts = load_pdf_exam_texts(DOCUMENTS_DIR)

    model = build_model()
    history: list[tuple[str, str]] = []

    print("=== Gestão de Cuidado | Chatbot ===")
    print("Digite sua pergunta ou 'sair' para encerrar.")
    print("Dica: você pode registrar pressão digitando algo como 'pressão 13/8'.\n")

    while True:
        query = input("Você: ").strip()
        if not query:
            continue

        if query.lower() in {"sair", "exit", "quit"}:
            print("Assistente: Até mais!")
            break

        pressure = parse_pressure_input(query)
        if pressure and "press" in query.lower():
            care_data["pressao_arterial"].append(
                {
                    "data": datetime.now().strftime("%Y-%m-%d"),
                    "sistolica": pressure["sistolica"],
                    "diastolica": pressure["diastolica"],
                }
            )
            ack = (
                f"Pressão registrada: {pressure['sistolica']}/{pressure['diastolica']} mmHg. "
                "Deseja que eu analise a tendência recente?"
            )
            history.append((query, ack))
            print(f"Assistente: {ack}\n")
            continue

        try:
            answer = ask_chatbot(model, care_data, exam_texts, history, query)
        except Exception as exc:
            answer = (
                "Não consegui acessar o modelo local agora. "
                "Confirme se o servidor está ativo em http://127.0.0.1:1234. "
                f"Detalhe técnico: {exc}"
            )

        history.append((query, answer))
        print(f"Assistente: {answer}\n")
