apiVersion: v1
kind: Secret
metadata:
  name: "{{ .Release.Name }}-secret"
type: Opaque
stringData:
  CHANNEL_ID: {{ .Values.secret.channel_id | quote }}
  DEV_BEARER_TOKEN: {{ .Values.secret.dev_bearer_token | quote }}
  SLACK_SIGNING_SECRET: {{ .Values.slack_signing_secret | quote }}
