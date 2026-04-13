"""Test de performance DIRECT - Sans serveur Flask, test inline"""
import time
import json
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("TEST DE PERFORMANCE SRMT (mode direct)")
print("=" * 50)
print()

# 1. Mesurer le chargement
print("1. Chargement des données...")
t0 = time.time()
from srmt_production_ready import ProductionConfig, OptimizedDataLoader, ProductionRAGSystem, ProductionAIEngine
config = ProductionConfig()
loader = OptimizedDataLoader(config)
data, summary = loader.load_data()
t_load = time.time() - t0
print(f"   => Chargement: {t_load:.2f}s | {len(loader.data_materialized):,} enregistrements")
print()

# 2. Init RAG + IA
print("2. Initialisation RAG + IA...")
t1 = time.time()
rag = ProductionRAGSystem(loader.data)
ai = ProductionAIEngine(config, rag, summary, loader.aggregated_tables, loader.lookup_index)
t_init = time.time() - t1
print(f"   => Init: {t_init:.2f}s")
print()

# 3. Test requête
question = "Top 5 des contribuables par montant recouvré en 2025"
print(f"3. Requête: {question}")
print("   En cours...")
t2 = time.time()
result = ai.analyze_query(question)
t_query = time.time() - t2
print()

print("=" * 50)
print(f"   TEMPS CHARGEMENT:  {t_load:.2f}s")
print(f"   TEMPS INIT:        {t_init:.2f}s")
print(f"   TEMPS REQUÊTE:     {t_query:.2f}s")
print(f"   TEMPS TOTAL:       {t_load + t_init + t_query:.2f}s")
print("=" * 50)
print()

# Résultat
resp = result.get('response', {})
if isinstance(resp, dict):
    if resp.get('analyse_resume'):
        print("ANALYSE:")
        print(resp['analyse_resume'][:400])
        print()
    if resp.get('donnees_detaillees'):
        dd = resp['donnees_detaillees']
        print(f"DONNÉES: {len(dd)} lignes")
        for i, row in enumerate(dd[:3]):
            print(f"  L{i+1}: {json.dumps(row, ensure_ascii=False)[:180]}")
    if resp.get('kpis'):
        print(f"\nKPIs: {json.dumps(resp['kpis'], ensure_ascii=False)}")
elif isinstance(resp, str):
    print("RÉPONSE:", resp[:400])
else:
    print("RÉSULTAT:", str(result)[:400])
