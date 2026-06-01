# syntax=docker/dockerfile:1.7
#
# Multi-stage Next.js Dockerfile for Cloud Run.
#
# Requires `output: "standalone"` in next.config.ts. Cloud Run looks for a
# container listening on $PORT (defaults to 8080).
#
# Build:  gcloud run deploy --source .  (Cloud Build does the heavy lifting)
# Or:     docker build -t aegis-frontend .  (if you want to build locally)

FROM node:20-bookworm-slim AS deps
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@latest --activate
COPY package.json pnpm-lock.yaml .npmrc* ./
RUN pnpm install --frozen-lockfile --prod=false

FROM node:20-bookworm-slim AS builder
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@latest --activate
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Demo mode is the default. To deploy in live mode, pass:
#   --build-arg NEXT_PUBLIC_AEGIS_MODE=live --build-arg NEXT_PUBLIC_AEGIS_API=https://...
ARG NEXT_PUBLIC_AEGIS_MODE=demo
ARG NEXT_PUBLIC_AEGIS_API=""
ENV NEXT_PUBLIC_AEGIS_MODE=${NEXT_PUBLIC_AEGIS_MODE}
ENV NEXT_PUBLIC_AEGIS_API=${NEXT_PUBLIC_AEGIS_API}
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:20-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=8080
ENV HOSTNAME=0.0.0.0

RUN groupadd --system --gid 1001 nodejs \
 && useradd --system --uid 1001 --gid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 8080
CMD ["node", "server.js"]
