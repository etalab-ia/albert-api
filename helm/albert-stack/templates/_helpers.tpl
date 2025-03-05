{{/* Generate basic labels */}}
{{- define "albert-stack.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{/* Component labels */}}
{{- define "albert-stack.componentLabels" -}}
{{- include "albert-stack.labels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Selector labels */}}
{{- define "albert-stack.selectorLabels" -}}
app: {{ .name }}
{{- end -}}