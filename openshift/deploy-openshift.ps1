param(
    [string]$Project = "srmt-bi",
    [Parameter(Mandatory = $true)]
    [string]$NvidiaApiKey
)

$ErrorActionPreference = "Stop"

Write-Host "[INFO] Vérification de oc CLI..." -ForegroundColor Cyan
if (-not (Get-Command oc -ErrorAction SilentlyContinue)) {
    throw "oc CLI non trouvé. Installez OpenShift CLI puis réessayez."
}

Write-Host "[INFO] Création/sélection du projet $Project..." -ForegroundColor Cyan
oc new-project $Project 2>$null | Out-Null
oc project $Project | Out-Null

Write-Host "[INFO] Application des manifestes OpenShift..." -ForegroundColor Cyan
oc apply -f "openshift/srmt-openshift.yaml"

Write-Host "[INFO] Mise à jour du secret NVIDIA_API_KEY..." -ForegroundColor Cyan
oc create secret generic srmt-bi-secrets --from-literal=NVIDIA_API_KEY="$NvidiaApiKey" --dry-run=client -o yaml | oc apply -f -

Write-Host "[INFO] Lancement du build binaire depuis le workspace..." -ForegroundColor Cyan
oc start-build srmt-bi --from-dir=. --follow

Write-Host "[INFO] Attente du déploiement..." -ForegroundColor Cyan
oc rollout status dc/srmt-bi --watch

$route = oc get route srmt-bi -o jsonpath='{.spec.host}'
Write-Host "[SUCCESS] Application déployée." -ForegroundColor Green
Write-Host "URL: https://$route" -ForegroundColor Green
