"""Test de la requête avec négation et filtre SOURCE"""
import requests
import json

url = "http://localhost:5000/api/analyze"
query = "quelles sont les recettes recu aujourdhui a la DGD dans le bureau de kedougou pas le CSF de kedougou"

print(f"🔍 Requête: {query}")
print("=" * 80)

try:
    r = requests.post(url, json={"question": query}, timeout=60)
    d = r.json()
    
    # Afficher toutes les clés de la réponse
    print(f"\n🔑 Clés réponse: {list(d.keys())}")
    
    # Afficher le code (chercher dans différents champs)
    code = d.get("code", d.get("generated_code", d.get("python_code", "N/A")))
    print("\n📝 CODE GÉNÉRÉ:")
    print(code)
    
    # Afficher les premières 500 chars de la réponse brute
    raw = json.dumps(d, ensure_ascii=False, default=str)
    print(f"\n📋 RÉPONSE BRUTE (500 chars):")
    print(raw[:500])
    
    print("\n📊 RÉSULTATS:")
    data = d.get("data", {})
    if isinstance(data, dict):
        items = data.get("principal", [])
    elif isinstance(data, list):
        items = data
    else:
        items = []
        print(data)
    
    print(f"Nombre de résultats: {len(items)}")
    for i, item in enumerate(items[:15]):
        bureau = item.get("BUREAU", "?")
        source = item.get("SOURCE", "?")
        recouvre = item.get("TOTAL_RECOUVRE", item.get("MONTANT_RECOUVRE", "?"))
        print(f"  [{i+1}] {bureau} | SOURCE={source} | RECOUVRE={recouvre}")
    
    # Vérifications
    print("\n✅ VÉRIFICATIONS:")
    has_csf = any("csf" in str(item.get("BUREAU", "")).lower() for item in items)
    has_dgid = any("DGID" in str(item.get("SOURCE", "")) for item in items)
    has_bureau_kedougou = any("bureau" in str(item.get("BUREAU", "")).lower() and "kedougou" in str(item.get("BUREAU", "")).lower() for item in items)
    
    print(f"  CSF présent (devrait être NON): {'❌ OUI - ERREUR!' if has_csf else '✅ NON - CORRECT!'}")
    print(f"  DGID présent (devrait être NON): {'❌ OUI - ERREUR!' if has_dgid else '✅ NON - CORRECT!'}")
    print(f"  Bureau kedougou présent (devrait être OUI): {'✅ OUI - CORRECT!' if has_bureau_kedougou else '❌ NON - ERREUR!'}")

except Exception as e:
    print(f"❌ Erreur: {e}")
