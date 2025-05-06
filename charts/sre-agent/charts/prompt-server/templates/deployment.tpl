apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-prompt-server
  namespace: {{ .Values.global.namespace }}
  labels:
    app: mcp-prompt-server
spec:
  replicas: {{ .Values.deployment.replicaCount }}
  selector:
    matchLabels:
      app: mcp-prompt-server
  template:
    metadata:
      labels:
        app: mcp-prompt-server
    spec:
      containers:
        - name: mcp-prompt-server
          image: "{{ .Values.global.containerRegistryAddress }}mcp/prompt-server:{{ .Values.deployment.image.tag | default "latest" }}"
          imagePullPolicy: {{ .Values.deployment.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.deployment.containerPort }}
          env:
            - name: GITHUB_ORGANISATION
              value: {{ .Values.github.organisation }}
            - name: GITHUB_REPO_NAME
              value: {{ .Values.github.repoName }}
            - name: PROJECT_ROOT
              value: {{ .Values.github.projectRoot }}
