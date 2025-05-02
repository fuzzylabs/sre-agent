apiVersion: v1
kind: Secret
metadata:
  name: "{{ .Release.Name }}-secret"
type: Opaque
stringData:
  ANTHROPIC_API_KEY: {{ .Values.secret.anthropic_api_key | quote }}
