{{- if .Values.enabled }}
apiVersion: v1
kind: Service
metadata:
  name: kubernetes
  namespace: {{ .Values.global.namespace }}
spec:
  selector:
    app: mcp-kubernetes
  ports:
    - protocol: TCP
      port: {{ .Values.service.port | default 3001 }}
      targetPort: {{ .Values.service.targetPort | default 3001 }}
  type: ClusterIP
{{- end }}
