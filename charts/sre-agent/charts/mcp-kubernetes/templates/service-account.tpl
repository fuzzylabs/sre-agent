{{- if .Values.enabled }}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ .Values.serviceAccount.name }}
  namespace: {{ .Values.global.namespace }}
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::{{ .Values.global.awsAccountId }}:role/{{ .Values.serviceAccount.role }}
{{- end }}
