apiVersion: v1
kind: Secret
metadata:
  name: "{{ .Release.Name }}-secret"
type: Opaque
stringData:
  ANTHROPIC_API_KEY: {{ .Values.global.anthropic_api_key | b64enc | quote }}
