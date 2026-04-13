# 📁 Dossier Documents PDF

## ⚠️ IMPORTANT - Placez vos PDFs ici !

Ce dossier doit contenir les fichiers PDF qui seront affichés dans le chatbot LexFin.

### 📚 Fichiers attendus :
1. **Code des impots.pdf**
2. **Plan de redressement economique et social (PRES).pdf**
3. **Strategie de Gestion de la Dette a moyen terme 2026-2028.pdf**

### ✅ Fonctionnement :
- Lorsque l'utilisateur clique sur une référence PDF, **le document complet s'ouvre**
- Le PDF s'affiche dans un viewer intégré
- **Navigation automatique** vers la page de la référence (ex: page 180)
- Le viewer permet de parcourir tout le PDF

### 📝 Format des noms de fichiers :
**Les noms doivent correspondre EXACTEMENT** aux noms retournés par l'API LexFin dans le champ `file_name`.

### 🔍 Exemple :
- API retourne: `"file_name": "Code des impots.pdf"`
- Fichier à créer: `documents/Code des impots.pdf`

### 🚀 Test :
1. Placez vos PDFs dans ce dossier
2. Lancez le serveur: `python lexfin_chatbot.py`
3. Cliquez sur une référence dans le chatbot
4. Le PDF s'ouvre automatiquement à la bonne page !

### ⚡ Navigation dans le PDF :
- **Page automatique** : Le PDF s'ouvre directement à la page de la référence
- **Zoom** : Utilisez les contrôles du navigateur (Ctrl + molette)
- **Recherche** : Ctrl+F dans le PDF pour chercher du texte
- **Téléchargement** : Bouton de téléchargement du navigateur disponible

