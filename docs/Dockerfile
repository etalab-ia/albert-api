
# syntax=docker/dockerfile:1

FROM node:lts-alpine AS base
ENV FORCE_COLOR=0
RUN corepack enable

FROM base AS deps
WORKDIR /opt/docusaurus
COPY package.json yarn.lock* ./
RUN yarn install --immutable --frozen-lockfile

FROM base AS dev
WORKDIR /opt/docusaurus
EXPOSE 3000
CMD [ -d "node_modules" ] && yarn start --host 0.0.0.0 --poll 1000 || yarn install && yarn start --host 0.0.0.0 --poll 1000

FROM deps AS prod
ARG DOCUSAURUS_BASE_URL
WORKDIR /opt/docusaurus
COPY . /opt/docusaurus/
RUN yarn build

FROM prod AS serve
EXPOSE 3000
CMD ["yarn", "serve", "--host", "0.0.0.0", "--no-open"]

FROM caddy:2-alpine AS caddy
COPY --from=prod /opt/docusaurus/Caddyfile /etc/caddy/Caddyfile
COPY --from=prod /opt/docusaurus/build /var/docusaurus