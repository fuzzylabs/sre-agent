apiVersion: apps/v1
kind: Deployment
metadata:
  name: sre-orchestrator
  namespace: {{ .Values.global.namespace }}
  labels:
    app: {{ .Values.global.namespace }}
spec:
  replicas: {{ .Values.deployment.replicaCount }}
  selector:
    matchLabels:
      app: sre-orchestrator
  template:
    metadata:
      labels:
        app: sre-orchestrator
    spec:
      containers:
        - name: sre-orchestrator
          image: "{{ .Values.global.containerRegistryAddress }}mcp/sre-orchestrator:{{ .Values.deployment.image.tag | default "latest" }}"
          imagePullPolicy: {{ .Values.deployment.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.deployment.containerPort }}
          env:
            - name: CHANNEL_ID
              valueFrom:
                secretKeyRef:
                  name: "{{ .Release.Name }}-secret"
                  key: CHANNEL_ID
            - name: TOOLS
              value: '["list_pods", "get_logs", "get_file_contents", "slack_post_message"]'
            - name: QUERY_TIMEOUT
<<<<<<< HEAD:charts/sre-agent/charts/orchestrator/templates/deployment.tpl
              value: "{{ .Values.deployment.timeout }}"
=======
              value: "300"
>>>>>>> origin/main:k8s/sre-orchestrator.yaml
            - name: DEV_BEARER_TOKEN
              valueFrom:
                secretKeyRef:
                  name: "{{ .Release.Name }}-secret"
                  key: DEV_BEARER_TOKEN
            - name: SLACK_SIGNING_SECRET
              valueFrom:
                secretKeyRef:
                  name: "{{ .Release.Name }}-secret"
                  key: SLACK_SIGNING_SECRET
