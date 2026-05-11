FROM node:20-alpine AS builder
WORKDIR /build
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine AS runtime
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /build/node_modules ./node_modules
COPY . .
RUN chown -R appuser:appgroup /app
USER appuser
ENV NODE_ENV=production PORT=4000
EXPOSE 4000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:4000/health || exit 1
CMD ["node", "server.js"]
