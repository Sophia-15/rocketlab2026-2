# 🚀 Rocket Movies

Sistema completo de catálogo e avaliação de filmes desenvolvido como parte do escopo de projeto da Visagio, inspirado na identidade visual, experiência de utilizador (*UX*) e minimalismo do Letterboxd.

---

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python, FastAPI, SQLAlchemy (Async), SQLite.
* **Frontend:** React, TypeScript, Vite, Tailwind CSS, React Router DOM.

---

## ⚙️ Como Executar o Projeto Localmente

Para rodar a aplicação na sua máquina, você precisará ter o **Python** (versão 3.10+) e o **Node.js** (versão 18+) instalados.

O projeto está dividido em duas partes: a API (Backend) e a Interface (Frontend). Abra **dois terminais separados** no diretório raiz do projeto para iniciar os servidores.

---

### 1. Configurando e Executando o Backend

1. Entre na pasta do backend:
   ´´´bash
   cd backend

2. Crie e ative um ambiente virtual Python:
   python -m venv .venv

   No Windows (PowerShell):
   .venv\Scripts\Activate

   No Mac/Linux:
   source .venv/bin/activate

3. Instale as dependências necessárias:
    pip install -r requirements.txt

4. Inicie o servidor da API (Uvicorn):
    uvicorn app.main:app --reload

### 2. Configurando e Executando o Frontend

1. No segundo terminal, abra a pasta do frontend:
   cd frontend

2. Instale as dependências do Node:
    npm install

3. Inicie o servidor de desenvolvimento padrão do Vite:
    npm run dev

4. Abra o link fornecido no terminal (geralmente http://localhost:5173) no seu navegador.

### Base de Dados e Seeding

O projeto utiliza SQLite para persistência de dados. O ficheiro da base de dados é gerado e configurado automaticamente pelo SQLAlchemy na primeira execução do backend, garantindo que o avaliador não precise de configurar servidores externos (como PostgreSQL ou Docker) para testar a aplicação.
