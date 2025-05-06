apiVersion: v1
kind: Service
metadata:
  name: sre-orchestrator-service
  namespace: {{ .Values.global.namespace }}
spec:
  selector:
    app: sre-orchestrator
  ports:
    - protocol: TCP
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
  type: {{ .Values.service.type }}
