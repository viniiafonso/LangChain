# Chatbot Gestão de Cuidado

Projeto enxuto de chatbot para acompanhamento clínico com:

- medicamentos em uso
- consultas
- pressão arterial
- alergias
- leitura de exames em PDF

O chatbot funciona em dois modos:

- terminal (`main.py`)
- web (`web_chat.py` + `index.html`)

## Estrutura final do projeto

- `src/chatbot/core.py`: núcleo do chatbot e integração com a LLM
- `src/chatbot/web.py`: servidor HTTP local + API `/api/chat`
- `src/chatbot/static/index.html`: interface web futurista
- `main.py`: entrypoint compatível para chat no terminal
- `web_chat.py`: entrypoint compatível para chat web
- `tests/`: testes unitários
- `docs/`: documentação didática
- `documentos/`: PDFs usados como base para contexto de exames

## Configuração rápida

### 1) Criar ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Instalar dependências

```bash
pip install -r requirements.txt
```

### 3) Configurar `.env`

```bash
OPENAI_API_KEY="local-key"
LOCAL_LLM_MODEL="allura-forge_llama-3.3-8b-instruct"
LOCAL_LLM_BASE_URL="http://127.0.0.1:1234"
```

> O código adiciona `/v1` automaticamente na URL quando necessário.

## Executar

### Chat no terminal

```bash
python main.py
```

### Chat no navegador

```bash
python web_chat.py
```

Abra:

```text
http://127.0.0.1:8000
```

## Testes

```bash
python -m unittest tests/test_main.py tests/test_web_chat.py
```

## Guia detalhado para iniciantes

Consulte o arquivo `docs/EXPLICACAO_CHATBOT.md` para uma explicação didática de cada arquivo e cada método, pensada para quem está começando em IA.
