FROM node:22-alpine

WORKDIR /app/packages/web

# Install dependencies first for Docker layer caching
COPY package*.json ./
RUN npm install

# Copy frontend source files
COPY . .

EXPOSE 5173

# Vite development server with host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
