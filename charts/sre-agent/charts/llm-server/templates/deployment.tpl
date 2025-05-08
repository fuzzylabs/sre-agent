apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-server
  namespace: {{ .Values.global.namespace }}
  labels:
    app: llm-server
spec:
  replicas: {{ .Values.deployment.replicaCount | default 1 }}
  selector:
    matchLabels:
      app: llm-server
  template:
    metadata:
      labels:
        app: llm-server
    spec:
      containers:
        - name: llm-server
          image: "{{ .Values.global.containerRegistryAddress }}mcp/llm-server:{{ .Values.deployment.image.tag | default "latest" }}"
          imagePullPolicy: {{ .Values.deployment.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.deployment.containerPort | default 80 }}
          env:
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef:
                  name: "{{ .Release.Name }}-secret"
                  key: ANTHROPIC_API_KEY
            - name: PROVIDER
              value: {{ .Values.deployment.provider }}
            - name: MODEL
              value: {{ .Values.deployment.model }}
            - name: MAX_TOKENS
              value: "{{ .Values.deployment.maxTokens }}"
            - name: TRANSPORT
              value: {{ .Values.global.transport }}
