{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "mop.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "mop.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mop.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "mop.labels" -}}
app.kubernetes.io/name: {{ include "mop.name" . }}
helm.sh/chart: {{ include "mop.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "mop.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "mop.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Generate the postgres DB hostname
*/}}
{{- define "mop.dbhost" -}}
{{- if .Values.postgresql.fullnameOverride -}}
{{- .Values.postgresql.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else if .Values.useDockerizedDatabase -}}
{{- printf "%s-postgresql" .Release.Name -}}
{{- else -}}
{{- required "`postgresql.hostname` must be set when `useDockerizedDatabase` is `false`" .Values.postgresql.hostname -}}
{{- end -}}
{{- end -}}

{{/*
Create the environment variables for configuration of this project. They are
repeated in a bunch of places, so to keep from repeating ourselves, we'll
build it here and use it everywhere.
*/}}
{{- define "mop.backendEnv" -}}
- name: PYTHONUNBUFFERED
  value: "1"
- name: DB_HOST
  value: {{ include "mop.dbhost" . | quote }}
- name: DB_NAME
  value: {{ .Values.postgresql.postgresqlDatabase | quote }}
- name: DB_PASS
  value: {{ .Values.postgresql.postgresqlPassword | quote }}
- name: DB_USER
  value: {{ .Values.postgresql.postgresqlUsername | quote }}
- name: DB_PORT
  value: {{ .Values.postgresql.service.port | quote }}
- name: HOME
  value: "/tmp"
- name: SECRET_KEY
  value: {{ .Values.djangoSecretKey | quote }}
- name: DJANGO_DEBUG
  value: {{ .Values.djangoDebug | toString | lower | title | quote }}
- name: DJANGO_SECRET_KEY
  value: {{ .Values.djangoSecretKey | quote }}
- name: ANTARES_KEY
  value: {{ .Values.antaresKey | quote }}
- name: ANTARES_PASSWORD
  value: {{ .Values.antaresPassword | quote }}
- name: LCO_API_KEY
  value: {{ .Values.lcoApiKey | quote }}
- name: LCO_PROPOSAL_ID
  value: {{ .Values.lcoProposalId | quote }}
- name: LCO_USERNAME
  value: {{ .Values.lcoUsername | quote }}
- name: IRSA_USERNAME
  value: {{ .Values.irsaUsername | quote }}
- name: IRSA_PASSWORD
  value: {{ .Values.irsaPassword | quote }}
- name: AWS_ACCESS_KEY_ID
  value: {{ .Values.awsAccessKeyId | quote }}
- name: AWS_SECRET_ACCESS_KEY
  value: {{ .Values.awsSecretAccessKey | quote }}
- name: AWS_S3_BUCKET
  value: {{ .Values.awsS3Bucket | quote }}
- name: GEMINI_USERNAME
  value: {{ .Values.geminiUsername | quote }}
- name: GEMINI_N_API_KEY
  value: {{ .Values.geminiNApiKey | quote }}
- name: GEMINI_S_API_KEY
  value: {{ .Values.geminiSApiKey | quote }}
- name: TNS_API_KEY
  value: {{ .Values.tnsApiKey | quote }}
- name: ATLAS_FORCED_PHOTOMETRY_API_KEY
  value: {{ .Values.atlasApiKey | quote }}
{{- end -}}
