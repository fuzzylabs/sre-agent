apiVersion: v1
kind: Secret
metadata:
  name: "{{ .Release.Name }}-secret"
  namespace: {{ .Values.global.namespace }}
type: Opaque
stringData:
  GITHUB_PERSONAL_ACCESS_TOKEN: {{ .Values.global.github_access_token | quote }}
  CHANNEL_ID: {{ .Values.global.channel_id | quote }}
  DEV_BEARER_TOKEN: {{ .Values.global.dev_bearer_token | quote }}
  SLACK_SIGNING_SECRET: {{ .Values.global.slack_signing_secret | quote }}
  ANTHROPIC_API_KEY: {{ .Values.global.anthropic_api_key | quote }}
  SLACK_BOT_TOKEN: {{ .Values.global.slack_bot_token | quote }}
  SLACK_TEAM_ID: {{ .Values.global.slack_team_id | quote }}
  HF_TOKEN: {{ .Values.global.hf_token | quote }}
