{{/*
Expand the name of the chart.
*/}}
{{- define "esddns-operator.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "esddns-operator.fullname" -}}
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
Create chart name and version as used by the chart label.
*/}}
{{- define "esddns-operator.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "esddns-operator.labels" -}}
helm.sh/chart: {{ include "esddns-operator.chart" . }}
{{ include "esddns-operator.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "esddns-operator.selectorLabels" -}}
app.kubernetes.io/name: {{ include "esddns-operator.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "esddns-operator.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "esddns-operator.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get log level based on environment
*/}}
{{- define "esddns-operator.logLevel" -}}
{{- if eq .Values.environment "development" }}
{{ .Values.development.logLevel }}
{{- else }}
{{ .Values.daemon.logLevel }}
{{- end }}
{{- end }}

{{/*
Get resources based on environment
*/}}
{{- define "esddns-operator.resources" -}}
{{- if eq .Values.environment "development" }}
{{ toYaml .Values.development.resources }}
{{- else }}
{{ toYaml .Values.daemon.resources }}
{{- end }}
{{- end }}
