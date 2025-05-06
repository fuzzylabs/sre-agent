apiVersion: v1
kind: Secret
metadata:
  name: "{{ .Release.Name }}-secret"
type: Opaque
stringData:
  CHANNEL_ID: {{ .Values.global.channel_id | b64enc | quote }}
  DEV_BEARER_TOKEN: {{ .Values.global.dev_bearer_token | b64enc | quote }}
  SLACK_SIGNING_SECRET: {{ .Values.global.slack_signing_secret | b64enc | quote }}
