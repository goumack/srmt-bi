"""Test du système d'apprentissage intelligent"""
import time
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from srmt_production_ready import ProductionConfig, OptimizedDataLoader, ProductionRAGSystem, ProductionAIEngine

config = ProductionConfig()
loader = OptimizedDataLoader(config)
data, summary = loader.load_data()
rag = ProductionRAGSystem(loader.data)
ai = ProductionAIEngine(config, rag, summary, loader.aggregated_tables, loader.lookup_index)

# Test 1: Requete deja connue (devrait etre cachee)
print("=" * 60)
print("TEST 1: Requete similaire a une deja reussie (cache)")
print("=" * 60)
t = time.time()
r = ai.analyze_query("Top 5 des contribuables par montant recouvre en 2025")
elapsed = time.time() - t
cached = r.get("cached_pattern", False)
print(f"  Temps: {elapsed:.2f}s | Cache: {cached}")
print(f"  Resultats: {len(r.get('execution_result', []))} lignes")
print()

# Test 2: Requete nouvelle (doit appeler API)
print("=" * 60)
print("TEST 2: Requete nouvelle (appel API)")
print("=" * 60)
t = time.time()
r2 = ai.analyze_query("Quel est le montant total des recettes par bureau en 2025")
elapsed2 = time.time() - t
cached2 = r2.get("cached_pattern", False)
err = r2.get("error")
print(f"  Temps: {elapsed2:.2f}s | Cache: {cached2}")
if err:
    print(f"  Erreur: {err}")
else:
    res = r2.get("execution_result", [])
    print(f"  Resultats: {len(res) if isinstance(res, list) else 'N/A'} lignes")
print()

# Test 3: Meme requete re-executee (devrait etre cachee maintenant)
print("=" * 60)
print("TEST 3: Meme requete re-executee (devrait etre cache)")
print("=" * 60)
t = time.time()
r3 = ai.analyze_query("Quel est le montant total des recettes par bureau en 2025")
elapsed3 = time.time() - t
cached3 = r3.get("cached_pattern", False)
print(f"  Temps: {elapsed3:.2f}s | Cache: {cached3}")
print()

print("=" * 60)
print("RESUME")
print("=" * 60)
print(f"  Test 1 (cache):    {elapsed:.2f}s")
print(f"  Test 2 (API):      {elapsed2:.2f}s")
print(f"  Test 3 (re-cache): {elapsed3:.2f}s")
print(f"  Gain cache: {elapsed2/max(elapsed3,0.01):.0f}x plus rapide")
