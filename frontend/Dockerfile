FROM node:20-alpine

WORKDIR /app/frontend

EXPOSE 5173

# Este Dockerfile ja deixa o frontend preparado para a proxima fase.
# Quando o app Vite for criado, basta adicionar package.json, instalar
# as dependencias e manter o mesmo compose.
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]
