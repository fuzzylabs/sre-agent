{{- if .Values.enabled }}
apiVersion: v1
kind: Service
metadata:
  name: slack
  namespace: {{ .Values.global.namespace }}
spec:
  selector:
    app: mcp-slack
  ports:
    - protocol: TCP
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
  type: ClusterIP
{{- end }}
