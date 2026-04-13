# 🔧 Commandes CURL pour Inférence NIM

## 📍 URL du Modèle Déployé
```
https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa
```

## 🧪 Tests Basiques

### 1. Health Check
```powershell
curl -X GET https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/health
```

### 2. Liste des Modèles Disponibles
```powershell
curl -X GET https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/models `
  -H "Content-Type: application/json"
```

## 💬 Inférence - Chat Completion

### 3. Requête Simple
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "user",
        "content": "Quelle est la capitale de la France?"
      }
    ],
    "temperature": 0.5,
    "max_tokens": 500
  }'
```

### 4. Requête avec Système Prompt
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "system",
        "content": "Tu es un expert en analyse de données fiscales et recouvrement."
      },
      {
        "role": "user",
        "content": "Comment analyser un dataset de recouvrement fiscal?"
      }
    ],
    "temperature": 0.3,
    "max_tokens": 1000
  }'
```

### 5. Génération de Code Polars
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "system",
        "content": "Tu es un expert en Polars et Python. Génère uniquement du code sans explication."
      },
      {
        "role": "user",
        "content": "Génère du code Polars pour calculer le top 10 des contribuables par montant recouvré."
      }
    ],
    "temperature": 0.1,
    "max_tokens": 800
  }'
```

## 🌊 Streaming (Réponse Progressive)

### 6. Avec Streaming Activé
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "user",
        "content": "Raconte-moi une courte histoire sur les données."
      }
    ],
    "stream": true,
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

## 🔐 Avec Authentification (si requise)

### 7. Avec Bearer Token
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer VOTRE_TOKEN_ICI" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "user",
        "content": "Test avec authentification"
      }
    ],
    "max_tokens": 100
  }'
```

### 8. Avec API Key
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -H "X-API-Key: VOTRE_API_KEY_ICI" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "user",
        "content": "Test avec API key"
      }
    ],
    "max_tokens": 100
  }'
```

## 📊 Test pour SRMT Business Intelligence

### 9. Génération de Requête Analytique
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "system",
        "content": "Tu es un expert en analyse de données SRMT. Le dataset contient: MONTANT_RECOUVRE, MONTANT_DECLARE, BUREAU, DIRECTION, LIBELLE, DATE_DECLARATION."
      },
      {
        "role": "user",
        "content": "Génère du code Polars pour: Top 10 des contribuables par montant recouvré en 2024"
      }
    ],
    "temperature": 0.05,
    "max_tokens": 1500
  }'
```

## ⚙️ Paramètres Disponibles

| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `model` | string | Nom du modèle | Requis |
| `messages` | array | Messages de conversation | Requis |
| `temperature` | float | Créativité (0-1) | 0.7 |
| `max_tokens` | int | Longueur max réponse | 2048 |
| `top_p` | float | Nucleus sampling | 1.0 |
| `frequency_penalty` | float | Pénalité répétition | 0.0 |
| `presence_penalty` | float | Pénalité nouveauté | 0.0 |
| `stream` | boolean | Streaming activé | false |
| `stop` | array | Séquences d'arrêt | null |

## 🚀 Scripts Utilitaires

### Exécuter le Script PowerShell
```powershell
cd "c:\Users\baye.niang\Desktop\Projets et realisations\SRMT_Business_Intelligent"
.\test_inference_curl.ps1
```

### Exécuter le Script Python
```powershell
cd "c:\Users\baye.niang\Desktop\Projets et realisations\SRMT_Business_Intelligent"
python test_inference_nim.py
```

## 📝 Notes Importantes

1. **Timeout**: Utilisez `--max-time 60` pour éviter les timeouts
2. **Verbose**: Ajoutez `-v` pour voir les détails de la requête
3. **Output**: Utilisez `-o fichier.json` pour sauvegarder la réponse
4. **Format**: Les réponses sont en JSON

## 🔍 Débogage

### Voir les Headers de la Réponse
```powershell
curl -I https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/health
```

### Verbose Output (Détails Complets)
```powershell
curl -v -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{...}'
```

### Sauvegarder la Réponse
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{...}' `
  -o response.json
```

## 🎯 Exemples Spécifiques SRMT

### Analyse de Performance
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "user",
        "content": "En tant qu'\''expert BI, explique comment analyser les performances de recouvrement par direction régionale."
      }
    ],
    "temperature": 0.3,
    "max_tokens": 1200
  }'
```

### Détection d'Anomalies
```powershell
curl -X POST https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "meta/llama-3.1-405b-instruct",
    "messages": [
      {
        "role": "user",
        "content": "Quelles méthodes utiliser pour détecter des anomalies dans les données de recouvrement fiscal?"
      }
    ],
    "temperature": 0.4,
    "max_tokens": 1000
  }'
```

---

**Auteur**: SRMT Business Intelligence Team  
**Date**: Février 2026  
**Version**: 1.0
