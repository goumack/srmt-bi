# Déploiement OpenShift - SRMT BI

## Pré-requis
- OpenShift CLI (`oc`) installé
- Session connectée (`oc login ...`)
- Droits de création projet/build/deploy

## Déploiement rapide (PowerShell)
Depuis la racine du projet :

- Script : [openshift/deploy-openshift.ps1](openshift/deploy-openshift.ps1)
- Manifestes : [openshift/srmt-openshift.yaml](openshift/srmt-openshift.yaml)

Le script :
1. crée/sélectionne le projet OpenShift,
2. applique les objets (Secret, ImageStream, BuildConfig, DeploymentConfig, Service, Route),
3. injecte `NVIDIA_API_KEY`,
4. lance un build binaire depuis le dossier courant,
5. attend le rollout et affiche l'URL.

## Notes
- L'app écoute sur le port `8080`.
- Health endpoint : `/api/health`.
- Le secret `srmt-bi-secrets` doit contenir une vraie clé `NVIDIA_API_KEY`.
- Le build inclut le fichier `srmt_data_2020_2025.parquet` depuis le workspace.
