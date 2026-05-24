{{/*
Expand the name of the chart.
*/}}
{{- define "triage-agent.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "triage-agent.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "triage-agent.labels" -}}
helm.sh/chart: {{ include "triage-agent.name" . }}-{{ .Chart.Version }}
{{ include "triage-agent.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "triage-agent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "triage-agent.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
