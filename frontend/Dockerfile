FROM node:18-alpine

WORKDIR /app

# Сначала копируем package.json
COPY package.json ./

# Устанавливаем зависимости
RUN npm install

# Копируем остальные файлы
COPY . .

EXPOSE 3000

CMD ["npm", "start"]