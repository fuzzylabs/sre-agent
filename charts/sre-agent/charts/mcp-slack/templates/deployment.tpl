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
          image: "{{ .Values.global.containerRegistryAddress }}mcp/slack:latest"
          imagePullPolicy: {{ .Values.deployment.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.deployment.containerPort }}
          env:
            - name: GITHUB_PERSONAL_ACCESS_TOKEN
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.global.secretKeyRef }}
                  key: GITHUB_PERSONAL_ACCESS_TOKEN
