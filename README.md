# Chatbot

Um sistema de chatbot organizado em **monorepo**, com:

- **Frontend** em **React + JavaScript**
- **Backend** em **Python + FastAPI**
- **Arquitetura em camadas** no backend
- Suporte a **RAG (Retrieval-Augmented Generation)** com embeddings

---

## Visão Geral da Arquitetura

Este repositório está estruturado como um monorepo com duas aplicações principais:

- `frontend/` → interface web
- `backend/` → API, regras de negócio, integrações e núcleo do chatbot

```text
Chatbot/
├── frontend/                         # Frontend em React + JavaScript
│   ├── public/
│   ├── src/
│   │   ├── pages/                    # Páginas da aplicação
│   │   │   ├── Login.jsx
│   │   │   └── admin/
│   │   │       ├── DocumentsList.jsx
│   │   │       ├── DocumentCreate.jsx
│   │   │       ├── DocumentEdit.jsx
│   │   │       └── Categories.jsx
│   │   ├── components/               # Componentes reutilizáveis
│   │   │   ├── Layout.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── DocumentForm.jsx
│   │   │   └── ConfirmDialog.jsx
│   │   ├── services/                 # Camada de consumo da API
│   │   │   ├── api.js
│   │   │   ├── authService.js
│   │   │   └── documentService.js
│   │   ├── routes/
│   │   │   └── AppRoutes.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── README.md
│
├── backend/                          # Backend em Python + FastAPI
│   ├── app/
│   │   ├── main.py                   # Ponto de entrada da aplicação FastAPI
│   │   │
│   │   ├── api/                      # Camada HTTP
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── categories.py
│   │   │   │   └── users.py
│   │   │   ├── schemas/
│   │   │   │   ├── auth_schema.py
│   │   │   │   ├── document_schema.py
│   │   │   │   ├── category_schema.py
│   │   │   │   └── user_schema.py
│   │   │   └── deps.py
│   │   │
│   │   ├── application/              # Casos de uso
│   │   │   ├── create_document.py
│   │   │   ├── list_documents.py
│   │   │   ├── update_document.py
│   │   │   ├── delete_document.py
│   │   │   ├── login_admin.py
│   │   │   ├── answer_question.py
│   │   │   └── index_document.py
│   │   │
│   │   ├── domain/                   # Regras centrais de negócio
│   │   │   ├── entities/
│   │   │   │   ├── document.py
│   │   │   │   ├── category.py
│   │   │   │   ├── user.py
│   │   │   │   └── profile.py
│   │   │   └── repositories/
│   │   │       ├── document_repository.py
│   │   │       ├── category_repository.py
│   │   │       └── user_repository.py
│   │   │
│   │   ├── infrastructure/           # Integrações externas
│   │   │   ├── database/
│   │   │   │   ├── connection.py
│   │   │   │   └── models/
│   │   │   │       ├── document_model.py
│   │   │   │       ├── category_model.py
│   │   │   │       ├── user_model.py
│   │   │   │       └── profile_model.py
│   │   │   ├── repositories/
│   │   │   │   ├── sql_document_repository.py
│   │   │   │   ├── sql_category_repository.py
│   │   │   │   └── sql_user_repository.py
│   │   │   ├── security/
│   │   │   │   ├── password_hasher.py
│   │   │   │   └── token_service.py
│   │   │   ├── indexing/
│   │   │   │   └── document_indexer.py
│   │   │   ├── embeddings/
│   │   │   ├── llm/
│   │   │   └── vectorstore/
│   │   │
│   │   └── config/
│   │       └── settings.py
│   │
│   ├── tests/
│   │   ├── api/
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   ├── requirements.txt
│   └── README.md
│
├── docs/
│   ├── arquitetura.md
│   ├── backlog.md
│   └── api.md
│
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│
├── README.md
└── .gitignore