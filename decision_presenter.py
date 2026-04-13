"""
Module de Présentation Décisionnelle pour Dirigeants
Transforme les résultats bruts en analyses actionnables avec KPIs, statistiques et recommandations
"""

import polars as pl
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DecisionPresenter:
    """Transforme les résultats d'analyse en présentations décisionnelles"""
    
    def __init__(self):
        self.month_names = {
            1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
            5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
            9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
        }
    
    def _generate_financial_analysis(self, df: pl.DataFrame, kpis: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """
        💼 ANALYSE FINANCIÈRE EXPERTE
        Génère une analyse financière détaillée pour les décideurs
        """
        analysis = {
            'synthese': '',
            'tendances': [],
            'points_vigilance': [],
            'opportunites': [],
            'risques': [],
            'recommandations_strategiques': []
        }
        
        try:
            # 1. SYNTHÈSE GLOBALE
            if 'total_declare' in kpis and 'total_recouvre' in kpis:
                ecart = kpis.get('ecart', 0)
                taux = kpis.get('taux_recouvrement', 0)
                
                if taux > 100:
                    analysis['synthese'] = f"Performance exceptionnelle avec un taux de recouvrement de {taux:.1f}%. Le surplus de {self._format_amount(abs(ecart))} FCFA témoigne d'une efficacité optimale du dispositif fiscal."
                elif taux >= 95:
                    analysis['synthese'] = f"Performance solide avec {taux:.1f}% de recouvrement. Écart maîtrisé de {self._format_amount(abs(ecart))} FCFA."
                elif taux >= 80:
                    analysis['synthese'] = f"Performance modérée ({taux:.1f}%). L'écart de {self._format_amount(abs(ecart))} FCFA nécessite des actions correctives."
                else:
                    analysis['synthese'] = f"⚠️ Performance critique ({taux:.1f}%). L'écart important de {self._format_amount(abs(ecart))} FCFA exige des mesures urgentes."
            
            # 2. TENDANCES DÉTECTÉES
            if 'MONTANT_DECLARE' in df.columns and 'MONTANT_RECOUVRE' in df.columns:
                # Analyser la distribution des écarts
                df_with_ecart = df.with_columns(
                    ((pl.col('MONTANT_RECOUVRE') - pl.col('MONTANT_DECLARE')) / pl.col('MONTANT_DECLARE') * 100).alias('ecart_pct')
                )
                
                ecarts_positifs = len(df_with_ecart.filter(pl.col('ecart_pct') > 0))
                ecarts_negatifs = len(df_with_ecart.filter(pl.col('ecart_pct') < 0))
                
                if ecarts_positifs > ecarts_negatifs:
                    analysis['tendances'].append(f"✅ Tendance positive: {ecarts_positifs}/{len(df)} opérations avec surplus de recouvrement")
                else:
                    analysis['tendances'].append(f"⚠️ Tendance négative: {ecarts_negatifs}/{len(df)} opérations en sous-recouvrement")
            
            # 3. POINTS DE VIGILANCE
            if 'taux_recouvrement' in kpis:
                if kpis['taux_recouvrement'] < 90:
                    analysis['points_vigilance'].append("📉 Taux de recouvrement inférieur au seuil optimal de 90%")
                
                if kpis.get('ecart', 0) < 0 and abs(kpis['ecart']) > kpis.get('total_declare', 0) * 0.1:
                    analysis['points_vigilance'].append("💰 Écart significatif (>10%) entre déclarations et recouvrements")
            
            # Analyser la concentration des risques
            if 'LIBELLE' in df.columns and 'MONTANT_DECLARE' in df.columns:
                top_3_taxes = (df.group_by('LIBELLE')
                              .agg(pl.col('MONTANT_DECLARE').sum().alias('total'))
                              .sort('total', descending=True)
                              .limit(3))
                
                top_3_sum = top_3_taxes['total'].sum()
                total_sum = df['MONTANT_DECLARE'].sum()
                concentration = (top_3_sum / total_sum * 100) if total_sum > 0 else 0
                
                if concentration > 70:
                    analysis['points_vigilance'].append(f"⚠️ Forte concentration: {concentration:.1f}% sur 3 taxes principales")
            
            # 4. OPPORTUNITÉS
            if 'BUREAU' in df.columns and len(df) > 100:
                # Identifier bureaux à fort potentiel
                bureaux_stats = (df.group_by('BUREAU')
                                .agg([
                                    pl.col('MONTANT_DECLARE').sum().alias('declare'),
                                    pl.col('MONTANT_RECOUVRE').sum().alias('recouvre') if 'MONTANT_RECOUVRE' in df.columns else pl.lit(0).alias('recouvre')
                                ]))
                
                if 'recouvre' in bureaux_stats.columns:
                    bureaux_performants = bureaux_stats.filter(
                        (pl.col('recouvre') / pl.col('declare') > 1.05) & (pl.col('declare') > 0)
                    )
                    
                    if len(bureaux_performants) > 0:
                        analysis['opportunites'].append(f"🎯 {len(bureaux_performants)} bureau(x) avec performance >105% : bonnes pratiques à capitaliser")
            
            # 5. RISQUES IDENTIFIÉS
            if 'total_declare' in kpis and kpis.get('taux_recouvrement', 100) < 85:
                perte_potentielle = kpis['total_declare'] * (1 - kpis['taux_recouvrement'] / 100)
                analysis['risques'].append(f"💸 Risque de perte fiscale: {self._format_amount(perte_potentielle)} FCFA")
            
            # 6. RECOMMANDATIONS STRATÉGIQUES
            if 'taux_recouvrement' in kpis:
                if kpis['taux_recouvrement'] < 90:
                    analysis['recommandations_strategiques'].append({
                        'priorite': 'haute',
                        'action': 'Plan de redressement fiscal immédiat',
                        'impact_estime': f"Potentiel de {self._format_amount(kpis.get('total_declare', 0) * 0.1)} FCFA"
                    })
                
                if kpis['taux_recouvrement'] >= 100:
                    analysis['recommandations_strategiques'].append({
                        'priorite': 'moyenne',
                        'action': 'Capitaliser et diffuser les bonnes pratiques',
                        'impact_estime': 'Optimisation continue'
                    })
            
        except Exception as e:
            logger.error(f"Erreur génération analyse financière: {e}")
            analysis['synthese'] = "Analyse en cours..."
        
        return analysis
    
    def _format_amount(self, amount: float) -> str:
        """Formater un montant en notation française"""
        if amount >= 1_000_000_000:
            return f"{amount/1_000_000_000:.1f} Mds"
        elif amount >= 1_000_000:
            return f"{amount/1_000_000:.1f} M"
        elif amount >= 1_000:
            return f"{amount/1_000:.1f} K"
        else:
            return f"{amount:.0f}"
    
    def generate_executive_summary(self, 
                                   query: str, 
                                   execution_result: Any, 
                                   code: str) -> Dict[str, Any]:
        """
        Génère un résumé exécutif complet avec KPIs, statistiques et recommandations
        """
        try:
            # Vérifier si on a des résultats
            if not execution_result or (isinstance(execution_result, list) and len(execution_result) == 0):
                return self._generate_empty_summary(query)
            
            # Convertir en DataFrame Polars si c'est une liste de dicts
            if isinstance(execution_result, list):
                df = pl.DataFrame(execution_result)
            elif isinstance(execution_result, pl.DataFrame):
                df = execution_result
            else:
                return self._generate_simple_summary(query, execution_result)
            
            # Identifier le type d'analyse selon les colonnes et le contexte
            analysis_type = self._identify_analysis_type(df, query)
            
            # Générer le résumé selon le type
            if analysis_type == 'non_recouvrement':
                return self._analyze_non_recouvrement(query, df, code)
            elif analysis_type == 'financial_comparison':
                return self._analyze_financial_comparison(query, df)
            elif analysis_type == 'regional':
                return self._analyze_regional(query, df)
            elif analysis_type == 'temporal':
                return self._analyze_temporal(query, df)
            else:
                return self._analyze_general(query, df)
                
        except Exception as e:
            logger.error(f"Erreur génération résumé exécutif: {e}")
            return self._generate_fallback_summary(query, execution_result)
    
    def _identify_analysis_type(self, df: pl.DataFrame, query: str) -> str:
        """Identifie le type d'analyse selon le contexte"""
        query_lower = query.lower()
        cols = df.columns
        
        # Détection non-recouvrement (priorité haute)
        if any(word in query_lower for word in ['non recouvr', 'pas recouvr', 'non encore', 'pas encore']):
            return 'non_recouvrement'
        
        # Détection comparaison financière (priorité haute si colonnes financières présentes)
        if 'MONTANT_DECLARE' in cols and 'MONTANT_RECOUVRE' in cols:
            return 'financial_comparison'
        
        # Détection régionale
        if any(col in cols for col in ['BUREAU', 'DIRECTION', 'REGION']):
            return 'regional'
        
        # Détection temporelle (priorité basse)
        if any('DATE' in col for col in cols):
            return 'temporal'
        
        return 'general'
    
    def _analyze_non_recouvrement(self, query: str, df: pl.DataFrame, code: str) -> Dict[str, Any]:
        """Analyse spécifique pour les déclarations non recouvrées"""
        
        total_records = len(df)
        
        # KPIs Financiers
        kpis = {}
        if 'MONTANT_DECLARE' in df.columns:
            total_declare = df['MONTANT_DECLARE'].sum()
            kpis['total_declare'] = float(total_declare) if total_declare else 0
        
        if 'MONTANT_RECOUVRE' in df.columns:
            total_recouvre = df['MONTANT_RECOUVRE'].sum()
            kpis['total_recouvre'] = float(total_recouvre) if total_recouvre else 0
        
        # Calcul de l'écart (perte potentielle)
        if 'total_declare' in kpis and 'total_recouvre' in kpis:
            kpis['ecart'] = kpis['total_recouvre'] - kpis['total_declare']
            kpis['taux_recouvrement'] = (kpis['total_recouvre'] / kpis['total_declare'] * 100) if kpis['total_declare'] > 0 else 0
        
        # Répartition par type de taxe (LIBELLE)
        repartition = {}
        if 'LIBELLE' in df.columns:
            top_taxes = (df.group_by('LIBELLE')
                          .agg([
                              pl.count().alias('nombre'),
                              pl.col('MONTANT_DECLARE').sum().alias('montant_declare') if 'MONTANT_DECLARE' in df.columns else pl.lit(0).alias('montant_declare'),
                              pl.col('MONTANT_RECOUVRE').sum().alias('montant_recouvre') if 'MONTANT_RECOUVRE' in df.columns else pl.lit(0).alias('montant_recouvre')
                          ])
                          .sort('montant_declare', descending=True)
                          .limit(10))
            
            repartition['par_taxe'] = top_taxes.to_dicts()
        
        # Répartition par bureau si disponible
        if 'BUREAU' in df.columns:
            by_bureau = (df.group_by('BUREAU')
                          .agg([
                              pl.count().alias('nombre'),
                              pl.col('MONTANT_DECLARE').sum().alias('montant_declare') if 'MONTANT_DECLARE' in df.columns else pl.lit(0).alias('montant_declare')
                          ])
                          .sort('montant_declare', descending=True)
                          .limit(10))
            
            repartition['par_bureau'] = by_bureau.to_dicts()
        
        # Statistiques descriptives
        statistiques = {
            'nombre_total': total_records,
            'nombre_types_taxes': len(df['LIBELLE'].unique()) if 'LIBELLE' in df.columns else 0
        }
        
        # Montant moyen
        if 'MONTANT_DECLARE' in df.columns:
            statistiques['montant_moyen'] = float(df['MONTANT_DECLARE'].mean()) if len(df) > 0 else 0
            statistiques['montant_median'] = float(df['MONTANT_DECLARE'].median()) if len(df) > 0 else 0
            statistiques['montant_max'] = float(df['MONTANT_DECLARE'].max()) if len(df) > 0 else 0
            statistiques['montant_min'] = float(df['MONTANT_DECLARE'].min()) if len(df) > 0 else 0
        
        # Analyse temporelle si dates disponibles
        tendance = None
        if 'DATE_DECLARATION' in df.columns:
            # Extraire mois et année
            temporal_df = df.with_columns([
                pl.col('DATE_DECLARATION').dt.month().alias('mois'),
                pl.col('DATE_DECLARATION').dt.year().alias('annee')
            ])
            
            by_month = (temporal_df.group_by(['annee', 'mois'])
                        .agg([
                            pl.count().alias('nombre'),
                            pl.col('MONTANT_DECLARE').sum().alias('montant') if 'MONTANT_DECLARE' in df.columns else pl.lit(0).alias('montant')
                        ])
                        .sort(['annee', 'mois']))
            
            tendance = by_month.to_dicts()
        
        # Alertes et recommandations
        alertes = []
        recommandations = []
        
        # Alerte sur montant non recouvré
        if kpis.get('total_declare', 0) > 0:
            perte_potentielle = kpis.get('total_declare', 0) - kpis.get('total_recouvre', 0)
            if perte_potentielle > 0:
                alertes.append({
                    'niveau': 'critique' if perte_potentielle > 1000000 else 'moyen',
                    'message': f"Perte potentielle de {perte_potentielle:,.0f} FCFA détectée",
                    'impact': 'financier'
                })
                
                recommandations.append({
                    'priorite': 'haute',
                    'action': 'Lancer une campagne de recouvrement ciblée',
                    'justification': f"Montant significatif en attente de recouvrement"
                })
        
        # Alerte sur volume
        if total_records > 1000:
            alertes.append({
                'niveau': 'info',
                'message': f"{total_records:,} déclarations non recouvrées",
                'impact': 'volume'
            })
            
            recommandations.append({
                'priorite': 'moyenne',
                'action': 'Automatiser le processus de relance',
                'justification': 'Volume élevé nécessitant une approche systématique'
            })
        
        # Top 3 taxes à prioriser
        if 'par_taxe' in repartition and len(repartition['par_taxe']) > 0:
            top_3_taxes = repartition['par_taxe'][:3]
            recommandations.append({
                'priorite': 'haute',
                'action': f"Prioriser le recouvrement sur: {', '.join([t['LIBELLE'] for t in top_3_taxes])}",
                'justification': 'Ces taxes représentent les montants les plus élevés'
            })
        
        return {
            'type': 'executive_summary',
            'titre': self._generate_title(query),
            'kpis': kpis,
            'statistiques': statistiques,
            'repartition': repartition,
            'tendance': tendance,
            'alertes': alertes,
            'recommandations': recommandations,
            'analyse_financiere': self._generate_financial_analysis(df, kpis, 'general'),
            'contexte': self._extract_context(query)
        }
    
    def _analyze_financial_comparison(self, query: str, df: pl.DataFrame) -> Dict[str, Any]:
        """Analyse comparative déclaré vs recouvré"""
        
        total_records = len(df)
        
        # KPIs
        kpis = {
            'total_declare': float(df['MONTANT_DECLARE'].sum()) if 'MONTANT_DECLARE' in df.columns else 0,
            'total_recouvre': float(df['MONTANT_RECOUVRE'].sum()) if 'MONTANT_RECOUVRE' in df.columns else 0
        }
        
        kpis['ecart'] = kpis['total_recouvre'] - kpis['total_declare']
        kpis['taux_recouvrement'] = (kpis['total_recouvre'] / kpis['total_declare'] * 100) if kpis['total_declare'] > 0 else 0
        
        # Performance par taxe
        performance = None
        if 'LIBELLE' in df.columns:
            perf_taxe = (df.group_by('LIBELLE')
                          .agg([
                              pl.count().alias('operations'),
                              pl.col('MONTANT_DECLARE').sum().alias('declare'),
                              pl.col('MONTANT_RECOUVRE').sum().alias('recouvre')
                          ])
                          .with_columns([
                              ((pl.col('recouvre') / pl.col('declare')) * 100).alias('taux_recouvrement')
                          ])
                          .sort('declare', descending=True)
                          .limit(15))
            
            performance = perf_taxe.to_dicts()
        
        # Recommandations
        recommandations = []
        if kpis['taux_recouvrement'] < 100:
            recommandations.append({
                'priorite': 'haute',
                'action': 'Améliorer le taux de recouvrement',
                'justification': f"Taux actuel: {kpis['taux_recouvrement']:.1f}%"
            })
        
        return {
            'type': 'financial_analysis',
            'titre': self._generate_title(query),
            'kpis': kpis,
            'performance': performance,
            'recommandations': recommandations
        }
    
    def _analyze_regional(self, query: str, df: pl.DataFrame) -> Dict[str, Any]:
        """Analyse régionale/géographique"""
        
        # Identifier la colonne géographique
        geo_col = None
        for col in ['BUREAU', 'DIRECTION', 'REGION']:
            if col in df.columns:
                geo_col = col
                break
        
        if not geo_col:
            return self._analyze_general(query, df)
        
        # Performance par zone
        by_zone = (df.group_by(geo_col)
                    .agg([
                        pl.count().alias('operations'),
                        pl.col('MONTANT_DECLARE').sum().alias('montant_declare') if 'MONTANT_DECLARE' in df.columns else pl.lit(0).alias('montant_declare'),
                        pl.col('MONTANT_RECOUVRE').sum().alias('montant_recouvre') if 'MONTANT_RECOUVRE' in df.columns else pl.lit(0).alias('montant_recouvre')
                    ])
                    .sort('montant_declare', descending=True))
        
        zones_data = by_zone.to_dicts()
        
        # KPIs
        kpis = {
            'nombre_zones': len(zones_data),
            'total_operations': len(df)
        }
        
        if 'MONTANT_DECLARE' in df.columns:
            kpis['total_montant'] = float(df['MONTANT_DECLARE'].sum())
        
        # Top 3 et bottom 3 zones
        top_zones = zones_data[:3]
        bottom_zones = zones_data[-3:] if len(zones_data) > 3 else []
        
        return {
            'type': 'regional_analysis',
            'titre': self._generate_title(query),
            'kpis': kpis,
            'top_zones': top_zones,
            'bottom_zones': bottom_zones,
            'toutes_zones': zones_data[:20]  # Limiter à 20 pour lisibilité
        }
    
    def _analyze_temporal(self, query: str, df: pl.DataFrame) -> Dict[str, Any]:
        """Analyse temporelle avec KPIs complets"""
        
        total_records = len(df)
        
        # KPIs Financiers
        kpis = {
            'total_records': total_records
        }
        
        if 'MONTANT_DECLARE' in df.columns:
            total_declare = df['MONTANT_DECLARE'].sum()
            kpis['total_declare'] = float(total_declare) if total_declare else 0
        
        if 'MONTANT_RECOUVRE' in df.columns:
            total_recouvre = df['MONTANT_RECOUVRE'].sum()
            kpis['total_recouvre'] = float(total_recouvre) if total_recouvre else 0
        
        # Calcul du taux de recouvrement
        if 'total_declare' in kpis and 'total_recouvre' in kpis and kpis['total_declare'] > 0:
            kpis['ecart'] = kpis['total_recouvre'] - kpis['total_declare']
            kpis['taux_recouvrement'] = (kpis['total_recouvre'] / kpis['total_declare'] * 100)
        
        # Statistiques descriptives
        statistiques = {
            'nombre_total': total_records,
            'nombre_types_taxes': len(df['LIBELLE'].unique()) if 'LIBELLE' in df.columns else 0
        }
        
        if 'MONTANT_DECLARE' in df.columns and len(df) > 0:
            statistiques['montant_moyen'] = float(df['MONTANT_DECLARE'].mean())
            statistiques['montant_median'] = float(df['MONTANT_DECLARE'].median())
            statistiques['montant_max'] = float(df['MONTANT_DECLARE'].max())
            statistiques['montant_min'] = float(df['MONTANT_DECLARE'].min())
        
        # Répartition par type de taxe
        repartition = {}
        if 'LIBELLE' in df.columns:
            top_taxes = (df.group_by('LIBELLE')
                          .agg([
                              pl.count().alias('nombre'),
                              pl.col('MONTANT_DECLARE').sum().alias('montant_declare') if 'MONTANT_DECLARE' in df.columns else pl.lit(0).alias('montant_declare'),
                              pl.col('MONTANT_RECOUVRE').sum().alias('montant_recouvre') if 'MONTANT_RECOUVRE' in df.columns else pl.lit(0).alias('montant_recouvre')
                          ])
                          .sort('montant_declare', descending=True)
                          .limit(10))
            
            repartition['par_taxe'] = top_taxes.to_dicts()
        
        # Identifier colonne de date
        date_col = None
        for col in df.columns:
            if 'DATE' in col:
                date_col = col
                break
        
        # Évolution temporelle
        tendance = None
        if date_col:
            temporal_df = df.with_columns([
                pl.col(date_col).dt.month().alias('mois'),
                pl.col(date_col).dt.year().alias('annee')
            ])
            
            by_period = (temporal_df.group_by(['annee', 'mois'])
                         .agg([
                             pl.count().alias('operations'),
                             pl.col('MONTANT_DECLARE').sum().alias('montant') if 'MONTANT_DECLARE' in df.columns else pl.lit(0).alias('montant')
                         ])
                         .sort(['annee', 'mois']))
            
            tendance = by_period.to_dicts()
        
        return {
            'type': 'temporal_analysis',
            'titre': self._generate_title(query),
            'kpis': kpis,
            'statistiques': statistiques,
            'repartition': repartition,
            'tendance': tendance,
            'contexte': self._extract_context(query)
        }
    
    def _analyze_general(self, query: str, df: pl.DataFrame) -> Dict[str, Any]:
        """Analyse générale pour tout type de données"""
        
        kpis = {
            'total_records': len(df)
        }
        
        # Calculs sur colonnes numériques
        numeric_cols = [col for col in df.columns if df[col].dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]]
        
        statistiques = {}
        for col in numeric_cols:
            if len(df) > 0:
                statistiques[col] = {
                    'total': float(df[col].sum()),
                    'moyenne': float(df[col].mean()),
                    'max': float(df[col].max()),
                    'min': float(df[col].min())
                }
        
        return {
            'type': 'general_analysis',
            'titre': self._generate_title(query),
            'kpis': kpis,
            'statistiques': statistiques
        }
    
    def _generate_empty_summary(self, query: str) -> Dict[str, Any]:
        """Résumé pour résultats vides"""
        return {
            'type': 'empty_result',
            'titre': 'Aucun Résultat Trouvé',
            'message': f"Aucune donnée ne correspond aux critères : {query}",
            'recommandations': [
                {
                    'priorite': 'haute',
                    'action': 'Vérifier les critères de recherche',
                    'justification': 'Aucune correspondance trouvée'
                }
            ]
        }
    
    def _generate_simple_summary(self, query: str, result: Any) -> Dict[str, Any]:
        """Résumé simple pour résultats non-tabulaires"""
        return {
            'type': 'simple_result',
            'titre': self._generate_title(query),
            'resultat': str(result)
        }
    
    def _generate_fallback_summary(self, query: str, result: Any) -> Dict[str, Any]:
        """Résumé de secours en cas d'erreur"""
        return {
            'type': 'fallback',
            'titre': 'Analyse des Données',
            'message': 'Analyse disponible dans le tableau de résultats'
        }
    
    def _generate_title(self, query: str) -> str:
        """Génère un titre professionnel pour le résumé"""
        query_lower = query.lower()
        
        if 'non recouvr' in query_lower or 'pas recouvr' in query_lower:
            return '📊 Analyse des Déclarations Non Recouvrées'
        elif 'recouvrement' in query_lower:
            return '💰 Analyse de Recouvrement'
        elif any(month in query_lower for month in ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 
                                                     'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']):
            return '📅 Analyse Périodique'
        elif any(place in query_lower for place in ['bureau', 'direction', 'région', 'dakar', 'kedougou']):
            return '🗺️ Analyse Régionale'
        else:
            return '📈 Analyse Fiscale'
    
    def _extract_context(self, query: str) -> Dict[str, Any]:
        """Extrait le contexte de la requête"""
        context = {}
        
        # Extraction du mois
        months_map = {
            'janvier': 1, 'fevrier': 2, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'aout': 8, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'decembre': 12, 'décembre': 12
        }
        
        query_lower = query.lower()
        for month_name, month_num in months_map.items():
            if month_name in query_lower:
                context['mois'] = month_num
                context['mois_nom'] = self.month_names[month_num]
                break
        
        # Extraction de l'année
        import re
        year_match = re.search(r'20\d{2}', query)
        if year_match:
            context['annee'] = int(year_match.group())
        
        return context
    
    def format_for_display(self, summary: Dict[str, Any]) -> str:
        """Formate le résumé pour affichage en Markdown enrichi"""
        
        if summary['type'] == 'executive_summary':
            return self._format_executive_summary(summary)
        elif summary['type'] == 'financial_analysis':
            return self._format_financial_analysis(summary)
        elif summary['type'] == 'regional_analysis':
            return self._format_regional_analysis(summary)
        elif summary['type'] == 'temporal_analysis':
            return self._format_executive_summary(summary)  # Utilise le même format que executive_summary
        elif summary['type'] == 'empty_result':
            return self._format_empty_result(summary)
        else:
            return self._format_general(summary)
    
    def _format_executive_summary(self, summary: Dict[str, Any]) -> str:
        """Formate un résumé exécutif complet"""
        
        md = f"### {summary['titre']}\n\n"
        
        # Contexte
        if summary.get('contexte'):
            ctx = summary['contexte']
            if 'mois_nom' in ctx and 'annee' in ctx:
                md += f"**📅 PÉRIODE ANALYSÉE:** {ctx['mois_nom']} {ctx['annee']}\n\n"
        
        # KPIs Clés
        kpis = summary.get('kpis', {})
        if kpis:
            md += "**🎯 INDICATEURS CLÉS**\n\n"
            
            if 'total_declare' in kpis:
                md += f"- **Montant Déclaré Total:** {kpis['total_declare']:,.0f} FCFA\n"
            
            if 'total_recouvre' in kpis:
                md += f"- **Montant Recouvré Total:** {kpis['total_recouvre']:,.0f} FCFA\n"
            
            if 'ecart' in kpis:
                ecart = kpis['ecart']
                perte = abs(ecart) if ecart < 0 else kpis['total_declare'] - kpis['total_recouvre']
                if perte > 0:
                    md += f"- **💸 Perte Potentielle:** {perte:,.0f} FCFA\n"
            
            if 'taux_recouvrement' in kpis:
                taux = kpis['taux_recouvrement']
                emoji = '🔴' if taux < 80 else '🟡' if taux < 95 else '🟢'
                md += f"- **{emoji} Taux de Recouvrement:** {taux:.1f}%\n"
            
            md += "\n"
        
        # Statistiques
        stats = summary.get('statistiques', {})
        if stats:
            md += "**📊 STATISTIQUES DESCRIPTIVES**\n\n"
            
            if 'nombre_total' in stats:
                md += f"- **Volume:** {stats['nombre_total']:,} déclarations\n"
            
            if 'nombre_types_taxes' in stats:
                md += f"- **Diversité:** {stats['nombre_types_taxes']} types de taxes différents\n"
            
            if 'montant_moyen' in stats:
                md += f"- **Montant Moyen:** {stats['montant_moyen']:,.0f} FCFA\n"
            
            if 'montant_median' in stats:
                md += f"- **Montant Médian:** {stats['montant_median']:,.0f} FCFA\n"
            
            if 'montant_max' in stats:
                md += f"- **Montant Maximum:** {stats['montant_max']:,.0f} FCFA\n"
            
            md += "\n"
        
        # Alertes
        alertes = summary.get('alertes', [])
        if alertes:
            md += "**🚨 ALERTES**\n\n"
            for alerte in alertes:
                emoji = '🔴' if alerte['niveau'] == 'critique' else '🟡' if alerte['niveau'] == 'moyen' else 'ℹ️'
                md += f"- {emoji} **{alerte['niveau'].upper()}:** {alerte['message']}\n"
            md += "\n"
        
        # Répartition par taxe
        repartition = summary.get('repartition', {})
        if 'par_taxe' in repartition and len(repartition['par_taxe']) > 0:
            md += "**📈 TOP TAXES PAR MONTANT**\n\n"
            for idx, taxe in enumerate(repartition['par_taxe'][:5], 1):
                montant = taxe.get('montant_declare', 0)
                nombre = taxe.get('nombre', 0)
                md += f"{idx}. **{taxe['LIBELLE']}**\n"
                md += f"   - Montant: {montant:,.0f} FCFA\n"
                md += f"   - Opérations: {nombre:,}\n"
            md += "\n"
        
        # Répartition par bureau
        if 'par_bureau' in repartition and len(repartition['par_bureau']) > 0:
            md += "**🏢 TOP BUREAUX**\n\n"
            for idx, bureau in enumerate(repartition['par_bureau'][:5], 1):
                montant = bureau.get('montant_declare', 0)
                nombre = bureau.get('nombre', 0)
                md += f"{idx}. **{bureau['BUREAU']}:** {montant:,.0f} FCFA ({nombre:,} opérations)\n"
            md += "\n"
        
        # Analyse Financière Experte
        analyse_financiere = summary.get('analyse_financiere', {})
        if analyse_financiere:
            md += "---\n\n"
            md += "## 💼 ANALYSE FINANCIÈRE EXPERTE\n\n"
            
            # Synthèse globale
            synthese = analyse_financiere.get('synthese', '')
            if synthese:
                md += f"**📊 Synthèse Globale:**\n\n{synthese}\n\n"
            
            # Tendances détectées
            tendances = analyse_financiere.get('tendances', [])
            if tendances:
                md += "**📈 Tendances Détectées:**\n\n"
                for tendance in tendances:
                    md += f"- {tendance}\n"
                md += "\n"
            
            # Points de vigilance
            vigilance = analyse_financiere.get('points_vigilance', [])
            if vigilance:
                md += "**⚠️ Points de Vigilance:**\n\n"
                for point in vigilance:
                    md += f"- 🔴 {point}\n"
                md += "\n"
            
            # Opportunités
            opportunites = analyse_financiere.get('opportunites', [])
            if opportunites:
                md += "**💡 Opportunités Identifiées:**\n\n"
                for opp in opportunites:
                    md += f"- ✅ {opp}\n"
                md += "\n"
            
            # Risques
            risques = analyse_financiere.get('risques', [])
            if risques:
                md += "**🚨 Risques Identifiés:**\n\n"
                for risque in risques:
                    md += f"- ⚠️ {risque}\n"
                md += "\n"
            
            # Recommandations stratégiques
            reco_strat = analyse_financiere.get('recommandations_strategiques', [])
            if reco_strat:
                md += "**🎯 Recommandations Stratégiques:**\n\n"
                md += "| Priorité | Action | Impact Attendu |\n"
                md += "|----------|--------|----------------|\n"
                for reco in reco_strat:
                    priority_icon = '🔥' if reco['priorite'] == 'critique' else '⚡' if reco['priorite'] == 'haute' else '📌'
                    md += f"| {priority_icon} {reco['priorite'].upper()} | {reco['action']} | {reco['impact']} |\n"
                md += "\n"
        
        # Recommandations
        recommandations = summary.get('recommandations', [])
        if recommandations:
            md += "**💡 RECOMMANDATIONS OPÉRATIONNELLES**\n\n"
            for idx, reco in enumerate(recommandations, 1):
                priority_emoji = '🔥' if reco['priorite'] == 'haute' else '⚡' if reco['priorite'] == 'moyenne' else '📌'
                md += f"{idx}. {priority_emoji} **{reco['action']}**\n"
                md += f"   - *{reco['justification']}*\n"
            md += "\n"
        
        return md
    
    def _format_financial_analysis(self, summary: Dict[str, Any]) -> str:
        """Formate une analyse financière"""
        
        md = f"### {summary['titre']}\n\n"
        
        kpis = summary.get('kpis', {})
        if kpis:
            md += "**💰 PERFORMANCE FINANCIÈRE**\n\n"
            md += f"- Déclaré: {kpis['total_declare']:,.0f} FCFA\n"
            md += f"- Recouvré: {kpis['total_recouvre']:,.0f} FCFA\n"
            md += f"- Taux: {kpis['taux_recouvrement']:.1f}%\n\n"
        
        performance = summary.get('performance', [])
        if performance:
            md += "**📊 PERFORMANCE PAR TAXE**\n\n"
            for idx, perf in enumerate(performance[:10], 1):
                taux = perf.get('taux_recouvrement', 0)
                emoji = '🟢' if taux >= 95 else '🟡' if taux >= 80 else '🔴'
                md += f"{idx}. {emoji} **{perf['LIBELLE']}:** {taux:.1f}% ({perf['operations']} ops)\n"
            md += "\n"
        
        return md
    
    def _format_regional_analysis(self, summary: Dict[str, Any]) -> str:
        """Formate une analyse régionale"""
        
        md = f"### {summary['titre']}\n\n"
        
        kpis = summary.get('kpis', {})
        md += f"**🗺️ COUVERTURE:** {kpis.get('nombre_zones', 0)} zones - {kpis.get('total_operations', 0):,} opérations\n\n"
        
        top_zones = summary.get('top_zones', [])
        if top_zones:
            md += "**🏆 MEILLEURES PERFORMANCES**\n\n"
            for idx, zone in enumerate(top_zones, 1):
                md += f"{idx}. **{list(zone.values())[0]}:** {zone.get('montant_declare', 0):,.0f} FCFA\n"
            md += "\n"
        
        return md
    
    def _format_empty_result(self, summary: Dict[str, Any]) -> str:
        """Formate un résultat vide"""
        return f"### ❌ {summary['titre']}\n\n{summary['message']}\n"
    
    def _format_general(self, summary: Dict[str, Any]) -> str:
        """Format général"""
        return f"### {summary.get('titre', 'Analyse')}\n\nRésultats disponibles dans le tableau ci-dessous.\n"
