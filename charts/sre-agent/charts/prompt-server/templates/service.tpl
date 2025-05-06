apiVersion: v1
kind: Service
metadata:
  name: prompt-server
  namespace: {{ .Values.global.namespace }}
spec:
  selector:
    app: mcp-prompt-server
  ports:
    - protocol: TCP
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
  type: ClusterIP
