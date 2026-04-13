"""
🧠 Système d'Apprentissage IA Avancé
Mémorisation intelligente des patterns de succès sans règles hardcodées
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib


@dataclass
class ErrorPattern:
    """Pattern d'erreur appris pour éviter les répétitions"""
    error_hash: str
    original_error: str
    error_type: str
    failed_code: str
    correction_applied: Optional[str]
    timestamp: float
    occurrence_count: int = 1
    corrected_code: Optional[str] = None  # Le code corrigé qui a résolu l'erreur
    
    def to_dict(self):
        return asdict(self)


@dataclass
class SuccessPattern:
    """Pattern de succès appris par l'IA"""
    query_hash: str
    original_query: str
    normalized_query: str
    successful_code: str
    execution_summary: Dict[str, Any]
    columns_used: List[str]
    filters_used: List[str]
    aggregations_used: List[str]
    timestamp: float
    success_count: int = 1
    
    def to_dict(self):
        return asdict(self)


class AILearningSystem:
    """🧠 Système d'apprentissage pur avec gestion des erreurs - Aucune règle prédéfinie"""
    
    def __init__(self, cache_file: str = "ai_learning_cache.json"):
        self.cache_file = Path(cache_file)
        self.patterns: Dict[str, SuccessPattern] = {}
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.load_cache()
    
    def normalize_query(self, query: str) -> str:
        """Normalisation intelligente de la requête"""
        # Minuscules, suppression ponctuation, espaces multiples
        normalized = query.lower().strip()
        normalized = ' '.join(normalized.split())
        # Garder seulement alphanumérique et espaces
        normalized = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in normalized)
        return ' '.join(normalized.split())
    
    def hash_query(self, query: str) -> str:
        """Hash de la requête normalisée"""
        normalized = self.normalize_query(query)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def hash_error(self, error_message: str, error_type: str) -> str:
        """Hash d'une erreur pour identification"""
        error_key = f"{error_type}:{error_message}"
        return hashlib.sha256(error_key.encode()).hexdigest()[:16]
    
    def learn_from_error(self, error_message: str, error_type: str, failed_code: str, correction: Optional[str] = None, corrected_code: Optional[str] = None):
        """📚 Apprend d'une erreur pour l'éviter à l'avenir
        corrected_code: le code complet qui a corrigé l'erreur (pour réutilisation directe)"""
        error_hash = self.hash_error(error_message, error_type)
        
        if error_hash in self.error_patterns:
            # Incrémenter le compteur d'occurrence
            self.error_patterns[error_hash].occurrence_count += 1
            # Mettre à jour le code corrigé si fourni
            if corrected_code:
                self.error_patterns[error_hash].corrected_code = corrected_code
                self.error_patterns[error_hash].correction_applied = correction
        else:
            # Nouveau pattern d'erreur
            self.error_patterns[error_hash] = ErrorPattern(
                error_hash=error_hash,
                original_error=error_message,
                error_type=error_type,
                failed_code=failed_code,
                correction_applied=correction,
                timestamp=time.time(),
                corrected_code=corrected_code
            )
        
        self.save_cache()
        print(f"🧠 Erreur apprise: {error_type} (occurrence #{self.error_patterns[error_hash].occurrence_count})")
    
    def get_error_prevention_prompt(self) -> str:
        """💡 Génère un prompt avec les erreurs corrigées - NE JAMAIS les reproduire"""
        if not self.error_patterns:
            return ""
        
        # Seulement les erreurs qui ONT une correction connue (les plus utiles)
        corrected_errors = [
            e for e in self.error_patterns.values()
            if e.correction_applied
        ]
        # Trier par fréquence d'occurrence
        sorted_errors = sorted(
            corrected_errors if corrected_errors else list(self.error_patterns.values()),
            key=lambda x: x.occurrence_count,
            reverse=True
        )[:5]  # Top 5 erreurs
        
        prevention_lines = ["🚫 ERREURS DÉJÀ CORRIGÉES - NE JAMAIS REPRODUIRE:"]
        
        for i, error in enumerate(sorted_errors, 1):
            # Extraire un résumé court de l'erreur
            error_short = error.original_error[:100]
            prevention_lines.append(f"{i}. ❌ INTERDIT: {error.error_type} - {error_short}")
            if error.correction_applied:
                prevention_lines.append(f"   ✅ FAIRE: {error.correction_applied}")
            # Si on a le code fautif, montrer un exemple concret
            if error.failed_code and 'agg()' in error.failed_code and 'group_by' not in error.failed_code:
                prevention_lines.append(f"   ❌ CODE FAUX: data.filter().agg() → CRASH")
                prevention_lines.append(f"   ✅ CODE BON: data.filter().group_by().agg()")
        
        return "\n".join(prevention_lines)
    
    def get_successful_code_for_query(self, query: str, threshold: float = 0.75) -> Optional[str]:
        """🔄 Retourne le code qui a DÉJÀ fonctionné pour une requête similaire
        Avec validation sémantique: vérifie que les filtres critiques sont présents"""
        pattern = self.find_similar_pattern(query, similarity_threshold=threshold)
        if pattern and pattern.success_count >= 1:
            # ⚠️ VALIDATION SÉMANTIQUE: vérifier cohérence mots-clés / code en cache
            if not self._validate_cache_coherence(query, pattern.successful_code):
                return None  # Cache incohérent, forcer appel API
            return pattern.successful_code
        return None
    
    def _validate_cache_coherence(self, query: str, cached_code: str) -> bool:
        """🔍 Vérifie que le code en cache est cohérent avec les mots-clés de la requête"""
        q = query.lower()
        code_lower = cached_code.lower()
        
        # 1. Si la requête mentionne DGD/douane → le code DOIT avoir un filtre SOURCE
        source_keywords = {'dgd', 'douane', 'régie douane', 'regie douane'}
        if any(kw in q for kw in source_keywords):
            if "source" not in code_lower:
                return False  # ❌ Requête DGD mais pas de filtre SOURCE
        
        # 2. Si la requête mentionne DGID/impôts → le code DOIT avoir un filtre SOURCE
        dgid_keywords = {'dgid', 'impôts', 'impots', 'fiscale'}
        if any(kw in q for kw in dgid_keywords):
            if "source" not in code_lower:
                return False  # ❌ Requête DGID mais pas de filtre SOURCE
        
        # 3. Si la requête contient une négation → le code DOIT avoir ~ ou != 
        negation_words = {'pas le ', 'pas la ', 'pas les ', 'sauf ', 'sans ', 'hors ', 'excepté ', 'excepte '}
        if any(neg in q for neg in negation_words):
            if '~' not in cached_code and '!=' not in cached_code:
                return False  # ❌ Requête avec exclusion mais pas de négation dans le code
        
        # 4. Si la requête mentionne un bureau spécifique ET exclut un type (CSF/Bureau)
        if 'csf' in q and ('pas' in q or 'sauf' in q or 'sans' in q):
            if '~' not in cached_code or 'csf' not in code_lower:
                return False  # ❌ Exclure CSF mais code ne le fait pas
        
        # 5. ⚠️ CRITIQUE: Vérifier que les noms de lieux/bureaux de la requête
        #    sont AUSSI présents dans le code en cache (éviter kedougou→dakar etc.)
        lieu_keywords = [
            'kedougou', 'dakar', 'thies', 'thiès', 'kaolack', 'ziguinchor',
            'saint-louis', 'saint louis', 'tambacounda', 'kolda', 'matam',
            'fatick', 'louga', 'diourbel', 'kaffrine', 'sedhiou', 'sédhiou',
            'kédougou', 'port nord', 'port sud', 'mbour', 'rufisque',
            'grandes entreprises', 'professions reglementees',
        ]
        # Trouver les lieux mentionnés dans la requête
        lieux_requete = [lieu for lieu in lieu_keywords if lieu in q]
        if lieux_requete:
            # Au moins un lieu de la requête doit être dans le code
            lieux_dans_code = [lieu for lieu in lieux_requete if lieu in code_lower]
            if not lieux_dans_code:
                return False  # ❌ Requête parle de 'dakar' mais code filtre 'kedougou'
        
        # 6. Vérifier les directions mentionnées
        direction_keywords = [
            'regionale', 'régionale', 'sud-est', 'ouest', 'nord',
            'services fiscaux', 'services regionaux',
        ]
        dirs_requete = [d for d in direction_keywords if d in q]
        if dirs_requete:
            dirs_dans_code = [d for d in dirs_requete if d in code_lower]
            if not dirs_dans_code:
                return False  # ❌ Requête parle d'une direction absente du code
        
        return True  # ✅ Code en cache cohérent avec la requête
    
    def update_error_with_correction(self, error_type: str, error_message: str, corrected_code: str):
        """📝 Met à jour un pattern d'erreur avec le code corrigé qui a fonctionné"""
        error_hash = self.hash_error(error_message, error_type)
        if error_hash in self.error_patterns:
            self.error_patterns[error_hash].correction_applied = f"Code corrigé disponible"
            self.error_patterns[error_hash].corrected_code = corrected_code
            self.save_cache()
    
    def find_correction_for_error(self, error_message: str, failed_code: str) -> Optional[str]:
        """🔍 Cherche dans le cache si une erreur similaire a déjà été corrigée.
        Retourne le CODE CORRIGÉ qui a résolu l'erreur, ou None."""
        from difflib import SequenceMatcher
        
        best_correction = None
        best_similarity = 0.0
        
        for pattern in self.error_patterns.values():
            # On ne peut corriger que si on a un code corrigé stocké
            if not pattern.corrected_code:
                continue
            
            # Comparer le type d'erreur (mots-clés dans le message)
            error_sim = SequenceMatcher(None, 
                error_message[:150].lower(), 
                pattern.original_error[:150].lower()
            ).ratio()
            
            # Comparer aussi le code fautif (même structure = même correction)
            code_sim = 0.0
            if pattern.failed_code and pattern.failed_code != "Voir erreur ci-dessus":
                code_sim = SequenceMatcher(None,
                    failed_code[:300].lower(),
                    pattern.failed_code[:300].lower()
                ).ratio()
            
            # Score combiné : 70% erreur + 30% code
            combined = error_sim * 0.7 + code_sim * 0.3
            
            if combined > best_similarity and combined >= 0.6:
                best_similarity = combined
                best_correction = pattern.corrected_code
        
        return best_correction
    
    def extract_code_patterns(self, code: str) -> Dict[str, List[str]]:
        """🔍 Extraction intelligente des patterns du code"""
        import re
        
        patterns = {
            'columns': [],
            'filters': [],
            'aggregations': []
        }
        
        # Colonnes utilisées (pl.col('NOM'))
        col_matches = re.findall(r"pl\.col\(['\"](\w+)['\"]\)", code)
        patterns['columns'] = list(set(col_matches))
        
        # Filtres (filter, contains, etc.)
        if 'filter(' in code:
            patterns['filters'].append('filter')
        if '.contains(' in code:
            patterns['filters'].append('contains')
        if '==' in code:
            patterns['filters'].append('equality')
        if '.dt.' in code:
            patterns['filters'].append('date_filter')
        
        # Agrégations
        if 'group_by(' in code:
            patterns['aggregations'].append('group_by')
        if '.sum()' in code:
            patterns['aggregations'].append('sum')
        if '.mean()' in code:
            patterns['aggregations'].append('mean')
        if '.count()' in code:
            patterns['aggregations'].append('count')
        if '.head(' in code:
            patterns['aggregations'].append('limit')
        
        return patterns
    
    def learn_from_success(self, query: str, code: str, execution_result: Any):
        """📚 Apprentissage à partir d'un succès"""
        query_hash = self.hash_query(query)
        normalized = self.normalize_query(query)
        
        # Extraction des patterns
        code_patterns = self.extract_code_patterns(code)
        
        # Résumé du résultat
        exec_summary = {
            'result_type': type(execution_result).__name__,
            'result_count': len(execution_result) if hasattr(execution_result, '__len__') else 1,
            'timestamp': time.time()
        }
        
        if query_hash in self.patterns:
            # Pattern déjà connu - augmenter le compteur
            self.patterns[query_hash].success_count += 1
            self.patterns[query_hash].timestamp = time.time()
        else:
            # Nouveau pattern
            self.patterns[query_hash] = SuccessPattern(
                query_hash=query_hash,
                original_query=query,
                normalized_query=normalized,
                successful_code=code,
                execution_summary=exec_summary,
                columns_used=code_patterns['columns'],
                filters_used=code_patterns['filters'],
                aggregations_used=code_patterns['aggregations'],
                timestamp=time.time()
            )
        
        # Sauvegarder
        self.save_cache()
    
    def find_similar_pattern(self, query: str, similarity_threshold: float = 0.7) -> Optional[SuccessPattern]:
        """🔍 Recherche de pattern similaire appris"""
        from difflib import SequenceMatcher
        
        normalized = self.normalize_query(query)
        
        best_match = None
        best_similarity = 0.0
        
        for pattern in self.patterns.values():
            similarity = SequenceMatcher(None, normalized, pattern.normalized_query).ratio()
            
            if similarity > best_similarity and similarity >= similarity_threshold:
                best_similarity = similarity
                best_match = pattern
        
        return best_match
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """📊 Statistiques d'apprentissage"""
        if not self.patterns:
            return {
                'total_patterns': 0,
                'most_used': None,
                'recent_learning': []
            }
        
        # Pattern le plus utilisé
        most_used = max(self.patterns.values(), key=lambda p: p.success_count)
        
        # Apprentissages récents
        recent = sorted(
            self.patterns.values(),
            key=lambda p: p.timestamp,
            reverse=True
        )[:5]
        
        return {
            'total_patterns': len(self.patterns),
            'most_used': {
                'query': most_used.original_query,
                'count': most_used.success_count
            },
            'recent_learning': [
                {
                    'query': p.original_query,
                    'columns': p.columns_used,
                    'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p.timestamp))
                }
                for p in recent
            ],
            'top_columns': self._get_top_columns(),
            'top_operations': self._get_top_operations()
        }
    
    def _get_top_columns(self) -> List[Dict[str, int]]:
        """Colonnes les plus utilisées"""
        from collections import Counter
        
        all_columns = []
        for pattern in self.patterns.values():
            all_columns.extend(pattern.columns_used)
        
        counter = Counter(all_columns)
        return [{'column': col, 'count': count} for col, count in counter.most_common(10)]
    
    def _get_top_operations(self) -> List[Dict[str, int]]:
        """Opérations les plus utilisées"""
        from collections import Counter
        
        all_ops = []
        for pattern in self.patterns.values():
            all_ops.extend(pattern.filters_used)
            all_ops.extend(pattern.aggregations_used)
        
        counter = Counter(all_ops)
        return [{'operation': op, 'count': count} for op, count in counter.most_common(10)]
    
    def save_cache(self):
        """💾 Sauvegarde du cache d'apprentissage"""
        try:
            cache_data = {
                'version': '1.1',
                'last_updated': time.time(),
                'patterns': {
                    key: pattern.to_dict()
                    for key, pattern in self.patterns.items()
                },
                'error_patterns': {
                    key: error.to_dict()
                    for key, error in self.error_patterns.items()
                }
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde cache: {e}")
    
    def load_cache(self):
        """📂 Chargement du cache d'apprentissage"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Charger les patterns de succès
                for key, pattern_dict in cache_data.get('patterns', {}).items():
                    self.patterns[key] = SuccessPattern(**pattern_dict)
                
                # Charger les patterns d'erreur
                for key, error_dict in cache_data.get('error_patterns', {}).items():
                    self.error_patterns[key] = ErrorPattern(**error_dict)
                
                print(f"✅ Cache chargé: {len(self.patterns)} patterns de succès, {len(self.error_patterns)} patterns d'erreur")
            else:
                print("ℹ️ Nouveau cache d'apprentissage créé")
        
        except Exception as e:
            print(f"⚠️ Erreur chargement cache: {e}")
            self.patterns = {}
            self.error_patterns = {}
    
    def reset_cache(self):
        """🗑️ Réinitialisation complète"""
        self.patterns = {}
        self.error_patterns = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        print("✅ Cache réinitialisé")


# API simplifiée
def create_learning_system(cache_file: str = "ai_learning_cache.json") -> AILearningSystem:
    """Factory pour créer le système d'apprentissage"""
    return AILearningSystem(cache_file)
