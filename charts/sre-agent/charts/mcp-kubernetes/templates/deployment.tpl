{{- if .Values.enabled }}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-kubernetes
  namespace: {{ .Values.global.namespace }}
  labels:
    app: mcp-kubernetes
spec:
  replicas: {{ .Values.deployment.replicaCount | default 1 }}
  selector:
    matchLabels:
      app: mcp-kubernetes
  template:
    metadata:
      labels:
        app: mcp-kubernetes
    spec:
      serviceAccountName: {{ .Values.serviceAccount.name }}
      containers:
        - name: mcp-kubernetes
          image: "{{ .Values.global.containerRegistryAddress }}mcp/kubernetes:{{ .Values.deployment.image.tag | default "latest" }}"
          imagePullPolicy: {{ .Values.deployment.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.deployment.containerPort | default 3001 }}
          env:
            - name: TRANSPORT
              value: {{ .Values.global.transport }}
            - name: AWS_REGION
              value: {{ .Values.global.awsRegion }}
            - name: TARGET_EKS_CLUSTER_NAME
              value: {{ .Values.deployment.targetEKSClusterName }}
{{- end }}
