{{/*
Expand the name of the chart.
*/}}
{{- define "security-baseline.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "security-baseline.fullname" -}}
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
{{- define "security-baseline.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "security-baseline.labels" -}}
helm.sh/chart: {{ include "security-baseline.chart" . }}
{{ include "security-baseline.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
security.homelab.local/baseline: "true"
{{- end }}

{{/*
Selector labels
*/}}
{{- define "security-baseline.selectorLabels" -}}
app.kubernetes.io/name: {{ include "security-baseline.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "security-baseline.serviceAccountName" -}}
{{- if .Values.rbac.serviceAccount.create }}
{{- default (include "security-baseline.fullname" .) .Values.rbac.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.rbac.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Security Context Template - Restricted
*/}}
{{- define "security-baseline.securityContext.restricted" -}}
runAsNonRoot: {{ .Values.securityContexts.restricted.runAsNonRoot }}
runAsUser: {{ .Values.securityContexts.restricted.runAsUser }}
runAsGroup: {{ .Values.securityContexts.restricted.runAsGroup }}
fsGroup: {{ .Values.securityContexts.restricted.fsGroup }}
seccompProfile:
  type: {{ .Values.securityContexts.restricted.seccompProfile.type }}
allowPrivilegeEscalation: {{ .Values.securityContexts.restricted.allowPrivilegeEscalation }}
readOnlyRootFilesystem: {{ .Values.securityContexts.restricted.readOnlyRootFilesystem }}
capabilities:
  drop:
  {{- range .Values.securityContexts.restricted.capabilities.drop }}
  - {{ . }}
  {{- end }}
{{- end }}

{{/*
Security Context Template - Baseline
*/}}
{{- define "security-baseline.securityContext.baseline" -}}
runAsNonRoot: {{ .Values.securityContexts.baseline.runAsNonRoot }}
runAsUser: {{ .Values.securityContexts.baseline.runAsUser }}
runAsGroup: {{ .Values.securityContexts.baseline.runAsGroup }}
fsGroup: {{ .Values.securityContexts.baseline.fsGroup }}
seccompProfile:
  type: {{ .Values.securityContexts.baseline.seccompProfile.type }}
allowPrivilegeEscalation: {{ .Values.securityContexts.baseline.allowPrivilegeEscalation }}
capabilities:
  drop:
  {{- range .Values.securityContexts.baseline.capabilities.drop }}
  - {{ . }}
  {{- end }}
{{- end }}

{{/*
Security Context Template - Privileged
*/}}
{{- define "security-baseline.securityContext.privileged" -}}
runAsNonRoot: {{ .Values.securityContexts.privileged.runAsNonRoot }}
runAsUser: {{ .Values.securityContexts.privileged.runAsUser }}
seccompProfile:
  type: {{ .Values.securityContexts.privileged.seccompProfile.type }}
allowPrivilegeEscalation: {{ .Values.securityContexts.privileged.allowPrivilegeEscalation }}
capabilities:
  drop:
  {{- range .Values.securityContexts.privileged.capabilities.drop }}
  - {{ . }}
  {{- end }}
  add:
  {{- range .Values.securityContexts.privileged.capabilities.add }}
  - {{ . }}
  {{- end }}
{{- end }}

{{/*
Security Context Template - Networking
*/}}
{{- define "security-baseline.securityContext.networking" -}}
runAsNonRoot: {{ .Values.securityContexts.networking.runAsNonRoot }}
runAsUser: {{ .Values.securityContexts.networking.runAsUser }}
runAsGroup: {{ .Values.securityContexts.networking.runAsGroup }}
seccompProfile:
  type: {{ .Values.securityContexts.networking.seccompProfile.type }}
allowPrivilegeEscalation: {{ .Values.securityContexts.networking.allowPrivilegeEscalation }}
capabilities:
  drop:
  {{- range .Values.securityContexts.networking.capabilities.drop }}
  - {{ . }}
  {{- end }}
  add:
  {{- range .Values.securityContexts.networking.capabilities.add }}
  - {{ . }}
  {{- end }}
{{- end }}

{{/*
Resource Template - Get resource profile
*/}}
{{- define "security-baseline.resources" -}}
{{- $profile := .profile | default "standard" -}}
{{- $resources := index .Values.resources.profiles $profile -}}
limits:
  cpu: {{ $resources.limits.cpu }}
  memory: {{ $resources.limits.memory }}
requests:
  cpu: {{ $resources.requests.cpu }}
  memory: {{ $resources.requests.memory }}
{{- end }}

{{/*
Liveness Probe Template
*/}}
{{- define "security-baseline.livenessProbe" -}}
{{- with .Values.healthChecks.livenessProbe }}
httpGet:
  path: {{ .httpGet.path }}
  port: {{ .httpGet.port }}
initialDelaySeconds: {{ .initialDelaySeconds }}
periodSeconds: {{ .periodSeconds }}
timeoutSeconds: {{ .timeoutSeconds }}
failureThreshold: {{ .failureThreshold }}
{{- end }}
{{- end }}

{{/*
Readiness Probe Template
*/}}
{{- define "security-baseline.readinessProbe" -}}
{{- with .Values.healthChecks.readinessProbe }}
httpGet:
  path: {{ .httpGet.path }}
  port: {{ .httpGet.port }}
initialDelaySeconds: {{ .initialDelaySeconds }}
periodSeconds: {{ .periodSeconds }}
timeoutSeconds: {{ .timeoutSeconds }}
failureThreshold: {{ .failureThreshold }}
{{- end }}
{{- end }}

{{/*
Pod Security Standards Labels
*/}}
{{- define "security-baseline.podSecurityLabels" -}}
{{ .Values.podSecurityStandards.labels.enforce }}: {{ .Values.podSecurityStandards.enforce }}
{{ .Values.podSecurityStandards.labels.audit }}: {{ .Values.podSecurityStandards.audit }}
{{ .Values.podSecurityStandards.labels.warn }}: {{ .Values.podSecurityStandards.warn }}
{{ .Values.podSecurityStandards.labels.version }}: "v1.28"
{{- end }}

{{/*
TLS Configuration
*/}}
{{- define "security-baseline.tls" -}}
{{- if .Values.global.tls.enabled }}
tls:
  - secretName: {{ .Values.global.tls.secretName }}
    hosts:
    - {{ .host }}
{{- end }}
{{- end }}

{{/*
Service Monitor Labels
*/}}
{{- define "security-baseline.serviceMonitorLabels" -}}
{{- with .Values.monitoring.serviceMonitor.labels }}
{{- range $key, $value := . }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end }}
{{- end }}
