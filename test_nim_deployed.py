"""
Test d'inférence sur le modèle NIM déployé - LexFin Assistant
"""

import requests
import json

NIM_URL = "https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa"

print("=" * 70)
print("🚀 Test d'Inférence - LexFin Assistant (NIM Déployé)")
print("=" * 70)
print(f"🔗 URL: {NIM_URL}\n")

# Test 1: Question simple
print("TEST 1: Question Simple")
print("-" * 70)
payload1 = {"message": "Quelle est la capitale de la France?"}
print(f"📤 Requête: {json.dumps(payload1, ensure_ascii=False)}")

try:
    response = requests.post(
        f"{NIM_URL}/chat",
        json=payload1,
        timeout=30
    )
    print(f"📥 Status: {response.status_code}")
    print(f"✅ Réponse:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ Erreur: {e}")

print("\n" + "=" * 70)

# Test 2: Question fiscale
print("TEST 2: Question Fiscale (Domaine du modèle)")
print("-" * 70)
payload2 = {"message": "Qu'est-ce que la TVA au Sénégal?"}
print(f"📤 Requête: {json.dumps(payload2, ensure_ascii=False)}")

try:
    response = requests.post(
        f"{NIM_URL}/chat",
        json=payload2,
        timeout=30
    )
    print(f"📥 Status: {response.status_code}")
    result = response.json()
    print(f"✅ Réponse:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Extraire le texte de réponse
    if 'response' in result:
        print(f"\n💬 Message:")
        print(result['response'])
        
    if 'references' in result and result['references']:
        print(f"\n📚 Références: {len(result['references'])}")
        
except Exception as e:
    print(f"❌ Erreur: {e}")

print("\n" + "=" * 70)

# Test 3: Question douanière
print("TEST 3: Question Douanière")
print("-" * 70)
payload3 = {"message": "Comment calculer les droits de douane?"}
print(f"📤 Requête: {json.dumps(payload3, ensure_ascii=False)}")

try:
    response = requests.post(
        f"{NIM_URL}/chat",
        json=payload3,
        timeout=30
    )
    print(f"📥 Status: {response.status_code}")
    result = response.json()
    
    if 'response' in result:
        print(f"\n💬 Réponse:")
        print(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
        
except Exception as e:
    print(f"❌ Erreur: {e}")

print("\n" + "=" * 70)
print("✅ Tests terminés")
print("=" * 70)
