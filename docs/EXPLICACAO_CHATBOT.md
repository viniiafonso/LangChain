# Explicação didática do projeto (para iniciantes em IA)

Este arquivo explica **cada arquivo** e **cada método/função** do chatbot de forma simples.

A ideia do projeto é: você conversa com um assistente de saúde chamado **Gestão de Cuidado**.
Ele responde com base em dados do paciente (medicamentos, consultas, pressão, alergias) e também pode usar conteúdo de exames em PDF.

---

## 1) Visão geral da arquitetura

Pense no sistema como 3 blocos:

1. **Cérebro** (`main.py`)  
   Onde mora a lógica do chatbot e a chamada da IA.

2. **Porta de entrada web** (`web_chat.py`)  
   Um mini servidor que recebe mensagens da página e chama o cérebro.

3. **Tela do usuário** (`index.html`)  
   Interface bonita para digitar e ver respostas.

Testes ficam em `tests/`, e os PDFs ficam em `documentos/`.

---

## 2) Arquivo por arquivo

## `main.py` (núcleo do chatbot)

Este é o arquivo principal da inteligência do sistema.

### `normalize_base_url(url: str) -> str`
**O que faz:** garante que a URL da IA termine em `/v1` quando o endpoint é compatível com OpenAI.  
**Por que foi usado:** muitos servidores locais (como LM Studio) seguem o padrão OpenAI e esperam esse sufixo.

---

### `parse_pressure_input(text: str) -> dict[str, int] | None`
**O que faz:** tenta achar pressão arterial na frase do usuário (ex.: `130/80` ou `13/8`).  
**Por que foi usado:** facilita o uso real. Pessoas escrevem de formas diferentes e o sistema aceita essas variações.

Se encontrar valores válidos, devolve:
- `{"sistolica": ..., "diastolica": ...}`

Se não encontrar, devolve `None`.

---

### `load_pdf_exam_texts(exams_folder: Path) -> dict[str, str]`
**O que faz:** lê os arquivos PDF da pasta `documentos/` e extrai texto.  
**Por que foi usado:** o chatbot consegue trazer contexto dos exames sem precisar treinar um modelo novo.

Retorna um dicionário no formato:
- chave = nome do arquivo PDF
- valor = texto extraído do PDF

---

### `search_exam_snippets(exams, query, limit=2) -> list[str]`
**O que faz:** busca palavras da pergunta do usuário dentro dos textos dos exames e retorna os trechos mais relevantes.  
**Por que foi usado:** é uma forma simples de “RAG leve” (buscar contexto antes de perguntar para a IA), melhorando a precisão.

---

### `default_care_data() -> dict[str, Any]`
**O que faz:** cria os dados iniciais do paciente (nome, idade, doenças, medicamentos, consultas, pressão e alergias).  
**Por que foi usado:** deixa o sistema pronto para rodar sem depender de banco de dados logo no início.

---

### `build_model() -> ChatOpenAI`
**O que faz:** monta o cliente da LLM usando variáveis de ambiente (`LOCAL_LLM_MODEL`, `LOCAL_LLM_BASE_URL`, `OPENAI_API_KEY`).  
**Por que foi usado:** separa configuração de modelo do restante da lógica e facilita troca de modelo/servidor.

---

### `build_system_prompt() -> str`
**O que faz:** define as regras fixas de comportamento da IA (responder em português, foco em segurança, etc.).  
**Por que foi usado:** o prompt de sistema dá “personalidade e regras” ao assistente.

---

### `build_human_prompt(today, care_data, exam_context, history_text, query) -> str`
**O que faz:** monta a mensagem dinâmica com os dados do paciente + trechos dos exames + histórico + pergunta atual.  
**Por que foi usado:** a IA responde melhor quando recebe o contexto organizado.

---

### `ask_chatbot(model, care_data, exam_texts, history, query) -> str`
**O que faz:** é a função central de resposta.

Passos internos:
1. busca trechos relevantes dos PDFs
2. monta histórico recente
3. cria mensagem completa
4. chama a LLM
5. devolve o texto final

**Por que foi usado:** concentra o fluxo principal em um único lugar reutilizável (CLI e web usam isso).

---

### `run_chat() -> None`
**O que faz:** roda o chatbot no terminal em loop.

- lê pergunta
- detecta pressão e registra
- se não for registro de pressão, chama a IA
- mostra resposta

**Por que foi usado:** modo simples para testar e usar sem navegador.

---

## `web_chat.py` (servidor web + API)

Este arquivo abre um servidor local para usar o chatbot no navegador.

### `normalize_text(text: str) -> str`
**O que faz:** remove acentos e coloca em minúsculo.  
**Por que foi usado:** ajuda a reconhecer palavras mesmo se o usuário digitar com/sem acento.

---

### `is_pressure_message(text: str) -> bool`
**O que faz:** detecta se a frase parece falar de pressão arterial.  
**Por que foi usado:** para ativar o fluxo de registro de pressão automaticamente.

---

### `parse_message_payload(payload: dict) -> str | None`
**O que faz:** valida se o JSON recebido possui `message` como texto válido.  
**Por que foi usado:** evita erro quando o frontend envia algo inválido.

---

### `CareChatState` (classe com estado da conversa)
**O que guarda:**
- dados do paciente
- textos dos exames
- histórico
- modelo da IA

#### Método `chat(self, query: str) -> str`
**O que faz:** processa uma pergunta e devolve a resposta.

- Se for pressão, registra e confirma.
- Caso contrário, chama `ask_chatbot` do `main.py`.

**Por que foi usado:** mantém estado em memória e separa lógica de negócio da lógica HTTP.

---

### `CareChatHandler` (classe HTTP)
Herdada de `SimpleHTTPRequestHandler`.

#### `_send_json(status_code, payload)`
Envia resposta JSON com headers corretos.

#### `do_OPTIONS()`
Responde pré-voo CORS.

#### `do_GET()`
Entrega `index.html` quando usuário abre `/`.

#### `do_POST()`
Trata o endpoint `/api/chat`:
- lê JSON
- valida `message`
- chama estado (`state.chat`)
- devolve resposta em JSON

**Por que foi usado:** implementa API mínima sem frameworks externos (simples e didático).

---

### `run_web_chat(host, port) -> None`
**O que faz:** inicializa estado, sobe servidor e mantém rodando.  
**Por que foi usado:** ponto único para iniciar o modo web.

---

## `index.html` (interface de chat)

Página única com HTML + CSS + JavaScript.

### Parte visual (CSS)
Paleta futurista solicitada:
- roxo
- ciano
- preto
- branco
- cinza

Objetivo visual: parecer moderno, legível e agradável.

### Funções JavaScript

#### `addMessage(role, text)`
Cria bolha no chat (`user` ou `bot`).

#### `setStatus(text, isError = false)`
Atualiza badge de status (Online, Processando, Falha).

#### `sendMessage()`
Fluxo principal do frontend:
1. pega texto digitado
2. mostra mensagem do usuário
3. chama `POST /api/chat`
4. mostra resposta
5. trata erro de conexão

Também há eventos:
- clique no botão Enviar
- tecla Enter para enviar

**Por que foi usado:** experiência rápida e simples para uso real.

---

## `tests/test_main.py`

Testa funções utilitárias do núcleo:
- normalização de URL
- parser de pressão (incluindo `13/8`)
- busca de trechos em exames

**Por que foi usado:** garante que regras importantes continuem funcionando após mudanças.

---

## `tests/test_web_chat.py`

Testa utilitários do modo web:
- normalização de texto com acento
- detecção de mensagem de pressão
- validação do payload JSON

**Por que foi usado:** evita regressões na camada de entrada HTTP.

---

## `requirements.txt`

Lista dependências necessárias para o chatbot final:
- `langchain`, `langchain-openai`, `openai`: integração com LLM
- `python-dotenv`: carregar variáveis do `.env`
- `pypdf`: ler PDFs
- `pydantic`: tipagem/secret para integração segura

---

## 3) Como tudo acontece, passo a passo

Quando você usa a web (`index.html`):

1. Você digita uma mensagem.
2. JavaScript envia para `POST /api/chat` no `web_chat.py`.
3. `web_chat.py` valida a entrada.
4. Ele chama `CareChatState.chat()`.
5. Se for pressão, registra direto.
6. Se for pergunta geral, chama `ask_chatbot()` do `main.py`.
7. `main.py` monta contexto (dados + exames + histórico).
8. A LLM responde.
9. Resposta volta para o navegador.

---

## 4) Por que esse desenho foi escolhido

- **Simples de entender:** sem banco de dados, sem framework pesado.
- **Fácil de evoluir:** dá para trocar a LLM sem reescrever tudo.
- **Didático:** separa bem as responsabilidades (núcleo, web, interface).
- **Prático:** já funciona em terminal e navegador.

---

## 5) Próximos passos para evoluir (opcional)

1. Persistir histórico em arquivo JSON.
2. Adicionar autenticação para múltiplos usuários.
3. Salvar dados clínicos em banco de dados.
4. Melhorar busca em PDFs com embeddings e vetor.
5. Criar painel de administração para equipe clínica.
