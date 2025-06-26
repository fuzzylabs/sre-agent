FROM node:22-bookworm-slim AS base
WORKDIR /usr/local/app
COPY package.json .

# Installing kubectl and gcloud with gke-gcloud-auth-plugin for accessing GKE
RUN apt-get update && apt-get install -y curl
RUN apt-get install -y apt-transport-https ca-certificates curl gnupg
# Add k8s apt repository
RUN curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.32/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
RUN chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg
RUN echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.32/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
RUN chmod 644 /etc/apt/sources.list.d/kubernetes.list
# Add gcloud apt repository
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get update
RUN apt-get update && apt-get install -y awscli google-cloud-cli google-cloud-cli-gke-gcloud-auth-plugin kubectl netcat-openbsd

# Build the typescript code
FROM base AS dependencies
RUN npm install
COPY tsconfig.json .
COPY src ./src
RUN npm run build

# Create the final production-ready image
FROM base AS release
RUN useradd -m appuser && chown -R appuser /usr/local/app
ENV NODE_ENV=production
ENV PORT=3001
RUN npm install --only=production
COPY --from=dependencies /usr/local/app/dist ./dist

# Copy the startup script into the container
COPY startup.sh /usr/local/app/startup.sh
RUN chmod +x /usr/local/app/startup.sh

# Switch to the app user
USER appuser

# Run the startup script
CMD ["/bin/bash", "/usr/local/app/startup.sh"]
