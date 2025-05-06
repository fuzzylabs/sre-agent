{{- if .Values.enabled }}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-github
  namespace: {{ .Values.global.namespace }}
  labels:
    app: mcp-github
spec:
  replicas: {{ .Values.deployment.replicaCount }}
  selector:
    matchLabels:
      app: mcp-github
  template:
    metadata:
      labels:
        app: mcp-github
    spec:
      containers:
        - name: mcp-github
          image: "{{ .Values.global.containerRegistryAddress }}mcp/github:{{ .Values.deployment.image.tag | default "latest" }}"
          imagePullPolicy: {{ .Values.deployment.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.deployment.containerPort }}
          env:
            - name: GITHUB_PERSONAL_ACCESS_TOKEN
              valueFrom:
                secretKeyRef:
                  name: "{{ .Release.Name }}-secret"
                  key: GITHUB_PERSONAL_ACCESS_TOKEN
{{- end }}
