FROM node:current-trixie-slim

WORKDIR /frontend
COPY package.json package-lock.json ./
RUN npm ci

# Make the workdir owned by the built-in node user
RUN chown -R node:node /frontend

USER node

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]