#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test de l'API SRMT depuis le terminal
"""

import requests
import json

# Configuration
API_URL = "http://127.0.0.1:5000/api/analyze"
TIMEOUT = 120  # 2 minutes

def test_query(question):
    """Teste une question via l'API"""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print(f"{'='*80}\n")
    
    try:
        response = requests.post(
            API_URL,
            json={'question': question},
            timeout=TIMEOUT
        )
        
        print(f"✅ Status HTTP: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Code généré
            code = data.get('code', '')
            print(f"\n📝 Code généré ({len(code)} caractères):")
            print("-" * 80)
            print(code)
            print("-" * 80)
            
            # Résultat d'exécution
            exec_result = data.get('execution_result')
            if exec_result:
                if isinstance(exec_result, list):
                    print(f"\n📊 Résultats: {len(exec_result)} enregistrements")
                    print("5 premiers:")
                    for i, row in enumerate(exec_result[:5], 1):
                        print(f"  {i}. {row}")
                elif isinstance(exec_result, dict):
                    print(f"\n📊 Résultat (dict avec {len(exec_result)} clés):")
                    for key, value in list(exec_result.items())[:10]:
                        print(f"  {key}: {value}")
                else:
                    print(f"\n📊 Résultat: {exec_result}")
            else:
                print("\n❌ Pas de résultat d'exécution")
            
            # Analyse narrative
            analysis = data.get('response', '')
            print(f"\n🧠 Analyse ({len(analysis)} caractères):")
            print("-" * 80)
            print(analysis)
            print("-" * 80)
            
            # Temps de traitement
            processing_time = data.get('processing_time', 0)
            print(f"\n⏱️ Temps de traitement: {processing_time:.2f}s")
            
            # Erreurs éventuelles
            error = data.get('error')
            if error:
                print(f"\n⚠️ Erreur: {error}")
                
        else:
            print(f"\n❌ Erreur HTTP {response.status_code}")
            print(response.text)
            
    except requests.Timeout:
        print(f"\n❌ Timeout après {TIMEOUT}s")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")


if __name__ == "__main__":
    import sys
    
    # Test avec question en argument ou questions par défaut
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        test_query(question)
    else:
        # Questions de test
        questions = [
            "Quels bureaux ont le plus d'anomalies aujourd'hui?",
            "Performance par direction régionale",
            "Top 10 contribuables",
        ]
        
        print("🧪 Tests API SRMT")
        print("="*80)
        
        for question in questions:
            test_query(question)
            print("\n" + "="*80 + "\n")
