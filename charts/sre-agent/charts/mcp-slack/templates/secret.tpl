apiVersion: v1
kind: Secret
metadata:
  name: "{{ .Release.Name }}-secret"
type: Opaque
stringData:
    SLACK_BOT_TOKEN: {{ .Values.global.slack_bot_token | b64enc | quote }}
    SLACK_TEAM_ID: {{ .Values.global.slack_team_id | b64enc | quote }}
