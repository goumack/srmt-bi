# Configuration NVIDIA NIM pour l'Agent IA SRMT

## 🔑 Configuration de la Clé API NVIDIA

Pour utiliser NVIDIA NIM avec votre agent IA SRMT, vous devez:

1. **Obtenir une clé API NVIDIA NIM:**
   - Visitez: https://build.nvidia.com/
   - Créez un compte ou connectez-vous
   - Générez une clé API

2. **Configurer la clé API:**
   ```bash
   # Méthode 1: Variable d'environnement (recommandée)
   export NVIDIA_API_KEY="votre_clé_api_ici"
   
   # Méthode 2: Dans le code Python
   # Modifiez la ligne dans srmt_ai_agent.py:
   api_key="nvapi-VOTRE_CLE_API_ICI"
   ```

3. **Modèles disponibles:**
   - `nvidia/llama-3.1-nemotron-70b-instruct` (recommandé)
   - `nvidia/llama-3.1-405b-instruct`
   - `nvidia/llama-3.1-70b-instruct`
   - `nvidia/llama-3.1-8b-instruct`

## 🚀 Instructions de Démarrage

1. **Installation des dépendances:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration de la clé API:**
   ```bash
   # Windows PowerShell
   $env:NVIDIA_API_KEY = "votre_clé_api_ici"
   
   # Linux/Mac
   export NVIDIA_API_KEY="votre_clé_api_ici"
   ```

3. **Lancement de l'application:**
   ```bash
   python taipy_interface.py
   ```

4. **Accès à l'interface:**
   - Ouvrez votre navigateur
   - Allez sur: http://localhost:5000

## 📋 Fonctionnalités de l'Agent IA

### 🔍 Recherche de Contribuables
- Recherche par ID de contribuable
- Informations complètes sur chaque contribuable
- Historique des déclarations et recouvrements

### 🧠 Analyse IA avec NVIDIA NIM
- Questions en langage naturel
- Analyses prédictives
- Recommandations personnalisées
- Détection d'anomalies

### 📊 Visualisations Avancées
- Graphiques interactifs avec Plotly
- Évolution temporelle des contribuables
- Analyse par bureau et direction
- Top contribuables par différents critères

### 🎯 Capacités d'Analyse
- Taux de recouvrement par contribuable
- Analyse des tendances de paiement
- Identification des contribuables à risque
- Recommandations d'actions correctives

## 🛠️ Structure du Projet

```
SRMT_Business_Intelligent/
├── srmt_data.parquet           # Vos données SRMT
├── srmt_ai_agent.py            # Classe principale de l'agent IA
├── taipy_interface.py          # Interface utilisateur Taipy
├── requirements.txt            # Dépendances Python
├── config_nvidia.md           # Ce fichier de configuration
└── importation.ipynb          # Notebook d'exploration
```

## 🔧 Personnalisation

Vous pouvez personnaliser l'agent en modifiant:

1. **Prompts IA** dans `srmt_ai_agent.py`
2. **Interface utilisateur** dans `taipy_interface.py`
3. **Graphiques** en ajoutant de nouveaux types dans `generate_chart()`
4. **Analyses** en ajoutant de nouvelles méthodes d'analyse

## 📞 Support

Pour toute question ou problème:
1. Vérifiez que votre clé API NVIDIA est correctement configurée
2. Assurez-vous que toutes les dépendances sont installées
3. Consultez les logs d'erreur dans la console