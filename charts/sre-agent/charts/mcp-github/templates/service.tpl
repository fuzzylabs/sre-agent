{{- if .Values.enabled }}
apiVersion: v1
kind: Service
metadata:
  name: github
  namespace: {{ .Values.global.namespace }}
spec:
  selector:
    app: mcp-github
  ports:
    - protocol: TCP
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
  type: ClusterIP
{{- end }}
