"""
Script de test pour l'inférence sur le modèle NIM déployé
URL: https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa/
"""

import requests
import json
import time

# Configuration
NIM_API_URL = "https://srmt-documind-nim-exploration-srmt.apps.ocp.heritage.africa"
API_KEY = "votre_api_key_si_necessaire"  # Modifier si authentification requise

def test_health():
    """Test de santé du endpoint"""
    print("=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    
    try:
        response = requests.get(f"{NIM_API_URL}/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_inference_completion(prompt: str):
    """Test d'inférence avec completion endpoint"""
    print("\n" + "=" * 60)
    print("TEST 2: Inference - Completion")
    print("=" * 60)
    
    payload = {
        "model": "meta/llama-3.1-405b-instruct",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.5,
        "max_tokens": 1024
    }
    
    headers = {
        "Content-Type": "application/json",
    }
    
    # Ajouter API key si nécessaire
    if API_KEY and API_KEY != "votre_api_key_si_necessaire":
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    try:
        print(f"\n📤 Requête:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        start_time = time.time()
        response = requests.post(
            f"{NIM_API_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Temps: {elapsed:.2f}s")
        print(f"📥 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Réponse:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Extraire le texte de réponse
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                print(f"\n💬 Contenu:")
                print(content)
        else:
            print(f"\n❌ Erreur:")
            print(response.text)
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_inference_simple(prompt: str):
    """Test d'inférence simple (si endpoint différent)"""
    print("\n" + "=" * 60)
    print("TEST 3: Inference - Simple")
    print("=" * 60)
    
    payload = {
        "prompt": prompt,
        "max_tokens": 500,
        "temperature": 0.5
    }
    
    headers = {
        "Content-Type": "application/json",
    }
    
    if API_KEY and API_KEY != "votre_api_key_si_necessaire":
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    try:
        response = requests.post(
            f"{NIM_API_URL}/v1/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Réponse:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"❌ Erreur:")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

def test_models_list():
    """Liste des modèles disponibles"""
    print("\n" + "=" * 60)
    print("TEST 4: Liste des Modèles")
    print("=" * 60)
    
    try:
        response = requests.get(f"{NIM_API_URL}/v1/models", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(response.text)
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    print("🚀 Test d'inférence sur modèle NIM déployé")
    print(f"🔗 URL: {NIM_API_URL}")
    print()
    
    # Test 1: Health check
    health_ok = test_health()
    
    if not health_ok:
        print("\n⚠️  Le endpoint health ne répond pas. On continue quand même...")
    
    # Test 2: Liste des modèles
    test_models_list()
    
    # Test 3: Inférence avec chat completion
    test_prompt = "Quelle est la capitale de la France?"
    test_inference_completion(test_prompt)
    
    # Test 4: Inférence simple (endpoint alternatif)
    test_inference_simple(test_prompt)
    
    print("\n" + "=" * 60)
    print("✅ Tests terminés")
    print("=" * 60)
