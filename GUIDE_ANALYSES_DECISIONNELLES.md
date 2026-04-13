# 📊 Guide des Analyses Décisionnelles - SRMT BI

## 🎯 Philosophie

**Principe fondamental** : Chaque analyse doit permettre au décideur de **prendre une décision éclairée**.

❌ **Mauvaise approche** : Retourner juste un chiffre ou un nom  
✅ **Bonne approche** : Fournir un contexte complet avec comparaison et KPIs

---

## 📋 Templates de Code par Type d'Analyse

### 1. 🏆 Analyse de Performance (Bureau/Région)

**Question type** : "Quel bureau a la meilleure performance ?"

**❌ Code incomplet (NE JAMAIS FAIRE)** :
```python
resultat = data.group_by('BUREAU').agg(
    pl.col('MONTANT_RECOUVRE').sum()
).limit(1).collect().to_dicts()
# Problème: 1 seul bureau, pas de contexte, pas de comparaison
```

**✅ Code enrichi (TOUJOURS FAIRE)** :
```python
resultat = data.lazy().filter(
    # Filtres temporels si nécessaire
    (pl.col('DATE_RECOUVREMENT').dt.month() == 12) &
    (pl.col('DATE_RECOUVREMENT').dt.year() == 2025)
).group_by('BUREAU').agg([
    # TOUS les montants
    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
    
    # Statistiques complémentaires
    pl.len().alias('NB_DECLARATIONS'),
    pl.col('MONTANT_RECOUVRE').mean().alias('MOYENNE_RECOUVRE'),
    pl.col('MONTANT_DECLARE').mean().alias('MOYENNE_DECLARE'),
    
    # Min/Max pour voir la dispersion
    pl.col('MONTANT_RECOUVRE').max().alias('MAX_RECOUVRE'),
    pl.col('MONTANT_RECOUVRE').min().alias('MIN_RECOUVRE')
    
]).with_columns([
    # KPIs calculés
    (pl.col('TOTAL_RECOUVRE') - pl.col('TOTAL_DECLARE')).alias('ECART'),
    ((pl.col('TOTAL_RECOUVRE') / pl.col('TOTAL_DECLARE')) * 100).alias('TAUX_RECOUVREMENT_%'),
    
    # Indicateur de performance
    pl.when(pl.col('TOTAL_RECOUVRE') / pl.col('TOTAL_DECLARE') > 0.95)
      .then(pl.lit('Excellent'))
      .when(pl.col('TOTAL_RECOUVRE') / pl.col('TOTAL_DECLARE') > 0.80)
      .then(pl.lit('Bon'))
      .otherwise(pl.lit('À améliorer'))
      .alias('PERFORMANCE')
      
]).sort('TAUX_RECOUVREMENT_%', descending=True).head(10).collect().to_dicts()
# TOP 10 pour permettre la comparaison et voir le contexte
```

**Résultat attendu** :
```json
[
  {
    "BUREAU": "Bureau Dakar Port Sud",
    "TOTAL_DECLARE": 45000000000,
    "TOTAL_RECOUVRE": 52685225414,
    "NB_DECLARATIONS": 1254,
    "MOYENNE_RECOUVRE": 42015000,
    "ECART": 7685225414,
    "TAUX_RECOUVREMENT_%": 117.1,
    "PERFORMANCE": "Excellent"
  },
  // ... 9 autres bureaux pour comparaison
]
```

---

### 2. 🏅 Top Contribuables

**Question type** : "Quels sont les meilleurs contribuables ?"

**✅ Code enrichi** :
```python
resultat = data.lazy().filter(
    # Filtres temporels
    pl.col('DATE_DECLARATION').dt.year() == 2024
).group_by(['LIBELLE', 'BUREAU', 'TYPE_IMPOT_TAXE']).agg([
    # Agrégations multiples
    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
    pl.len().alias('NB_DECLARATIONS'),
    
    # Dates pour voir la régularité
    pl.col('DATE_DECLARATION').min().alias('PREMIERE_DECLARATION'),
    pl.col('DATE_DECLARATION').max().alias('DERNIERE_DECLARATION')
    
]).with_columns([
    (pl.col('TOTAL_RECOUVRE') - pl.col('TOTAL_DECLARE')).alias('ECART'),
    ((pl.col('TOTAL_RECOUVRE') / pl.col('TOTAL_DECLARE')) * 100).alias('TAUX_%')
    
]).sort('TOTAL_RECOUVRE', descending=True).head(20).collect().to_dicts()
```

---

### 3. 📈 Évolution Temporelle

**Question type** : "Évolution mensuelle des recouvrements"

**✅ Code enrichi** :
```python
resultat = data.lazy().filter(
    pl.col('DATE_DECLARATION').dt.year() == 2024
).with_columns([
    pl.col('DATE_DECLARATION').dt.month().alias('MOIS'),
    pl.col('DATE_DECLARATION').dt.year().alias('ANNEE')
]).group_by(['ANNEE', 'MOIS']).agg([
    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
    pl.len().alias('NB_DECLARATIONS'),
    
    # Nombre de bureaux actifs ce mois
    pl.col('BUREAU').n_unique().alias('NB_BUREAUX_ACTIFS'),
    
    # Types d'impôts différents
    pl.col('TYPE_IMPOT_TAXE').n_unique().alias('NB_TYPES_IMPOTS')
    
]).with_columns([
    (pl.col('TOTAL_RECOUVRE') - pl.col('TOTAL_DECLARE')).alias('ECART'),
    ((pl.col('TOTAL_RECOUVRE') / pl.col('TOTAL_DECLARE')) * 100).alias('TAUX_%')
    
]).sort(['ANNEE', 'MOIS']).collect().to_dicts()
```

---

### 4. ⚖️ Analyse Comparative (Bureaux/Régions)

**Question type** : "Comparer les performances entre régions"

**✅ Code enrichi** :
```python
resultat = data.lazy().group_by(['DIRECTION_REGIONALE', 'BUREAU']).agg([
    # Montants
    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
    
    # Activité
    pl.len().alias('NB_DECLARATIONS'),
    pl.col('LIBELLE').n_unique().alias('NB_CONTRIBUABLES_UNIQUES'),
    
    # Diversité des impôts
    pl.col('TYPE_IMPOT_TAXE').n_unique().alias('NB_TYPES_IMPOTS')
    
]).with_columns([
    (pl.col('TOTAL_RECOUVRE') - pl.col('TOTAL_DECLARE')).alias('ECART'),
    ((pl.col('TOTAL_RECOUVRE') / pl.col('TOTAL_DECLARE')) * 100).alias('TAUX_%'),
    (pl.col('TOTAL_RECOUVRE') / pl.col('NB_DECLARATIONS')).alias('RECOUVRE_MOYEN_PAR_DECLA')
    
]).sort('TOTAL_RECOUVRE', descending=True).collect().to_dicts()
```

---

## 🎯 Règles d'Or

### ✅ TOUJOURS Inclure

1. **Les deux montants** : `MONTANT_DECLARE` ET `MONTANT_RECOUVRE`
2. **Les KPIs calculés** : `ECART`, `TAUX_%`
3. **Le contexte** : Bureau, Région, Type impôt (selon pertinence)
4. **Les statistiques** : Nombre de déclarations, moyennes
5. **TOP N au lieu de LIMIT 1** : Pour permettre la comparaison

### ❌ NE JAMAIS Faire

1. Retourner qu'**une seule colonne** (ex: juste MONTANT_RECOUVRE)
2. Utiliser `limit(1)` pour une analyse (utiliser `head(10)` minimum)
3. Oublier les **colonnes de contexte** (Bureau, Région, etc.)
4. Ne pas calculer les **KPIs dérivés** (écart, taux)
5. Retourner des **données brutes** sans agrégation pour des questions analytiques

---

## 📊 Colonnes par Cas d'Usage

### Performance Bureau/Région
```
OBLIGATOIRE:
- BUREAU ou DIRECTION_REGIONALE
- MONTANT_DECLARE
- MONTANT_RECOUVRE
- ECART (calculé)
- TAUX_% (calculé)
- NB_DECLARATIONS

RECOMMANDÉ:
- MOYENNE_RECOUVRE
- MAX/MIN pour dispersion
- PERFORMANCE (catégorie calculée)
```

### Top Contribuables
```
OBLIGATOIRE:
- LIBELLE
- BUREAU
- TYPE_IMPOT_TAXE
- MONTANT_DECLARE
- MONTANT_RECOUVRE
- ECART
- TAUX_%

RECOMMANDÉ:
- NB_DECLARATIONS
- PREMIERE/DERNIERE_DECLARATION
```

### Évolution Temporelle
```
OBLIGATOIRE:
- ANNEE, MOIS (ou DATE)
- MONTANT_DECLARE
- MONTANT_RECOUVRE
- ECART
- TAUX_%

RECOMMANDÉ:
- NB_DECLARATIONS
- NB_BUREAUX_ACTIFS
- Variation par rapport au mois précédent
```

---

## 💡 Conseils pour Décideurs

**Ce qu'un décideur veut savoir** :

1. **Le résultat principal** : "Quel est le meilleur ?"
2. **Le contexte** : "Comment se compare-t-il aux autres ?"
3. **Les KPIs** : "Quel est le taux de recouvrement ?"
4. **La tendance** : "Est-ce mieux ou pire que prévu ?"
5. **L'action** : "Que faut-il faire ?"

**Ce qu'un décideur NE veut PAS** :

1. Juste un nombre sans contexte
2. Un seul résultat sans comparaison
3. Des données brutes non analysées
4. Des chiffres sans interprétation

---

## 🚀 Checklist Avant Génération

Avant de générer ton code, vérifie :

- [ ] Au moins **5 colonnes** dans le résultat
- [ ] **MONTANT_DECLARE** ET **MONTANT_RECOUVRE** présents ensemble
- [ ] **KPIs calculés** : ECART, TAUX_%
- [ ] **TOP 10-20** au lieu de limit(1)
- [ ] **Colonnes de contexte** : Bureau, Région, Type impôt
- [ ] **Statistiques** : COUNT, MEAN si pertinent
- [ ] **Tri** : descendant sur le KPI principal

---

**Version** : 1.0 - Guide Analyses Décisionnelles
**Usage** : Formation des prompts IA pour génération de code analytique
