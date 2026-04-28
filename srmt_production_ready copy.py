"""
SRMT Business Intelligence Platform - Simplified Production Version
Version prête pour déploiement immédiat avec toutes les optimisations de production
"""

import os
import re
import json
import time
import math
from datetime import datetime, date, timedelta
import logging
import warnings
import requests  # Pour les appels IA de correction
from functools import lru_cache
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union

# Optimiseur de requêtes
try:
    from query_optimizer import QueryOptimizer, AdvancedPolarsOptimizer
except ImportError:
    # Fallback si le fichier n'existe pas encore
    QueryOptimizer = None
    AdvancedPolarsOptimizer = None
from pathlib import Path
import hashlib

# Data processing
import polars as pl
import pandas as pd # Gardé pour compatibilité de types mineurs si nécessaire
import numpy as np

# AI and ML
from openai import OpenAI
from difflib import SequenceMatcher
from collections import defaultdict, Counter

# Web framework
from flask import Flask, render_template_string, request, jsonify, g

# Decision Presenter for Executive Summaries
try:
    from decision_presenter import DecisionPresenter
    DECISION_PRESENTER_AVAILABLE = True
except ImportError:
    DECISION_PRESENTER_AVAILABLE = False
    DecisionPresenter = None

# AI Learning System
try:
    from ai_learning_system import AILearningSystem
    AI_LEARNING_AVAILABLE = True
except ImportError:
    AI_LEARNING_AVAILABLE = False
    AILearningSystem = None

# Basic caching (fallback if Redis not available)
try:
    from flask_caching import Cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    Cache = None

# Suppress warnings for cleaner production logs
warnings.filterwarnings('ignore')
pd.options.mode.chained_assignment = None

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ProductionConfig:
    """Configuration optimisée pour production"""
    
    # AI Configuration
    NVIDIA_API_KEY: str = field(default_factory=lambda: os.getenv('NVIDIA_API_KEY', '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'))
    NVIDIA_BASE_URL: str = field(default_factory=lambda: os.getenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1'))
    # FAST Modèle actif et performant - Utilisez AI_MODEL env var pour changer
    # ✅ Modèles disponibles 2026:
    #    - meta/llama-3.1-8b-instruct (rapide, général) ← PAR DÉFAUT
    #    - mistralai/mistral-7b-instruct-v0.3 (rapide, polyvalent)
    #    - qwen/qwen2.5-coder-32b-instruct (codage, moyen)
    #    - meta/llama-3.1-70b-instruct (précis, lent)
    #    - nvidia/nemotron-4-340b-instruct (très puissant mais lent)
    #    - meta/llama-3.1-405b-instruct (ultra, très lent)
    # ⛔ Modèles obsolètes: qwen/qwen2.5-coder-7b-instruct, qwen/qwq-32b-preview (404 not found)
    MODEL_NAME: str = field(default_factory=lambda: os.getenv('AI_MODEL', 'meta/llama-3.1-8b-instruct'))
    MAX_TOKENS: int = field(default_factory=lambda: int(os.getenv('MAX_TOKENS', '1000')))
    TEMPERATURE: float = field(default_factory=lambda: float(os.getenv('TEMPERATURE', '0.05')))
    
    # Data Configuration
    DATA_FILE: str = field(default_factory=lambda: os.getenv('DATA_FILE', './srmt_data_2020_2025.parquet'))
    CHUNK_SIZE: int = field(default_factory=lambda: int(os.getenv('CHUNK_SIZE', '100000')))
    
    # Cache Configuration
    CACHE_TTL: int = field(default_factory=lambda: int(os.getenv('CACHE_TTL', '1800')))  # 30 minutes
    
    # Performance
    REQUEST_TIMEOUT: int = field(default_factory=lambda: int(os.getenv('REQUEST_TIMEOUT', '120')))  # FAST 120s pour API NVIDIA lente
    MAX_QUERY_TIME: int = field(default_factory=lambda: int(os.getenv('MAX_QUERY_TIME', '90')))  # FAST Timeout global par requête (augmenté)
    ENABLE_AUTO_CORRECTION: bool = field(default_factory=lambda: os.getenv('AUTO_CORRECTION', 'false').lower() == 'true')  # FAST Désactivé - cause des problèmes avec le LLM
    ENABLE_RECOMMENDATIONS: bool = field(default_factory=lambda: os.getenv('ENABLE_RECOMMENDATIONS', 'false').lower() == 'true')  # FAST Désactivé (gagne 30s)
    ENABLE_ALERTS: bool = field(default_factory=lambda: os.getenv('ENABLE_ALERTS', 'false').lower() == 'true')  # FAST Désactivé (gagne 30s)
    
    #  Mode IA Pure - 100% Intelligence Artificielle
    PURE_AI_MODE: bool = field(default_factory=lambda: os.getenv('PURE_AI_MODE', 'false').lower() == 'true')  #  Mode 100% IA sans règles
    AI_CONFIDENCE_THRESHOLD: float = field(default_factory=lambda: float(os.getenv('AI_CONFIDENCE_THRESHOLD', '0.8')))  # Seuil de confiance IA
    
    # Production flags
    PRODUCTION_MODE: bool = field(default_factory=lambda: os.getenv('PRODUCTION', 'false').lower() == 'true')
    DEBUG_MODE: bool = field(default_factory=lambda: os.getenv('DEBUG', 'false').lower() == 'true')
    DEBUG_EXECUTION: bool = field(default_factory=lambda: os.getenv('DEBUG_EXECUTION', 'true').lower() == 'true')

class OptimizedDataLoader:
    """Chargement optimisé des données avec Polars"""
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        self.data = None
        self.data_summary = None
        
    @lru_cache(maxsize=1)
    def load_data(self) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        """Charge les données avec Polars (beaucoup plus rapide)"""
        start_time = time.time()
        
        try:
            if not os.path.exists(self.config.DATA_FILE):
                raise FileNotFoundError(f"Fichier de données non trouvé: {self.config.DATA_FILE}")
            
            
            # *** OPTIMISATION ULTRA-RAPIDE: Garder en lazy + créer lookup index
            lazy_frame = pl.scan_parquet(self.config.DATA_FILE)
            
            # Matérialiser UNE SEULE FOIS pour métadonnées et index
            df_temp = lazy_frame.collect()
            
            # Conversion explicite des dates si nécessaire
            date_cols = ['DATE_RECOUVREMENT', 'DATE_DECLARATION', 'DATE_ECHEANCE']
            for col in date_cols:
                if col in df_temp.columns and df_temp[col].dtype == pl.Utf8:
                    df_temp = df_temp.with_columns(pl.col(col).str.strptime(pl.Date, "%Y-%m-%d", strict=False))
            
            # ⚡ OPTIMISATION: Ne garder que les 2 dernières années (2025-2026)
            if 'DATE_DECLARATION' in df_temp.columns:
                annee_min = date.today().year - 1  # Année courante - 1
                logger.info(f"⚡ Filtrage données: uniquement >= {annee_min} (2 dernières années)")
                df_temp = df_temp.filter(pl.col('DATE_DECLARATION').dt.year() >= annee_min)
                logger.info(f"✅ Après filtrage: {len(df_temp):,} enregistrements (au lieu de 11M+)")
            
            # *** CRER INDEX DE LOOKUP pour filtres rapides (bureaux/directions normalisés)
            self.lookup_index = self._create_lookup_index(df_temp)
            
            # Garder données en LAZY pour pushdown optimization
            self.data = df_temp.lazy()
            
            # Aussi garder version matérialisée triée pour opérations non-lazy
            self.data_materialized = df_temp.sort('DATE_DECLARATION')
            logger.info(f"DATA Index de lookup créé pour accès ultra-rapide")

            # Création du résumé (utiliser version matérialisée)
            self.data_summary = self._create_summary(df_temp)
            
            # *** OPTIMISATION: Créer tables pré-agrégées (utiliser version matérialisée)
            self.aggregated_tables = self._create_aggregated_tables(df_temp)
            self.data_summary['aggregated_tables'] = list(self.aggregated_tables.keys())
            
            load_time = time.time() - start_time
            logger.info(f"OK Données chargées en {load_time:.2f}s: {len(df_temp):,} enregistrements")
            
            return self.data_materialized, self.data_summary
            
        except Exception as e:
            logger.error(f"ERREUR chargement données: {e}")
            raise
    
    def _create_lookup_index(self, df: pl.DataFrame) -> Dict[str, set]:
        """*** CRATION INDEX DE LOOKUP - Accès O(1) pour filtres communs"""
        logger.info("INDEX Création index de lookup...")
        lookup = {}
        
        try:
            # Index BUREAU (liste simple)
            if 'BUREAU' in df.columns:
                bureaux = df.select(pl.col('BUREAU').unique()).drop_nulls()['BUREAU'].to_list()
                lookup['BUREAU'] = sorted([str(b) for b in bureaux])
                logger.info(f"OK Index BUREAU: {len(lookup['BUREAU'])} valeurs")
            
            # Index DIRECTION (liste simple)
            if 'DIRECTION' in df.columns:
                directions = df.select(pl.col('DIRECTION').unique()).drop_nulls()['DIRECTION'].to_list()
                lookup['DIRECTION'] = sorted([str(d) for d in directions])
                logger.info(f"OK Index DIRECTION: {len(lookup['DIRECTION'])} valeurs")
            
            # Index SOURCE (liste simple)
            if 'SOURCE' in df.columns:
                sources = df.select(pl.col('SOURCE').unique()).drop_nulls()['SOURCE'].to_list()
                lookup['SOURCE'] = sorted([str(s) for s in sources])
                logger.info(f"OK Index SOURCE: {len(lookup['SOURCE'])} valeurs")
            
        except Exception as e:
            logger.warning(f" Erreur création index lookup: {e}")
        
        return lookup
    
    def _create_aggregated_tables(self, df: pl.DataFrame) -> Dict[str, pl.LazyFrame]:
        """*** PR-AGRGATION: Créer tables optimisées pour requêtes communes"""
        logger.info("DATA Création des tables pré-agrégées...")
        start_time = time.time()
        
        aggregated = {}
        
        try:
            # 1. Agrégation mensuelle (année-mois)
            if 'DATE_DECLARATION' in df.columns:
                monthly_agg = df.lazy().with_columns([
                    pl.col('DATE_DECLARATION').dt.year().alias('ANNEE'),
                    pl.col('DATE_DECLARATION').dt.month().alias('MOIS')
                ]).group_by(['ANNEE', 'MOIS']).agg([
                    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
                    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
                    pl.len().alias('NOMBRE_DECLARATIONS')
                ])
                aggregated['monthly_summary'] = monthly_agg
                logger.info("OK Table mensuelle créée")
            
            # 2. Top 100 contribuables (pré-calculé)
            if 'LIBELLE' in df.columns:
                top_contributors = df.lazy().group_by('LIBELLE').agg([
                    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
                    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
                    pl.len().alias('NOMBRE_DECLARATIONS')
                ]).sort('TOTAL_RECOUVRE', descending=True).head(100)
                aggregated['top_contributors'] = top_contributors
                logger.info("OK Top 100 contribuables créé")
            
            # 3. Statistiques par bureau
            if 'BUREAU' in df.columns:
                bureau_stats = df.lazy().group_by('BUREAU').agg([
                    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
                    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
                    pl.col('MONTANT_DECLARE').mean().alias('MOYENNE_DECLARE'),
                    pl.len().alias('NOMBRE_DECLARATIONS')
                ])
                aggregated['bureau_stats'] = bureau_stats
                logger.info("OK Statistiques par bureau créées")
            
            # 4. Statistiques par direction
            if 'DIRECTION' in df.columns:
                region_stats = df.lazy().group_by('DIRECTION').agg([
                    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
                    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
                    pl.len().alias('NOMBRE_DECLARATIONS')
                ])
                aggregated['region_stats'] = region_stats
                logger.info("OK Statistiques régionales créées")
            
            # 5. Statistiques par type de taxe
            if 'TAXE_IMPOT_CD' in df.columns:
                tax_stats = df.lazy().group_by('TAXE_IMPOT_CD').agg([
                    pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'),
                    pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'),
                    pl.len().alias('NOMBRE_DECLARATIONS')
                ])
                aggregated['tax_stats'] = tax_stats
                logger.info("OK Statistiques par taxe créées")
            
            elapsed = time.time() - start_time
            logger.info(f"OK Pré-agrégation terminée en {elapsed:.2f}s ({len(aggregated)} tables)")
            
        except Exception as e:
            logger.warning(f" Erreur pré-agrégation: {e}")
        
        return aggregated
    
    def _create_summary(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Crée un résumé structuré des données (Version Polars)"""
        summary = {
            'shape': df.shape,
            'columns': {},
            'numeric_columns': [col for col, dtype in zip(df.columns, df.dtypes) if dtype in [pl.Int64, pl.Float64, pl.Int32, pl.Float32]],
            'categorical_columns': [col for col, dtype in zip(df.columns, df.dtypes) if dtype == pl.Utf8 or dtype == pl.Categorical],
            'date_columns': [col for col, dtype in zip(df.columns, df.dtypes) if dtype == pl.Date or dtype == pl.Datetime],
            'memory_usage_mb': df.estimated_size() / 1024**2
        }
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            summary['columns'][col] = {
                'dtype': dtype,
                'null_count': df[col].null_count(),
                'unique_count': df[col].n_unique()
            }
            
            if col in summary['categorical_columns']:
                try:
                    # MAXIMISER les échantillons pour que l'IA connaisse TOUTES les modalités possibles
                    unique_vals = df[col].n_unique()
                    # Si < 100 valeurs uniques, montrer TOUT; sinon montrer 100 premiers
                    limit = unique_vals if unique_vals <= 100 else 100
                    samples = df[col].unique().head(limit).to_list()
                    summary['columns'][col]['samples'] = [s for s in samples if s]
                    summary['columns'][col]['total_unique'] = unique_vals
                except:
                    summary['columns'][col]['samples'] = []
            
        return summary

class ProductionRAGSystem:
    """ Système RAG Ultra-Intelligent - Apprentissage Pur des Données"""
    
    def __init__(self, data: Union[pl.DataFrame, pl.LazyFrame]):
        # Accepter lazy ou materializé
        if isinstance(data, pl.LazyFrame):
            self.data = data  # Garder lazy pour requêtes
            # Matérialiser uniquement les colonnes nécessaires pour indexation
            self.data_for_index = data.select([
                pl.col('BUREAU'), pl.col('DIRECTION'), pl.col('SOURCE')
            ]).unique().collect()
        else:
            self.data = data.lazy()  # Convertir en lazy si nécessaire
            self.data_for_index = data
        
        self.index = {}
        self.fuzzy_index = defaultdict(list)
        self._build_index()
    
    def _build_index(self):
        """Construction de l'index de recherche - Approche IA Pure"""
        # Index des colonnes (utiliser la version lazy)
        if isinstance(self.data, pl.LazyFrame):
            # Collecter juste les noms de colonnes
            columns = self.data.collect_schema().names()
        else:
            columns = self.data.columns
        
        for col in columns:
            self.index[col.lower()] = {'type': 'column', 'name': col}
        
        # Index des valeurs pour colonnes importantes (utiliser data_for_index)
        important_columns = [
            'BUREAU', 'DIRECTION', 'SOURCE'
        ]
        for col in important_columns:
            if col in self.data_for_index.columns:
                try:
                    # Indexer TOUTES les valeurs uniques
                    unique_values = self.data_for_index[col].unique().drop_nulls().to_list()
                    logger.info(f"INDEX Indexation RAG: {col} ({len(unique_values)} valeurs uniques)")
                    for val in unique_values:
                        key = str(val).lower().strip()
                        if len(key) > 1:
                            self.index[key] = {'type': 'value', 'column': col, 'original': val}
                except Exception as e:
                    logger.warning(f" Erreur indexation {col}: {e}")
    
    def _analyze_error_with_ai(self, error_msg: str, code: str, query: str, schema_info: str) -> str:
        """ ANALYSE D'ERREUR PURE IA - Sans règles prédéfinies"""
        # L'IA analyse l'erreur et génère une correction intelligente
        # Pas de patterns hardcodés, juste l'intelligence de l'IA
        return error_msg  # L'erreur brute sera envoyée à l'IA pour analyse
    

    
    @lru_cache(maxsize=500)
    def search(self, query: str) -> Dict[str, Any]:
        """Recherche avec cache"""
        query_words = re.findall(r'\w+', query.lower())
        
        results = {
            'exact_matches': [],
            'fuzzy_matches': [],
            'suggestions': []
        }
        
        for word in query_words:
            if len(word) > 2:
                # Recherche exacte
                if word in self.index:
                    results['exact_matches'].append(self.index[word])
                
                # Recherche floue
                if word in self.fuzzy_index:
                    results['fuzzy_matches'].extend(self.fuzzy_index[word])
                
                # Recherche améliorée: Similarité ET Contenu
                # Optimisation: On évite de scanner tout l'index si le mot est très court
                if len(word) > 3:
                    for key in self.index.keys():
                        if word == key: continue
                        
                        # 1. Contenu (Le mot de la requête est dans la valeur)
                        # Ex: "Douane" -> "Droit de Douane"
                        if word in key:
                            results['fuzzy_matches'].append(self.index[key])
                            continue # Si trouvé par inclusion, pas besoin de check similarity
                            
                        # 2. Similarité (Typos)
                        similarity = SequenceMatcher(None, word, key).ratio()
                        if similarity > 0.8:
                            match = self.index[key].copy()
                            match['similarity'] = similarity
                            results['fuzzy_matches'].append(match)
        
        # Pas de suggestions prédéfinies - l'IA apprend du contexte
        results['suggestions'] = []
        
        return results

class ProductionAIEngine:
    """Moteur IA optimisé pour production"""
    
    def __init__(self, config: ProductionConfig, rag_system: ProductionRAGSystem, data_summary: Dict[str, Any], aggregated_tables: Dict[str, Any] = None, lookup_index: Dict[str, Dict] = None):
        self.config = config
        self.rag_system = rag_system
        self.data_summary = data_summary
        self.aggregated_tables = aggregated_tables or {}
        self.lookup_index = lookup_index or {}
        
        # *** CACHE INTELLIGENT: Stocker résultats similaires
        # ⚠️ Cache vidé à chaque redémarrage pour éviter les résultats obsolètes
        self.query_cache = {}  # {query_hash: (result, timestamp)}
        self.cache_ttl = 1800  # 30 minutes (réduit de 1h pour forcer refresh plus fréquent)
        
        #  SYSTME D'APPRENTISSAGE IA
        if AI_LEARNING_AVAILABLE:
            self.learning_system = AILearningSystem()
            logger.info(f"OK Système d'apprentissage IA initialisé ({len(self.learning_system.patterns)} patterns)")
        else:
            self.learning_system = None
            logger.warning(" Système d'apprentissage IA non disponible")
        
        # Client IA avec timeout
        self.client = OpenAI(
            api_key=config.NVIDIA_API_KEY,
            base_url=config.NVIDIA_BASE_URL,
            timeout=config.REQUEST_TIMEOUT,
            max_retries=0  # OPTIMISATION CRITIQUE : Désactive les retries automatiques qui causent l'effet "infini"
        )
        
        # Decision Presenter pour analyses décisionnelles
        if DECISION_PRESENTER_AVAILABLE:
            self.decision_presenter = DecisionPresenter()
            logger.info("OK DecisionPresenter initialisé pour analyses décisionnelles")
        else:
            self.decision_presenter = None
            logger.warning(" DecisionPresenter non disponible - utilisation du fallback")
        
        # Fonction de recherche fuzzy pour lookup
        def find_match(keyword: str, column: str) -> list:
            """Trouve les valeurs contenant le mot-cle (case-insensitive)"""
            keyword_lower = keyword.lower()
            return [v for v in self.lookup_index.get(column, []) if keyword_lower in v.lower()]
        
        # Environnement d'exécution sécurisé (Polars + Tables pré-agrégées)
        from datetime import date, datetime, timedelta
        self.safe_globals = {
            'pl': pl,
            'np': np,
            'data': rag_system.data,  # Déjà en lazy pour pushdown optimization
            'lookup': self.lookup_index,  # Index de lookup pour filtres rapides
            'find_match': find_match,  # Fonction de recherche fuzzy
            'len': len, 'str': str, 'int': int, 'float': float,
            'sum': sum, 'max': max, 'min': min, 'round': round,
            'list': list, 'dict': dict, 'sorted': sorted,
            # Dates pré-définies pour l'IA
            'TODAY': date.today(),  # Date du jour
            'date': date,  # Module date
            'datetime': datetime,  # Module datetime
            'timedelta': timedelta  # Pour calculs de dates
        }
        
        # Ajouter tables pré-agrégées à l'environnement
        for table_name, lazy_frame in self.aggregated_tables.items():
            try:
                self.safe_globals[table_name] = lazy_frame.collect()
                logger.info(f"OK Table '{table_name}' disponible pour l'IA")
            except Exception as e:
                logger.warning(f" Erreur chargement table {table_name}: {e}")
    
    def _hash_query(self, query: str) -> str:
        """Générer hash normalisé pour cache intelligent"""
        import hashlib
        # Normaliser: minuscules, sans espaces multiples, sans ponctuation
        normalized = ' '.join(query.lower().split())
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _check_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """Vérifier si résultat en cache (valide)"""
        query_hash = self._hash_query(query)
        if query_hash in self.query_cache:
            result, timestamp = self.query_cache[query_hash]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"SAVE Cache HIT pour: {query[:50]}...")
                result['cached'] = True
                result['cache_age'] = time.time() - timestamp
                return result
            else:
                # Cache expiré
                del self.query_cache[query_hash]
        return None
    
    def _save_to_cache(self, query: str, result: Dict[str, Any]):
        """Sauvegarder résultat dans cache"""
        query_hash = self._hash_query(query)
        self.query_cache[query_hash] = (result.copy(), time.time())
        # Limiter taille cache (garder 100 dernières requêtes)
        if len(self.query_cache) > 100:
            oldest = min(self.query_cache.items(), key=lambda x: x[1][1])
            del self.query_cache[oldest[0]]
            logger.info(" Cache nettoyé (limite 100 entrées)")
    
    def _fallback_correct_entities(self, query: str) -> tuple[str, bool]:
        """TOOL FALLBACK DTERMINISTE - Correction basée sur les données RELLES de la base"""
        corrected = query
        has_corrections = False
        
        try:
            query_lower = query.lower()
            
            # 1. CORRECTION DES BUREAUX - Recherche dans lookup_index
            if 'BUREAU' in self.lookup_index:
                bureaux = self.lookup_index['BUREAU']
                
                # Patterns communs à détecter: "bureau de X", "bureau X", "au X"
                import re
                bureau_patterns = [
                    r'bureau\s+(?:de\s+)?(\w+)',  # "bureau de kedougou" ou "bureau kedougou"
                    r'(?:au|dans\s+le|du)\s+(?:bureau\s+)?(?:de\s+)?(\w+)',  # "au kedougou", "dans le bureau de X"
                ]
                
                for pattern in bureau_patterns:
                    matches = re.finditer(pattern, query_lower, re.IGNORECASE)
                    for match in matches:
                        ville_mentionnee = match.group(1).lower()
                        
                        # Chercher le bureau correspondant dans les données réelles
                        for bureau_reel in bureaux:
                            # Vérifier si la ville mentionnée est dans le nom du bureau
                            if ville_mentionnee in bureau_reel.lower():
                                # Remplacer dans la requête
                                original_text = match.group(0)
                                # Construire le remplacement avec le nom exact du bureau
                                if 'bureau' in original_text.lower():
                                    new_text = f"au {bureau_reel}"
                                else:
                                    new_text = bureau_reel
                                
                                # viter les doublons comme "au au"
                                if 'au au' in new_text.lower():
                                    new_text = new_text.replace('au au', 'au')
                                
                                corrected = corrected[:match.start()] + new_text + corrected[match.end():]
                                has_corrections = True
                                logger.info(f"TOOL FALLBACK CORRECTION: '{original_text}'  '{new_text}' (bureau réel: {bureau_reel})")
                                break
            
            # 2. CORRECTION DES DIRECTIONS
            if 'DIRECTION' in self.lookup_index and not has_corrections:
                directions = self.lookup_index['DIRECTION']
                
                for direction in directions:
                    # Extraire le nom de la direction (ex: "DGI Dakar"  "dakar")
                    dir_words = direction.lower().split()
                    for word in dir_words:
                        if len(word) > 3 and word in query_lower:
                            # Vérifier si ce n'est pas déjà correct
                            if direction.lower() not in query_lower:
                                corrected = re.sub(
                                    rf'\b{word}\b', 
                                    direction, 
                                    corrected, 
                                    flags=re.IGNORECASE, 
                                    count=1
                                )
                                has_corrections = True
                                logger.info(f"TOOL FALLBACK DIRECTION: '{word}'  '{direction}'")
                                break
            
            return corrected, has_corrections
            
        except Exception as e:
            logger.warning(f" Erreur fallback correction: {e}")
            return query, False
    
    def _analyze_and_correct_prompt(self, query: str) -> tuple[str, bool]:
        """TOOL CORRECTION AUTOMATIQUE - Orthographe et terminologie fiscale SRMT"""
        try:
            # Prompt pour l'IA NVIDIA pour correction automatique
            correction_prompt = f"""Corrige les fautes d'orthographe et la terminologie dans cette phrase pour correspondre au système fiscal SRMT sénégalais:
"{query}"

RGLES DE CORRECTION:
1. Villes mal orthographiées: ziguichorziguinchor, kidougoukédougou, etc.
2. BUREAUX FISCAUX - Toujours utiliser le préfixe correct:
   - "bureau de kedougou"  "CSF de kedougou"
   - "bureau de thies"  "CSP de thies" 
   - "bureau de kaolack"  "CSF de kaolack"
   - En général: "bureau de [ville]"  "CSF de [ville]" ou "CSP de [ville]"
3. Si AUCUNE correction n'est nécessaire, retourne EXACTEMENT la phrase originale
4. NE JAMAIS ajouter d'explication ou de commentaire
5. Retourne UNIQUEMENT la phrase (corrigée ou non)

Phrase:"""

            # Appel à l'IA NVIDIA pour correction
            headers = {
                "Authorization": f"Bearer {self.config.NVIDIA_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.MODEL_NAME,
                "messages": [
                    {"role": "system", "content": "Tu es un expert correcteur spécialisé en géographie sénégalaise et terminologie fiscale. Tu corriges automatiquement les erreurs."},
                    {"role": "user", "content": correction_prompt}
                ],
                "temperature": 0.1,  # Très bas pour cohérence
                "max_tokens": 150
            }
            
            response = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                corrected_query = result['choices'][0]['message']['content'].strip()
                
                # Nettoyer la réponse
                corrected_query = corrected_query.strip('"\'`\n').strip()
                
                # Si l'IA a retourné une explication au lieu de la phrase, ignorer
                if "il n'y a pas" in corrected_query.lower() or "aucune correction" in corrected_query.lower() or "reste inchangée" in corrected_query.lower():
                    # TOOL FALLBACK: Appliquer correction déterministe basée sur données réelles
                    fallback_query, fallback_applied = self._fallback_correct_entities(query)
                    if fallback_applied:
                        return fallback_query, True
                    logger.info(f"OK PROMPT DJ CORRECT: {query}")
                    return query, False
                
                # Vérifier si une correction a été faite
                has_corrections = corrected_query.lower().strip() != query.lower().strip()
                
                if has_corrections:
                    logger.info(f" CORRECTION IA AUTOMATIQUE:")
                    logger.info(f" ORIGINAL: {query}")
                    logger.info(f" CORRIG: {corrected_query}")
                    
                    # TOOL FALLBACK ADDITIONNEL: Vérifier que les entités corrigées existent dans les données
                    final_query, final_applied = self._fallback_correct_entities(corrected_query)
                    if final_applied:
                        logger.info(f"TOOL FALLBACK APPLIQU APRS IA: {final_query}")
                        return final_query, True
                    
                    return corrected_query, True
                else:
                    # TOOL FALLBACK: Appliquer correction déterministe si l'IA n'a rien corrigé
                    fallback_query, fallback_applied = self._fallback_correct_entities(query)
                    if fallback_applied:
                        return fallback_query, True
                    logger.info(f"OK PROMPT DJ CORRECT: {query}")
                    return query, False
            else:
                logger.warning(f" Erreur correction IA: {response.status_code}")
                # TOOL FALLBACK si l'IA échoue
                return self._fallback_correct_entities(query)
                
        except Exception as e:
            logger.error(f"ERREUR Erreur lors de la correction IA: {e}")
            # TOOL FALLBACK en cas d'exception
            return self._fallback_correct_entities(query)
    
    # ⚠️ CACHE DÉSACTIVÉ : Les données fiscales changent constamment, chaque requête doit être fraîche
    # @lru_cache(maxsize=200)  # Cache Python désactivé
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """ ANALYSE INTELLIGENTE - DONNÉES TOUJOURS FRAÎCHES"""
        start_time = time.time()
        
        # ⚠️ CACHE DÉSACTIVÉ : Pour garantir des données toujours à jour
        # Les données fiscales évoluent constamment, le cache peut retourner des informations obsolètes
        # cached_result = self._check_cache(query)
        # if cached_result and not cached_result.get('error'):
        #     cached_result['processing_time'] = time.time() - start_time
        #     return cached_result
        
        # SEARCH TAPE 1: CORRECTION AUTO (seulement si activée - gagne 20-40s)
        if self.config.ENABLE_AUTO_CORRECTION:
            corrected_query, corrections_applied = self._analyze_and_correct_prompt(query)
            if corrections_applied:
                logger.info(f" Correction automatique: '{query}'  '{corrected_query}'")
        else:
            corrected_query = query
            corrections_applied = False
        
        try:
            # Recherche RAG avec la requête corrigée
            rag_context = self.rag_system.search(corrected_query)
            
            # Génération de la réponse avec la requête CORRIGE
            response = self._generate_response(corrected_query, rag_context)
            
            # Ajouter les informations de correction à la réponse
            if corrections_applied:
                response['original_query'] = query
                response['corrected_query'] = corrected_query
                response['auto_corrections_applied'] = True
            else:
                response['auto_corrections_applied'] = False
            
            response['processing_time'] = time.time() - start_time
            response['cached'] = False  # Toujours False car cache désactivé
            
            # ⚠️ CACHE DÉSACTIVÉ : Ne plus sauvegarder dans le cache
            # self._save_to_cache(query, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur analyse requête: {e}")
            return {
                'error': str(e),
                'response': "Je n'ai pas pu comprendre votre requête ou trouver de données correspondantes. Veuillez la modifier ou la simplifier.",
                'code': '',
                'execution_result': None,
                'processing_time': time.time() - start_time
            }
    
    def _generate_response(self, query: str, rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """Génération avec Auto-Correction Pure IA (Self-Healing AI)"""
        
        #  MODE IA PURE: Bypass toutes les règles et laisser l'IA décider
        if self.config.PURE_AI_MODE:
            return self._generate_response_pure_ai(query, rag_context)
        
        # 🧠 Le modèle génère TOUJOURS le code frais
        # Le cache sert uniquement à corriger les erreurs sans rappeler l'API
        
        system_prompt = self._build_system_prompt(rag_context)
        original_prompt = f"REQUTE UTILISATEUR: {query}"
        
        max_retries = 2  # Auto-correction: 3 tentatives max (0, 1, 2) - FAST optimisé
        current_code = ""
        current_error = None
        syntax_error = None  # TOOL Pour stocker les erreurs de syntaxe
        query_start = time.time()  # FAST Timer pour timeout global

        for attempt in range(max_retries + 1):
            # FAST TIMEOUT GLOBAL: Abandonner si > MAX_QUERY_TIME
            if time.time() - query_start > self.config.MAX_QUERY_TIME:
                elapsed = int(time.time() - query_start)
                logger.warning(f"⏱️ Timeout global dépassé ({elapsed}s/{self.config.MAX_QUERY_TIME}s) - abandon")
                return {
                    'error': 'Timeout',
                    'response': f"⏱️ L'API NVIDIA est trop lente ({elapsed}s). Essayez avec une question plus simple ou réessayez dans quelques instants.",
                    'code': current_code,
                    'execution_result': None,
                    'suggestions': [
                        "Simplifiez votre question",
                        "Limitez la période d'analyse",
                        "Réessayez dans quelques instants"
                    ]
                }
            
            try:
                # Prompt adaptatif selon la tentative
                if attempt == 0:
                    current_prompt = original_prompt
                elif syntax_error:
                    # TOOL ERREUR DE SYNTAXE - Correction spécifique
                    current_prompt = f"""{original_prompt}

TOOL ERREUR DE SYNTAXE DTECTE - CORRECTION REQUISE

CODE AVEC ERREUR:
```python
{current_code}
```

ERREUR DE SYNTAXE:
{syntax_error}

 RGLES CRITIQUES POLARS:
1. JAMAIS utiliser df['colonne'] sur un LazyFrame  Utiliser pl.col('colonne')
2. TOUJOURS équilibrer les parenthèses () et crochets []
3. .group_by() PAS .groupby()
4. .sort('col', descending=True) PAS .sort('col').desc()
5. Terminer par .collect().to_dicts()

SEARCH VRIFIE:
- Chaque ( a son )
- Chaque [ a son ]
- Pas de virgule manquante dans les listes
- Pas de syntaxe pandas sur LazyFrame

Génère un code SYNTAXIQUEMENT CORRECT."""
                    syntax_error = None  # Reset après utilisation
                elif attempt == 1:
                    #  AUTO-CORRECTION PURE IA - L'IA analyse et corrige elle-même
                    current_prompt = f"""{original_prompt}

 AUTO-APPRENTISSAGE IA ACTIV

CODE QUI A CHOU:
```python
{current_code}
```

ERREUR COMPLTE:
{current_error}

SEARCH ANALYSE INTELLIGENTE REQUISE:
Tu es une IA avancée capable d'apprendre de tes erreurs.
Analyse cette erreur et comprends POURQUOI le code a échoué.

Questions à te poser :
1. Quelle est la VRAIE cause de l'erreur ?
2. Le problème vient-il du filtrage, de la syntaxe, ou des noms de colonnes ?
3. Les valeurs que j'ai utilisées existent-elles dans [Ex: ...] ?
4. Ma logique correspond-elle à ce que l'utilisateur demande ?

INFO STRATGIE DE CORRECTION:
- Regarde les EXEMPLES de valeurs dans le schéma
- Utilise .str.contains() pour les recherches textuelles
- Vérifie CHAQUE nom de colonne
- Simplifie la logique si nécessaire
- Génère un code DIFFRENT qui résout le problème

Génère un NOUVEAU code basé sur ton analyse intelligente."""
                else:
                    # TARGET Dernière tentative : Approche minimaliste IA pure
                    current_prompt = f"""{original_prompt}

TARGET TENTATIVE {attempt + 1}/{max_retries + 1} - APPROCHE MINIMALISTE

Tu as échoué {attempt} fois. Il est temps de RINVENTER ton approche.

CODE PRCDENT:
```python
{current_code}
```

ERREUR:
{current_error}

 NOUVELLE STRATGIE INTELLIGENTE:
1. OUBLIE tout ce qui a été tenté
2. RELIS la question utilisateur avec un regard neuf
3. Regarde les EXEMPLES de valeurs dans le schéma
4. Construis la solution la PLUS SIMPLE possible
5. Utilise uniquement : filter(), select(), group_by(), agg()
6. Chaque ligne doit être VIDENTE et CLAIRE
7. VRIFIE que toutes les parenthèses sont équilibrées

Génère un code COMPLTEMENT DIFFRENT et ULTRA-SIMPLE."""

                # Appel IA
                response = self._call_ai(system_prompt, current_prompt)
                current_code = self._extract_code_raw(response)  # Extraction sans validation
                
                if not current_code:
                    if attempt < max_retries:
                        current_error = "Aucun code généré"
                        continue
                    return {'error': 'Echec génération code', 'response': 'Impossible de générer le code.', 'code': ''}

                # TOOL VALIDATION SYNTAXE AVANT EXCUTION
                syntax_valid, syntax_error = self._validate_syntax(current_code)
                if not syntax_valid:
                    logger.warning(f" Erreur syntaxe détectée (tentative {attempt+1}): {syntax_error}")
                    if attempt < max_retries:
                        continue  # Retry avec le prompt de correction syntaxe
                    # Dernière tentative - on essaie quand même d'exécuter
                
                # TOOL CORRECTIONS AUTOMATIQUES SIMPLES
                current_code = self._apply_polars_fixes(current_code)

                # Exécution sécurisée
                execution_result = self._execute_code(current_code)
                
                # Affichage pour validation des modalités (mode debug)
                if self.config.DEBUG_EXECUTION and execution_result:
                    logger.info(f"Résultat exécution: {execution_result}")
                
                # Vérification succès (si résultat n'est pas une chane commençant par "Erreur")
                is_error = isinstance(execution_result, str) and execution_result.startswith("Erreur")
                
                # SEARCH DTECTION RSULTATS VIDES pour auto-correction
                is_empty = False
                if not is_error:
                    if isinstance(execution_result, list) and len(execution_result) == 0:
                        is_empty = True
                        logger.warning(f" Résultat vide détecté (tentative {attempt+1}/{max_retries+1})")
                
                if not is_error and not is_empty:
                    #  SUCCS - Apprentissage + Génération d'insight
                    
                    #  APPRENTISSAGE du succès
                    if self.learning_system and execution_result:
                        try:
                            self.learning_system.learn_from_success(query, current_code, execution_result)
                            logger.info(f" Pattern appris: {query[:50]}...")
                            # 🧠 Si auto-corrigé, mémoriser l'erreur + le code corrigé complet
                            if attempt > 0 and current_error:
                                error_type = "AutoCorrected"
                                if "SyntaxError" in str(current_error):
                                    error_type = "SyntaxError"
                                elif "AttributeError" in str(current_error):
                                    error_type = "AttributeError"
                                elif "agg()" in str(current_error):
                                    error_type = "InvalidOperation_agg"
                                elif "TypeError" in str(current_error):
                                    error_type = "TypeError"
                                elif "not supported" in str(current_error):
                                    error_type = "InvalidOperation"
                                self.learning_system.learn_from_error(
                                    error_message=str(current_error)[:150],
                                    error_type=error_type,
                                    failed_code=current_code[:500],  # Sauvegarder le vrai code fautif
                                    correction=f"Corrigé en tentative {attempt+1}",
                                    corrected_code=current_code  # Le code complet qui a marché
                                )
                                logger.info(f"🧠 Erreur→Correction mémorisée (code complet sauvegardé)")
                        except Exception as e:
                            logger.warning(f" Erreur apprentissage: {e}")
                    
                    explanation = self._generate_insight(query, execution_result, current_code)
                    
                    return {
                        'response': explanation,
                        'code': current_code,
                        'execution_result': execution_result,
                        'error': None,
                        'auto_corrected': attempt > 0,
                        'correction_attempt': attempt if attempt > 0 else None,
                        'rag_matches': len(rag_context['exact_matches']) + len(rag_context['fuzzy_matches'])
                    }
                else:
                    # C'est une erreur ou résultat vide, on la capture pour le tour suivant
                    if is_empty:
                        current_error = f"Résultat vide: Le code s'exécute mais ne retourne aucun enregistrement (0 résultats). Probable filtre trop strict.\n\n CAUSES FRQUENTES:\n1. galité stricte sur BUREAU/DIRECTION au lieu de .str.contains()\n2. Format de date incorrect\n3. Valeur exacte qui n'existe pas dans les données\n\nINFO CORRECTIONS  TENTER:\n- Utiliser .str.to_lowercase().str.contains('mot') pour les lieux\n- Vérifier le format des valeurs dans [Ex: ...]\n- largir les critères de filtrage\n\nCode actuel qui retourne 0 résultats:\n{current_code}"
                        logger.info(f"RELOAD Auto-correction pour résultat vide...")
                    else:
                        current_error = execution_result
                        logger.info(f"RELOAD Auto-correction pour erreur d'exécution...")
                    
                    # 🧠 CORRECTION VIA CACHE: Chercher si cette erreur a déjà été corrigée
                    if self.learning_system and not is_empty:
                        cached_fix = self.learning_system.find_correction_for_error(
                            str(current_error)[:200], current_code[:300]
                        )
                        if cached_fix:
                            logger.info(f"🧠 Correction trouvée dans le cache d'erreurs, application directe...")
                            fix_result = self._execute_code(cached_fix)
                            fix_is_error = isinstance(fix_result, str) and fix_result.startswith("Erreur")
                            fix_is_empty = isinstance(fix_result, list) and len(fix_result) == 0
                            
                            if not fix_is_error and not fix_is_empty:
                                logger.info(f"✅ Correction du cache appliquée avec succès!")
                                self.learning_system.learn_from_success(query, cached_fix, fix_result)
                                explanation = self._generate_insight(query, fix_result, cached_fix)
                                return {
                                    'response': explanation,
                                    'code': cached_fix,
                                    'execution_result': fix_result,
                                    'error': None,
                                    'auto_corrected': True,
                                    'cached_correction': True,
                                    'rag_matches': len(rag_context['exact_matches']) + len(rag_context['fuzzy_matches'])
                                }
                            else:
                                logger.warning(f"⚠️ Correction du cache n'a pas fonctionné, poursuite auto-correction IA")
            
            except Exception as e:
                # Gestion des erreurs réseau/timeout
                error_msg = str(e)
                logger.error(f"Erreur tentative {attempt + 1}/{max_retries + 1}: {e}")
                
                # Si dernière tentative ET erreur réseau, abandonner
                if attempt >= max_retries and ("connection" in error_msg.lower() or "timed out" in error_msg.lower() or "timeout" in error_msg.lower()):
                    logger.error(f"🚫 Échec final - Problème de connexion API (tentative {attempt + 1}/{max_retries + 1})")
                    return {
                        'error': "Connexion API impossible", 
                        'response': f"🚫 L'API NVIDIA ne répond pas après {attempt + 1} tentatives.\n\n✅ Solutions:\n1. Vérifiez votre connexion internet\n2. Réessayez dans quelques instants\n3. L'API NVIDIA peut être surchargée", 
                        'code': current_code,
                        'execution_result': None,
                        'retry_count': attempt + 1
                    }
                
                # Sinon, on continue avec retry
                current_error = error_msg
        
        # Si on arrive ici, c'est l'échec final après retries
        return {
            'error': current_error, 
            'response': "Je n'ai pas pu comprendre votre requête ou trouver de données correspondantes. Veuillez la modifier ou la simplifier.",
            'code': current_code,
            'execution_result': None
        }
    
    def _generate_response_pure_ai(self, query: str, rag_context: Dict[str, Any]) -> Dict[str, Any]:
        """ MODE IA PURE - 100% Intelligence Artificielle sans contraintes"""
        try:
            logger.info(" MODE IA PURE ACTIV - L'IA prend toutes les décisions")
            
            # Prompt métacognitif pour l'IA
            meta_prompt = f""" MODE INTELLIGENCE ARTIFICIELLE PURE ACTIV

Tu es une IA avancée avec capacité d'auto-analyse et de métacognition. Tu as accès à une base de données fiscales sénégalaises et tu dois répondre à cette requête avec une intelligence pure, sans contraintes de règles prédéfinies.

REQUTE UTILISATEUR: {query}

CONTEXTE DISPONIBLE:
- Base de données: LazyFrame Polars avec 11M+ d'enregistrements fiscaux
- Colonnes disponibles: {', '.join(list(self.data_summary['columns'].keys())[:20])}...
- Période: 2025-2026
- RAG Context: {len(rag_context.get('exact_matches', []))} correspondances exactes

 MTACOGNITION REQUISE:
1. ANALYSE la requête et identifie l'intention réelle de l'utilisateur
2. DCIDE de l'approche optimale (statistique, analytique, exploratoire)
3. CONOIS ton propre code Python/Polars pour répondre
4. VALUE la pertinence de ta réponse et ajuste si nécessaire
5. GNRE une synthèse décisionnelle riche

FAST LIBERTS ACCORDES:
- Tu peux interpréter librement la requête
- Tu peux choisir tes propres métriques et KPIs
- Tu peux décider du niveau de détail approprié
- Tu peux créer des analyses innovantes
- Tu peux proposer des insights non demandés mais pertinents

TARGET OBJECTIF: Fournir la réponse la plus intelligente et utile possible

Commence par analyser la requête, puis génère le code Python approprié, puis fournis une analyse complète."""

            # Appel IA sans contraintes
            response = self._call_ai(
                "Tu es une IA pure avec liberté totale d'analyse et de décision.", 
                meta_prompt
            )
            
            # Extraction intelligente du code
            code = self._extract_code_intelligent(response)
            
            if code:
                # Exécution avec confiance IA
                execution_result = self._execute_code_with_ai_confidence(code, query)
                
                if execution_result and not isinstance(execution_result, str):
                    # Génération d'insights 100% IA
                    insights = self._generate_insights_pure_ai(query, execution_result, response)
                    
                    return {
                        'response': insights,
                        'code': code,
                        'execution_result': execution_result,
                        'error': None,
                        'ai_mode': 'pure',
                        'ai_reasoning': response,
                        'confidence': self._evaluate_ai_confidence(response, execution_result)
                    }
            
            # Si échec, l'IA génère sa propre réponse fallback
            fallback_response = self._ai_generate_fallback(query, response)
            
            return {
                'response': fallback_response,
                'code': code or '',
                'execution_result': None,
                'error': 'Code generation failed',
                'ai_mode': 'pure_fallback',
                'ai_reasoning': response
            }
            
        except Exception as e:
            logger.error(f"Erreur mode IA pure: {e}")
            # Même en mode IA pure, on a un fallback minimal
            return {
                'error': str(e),
                'response': f"L'IA pure a rencontré une difficulté technique: {e}",
                'ai_mode': 'pure_error'
            }
    
    def _extract_code_intelligent(self, ai_response: str) -> str:
        """ Extraction de code avec intelligence contextuelle"""
        # L'IA peut décider de son propre format de code
        patterns = [
            r"```python\n(.*?)\n```",
            r"```\n(.*?)\n```",
            r"CODE:\n(.*?)(?=\n[A-Z]|\n$)",
            r"SOLUTION:\n(.*?)(?=\n[A-Z]|\n$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ai_response, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                if 'data' in code and ('pl.' in code or 'polars' in code.lower()):
                    return code
        
        # Extraction intelligente ligne par ligne
        lines = ai_response.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            stripped = line.strip()
            if any(keyword in stripped for keyword in ['data.', 'pl.', 'polars', 'result =']):
                in_code_block = True
                code_lines.append(stripped)
            elif in_code_block and stripped and not stripped[0].isupper():
                code_lines.append(stripped)
            elif in_code_block and stripped.startswith(('ANALYSE', 'CONCLUSION', 'RSULTAT')):
                break
        
        return '\n'.join(code_lines) if code_lines else ''
    
    def _execute_code_with_ai_confidence(self, code: str, query: str) -> Any:
        """TARGET Exécution avec évaluation de confiance IA"""
        try:
            # L'IA évalue elle-même la qualité de son code avant exécution
            confidence_prompt = f"""value la qualité de ce code Python/Polars sur une échelle de 0 à 1:

CODE:
{code}

REQUTE: {query}

Réponds UNIQUEMENT avec un nombre entre 0 et 1 (ex: 0.85)"""
            
            confidence_str = self._call_ai("Expert évaluateur de code.", confidence_prompt)
            try:
                confidence = float(confidence_str.strip())
            except:
                confidence = 0.5  # Confiance neutre par défaut
            
            # Si confiance suffisante, exécution
            if confidence >= self.config.AI_CONFIDENCE_THRESHOLD:
                logger.info(f"TARGET IA confiante ({confidence:.2f}) - Exécution du code")
                return self._execute_code(code)
            else:
                logger.warning(f" IA peu confiante ({confidence:.2f}) - Code rejeté")
                return f"IA_CONFIDENCE_TOO_LOW: {confidence:.2f} < {self.config.AI_CONFIDENCE_THRESHOLD}"
                
        except Exception as e:
            return f"Erreur évaluation confiance IA: {e}"
    
    def _generate_insights_pure_ai(self, query: str, execution_result: Any, ai_reasoning: str) -> Dict[str, Any]:
        """ Génération d'insights 100% IA avec raisonnement métacognitif"""
        try:
            insight_prompt = f"""GNRATION D'INSIGHTS MTACOGNITIFS

REQUTE ORIGINALE: {query}
RAISONNEMENT IA INITIAL: {ai_reasoning[:1000]}...
RSULTATS OBTENUS: {len(execution_result) if isinstance(execution_result, list) else 1} enregistrements

 MISSION MTACOGNITIVE:
Tu viens d'analyser des données et d'obtenir des résultats. Maintenant, avec un recul métacognitif:

1. INTERPRTE les résultats dans le contexte fiscal sénégalais
2. IDENTIFIE les patterns et insights non évidents
3. GNRE des recommandations stratégiques
4. VALUE la pertinence de ta propre analyse
5. PROPOSE des angles d'analyse complémentaires

FORMAT DE RPONSE:
{{
    "analyse_narrative": "Description intelligente des résultats...",
    "insights_cles": ["Insight 1", "Insight 2", "Insight 3"],
    "recommandations": ["Action 1", "Action 2"],
    "meta_evaluation": "valuation de ma propre analyse...",
    "pistes_complementaires": ["Angle 1", "Angle 2"]
}}

Génère une analyse riche et métacognitive en JSON:"""

            insights_json = self._call_ai(
                "IA métacognitive avec capacité d'auto-analyse et de réflexion stratégique.",
                insight_prompt
            )
            
            try:
                return json.loads(insights_json)
            except:
                # Si le JSON échoue, retourner analyse textuelle
                return {
                    'analyse_narrative': insights_json,
                    'ai_mode': 'pure_text_fallback'
                }
                
        except Exception as e:
            logger.error(f"Erreur insights IA pure: {e}")
            return {
                'analyse_narrative': f"Résultats obtenus pour: {query}",
                'ai_mode': 'pure_error'
            }
    
    def _evaluate_ai_confidence(self, ai_response: str, execution_result: Any) -> float:
        """DATA valuation de la confiance de l'IA dans sa propre réponse"""
        try:
            confidence_factors = 0.0
            total_factors = 5
            
            # Facteur 1: Longueur et détail de la réponse
            if len(ai_response) > 200:
                confidence_factors += 1
            
            # Facteur 2: Présence de code structuré
            if 'data.' in ai_response and '.collect()' in ai_response:
                confidence_factors += 1
            
            # Facteur 3: Résultats obtenus
            if execution_result and not isinstance(execution_result, str):
                confidence_factors += 1
            
            # Facteur 4: Présence d'analyse
            if any(word in ai_response.lower() for word in ['analyse', 'résultat', 'conclusion']):
                confidence_factors += 1
                
            # Facteur 5: Pas d'erreurs apparentes
            if 'erreur' not in ai_response.lower() and 'error' not in ai_response.lower():
                confidence_factors += 1
            
            return confidence_factors / total_factors
            
        except:
            return 0.5  # Confiance neutre par défaut
    
    def _ai_generate_fallback(self, query: str, failed_response: str) -> str:
        """ L'IA génère sa propre stratégie de fallback"""
        try:
            fallback_prompt = f"""L'analyse précédente a échoué. En tant qu'IA métacognitive, génère une réponse alternative intelligente.

REQUTE: {query}
TENTATIVE CHOUE: {failed_response[:500]}...

 STRATGIE DE RCUPRATION:
1. Réinterprète la requête avec un angle différent
2. Propose une analyse conceptuelle même sans données
3. Fournis des insights généraux sur le sujet
4. Suggère des reformulations de la requête

Génère une réponse utile malgré l'échec technique:"""
            
            return self._call_ai(
                "IA résiliente capable de s'adapter aux échecs.",
                fallback_prompt
            )
        except:
            return f"L'IA a tenté d'analyser '{query}' mais a rencontré des difficultés techniques. Veuillez reformuler votre demande."
    
    def _validate_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """TOOL Valide la syntaxe Python du code généré"""
        if not code:
            return False, "Code vide"
        
        try:
            compile(code, '<generated>', 'exec')
            return True, None
        except SyntaxError as e:
            error_msg = f"Ligne {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\nCode problématique: {e.text.strip()}"
            return False, error_msg
    
    def _apply_polars_fixes(self, code: str) -> str:
        """TOOL Applique des corrections automatiques pour Polars"""
        # TOOL CORRECTION CRITIQUE: Suppression des lectures de fichiers interdites
        code = re.sub(r'pl\.read_csv\([^)]+\)', 'data', code)
        code = re.sub(r'pd\.read_csv\([^)]+\)', 'data', code)
        
        # TOOL CORRECTION: Remplacement des ellipsis par du code valide
        code = re.sub(r'pl\.DataFrame\(\.\.\.\)', 'data', code)
        code = re.sub(r'pl\.DataFrame\(\[\.\.\.\]\)', 'data', code)
        
        # TOOL CORRECTION: Créations manuelles de DataFrame vers utilisation de data
        code = re.sub(r'pl\.DataFrame\(\[.*?\]\)', 'data', code, flags=re.DOTALL)
        
        # .groupby()  .group_by()
        code = re.sub(r'\.groupby\s*\(', '.group_by(', code)
        
        # TOOL CORRECTION CRITIQUE: .sort(reverse=True)  .sort(descending=True)
        code = re.sub(r'\.sort\s*\(\s*reverse\s*=\s*True\s*\)', '.sort(descending=True)', code)
        code = re.sub(r'\.sort\s*\(\s*reverse\s*=\s*False\s*\)', '.sort(descending=False)', code)
        
        # TOOL CORRECTION: .sort().desc()  .sort(descending=True)
        code = re.sub(r'\.sort\s*\(([^)]+)\)\s*\.desc\s*\(\s*\)', r'.sort(\1, descending=True)', code)
        
        # TOOL CORRECTION: .desc() seul  descending=True dans sort
        code = re.sub(r'\.sort\s*\(\s*\)\s*\.desc\s*\(\s*\)', '.sort(descending=True)', code)
        
        # TOOL CORRECTION: pl.col('col').desc() dans sort  doit être pl.col('col')
        # Problème: .sort(pl.col('MONTANT').desc())  .sort(pl.col('MONTANT'), descending=True)
        code = re.sub(r'\.sort\s*\(\s*(pl\.col\([^)]+\))\.desc\s*\(\s*\)\s*\)', r'.sort(\1, descending=True)', code)
        
        # TOOL CORRECTION CRITIQUE: Retirer descending des pl.col() calls
        # Problème: pl.col('X')(descending=True) → TypeError "unexpected keyword argument"
        # Solution: Déplacer descending vers .sort()
        # Pattern 1: pl.col('X')(descending=True) seul
        code = re.sub(r'pl\.col\(([^)]+)\)\s*\(\s*descending\s*=\s*True\s*\)', r'pl.col(\1)', code)
        code = re.sub(r'pl\.col\(([^)]+)\)\s*\(\s*descending\s*=\s*False\s*\)', r'pl.col(\1)', code)
        # Pattern 2: Dans un .sort() - .sort(pl.col('X')(descending=True))
        code = re.sub(
            r'\.sort\s*\(\s*pl\.col\(([^)]+)\)\s*\(\s*descending\s*=\s*True\s*\)\s*\)',
            r'.sort(pl.col(\1), descending=True)',
            code
        )
        code = re.sub(
            r'\.sort\s*\(\s*pl\.col\(([^)]+)\)\s*\(\s*descending\s*=\s*False\s*\)\s*\)',
            r'.sort(pl.col(\1), descending=False)',
            code
        )
        
        # Correction des crochets pandas sur LazyFrame: data['col']  pl.col('col')
        # Pattern: data['QUELQUE_CHOSE'] ou data["QUELQUE_CHOSE"]
        code = re.sub(r"data\[(['\"])([^'\"]+)\1\]", r"pl.col('\2')", code)
        
        # TOOL CORRECTION CRITIQUE: Opérateurs logiques Python vs Polars
        # Problème: pl.col('A') and pl.col('B')  Erreur "truth value ambiguous"
        # Solution: pl.col('A') & pl.col('B')
        code = re.sub(r'\)\s+and\s+\(', ') & (', code)
        code = re.sub(r'\)\s+or\s+\(', ') | (', code)
        
        # TOOL CORRECTION CRITIQUE: Filtre OR entre bool et date
        # Problème: .is_null()) | (pl.col('DATE')) > date(...)  Erreur "| not allowed on bool and date"
        # Solution: .is_null()) | (pl.col('DATE') > date(...))
        # Pattern: .is_null()) | (pl.col('XXX'))] >  DOIT ÊTRE .is_null()) | (pl.col('XXX') >
        code = re.sub(
            r'\(pl\.col\([\'"]([^\'"]+)[\'"]\)\.is_null\(\)\)\s*\|\s*\(pl\.col\([\'"]([^\'"]+)[\'"]\)\)\]\s*([><=!]+)',
            r'(pl.col("\1").is_null()) | (pl.col("\2") \3',
            code
        )
        # Pattern alternatif: .is_null()) | (pl.col('XXX'))) >
        code = re.sub(
            r'\(pl\.col\([\'"]([^\'"]+)[\'"]\)\.is_null\(\)\)\s*\|\s*\(pl\.col\([\'"]([^\'"]+)[\'"]\)\)\)\s*([><=!]+)',
            r'(pl.col("\1").is_null()) | (pl.col("\2") \3',
            code
        )
        
        # TOOL CORRECTION CRITIQUE: Méthodes de date manquantes ()
        # Problème: pl.col('DATE').dt.year >= 2025  TypeError car dt.year est une méthode
        # Solution: pl.col('DATE').dt.year() >= 2025
        code = re.sub(r'\.dt\.year\s*(>=|<=|==|!=|>|<)', r'.dt.year() \1', code)
        code = re.sub(r'\.dt\.month\s*(>=|<=|==|!=|>|<)', r'.dt.month() \1', code)
        code = re.sub(r'\.dt\.day\s*(>=|<=|==|!=|>|<)', r'.dt.day() \1', code)
        
        # TOOL CORRECTION AUTOMATIQUE: Plages temporelles incorrectes
        # Problème: .dt.year() == 2022) & (.dt.year() <= 2025)  ne donne que 2022
        # Solution: .dt.year() >= 2022) & (.dt.year() <= 2025)  donne 2022-2025
        # Pattern: (year() == ANNE_DEBUT) & (year() <= ANNE_FIN)
        plage_pattern = r'\(pl\.col\([^)]+\)\.dt\.year\(\)\s*==\s*(\d{4})\)\s*&\s*\(pl\.col\([^)]+\)\.dt\.year\(\)\s*<=\s*(\d{4})\)'
        
        def fix_temporal_range(match):
            annee_debut = int(match.group(1))
            annee_fin = int(match.group(2))
            if annee_fin > annee_debut:  # C'est bien une plage
                # Remplacer == par >= pour le début
                fixed = match.group(0).replace(f'== {annee_debut}', f'>= {annee_debut}')
                logger.info(f"TOOL Auto-correction plage temporelle: == {annee_debut}  >= {annee_debut}")
                return fixed
            return match.group(0)  # Pas de changement si pas une plage logique
        
        code = re.sub(plage_pattern, fix_temporal_range, code)
        
        # TOOL CORRECTION INTELLIGENTE: Vérifier si les valeurs filtrées existent dans la base
        code = self._fix_filter_values(code)
        
        return code
    
    def _fix_filter_values(self, code: str) -> str:
        """SEARCH Corrige les filtres pour utiliser les VRAIES valeurs de la base"""
        try:
            # Extraire les valeurs utilisées dans les filtres du code
            # Pattern: pl.col('COLONNE') == 'valeur' ou .contains('valeur')
            
            # Pour chaque colonne catégorielle, vérifier si les valeurs filtrées existent
            for col_name, col_info in self.data_summary['columns'].items():
                if 'samples' not in col_info or not col_info['samples']:
                    continue
                    
                samples = col_info['samples']
                
                # Chercher les filtres sur cette colonne avec str.contains()
                # Ex: pl.col("LIBELLE").str.to_lowercase().str.contains("tva")
                contains_pattern = rf"pl\.col\(['\"]({col_name})['\"].*?\.contains\(['\"]([^'\"]+)['\"]\)"
                
                for match in re.finditer(contains_pattern, code, re.IGNORECASE):
                    search_term = match.group(2).lower()
                    
                    # Chercher dans TOUTES les colonnes si cette valeur existe exactement
                    for other_col, other_info in self.data_summary['columns'].items():
                        if 'samples' not in other_info:
                            continue
                        for sample in other_info['samples']:
                            if sample and search_term in str(sample).lower():
                                # Trouvé! Remplacer par un filtre exact sur la bonne colonne
                                if other_col != col_name:
                                    old_filter = match.group(0)
                                    new_filter = f"pl.col('{other_col}') == '{sample}'"
                                    code = code.replace(old_filter, new_filter)
                                    logger.info(f"TOOL Auto-correction filtre: {col_name}.contains('{search_term}')  {other_col} == '{sample}'")
                                break
            
            return code
        except Exception as e:
            logger.warning(f" Erreur correction filtres: {e}")
            return code
    
    def _extract_code_raw(self, response: str) -> str:
        """Extraction du code Python SANS validation (pour permettre retry)"""
        patterns = [
            r"```python\n(.*?)\n```",
            r"```\n(.*?)\n```",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Si pas de blocs de code, prendre les lignes qui ressemblent à du code
        lines = response.split('\n')
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if (stripped and 
                not stripped.startswith('#') and 
                not stripped.startswith('//') and
                ('data' in stripped or 'pl.' in stripped or '=' in stripped or 'print(' in stripped)):
                code_lines.append(stripped)
        
        return '\n'.join(code_lines) if code_lines else ''

    def _build_system_prompt(self, rag_context: Dict[str, Any]) -> str:
        """Prompt système minimaliste - Intelligence Pure & Contextuelle"""
        
        # Construction du schéma avec exemples
        schema_lines = []
        for col, info in self.data_summary['columns'].items():
            base_info = f"- {col} ({info['dtype']})"
            if 'samples' in info and info['samples']:
                # FAST OPTIMIS: 15 exemples max (réduit prompt de ~8K chars)
                samples_str = ", ".join([f"'{s}'" for s in info['samples'][:15]])
                base_info += f" [Ex: {samples_str}]"
            schema_lines.append(base_info)
            
        # Prioriser l'affichage: Catégories + Dates + Colonnes 'MONTANT'
        important_cols = self.data_summary['categorical_columns'] + self.data_summary['date_columns']
        numeric_important = [c for c in self.data_summary['numeric_columns'] if 'MONTANT' in c.upper()]
        
        visible_schema = [l for l in schema_lines if any(c in l for c in important_cols + numeric_important)]
        # FAST OPTIMIS: 20 lignes max pour réduire le prompt
        schema_display = "\n".join(visible_schema[:20])
        
        # Contexte RAG simplifié et sécurisé
        rag_info = ""
        context_items = []
        
        if rag_context.get('exact_matches'):
            for m in rag_context['exact_matches'][:5]:
                if m.get('type') == 'value':
                    context_items.append(f"Valeur '{m.get('original')}' (ds '{m.get('column')}')")
                elif m.get('type') == 'column':
                    context_items.append(f"Colonne '{m.get('name')}'")
        
        if ragged_items := ", ".join(context_items):
            rag_info = f"Info Contexte (Mémoire): {ragged_items}"

        #  Apprentissage automatique des erreurs
        error_prevention = ""
        if hasattr(self, 'learning_system') and self.learning_system:
            error_prevention = self.learning_system.get_error_prevention_prompt()
            if error_prevention:
                error_prevention = f"\n\n{error_prevention}\n"

        from datetime import date
        today = date.today()
        
        return f"""Tu es un expert en analyse de données fiscales et douanières du Sénégal. Tu génères du code Python Polars pour répondre aux questions des utilisateurs.

DATE DU JOUR: {today} | Monnaie: FCFA

⚠️ GESTION DES REQUÊTES TEMPORELLES - DISTINGUER "DU JOUR" vs "JUSQU'À AUJOURD'HUI":

1. RECETTES **DU JOUR** / **AUJOURD'HUI** / **CE JOUR** / **SEULEMENT AUJOURD'HUI**:
   → L'utilisateur veut UNIQUEMENT les opérations effectuées aujourd'hui
   ✅ CORRECT: .filter(pl.col('DATE_RECOUVREMENT') == pl.lit(TODAY))
   ❌ ERREUR: .filter(pl.col('DATE_RECOUVREMENT') <= pl.lit(TODAY))  → Donne TOUT l'historique, pas seulement aujourd'hui !
   
   Exemples de requêtes:
   - "Recettes de la douane aujourd'hui"
   - "Montant recouvré DGD du jour"
   - "Recettes du 27 avril 2026"
   - "Combien a été recouvré aujourd'hui à la douane"
   → Utiliser `== TODAY`

2. TOTAL CUMULÉ / TOP CONTRIBUTEURS / **JUSQU'À AUJOURD'HUI**:
   → L'utilisateur veut le CUMULATIF depuis le début jusqu'à maintenant
   ✅ CORRECT: .filter(pl.col('DATE_RECOUVREMENT') <= pl.lit(TODAY))
   ❌ ERREUR: .filter(pl.col('DATE_RECOUVREMENT') == pl.lit(TODAY))  → Ne donne que les opérations d'aujourd'hui !
   ❌ INTERDIT: .filter(DATE_RECOUVREMENT.dt.year() == 2026)  → Ne prend que 2026, exclut 2025 !
   ❌ INTERDIT: .filter(DATE_RECOUVREMENT.dt.month() == 4)  → Ne prend qu'avril, exclut jan-mars !
   
   Exemples de requêtes:
   - "Top 10 des contribuables par montant recouvré"
   - "Quels sont les plus gros contribuables"
   - "Montant total recouvré jusqu'à aujourd'hui"
   - "Performance globale"
   → Utiliser `<= TODAY`

3. NE filtrer par année/mois spécifique QUE si l'utilisateur demande explicitement :
   - "En avril 2026" → .filter(dt.year() == 2026 & dt.month() == 4)
   - "En 2026" → .filter(dt.year() == 2026)
   - Par défaut (Top 10, Total, etc.) → .filter(DATE <= TODAY) SANS filtre année/mois

📝 EXEMPLES CONCRETS - BIEN DISTINGUER LES CAS:

Requête: "De combien est la recette de la douane aujourd'hui"
✅ CORRECT:
result = {{
    "principal": data.filter(pl.col('SOURCE') == 'DGD')
                       .filter(pl.col('DATE_RECOUVREMENT') == pl.lit(TODAY))  # == pour "aujourd'hui"
                       .group_by('SOURCE')
                       .agg([pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'), pl.len().alias('NB_LIGNES')])
                       .collect().to_dicts()
}}

Requête: "Top 10 des contribuables DGD par montant recouvré"
✅ CORRECT:
result = {{
    "principal": data.filter(pl.col('SOURCE') == 'DGD')
                       .filter(pl.col('DATE_RECOUVREMENT') <= pl.lit(TODAY))  # <= pour cumul total
                       .group_by('ID_CONTRIBUABLE')
                       .agg([pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'), 
                             pl.col('BUREAU').first().alias('BUREAU'),
                             pl.len().alias('NB_LIGNES')])
                       .sort(pl.col('TOTAL_RECOUVRE'), descending=True)
                       .limit(10)
                       .collect().to_dicts()
}}
   
3. Les données contiennent 2025-2026. Pour "Top 10 contribuables", inclure TOUTES les périodes passées :
   - 2025 entier (janvier à décembre)
   - 2026 jusqu'à aujourd'hui (janvier à avril 27)
   
4. NE filtrer par année/mois spécifique QUE si l'utilisateur demande explicitement :
   - "En avril 2026" → .filter(dt.year() == 2026 & dt.month() == 4)
   - "En 2026" → .filter(dt.year() == 2026)
   - "Aujourd'hui" / "Top 10" / "Total" → .filter(DATE <= TODAY) SANS filtre année/mois

CONTEXTE MÉTIER:
Les données proviennent de deux régies financières sénégalaises :
- DGD (Direction Générale des Douanes) : gère les "Bureau ..." (Bureau kedougou, Bureau dakar port nord, etc.). SOURCE='DGD'
- DGID (Direction Générale des Impôts et Domaines) : gère les "Csf ..." (centres fiscaux), "Centre ...", "Direction des grandes entreprises", "Direction moyennes entreprises". SOURCE='DGID'
Le nom de la structure dans BUREAU détermine la SOURCE. Exemple: "Csf de kedougou" = DGID, "Bureau kedougou" = DGD.

SCHMA DES DONNES:
{schema_display}

{rag_info}
{error_prevention}
ENVIRONNEMENT:
- `data` : LazyFrame Polars pré-chargé (2025-2026), utiliser tel quel
- `TODAY` : date du jour (type Python date) | `pl` : module polars importé
- `timedelta` : déjà importé depuis datetime
- Ne PAS importer de fichiers, ne PAS créer de DataFrame manuellement

CONTRAINTES POLARS:
- Pipeline: data.filter().group_by().agg().sort().collect().to_dicts()
- .agg() nécessite .group_by() avant (jamais .filter().agg() directement)
- Méthodes: .group_by() (pas .groupby()), .sort(descending=True) (pas reverse=True)
- ⚠️ CRITIQUE: descending est un paramètre de .sort(), PAS de pl.col()
  ❌ INTERDIT: .sort(pl.col('MONTANT')(descending=True))  → TypeError
  ❌ INTERDIT: pl.col('MONTANT', descending=True)  → TypeError
  ✅ CORRECT: .sort(pl.col('MONTANT'), descending=True)  → OK
  ✅ CORRECT: .sort('MONTANT', descending=True)  → OK
- Dates: .dt.year() .dt.month() avec parenthèses
- Négation: ~pl.col('X').str.contains('y') OK, mais JAMAIS ~pl.col('X') == 'Y' → utiliser pl.col('X') != 'Y'
- Inclure pl.len().alias('NB_LIGNES') dans les agrégations
- Faire les calculs dans Polars (.with_columns()) pas en Python après .collect()

⚠️ GESTION DES DATES - RÈGLES CRITIQUES:
1. Les colonnes DATE_DECLARATION, DATE_RECOUVREMENT sont de type DATE (pas string)
2. JAMAIS utiliser .str.contains() sur une colonne DATE → ERREUR "expected String type, got: date"
3. Pour filtrer par année:
   ❌ INTERDIT: pl.col('DATE_DECLARATION').str.contains('2026')
   ✅ CORRECT: pl.col('DATE_DECLARATION').dt.year() == 2026
4. Pour filtrer par mois:
   ❌ INTERDIT: pl.col('DATE_RECOUVREMENT').str.contains('04')
   ✅ CORRECT: pl.col('DATE_RECOUVREMENT').dt.month() == 4
5. Pour "aujourd'hui":
   ✅ CORRECT: pl.col('DATE_RECOUVREMENT') == pl.lit(TODAY)
6. Pour extraire année/mois dans group_by:
   ✅ CORRECT: .with_columns([pl.col('DATE_DECLARATION').dt.year().alias('ANNEE'), pl.col('DATE_DECLARATION').dt.month().alias('MOIS')]).group_by(['ANNEE', 'MOIS'])
7. Comparer avec date littérale:
   ✅ CORRECT: pl.col('DATE_DECLARATION') >= pl.lit(date(2026, 1, 1))

- ⚠️ ARITHMÉTIQUE DE DATES: TODAY est un Python date. Utiliser timedelta pour les calculs :
  INTERDIT: TODAY - pl.duration(days=1)  → ERREUR de type !
  CORRECT:  pl.lit(TODAY - timedelta(days=1))  ou  pl.lit(TODAY) pour la date du jour
  Exemple hier: pl.col('DATE_DECLARATION') == pl.lit(TODAY - timedelta(days=1))
- ⚠️ OPÉRATEUR | (OU): TOUJOURS entourer les conditions OR de parenthèses car & a priorité sur |
  INTERDIT: .filter((A) & (B) & (C) | (D))  → D est évalué seul !
  CORRECT:  .filter((A) & (B) & ((C) | (D)))  → C|D est groupé
- ⚠️ DATES NULL: Quand on filtre des dates potentiellement nulles, TOUJOURS tester .is_null() AVANT les comparaisons
  ❌ INTERDIT: .filter((pl.col('DATE').is_null()) | (pl.col('DATE')) > TODAY)  → ERREUR "| not allowed on bool and date"
  ✅ CORRECT: .filter((pl.col('DATE').is_null()) | (pl.col('DATE') > pl.lit(TODAY)))  → Parenthèses autour de la comparaison complète
  La comparaison doit être COMPLÈTE avant le | : (is_null()) | (DATE > TODAY), pas (is_null()) | (DATE) > TODAY

RÈGLES MÉTIER IMPORTANTES:

⚠️ DISTINCTION CRITIQUE - "RECOUVRÉ" vs "PAS ENCORE RECOUVRÉ":
1. "Top 10 des contribuables par montant RECOUVRÉ" = Montants DÉJÀ payés (passé)
   ✅ CORRECT: .filter(pl.col('DATE_RECOUVREMENT') <= pl.lit(TODAY))
   ❌ INTERDIT: .filter(DATE_RECOUVREMENT > TODAY) → Ceci filtre le FUTUR, pas le passé !
   
2. "Montants PAS ENCORE recouvrés" / "En attente" = Recouvrements FUTURS ou NULL
   ✅ CORRECT: .filter((pl.col('DATE_RECOUVREMENT').is_null()) | (pl.col('DATE_RECOUVREMENT') > pl.lit(TODAY)))
   Les données contiennent des projections futures. Un recouvrement futur = pas encore effectué.

3. "Déclaré mais pas encore recouvré" = DATE_DECLARATION <= TODAY ET (DATE_RECOUVREMENT > TODAY OU NULL)
   ✅ CORRECT: .filter(pl.col('DATE_DECLARATION') <= pl.lit(TODAY)).filter((pl.col('DATE_RECOUVREMENT').is_null()) | (pl.col('DATE_RECOUVREMENT') > pl.lit(TODAY)))

⚠️ LOGIQUE CONTRADICTOIRE À ÉVITER:
❌ ERREUR GRAVE: Ne JAMAIS combiner ces deux filtres ensemble :
   .filter(DATE_RECOUVREMENT > TODAY)  # Futur
   .filter(DATE_RECOUVREMENT <= TODAY)  # Passé
   → Ces filtres s'annulent ! Résultat = 0 enregistrements toujours !

COLONNES RÉELLES (noms exacts):
- BUREAU, SOURCE, DIRECTION, LIBELLE, NATURE, CATEGORIE, TAXE_IMPOT_CD
- ⚠️ La colonne s'appelle DIRECTION (pas DIRECTION_REGIONALE) et TAXE_IMPOT_CD (pas TYPE_IMPOT_TAXE)

INSTRUCTIONS:
1. Comprends la demande de l'utilisateur naturellement
2. Définis les filtres appropriés (BUREAU, SOURCE, dates, etc.)
3. Choisis le group_by qui correspond à ce que l'utilisateur veut voir
4. Agrège avec TOTAL_DECLARE, TOTAL_RECOUVRE, NB_LIGNES
5. ⚠️ COLONNES ENRICHIES pour DÉCIDEURS: Ajouter dans .agg() des colonnes descriptives avec .first().
   ❗ RÈGLE ANTI-DOUBLON: NE JAMAIS ajouter dans .agg() une colonne qui est DÉJÀ dans group_by().
   Exemple si group_by('ID_CONTRIBUABLE'):
     .agg([pl.col('MONTANT_RECOUVRE').sum().alias('TOTAL_RECOUVRE'), pl.col('MONTANT_DECLARE').sum().alias('TOTAL_DECLARE'), pl.len().alias('NB_LIGNES'), pl.col('BUREAU').first().alias('BUREAU'), pl.col('SOURCE').first().alias('SOURCE'), pl.col('DIRECTION').first().alias('DIRECTION'), pl.col('LIBELLE').first().alias('LIBELLE'), pl.col('NATURE').first().alias('NATURE'), pl.col('TAXE_IMPOT_CD').first().alias('TYPE_IMPOT')])
   Exemple si group_by('BUREAU'):
     .agg([...]) → NE PAS mettre pl.col('BUREAU').first() car BUREAU est déjà clé du group_by !
   ❗ INTERDIT: Mettre la même colonne dans group_by() ET dans .agg() → DuplicateError
6. Retourne: result = {{"principal": data.filter(...).group_by(...).agg([...]).sort(...).collect().to_dicts()}}

Génère uniquement le code Python, sans explication.

"""

    def _generate_insight(self, query: str, execution_result: Any, code: str = "") -> Dict[str, Any]:
        """DATA Génère une synthèse décisionnelle complète avec KPIs et recommandations"""
        
        try:
            # CHART ENRICHISSEMENT AUTOMATIQUE
            enriched = self._enrich_results_for_decision(execution_result, query)
            
            #  Génération de l'analyse décisionnelle complète (PAS DE FALLBACK)
            return self._generate_decision_insight(query, enriched)
            
        except Exception as e:
            logger.error(f"Erreur génération insight: {e}")
            # Réessayer avec données brutes
            return self._generate_decision_insight(query, {'data': execution_result, 'kpis': {}})
    
    def _generate_decision_insight(self, query: str, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """CHART Synthèse décisionnelle enrichie avec analyses multi-dimensionnelles"""
        
        try:
            data = enriched_data.get('data', [])
            kpis = enriched_data.get('kpis', {})
            metadata = enriched_data.get('metadata', {})
            analyses_complementaires = enriched_data.get('analyses_complementaires', {})
            
            #  GNRATION D'ANALYSE RSUME NARRATIVE (avec analyses complémentaires)
            analyse_resume = self._generate_narrative_summary(query, data, kpis, analyses_complementaires)
            
            # 🎯 RECOMMANDATIONS STRATÉGIQUES LOCALES (toujours activées, sans appel API)
            recommandations_strategiques = enriched_data.get('recommandations_strategiques', [])
            alertes_decisionnelles = enriched_data.get('alertes_decisionnelles', [])
            
            # FAST Recommandations et alertes via IA optionnelles (gain 60s si désactivées)
            recommandations = []
            alertes = []
            
            if self.config.ENABLE_RECOMMENDATIONS:
                try:
                    recommandations = self._generate_recommendations(kpis, metadata.get('query_type'), data, query)
                except Exception as e:
                    logger.warning(f" Recommandations timeout/erreur: {e}")
            
            if self.config.ENABLE_ALERTS:
                try:
                    alertes = self._generate_alerts(kpis, data, query)
                except Exception as e:
                    logger.warning(f" Alertes timeout/erreur: {e}")
            
            # Construction de la synthèse
            # FAST IMPORTANT: donnees_detaillees doit TOUJOURS être un array pour affichage tableau
            donnees_array = data if isinstance(data, list) else [data] if data else []
            
            summary = {
                'type': 'decision_analysis',
                'titre': self._generate_title(query, metadata.get('query_type', 'general')),
                'analyse_resume': analyse_resume,  # Briefing décisionnel complet
                'synthese_executive': self._generate_executive_text(query, kpis, data),
                'kpis': kpis,
                'donnees_detaillees': donnees_array,  # TOUJOURS un array
                'analyses_complementaires': analyses_complementaires,  #  Analyses multi-dimensionnelles
                'recommandations_strategiques': recommandations_strategiques,  # 🎯 NOUVEAU: Recommandations pour décideurs
                'alertes_decisionnelles': alertes_decisionnelles,  # 🚨 NOUVEAU: Alertes pour décideurs
                'recommandations': recommandations,
                'alertes': alertes
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur génération insight décisionnel: {e}")
            return {
                'type': 'simple_result',
                'titre': 'Analyse des Données',
                'donnees_detaillees': enriched_data.get('data', [])
            }
    
    def _generate_title(self, query: str, query_type: str) -> str:
        """Génère un titre pertinent basé sur le contexte de la requête"""
        query_lower = query.lower()
        
        # Contexte spécifique prioritaire
        if any(mot in query_lower for mot in ['fraude', 'fraudeur', 'fraudes', 'fraudeurs']):
            return 'ALERT Analyse des Fraudes Fiscales'
        elif any(mot in query_lower for mot in ['anomalie', 'anomalies', 'irrégularité', 'irrégularités']):
            return ' Analyse des Anomalies Fiscales'
        elif any(mot in query_lower for mot in ['douane', 'dgd', 'douanes', 'douanier']):
            return ' Analyse Douanière (DGD)'
        
        # Fallback sur le type de requête
        titles = {
            'classement': ' Classement et Performance',
            'temporel': 'CHART volution Temporelle',
            'performance': 'TARGET Analyse de Performance',
            'comparaison': 'COMPARE Analyse Comparative',
            'general': 'DATA Analyse Décisionnelle'
        }
        return titles.get(query_type, 'DATA Synthèse Décisionnelle')
    
    def _generate_narrative_summary(self, query: str, data: list, kpis: Dict, analyses_complementaires: Dict = None) -> str:
        """📊 BRIEFING DÉCISIONNEL COMPLET pour décideurs de haut niveau (Ministre, DG)"""
        try:
            result_rows = len(data) if data else 0
            parts = []
            
            # ═══════════════════════════════════════════════════════════════
            # 1. CONTEXTE ET PÉRIMÈTRE D'ANALYSE
            # ═══════════════════════════════════════════════════════════════
            nb_records = kpis.get('nb_enregistrements_analyses', 0)
            if nb_records > 0:
                parts.append(f"**📋 Périmètre d'analyse :** {nb_records:,} enregistrements fiscaux agrégés en **{result_rows} entités distinctes**.")
            elif result_rows > 0:
                parts.append(f"**📋 Périmètre :** {result_rows} entités identifiées dans le périmètre de l'analyse.")
            
            # ═══════════════════════════════════════════════════════════════
            # 2. PERFORMANCE FINANCIÈRE GLOBALE
            # ═══════════════════════════════════════════════════════════════
            total_recouvre = kpis.get('montant_recouvre') or kpis.get('total_recouvre')
            total_declare = kpis.get('montant_declare') or kpis.get('total_declare')
            
            if total_recouvre and total_declare:
                taux = (total_recouvre / total_declare * 100) if total_declare > 0 else 0
                # Qualification de la performance
                if taux >= 105:
                    perf_label = "🟢 **SURPERFORMANCE**"
                    perf_detail = "Le recouvrement excède significativement les déclarations, traduisant une efficacité remarquable du dispositif de recouvrement."
                elif taux >= 95:
                    perf_label = "🟢 **PERFORMANCE SATISFAISANTE**"
                    perf_detail = "Le taux de recouvrement est dans la fourchette optimale, traduisant un bon fonctionnement du système fiscal."
                elif taux >= 80:
                    perf_label = "🟡 **PERFORMANCE MODÉRÉE**"
                    perf_detail = "Le taux de recouvrement reste en deçà des objectifs. Des mesures d'optimisation sont nécessaires."
                else:
                    perf_label = "🔴 **SOUS-PERFORMANCE CRITIQUE**"
                    perf_detail = "Le déficit de recouvrement est alarmant et nécessite des mesures d'urgence de la part des autorités."
                
                parts.append(f"\n\n**💰 Performance financière globale — {perf_label}**")
                parts.append(f"Le montant total déclaré s'élève à **{total_declare:,.0f} FCFA** pour un recouvrement effectif de **{total_recouvre:,.0f} FCFA**, soit un **taux de recouvrement de {taux:.1f}%**. {perf_detail}")
                
                ecart = total_recouvre - total_declare
                if ecart > 0:
                    parts.append(f"L'excédent de recouvrement de **+{ecart:,.0f} FCFA** ({ecart/total_declare*100:.1f}% au-dessus des déclarations) peut s'expliquer par les pénalités de retard, les redressements fiscaux ou les recouvrements sur exercices antérieurs.")
                elif ecart < 0:
                    perte_pct = abs(ecart) / total_declare * 100
                    parts.append(f"⚠️ **Alerte financière :** Un manque à gagner de **{abs(ecart):,.0f} FCFA** est constaté, représentant **{perte_pct:.1f}%** du montant déclaré. Ce gap nécessite une analyse approfondie des causes de sous-recouvrement.")
            elif total_recouvre:
                parts.append(f"\n\n**💰 Volume de recouvrement :** Le montant total recouvré atteint **{total_recouvre:,.0f} FCFA**.")
            elif total_declare:
                parts.append(f"\n\n**💰 Volume déclaré :** Le montant total déclaré s'élève à **{total_declare:,.0f} FCFA**.")
            
            # ═══════════════════════════════════════════════════════════════
            # 3. POIDS ET RÉPARTITION DES RECETTES (langage décisionnel)
            # ═══════════════════════════════════════════════════════════════
            if data and isinstance(data, list) and len(data) >= 3 and isinstance(data[0], dict):
                val_col = next((k for k in ['TOTAL_RECOUVRE', 'MONTANT_RECOUVRE', 'TOTAL_DECLARE', 'MONTANT_DECLARE'] if k in data[0]), None)
                id_col = next((k for k in data[0].keys() if k not in ['NB_LIGNES', 'TOTAL_DECLARE', 'TOTAL_RECOUVRE', 'MONTANT_DECLARE', 'MONTANT_RECOUVRE', 'COUNT', 'count', 'BUREAU', 'SOURCE', 'DIRECTION', 'LIBELLE', 'NATURE', 'CATEGORIE', 'TAXE_IMPOT_CD', 'TYPE_IMPOT']), None)
                
                if val_col and id_col:
                    values = [float(row.get(val_col, 0) or 0) for row in data]
                    total_val = sum(values)
                    
                    if total_val > 0 and len(values) >= 3:
                        # Concentration Top 3
                        top3_sum = sum(sorted(values, reverse=True)[:3])
                        concentration_top3 = (top3_sum / total_val) * 100
                        
                        # Montant moyen
                        moy = total_val / len(values)
                        
                        # Écart entre premier et dernier
                        val_max = max(values)
                        val_min = min(values)
                        
                        parts.append(f"\n\n**📊 Poids et répartition des recettes**")
                        parts.append(f"Le montant moyen par entité s'établit à **{moy:,.0f} FCFA** sur {len(values)} entités analysées.")
                        
                        if concentration_top3 > 50:
                            parts.append(f"⚠️ **Point d'attention :** Les 3 premiers contribuables pèsent à eux seuls **{concentration_top3:.1f}%** des recettes totales. Cette dépendance constitue un risque budgétaire : la défaillance d'un seul d'entre eux impacterait significativement les finances publiques.")
                        elif concentration_top3 > 30:
                            parts.append(f"Les 3 premiers contribuables représentent **{concentration_top3:.1f}%** des recettes, montrant une répartition relativement équilibrée.")
                        else:
                            parts.append(f"La base fiscale est bien diversifiée : les 3 premiers ne représentent que **{concentration_top3:.1f}%** du total, limitant le risque de dépendance.")
                        
                        if val_min > 0:
                            ecart_absolu = val_max - val_min
                            parts.append(f"L'écart entre le plus gros contributeur (**{val_max:,.0f} FCFA**) et le plus petit (**{val_min:,.0f} FCFA**) est de **{ecart_absolu:,.0f} FCFA**.")
            
            # ═══════════════════════════════════════════════════════════════
            # 4. CLASSEMENT DÉTAILLÉ ET FAITS SAILLANTS
            # ═══════════════════════════════════════════════════════════════
            if data and isinstance(data, list) and len(data) >= 2 and isinstance(data[0], dict):
                first = data[0]
                last = data[-1]
                id_col = next((k for k in first.keys() if k not in ['NB_LIGNES', 'TOTAL_DECLARE', 'TOTAL_RECOUVRE', 'MONTANT_DECLARE', 'MONTANT_RECOUVRE', 'COUNT', 'count', 'BUREAU', 'SOURCE', 'DIRECTION', 'LIBELLE', 'NATURE', 'CATEGORIE', 'TAXE_IMPOT_CD', 'TYPE_IMPOT']), None)
                val_col = next((k for k in ['TOTAL_RECOUVRE', 'MONTANT_RECOUVRE', 'TOTAL_DECLARE', 'MONTANT_DECLARE'] if k in first), None)
                
                if id_col and val_col:
                    parts.append(f"\n\n**🏆 Classement et faits saillants**")
                    # Top 3 détaillé avec caractéristiques
                    for i, row in enumerate(data[:3]):
                        val = float(row.get(val_col, 0) or 0)
                        medal = ['🥇', '🥈', '🥉'][i]
                        nb_ops = row.get('NB_LIGNES', 'N/A')
                        # Enrichir avec les infos contextuelles disponibles
                        details = []
                        if row.get('BUREAU'): details.append(f"Bureau : {row['BUREAU']}")
                        if row.get('SOURCE'): details.append(f"Source : {row['SOURCE']}")
                        if row.get('DIRECTION') or row.get('DIRECTION_REGIONALE'): details.append(f"Direction : {row.get('DIRECTION') or row.get('DIRECTION_REGIONALE')}")
                        detail_str = f" — *{', '.join(details)}*" if details else ""
                        parts.append(f"{medal} **{row.get(id_col, 'N/A')}** — **{val:,.0f} FCFA** ({nb_ops} opérations){detail_str}")
                    
                    # Écart entre 1er et dernier (langage simple)
                    val_first = float(first.get(val_col, 0) or 0)
                    val_last = float(last.get(val_col, 0) or 0)
                    if val_last > 0:
                        parts.append(f"\nL'écart entre le 1er (**{first.get(id_col)}**, {val_first:,.0f} FCFA) et le dernier (**{last.get(id_col)}**, {val_last:,.0f} FCFA) est de **{val_first - val_last:,.0f} FCFA**.")
            
            # ═══════════════════════════════════════════════════════════════
            # 5. VENTILATION PAR DIMENSIONS (CATEGORIE, NATURE, LIBELLE, SOURCE)
            # ═══════════════════════════════════════════════════════════════
            if data and isinstance(data, list) and len(data) >= 2 and isinstance(data[0], dict):
                val_col_vent = next((k for k in ['TOTAL_RECOUVRE', 'MONTANT_RECOUVRE', 'TOTAL_DECLARE', 'MONTANT_DECLARE'] if k in data[0]), None)
                total_vent = sum(float(row.get(val_col_vent, 0) or 0) for row in data) if val_col_vent else 0
                
                # Dimensions à analyser (colonnes catégorielles présentes dans les données)
                dimensions = [
                    ('CATEGORIE', '📂 Répartition par catégorie', 'catégorie'),
                    ('NATURE', '🏷️ Répartition par nature', 'nature'),
                    ('SOURCE', '🏛️ Répartition par source (DGID/DGD)', 'source'),
                ]
                
                has_ventilation = False
                for col_name, titre, label in dimensions:
                    if col_name in data[0] and val_col_vent and total_vent > 0:
                        # Agréger par cette dimension
                        dim_totals = {}
                        dim_counts = {}
                        for row in data:
                            key = row.get(col_name, 'Non renseigné') or 'Non renseigné'
                            val = float(row.get(val_col_vent, 0) or 0)
                            nb = int(row.get('NB_LIGNES', 0) or 0)
                            dim_totals[key] = dim_totals.get(key, 0) + val
                            dim_counts[key] = dim_counts.get(key, 0) + nb
                        
                        # Trier par montant décroissant
                        sorted_dims = sorted(dim_totals.items(), key=lambda x: x[1], reverse=True)
                        
                        if len(sorted_dims) >= 2:
                            if not has_ventilation:
                                parts.append(f"\n\n**📊 Analyse détaillée par dimension**")
                                has_ventilation = True
                            
                            parts.append(f"\n**{titre}** ({len(sorted_dims)} {label}s distinctes) :")
                            for i, (dim_name, dim_val) in enumerate(sorted_dims[:5]):
                                pct = (dim_val / total_vent * 100)
                                nb_total = dim_counts.get(dim_name, 0)
                                bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
                                parts.append(f"  {'▸' if i > 0 else '▹'} **{dim_name}** — {dim_val:,.0f} FCFA ({pct:.1f}%) — {nb_total:,} opérations")
                            
                            if len(sorted_dims) > 5:
                                reste_val = sum(v for _, v in sorted_dims[5:])
                                parts.append(f"  ▸ *{len(sorted_dims) - 5} autres {label}s* — {reste_val:,.0f} FCFA ({reste_val/total_vent*100:.1f}%)")
                            
                            # Insight décisionnel sur la concentration de cette dimension
                            top1_pct = sorted_dims[0][1] / total_vent * 100 if total_vent > 0 else 0
                            if top1_pct > 40:
                                parts.append(f"  ⚠️ *La {label} «{sorted_dims[0][0]}» représente à elle seule {top1_pct:.1f}% des recettes — forte dépendance.*")
                        elif len(sorted_dims) == 1:
                            parts.append(f"\n**{titre}** : Toutes les recettes proviennent de **{sorted_dims[0][0]}**.")
                
                # Analyse LIBELLE spécifique (top contributeurs par type de taxe)
                if 'LIBELLE' in data[0] and val_col_vent and total_vent > 0:
                    lib_totals = {}
                    for row in data:
                        key = row.get('LIBELLE', 'Non renseigné') or 'Non renseigné'
                        val = float(row.get(val_col_vent, 0) or 0)
                        lib_totals[key] = lib_totals.get(key, 0) + val
                    
                    sorted_libs = sorted(lib_totals.items(), key=lambda x: x[1], reverse=True)
                    
                    if len(sorted_libs) >= 2:
                        if not has_ventilation:
                            parts.append(f"\n\n**📊 Analyse détaillée par dimension**")
                            has_ventilation = True
                        
                        parts.append(f"\n**📋 Principales taxes et impôts** ({len(sorted_libs)} libellés distincts) :")
                        for i, (lib_name, lib_val) in enumerate(sorted_libs[:5]):
                            pct = (lib_val / total_vent * 100)
                            parts.append(f"  {'▸' if i > 0 else '▹'} **{lib_name}** — {lib_val:,.0f} FCFA ({pct:.1f}%)")
                        
                        # Top 3 représentent X% du total
                        top3_val = sum(v for _, v in sorted_libs[:3])
                        top3_pct = top3_val / total_vent * 100 if total_vent > 0 else 0
                        parts.append(f"  💡 *Les 3 premiers types de taxes représentent **{top3_pct:.1f}%** des recettes totales.*")
            
            # ═══════════════════════════════════════════════════════════════
            # 6. ANALYSES COMPLÉMENTAIRES (depuis statistiques pré-calculées)
            # ═══════════════════════════════════════════════════════════════
            if analyses_complementaires:
                has_complementaires = False
                
                if 'repartition_nature' in analyses_complementaires and analyses_complementaires['repartition_nature']:
                    has_complementaires = True
                    natures = analyses_complementaires['repartition_nature'][:5]
                    nature_names = [r.get('NATURE', '') for r in natures if r.get('NATURE')]
                    if nature_names:
                        parts.append(f"\n\n**🏷️ Ventilation par nature d'impôt :** Les principales natures concernées sont : **{', '.join(nature_names[:3])}**. Cette diversification des sources fiscales est {'un facteur de résilience' if len(nature_names) > 3 else 'à surveiller pour éviter une dépendance excessive'}.")
                
                if 'repartition_direction' in analyses_complementaires and analyses_complementaires['repartition_direction']:
                    has_complementaires = True
                    directions = analyses_complementaires['repartition_direction'][:3]
                    dir_names = [r.get('DIRECTION', r.get('DIRECTION_REGIONALE', '')) for r in directions]
                    dir_names = [d for d in dir_names if d]
                    if dir_names:
                        parts.append(f"**🗺️ Couverture géographique :** Les principales directions contributrices sont : **{', '.join(dir_names)}**.")
            
            return "\n".join(parts) if parts else f"Analyse des données en réponse à : {query}"
            
        except Exception as e:
            logger.warning(f"Erreur génération analyse narrative: {e}")
            return f"Analyse statistique des données en réponse à: {query}"
    
    def _compute_financial_statistics(self, data: list, query: str) -> Dict[str, Any]:
        """Calcul statistiques essentielles pour l'analyse narrative (version optimisée)"""
        if not data:
            return {"message": "Aucune donnée à analyser"}
        
        try:
            stats = {
                "nombre_total_enregistrements": len(data),
                "analyse_montants": {}
            }
            
            df = pd.DataFrame(data)
            
            # Seules les colonnes financières essentielles
            montant_cols = [
                'MONTANT_DECLARE', 'MONTANT_RECOUVRE',
                'TOTAL_DECLARE', 'TOTAL_RECOUVRE',
                'TAUX_RECOUVREMENT'
            ]
            for col in montant_cols:
                if col in df.columns:
                    values = pd.to_numeric(df[col], errors='coerce').dropna()
                    if len(values) > 0:
                        stats["analyse_montants"][col.lower()] = {
                            "somme": float(values.sum()),
                            "moyenne": float(values.mean()),
                            "min": float(values.min()),
                            "max": float(values.max()),
                            "count": len(values)
                        }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques financières: {e}")
            return {
                "erreur": f"Erreur calcul statistiques: {e}",
                "nombre_enregistrements": len(data),
                "message": "Statistiques partielles - utilisation des KPIs de base"
            }
    
    def _format_value(self, value: Any) -> str:
        """Formatte une valeur pour affichage lisible"""
        if isinstance(value, float):
            if value > 1_000_000_000:
                return f"{value/1_000_000_000:.2f}Mds"
            elif value > 1_000_000:
                return f"{value/1_000_000:.2f}M"
            elif value > 1_000:
                return f"{value/1_000:.2f}K"
            else:
                return f"{value:.2f}"
        elif isinstance(value, int):
            if value > 1_000_000_000:
                return f"{value/1_000_000_000:.2f}Mds"
            elif value > 1_000_000:
                return f"{value/1_000_000:.2f}M"
            elif value > 1_000:
                return f"{value:,}"
            else:
                return str(value)
        else:
            return str(value)[:50]  # Limiter les chanes longues
    
    def _generate_executive_text(self, query: str, kpis: Dict, data: list) -> str:
        """Génère le texte de synthèse exécutive ENRICHI"""
        parts = []
        
        # DATA PRIORIT: Afficher le nombre EXACT d'enregistrements si disponible
        if kpis.get('nb_enregistrements_analyses'):
            parts.append(f"📋 **{kpis['nb_enregistrements_analyses']:,} enregistrements fiscaux** analysés")
        elif kpis.get('total_records'):
            parts.append(f"📋 **{kpis['total_records']} groupes** agrégés")
        
        if kpis.get('montant_declare'):
            parts.append(f"💰 **Montant total déclaré** : {kpis['montant_declare']:,.0f} FCFA")
        
        if kpis.get('montant_recouvre'):
            parts.append(f"✅ **Montant total recouvré** : {kpis['montant_recouvre']:,.0f} FCFA")
        
        if kpis.get('taux_recouvrement'):
            qualif = kpis.get('qualification_performance', '')
            parts.append(f"📈 **Taux de recouvrement global** : {kpis['taux_recouvrement']:.1f}% — {qualif}")
        
        if kpis.get('ecart'):
            ecart = kpis['ecart']
            signe = '+' if ecart > 0 else ''
            parts.append(f"📊 **Écart déclaré/recouvré** : {signe}{ecart:,.0f} FCFA")
        
        if kpis.get('moyenne_par_entite'):
            parts.append(f"📐 **Montant moyen par entité** : {kpis['moyenne_par_entite']:,.0f} FCFA")
        
        if kpis.get('concentration_top3'):
            pct = kpis['concentration_top3']
            if pct > 50:
                parts.append(f"⚠️ **Dépendance fiscale** : Les 3 premiers contribuables pèsent {pct:.1f}% des recettes — risque budgétaire")
            else:
                parts.append(f"⚖️ **Répartition des recettes** : Les 3 premiers représentent {pct:.1f}% du total")
        
        if kpis.get('valeur_max') and kpis.get('valeur_min'):
            parts.append(f"📊 **Fourchette** : de {kpis['valeur_min']:,.0f} à {kpis['valeur_max']:,.0f} FCFA")
        
        if kpis.get('atteinte_objectif'):
            parts.append(f"🎯 **Atteinte objectif** : {kpis['atteinte_objectif']:.1f}%")
        
        return "\n".join(parts) if parts else "Analyse des données fiscales"
    
    def _generate_narrative_summary_OLD_DEPRECATED(self, query: str, data: list, kpis: Dict) -> str:
        """ ANALYSE RSUME NARRATIVE - Génération IA basée sur les KPIs RELS"""
        try:
            #  CRITIQUE: Utiliser les KPIs AGRGS comme source de vérité, PAS les données brutes
            # Les KPIs sont les totaux réels calculés par _enrich_results_for_decision()
            
            # Formater les KPIs de façon lisible pour l'IA
            kpi_details = []
            if kpis:
                kpi_mapping = {
                    'montant_declare': ('Montant Total Déclaré', 'FCFA'),
                    'montant_recouvre': ('Montant Total Recouvré', 'FCFA'),
                    'attendu_mensuel': ('Attendu pour ce mois', 'FCFA'),
                    'objectif': ('Objectif mensuel', 'FCFA'),
                    'taux_recouvrement': ('Taux de Recouvrement', '%'),
                    'atteinte_objectif': ('Taux Atteinte Objectif mensuel', '%'),
                    'ecart': ('cart (Recouvré - Déclaré)', 'FCFA'),
                    'depassement_objectif': ('Dépassement Objectif mensuel', 'FCFA'),
                    'nb_lignes': ('Nombre de lignes', '')
                }
                for key, value in kpis.items():
                    if key in kpi_mapping and value is not None:
                        label, unit = kpi_mapping[key]
                        if isinstance(value, (int, float)):
                            if unit == 'FCFA':
                                formatted = f"{value:,.0f} FCFA"
                            elif unit == '%':
                                formatted = f"{value:.1f}%"
                            else:
                                formatted = f"{value:,.0f}"
                        else:
                            formatted = str(value)
                        kpi_details.append(f"- {label}: {formatted}")
            
            kpi_text = "\n".join(kpi_details) if kpi_details else "Aucun KPI disponible"
            nb_lignes = len(data) if data else 0
            
            # Prompt pour l'IA avec KPIs EXPLICITES comme source de vérité
            narrative_prompt = f"""Tu es un CONSEILLER STRATGIQUE SENIOR de la Direction Générale des Impts et Domaines (DGID) du Sénégal. Tu fournis des briefings décisionnels de haut niveau aux décideurs.

TARGET MISSION: Fournir une analyse claire, factuelle et orientée action pour la prise de décision.

Requête analysée: {query}

DATA INDICATEURS OFFICIELS CERTIFIS:
{kpi_text}
- Nombre d'opérations analysées: {nb_lignes}

 RGLES D'ANALYSE:
1. Utilise EXCLUSIVEMENT les chiffres officiels ci-dessus
2. Taux de recouvrement = Montant Recouvré / Montant Déclaré  100
3. cart = Montant Recouvré - Montant Déclaré
4. Taux > 100% = SURPERFORMANCE (recouvrement excédentaire)
5. Taux < 100% = SOUS-PERFORMANCE (déficit de recouvrement)
6.  OBJECTIF et ATTENDU sont des valeurs MENSUELLES, PAS annuelles

 FORMAT BRIEFING DCISIONNEL:
1. Rédige 3-5 phrases dans un style de note professionnelle de haut niveau
2. VARIT OBLIGATOIRE - NE commence JAMAIS par "Cette analyse révèle" - utilise:
   - "Les indicateurs de [période/zone] montrent..."
   - "Sur le périmètre analysé, on observe..."
   - "Le point de situation fait ressortir..."
   - "Les données fiscales confirment..."
   - "Concernant [sujet de la requête]..."
   - "L'analyse des recettes indique..."
3. Cite les chiffres clés avec leur SIGNIFICATION pour la politique fiscale
4. Qualifie la PERFORMANCE (excellente/satisfaisante/préoccupante)
5. Identifie les POINTS D'ATTENTION pour la prise de décision
6. Ton: formel, précis, stratégique - adapté à un décideur de haut niveau

Génère le briefing (texte seul, sans titre ni formatage):"""
            
            response = self._call_ai("Tu es un Conseiller Stratégique Senior de la DGID du Sénégal, expert en analyse décisionnelle fiscale pour les autorités de tous niveaux.", narrative_prompt)
            return response.strip()
            
        except Exception as e:
            logger.warning(f" Erreur génération analyse narrative: {e}")
            # Fallback simple
            return f"Analyse des données en réponse à: {query}"
    
    def _generate_recommendations(self, kpis: Dict, query_type: str, data: list, query: str) -> list:
        """ RECOMMANDATIONS OPTIMISES - Basées sur KPIs uniquement"""
        try:
            # FAST OPTIMIS: Utiliser KPIs au lieu de data brut (gain 5-10s)
            kpis_str = ", ".join([f"{k}={v}" for k, v in kpis.items()]) if kpis else "Aucun KPI"
            
            rec_prompt = f"""KPIs: {kpis_str}
Requête: {query}

Génère 2 recommandations en JSON:
[{{"priorite": "haute/moyenne", "action": "...", "justification": "..."}}]

Sois CONCRET et ACTIONNABLE."""
            
            response = self._call_ai("Expert conseil fiscal.", rec_prompt)
            import json
            return json.loads(response)
        except:
            return []  # Pas de recommandations si échec
    
    def _generate_alerts(self, kpis: Dict, data: list, query: str) -> list:
        """ ALERTES OPTIMISES - Basées sur KPIs uniquement"""
        try:
            # FAST OPTIMIS: Utiliser KPIs au lieu de data brut (gain 5-10s)
            kpis_str = ", ".join([f"{k}={v}" for k, v in kpis.items()]) if kpis else "Aucun KPI"
            
            alert_prompt = f"""KPIs: {kpis_str}

Identifie ALERTES si nécessaire en JSON:
[{{"niveau": "critique/warning", "message": "..."}}]

Si aucune alerte: réponds []"""
            
            response = self._call_ai("Expert analyste fiscal.", alert_prompt)
            import json
            return json.loads(response)
        except:
            return []
        """Méthode de secours pour la génération d'insights (version structurée)"""
        
        try:
            # Vérification des résultats
            has_data = False
            data_len = 0
            
            if execution_result:
                if isinstance(execution_result, list) and len(execution_result) > 0:
                    has_data = True
                    data_len = len(execution_result)
                elif isinstance(execution_result, dict) and execution_result:
                    has_data = True
                    data_len = 1
                elif hasattr(execution_result, '__len__') and len(execution_result) > 0:
                    has_data = True
                    data_len = len(execution_result)
                elif execution_result not in [None, [], {}, ""]:
                    has_data = True
                    data_len = 1
            
            # Aucune donnée trouvée
            if not has_data:
                return {
                    'type': 'empty_result',
                    'titre': 'Aucun Résultat',
                    'kpis': {},
                    'alertes': [{
                        'niveau': 'info',
                        'message': 'Aucune donnée correspondant aux critères'
                    }],
                    'recommandations': [{
                        'priorite': 'haute',
                        'action': 'Vérifier les critères de recherche',
                        'justification': 'Aucun résultat trouvé'
                    }]
                }
            
            # Données trouvées - Analyse basique
            return {
                'type': 'simple_result',
                'titre': 'Analyse des Données',
                'kpis': {
                    'total_records': data_len
                },
                'statistiques': {},
                'recommandations': []
            }
            
        except Exception as e:
            logger.error(f"Erreur génération insight fallback: {e}")
            return {
                'type': 'error',
                'titre': 'Analyse des Données',
                'kpis': {}
            }


    def _call_ai(self, system_prompt: str, user_prompt: str) -> str:
        """Appel IA avec gestion d'erreur avancée et validation taille"""
        try:
            #  Validation de la taille des prompts pour éviter les erreurs
            total_size = len(system_prompt) + len(user_prompt)
            if total_size > 30000:  # Seuil ajusté pour permettre plus de contexte
                logger.warning(f" Prompt très long ({total_size} caractères)")
                if len(user_prompt) > 20000:
                    user_prompt = user_prompt[:20000] + "\n\n[...Données tronquées...]"
                    logger.info(" Prompt tronqué pour performance")
            
            # Log pour débogage
            logger.info(f"🤖 Appel IA ({self.config.MODEL_NAME}) - Taille: {total_size} caractères")
            
            api_start = time.time()
            response = self.client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.config.TEMPERATURE,
                max_tokens=self.config.MAX_TOKENS,
                timeout=self.config.REQUEST_TIMEOUT  # Timeout explicite
            )
            api_time = time.time() - api_start
            logger.info(f"✅ API répondu en {api_time:.1f}s")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Erreur appel IA (taille prompt: {len(system_prompt) + len(user_prompt)} chars): {e}")
            raise
    
    def _extract_code(self, response: str) -> str:
        """Extraction du code Python (alias vers _extract_code_raw + corrections)"""
        code = self._extract_code_raw(response)
        return self._apply_polars_fixes(code) if code else ''
    
    def _enrich_results_for_decision(self, execution_result: Any, query: str) -> Dict[str, Any]:
        """CHART ENRICHISSEMENT avec calcul EXACT du nombre d'enregistrements et support multi-dimensionnel"""
        
        enriched = {
            'data': execution_result,
            'metadata': {},
            'kpis': {},
            'analyses_complementaires': {}
        }
        
        try:
            # SEARCH DTECTION RSULTAT MULTI-DIMENSIONNEL (dict avec sous-analyses)
            if isinstance(execution_result, dict):
                # Vérifier si c'est un résultat multi-dimensionnel
                multi_keys = ['principal', 'repartition_nature', 'top_libelles', 'repartition_pays', 
                              'repartition_categorie', 'repartition_regime', 'repartition_direction']
                has_multi = any(key in execution_result for key in multi_keys)
                
                if has_multi:
                    enriched['metadata']['type_analyse'] = 'multi_dimensionnelle'
                    
                    # Extraire le résultat principal
                    if 'principal' in execution_result:
                        enriched['data'] = execution_result['principal']
                        execution_result_for_kpis = execution_result['principal']
                    else:
                        execution_result_for_kpis = []
                    
                    # Stocker les analyses complémentaires
                    for key in multi_keys[1:]:  # Toutes sauf 'principal'
                        if key in execution_result and execution_result[key]:
                            enriched['analyses_complementaires'][key] = execution_result[key]
                    
                    # Utiliser le résultat principal pour les KPIs
                    if isinstance(execution_result_for_kpis, list) and len(execution_result_for_kpis) > 0:
                        execution_result = execution_result_for_kpis
                    else:
                        return enriched
                else:
                    # Dict simple, le convertir en liste
                    execution_result = [execution_result]
            
            if isinstance(execution_result, list) and len(execution_result) > 0:
                # Nombre de groupes agrégés
                enriched['kpis']['total_records'] = len(execution_result)
                enriched['metadata']['query_type'] = self._detect_query_type(query)
                
                # DATA CALCUL EXACT du nombre d'enregistrements via NB_LIGNES
                if isinstance(execution_result[0], dict):
                    first_row = execution_result[0]
                    count_keys = ['NB_LIGNES', 'COUNT', 'count', 'nb_enregistrements', 'NOMBRE', 'nb_lignes']
                    for key in count_keys:
                        if key in first_row:
                            total_records_exact = sum(int(row.get(key, 0) or 0) for row in execution_result)
                            enriched['kpis']['nb_enregistrements_analyses'] = total_records_exact
                            enriched['metadata']['has_exact_count'] = True
                            break
                
                # Si l'IA a calculé des KPIs dans les résultats, on les extrait
                if execution_result and isinstance(execution_result[0], dict):
                    first_row = execution_result[0]
                    
                    # SEARCH DTECTION FLEXIBLE des colonnes montants (alias variés)
                    recouvre_keys = ['TOTAL_RECOUVRE', 'MONTANT_RECOUVRE_TOTAL', 'MONTANT_RECOUVRE', 'total_recouvre', 'recouvre']
                    declare_keys = ['TOTAL_DECLARE', 'MONTANT_DECLARE_TOTAL', 'MONTANT_DECLARE', 'total_declare', 'declare']
                    attendu_keys = ['ATTENDU_MENSUEL', 'ATTENDU_MT', 'attendu_mensuel', 'attendu']
                    objectif_keys = ['OBJECTIF', 'OBJ_MT', 'objectif']
                    
                    # Trouver la clé qui existe pour chaque type
                    recouvre_key = next((k for k in recouvre_keys if k in first_row), None)
                    declare_key = next((k for k in declare_keys if k in first_row), None)
                    attendu_key = next((k for k in attendu_keys if k in first_row), None)
                    objectif_key = next((k for k in objectif_keys if k in first_row), None)
                    
                    # Somme des montants déclarés et recouvrés
                    if recouvre_key:
                        enriched['kpis']['montant_recouvre'] = sum(row.get(recouvre_key, 0) or 0 for row in execution_result)
                    if declare_key:
                        enriched['kpis']['montant_declare'] = sum(row.get(declare_key, 0) or 0 for row in execution_result)
                    
                    #  OBJECTIF et ATTENDU_MENSUEL sont FIXES par LIBELLE et par MOIS/ANNE
                    # On doit les dédupliquer par LIBELLE pour éviter de compter les doublons
                    if attendu_key:
                        # Dédupliquer par LIBELLE si présent
                        if 'LIBELLE' in first_row:
                            seen_libelles = {}
                            for row in execution_result:
                                libelle = row.get('LIBELLE', 'unknown')
                                attendu = row.get(attendu_key, 0) or 0
                                if libelle not in seen_libelles:
                                    seen_libelles[libelle] = attendu
                            enriched['kpis']['attendu_mensuel'] = sum(seen_libelles.values())
                        else:
                            # Pas de libellé, prendre la somme (peut être approximatif)
                            enriched['kpis']['attendu_mensuel'] = sum(row.get(attendu_key, 0) or 0 for row in execution_result)
                    
                    if objectif_key:
                        # Dédupliquer par LIBELLE si présent
                        if 'LIBELLE' in first_row:
                            seen_libelles = {}
                            for row in execution_result:
                                libelle = row.get('LIBELLE', 'unknown')
                                objectif = row.get(objectif_key, 0) or 0
                                if libelle not in seen_libelles:
                                    seen_libelles[libelle] = objectif
                            enriched['kpis']['objectif'] = sum(seen_libelles.values())
                        else:
                            # Pas de libellé, prendre la somme
                            enriched['kpis']['objectif'] = sum(row.get(objectif_key, 0) or 0 for row in execution_result)
                    
                    # Calcul taux global si les deux présents
                    if enriched['kpis'].get('montant_recouvre') and enriched['kpis'].get('montant_declare'):
                        total_r = enriched['kpis']['montant_recouvre']
                        total_d = enriched['kpis']['montant_declare']        
                        if total_d > 0:
                            enriched['kpis']['taux_recouvrement'] = (total_r / total_d) * 100
                            enriched['kpis']['ecart'] = total_r - total_d
                    
                    # Calcul taux d'atteinte objectif si présent
                    if enriched['kpis'].get('montant_recouvre') and enriched['kpis'].get('objectif'):
                        total_r = enriched['kpis']['montant_recouvre']
                        objectif = enriched['kpis']['objectif']
                        if objectif > 0:
                            enriched['kpis']['atteinte_objectif'] = (total_r / objectif) * 100
                            enriched['kpis']['depassement_objectif'] = total_r - objectif
                    
                    # ══════════════════════════════════════════════════════════
                    # 📊 KPIs AVANCÉS POUR DÉCIDEURS (concentration, dispersion, risques)
                    # ══════════════════════════════════════════════════════════
                    try:
                        # Identifier la colonne de valeur principale
                        main_val_key = recouvre_key or declare_key
                        if main_val_key and len(execution_result) >= 3:
                            values = [float(row.get(main_val_key, 0) or 0) for row in execution_result]
                            values_sorted = sorted(values, reverse=True)
                            total_val = sum(values)
                            n = len(values)
                            
                            if total_val > 0:
                                # Moyenne et écart-type
                                moyenne = total_val / n
                                variance = sum((v - moyenne) ** 2 for v in values) / n
                                ecart_type = variance ** 0.5
                                
                                enriched['kpis']['moyenne_par_entite'] = moyenne
                                enriched['kpis']['valeur_max'] = max(values)
                                enriched['kpis']['valeur_min'] = min(values)
                                
                                # Concentration Top 3 (% poids des 3 premiers)
                                top3_sum = sum(values_sorted[:3])
                                enriched['kpis']['concentration_top3'] = (top3_sum / total_val) * 100
                                
                                # Qualification de la performance globale
                                taux = enriched['kpis'].get('taux_recouvrement', 0)
                                if taux >= 105:
                                    enriched['kpis']['qualification_performance'] = 'SURPERFORMANCE'
                                elif taux >= 95:
                                    enriched['kpis']['qualification_performance'] = 'SATISFAISANTE'
                                elif taux >= 80:
                                    enriched['kpis']['qualification_performance'] = 'MODÉRÉE'
                                elif taux > 0:
                                    enriched['kpis']['qualification_performance'] = 'CRITIQUE'
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur calcul KPIs avancés: {e}")
                    
                    # ══════════════════════════════════════════════════════════
                    # 🎯 RECOMMANDATIONS STRATÉGIQUES AUTOMATIQUES (sans appel API)
                    # ══════════════════════════════════════════════════════════
                    try:
                        enriched['recommandations_strategiques'] = self._generate_local_strategic_recommendations(
                            enriched['kpis'], execution_result, query
                        )
                        enriched['alertes_decisionnelles'] = self._generate_local_alerts(
                            enriched['kpis'], execution_result, query
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur recommandations locales: {e}")
                
            return enriched
            
        except Exception as e:
            logger.warning(f" Erreur enrichissement: {e}")
            return enriched
    
    def _detect_query_type(self, query: str) -> str:
        """Détection du type de requête pour contexte"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['top', 'meilleur', 'plus grand']):
            return 'classement'
        elif any(word in query_lower for word in ['évolution', 'temporel', 'mois', 'année']):
            return 'temporel'
        elif any(word in query_lower for word in ['performance', 'efficacité', 'taux']):
            return 'performance'
        elif any(word in query_lower for word in ['écart', 'différence', 'comparaison']):
            return 'comparaison'
        else:
            return 'general'
    
    def _generate_local_strategic_recommendations(self, kpis: Dict, data: list, query: str) -> list:
        """🎯 Recommandations stratégiques pour décideurs (Ministre, DG) — SANS appel API"""
        recommandations = []
        
        try:
            taux = kpis.get('taux_recouvrement', 0)
            total_declare = kpis.get('montant_declare', 0)
            total_recouvre = kpis.get('montant_recouvre', 0)
            concentration = kpis.get('concentration_top3', 0)
            
            # 1. Recommandation sur le taux de recouvrement
            if 0 < taux < 80:
                ecart_optimal = total_declare * 0.95 - total_recouvre
                recommandations.append({
                    'priorite': 'CRITIQUE',
                    'domaine': 'Recouvrement',
                    'action': 'Mettre en œuvre un plan de redressement fiscal d\'urgence',
                    'detail': f"Le taux de {taux:.1f}% est très en deçà de la cible de 95%. Un gain de {ecart_optimal:,.0f} FCFA est possible en renforçant le contrôle et les relances.",
                    'impact_estime': f"+{ecart_optimal:,.0f} FCFA",
                    'responsable': 'Direction du Recouvrement'
                })
            elif 80 <= taux < 95:
                ecart_optimal = total_declare * 0.95 - total_recouvre
                recommandations.append({
                    'priorite': 'HAUTE',
                    'domaine': 'Optimisation',
                    'action': 'Renforcer les procédures de relance et de suivi des contribuables défaillants',
                    'detail': f"Un effort ciblé permettrait de récupérer jusqu'à {ecart_optimal:,.0f} FCFA supplémentaires pour atteindre le taux cible de 95%.",
                    'impact_estime': f"+{ecart_optimal:,.0f} FCFA",
                    'responsable': 'Bureaux de recouvrement'
                })
            elif taux >= 105:
                recommandations.append({
                    'priorite': 'MOYENNE',
                    'domaine': 'Bonnes pratiques',
                    'action': 'Documenter et capitaliser les facteurs de surperformance',
                    'detail': f"Le surplus de {total_recouvre - total_declare:,.0f} FCFA (taux {taux:.1f}%) traduit une efficacité remarquable. Identifier et diffuser les bonnes pratiques.",
                    'impact_estime': 'Pérennisation de la performance',
                    'responsable': 'Direction de la Stratégie'
                })
            
            # 2. Recommandation sur la concentration
            if concentration > 50:
                recommandations.append({
                    'priorite': 'HAUTE',
                    'domaine': 'Risque systémique',
                    'action': 'Diversifier l\'assiette fiscale pour réduire la dépendance aux grands contribuables',
                    'detail': f"Avec {concentration:.1f}% du total concentré sur 3 entités, une défaillance d'un seul grand contribuable menacerait l'équilibre budgétaire.",
                    'impact_estime': 'Réduction du risque fiscal',
                    'responsable': 'Direction de la Politique Fiscale'
                })
            
            # 3. Recommandation sur les disparités entre entités
            val_max = kpis.get('valeur_max', 0)
            val_min = kpis.get('valeur_min', 0)
            if val_max > 0 and val_min > 0 and val_max / val_min > 10:
                recommandations.append({
                    'priorite': 'MOYENNE',
                    'domaine': 'Équité territoriale',
                    'action': 'Analyser les causes des disparités entre entités et renforcer les bureaux sous-performants',
                    'detail': f"Le plus gros contributeur ({val_max:,.0f} FCFA) rapporte {val_max/val_min:.0f} fois plus que le plus petit ({val_min:,.0f} FCFA). Un rééquilibrage des moyens pourrait améliorer la performance globale.",
                    'impact_estime': 'Harmonisation des performances',
                    'responsable': 'Direction de l\'Administration'
                })
            
            # 4. Recommandation basée sur le contexte de la requête
            query_lower = query.lower()
            if any(w in query_lower for w in ['contribuable', 'top', 'plus grand']):
                recommandations.append({
                    'priorite': 'HAUTE',
                    'domaine': 'Gestion des grands comptes',
                    'action': 'Mettre en place un suivi personnalisé des principaux contribuables identifiés',
                    'detail': 'Désigner un gestionnaire de compte dédié pour chacun des 10 premiers contribuables afin de sécuriser les recettes et anticiper les risques de défaillance.',
                    'impact_estime': 'Sécurisation des recettes principales',
                    'responsable': 'Direction des Grandes Entreprises'
                })
            
            if not recommandations:
                recommandations.append({
                    'priorite': 'INFO',
                    'domaine': 'Suivi général',
                    'action': 'Maintenir la veille sur les indicateurs de performance fiscale',
                    'detail': 'Les indicateurs actuels sont dans les normes. Continuer le suivi périodique pour détecter toute déviation.',
                    'impact_estime': 'Maintien de la performance',
                    'responsable': 'Direction Générale'
                })
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur recommandations locales: {e}")
        
        return recommandations
    
    def _generate_local_alerts(self, kpis: Dict, data: list, query: str) -> list:
        """🚨 Alertes décisionnelles automatiques — SANS appel API"""
        alertes = []
        
        try:
            taux = kpis.get('taux_recouvrement', 0)
            total_declare = kpis.get('montant_declare', 0)
            total_recouvre = kpis.get('montant_recouvre', 0)
            concentration = kpis.get('concentration_top3', 0)
            
            # Alerte taux de recouvrement
            if 0 < taux < 80:
                perte = total_declare - total_recouvre
                alertes.append({
                    'niveau': 'CRITIQUE',
                    'icone': '🔴',
                    'titre': 'Taux de recouvrement critique',
                    'message': f"Le taux de recouvrement de {taux:.1f}% est alarmant. Perte potentielle : {perte:,.0f} FCFA.",
                    'action_requise': 'Intervention immédiate de la Direction Générale'
                })
            elif 80 <= taux < 90:
                perte = total_declare - total_recouvre
                alertes.append({
                    'niveau': 'ATTENTION',
                    'icone': '🟠',
                    'titre': 'Taux de recouvrement sous-optimal',
                    'message': f"Le taux de {taux:.1f}% est en deçà de l'objectif de 95%. Manque à gagner : {perte:,.0f} FCFA.",
                    'action_requise': 'Plan d\'action correctif requis'
                })
            
            # Alerte concentration
            if concentration > 60:
                alertes.append({
                    'niveau': 'ATTENTION',
                    'icone': '⚠️',
                    'titre': 'Risque de concentration fiscale',
                    'message': f"Les 3 premières entités représentent {concentration:.1f}% du total. Risque systémique en cas de défaillance.",
                    'action_requise': 'Stratégie de diversification de l\'assiette'
                })
            
            # Alerte montant élevé
            if total_recouvre and total_recouvre > 10_000_000_000:
                alertes.append({
                    'niveau': 'INFO',
                    'icone': '📊',
                    'titre': 'Volume significatif de recettes',
                    'message': f"Le volume de {total_recouvre:,.0f} FCFA représente un enjeu budgétaire majeur nécessitant un suivi renforcé.",
                    'action_requise': 'Rapport de suivi mensuel au Ministre'
                })
            
            # Alerte disparité
            val_max = kpis.get('valeur_max', 0)
            val_min = kpis.get('valeur_min', 0)
            if val_max > 0 and val_min > 0 and val_max / val_min > 20:
                alertes.append({
                    'niveau': 'ATTENTION',
                    'icone': '📉',
                    'titre': 'Forte disparité entre entités',
                    'message': f"L'écart entre le plus gros contribuable ({val_max:,.0f} FCFA) et le plus petit ({val_min:,.0f} FCFA) est considérable, révélant des déséquilibres structurels importants.",
                    'action_requise': 'Audit des entités sous-performantes'
                })
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur alertes locales: {e}")
        
        return alertes
    
    def _fix_polars_syntax(self, code: str) -> str:
        """🔧 Corrige automatiquement les erreurs de syntaxe Polars courantes"""
        import re
        
        # 1. ~pl.col('X') == 'Y' → pl.col('X') != 'Y'
        # Pattern: ~pl.col('...') == '...' ou ~(pl.col('...') == '...')
        code = re.sub(
            r"~pl\.col\(['\"](\w+)['\"]\)\s*==\s*['\"]([^'\"]+)['\"]",
            r"pl.col('\1') != '\2'",
            code
        )
        
        # 2. ~(pl.col('X') == 'Y') → pl.col('X') != 'Y'
        code = re.sub(
            r"~\(pl\.col\(['\"](\w+)['\"]\)\s*==\s*['\"]([^'\"]+)['\"]\)",
            r"pl.col('\1') != '\2'",
            code
        )
        
        # 3. Fix OR operator precedence in .filter()
        # Detect: ... & (condition) | (pl.col(...).is_null()) without proper grouping
        # The | must be grouped with the preceding condition using outer parentheses
        code = re.sub(
            r'(\(pl\.col\([^)]+\)\.[^)]+\))\s*\|\s*(\(pl\.col\([^)]+\)\.is_null\(\)\))',
            r'(\1 | \2)',
            code
        )
        
        # 4. Fix column name DIRECTION_REGIONALE → DIRECTION (actual parquet column name)
        code = code.replace("'DIRECTION_REGIONALE'", "'DIRECTION'")
        code = code.replace('"DIRECTION_REGIONALE"', '"DIRECTION"')
        
        # 5. Fix column name TYPE_IMPOT_TAXE → TAXE_IMPOT_CD (actual parquet column name)
        code = code.replace("'TYPE_IMPOT_TAXE'", "'TAXE_IMPOT_CD'")
        code = code.replace('"TYPE_IMPOT_TAXE"', '"TAXE_IMPOT_CD"')
        
        # 6. Fix TODAY - pl.duration(days=N) → pl.lit(TODAY - timedelta(days=N))
        # TODAY is a Python date, can't subtract a Polars duration from it
        code = re.sub(
            r'TODAY\s*-\s*pl\.duration\(days\s*=\s*(\d+)\)',
            r'pl.lit(TODAY - timedelta(days=\1))',
            code
        )
        # Also fix: pl.lit(TODAY) - pl.duration(days=N) → pl.lit(TODAY - timedelta(days=N))
        code = re.sub(
            r'pl\.lit\(TODAY\)\s*-\s*pl\.duration\(days\s*=\s*(\d+)\)',
            r'pl.lit(TODAY - timedelta(days=\1))',
            code
        )
        
        # 7. Ensure timedelta import exists if used
        if 'timedelta' in code and 'from datetime import' not in code and 'import datetime' not in code:
            code = 'from datetime import timedelta\n' + code
        
        return code
    
    def _fix_duplicate_columns(self, code: str) -> str:
        """🔧 Corrige automatiquement les DuplicateError Polars.
        Supprime les colonnes dans .agg() qui sont déjà présentes dans .group_by().
        Gère aussi les .select() avec doublons après .with_columns().
        """
        import re
        
        try:
            # 1. Trouver les colonnes dans group_by
            gb_matches = re.findall(r"\.group_by\(\[?([^\]\)]+)\]?\)", code)
            if not gb_matches:
                # Pas de group_by → vérifier si .select() ou .with_columns() crée des doublons
                # Quand il n'y a pas de group_by, les colonnes BUREAU, SOURCE etc. existent déjà
                # Supprimer les .with_columns() ou .select() qui re-créent des colonnes existantes
                native_cols = ['BUREAU', 'SOURCE', 'DIRECTION', 'LIBELLE', 
                              'NATURE', 'CATEGORIE', 'TAXE_IMPOT_CD', 'ID_CONTRIBUABLE']
                for col_name in native_cols:
                    # Supprimer pl.col('COL').first().alias('COL') ou pl.col('COL').alias('COL') hors agg
                    pattern = rf",?\s*pl\.col\(['\"{col_name}['\"]\)\.first\(\)\.alias\(['\"][^'\"]*['\"]\)"
                    code = re.sub(pattern, '', code)
                return code
            
            # 2. Extraire les noms de colonnes du group_by
            gb_text = gb_matches[0]
            gb_cols = re.findall(r"['\"]([^'\"]+)['\"]", gb_text)
            
            if not gb_cols:
                return code
            
            # 3. Pour chaque colonne du group_by, supprimer son .first().alias() dans .agg()
            for col_name in gb_cols:
                # Pattern: pl.col('COL').first().alias('COL') ou pl.col('COL').first().alias('AUTRE')
                pattern = rf",?\s*pl\.col\(['\"{col_name}['\"]\)\.first\(\)\.alias\(['\"][^'\"]*['\"]\)"
                code = re.sub(pattern, '', code)
                # Pattern variante: pl.col("COL").first().alias("COL")
                pattern2 = rf"pl\.col\(['\"{col_name}['\"]\)\.first\(\)\.alias\(['\"][^'\"]*['\"]\),?\s*"
                code = re.sub(pattern2, '', code)
            
            # 4. Nettoyer les virgules orphelines dans .agg([, ...]) ou .agg([..., ])
            code = re.sub(r'\.agg\(\[\s*,', '.agg([', code)
            code = re.sub(r',\s*\]\)', '])', code)
            code = re.sub(r',\s*,', ',', code)
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur fix_duplicate_columns: {e}")
        
        return code
    
    def _execute_code(self, code: str) -> Any:
        """Exécution sécurisée avec environnement minimal"""
        try:
            # 🔧 PRÉ-TRAITEMENT: Corriger les erreurs de syntaxe Polars courantes
            code = self._fix_polars_syntax(code)
            
            # 🔧 PRÉ-TRAITEMENT: Supprimer les colonnes dupliquées (group_by + agg)
            code = self._fix_duplicate_columns(code)
            
            # Charger les données directement
            data_path = "srmt_data_2020_2025.parquet"
            if os.path.exists(data_path):
                data = pl.scan_parquet(data_path)
            else:
                return "Erreur: Fichier de données non trouvé"
            
            # Créer un environnement minimal avec les imports nécessaires
            safe_globals = {
                '__builtins__': __builtins__,
                'pl': pl,
                'data': data,
                'datetime': datetime,
                'date': date,
                'timedelta': timedelta,
                'TODAY': date.today(),
            }
            
            local_vars = {}
            exec(code, safe_globals, local_vars)
            
            if local_vars:
                result = list(local_vars.values())[-1]
                return self._serialize_result(result)
            else:
                return "Code exécuté avec succès"
                
        except SyntaxError as e:
            # Erreur de syntaxe Python
            error_msg = f"Erreur d'exécution: SyntaxError à la ligne {e.lineno}: {e.msg}\nProblème près de: {e.text}"
            logger.error(error_msg)
            
            #  Apprentissage automatique
            if hasattr(self, 'learning_system') and self.learning_system:
                self.learning_system.learn_from_error(
                    error_message=f"SyntaxError: {e.msg}",
                    error_type="SyntaxError",
                    failed_code=code[:200] + "..." if len(code) > 200 else code
                )
            
            return error_msg
            
        except AttributeError as e:
            # Erreur de méthode/attribut (ex: groupby vs group_by)
            error_details = str(e)
            suggestions = []
            correction = None
            
            if "'groupby'" in error_details or "has no attribute 'groupby'" in error_details:
                suggestions.append("REMPLACER .groupby() par .group_by()")
                correction = "Utiliser .group_by() au lieu de .groupby()"
            if "'agg'" in error_details or "has no attribute 'agg'" in error_details:
                suggestions.append("UTILISER .agg() seulement APRS .group_by()")
                correction = "Utiliser .agg() après .group_by()"
            if "'desc'" in error_details:
                suggestions.append("REMPLACER .desc() par .sort(descending=True)")
                correction = "Utiliser .sort(descending=True) au lieu de .desc()"
            
            correction_hint = " | ".join(suggestions) if suggestions else "Vérifie les noms de méthodes Polars"
            error_msg = f"Erreur d'exécution: AttributeError - {error_details}\nCORRECTION: {correction_hint}"
            logger.error(error_msg)
            
            #  Apprentissage automatique
            if hasattr(self, 'learning_system') and self.learning_system:
                self.learning_system.learn_from_error(
                    error_message=error_details,
                    error_type="AttributeError",
                    failed_code=code[:200] + "..." if len(code) > 200 else code,
                    correction=correction
                )
            
            return error_msg
            
        except FileNotFoundError as e:
            # Erreur de fichier inexistant (l'IA essaie de lire un fichier)
            error_msg = f"Erreur d'exécution: FileNotFoundError - {str(e)}"
            error_msg += "\nCORRECTION: UTILISE la variable 'data' déjà chargée, ne lis pas de fichiers externes"
            error_msg += "\nERREUR INTERDIT: pl.read_csv('fichier.csv')"
            error_msg += "\nOK CORRECT: data (variable Polars LazyFrame pré-chargée)"
            logger.error(error_msg)
            
            #  Apprentissage automatique
            if hasattr(self, 'learning_system') and self.learning_system:
                self.learning_system.learn_from_error(
                    error_message=str(e),
                    error_type="FileNotFoundError",
                    failed_code=code[:200] + "..." if len(code) > 200 else code,
                    correction="Utiliser la variable 'data' au lieu de lire des fichiers"
                )
            
            return error_msg
            
        except KeyError as e:
            # Erreur de colonne inexistante
            error_msg = f"Erreur d'exécution: KeyError - Colonne {str(e)} n'existe pas\nColonnes disponibles dans le schéma ci-dessus"
            logger.error(error_msg)
            
            #  Apprentissage automatique
            if hasattr(self, 'learning_system') and self.learning_system:
                self.learning_system.learn_from_error(
                    error_message=f"Colonne {str(e)} n'existe pas",
                    error_type="KeyError",
                    failed_code=code[:200] + "..." if len(code) > 200 else code,
                    correction="Vérifier les noms de colonnes dans le schéma"
                )
            
            return error_msg
            
        except TypeError as e:
            error_details = str(e)
            correction = None
            
            # TOOL CORRECTION CRITIQUE: Erreur de méthode de date non appelée
            if ">=" in error_details and "method" in error_details and "int" in error_details:
                correction = "Appeler les méthodes de date avec des parenthèses: .dt.year() au lieu de .dt.year"
                error_msg = f"Erreur d'exécution: TypeError - {error_details}\nCORRECTION: Méthode de date non appelée avec des parenthèses\n"
                error_msg += "PROBLME: pl.col('DATE').dt.year >= 2025 (year est une méthode, pas une propriété)\n"
                error_msg += "SOLUTION: pl.col('DATE').dt.year() >= 2025\n"
                error_msg += "AUTRES MTHODES: .dt.month() .dt.day() .dt.hour() etc.\n"
                error_msg += "ERREUR INTERDIT: .dt.year >= 2025\n"
                error_msg += "OK CORRECT: .dt.year() >= 2025"
                logger.error(error_msg)
            
            # Erreur d'ellipsis dans DataFrame
            elif "ellipsis" in error_details and "DataFrame constructor" in error_details:
                correction = "Supprimer les ellipsis (...) et utiliser la variable 'data' existante"
                error_msg = f"Erreur d'exécution: TypeError - {error_details}\nCORRECTION: {correction}"
                error_msg += "\nERREUR INTERDIT: pl.DataFrame([...]) ou pl.DataFrame(...)"
                error_msg += "\nOK CORRECT: data (variable LazyFrame déjà disponible)"
            # Autres erreurs de sort/reverse
            elif "reverse" in error_details and "sort" in error_details:
                correction = "Utiliser descending=True au lieu de reverse=True dans .sort()"
                error_msg = f"Erreur d'exécution: TypeError - {error_details}\nCORRECTION: {correction}"
            elif "descending" in error_details and "Col.__call__" in error_details:
                correction = "Ne pas passer descending à pl.col(), l'utiliser dans .sort()"
                error_msg = f"Erreur d'exécution: TypeError - {error_details}\nCORRECTION: {correction}"
            else:
                # Erreur de type générique
                error_msg = f"Erreur d'exécution: TypeError - {error_details}\nVérifie les arguments des fonctions Polars"
            
            logger.error(error_msg)
            
            #  Apprentissage automatique
            if hasattr(self, 'learning_system') and self.learning_system:
                self.learning_system.learn_from_error(
                    error_message=error_details,
                    error_type="TypeError",
                    failed_code=code[:200] + "..." if len(code) > 200 else code,
                    correction=correction
                )
            
            return error_msg
            
        except ValueError as e:
            # Erreur de valeur
            error_msg = f"Erreur d'exécution: ValueError - {str(e)}"
            logger.error(error_msg)
            
            #  Apprentissage automatique
            if hasattr(self, 'learning_system') and self.learning_system:
                self.learning_system.learn_from_error(
                    error_message=str(e),
                    error_type="ValueError",
                    failed_code=code[:200] + "..." if len(code) > 200 else code
                )
            
            return error_msg
            
        except Exception as e:
            # Capture InvalidOperationError de Polars et autres erreurs
            error_type = type(e).__name__
            error_details = str(e)
            correction = None
            
            # Détection erreur LazyFrame en contexte booléen
            if 'truth value of a LazyFrame is ambiguous' in error_details:
                correction = "Appeler .collect() AVANT toute vérification if/and/or"
                error_msg = f"Erreur d'exécution: {error_type} - LazyFrame utilisé en contexte booléen\n"
                error_msg += "CORRECTION: Appeler .collect() AVANT toute vérification if/and/or\n"
                error_msg += "ERREUR INTERDIT: if resultat: ou resultat and autre\n"
                error_msg += "OK CORRECT: resultat = query.collect().to_dicts()\n"
                error_msg += "OK CORRECT: if len(resultat) > 0:\n"
                error_msg += f"Erreur complète: {error_details}"
                logger.error(error_msg)
            
            # Détection DuplicateError (colonne dupliquée dans group_by + agg)
            elif 'DuplicateError' in error_type or 'has more than one occurrence' in error_details:
                # Tentative de correction automatique
                fixed_code = self._fix_duplicate_columns(code)
                if fixed_code != code:
                    logger.info("🔧 Correction automatique DuplicateError: suppression colonnes dupliquées")
                    fix_result = self._execute_code(fixed_code)
                    if not (isinstance(fix_result, str) and fix_result.startswith("Erreur")):
                        return fix_result
                
                # Extraire le nom de la colonne dupliquée
                dup_col = re.search(r"column with name '(\w+)' has more than one occurrence", error_details)
                dup_col_name = dup_col.group(1) if dup_col else 'INCONNUE'
                correction = f"Supprimer pl.col('{dup_col_name}').first().alias('{dup_col_name}') du .agg() car '{dup_col_name}' est déjà dans group_by() ou existe déjà"
                error_msg = f"Erreur d'exécution: DuplicateError - La colonne '{dup_col_name}' apparaît en double\n"
                error_msg += f"CORRECTION: {correction}\n"
                error_msg += "❗ RÈGLE: NE JAMAIS mettre dans .agg() une colonne qui est DÉJÀ dans group_by()\n"
                error_msg += f"INTERDIT: .group_by('{dup_col_name}').agg([..., pl.col('{dup_col_name}').first().alias('{dup_col_name}')])\n"
                error_msg += f"CORRECT: .group_by('{dup_col_name}').agg([...]) — {dup_col_name} apparaît automatiquement dans le résultat"
                logger.error(error_msg)
            
            # Détection erreur de date Polars
            elif 'InvalidOperationError' in error_type and 'date/datetime/time' in error_details:
                correction = "Utiliser .dt.year(), .dt.month(), .dt.day() pour filtrer les dates"
                error_msg = f"Erreur d'exécution: {error_type} - Comparaison de date invalide\n"
                error_msg += "CORRECTION: Pour filtrer par date, utilise .dt.year(), .dt.month(), .dt.day()\n"
                error_msg += "EXEMPLE: pl.col('DATE_RECOUVREMENT').dt.year() == 2024\n"
                error_msg += "EXEMPLE: pl.col('DATE_RECOUVREMENT').dt.month() == 12\n"
                error_msg += "JAMAIS: pl.col('DATE').dt.date() >= '2024-12-01' (INTERDIT)\n"
                error_msg += f"Erreur complète: {error_details}"
                logger.error(error_msg)
            else:
                error_msg = f"Erreur d'exécution: {error_type} - {error_details}"
                logger.error(error_msg)
            
            #  Apprentissage automatique
            if hasattr(self, 'learning_system') and self.learning_system:
                self.learning_system.learn_from_error(
                    error_message=error_details,
                    error_type=error_type,
                    failed_code=code[:200] + "..." if len(code) > 200 else code,
                    correction=correction
                )
            
            return error_msg


    def _serialize_result(self, result: Any) -> Any:
        """Sérialisation récursive et robuste des résultats avec nettoyage JSON"""
        try:
            serialized = self._serialize_raw(result)
            return self._clean_json_values(serialized)
        except Exception as e:
            logger.error(f"Erreur sérialisation: {e}")
            return str(result)

    def _clean_json_values(self, obj: Any) -> Any:
        """Nettoie itérativement les valeurs invalides pour JSON (Infinity, NaN)"""
        if isinstance(obj, float):
            if math.isinf(obj) or math.isnan(obj):
                return None
            return obj
        elif isinstance(obj, dict):
            return {k: self._clean_json_values(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_json_values(v) for v in obj]
        return obj

    def _serialize_raw(self, result: Any) -> Any:
        """Conversion brute des types complexes vers types Python de base"""
        # Gestion Polars DataFrame
        if isinstance(result, pl.DataFrame):
            return result.to_dicts()

        # Gestion Polars Series -> list
        elif isinstance(result, pl.Series):
            return result.to_list()
            
        # Gestion DataFrame Pandas (Legacy / Fallback)
        elif 'pandas' in str(type(result)):
            result.replace([np.inf, -np.inf], None, inplace=True)
            result = result.where(pd.notnull(result), None)
            for col in result.columns:
                if pd.api.types.is_datetime64_any_dtype(result[col]):
                    result[col] = result[col].astype(str)
            return result.to_dict('records')
            
        # Gestion Numpy
        elif isinstance(result, (np.int64, np.int32, np.int16, np.int8, np.integer)):
            return int(result)
        elif isinstance(result, (np.float64, np.float32, np.floating)):
            return float(result)
        elif isinstance(result, np.ndarray):
            return [self._serialize_raw(x) for x in result.tolist()]
            
        # Types date/time
        elif isinstance(result, (datetime, date)):
            return result.isoformat()
            
        # Gestion Liste/Tuple (Récursif)
        elif isinstance(result, (list, tuple)):
            return [self._serialize_raw(item) for item in result]
            
        # Gestion Dictionnaire (Récursif)
        elif isinstance(result, dict):
            return {str(k): self._serialize_raw(v) for k, v in result.items()}
            
        return result
    
    def _format_explanation(self, query: str, result: Any) -> str:
        """Explication formatée"""
        if isinstance(result, list) and result:
            summary = f"DATA {len(result)} enregistrements trouvés"
        elif isinstance(result, dict):
            summary = f"CHART {len(result)} éléments analysés"
        else:
            summary = "OK Analyse terminée"
        
        return f"""**Analyse SRMT Business Intelligence**

**Requête:** {query}

**Résultat:** {summary}

L'analyse a été effectuée selon les standards SRMT. Consultez les données ci-dessous pour plus de détails."""

def create_production_app() -> Flask:
    """Application Flask optimisée pour production"""
    
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', os.urandom(24).hex()),
        JSON_SORT_KEYS=False
    )
    
    # Configuration du cache
    cache = None
    if CACHE_AVAILABLE:
        try:
            cache = Cache(app, config={'CACHE_TYPE': 'simple'})
            # Cache activé silencieusement
        except Exception as e:
            logger.warning(f"Cache non disponible: {e}")
    
    # Initialisation des composants
    config = ProductionConfig()
    # Initialisation silencieuse
    
    data_loader = OptimizedDataLoader(config)
    data, data_summary = data_loader.load_data()
    rag_system = ProductionRAGSystem(data_loader.data)  # Utiliser data en lazy
    ai_engine = ProductionAIEngine(
        config, 
        rag_system, 
        data_summary, 
        data_loader.aggregated_tables,
        data_loader.lookup_index  # Passer le lookup index
    )
    
    # Routes
    @app.route('/')
    def index():
        """Interface principale"""
        try:
            return render_template_string(
                open(os.path.join(os.path.dirname(__file__), 'templates', 'srmt_production.html'), encoding='utf-8').read(),
                data_summary=data_summary,
                total_records=len(data_loader.data_materialized),
                config=config
            )
        except Exception as e:
            logger.error(f"Erreur rendu template: {e}")
            return f"CRITICAL ERROR: {str(e)}", 500
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_endpoint():
        """API d'analyse principale"""
        try:
            data_input = request.get_json()
            if not data_input or 'question' not in data_input:
                return jsonify({'error': 'Question manquante'}), 400
            
            question = data_input['question'].strip()
            if not question:
                return jsonify({'error': 'Question vide'}), 400
            
            # 🤖 Récupérer le modèle sélectionné (optionnel)
            selected_model = data_input.get('model', None)
            if selected_model:
                # Changer temporairement le modèle pour cette requête
                original_model = ai_engine.config.MODEL_NAME
                ai_engine.config.MODEL_NAME = selected_model
                logger.info(f"🤖 Utilisation du modèle: {selected_model}")
            
            # Analyse
            result = ai_engine.analyze_query(question)
            
            # Restaurer le modèle original si changé
            if selected_model:
                ai_engine.config.MODEL_NAME = original_model
            
            # Vérifier si résultat contient une erreur
            if 'error' in result and result['error']:
                error_type = result['error']
                
                # Timeout global
                if 'timeout' in error_type.lower():
                    logger.warning(f"⏱️ Timeout détecté: {error_type}")
                    return jsonify(result), 408  # Request Timeout
                
                # Erreur de connexion API
                if 'connexion' in error_type.lower() or 'connection' in error_type.lower():
                    logger.error(f"🚫 Erreur de connexion: {error_type}")
                    return jsonify(result), 503  # Service Unavailable
                
                # Autres erreurs
                logger.error(f"❌ Erreur d'analyse: {error_type}")
                return jsonify(result), 500  # Internal Server Error
            
            # Succès
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Erreur endpoint analyse: {e}")
            return jsonify({'error': 'Erreur interne', 'message': str(e)}), 500
    
    @app.route('/query', methods=['POST'])
    def query_endpoint():
        """Route de compatibilité pour l'interface - redirige vers analyze"""
        try:
            data_input = request.get_json()
            if not data_input or 'query' not in data_input:
                return jsonify({'error': 'Requête manquante'}), 400
            
            # Convertir le format query vers question
            question = data_input['query'].strip()
            if not question:
                return jsonify({'error': 'Requête vide'}), 400
            
            # Analyse avec l'IA engine
            result = ai_engine.analyze_query(question)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Erreur endpoint query: {e}")
            return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

    @app.route('/api/models')
    def list_models():
        """Liste des modèles NIM disponibles"""
        return jsonify({
            'current': ai_engine.config.MODEL_NAME,
            'available': [
                {
                    'id': 'meta/llama-3.1-8b-instruct',
                    'name': 'Llama 3.1 8B',
                    'description': 'Rapide et efficace',
                    'speed': 'fast',
                    'quality': 'good',
                    'category': 'general'
                },
                {
                    'id': 'mistralai/mistral-7b-instruct-v0.3',
                    'name': 'Mistral 7B',
                    'description': 'Rapide et polyvalent',
                    'speed': 'fast',
                    'quality': 'good',
                    'category': 'general'
                },
                {
                    'id': 'qwen/qwen2.5-coder-32b-instruct',
                    'name': 'Qwen Coder 32B',
                    'description': 'Spécialisé en codage',
                    'speed': 'medium',
                    'quality': 'excellent',
                    'category': 'coding'
                },
                {
                    'id': 'qwen/qwq-32b-preview',
                    'name': 'Qwen QwQ 32B',
                    'description': 'Raisonnement avancé',
                    'speed': 'medium',
                    'quality': 'excellent',
                    'category': 'reasoning'
                },
                {
                    'id': 'meta/llama-3.1-70b-instruct',
                    'name': 'Llama 3.1 70B',
                    'description': 'Précis et équilibré',
                    'speed': 'medium',
                    'quality': 'excellent',
                    'category': 'general'
                },
                {
                    'id': 'nvidia/nemotron-4-340b-instruct',
                    'name': 'Nemotron 340B',
                    'description': 'Très puissant',
                    'speed': 'slow',
                    'quality': 'excellent',
                    'category': 'general'
                },
                {
                    'id': 'meta/llama-3.1-405b-instruct',
                    'name': 'Llama 3.1 405B',
                    'description': 'Ultra performant',
                    'speed': 'very_slow',
                    'quality': 'outstanding',
                    'category': 'general'
                }
            ]
        })
    
    @app.route('/api/health')
    def health_check():
        """Vérification de l'état"""
        return jsonify({
            'status': 'healthy',
            'data_loaded': True,
            'total_records': len(data_loader.data_materialized),
            'memory_usage_mb': round(data_summary['memory_usage_mb'], 2),
            'production_mode': config.PRODUCTION_MODE,
            'current_model': ai_engine.config.MODEL_NAME
        })
    
    @app.route('/api/stats')
    def stats():
        """Statistiques système"""
        return jsonify(data_summary)
    
    @app.route('/api/learning/stats')
    def learning_stats():
        """DATA Statistiques d'apprentissage IA"""
        if hasattr(ai_engine, 'learning_system') and ai_engine.learning_system:
            return jsonify(ai_engine.learning_system.get_learning_stats())
        return jsonify({'error': 'Learning system not available'}), 503
    
    @app.route('/api/cache/clear', methods=['POST'])
    def clear_cache():
        """🗑️ Vider le cache des requêtes pour forcer la régénération"""
        try:
            cache_size = len(ai_engine.query_cache)
            ai_engine.query_cache.clear()
            logger.info(f"🗑️ Cache vidé: {cache_size} entrées supprimées")
            return jsonify({
                'status': 'success',
                'message': f'Cache vidé: {cache_size} requêtes supprimées',
                'entries_cleared': cache_size
            })
        except Exception as e:
            logger.error(f"Erreur vidage cache: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/cache/stats')
    def cache_stats():
        """📊 Statistiques du cache"""
        try:
            return jsonify({
                'total_entries': len(ai_engine.query_cache),
                'cache_ttl_seconds': ai_engine.cache_ttl,
                'max_entries': 100
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/learning/reset', methods=['POST'])
    def reset_learning():
        """ Réinitialisation de l'apprentissage"""
        if hasattr(ai_engine, 'learning_system') and ai_engine.learning_system:
            ai_engine.learning_system.reset_cache()
            return jsonify({'status': 'success', 'message': 'Cache d\'apprentissage réinitialisé'})
        return jsonify({'error': 'Learning system not available'}), 503
    
    @app.route('/api/lexfin/chat', methods=['POST'])
    def lexfin_chat():
        """Route pour le chatbot LexFin intégré"""
        try:
            data_input = request.get_json()
            message = data_input.get('message', '').strip()
            
            if not message:
                return jsonify({'status': 'error', 'error': 'Message vide'}), 400
            
            # Appel à l'API LexFin NIM avec timeout réduit
            lexfin_url = "https://srmt-documind-srmtbi.apps.data-ai.heritage.africa/chat"
            
            import requests as req
            response = req.post(
                lexfin_url,
                json={'message': message},
                timeout=30  # Timeout réduit à 30s
            )
            
            if response.status_code == 200:
                result = response.json()
                return jsonify({
                    'status': 'success',
                    'response': result.get('response', ''),
                    'references': result.get('references', [])
                })
            else:
                logger.warning(f"LexFin API erreur {response.status_code}")
                return jsonify({
                    'status': 'error',
                    'error': f'Erreur API: {response.status_code}'
                }), response.status_code
                
        except req.Timeout:
            logger.error("LexFin API timeout après 30s")
            return jsonify({
                'status': 'error', 
                'error': 'Timeout - L\'API LexFin ne répond pas. Vérifiez la connexion.'
            }), 504
        except req.ConnectionError:
            logger.error("LexFin API connexion impossible")
            return jsonify({
                'status': 'error',
                'error': 'Impossible de contacter l\'API LexFin. Service indisponible.'
            }), 503
        except Exception as e:
            logger.error(f"Erreur LexFin chat: {str(e)}")
            return jsonify({'status': 'error', 'error': str(e)}), 500
    
    return app

# Template HTML optimisé
PRODUCTION_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SRMT Business Intelligence - Plateforme d'Analyse Fiscale</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
        .glass { 
            background: rgba(255, 255, 255, 0.08); 
            backdrop-filter: blur(12px); 
            border: 1px solid rgba(255, 255, 255, 0.15); 
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .gradient-bg { 
            background: linear-gradient(135deg, #0f1419 0%, #1a202c 25%, #2d3748 50%, #4a5568 100%);
            min-height: 100vh;
        }
        .gradient-card {
            background: linear-gradient(145deg, rgba(76, 175, 80, 0.1), rgba(33, 150, 243, 0.1));
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .result-scroll { max-height: 600px; overflow-y: auto; }
        .loading { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .pulse-animation { animation: pulse 2s infinite; }
        
        /* Responsive optimizations */
        @media (max-width: 768px) {
            .glass { padding: 1rem; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .quick-actions { flex-direction: column; gap: 0.5rem; }
        }
        
        /* Smooth transitions */
        * { transition: all 0.3s ease; }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.1); }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.3); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.5); }
        
        /* Enhanced table styles */
        .data-table { border-collapse: separate; border-spacing: 0; }
        .data-table th { 
            background: rgba(59, 130, 246, 0.1); 
            border: 1px solid rgba(59, 130, 246, 0.2);
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .data-table td { 
            border: 1px solid rgba(255, 255, 255, 0.1); 
            transition: background-color 0.2s ease;
        }
        .data-table tbody tr:hover { background-color: rgba(59, 130, 246, 0.05); }
        
        /* Button enhancements */
        .btn-primary {
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
        }
    </style>
</head>
<body class="gradient-bg">
    <!-- Enhanced Header -->
    <header class="glass border-b border-white border-opacity-20 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <div class="p-2 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600">
                        <i class="fas fa-chart-network text-2xl text-white"></i>
                    </div>
                    <div>
                        <h1 class="text-xl sm:text-2xl lg:text-3xl font-bold text-white">SRMT Business Intelligence</h1>
                        <p class="text-blue-200 text-xs sm:text-sm">Plateforme d'Analyse Fiscale Intelligente</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2 sm:space-x-4">
                    <div class="hidden sm:flex items-center space-x-3 text-white text-xs sm:text-sm">
                        <span class="glass px-2 sm:px-3 py-1 rounded-full">
                            <i class="fas fa-database mr-1"></i>{{ "{:,}".format(total_records) }}
                        </span>
                        {% if config.PRODUCTION_MODE %}
                        <span class="bg-green-600 px-2 sm:px-3 py-1 rounded-full font-medium">
                            <i class="fas fa-shield-check mr-1"></i>PRODUCTION
                        </span>
                        {% else %}
                        <span class="bg-amber-600 px-2 sm:px-3 py-1 rounded-full font-medium">
                            <i class="fas fa-code mr-1"></i>DEV
                        </span>
                        {% endif %}
                    </div>
                    <button class="glass p-2 rounded-lg hover:bg-white hover:bg-opacity-10 text-white">
                        <i class="fas fa-cog"></i>
                    </button>
                </div>
            </div>
        </div>
    </header>

    <!-- Enhanced Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <!-- Enhanced Stats Dashboard -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6 mb-6 sm:mb-8">
            <div class="gradient-card rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:scale-105 transition-transform">
                <div class="flex items-center">
                    <div class="p-2 sm:p-3 rounded-full bg-blue-500 bg-opacity-20">
                        <i class="fas fa-database text-blue-400 text-xl sm:text-2xl"></i>
                    </div>
                    <div class="ml-3 sm:ml-4">
                        <p class="text-blue-200 text-xs sm:text-sm font-medium">Enregistrements</p>
                        <p class="text-lg sm:text-2xl font-bold text-white">{{ "{:,}".format(total_records) }}</p>
                    </div>
                </div>
            </div>
            
            <div class="gradient-card rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:scale-105 transition-transform">
                <div class="flex items-center">
                    <div class="p-2 sm:p-3 rounded-full bg-emerald-500 bg-opacity-20">
                        <i class="fas fa-columns text-emerald-400 text-xl sm:text-2xl"></i>
                    </div>
                    <div class="ml-3 sm:ml-4">
                        <p class="text-blue-200 text-xs sm:text-sm font-medium">Colonnes</p>
                        <p class="text-lg sm:text-2xl font-bold text-white">{{ data_summary['shape'][1] }}</p>
                    </div>
                </div>
            </div>
            
            <div class="gradient-card rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:scale-105 transition-transform">
                <div class="flex items-center">
                    <div class="p-2 sm:p-3 rounded-full bg-purple-500 bg-opacity-20">
                        <i class="fas fa-brain text-purple-400 text-xl sm:text-2xl"></i>
                    </div>
                    <div class="ml-3 sm:ml-4">
                        <p class="text-blue-200 text-xs sm:text-sm font-medium">IA Engine</p>
                        <p class="text-lg sm:text-2xl font-bold text-white">QWEN</p>
                    </div>
                </div>
            </div>
            
            <div class="gradient-card rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:scale-105 transition-transform">
                <div class="flex items-center">
                    <div class="p-2 sm:p-3 rounded-full bg-orange-500 bg-opacity-20">
                        <i class="fas fa-memory text-orange-400 text-xl sm:text-2xl"></i>
                    </div>
                    <div class="ml-3 sm:ml-4">
                        <p class="text-blue-200 text-xs sm:text-sm font-medium">Mémoire</p>
                        <p class="text-lg sm:text-2xl font-bold text-white">{{ "%.1f" | format(data_summary['memory_usage_mb']) }}MB</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Enhanced AI Query Interface -->
        <div class="glass rounded-2xl p-6 sm:p-8">
            <div class="mb-6 sm:mb-8">
                <div class="flex items-center mb-3">
                    <div class="p-2 rounded-xl bg-gradient-to-r from-green-600 to-blue-600 mr-3">
                        <i class="fas fa-robot text-white text-xl"></i>
                    </div>
                    <div>
                        <h2 class="text-xl sm:text-2xl font-bold text-white">Assistant IA Fiscal</h2>
                        <p class="text-blue-200 text-sm">Posez vos questions en français sur les données SRMT</p>
                    </div>
                </div>
            </div>

            <!-- Enhanced Query Input -->
            <div class="mb-6 sm:mb-8">
                <div class="relative">
                    <div class="flex flex-col sm:flex-row gap-3">
                        <input 
                            type="text" 
                            id="queryInput" 
                            placeholder="Ex: Quels sont les 10 plus gros contribuables par montant recouvré en 2025 ?" 
                            class="flex-1 px-4 py-3 sm:py-4 bg-white bg-opacity-10 border border-white border-opacity-30 rounded-xl text-white placeholder-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent focus:bg-opacity-15 transition-all">
                        <button 
                            id="analyzeBtn" 
                            class="btn-primary px-6 py-3 sm:py-4 rounded-xl text-white font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap">
                            <i class="fas fa-search mr-2"></i>Analyser
                        </button>
                    </div>
                </div>
            </div>

            <!-- Enhanced Quick Actions -->
            <div class="mb-6 sm:mb-8">
                <p class="text-blue-200 mb-4 font-medium flex items-center">
                    <i class="fas fa-bolt mr-2"></i>Analyses rapides :
                </p>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <button id="btnTop" class="bg-white bg-opacity-10 hover:bg-opacity-20 text-white px-4 py-3 rounded-xl text-sm transition-all flex items-center justify-center">
                        <i class="fas fa-trophy mr-2 text-yellow-400"></i>Top contribuables
                    </button>
                    <button id="btnEvolution" class="bg-white bg-opacity-10 hover:bg-opacity-20 text-white px-4 py-3 rounded-xl text-sm transition-all flex items-center justify-center">
                        <i class="fas fa-chart-line mr-2 text-green-400"></i>volution temporelle
                    </button>
                    <button id="btnRegional" class="bg-white bg-opacity-10 hover:bg-opacity-20 text-white px-4 py-3 rounded-xl text-sm transition-all flex items-center justify-center">
                        <i class="fas fa-map-marked-alt mr-2 text-blue-400"></i>Analyse régionale
                    </button>
                    <button id="btnComparaison" class="bg-white bg-opacity-10 hover:bg-opacity-20 text-white px-4 py-3 rounded-xl text-sm transition-all flex items-center justify-center">
                        <i class="fas fa-balance-scale mr-2 text-purple-400"></i>carts & Fraudes
                    </button>
                </div>
            </div>

            <!-- Enhanced Loading State -->
            <div id="loadingState" class="hidden text-center py-12">
                <div class="loading rounded-full h-12 w-12 border-4 border-white border-t-transparent mx-auto mb-4"></div>
                <p class="text-white font-medium text-lg">Analyse en cours...</p>
                <p class="text-blue-200 text-sm pulse-animation">Traitement par l'IA, veuillez patienter</p>
                <div class="mt-4 w-full bg-white bg-opacity-10 rounded-full h-1">
                    <div class="bg-blue-500 h-1 rounded-full animate-pulse" style="width: 60%;"></div>
                </div>
            </div>

            <!-- Enhanced Results Area -->
            <div id="resultsArea" class="hidden">"
                <div class="mb-4">
                    <h3 class="text-2xl font-bold text-white flex items-center">
                        <i class="fas fa-chart-pie mr-3 text-blue-400"></i>Résultats d'Analyse
                    </h3>
                    <div class="w-20 h-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mt-2"></div>
                </div>
                
                <div class="space-y-6">
                    <!-- Enhanced AI Response -->
                    <div class="glass rounded-2xl p-6 sm:p-8 border border-blue-500 border-opacity-30">
                        <h4 class="text-xl font-semibold text-white mb-4 flex items-center">
                            <div class="p-2 rounded-lg bg-gradient-to-r from-green-600 to-blue-600 mr-3">
                                <i class="fas fa-robot text-white"></i>
                            </div>
                            Analyse Intelligente
                        </h4>
                        <div id="aiResponse" class="text-blue-100 leading-relaxed text-base"></div>
                    </div>
                    
                    <!-- Enhanced Data Results -->
                    <div class="glass rounded-2xl p-6 sm:p-8 border border-emerald-500 border-opacity-30">
                        <h4 class="text-xl font-semibold text-white mb-4 flex items-center">
                            <div class="p-2 rounded-lg bg-gradient-to-r from-emerald-600 to-cyan-600 mr-3">
                                <i class="fas fa-table text-white"></i>
                            </div>
                            Données Résultantes
                        </h4>
                        <div id="dataResults" class="result-scroll"></div>
                    </div>
                    
                    <!-- Enhanced Performance Info -->
                    <div id="performanceInfo" class="glass rounded-2xl p-4 sm:p-6">
                        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between space-y-2 sm:space-y-0 text-sm">
                            <div class="flex items-center text-blue-200">
                                <i class="fas fa-stopwatch mr-2 text-blue-400"></i>
                                <span>Temps de traitement: <span id="processingTime" class="font-medium text-white">-</span>s</span>
                            </div>
                            <div class="flex items-center text-blue-200">
                                <i class="fas fa-search-plus mr-2 text-purple-400"></i>
                                <span>Correspondances RAG: <span id="ragMatches" class="font-medium text-white">-</span></span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Enhanced Code Section -->
                    <div class="glass rounded-2xl border border-gray-600 border-opacity-50">
                        <button id="toggleCodeBtn" class="w-full text-left p-4 sm:p-6 text-white font-medium flex items-center justify-between hover:bg-white hover:bg-opacity-5 transition-all rounded-2xl">
                            <div class="flex items-center">
                                <div class="p-2 rounded-lg bg-gradient-to-r from-gray-600 to-gray-700 mr-3">
                                    <i class="fas fa-code text-white"></i>
                                </div>
                                <span class="text-lg">Code Python Généré</span>
                            </div>
                            <i class="fas fa-chevron-down transition-transform text-blue-400" id="codeChevron"></i>
                        </button>
                        <div id="codeSection" class="hidden px-4 sm:px-6 pb-4 sm:pb-6">
                            <div class="bg-gray-900 rounded-xl p-4 border border-gray-700">
                                <div class="flex items-center justify-between mb-3">
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 rounded-full bg-red-500"></div>
                                        <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
                                        <div class="w-3 h-3 rounded-full bg-green-500"></div>
                                    </div>
                                    <span class="text-xs text-gray-400">Python  Polars</span>
                                </div>
                                <pre id="generatedCode" class="text-green-300 text-sm overflow-x-auto font-mono leading-relaxed"></pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Enhanced Footer -->
    <footer class="glass border-t border-white border-opacity-10 mt-12">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div class="flex flex-col sm:flex-row items-center justify-between space-y-4 sm:space-y-0">
                <div class="flex items-center space-x-4 text-blue-200 text-sm">
                    <span> 2026 SRMT Business Intelligence</span>
                    <span class="hidden sm:inline"></span>
                    <span class="flex items-center">
                        <i class="fas fa-shield-check mr-1 text-green-400"></i>
                        Système sécurisé avec nvidia 
                    </span>
                </div>
                <div class="flex items-center space-x-4 text-xs text-blue-300">
                    <span>Version 2.0</span>
                    <span></span>
                    <span>Powered by ACCEL-TECH</span>
                </div>
            </div>
        </div>
    </footer>

    <script>
        // Version avec addEventListener pour la fiabilité
        console.log('TOOL Interface SRMT - JavaScript chargé');

        function setQuery(query) {
            document.getElementById('queryInput').value = query;
            console.log('Query set:', query);
        }

        function toggleCode() {
            const codeSection = document.getElementById('codeSection');
            const chevron = document.getElementById('codeChevron');
            
            if (codeSection.classList.contains('hidden')) {
                codeSection.classList.remove('hidden');
                chevron.style.transform = 'rotate(180deg)';
            } else {
                codeSection.classList.add('hidden');
                chevron.style.transform = 'rotate(0deg)';
            }
            console.log('Code section toggled');
        }

        async function analyzeQuery() {
            console.log('DATA analyzeQuery() called');
            const query = document.getElementById('queryInput').value.trim();
            if (!query) {
                alert('Veuillez saisir une question');
                return;
            }

            // UI state management
            const loadingState = document.getElementById('loadingState');
            const resultsArea = document.getElementById('resultsArea');
            const analyzeBtn = document.getElementById('analyzeBtn');

            loadingState.classList.remove('hidden');
            resultsArea.classList.add('hidden');
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Analyse...';

            try {
                console.log('*** Sending request to API...');
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ question: query })
                });

                console.log(' Response status:', response.status, response.statusText);
                
                // Vérifier le Content-Type avant de parser
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error(`Réponse invalide du serveur (${response.status}). Type: ${contentType}`);
                }
                
                // Lire le JSON une seule fois
                const result = await response.json();
                console.log('OK API Response received');

                if (response.ok) {
                    displayResults(result);
                } else {
                    displayError(result.error || 'Erreur lors de l\'analyse');
                }
            } catch (error) {
                console.error('ERREUR API Error:', error);
                displayError('Erreur de connexion: ' + error.message);
            } finally {
                loadingState.classList.add('hidden');
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-search mr-1"></i>Analyser';
            }
        }

        function displayResults(result) {
            // TARGET AFFICHAGE DCISIONNEL ENRICHI
            const aiResponse = document.getElementById('aiResponse');
            
            // SEARCH DEBUG: Afficher ce qui est reçu
            console.log(' Result reçu:', result);
            console.log(' Type de result.response:', typeof result.response);
            console.log(' Contenu result.response:', result.response);
            
            // Vérifier si c'est une analyse décisionnelle structurée
            if (result.response && typeof result.response === 'object') {
                console.log('OK Affichage via formatDecisionAnalysis');
                console.log(' analyse_resume présent?', result.response.analyse_resume ? 'OUI' : 'NON');
                aiResponse.innerHTML = formatDecisionAnalysis(result.response);
            } else if (window.marked && result.response) {
                console.log(' Affichage via marked.parse (pas d\'objet structuré)');
                aiResponse.innerHTML = marked.parse(result.response);
            } else {
                console.log('ERREUR Affichage texte brut');
                aiResponse.innerHTML = (result.response || 'Aucune réponse générée').replace(/\n/g, '<br>');
            }

            // Data Results - Affichage enrichi
            const dataDiv = document.getElementById('dataResults');
            
            // Si c'est une réponse structurée avec donnees_detaillees
            let dataToDisplay = null;
            if (result.response && result.response.donnees_detaillees) {
                dataToDisplay = result.response.donnees_detaillees;
            } else if (result.execution_result) {
                dataToDisplay = result.execution_result;
            }
            
            // FAST TOUJOURS afficher en tableau si c'est un array
            if (dataToDisplay && Array.isArray(dataToDisplay) && dataToDisplay.length > 0) {
                dataDiv.innerHTML = formatTableData(dataToDisplay);
            } else if (dataToDisplay && typeof dataToDisplay === 'object' && !Array.isArray(dataToDisplay)) {
                // Si c'est un objet unique, le convertir en array à 1 élément
                dataDiv.innerHTML = formatTableData([dataToDisplay]);
            } else {
                dataDiv.innerHTML = '<p class="text-blue-200">Aucune donnée à afficher</p>';
            }

            // Generated Code
            document.getElementById('generatedCode').textContent = result.code || 'Aucun code généré';

            // Performance Info
            if (result.processing_time) {
                document.getElementById('processingTime').textContent = result.processing_time.toFixed(2);
            }
            if (result.rag_matches !== undefined) {
                document.getElementById('ragMatches').textContent = result.rag_matches;
            }

            // Show results
            document.getElementById('resultsArea').classList.remove('hidden');
        }
        
        function formatDecisionAnalysis(analysis) {
            let html = '<div class="space-y-4">';
            
            // Titre
            if (analysis.titre) {
                html += `<h3 class="text-2xl font-bold text-white mb-4">${analysis.titre}</h3>`;
            }
            
            //  ANALYSE RSUME NARRATIVE (briefing décisionnel complet)
            if (analysis.analyse_resume) {
                // Convertir le markdown basique en HTML
                let resumeHtml = analysis.analyse_resume
                    .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')
                    .replace(/\\*([^*]+)\\*/g, '<em>$1</em>')
                    .replace(/\\*/g, '')
                    .replace(/\n\n/g, '</p><p class="mt-3">')
                    .replace(/\n/g, '<br>');
                
                html += `<div class="bg-gradient-to-r from-indigo-900 to-blue-900 bg-opacity-40 p-6 rounded-lg border-l-4 border-indigo-400 mb-4">
                    <h4 class="font-bold text-indigo-200 mb-4 flex items-center text-lg">
                        <i class="fas fa-brain mr-2"></i>📋 Briefing Décisionnel
                    </h4>
                    <div class="text-white leading-relaxed text-base" style="line-height: 1.8;"><p>${resumeHtml}</p></div>
                </div>`;
            }
            
            // 🚨 ALERTES DÉCISIONNELLES (nouveau - affiché en premier si critique)
            if (analysis.alertes_decisionnelles && analysis.alertes_decisionnelles.length > 0) {
                html += `<div class="rounded-lg border-2 border-red-500 border-opacity-50 p-5 mb-4" style="background: rgba(220, 38, 38, 0.08);">
                    <h4 class="font-bold text-red-300 mb-4 text-lg flex items-center">
                        <i class="fas fa-exclamation-triangle mr-2"></i>🚨 Alertes pour la Prise de Décision
                    </h4>
                    <div class="space-y-3">`;
                
                analysis.alertes_decisionnelles.forEach(alerte => {
                    const bgColor = alerte.niveau === 'CRITIQUE' ? 'bg-red-900 bg-opacity-40 border-red-500' : 
                                    alerte.niveau === 'ATTENTION' ? 'bg-orange-900 bg-opacity-30 border-orange-500' : 
                                    'bg-blue-900 bg-opacity-20 border-blue-500';
                    const textColor = alerte.niveau === 'CRITIQUE' ? 'text-red-200' : 
                                     alerte.niveau === 'ATTENTION' ? 'text-orange-200' : 'text-blue-200';
                    html += `<div class="${bgColor} p-4 rounded-lg border-l-4">
                        <div class="flex items-start">
                            <span class="text-2xl mr-3">${alerte.icone || '⚠️'}</span>
                            <div class="flex-1">
                                <h5 class="${textColor} font-bold mb-1">${alerte.niveau} — ${alerte.titre}</h5>
                                <p class="text-white text-sm mb-2">${alerte.message}</p>
                                <p class="text-gray-300 text-xs italic"><i class="fas fa-arrow-right mr-1"></i>${alerte.action_requise}</p>
                            </div>
                        </div>
                    </div>`;
                });
                html += '</div></div>';
            }
            
            // Indicateurs Clés (KPIs enrichis)
            if (analysis.kpis && Object.keys(analysis.kpis).length > 0) {
                html += `<div class="mb-4">
                    <h4 class="font-bold text-blue-200 mb-3 text-lg flex items-center">
                        <i class="fas fa-chart-bar mr-2"></i>📊 Indicateurs Clés de Performance
                    </h4>`;
                html += '<div class="grid grid-cols-2 md:grid-cols-4 gap-3">';
                
                const kpiConfig = {
                    'montant_declare': { label: '💰 Total Déclaré', color: 'blue', icon: 'fas fa-file-invoice-dollar' },
                    'montant_recouvre': { label: '✅ Total Recouvré', color: 'green', icon: 'fas fa-coins' },
                    'attendu_mensuel': { label: '📅 Attendu Mensuel', color: 'purple', icon: 'fas fa-calendar-alt' },
                    'objectif': { label: '🎯 Objectif', color: 'indigo', icon: 'fas fa-bullseye' },
                    'taux_recouvrement': { label: '📈 Taux de Recouvrement', color: 'cyan', icon: 'fas fa-percentage' },
                    'atteinte_objectif': { label: '🏆 Atteinte Objectif', color: 'yellow', icon: 'fas fa-trophy' },
                    'ecart': { label: '📊 Écart Déclaré / Recouvré', color: 'orange', icon: 'fas fa-exchange-alt' },
                    'depassement_objectif': { label: '🚀 Dépassement Objectif', color: 'emerald', icon: 'fas fa-rocket' },
                    'moyenne_par_entite': { label: '📐 Montant Moyen / Entité', color: 'sky', icon: 'fas fa-chart-line' },
                    'concentration_top3': { label: '⚖️ Poids des 3 Premiers', color: 'amber', icon: 'fas fa-balance-scale' },
                    'valeur_max': { label: '🔺 Plus Gros Contributeur', color: 'green', icon: 'fas fa-arrow-up' },
                    'valeur_min': { label: '🔻 Plus Petit Contributeur', color: 'red', icon: 'fas fa-arrow-down' },
                    'nb_enregistrements_analyses': { label: '📋 Opérations Analysées', color: 'slate', icon: 'fas fa-database' }
                };
                
                const kpiOrder = ['montant_declare', 'montant_recouvre', 'attendu_mensuel', 'objectif', 
                                  'taux_recouvrement', 'atteinte_objectif', 'ecart', 'depassement_objectif',
                                  'moyenne_par_entite', 'concentration_top3', 'valeur_max', 'valeur_min', 'nb_enregistrements_analyses'];
                
                for (let key of kpiOrder) {
                    if (analysis.kpis[key] !== undefined && analysis.kpis[key] !== null) {
                        let value = analysis.kpis[key];
                        let displayValue = value;
                        let config = kpiConfig[key] || { label: key, color: 'gray', icon: 'fas fa-info-circle' };
                        
                        if (typeof value === 'number') {
                            if (key.includes('taux') || key.includes('atteinte') || key.includes('concentration')) {
                                displayValue = value.toFixed(1) + '%';
                            } else if (key === 'nb_enregistrements_analyses' || key === 'total_records') {
                                displayValue = value.toLocaleString('fr-FR');
                            } else {
                                displayValue = value.toLocaleString('fr-FR', {maximumFractionDigits: 0}) + ' FCFA';
                            }
                        }
                        
                        // Qualification couleur dynamique pour taux
                        let valueBgClass = 'bg-gray-800 bg-opacity-50';
                        if (key === 'taux_recouvrement' || key === 'atteinte_objectif') {
                            if (value >= 100) valueBgClass = 'bg-green-900 bg-opacity-40 border border-green-600';
                            else if (value >= 90) valueBgClass = 'bg-green-900 bg-opacity-20';
                            else if (value >= 80) valueBgClass = 'bg-yellow-900 bg-opacity-30 border border-yellow-600';
                            else valueBgClass = 'bg-red-900 bg-opacity-40 border border-red-600';
                        }
                        if (key === 'concentration_top3') {
                            if (value > 50) valueBgClass = 'bg-red-900 bg-opacity-30 border border-red-600';
                            else if (value > 30) valueBgClass = 'bg-yellow-900 bg-opacity-20';
                            else valueBgClass = 'bg-green-900 bg-opacity-20';
                        }
                        if (key === 'valeur_max') valueBgClass = 'bg-green-900 bg-opacity-30';
                        if (key === 'valeur_min') valueBgClass = 'bg-orange-900 bg-opacity-20';
                        
                        html += `<div class="${valueBgClass} rounded-lg p-3">
                            <div class="text-blue-200 text-xs mb-1 flex items-center">
                                <i class="${config.icon} mr-1 text-xs"></i>${config.label}
                            </div>
                            <div class="text-white font-bold text-lg">${displayValue}</div>
                        </div>`;
                    }
                }
                
                // Qualification de la performance globale
                if (analysis.kpis.qualification_performance) {
                    const qualifColors = {
                        'SURPERFORMANCE': 'bg-green-600',
                        'SATISFAISANTE': 'bg-green-500',
                        'MODÉRÉE': 'bg-yellow-500',
                        'CRITIQUE': 'bg-red-600'
                    };
                    const qualifColor = qualifColors[analysis.kpis.qualification_performance] || 'bg-gray-500';
                    html += `<div class="col-span-2 md:col-span-4 flex justify-center">
                        <span class="${qualifColor} text-white px-6 py-2 rounded-full font-bold text-sm tracking-wider">
                            PERFORMANCE GLOBALE : ${analysis.kpis.qualification_performance}
                        </span>
                    </div>`;
                }
                
                html += '</div></div>';
            }
            
            // 🎯 RECOMMANDATIONS STRATÉGIQUES POUR DÉCIDEURS (nouveau)
            if (analysis.recommandations_strategiques && analysis.recommandations_strategiques.length > 0) {
                html += `<div class="rounded-lg border-2 border-yellow-500 border-opacity-40 p-5 mb-4" style="background: rgba(234, 179, 8, 0.05);">
                    <h4 class="font-bold text-yellow-200 mb-4 text-lg flex items-center">
                        <i class="fas fa-bullseye mr-2"></i>🎯 Recommandations Stratégiques
                    </h4>
                    <div class="space-y-4">`;
                
                analysis.recommandations_strategiques.forEach((reco, index) => {
                    const priorityConfig = {
                        'CRITIQUE': { bg: 'bg-red-900 bg-opacity-30', border: 'border-red-500', badge: 'bg-red-600', icon: '🔥' },
                        'HAUTE': { bg: 'bg-orange-900 bg-opacity-20', border: 'border-orange-500', badge: 'bg-orange-600', icon: '⚡' },
                        'MOYENNE': { bg: 'bg-yellow-900 bg-opacity-15', border: 'border-yellow-500', badge: 'bg-yellow-600', icon: '📌' },
                        'INFO': { bg: 'bg-blue-900 bg-opacity-15', border: 'border-blue-500', badge: 'bg-blue-600', icon: 'ℹ️' }
                    };
                    const config = priorityConfig[reco.priorite] || priorityConfig['MOYENNE'];
                    
                    html += `<div class="${config.bg} ${config.border} border-l-4 p-4 rounded-lg">
                        <div class="flex items-start justify-between mb-2">
                            <div class="flex items-center">
                                <span class="${config.badge} text-white text-xs px-2 py-1 rounded-full font-bold mr-2">${config.icon} ${reco.priorite}</span>
                                <span class="text-gray-300 text-xs"><i class="fas fa-tag mr-1"></i>${reco.domaine || ''}</span>
                            </div>
                            <span class="text-gray-400 text-xs"><i class="fas fa-user-tie mr-1"></i>${reco.responsable || ''}</span>
                        </div>
                        <h5 class="text-white font-semibold mb-1">${reco.action}</h5>
                        <p class="text-gray-300 text-sm mb-2">${reco.detail || ''}</p>
                        <div class="flex items-center text-xs">
                            <span class="bg-green-900 bg-opacity-40 text-green-300 px-2 py-1 rounded"><i class="fas fa-chart-line mr-1"></i>Impact : ${reco.impact_estime || 'À évaluer'}</span>
                        </div>
                    </div>`;
                });
                html += '</div></div>';
            }
            
            // Synthèse exécutive (indicateurs textuels)
            if (analysis.synthese_executive) {
                let syntheseHtml = analysis.synthese_executive
                    .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')
                    .replace(/\\*([^*]+)\\*/g, '<em>$1</em>')
                    .replace(/\\*/g, '')
                    .replace(/\n/g, '<br>');

                html += `<div class="bg-blue-900 bg-opacity-30 p-4 rounded-lg border border-blue-500">
                    <h4 class="font-semibold text-blue-200 mb-2"><i class="fas fa-star mr-2"></i>Indicateurs Détaillés</h4>
                    <div class="text-white text-sm">${syntheseHtml}</div>
                </div>`;
            }
            
            // Recommandations IA (si activées)
            if (analysis.recommandations && analysis.recommandations.length > 0) {
                html += `<div class="bg-green-900 bg-opacity-20 p-4 rounded-lg border border-green-500">
                    <h4 class="font-semibold text-green-200 mb-3"><i class="fas fa-lightbulb mr-2"></i>Recommandations Complémentaires</h4>
                    <ul class="space-y-2">`;
                
                analysis.recommandations.forEach(rec => {
                    const priorityColors = {
                        'haute': 'text-red-300',
                        'moyenne': 'text-yellow-300',
                        'info': 'text-blue-300'
                    };
                    html += `<li class="${priorityColors[rec.priorite] || 'text-white'}">
                        <strong>${rec.action}</strong>: ${rec.justification}
                    </li>`;
                });
                
                html += '</ul></div>';
            }
            
            // Alertes IA (si activées)
            if (analysis.alertes && analysis.alertes.length > 0) {
                html += `<div class="bg-red-900 bg-opacity-30 p-4 rounded-lg border border-red-500">
                    <h4 class="font-semibold text-red-200 mb-2"><i class="fas fa-exclamation-triangle mr-2"></i>Alertes</h4>
                    <ul class="space-y-1">`;
                
                analysis.alertes.forEach(alert => {
                    html += `<li class="text-red-200"> ${alert.message}</li>`;
                });
                
                html += '</ul></div>';
            }
            
            html += '</div>';
            return html;
        }
        
        function formatDecisionData(data) {
            return `<pre class="text-sm text-blue-200 bg-gray-900 p-3 rounded">${JSON.stringify(data, null, 2)}</pre>`;
        }

        function displayError(error) {
            document.getElementById('aiResponse').innerHTML = `<div class="text-red-300 bg-red-900 bg-opacity-30 p-3 rounded"><i class="fas fa-exclamation-triangle mr-2"></i>${error}</div>`;
            document.getElementById('dataResults').innerHTML = '<p class="text-blue-200">Aucune donnée disponible suite à l\'erreur</p>';
            document.getElementById('generatedCode').textContent = '';
            document.getElementById('resultsArea').classList.remove('hidden');
        }

        let fullTableData = [];

        function formatTableData(data, showAll = false) {
            fullTableData = data;
            if (!data || data.length === 0) return '<p class="text-blue-200 text-center py-8"><i class="fas fa-info-circle mr-2"></i>Aucune donnée disponible</p>';

            // Intelligence: Adaptation dynamique selon le volume et la complexité
            const intelligentLimit = showAll ? data.length : Math.min(25, Math.max(10, Math.floor(data.length * 0.2)));
            const displayedData = data.slice(0, intelligentLimit);

            const keys = Object.keys(data[0]);
            
            // Enhanced responsive table with better styling
            let html = `<div class="overflow-x-auto rounded-xl border border-white border-opacity-10">
                <table class="data-table min-w-full text-sm">`;
            
            // Enhanced Header with gradients
            html += '<thead><tr>';
            keys.forEach((key, index) => {
                const isNumeric = typeof data[0][key] === 'number';
                const alignment = isNumeric ? 'text-right' : 'text-left';
                html += `<th class="px-4 py-3 ${alignment} font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 border-r border-blue-500 border-opacity-30 ${index === 0 ? 'rounded-tl-xl' : ''} ${index === keys.length - 1 ? 'rounded-tr-xl border-r-0' : ''}">${key}</th>`;
            });
            html += '</tr></thead>';
            
            // Enhanced Body with better styling
            html += '<tbody>';
            displayedData.forEach((row, rowIndex) => {
                const bgClass = rowIndex % 2 === 0 ? 'bg-white bg-opacity-5' : 'bg-white bg-opacity-8';
                html += `<tr class="${bgClass} hover:bg-blue-500 hover:bg-opacity-10 transition-colors">`;
                
                keys.forEach((key, colIndex) => {
                    const value = row[key];
                    const isNumeric = typeof value === 'number';
                    const alignment = isNumeric ? 'text-right' : 'text-left';
                    
                    let displayValue = '';
                    if (typeof value === 'number') {
                        if (Number.isInteger(value) && value > 1000) {
                            displayValue = `<span class="font-medium">${value.toLocaleString('fr-FR')}</span>`;
                        } else if (Number.isInteger(value)) {
                            displayValue = `<span class="font-medium">${value}</span>`;
                        } else {
                            displayValue = `<span class="font-medium">${value.toFixed(2).toLocaleString('fr-FR')}</span>`;
                        }
                    } else {
                        displayValue = value || '<span class="text-gray-400">-</span>';
                    }
                    
                    const borderClass = colIndex < keys.length - 1 ? 'border-r border-white border-opacity-10' : '';
                    html += `<td class="px-4 py-3 text-blue-100 ${alignment} ${borderClass}">${displayValue}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            
            // Enhanced pagination controls
            if (!showAll && data.length > intelligentLimit) {
                const totalPages = Math.ceil(data.length / intelligentLimit);
                html += `<div class="mt-6 flex flex-col sm:flex-row items-center justify-between space-y-4 sm:space-y-0 p-4 glass rounded-xl">
                    <div class="flex items-center space-x-4 text-sm text-blue-300">
                        <span class="flex items-center">
                            <i class="fas fa-table mr-2 text-blue-400"></i>
                            <strong class="text-white">${intelligentLimit}</strong> sur <strong class="text-white">${data.length}</strong> résultats
                        </span>
                        <span class="hidden sm:inline"></span>
                        <span class="text-xs bg-blue-500 bg-opacity-20 px-2 py-1 rounded-full">${Math.round((intelligentLimit/data.length)*100)}% affiché</span>
                    </div>
                    <div class="flex items-center space-x-3">
                        <button id="btnShowAll" onclick="expandTable()" class="px-4 py-2 btn-primary rounded-lg text-white text-sm transition-all flex items-center">
                            <i class="fas fa-eye mr-2"></i>Afficher tout
                        </button>
                        <button onclick="downloadCSV()" class="px-4 py-2 bg-white bg-opacity-10 hover:bg-opacity-20 border border-white border-opacity-30 rounded-lg text-white text-sm transition-all flex items-center">
                            <i class="fas fa-download mr-2"></i>Export CSV
                        </button>
                    </div>
                </div>`;
            } else {
                html += `<div class="text-center mt-4 p-3 glass rounded-xl">
                    <div class="flex items-center justify-center space-x-4 text-sm text-blue-400">
                        <span class="flex items-center">
                            <i class="fas fa-check-circle mr-2 text-green-400"></i>
                            Tous les résultats affichés
                        </span>
                        <span class="text-white font-medium">${data.length} enregistrements</span>
                        <button onclick="downloadCSV()" class="px-3 py-1 bg-white bg-opacity-10 hover:bg-opacity-20 rounded-lg transition-all flex items-center">
                            <i class="fas fa-download mr-1"></i>Export
                        </button>
                    </div>
                </div>`;
            }
            
            return html;
        }

        function downloadCSV() {
            if (!fullTableData || fullTableData.length === 0) return;
            
            const headers = Object.keys(fullTableData[0]);
            const csvContent = [
                headers.join(','),
                ...fullTableData.map(row => headers.map(key => {
                    const value = row[key];
                    return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
                }).join(','))
            ].join('\n');
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `srmt_export_${new Date().toISOString().slice(0,10)}.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        function expandTable() {
            const dataDiv = document.getElementById('dataResults');
            showToast('DATA Expansion de la table...', 'info');
            dataDiv.innerHTML = formatTableData(fullTableData, true);
        }

        // Configuration des événements avec addEventListener (plus fiable)
        document.addEventListener('DOMContentLoaded', function() {
            console.log('*** DOM loaded - Setting up event listeners');
            
            // Bouton principal d'analyse
            const analyzeBtn = document.getElementById('analyzeBtn');
            if (analyzeBtn) {
                analyzeBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('SEARCH Analyze button clicked');
                    analyzeQuery();
                });
                console.log('OK Analyze button event added');
            }

            // Boutons rapides
            const btnTop = document.getElementById('btnTop');
            if (btnTop) {
                btnTop.addEventListener('click', function() {
                    console.log('DATA Top contributors button clicked');
                    setQuery('Top 10 des contribuables par montant recouvré');
                });
            }

            const btnEvolution = document.getElementById('btnEvolution');
            if (btnEvolution) {
                btnEvolution.addEventListener('click', function() {
                    console.log('CHART Evolution button clicked');
                    setQuery('volution mensuelle des recouvrements en 2023');
                });
            }

            const btnRegional = document.getElementById('btnRegional');
            if (btnRegional) {
                btnRegional.addEventListener('click', function() {
                    console.log('REGIONAL Regional button clicked');
                    setQuery('Performance par direction régionale');
                });
            }

            const btnComparaison = document.getElementById('btnComparaison');
            if (btnComparaison) {
                btnComparaison.addEventListener('click', function() {
                    console.log('COMPARE Comparison button clicked');
                    setQuery('Comparaison montant déclaré vs recouvré');
                });
            }

            // Bouton toggle code
            const toggleCodeBtn = document.getElementById('toggleCodeBtn');
            if (toggleCodeBtn) {
                toggleCodeBtn.addEventListener('click', function() {
                    console.log('TOOL Toggle code button clicked');
                    toggleCode();
                });
            }

            // Enter key support
            const queryInput = document.getElementById('queryInput');
            if (queryInput) {
                queryInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        console.log('KEY Enter key pressed');
                        analyzeQuery();
                    }
                });
                queryInput.focus();
            }

            console.log('OK All event listeners configured');
        });

        // Test global des clics pour debug
        document.addEventListener('click', function(e) {
            console.log('CLICK Click detected on:', e.target.tagName, e.target.id || e.target.className);
        });
    </script>
</body>
</html>"""

if __name__ == '__main__':
    try:
        config = ProductionConfig()
        app = create_production_app()
        
        # Démarrage silencieux
        print("*** SRMT Business Intelligence - Serveur demarre ***")
        
        # Configuration des logs Flask pour voir les erreurs
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.INFO)
        
        if config.PRODUCTION_MODE:
            print("*** SRMT BI Server: http://localhost:5000")
            app.run(
                host='0.0.0.0',
                port=int(os.getenv('PORT', 5000)),
                debug=False,
                threaded=True
            )
        else:
            print("*** SRMT BI Server: http://localhost:5000")
            app.run(
                host='127.0.0.1',
                port=5000,
                debug=True,
                threaded=True
            )
    except Exception as e:
        print(f"ERREUR CRITIQUE AU DEMARRAGE: {e}")
        import traceback
        traceback.print_exc()
        input("Appuyez sur Entrée pour fermer...")