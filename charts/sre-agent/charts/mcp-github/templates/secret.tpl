apiVersion: v1
kind: Secret
metadata:
  name: "{{ .Release.Name }}-secret"
type: Opaque
stringData:
  GITHUB_PERSONAL_ACCESS_TOKEN: {{ .Values.global.github_access_token | b64enc | quote }}
