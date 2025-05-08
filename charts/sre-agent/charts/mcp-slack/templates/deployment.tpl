{{- if .Values.enabled }}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-slack
  namespace: {{ .Values.global.namespace }}
  labels:
    app: {{ .Values.global.namespace }}
spec:
  replicas: {{ .Values.deployment.replicaCount }}
  selector:
    matchLabels:
      app: mcp-slack
  template:
    metadata:
      labels:
        app: mcp-slack
    spec:
      containers:
        - name: mcp-slack
          image: "{{ .Values.global.containerRegistryAddress }}mcp/slack:{{ .Values.deployment.image.tag | default "latest" }}"
          imagePullPolicy: {{ .Values.deployment.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.deployment.containerPort }}
          env:
            - name: SLACK_BOT_TOKEN
              valueFrom:
                secretKeyRef:
                  name: "{{ .Release.Name }}-secret"
                  key: SLACK_BOT_TOKEN
            - name: SLACK_TEAM_ID
              valueFrom:
                secretKeyRef:
                  name: "{{ .Release.Name }}-secret"
                  key: SLACK_TEAM_ID
{{- end }}
